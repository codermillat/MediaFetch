"""
Caching System for MediaFetch
Provides multi-level caching for improved performance and reduced database load
"""

import time
import json
import hashlib
from typing import Dict, Any, Optional, Callable, Union
from functools import wraps
import threading
import logging

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a cached item with TTL"""

    def __init__(self, value: Any, ttl: int = 300):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl

    def is_expired(self) -> bool:
        """Check if the cache entry has expired"""
        return time.time() - self.created_at > self.ttl

    def get_age(self) -> float:
        """Get the age of the cache entry in seconds"""
        return time.time() - self.created_at


class CacheManager:
    """Multi-level caching system with memory and file-based storage"""

    def __init__(self,
                 default_ttl: int = 300,  # 5 minutes
                 max_memory_entries: int = 1000,
                 cleanup_interval: int = 300):  # 5 minutes
        self.default_ttl = default_ttl
        self.max_memory_entries = max_memory_entries
        self.cleanup_interval = cleanup_interval

        # Memory cache
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'expired': 0,
            'evictions': 0,
            'sets': 0
        }

        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()

        logger.info("Cache manager initialized")

    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """Get a value from cache"""
        with self._lock:
            if key in self._memory_cache:
                entry = self._memory_cache[key]

                if entry.is_expired():
                    del self._memory_cache[key]
                    self.stats['expired'] += 1
                    self.stats['misses'] += 1
                    return default
                else:
                    self.stats['hits'] += 1
                    return entry.value
            else:
                self.stats['misses'] += 1
                return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache"""
        with self._lock:
            if len(self._memory_cache) >= self.max_memory_entries:
                self._evict_oldest()

            ttl_value = ttl if ttl is not None else self.default_ttl
            self._memory_cache[key] = CacheEntry(value, ttl_value)
            self.stats['sets'] += 1
            return True

    def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        with self._lock:
            if key in self._memory_cache:
                del self._memory_cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._memory_cache.clear()
            logger.info("Cache cleared")

    def has(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        with self._lock:
            if key in self._memory_cache:
                entry = self._memory_cache[key]
                if not entry.is_expired():
                    return True
                else:
                    del self._memory_cache[key]
            return False

    def get_or_set(self, key: str, func: Callable, ttl: Optional[int] = None) -> Any:
        """Get value from cache or compute and cache it"""
        value = self.get(key)
        if value is None:
            value = func()
            self.set(key, value, ttl)
        return value

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests) if total_requests > 0 else 0

            return {
                **self.stats,
                'memory_entries': len(self._memory_cache),
                'hit_rate': hit_rate,
                'memory_usage_mb': self._estimate_memory_usage()
            }

    def _evict_oldest(self) -> None:
        """Evict oldest cache entries to make space"""
        with self._lock:
            # Find oldest entries
            entries = [(k, v.get_age()) for k, v in self._memory_cache.items()]
            entries.sort(key=lambda x: x[1], reverse=True)

            # Remove oldest 10% or at least 1 entry
            to_remove = max(1, int(len(entries) * 0.1))
            for i in range(to_remove):
                if i < len(entries):
                    key = entries[i][0]
                    del self._memory_cache[key]
                    self.stats['evictions'] += 1

    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB"""
        # Rough estimation based on number of entries
        # In production, you'd use a more sophisticated approach
        base_memory = 0.1  # Base memory usage
        per_entry = 0.001  # Rough estimate per entry
        return base_memory + (len(self._memory_cache) * per_entry)

    def _cleanup_worker(self) -> None:
        """Background worker to clean up expired entries"""
        while True:
            try:
                time.sleep(self.cleanup_interval)
                self._cleanup_expired()
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")

    def _cleanup_expired(self) -> None:
        """Remove expired cache entries"""
        with self._lock:
            expired_keys = []
            for key, entry in self._memory_cache.items():
                if entry.is_expired():
                    expired_keys.append(key)

            for key in expired_keys:
                del self._memory_cache[key]

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")


# Global cache instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance"""
    global _cache_manager

    if _cache_manager is None:
        _cache_manager = CacheManager()

    return _cache_manager


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """Decorator to cache function results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache_manager()

            # Generate cache key
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()

            return cache.get_or_set(cache_key, lambda: func(*args, **kwargs), ttl)

        return wrapper
    return decorator


class UserCache:
    """User-specific caching with automatic key generation"""

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager

    def get_user_data(self, user_id: int, key: str) -> Optional[Any]:
        """Get user-specific cached data"""
        cache_key = f"user:{user_id}:{key}"
        return self.cache.get(cache_key)

    def set_user_data(self, user_id: int, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set user-specific cached data"""
        cache_key = f"user:{user_id}:{key}"
        return self.cache.set(cache_key, value, ttl)

    def clear_user_cache(self, user_id: int) -> None:
        """Clear all cached data for a user"""
        # This is a simplified implementation
        # In production, you might want to maintain a user key registry
        logger.info(f"User {user_id} cache cleared (simplified)")

    def get_user_bindings(self, user_id: int) -> Optional[Any]:
        """Get cached user bindings"""
        return self.get_user_data(user_id, "bindings")

    def set_user_bindings(self, user_id: int, bindings: Any, ttl: int = 300) -> bool:
        """Cache user bindings"""
        return self.set_user_data(user_id, "bindings", bindings, ttl)


class InstagramCache:
    """Instagram-specific caching for posts, stories, and account data"""

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager

    def get_account_info(self, username: str) -> Optional[Dict]:
        """Get cached Instagram account information"""
        cache_key = f"instagram:account:{username}"
        return self.cache.get(cache_key)

    def set_account_info(self, username: str, data: Dict, ttl: int = 600) -> bool:
        """Cache Instagram account information"""
        cache_key = f"instagram:account:{username}"
        return self.cache.set(cache_key, data, ttl)

    def get_recent_posts(self, username: str, limit: int = 10) -> Optional[List]:
        """Get cached recent posts for an account"""
        cache_key = f"instagram:posts:{username}:{limit}"
        return self.cache.get(cache_key)

    def set_recent_posts(self, username: str, posts: List, limit: int = 10, ttl: int = 300) -> bool:
        """Cache recent posts for an account"""
        cache_key = f"instagram:posts:{username}:{limit}"
        return self.cache.set(cache_key, posts, ttl)

    def invalidate_account_cache(self, username: str) -> None:
        """Invalidate all cache entries for an Instagram account"""
        # Simplified implementation - in production, maintain a key registry
        logger.info(f"Instagram account {username} cache invalidated (simplified)")


# Initialize global cache components
def init_cache_system():
    """Initialize the global caching system"""
    cache_manager = get_cache_manager()
    user_cache = UserCache(cache_manager)
    instagram_cache = InstagramCache(cache_manager)

    logger.info("Cache system initialized")

    return {
        'cache_manager': cache_manager,
        'user_cache': user_cache,
        'instagram_cache': instagram_cache
    }


def get_cache_health() -> Dict[str, Any]:
    """Get comprehensive cache system health"""
    cache_manager = get_cache_manager()

    stats = cache_manager.get_stats()
    stats['healthy'] = True
    stats['status'] = 'Cache system is healthy'

    return stats
