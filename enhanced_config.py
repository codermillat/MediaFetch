"""
Enhanced Configuration System for MediaFetch
Runtime validation and environment-specific configurations
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from pathlib import Path
from dataclasses import dataclass, field
import re

logger = logging.getLogger(__name__)


@dataclass
class ConfigValidationError(Exception):
    """Exception raised for configuration validation errors"""
    field: str
    value: Any
    reason: str

    def __str__(self):
        return f"Configuration error for '{self.field}': {self.reason} (value: {self.value})"


@dataclass
class ConfigField:
    """Represents a configuration field with validation"""
    name: str
    type: type
    required: bool = False
    default: Any = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[List[Any]] = None
    pattern: Optional[str] = None
    validator: Optional[Callable] = None
    description: str = ""

    def validate(self, value: Any) -> Any:
        """Validate and convert the configuration value"""
        if value is None:
            if self.required and self.default is None:
                raise ConfigValidationError(self.name, value, "Required field is missing")
            return self.default

        # Type conversion and validation
        try:
            if self.type == bool:
                if isinstance(value, str):
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif isinstance(value, int):
                    value = bool(value)
                else:
                    value = bool(value)
            elif self.type == int:
                value = int(value)
            elif self.type == float:
                value = float(value)
            elif self.type == str:
                value = str(value)
            elif self.type == list:
                if isinstance(value, str):
                    value = [v.strip() for v in value.split(',')]
                elif not isinstance(value, list):
                    value = [value]
            elif self.type == dict:
                if isinstance(value, str):
                    value = json.loads(value)
                elif not isinstance(value, dict):
                    raise ValueError(f"Cannot convert {type(value)} to dict")
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            raise ConfigValidationError(self.name, value, f"Invalid type conversion: {e}")

        # Range validation
        if self.min_value is not None and value < self.min_value:
            raise ConfigValidationError(self.name, value, f"Value below minimum {self.min_value}")

        if self.max_value is not None and value > self.max_value:
            raise ConfigValidationError(self.name, value, f"Value above maximum {self.max_value}")

        # Allowed values validation
        if self.allowed_values is not None and value not in self.allowed_values:
            raise ConfigValidationError(self.name, value, f"Value not in allowed list: {self.allowed_values}")

        # Pattern validation
        if self.pattern is not None and isinstance(value, str):
            if not re.match(self.pattern, value):
                raise ConfigValidationError(self.name, value, f"Value doesn't match pattern {self.pattern}")

        # Custom validation
        if self.validator is not None:
            try:
                self.validator(value)
            except Exception as e:
                raise ConfigValidationError(self.name, value, f"Custom validation failed: {e}")

        return value


@dataclass
class ConfigSchema:
    """Configuration schema with validation rules"""
    fields: Dict[str, ConfigField] = field(default_factory=dict)
    environment_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def add_field(self, field: ConfigField):
        """Add a field to the schema"""
        self.fields[field.name] = field

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a complete configuration"""
        validated_config = {}

        # Validate each field
        for field_name, field in self.fields.items():
            try:
                value = config.get(field_name, os.getenv(field_name.upper()))
                validated_value = field.validate(value)
                validated_config[field_name] = validated_value
            except ConfigValidationError as e:
                logger.error(f"Configuration validation error: {e}")
                raise

        return validated_config

    def get_environment_schema(self, environment: str) -> Dict[str, ConfigField]:
        """Get schema for specific environment"""
        base_schema = self.fields.copy()

        if environment in self.environment_overrides:
            base_schema.update(self.environment_overrides[environment])

        return base_schema


