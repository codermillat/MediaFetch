#!/usr/bin/env python3
"""
Configuration management for MediaFetch bot
Loads all configuration from environment variables for Heroku deployment
"""

import os
from typing import Optional, Dict, Any
from urllib.parse import urlparse

class Config:
    """Configuration management for the MediaFetch bot"""
    
    def __init__(self):
        """Initialize configuration from environment variables"""
        self._validate_required_config()
    
    def _validate_required_config(self):
        """Validate that all required configuration is present"""
        required_vars = ['TELEGRAM_BOT_TOKEN']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}. "
                "Please set these in your Heroku config vars."
            )
    
    def get_telegram_token(self) -> str:
        """Get Telegram bot token from environment variable"""
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        return token
    
    def get_instagram_token(self) -> Optional[str]:
        """Get Instagram access token from environment variable"""
        return os.getenv('INSTAGRAM_ACCESS_TOKEN')
    
    def get_facebook_token(self) -> Optional[str]:
        """Get Facebook access token from environment variable"""
        return os.getenv('FACEBOOK_ACCESS_TOKEN')
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration from environment variables (for Heroku Redis)"""
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            parsed = urlparse(redis_url)
            return {
                'host': parsed.hostname,
                'port': parsed.port or 6379,
                'password': parsed.password,
                'ssl': parsed.scheme == 'rediss'
            }
        else:
            # Fallback to local Redis for development
            return {
                'host': 'localhost',
                'port': 6379,
                'password': None,
                'ssl': False
            }
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration from environment variables (for Heroku Postgres)"""
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            parsed = urlparse(database_url)
            return {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'database': parsed.path[1:],  # Remove leading slash
                'username': parsed.username,
                'password': parsed.password,
                'ssl': parsed.scheme == 'postgresql'
            }
        else:
            # Fallback to local database for development
            return {
                'host': 'localhost',
                'port': 5432,
                'database': 'mediafetch',
                'username': 'postgres',
                'password': 'password',
                'ssl': False
            }
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration for Heroku ephemeral filesystem"""
        return {
            'temp_dir': os.getenv('TEMP_DIR', '/tmp'),
            'max_file_size': int(os.getenv('MAX_FILE_SIZE', 50 * 1024 * 1024)),  # 50MB default
            'cleanup_interval': int(os.getenv('CLEANUP_INTERVAL', 300)),  # 5 minutes
            'max_concurrent_downloads': int(os.getenv('MAX_CONCURRENT_DOWNLOADS', 5))
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return {
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'enable_metrics': os.getenv('ENABLE_METRICS', 'true').lower() == 'true',
            'metrics_port': int(os.getenv('METRICS_PORT', 8000)),
            'health_check_interval': int(os.getenv('HEALTH_CHECK_INTERVAL', 30))
        }
    
    def get_download_config(self) -> Dict[str, Any]:
        """Get download configuration"""
        return {
            'timeout': int(os.getenv('DOWNLOAD_TIMEOUT', 300)),  # 5 minutes
            'max_retries': int(os.getenv('MAX_RETRIES', 3)),
            'retry_delay': int(os.getenv('RETRY_DELAY', 5)),  # 5 seconds
            'user_agent': os.getenv('USER_AGENT', 'MediaFetch/1.0'),
            'format_preference': os.getenv('FORMAT_PREFERENCE', 'best')
        }
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration"""
        return {
            'allowed_domains': os.getenv('ALLOWED_DOMAINS', '').split(','),
            'blocked_domains': os.getenv('BLOCKED_DOMAINS', '').split(','),
            'rate_limit_per_user': int(os.getenv('RATE_LIMIT_PER_USER', 10)),  # downloads per hour
            'rate_limit_window': int(os.getenv('RATE_LIMIT_WINDOW', 3600))  # 1 hour
        }
    
    def is_production(self) -> bool:
        """Check if running in production (Heroku)"""
        return os.getenv('DYNO') is not None
    
    def get_environment(self) -> str:
        """Get current environment"""
        return os.getenv('ENVIRONMENT', 'development')
    
    def get_version(self) -> str:
        """Get application version"""
        return os.getenv('APP_VERSION', '1.0.0')
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration as a dictionary"""
        return {
            'telegram_token': self.get_telegram_token(),
            'instagram_token': self.get_instagram_token(),
            'facebook_token': self.get_facebook_token(),
            'redis_config': self.get_redis_config(),
            'database_config': self.get_database_config(),
            'storage_config': self.get_storage_config(),
            'monitoring_config': self.get_monitoring_config(),
            'download_config': self.get_download_config(),
            'security_config': self.get_security_config(),
            'environment': self.get_environment(),
            'version': self.get_version(),
            'is_production': self.is_production()
        }
