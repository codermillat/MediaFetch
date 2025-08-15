#!/usr/bin/env python3
"""
Worker module for MediaFetch bot
Handles background tasks and media processing for Heroku deployment
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from .config import Config
from .utils import cleanup_old_files

logger = logging.getLogger(__name__)

class MediaWorker:
    """Background worker for media processing and cleanup tasks"""
    
    def __init__(self):
        """Initialize the worker"""
        self.config = Config()
        self.storage_config = self.config.get_storage_config()
        self.monitoring_config = self.config.get_monitoring_config()
        
        # Worker state
        self.is_running = False
        self.tasks = {}
        self.last_cleanup = time.time()
        
        logger.info("MediaWorker initialized")
    
    async def start(self):
        """Start the worker"""
        if self.is_running:
            logger.warning("Worker is already running")
            return
        
        self.is_running = True
        logger.info("MediaWorker started")
        
        # Start background tasks
        asyncio.create_task(self._cleanup_task())
        asyncio.create_task(self._health_check_task())
        asyncio.create_task(self._metrics_update_task())
    
    async def stop(self):
        """Stop the worker"""
        if not self.is_running:
            logger.warning("Worker is not running")
            return
        
        self.is_running = False
        logger.info("MediaWorker stopped")
        
        # Cancel all running tasks
        for task_name, task in self.tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.tasks.clear()
    
    async def _cleanup_task(self):
        """Background task for cleaning up old files"""
        while self.is_running:
            try:
                current_time = time.time()
                cleanup_interval = self.storage_config['cleanup_interval']
                
                if current_time - self.last_cleanup >= cleanup_interval:
                    await self._perform_cleanup()
                    self.last_cleanup = current_time
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _health_check_task(self):
        """Background task for health checks"""
        while self.is_running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.monitoring_config['health_check_interval'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check task error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _metrics_update_task(self):
        """Background task for updating metrics"""
        while self.is_running:
            try:
                await self._update_metrics()
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics update task error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _perform_cleanup(self):
        """Perform file cleanup operations"""
        try:
            logger.info("Starting cleanup task")
            
            # Clean up old temporary files
            temp_dir = self.storage_config['temp_dir']
            cleanup_old_files(temp_dir, max_age_hours=1)  # Clean files older than 1 hour
            
            # Clean up processed files
            await self._cleanup_processed_files()
            
            # Clean up download cache
            await self._cleanup_download_cache()
            
            logger.info("Cleanup task completed")
            
        except Exception as e:
            logger.error(f"Cleanup task failed: {e}")
    
    async def _cleanup_processed_files(self):
        """Clean up processed media files"""
        try:
            import os
            from pathlib import Path
            
            temp_dir = Path(self.storage_config['temp_dir'])
            
            # Remove processed files
            for pattern in ['processed_*', 'telegram_optimized_*']:
                for file_path in temp_dir.glob(pattern):
                    if file_path.is_file():
                        try:
                            file_path.unlink()
                            logger.debug(f"Cleaned up processed file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to cleanup file {file_path}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup processed files: {e}")
    
    async def _cleanup_download_cache(self):
        """Clean up download cache files"""
        try:
            import os
            from pathlib import Path
            
            temp_dir = Path(self.storage_config['temp_dir'])
            
            # Remove old download files
            for file_path in temp_dir.glob("mediafetch_*"):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        logger.debug(f"Cleaned up download file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup file {file_path}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup download cache: {e}")
    
    async def _perform_health_check(self):
        """Perform system health check"""
        try:
            health_status = await self._check_system_health()
            
            if health_status['status'] == 'healthy':
                logger.debug("Health check passed")
            else:
                logger.warning(f"Health check failed: {health_status['issues']}")
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def _check_system_health(self) -> Dict[str, Any]:
        """Check system health status"""
        try:
            issues = []
            
            # Check disk space
            disk_status = await self._check_disk_space()
            if not disk_status['healthy']:
                issues.append(f"Disk space low: {disk_status['message']}")
            
            # Check memory usage
            memory_status = await self._check_memory_usage()
            if not memory_status['healthy']:
                issues.append(f"Memory usage high: {memory_status['message']}")
            
            # Check file count
            file_status = await self._check_file_count()
            if not file_status['healthy']:
                issues.append(f"Too many files: {file_status['message']}")
            
            return {
                'status': 'healthy' if not issues else 'unhealthy',
                'timestamp': datetime.now().isoformat(),
                'issues': issues,
                'disk': disk_status,
                'memory': memory_status,
                'files': file_status
            }
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {
                'status': 'error',
                'timestamp': datetime.now().isoformat(),
                'issues': [f"Health check error: {e}"],
                'disk': {'healthy': False, 'message': 'Check failed'},
                'memory': {'healthy': False, 'message': 'Check failed'},
                'files': {'healthy': False, 'message': 'Check failed'}
            }
    
    async def _check_disk_space(self) -> Dict[str, Any]:
        """Check disk space usage"""
        try:
            import os
            from pathlib import Path
            
            temp_dir = Path(self.storage_config['temp_dir'])
            
            if not temp_dir.exists():
                return {'healthy': True, 'message': 'Directory does not exist'}
            
            # Get disk usage
            stat = os.statvfs(temp_dir)
            total_space = stat.f_frsize * stat.f_blocks
            free_space = stat.f_frsize * stat.f_bavail
            used_space = total_space - free_space
            usage_percent = (used_space / total_space) * 100
            
            # Check if usage is acceptable (less than 80%)
            healthy = usage_percent < 80
            
            return {
                'healthy': healthy,
                'total_bytes': total_space,
                'free_bytes': free_space,
                'used_bytes': used_space,
                'usage_percent': round(usage_percent, 2),
                'message': f"{usage_percent:.1f}% used"
            }
            
        except Exception as e:
            logger.error(f"Disk space check failed: {e}")
            return {'healthy': False, 'message': f'Check failed: {e}'}
    
    async def _check_memory_usage(self) -> Dict[str, Any]:
        """Check memory usage"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            # Check if memory usage is acceptable (less than 90%)
            healthy = usage_percent < 90
            
            return {
                'healthy': healthy,
                'total_bytes': memory.total,
                'available_bytes': memory.available,
                'used_bytes': memory.used,
                'usage_percent': usage_percent,
                'message': f"{usage_percent:.1f}% used"
            }
            
        except ImportError:
            return {'healthy': True, 'message': 'psutil not available'}
        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return {'healthy': False, 'message': f'Check failed: {e}'}
    
    async def _check_file_count(self) -> Dict[str, Any]:
        """Check file count in temp directory"""
        try:
            from pathlib import Path
            
            temp_dir = Path(self.storage_config['temp_dir'])
            
            if not temp_dir.exists():
                return {'healthy': True, 'message': 'Directory does not exist'}
            
            file_count = len(list(temp_dir.glob('*')))
            
            # Check if file count is acceptable (less than 1000)
            max_files = 1000
            healthy = file_count < max_files
            
            return {
                'healthy': healthy,
                'file_count': file_count,
                'max_files': max_files,
                'message': f"{file_count} files"
            }
            
        except Exception as e:
            logger.error(f"File count check failed: {e}")
            return {'healthy': False, 'message': f'Check failed: {e}'}
    
    async def _update_metrics(self):
        """Update system metrics"""
        try:
            # This would typically update Prometheus metrics
            # For now, just log the current status
            if self.is_running:
                logger.debug("Worker metrics updated")
                
        except Exception as e:
            logger.error(f"Metrics update failed: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get worker status information"""
        return {
            'is_running': self.is_running,
            'last_cleanup': datetime.fromtimestamp(self.last_cleanup).isoformat(),
            'active_tasks': len(self.tasks),
            'cleanup_interval': self.storage_config['cleanup_interval'],
            'health_check_interval': self.monitoring_config['health_check_interval']
        }
    
    async def run_cleanup_now(self):
        """Run cleanup immediately"""
        try:
            logger.info("Manual cleanup requested")
            await self._perform_cleanup()
            return {'status': 'success', 'message': 'Cleanup completed'}
        except Exception as e:
            logger.error(f"Manual cleanup failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return await self._check_system_health()
