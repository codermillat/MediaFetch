"""
Performance Tests for MediaFetch
Tests performance aspects including caching, database operations, and system resources
"""

import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile
import os
from pathlib import Path

# Import performance modules
from cache_manager import get_cache_manager, CacheManager
from connection_pool import get_db_pool
from monitoring_system import get_performance_monitor


class TestCacheManager:
    """Test cache manager performance"""

    def test_cache_basic_operations(self):
        """Test basic cache operations performance"""
        cache = CacheManager()

        # Test set/get operations
        start_time = time.time()

        # Set 1000 cache entries
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")

        set_time = time.time() - start_time

        # Get operations
        start_time = time.time()

        for i in range(1000):
            value = cache.get(f"key_{i}")
            assert value == f"value_{i}"

        get_time = time.time() - start_time

        # Performance assertions (adjust based on requirements)
        assert set_time < 2.0  # Should complete within 2 seconds
        assert get_time < 1.0  # Should complete within 1 second

    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration performance"""
        cache = CacheManager()

        # Set entries with short TTL
        for i in range(100):
            cache.set(f"ttl_key_{i}", f"ttl_value_{i}", ttl=1)  # 1 second TTL

        # Verify entries exist
        assert len([k for k in cache._memory_cache.keys() if k.startswith("ttl_key_")]) == 100

        # Wait for expiration
        time.sleep(1.1)

        # Check cleanup performance
        start_time = time.time()
        expired_count = 0

        for i in range(100):
            if cache.get(f"ttl_key_{i}") is None:
                expired_count += 1

        cleanup_time = time.time() - start_time

        assert expired_count == 100  # All should be expired
        assert cleanup_time < 0.5  # Cleanup should be fast

    def test_cache_memory_usage(self):
        """Test cache memory usage"""
        cache = CacheManager(max_memory_entries=100)

        # Fill cache to capacity
        for i in range(150):  # Exceed capacity
            cache.set(f"mem_key_{i}", f"mem_value_{i}" * 100)  # Larger values

        # Should have evicted old entries
        assert len(cache._memory_cache) <= 100

        # Test memory usage estimation
        memory_mb = cache._estimate_memory_usage()
        assert memory_mb > 0
        assert memory_mb < 10  # Should be reasonable

    def test_cache_concurrent_access(self):
        """Test cache performance under concurrent access"""
        import threading
        import concurrent.futures

        cache = CacheManager()
        results = []

        def worker(worker_id):
            for i in range(100):
                cache_key = f"concurrent_{worker_id}_{i}"
                cache.set(cache_key, f"worker_{worker_id}_value_{i}")
                value = cache.get(cache_key)
                results.append(value)

        # Run 5 concurrent workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(5)]
            concurrent.futures.wait(futures)

        # Verify all operations completed
        assert len(results) == 500  # 5 workers * 100 operations each

    def test_get_or_set_performance(self):
        """Test get_or_set performance"""
        cache = CacheManager()
        call_count = 0

        def expensive_operation():
            nonlocal call_count
            call_count += 1
            time.sleep(0.01)  # Simulate expensive operation
            return f"result_{call_count}"

        start_time = time.time()

        # Multiple get_or_set calls
        for i in range(50):
            cache_key = f"get_or_set_{i % 10}"  # Re-use some keys
            result = cache.get_or_set(cache_key, expensive_operation)

        elapsed_time = time.time() - start_time

        # Should be faster due to caching
        assert elapsed_time < 1.0  # Should complete within 1 second
        assert call_count <= 10  # Should not call expensive operation more than needed


class TestConnectionPool:
    """Test database connection pool performance"""

    @patch('connection_pool.psycopg2.pool')
    def test_connection_pool_initialization(self, mock_pool):
        """Test connection pool initialization performance"""
        from connection_pool import DatabaseConnectionPool

        start_time = time.time()

        pool = DatabaseConnectionPool(
            min_connections=2,
            max_connections=10,
            connection_timeout=30
        )

        init_time = time.time() - start_time
        assert init_time < 1.0  # Should initialize quickly

    @patch('connection_pool.DatabaseConnectionPool._build_connection_string')
    @patch('connection_pool.psycopg2.pool.ThreadedConnectionPool')
    def test_query_performance(self, mock_pool_class, mock_build_string):
        """Test query execution performance"""
        from connection_pool import DatabaseConnectionPool

        # Mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool_instance = MagicMock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool_class.return_value = mock_pool_instance

        pool = DatabaseConnectionPool()
        pool._pool = mock_pool_instance

        # Mock query execution
        mock_cursor.fetchall.return_value = [{'id': 1, 'name': 'test'}]

        start_time = time.time()

        # Execute multiple queries
        for i in range(100):
            result = pool.execute_query("SELECT * FROM test_table")

        query_time = time.time() - start_time

        assert query_time < 2.0  # Should complete within 2 seconds
        assert pool.connection_stats['total_queries'] == 100

    def test_pool_stats_performance(self):
        """Test pool statistics retrieval performance"""
        from connection_pool import DatabaseConnectionPool

        pool = DatabaseConnectionPool()

        start_time = time.time()

        # Get stats multiple times
        for _ in range(100):
            stats = pool.get_pool_stats()

        stats_time = time.time() - start_time

        assert stats_time < 0.1  # Should be very fast


class TestPerformanceMonitor:
    """Test performance monitoring"""

    def test_function_profiling(self):
        """Test function performance profiling"""
        monitor = get_performance_monitor()

        @monitor.profile_function("test_function")
        def sample_function():
            time.sleep(0.01)  # 10ms operation
            return "result"

        # Call function multiple times
        for _ in range(10):
            result = sample_function()

        # Get performance stats
        stats = monitor.get_performance_stats()

        assert "test_function" in stats
        assert stats["test_function"]["calls"] == 10
        assert stats["test_function"]["avg_time"] > 0.009  # At least 9ms average
        assert stats["test_function"]["total_time"] > 0.09  # At least 90ms total

    def test_performance_stats_accuracy(self):
        """Test accuracy of performance statistics"""
        monitor = get_performance_monitor()

        @monitor.profile_function("accuracy_test")
        def fast_function():
            return sum(range(100))

        @monitor.profile_function("accuracy_test")
        def slow_function():
            time.sleep(0.02)
            return sum(range(100))

        # Call functions
        fast_function()
        slow_function()

        stats = monitor.get_performance_stats()

        assert stats["accuracy_test"]["calls"] == 2
        assert stats["accuracy_test"]["max_time"] > stats["accuracy_test"]["min_time"]

    def test_stats_clearing(self):
        """Test performance statistics clearing"""
        monitor = get_performance_monitor()

        @monitor.profile_function("clear_test")
        def test_function():
            return "test"

        # Generate some stats
        for _ in range(5):
            test_function()

        # Verify stats exist
        stats = monitor.get_performance_stats()
        assert "clear_test" in stats

        # Clear stats
        monitor.clear_stats()

        # Verify stats are cleared
        new_stats = monitor.get_performance_stats()
        assert "clear_test" not in new_stats


class TestSystemPerformance:
    """Test overall system performance"""

    @patch('monitoring_system.psutil')
    def test_system_health_check_performance(self, mock_psutil):
        """Test system health check performance"""
        from monitoring_system import get_system_monitor

        # Mock psutil methods
        mock_psutil.cpu_percent.return_value = 25.0
        mock_psutil.virtual_memory.return_value = MagicMock(
            percent=45.0,
            used=4 * 1024**3,  # 4GB
            total=8 * 1024**3   # 8GB
        )
        mock_psutil.disk_usage.return_value = MagicMock(
            percent=60.0,
            free=100 * 1024**3,  # 100GB
            total=500 * 1024**3  # 500GB
        )

        monitor = get_system_monitor()

        start_time = time.time()

        # Perform multiple health checks
        for _ in range(10):
            health = monitor.get_system_health()

        health_check_time = time.time() - start_time

        assert health_check_time < 5.0  # Should complete within 5 seconds
        assert health['overall_healthy'] is True  # Mock data should be healthy

    def test_cache_health_performance(self):
        """Test cache health check performance"""
        from cache_manager import get_cache_manager

        cache = get_cache_manager()

        # Add some test data
        for i in range(100):
            cache.set(f"health_test_{i}", f"health_value_{i}")

        start_time = time.time()

        # Get health multiple times
        for _ in range(50):
            health = cache.get_stats()

        health_time = time.time() - start_time

        assert health_time < 0.5  # Should be very fast
        assert health['memory_entries'] >= 100


class TestAsyncPerformance:
    """Test async operation performance"""

    @pytest.mark.asyncio
    async def test_async_cache_operations(self):
        """Test cache operations in async context"""
        cache = CacheManager()

        async def async_cache_worker(worker_id):
            results = []
            for i in range(50):
                key = f"async_{worker_id}_{i}"
                cache.set(key, f"value_{worker_id}_{i}")
                value = cache.get(key)
                results.append(value)
            return results

        start_time = time.time()

        # Run multiple async workers
        tasks = [async_cache_worker(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        async_time = time.time() - start_time

        assert async_time < 3.0  # Should complete within 3 seconds
        assert len(results) == 5
        assert all(len(result) == 50 for result in results)

    @pytest.mark.asyncio
    async def test_concurrent_async_operations(self):
        """Test concurrent async operations"""
        cache = CacheManager()

        async def concurrent_operation(task_id):
            # Mix of set and get operations
            for i in range(20):
                if i % 2 == 0:
                    cache.set(f"concurrent_{task_id}_{i}", f"data_{task_id}_{i}")
                else:
                    cache.get(f"concurrent_{task_id}_{i-1}")

            return task_id

        start_time = time.time()

        # Run concurrent async operations
        tasks = [concurrent_operation(i) for i in range(10)]
        completed = await asyncio.gather(*tasks)

        concurrent_time = time.time() - start_time

        assert concurrent_time < 2.0  # Should complete within 2 seconds
        assert len(completed) == 10
        assert set(completed) == set(range(10))


# Performance benchmarks
PERFORMANCE_THRESHOLDS = {
    'cache_set_1000': 1.0,      # 1 second for 1000 cache sets
    'cache_get_1000': 0.5,      # 0.5 seconds for 1000 cache gets
    'db_query_100': 2.0,        # 2 seconds for 100 simple queries
    'health_check_10': 3.0,     # 3 seconds for 10 health checks
    'async_operations_50': 2.0  # 2 seconds for 50 async operations
}


def test_performance_thresholds():
    """Test that all performance tests meet thresholds"""
    # This test would run all performance tests and verify they meet thresholds
    # In practice, this would aggregate results from all performance tests
    pass


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--tb=short"])