class MediaFetchConfig:
    """Enhanced configuration system for MediaFetch"""

    def __init__(self):
        self.schema = ConfigSchema()
        self._config: Dict[str, Any] = {}
        self._loaded = False

        # Initialize schema with all configuration fields
        self._init_schema()

    def _init_schema(self):
        """Initialize the configuration schema"""
        # Core application settings
        self.schema.add_field(ConfigField(
            "environment", str,
            required=True,
            allowed_values=["development", "staging", "production"],
            default="development",
            description="Application environment"
        ))

        self.schema.add_field(ConfigField(
            "debug", bool,
            default=False,
            description="Enable debug mode"
        ))

        self.schema.add_field(ConfigField(
            "log_level", str,
            allowed_values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            default="INFO",
            description="Logging level"
        ))

        # Telegram configuration
        self.schema.add_field(ConfigField(
            "telegram_bot_token", str,
            required=True,
            pattern=r"^\d+:[A-Za-z0-9_-]{35}$",
            description="Telegram bot token"
        ))

        # Database configuration
        self.schema.add_field(ConfigField(
            "supabase_url", str,
            required=True,
            pattern=r"^https://[a-z0-9-]+\.supabase\.co$",
            description="Supabase URL"
        ))

        self.schema.add_field(ConfigField(
            "supabase_anon_key", str,
            required=True,
            pattern=r"^eyJ[A-Za-z0-9_.-]+$",
            description="Supabase anonymous key"
        ))

        self.schema.add_field(ConfigField(
            "supabase_service_role_key", str,
            required=True,
            pattern=r"^eyJ[A-Za-z0-9_.-]+$",
            description="Supabase service role key"
        ))

        # Instagram configuration
        self.schema.add_field(ConfigField(
            "instagram_username", str,
            pattern=r"^[a-zA-Z0-9_.]{1,30}$",
            description="Instagram bot username"
        ))

        self.schema.add_field(ConfigField(
            "instagram_password", str,
            description="Instagram bot password"
        ))

        # Performance settings
        self.schema.add_field(ConfigField(
            "database_pool_size", int,
            min_value=1,
            max_value=50,
            default=10,
            description="Database connection pool size"
        ))

        self.schema.add_field(ConfigField(
            "cache_ttl", int,
            min_value=60,
            max_value=86400,
            default=300,
            description="Cache TTL in seconds"
        ))

        self.schema.add_field(ConfigField(
            "max_file_size", int,
            min_value=1024,
            max_value=2147483648,  # 2GB
            default=52428800,  # 50MB
            description="Maximum file size in bytes"
        ))

        # Rate limiting
        self.schema.add_field(ConfigField(
            "rate_limit_per_user", int,
            min_value=1,
            max_value=10000,
            default=10,
            description="Rate limit per user per hour"
        ))

        self.schema.add_field(ConfigField(
            "rate_limit_window", int,
            min_value=60,
            max_value=86400,
            default=3600,
            description="Rate limit window in seconds"
        ))

        # Monitoring and alerting
        self.schema.add_field(ConfigField(
            "monitoring_enabled", bool,
            default=True,
            description="Enable monitoring"
        ))

        self.schema.add_field(ConfigField(
            "health_check_interval", int,
            min_value=10,
            max_value=3600,
            default=30,
            description="Health check interval in seconds"
        ))

        # Webhook URLs
        self.schema.add_field(ConfigField(
            "health_webhook_url", str,
            pattern=r"^https?://[^\s/$.?#].[^\s]*$",
            description="Health monitoring webhook URL"
        ))

        self.schema.add_field(ConfigField(
            "error_webhook_url", str,
            pattern=r"^https?://[^\s/$.?#].[^\s]*$",
            description="Error reporting webhook URL"
        ))

        # External monitoring services
        self.schema.add_field(ConfigField(
            "datadog_api_key", str,
            description="DataDog API key"
        ))

        self.schema.add_field(ConfigField(
            "new_relic_license_key", str,
            description="New Relic license key"
        ))

        self.schema.add_field(ConfigField(
            "prometheus_push_gateway", str,
            pattern=r"^https?://[^\s/$.?#].[^\s]*$",
            description="Prometheus push gateway URL"
        ))

        # Environment-specific overrides
        self._init_environment_overrides()

    def _init_environment_overrides(self):
        """Initialize environment-specific configuration overrides"""
        # Production overrides
        self.schema.environment_overrides["production"] = {
            "debug": ConfigField("debug", bool, default=False),
            "database_pool_size": ConfigField("database_pool_size", int, default=20),
            "cache_ttl": ConfigField("cache_ttl", int, default=3600),
            "monitoring_enabled": ConfigField("monitoring_enabled", bool, default=True),
            "log_level": ConfigField("log_level", str, default="WARNING")
        }

        # Staging overrides
        self.schema.environment_overrides["staging"] = {
            "debug": ConfigField("debug", bool, default=False),
            "database_pool_size": ConfigField("database_pool_size", int, default=10),
            "cache_ttl": ConfigField("cache_ttl", int, default=1800),
            "monitoring_enabled": ConfigField("monitoring_enabled", bool, default=True),
            "log_level": ConfigField("log_level", str, default="INFO")
        }

        # Development overrides
        self.schema.environment_overrides["development"] = {
            "debug": ConfigField("debug", bool, default=True),
            "database_pool_size": ConfigField("database_pool_size", int, default=2),
            "cache_ttl": ConfigField("cache_ttl", int, default=300),
            "monitoring_enabled": ConfigField("monitoring_enabled", bool, default=False),
            "log_level": ConfigField("log_level", str, default="DEBUG")
        }

    def load_config(self, config_file: Optional[str] = None, environment: Optional[str] = None) -> Dict[str, Any]:
        """Load and validate configuration"""
        try:
            # Load from environment variables
            raw_config = dict(os.environ)

            # Load from config file if provided
            if config_file and Path(config_file).exists():
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                    raw_config.update(file_config)

            # Determine environment
            if environment is None:
                environment = raw_config.get('ENVIRONMENT', 'development')

            # Get environment-specific schema
            env_schema = self.schema.get_environment_schema(environment)

            # Validate configuration
            validated_config = {}
            for field_name, field in env_schema.items():
                try:
                    value = raw_config.get(field_name.upper())  # Environment variables are uppercase
                    validated_value = field.validate(value)
                    validated_config[field_name] = validated_value
                except ConfigValidationError as e:
                    logger.error(f"Configuration error: {e}")
                    raise

            # Store validated configuration
            self._config = validated_config
            self._loaded = True

            logger.info(f"Configuration loaded successfully for environment: {environment}")
            return self._config

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        if not self._loaded:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")

        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        """Set configuration value with validation"""
        if key not in self.schema.fields:
            raise ConfigValidationError(key, value, "Unknown configuration field")

        field = self.schema.fields[key]
        validated_value = field.validate(value)
        self._config[key] = validated_value

    def validate_runtime_config(self) -> Dict[str, Any]:
        """Validate configuration at runtime"""
        issues = []

        # Check required services connectivity
        if self.get('supabase_url') and self.get('supabase_anon_key'):
            try:
                # Test Supabase connection
                import requests
                response = requests.get(f"{self.get('supabase_url')}/rest/v1/", timeout=5)
                if response.status_code != 200:
                    issues.append({
                        'severity': 'error',
                        'service': 'supabase',
                        'message': f'Supabase connection failed: {response.status_code}'
                    })
            except Exception as e:
                issues.append({
                    'severity': 'error',
                    'service': 'supabase',
                    'message': f'Supabase connection error: {e}'
                })

        # Check file system permissions
        temp_dir = self.get('temp_dir', '/tmp')
        try:
            Path(temp_dir).mkdir(parents=True, exist_ok=True)
            test_file = Path(temp_dir) / 'test_write'
            test_file.write_text('test')
            test_file.unlink()
        except Exception as e:
            issues.append({
                'severity': 'warning',
                'service': 'filesystem',
                'message': f'File system write error: {e}'
            })

        # Check rate limiting configuration
        rate_limit = self.get('rate_limit_per_user', 10)
        if rate_limit > 1000:
            issues.append({
                'severity': 'warning',
                'service': 'rate_limiting',
                'message': f'Very high rate limit: {rate_limit} requests/hour'
            })

        return {
            'valid': len([i for i in issues if i['severity'] == 'error']) == 0,
            'issues': issues
        }

    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for monitoring"""
        if not self._loaded:
            return {'error': 'Configuration not loaded'}

        return {
            'environment': self.get('environment'),
            'debug_mode': self.get('debug'),
            'log_level': self.get('log_level'),
            'database_pool_size': self.get('database_pool_size'),
            'cache_ttl': self.get('cache_ttl'),
            'max_file_size_mb': self.get('max_file_size', 0) / (1024 * 1024),
            'rate_limit_per_user': self.get('rate_limit_per_user'),
            'monitoring_enabled': self.get('monitoring_enabled'),
            'external_monitoring': bool(
                self.get('datadog_api_key') or
                self.get('new_relic_license_key') or
                self.get('prometheus_push_gateway')
            )
        }

    def export_config(self, file_path: str, mask_sensitive: bool = True):
        """Export configuration to file"""
        export_config = self._config.copy()

        if mask_sensitive:
            sensitive_fields = [
                'telegram_bot_token', 'supabase_anon_key', 'supabase_service_role_key',
                'instagram_password', 'datadog_api_key', 'new_relic_license_key'
            ]

            for field in sensitive_fields:
                if field in export_config:
                    export_config[field] = '***MASKED***'

        with open(file_path, 'w') as f:
            json.dump(export_config, f, indent=2, default=str)

        logger.info(f"Configuration exported to {file_path}")


# Global configuration instance
_config_instance: Optional[MediaFetchConfig] = None


def get_config() -> MediaFetchConfig:
    """Get the global configuration instance"""
    global _config_instance

    if _config_instance is None:
        _config_instance = MediaFetchConfig()

    return _config_instance


def init_config(config_file: Optional[str] = None, environment: Optional[str] = None) -> MediaFetchConfig:
    """Initialize and load configuration"""
    config = get_config()
    config.load_config(config_file, environment)
    return config


def get_config_validation_status() -> Dict[str, Any]:
    """Get configuration validation status"""
    config = get_config()

    if not config._loaded:
        return {
            'valid': False,
            'error': 'Configuration not loaded'
        }

    return config.validate_runtime_config()


def reload_config() -> Dict[str, Any]:
    """Reload configuration from environment"""
    try:
        config = get_config()
        config.load_config()
        validation = config.validate_runtime_config()

        return {
            'success': True,
            'message': 'Configuration reloaded successfully',
            'validation': validation
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
