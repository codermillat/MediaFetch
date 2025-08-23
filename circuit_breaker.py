"""
Circuit Breaker Implementation for MediaFetch
Provides fault tolerance and automatic recovery for external service calls
"""

import time
import threading
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Circuit is open, failing fast
    HALF_OPEN = "half_open" # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker implementation with configurable thresholds and timeouts"""

    def __init__(self,
                 name: str,
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: Exception = Exception,
                 success_threshold: int = 3):
        """
        Initialize circuit breaker

        Args:
            name: Name identifier for this circuit breaker
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch and count as failure
            success_threshold: Number of successes needed to close circuit from half-open
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._lock = threading.RLock()

        # Statistics
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'rejected_calls': 0,
            'state_changes': 0
        }

        logger.info(f"Circuit breaker '{name}' initialized")

    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        with self._lock:
            self.stats['total_calls'] += 1

            # Check if circuit is open
            if self._state == CircuitState.OPEN:
                if not self._should_attempt_reset():
                    self.stats['rejected_calls'] += 1
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker '{self.name}' is OPEN"
                    )
                else:
                    self._set_state(CircuitState.HALF_OPEN)
                    logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")

            # Execute the function
            try:
                result = func(*args, **kwargs)

                # Success - reset failure count
                self._on_success()
                self.stats['successful_calls'] += 1

                return result

            except self.expected_exception as e:
                # Expected failure - count it
                self._on_failure()
                self.stats['failed_calls'] += 1
                raise
            except Exception as e:
                # Unexpected exception - re-raise without counting
                logger.error(f"Unexpected exception in circuit breaker '{self.name}': {e}")
                raise

    def _on_success(self):
        """Handle successful call"""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1

            if self._success_count >= self.success_threshold:
                self._set_state(CircuitState.CLOSED)
                self._failure_count = 0
                self._success_count = 0
                logger.info(f"Circuit breaker '{self.name}' CLOSED after successful recovery")

        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success in closed state
            if self._failure_count > 0:
                self._failure_count = 0
                logger.debug(f"Circuit breaker '{self.name}' failure count reset")

    def _on_failure(self):
        """Handle failed call"""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open state sends us back to open
            self._set_state(CircuitState.OPEN)
            self._success_count = 0
            logger.warning(f"Circuit breaker '{self.name}' returned to OPEN state")

        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._set_state(CircuitState.OPEN)
                logger.warning(f"Circuit breaker '{self.name}' OPENED due to failure threshold")

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit"""
        if self._last_failure_time is None:
            return False

        return time.time() - self._last_failure_time >= self.recovery_timeout

    def _set_state(self, new_state: CircuitState):
        """Set new circuit state"""
        if self._state != new_state:
            self._state = new_state
            self.stats['state_changes'] += 1
            logger.info(f"Circuit breaker '{self.name}' state changed to {new_state.value}")

    def reset(self):
        """Manually reset the circuit breaker"""
        with self._lock:
            self._set_state(CircuitState.CLOSED)
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            logger.info(f"Circuit breaker '{self.name}' manually reset")

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        with self._lock:
            total_calls = self.stats['total_calls']
            successful_calls = self.stats['successful_calls']
            failed_calls = self.stats['failed_calls']
            rejected_calls = self.stats['rejected_calls']

            success_rate = (successful_calls / total_calls) if total_calls > 0 else 0
            failure_rate = (failed_calls / total_calls) if total_calls > 0 else 0

            return {
                'name': self.name,
                'state': self.state.value,
                'failure_count': self._failure_count,
                'success_count': self._success_count,
                'failure_threshold': self.failure_threshold,
                'success_threshold': self.success_threshold,
                'recovery_timeout': self.recovery_timeout,
                'last_failure_time': self._last_failure_time,
                'stats': {
                    **self.stats,
                    'success_rate': success_rate,
                    'failure_rate': failure_rate
                }
            }


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers"""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()

    def get_breaker(self,
                   name: str,
                   failure_threshold: int = 5,
                   recovery_timeout: int = 60,
                   expected_exception: Exception = Exception,
                   success_threshold: int = 3) -> CircuitBreaker:
        """Get or create a circuit breaker"""
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    expected_exception=expected_exception,
                    success_threshold=success_threshold
                )

            return self._breakers[name]

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        with self._lock:
            return {name: breaker.get_stats() for name, breaker in self._breakers.items()}

    def reset_all(self):
        """Reset all circuit breakers"""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
            logger.info("All circuit breakers reset")

    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall health status of all circuit breakers"""
        stats = self.get_all_stats()

        total_break = len(stats)
        open_breakers = sum(1 for stat in stats.values() if stat['state'] == 'open')
        half_open_breakers = sum(1 for stat in stats.values() if stat['state'] == 'half_open')

        healthy = open_breakers == 0  # Consider healthy if no breakers are open

        return {
            'healthy': healthy,
            'total_breakers': total_break,
            'open_breakers': open_breakers,
            'half_open_breakers': half_open_breakers,
            'breakers': stats
        }


# Global circuit breaker registry
_breaker_registry: Optional[CircuitBreakerRegistry] = None


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get a circuit breaker from the global registry"""
    global _breaker_registry

    if _breaker_registry is None:
        _breaker_registry = CircuitBreakerRegistry()

    return _breaker_registry.get_breaker(name, **kwargs)


def circuit_breaker(name: str, **kwargs):
    """Decorator to apply circuit breaker to a function"""
    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker(name, **kwargs)

        def wrapper(*args, **kwargs_inner):
            return breaker.call(func, *args, **kwargs_inner)

        return wrapper
    return decorator


def get_circuit_breaker_health() -> Dict[str, Any]:
    """Get overall circuit breaker system health"""
    global _breaker_registry

    if _breaker_registry is None:
        return {'healthy': True, 'message': 'No circuit breakers registered'}

    return _breaker_registry.get_overall_health()


# Pre-configured circuit breakers for common services
def get_supabase_breaker() -> CircuitBreaker:
    """Get circuit breaker for Supabase API calls"""
    return get_circuit_breaker(
        'supabase',
        failure_threshold=3,
        recovery_timeout=30,
        success_threshold=2
    )


def get_instagram_breaker() -> CircuitBreaker:
    """Get circuit breaker for Instagram API calls"""
    return get_circuit_breaker(
        'instagram',
        failure_threshold=5,
        recovery_timeout=60,
        success_threshold=3
    )


def get_telegram_breaker() -> CircuitBreaker:
    """Get circuit breaker for Telegram API calls"""
    return get_circuit_breaker(
        'telegram',
        failure_threshold=3,
        recovery_timeout=10,
        success_threshold=2
    )
