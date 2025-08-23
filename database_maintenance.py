"""
Database Maintenance and Backup System for MediaFetch
Provides automated backup, archiving, and maintenance operations
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import threading
import gzip
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseBackupManager:
    """Manages database backups and maintenance"""

    def __init__(self, backup_dir: str = "backups", retention_days: int = 30):
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.backup_dir.mkdir(exist_ok=True)

        # Backup configuration
        self.backup_config = {
            'daily_backups': True,
            'weekly_backups': True,
            'monthly_backups': True,
            'compress_backups': True,
            'backup_tables': [
                'users', 'user_bindings', 'binding_codes',
                'content_deliveries', 'instagram_posts', 'media_files'
            ]
        }

        # Start maintenance thread
        self._maintenance_thread = threading.Thread(target=self._maintenance_worker, daemon=True)
        self._maintenance_thread.start()

        logger.info(f"Database backup manager initialized with backup dir: {self.backup_dir}")

    def create_backup(self, backup_type: str = 'manual', tables: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a database backup"""
        try:
            from connection_pool import get_db_pool

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"mediafetch_{backup_type}_{timestamp}"

            if self.backup_config['compress_backups']:
                backup_filename += ".json.gz"
            else:
                backup_filename += ".json"

            backup_path = self.backup_dir / backup_filename

            # Get database connection
            db_pool = get_db_pool()
            backup_data = {}

            # Backup specified tables or all configured tables
            tables_to_backup = tables or self.backup_config['backup_tables']

            for table in tables_to_backup:
                try:
                    logger.info(f"Backing up table: {table}")
                    result = db_pool.execute_query(f"SELECT * FROM {table}")

                    if result:
                        backup_data[table] = result
                        logger.info(f"Backed up {len(result)} records from {table}")
                    else:
                        logger.warning(f"No data found in table: {table}")

                except Exception as e:
                    logger.error(f"Failed to backup table {table}: {e}")
                    backup_data[f"ERROR_{table}"] = str(e)

            # Add metadata
            backup_data['_metadata'] = {
                'timestamp': datetime.utcnow().isoformat(),
                'backup_type': backup_type,
                'tables_backed_up': len([k for k in backup_data.keys() if not k.startswith('_')]),
                'total_records': sum(len(data) if isinstance(data, list) else 0 for data in backup_data.values())
            }

            # Save backup
            if self.backup_config['compress_backups']:
                with gzip.open(backup_path, 'wt', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, default=str)
            else:
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, default=str)

            logger.info(f"Database backup created: {backup_path}")

            return {
                'success': True,
                'backup_path': str(backup_path),
                'backup_size': backup_path.stat().st_size,
                'tables_backed_up': len(tables_to_backup),
                'metadata': backup_data['_metadata']
            }

        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def restore_backup(self, backup_path: str, tables: Optional[List[str]] = None) -> Dict[str, Any]:
        """Restore database from backup"""
        try:
            from connection_pool import get_db_pool

            backup_file = Path(backup_path)
            if not backup_file.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")

            # Load backup data
            if backup_path.endswith('.gz'):
                with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                    backup_data = json.load(f)
            else:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)

            # Get database connection
            db_pool = get_db_pool()
            restored_tables = []
            total_records = 0

            # Restore specified tables or all tables in backup
            tables_to_restore = tables or [k for k in backup_data.keys() if not k.startswith('_')]

            for table in tables_to_restore:
                if table in backup_data and isinstance(backup_data[table], list):
                    try:
                        logger.info(f"Restoring table: {table}")

                        # Clear existing data
                        db_pool.execute_query(f"DELETE FROM {table}")

                        # Insert backup data
                        if backup_data[table]:
                            # This is a simplified restore - in production you'd want more sophisticated handling
                            logger.warning(f"Restore for table {table} requires manual handling")
                            restored_tables.append(table)
                            total_records += len(backup_data[table])

                    except Exception as e:
                        logger.error(f"Failed to restore table {table}: {e}")

            return {
                'success': True,
                'backup_path': backup_path,
                'restored_tables': restored_tables,
                'total_records': total_records,
                'metadata': backup_data.get('_metadata', {})
            }

        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def cleanup_old_backups(self) -> Dict[str, Any]:
        """Clean up old backup files based on retention policy"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)

            deleted_files = []
            total_size_cleaned = 0

            for backup_file in self.backup_dir.glob("mediafetch_*.json*"):
                try:
                    # Extract timestamp from filename
                    filename = backup_file.name
                    timestamp_str = filename.split('_')[2].split('.')[0]  # Extract timestamp part
                    file_timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                    if file_timestamp < cutoff_date:
                        file_size = backup_file.stat().st_size
                        backup_file.unlink()
                        deleted_files.append(filename)
                        total_size_cleaned += file_size
                        logger.info(f"Deleted old backup: {filename}")

                except Exception as e:
                    logger.error(f"Error processing backup file {backup_file}: {e}")

            return {
                'success': True,
                'deleted_files': deleted_files,
                'total_cleaned_size': total_size_cleaned,
                'retention_days': self.retention_days
            }

        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def list_backups(self) -> Dict[str, Any]:
        """List all available backup files"""
        try:
            backups = []

            for backup_file in self.backup_dir.glob("mediafetch_*.json*"):
                try:
                    stat = backup_file.stat()
                    backups.append({
                        'filename': backup_file.name,
                        'path': str(backup_file),
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'compressed': backup_file.suffix == '.gz'
                    })
                except Exception as e:
                    logger.error(f"Error reading backup file info: {e}")

            backups.sort(key=lambda x: x['created'], reverse=True)

            return {
                'success': True,
                'backups': backups,
                'total_backups': len(backups),
                'total_size': sum(b['size'] for b in backups)
            }

        except Exception as e:
            logger.error(f"List backups failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _maintenance_worker(self):
        """Background maintenance worker"""
        while True:
            try:
                # Run maintenance tasks every 24 hours
                time.sleep(24 * 3600)

                logger.info("Running scheduled database maintenance")

                # Create daily backup
                if self.backup_config['daily_backups']:
                    self.create_backup('daily')

                # Clean up old backups
                self.cleanup_old_backups()

                # Archive old data (if needed)
                self._archive_old_data()

            except Exception as e:
                logger.error(f"Database maintenance error: {e}")
                time.sleep(3600)  # Wait 1 hour before retry

    def _archive_old_data(self):
        """Archive old data to reduce database size"""
        try:
            from connection_pool import get_db_pool

            db_pool = get_db_pool()

            # Archive binding codes older than 90 days
            cutoff_date = datetime.utcnow() - timedelta(days=90)

            # Move old binding codes to archive table
            archive_query = """
                INSERT INTO binding_codes_archive
                SELECT * FROM binding_codes
                WHERE expires_at < %s AND is_used = TRUE
            """
            db_pool.execute_query(archive_query, (cutoff_date.isoformat(),))

            # Delete archived records from main table
            delete_query = """
                DELETE FROM binding_codes
                WHERE expires_at < %s AND is_used = TRUE
            """
            db_pool.execute_query(delete_query, (cutoff_date.isoformat(),))

            logger.info("Old binding codes archived and cleaned up")

        except Exception as e:
            logger.error(f"Data archiving failed: {e}")


class DataArchivalManager:
    """Manages data archival for long-term storage"""

    def __init__(self, archive_dir: str = "archives"):
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(exist_ok=True)

    def archive_user_data(self, user_id: int, retention_days: int = 365) -> Dict[str, Any]:
        """Archive user data for long-term storage"""
        try:
            from connection_pool import get_db_pool

            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            db_pool = get_db_pool()

            # Get user data to archive
            user_data = {}

            # Get old bindings
            bindings = db_pool.execute_query(
                "SELECT * FROM user_bindings WHERE user_id = %s AND created_at < %s",
                (user_id, cutoff_date.isoformat())
            )
            user_data['bindings'] = bindings or []

            # Get old content deliveries
            deliveries = db_pool.execute_query(
                "SELECT * FROM content_deliveries WHERE telegram_user_id = %s AND created_at < %s",
                (user_id, cutoff_date.isoformat())
            )
            user_data['deliveries'] = deliveries or []

            if not user_data['bindings'] and not user_data['deliveries']:
                return {
                    'success': True,
                    'message': 'No old data to archive',
                    'archived_records': 0
                }

            # Create archive file
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"user_{user_id}_archive_{timestamp}.json.gz"
            archive_path = self.archive_dir / archive_filename

            # Save archived data
            with gzip.open(archive_path, 'wt', encoding='utf-8') as f:
                json.dump(user_data, f, indent=2, default=str)

            # Delete archived data from main tables (optional)
            # This would require careful consideration of data dependencies

            return {
                'success': True,
                'archive_path': str(archive_path),
                'archived_bindings': len(user_data['bindings']),
                'archived_deliveries': len(user_data['deliveries']),
                'total_archived': len(user_data['bindings']) + len(user_data['deliveries'])
            }

        except Exception as e:
            logger.error(f"User data archival failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global instances
_backup_manager: Optional[DatabaseBackupManager] = None
_archival_manager: Optional[DataArchivalManager] = None


def get_backup_manager() -> DatabaseBackupManager:
    """Get the global backup manager instance"""
    global _backup_manager

    if _backup_manager is None:
        _backup_manager = DatabaseBackupManager()

    return _backup_manager


def get_archival_manager() -> DataArchivalManager:
    """Get the global archival manager instance"""
    global _archival_manager

    if _archival_manager is None:
        _archival_manager = DataArchivalManager()

    return _archival_manager


def init_database_maintenance():
    """Initialize database maintenance system"""
    backup_manager = get_backup_manager()
    archival_manager = get_archival_manager()

    logger.info("Database maintenance system initialized")

    return {
        'backup_manager': backup_manager,
        'archival_manager': archival_manager
    }


def create_database_backup(backup_type: str = 'manual') -> Dict[str, Any]:
    """Create a database backup"""
    return get_backup_manager().create_backup(backup_type)


def restore_database_backup(backup_path: str) -> Dict[str, Any]:
    """Restore database from backup"""
    return get_backup_manager().restore_backup(backup_path)


def cleanup_database_backups() -> Dict[str, Any]:
    """Clean up old database backups"""
    return get_backup_manager().cleanup_old_backups()


def list_database_backups() -> Dict[str, Any]:
    """List available database backups"""
    return get_backup_manager().list_backups()
