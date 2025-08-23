"""
Comprehensive Monitoring System for MediaFetch
Provides centralized monitoring, alerting, and health checks
"""

import time
import psutil
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import threading
import json

# Import our custom modules
from cache_manager import get_cache_health
from circuit_breaker import get_circuit_breaker_health
from webhook_manager import alert_critical_error, alert_system_health
from connection_pool import get_db_pool

logger = logging.getLogger(__name__)


class SystemMonitor:
    """Comprehensive system monitoring and alerting"""

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.last_check = 0
        self.health_status = {}
        self.alert_thresholds = {
            'memory_usage_percent': 85.0,
            'disk_usage_percent': 90.0,
            'cpu_usage_percent': 80.0,
            'response_time_seconds': 5.0,
            'error_rate_percent': 5.0
        }

        self.monitoring_enabled = True
        self._lock = threading.RLock()

        # Start monitoring thread
        self._monitor_thread = threading.Thread(target=self._monitoring_worker, daemon=True)
        self._monitor_thread.start()

        logger.info("System monitor initialized")

    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        try:
            health_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'overall_healthy': True,
                'services': {},
                'metrics': {},
                'alerts': []
            }

            # System resource health
            system_health = self._check_system_resources()
            health_data['services']['system_resources'] = system_health

            # Database health
            db_health = self._check_database_health()
            health_data['services']['database'] = db_health

            # Cache health
            cache_health = get_cache_health()
            health_data['services']['cache'] = cache_health

            # Circuit breaker health
            circuit_health = get_circuit_breaker_health()
            health_data['services']['circuit_breakers'] = circuit_health

            # Determine overall health
            all_services_healthy = all(
                service.get('healthy', True)
                for service in health_data['services'].values()
            )
            health_data['overall_healthy'] = all_services_healthy

            # Generate alerts for unhealthy services
            if not all_services_healthy:
                health_data['alerts'] = self._generate_alerts(health_data['services'])

                # Send critical alerts
                for alert in health_data['alerts']:
                    if alert['severity'] == 'critical':
                        alert_critical_error(alert['message'], alert)

            return health_data

        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'overall_healthy': False,
                'error': str(e),
                'services': {},
                'metrics': {},
                'alerts': [{
                    'severity': 'critical',
                    'message': f'System health check failed: {e}',
                    'service': 'system_monitor'
                }]
            }

    def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent

            # Network I/O
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_recv = network.bytes_recv

            # System load (Unix-like systems)
            load_avg = []
            try:
                load_avg = psutil.getloadavg()
            except AttributeError:
                # Windows doesn't have getloadavg
                load_avg = [0, 0, 0]

            healthy = (
                cpu_percent < self.alert_thresholds['cpu_usage_percent'] and
                memory_percent < self.alert_thresholds['memory_usage_percent'] and
                disk_percent < self.alert_thresholds['disk_usage_percent']
            )

            status = 'healthy' if healthy else 'unhealthy'

            return {
                'healthy': healthy,
                'status': status,
                'metrics': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'memory_used_gb': memory.used / (1024**3),
                    'memory_total_gb': memory.total / (1024**3),
                    'disk_percent': disk_percent,
                    'disk_free_gb': disk.free / (1024**3),
                    'disk_total_gb': disk.total / (1024**3),
                    'network_bytes_sent': network_bytes_sent,
                    'network_bytes_recv': network_bytes_recv,
                    'load_average': load_avg
                }
            }

        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {
                'healthy': False,
                'status': f'Error: {e}',
                'metrics': {}
            }

    def _check_database_health(self) -> Dict[str, Any]:
        """Check database connection and performance"""
        try:
            db_pool = get_db_pool()
            pool_stats = db_pool.get_pool_stats()

            # Basic connectivity test
            test_result = db_pool.execute_query("SELECT 1 as test")
            connectivity_healthy = test_result is not None and len(test_result) > 0

            if connectivity_healthy:
                # Check query performance
                avg_query_time = 0
                if pool_stats.get('query_performance'):
                    query_times = [stats['avg_time'] for stats in pool_stats['query_performance'].values()]
                    avg_query_time = sum(query_times) / len(query_times) if query_times else 0

                healthy = avg_query_time < self.alert_thresholds['response_time_seconds']
                status = 'healthy' if healthy else 'slow_queries'

                return {
                    'healthy': healthy,
                    'status': status,
                    'metrics': {
                        **pool_stats,
                        'avg_query_time': avg_query_time
                    }
                }
            else:
                return {
                    'healthy': False,
                    'status': 'connection_failed',
                    'metrics': pool_stats
                }

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'healthy': False,
                'status': f'Error: {e}',
                'metrics': {}
            }

    def _generate_alerts(self, services: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """Generate alerts for unhealthy services"""
        alerts = []

        for service_name, service_data in services.items():
            if not service_data.get('healthy', True):
                alerts.append({
                    'severity': 'warning' if service_name != 'system_resources' else 'critical',
                    'service': service_name,
                    'message': f'Service {service_name} is unhealthy: {service_data.get("status", "Unknown status")}',
                    'details': service_data.get('metrics', {})
                })

        return alerts

    def _monitoring_worker(self):
        """Background monitoring worker"""
        while self.monitoring_enabled:
            try:
                current_time = time.time()
                if current_time - self.last_check >= self.check_interval:
                    self.last_check = current_time

                    # Perform health check
                    health_data = self.get_system_health()

                    # Store health status
                    with self._lock:
                        self.health_status = health_data

                    # Send periodic health report
                    alert_system_health(health_data)

                    logger.debug("System health check completed")

            except Exception as e:
                logger.error(f"Monitoring worker error: {e}")

            time.sleep(10)  # Check every 10 seconds

    def get_current_health(self) -> Dict[str, Any]:
        """Get current health status"""
        with self._lock:
            return self.health_status.copy()

    def update_threshold(self, metric: str, value: float):
        """Update alert threshold for a metric"""
        if metric in self.alert_thresholds:
            self.alert_thresholds[metric] = value
            logger.info(f"Alert threshold updated: {metric} = {value}")

    def enable_monitoring(self):
        """Enable monitoring"""
        self.monitoring_enabled = True
        logger.info("System monitoring enabled")

    def disable_monitoring(self):
        """Disable monitoring"""
        self.monitoring_enabled = False
        logger.info("System monitoring disabled")


class PerformanceMonitor:
    """Performance monitoring and profiling"""

    def __init__(self):
        self.performance_data: Dict[str, List[float]] = {}
        self.function_calls: Dict[str, int] = {}
        self._lock = threading.RLock()

    def profile_function(self, func_name: str):
        """Decorator to profile function performance"""
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.time()
                    execution_time = end_time - start_time

                    with self._lock:
                        if func_name not in self.performance_data:
                            self.performance_data[func_name] = []
                        self.performance_data[func_name].append(execution_time)

                        if func_name not in self.function_calls:
                            self.function_calls[func_name] = 0
                        self.function_calls[func_name] += 1

            return wrapper
        return decorator

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        with self._lock:
            stats = {}

            for func_name, times in self.performance_data.items():
                if times:
                    stats[func_name] = {
                        'calls': self.function_calls.get(func_name, 0),
                        'avg_time': sum(times) / len(times),
                        'max_time': max(times),
                        'min_time': min(times),
                        'total_time': sum(times),
                        'recent_calls': len(times)
                    }

            return stats

    def clear_stats(self):
        """Clear performance statistics"""
        with self._lock:
            self.performance_data.clear()
            self.function_calls.clear()
            logger.info("Performance statistics cleared")


class ErrorTracker:
    """Error tracking and analysis"""

    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.error_details: Dict[str, List[Dict[str, Any]]] = {}
        self.error_timestamps: Dict[str, List[float]] = {}
        self._lock = threading.RLock()

    def track_error(self, error_type: str, error_message: str, details: Dict[str, Any] = None):
        """Track an error occurrence"""
        with self._lock:
            current_time = time.time()

            # Update error count
            if error_type not in self.error_counts:
                self.error_counts[error_type] = 0
            self.error_counts[error_type] += 1

            # Store error details
            if error_type not in self.error_details:
                self.error_details[error_type] = []
            self.error_details[error_type].append({
                'message': error_message,
                'details': details or {},
                'timestamp': current_time
            })

            # Keep only last 100 errors per type
            if len(self.error_details[error_type]) > 100:
                self.error_details[error_type] = self.error_details[error_type][-100:]

            # Store timestamp for rate calculation
            if error_type not in self.error_timestamps:
                self.error_timestamps[error_type] = []
            self.error_timestamps[error_type].append(current_time)

            # Keep only timestamps from last hour
            one_hour_ago = current_time - 3600
            self.error_timestamps[error_type] = [
                t for t in self.error_timestamps[error_type] if t > one_hour_ago
            ]

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        with self._lock:
            current_time = time.time()
            one_hour_ago = current_time - 3600

            stats = {}

            for error_type in self.error_counts:
                timestamps = self.error_timestamps.get(error_type, [])
                recent_timestamps = [t for t in timestamps if t > one_hour_ago]

                error_rate = len(recent_timestamps) / 3600  # errors per second over last hour

                stats[error_type] = {
                    'total_count': self.error_counts[error_type],
                    'hourly_rate': error_rate,
                    'recent_errors': len(recent_timestamps),
                    'last_error': max(timestamps) if timestamps else None,
                    'error_details': self.error_details[error_type][-5:]  # Last 5 errors
                }

            return stats

    def clear_error_stats(self):
        """Clear error statistics"""
        with self._lock:
            self.error_counts.clear()
            self.error_details.clear()
            self.error_timestamps.clear()
            logger.info("Error statistics cleared")


# Global monitoring instances
_system_monitor: Optional[SystemMonitor] = None
_performance_monitor: Optional[PerformanceMonitor] = None
_error_tracker: Optional[ErrorTracker] = None


def get_system_monitor() -> SystemMonitor:
    """Get the global system monitor instance"""
    global _system_monitor

    if _system_monitor is None:
        _system_monitor = SystemMonitor()

    return _system_monitor


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    global _performance_monitor

    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()

    return _performance_monitor


def get_error_tracker() -> ErrorTracker:
    """Get the global error tracker instance"""
    global _error_tracker

    if _error_tracker is None:
        _error_tracker = ErrorTracker()

    return _error_tracker


def init_monitoring_system():
    """Initialize the complete monitoring system"""
    system_monitor = get_system_monitor()
    performance_monitor = get_performance_monitor()
    error_tracker = get_error_tracker()

    logger.info("Complete monitoring system initialized")

    return {
        'system_monitor': system_monitor,
        'performance_monitor': performance_monitor,
        'error_tracker': error_tracker
    }


def get_comprehensive_health() -> Dict[str, Any]:
    """Get comprehensive system health from all monitoring components"""
    try:
        system_health = get_system_monitor().get_current_health()
        performance_stats = get_performance_monitor().get_performance_stats()
        error_stats = get_error_tracker().get_error_stats()

        comprehensive_health = {
            'timestamp': datetime.utcnow().isoformat(),
            'system_health': system_health,
            'performance_stats': performance_stats,
            'error_stats': error_stats,
            'overall_status': 'healthy'
        }

        # Determine overall status
        issues = []

        if not system_health.get('overall_healthy', True):
            issues.append('System health issues detected')

        if error_stats and any(
            stat.get('hourly_rate', 0) > 0.001 for stat in error_stats.values()
        ):
            issues.append('High error rate detected')

        if issues:
            comprehensive_health['overall_status'] = 'warning' if len(issues) == 1 else 'critical'
            comprehensive_health['issues'] = issues

        return comprehensive_health

    except Exception as e:
        logger.error(f"Comprehensive health check failed: {e}")
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'error',
            'error': str(e)
        }
