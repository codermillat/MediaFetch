#!/usr/bin/env python3
"""
Metrics collection module for MediaFetch bot
Provides comprehensive monitoring and metrics for production deployment
"""

import time
import logging
from typing import Dict, Any, Optional
from collections import defaultdict, Counter
from datetime import datetime, timedelta

from prometheus_client import (
    Counter, Histogram, Gauge, Summary, generate_latest,
    CONTENT_TYPE_LATEST
)

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects and manages metrics for the MediaFetch bot"""
    
    def __init__(self):
        """Initialize metrics collector with Prometheus metrics"""
        # Command usage metrics
        self.command_usage = Counter(
            'mediafetch_commands_total',
            'Total command usage',
            ['command_name']
        )
        
        # Download metrics
        self.downloads_total = Counter(
            'mediafetch_downloads_total',
            'Total download attempts'
        )
        
        self.downloads_successful = Counter(
            'mediafetch_downloads_successful_total',
            'Total successful downloads'
        )
        
        self.downloads_failed = Counter(
            'mediafetch_downloads_failed_total',
            'Total failed downloads'
        )
        
        self.download_duration = Histogram(
            'mediafetch_download_duration_seconds',
            'Download duration in seconds',
            buckets=[1, 5, 10, 30, 60, 120, 300, 600]
        )
        
        self.download_size = Histogram(
            'mediafetch_download_size_bytes',
            'Downloaded file size in bytes',
            buckets=[1024, 10240, 102400, 1048576, 10485760, 52428800]
        )
        
        # User metrics
        self.active_users = Gauge(
            'mediafetch_active_users',
            'Number of active users'
        )
        
        self.user_downloads = Counter(
            'mediafetch_user_downloads_total',
            'Total downloads per user',
            ['user_id']
        )
        
        # Error metrics
        self.errors_total = Counter(
            'mediafetch_errors_total',
            'Total errors',
            ['error_type']
        )
        
        # Platform metrics
        self.platform_downloads = Counter(
            'mediafetch_platform_downloads_total',
            'Total downloads per platform',
            ['platform']
        )
        
        # Processing metrics
        self.processing_duration = Histogram(
            'mediafetch_processing_duration_seconds',
            'Media processing duration in seconds',
            buckets=[1, 5, 10, 30, 60, 120, 300]
        )
        
        self.processing_success = Counter(
            'mediafetch_processing_success_total',
            'Total successful media processing operations'
        )
        
        self.processing_failures = Counter(
            'mediafetch_processing_failures_total',
            'Total failed media processing operations'
        )
        
        # System metrics
        self.bot_uptime = Gauge(
            'mediafetch_bot_uptime_seconds',
            'Bot uptime in seconds'
        )
        
        self.memory_usage = Gauge(
            'mediafetch_memory_usage_bytes',
            'Memory usage in bytes'
        )
        
        self.disk_usage = Gauge(
            'mediafetch_disk_usage_bytes',
            'Disk usage in bytes'
        )
        
        # Initialize internal tracking
        self.start_time = time.time()
        self.user_sessions = defaultdict(dict)
        self.download_history = []
        self.error_history = []
        self.platform_stats = Counter()
        
        logger.info("Metrics collector initialized")
    
    def increment_command_usage(self, command_name: str):
        """Increment command usage counter"""
        try:
            self.command_usage.labels(command_name=command_name).inc()
            logger.debug(f"Command usage incremented: {command_name}")
        except Exception as e:
            logger.error(f"Failed to increment command usage: {e}")
    
    def increment_downloads_total(self):
        """Increment total downloads counter"""
        try:
            self.downloads_total.inc()
        except Exception as e:
            logger.error(f"Failed to increment downloads total: {e}")
    
    def increment_successful_downloads(self):
        """Increment successful downloads counter"""
        try:
            self.downloads_successful.inc()
        except Exception as e:
            logger.error(f"Failed to increment successful downloads: {e}")
    
    def increment_failed_downloads(self):
        """Increment failed downloads counter"""
        try:
            self.downloads_failed.inc()
        except Exception as e:
            logger.error(f"Failed to increment failed downloads: {e}")
    
    def record_download_duration(self, duration_seconds: float):
        """Record download duration"""
        try:
            self.download_duration.observe(duration_seconds)
        except Exception as e:
            logger.error(f"Failed to record download duration: {e}")
    
    def record_download_size(self, size_bytes: int):
        """Record download file size"""
        try:
            self.download_size.observe(size_bytes)
        except Exception as e:
            logger.error(f"Failed to record download size: {e}")
    
    def set_active_users(self, count: int):
        """Set active users gauge"""
        try:
            self.active_users.set(count)
        except Exception as e:
            logger.error(f"Failed to set active users: {e}")
    
    def increment_user_downloads(self, user_id: int):
        """Increment user downloads counter"""
        try:
            self.user_downloads.labels(user_id=str(user_id)).inc()
        except Exception as e:
            logger.error(f"Failed to increment user downloads: {e}")
    
    def increment_errors(self, error_type: str = "general"):
        """Increment error counter"""
        try:
            self.errors_total.labels(error_type=error_type).inc()
            
            # Track error in history
            self.error_history.append({
                'timestamp': datetime.now(),
                'type': error_type
            })
            
            # Keep only last 100 errors
            if len(self.error_history) > 100:
                self.error_history = self.error_history[-100:]
                
        except Exception as e:
            logger.error(f"Failed to increment errors: {e}")
    
    def record_platform_download(self, platform: str):
        """Record download from specific platform"""
        try:
            self.platform_downloads.labels(platform=platform).inc()
            self.platform_stats[platform] += 1
        except Exception as e:
            logger.error(f"Failed to record platform download: {e}")
    
    def record_processing_duration(self, duration_seconds: float):
        """Record media processing duration"""
        try:
            self.processing_duration.observe(duration_seconds)
        except Exception as e:
            logger.error(f"Failed to record processing duration: {e}")
    
    def increment_processing_success(self):
        """Increment successful processing counter"""
        try:
            self.processing_success.inc()
        except Exception as e:
            logger.error(f"Failed to increment processing success: {e}")
    
    def increment_processing_failures(self):
        """Increment processing failures counter"""
        try:
            self.processing_failures.inc()
        except Exception as e:
            logger.error(f"Failed to increment processing failures: {e}")
    
    def update_system_metrics(self):
        """Update system-level metrics"""
        try:
            # Update uptime
            uptime = time.time() - self.start_time
            self.bot_uptime.set(uptime)
            
            # Update memory usage (if psutil available)
            try:
                import psutil
                memory_info = psutil.virtual_memory()
                self.memory_usage.set(memory_info.used)
            except ImportError:
                pass
            
            # Update disk usage
            try:
                import psutil
                disk_info = psutil.disk_usage('/')
                self.disk_usage.set(disk_info.used)
            except ImportError:
                pass
                
        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")
    
    def record_download(self, user_id: int, platform: str, duration: float, 
                       size: int, success: bool):
        """Record comprehensive download information"""
        try:
            # Record basic metrics
            self.increment_downloads_total()
            if success:
                self.increment_successful_downloads()
            else:
                self.increment_failed_downloads()
            
            # Record detailed metrics
            self.record_download_duration(duration)
            self.record_download_size(size)
            self.increment_user_downloads(user_id)
            self.record_platform_download(platform)
            
            # Track in history
            self.download_history.append({
                'timestamp': datetime.now(),
                'user_id': user_id,
                'platform': platform,
                'duration': duration,
                'size': size,
                'success': success
            })
            
            # Keep only last 1000 downloads
            if len(self.download_history) > 1000:
                self.download_history = self.download_history[-1000:]
                
        except Exception as e:
            logger.error(f"Failed to record download: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        try:
            # Calculate rates
            now = datetime.now()
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)
            
            recent_downloads = [
                d for d in self.download_history 
                if d['timestamp'] > hour_ago
            ]
            
            daily_downloads = [
                d for d in self.download_history 
                if d['timestamp'] > day_ago
            ]
            
            # Calculate success rate
            total_downloads = len(self.download_history)
            successful_downloads = len([d for d in self.download_history if d['success']])
            success_rate = (successful_downloads / total_downloads * 100) if total_downloads > 0 else 0
            
            # Platform breakdown
            platform_breakdown = dict(self.platform_stats)
            
            # Error breakdown
            error_breakdown = Counter([e['type'] for e in self.error_history])
            
            return {
                'total_downloads': total_downloads,
                'successful_downloads': successful_downloads,
                'failed_downloads': total_downloads - successful_downloads,
                'success_rate_percent': round(success_rate, 2),
                'downloads_last_hour': len(recent_downloads),
                'downloads_last_24h': len(daily_downloads),
                'platform_breakdown': platform_breakdown,
                'error_breakdown': dict(error_breakdown),
                'uptime_seconds': time.time() - self.start_time,
                'active_users': len(self.user_sessions),
                'total_errors': len(self.error_history)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate metrics summary: {e}")
            return {'error': str(e)}
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus-formatted metrics"""
        try:
            # Update system metrics before generating
            self.update_system_metrics()
            
            # Generate Prometheus metrics
            return generate_latest()
            
        except Exception as e:
            logger.error(f"Failed to generate Prometheus metrics: {e}")
            return f"# Error generating metrics: {e}"
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)"""
        try:
            # Reset internal tracking
            self.start_time = time.time()
            self.user_sessions.clear()
            self.download_history.clear()
            self.error_history.clear()
            self.platform_stats.clear()
            
            logger.info("Metrics reset successfully")
            
        except Exception as e:
            logger.error(f"Failed to reset metrics: {e}")
    
    def export_metrics(self, format_type: str = 'json') -> str:
        """Export metrics in various formats"""
        try:
            if format_type == 'json':
                import json
                return json.dumps(self.get_summary(), indent=2, default=str)
            elif format_type == 'prometheus':
                return self.get_prometheus_metrics()
            else:
                raise ValueError(f"Unsupported format: {format_type}")
                
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return f"Error exporting metrics: {e}"
