#!/usr/bin/env python3
"""
Production Configuration for MediaFetch
Environment variables and production settings
"""

import os

# Production Environment Configuration
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'production')
FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# Supabase Configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://vtbrkmnizkyeflhwypfm.supabase.co')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')

# Instagram Configuration
INSTAGRAM_USERNAME = os.environ.get('INSTAGRAM_USERNAME', 'mediafetchbot')
INSTAGRAM_PASSWORD = os.environ.get('INSTAGRAM_PASSWORD')

# Production Settings
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', 52428800))  # 50MB
DOWNLOAD_TIMEOUT = int(os.environ.get('DOWNLOAD_TIMEOUT', 300))
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', 3))
CLEANUP_INTERVAL = int(os.environ.get('CLEANUP_INTERVAL', 300))
HEALTH_CHECK_INTERVAL = int(os.environ.get('HEALTH_CHECK_INTERVAL', 30))
RATE_LIMIT_PER_USER = int(os.environ.get('RATE_LIMIT_PER_USER', 10))

# Heroku Configuration
PORT = int(os.environ.get('PORT', 5001))
DYNO = os.environ.get('DYNO', 'web')

# Production Features
ENABLE_METRICS = True
ENABLE_HEALTH_CHECKS = True
ENABLE_RATE_LIMITING = True
ENABLE_AUTO_CLEANUP = True
ENABLE_ERROR_REPORTING = True

# Security Settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Logging Configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Performance Settings
WORKER_CONNECTIONS = 1000
WORKER_TIMEOUT = 120
KEEPALIVE = 5
MAX_REQUESTS = 1000
MAX_REQUESTS_JITTER = 50

def is_production():
    """Check if running in production environment"""
    return ENVIRONMENT == 'production'

def get_config():
    """Get production configuration"""
    return {
        'environment': ENVIRONMENT,
        'flask_env': FLASK_ENV,
        'flask_debug': FLASK_DEBUG,
        'port': PORT,
        'dyno': DYNO,
        'log_level': LOG_LEVEL,
        'max_file_size': MAX_FILE_SIZE,
        'download_timeout': DOWNLOAD_TIMEOUT,
        'max_retries': MAX_RETRIES,
        'cleanup_interval': CLEANUP_INTERVAL,
        'health_check_interval': HEALTH_CHECK_INTERVAL,
        'rate_limit_per_user': RATE_LIMIT_PER_USER,
        'enable_metrics': ENABLE_METRICS,
        'enable_health_checks': ENABLE_HEALTH_CHECKS,
        'enable_rate_limiting': ENABLE_RATE_LIMITING,
        'enable_auto_cleanup': ENABLE_AUTO_CLEANUP,
        'enable_error_reporting': ENABLE_ERROR_REPORTING,
    }
