"""
Deployment Configuration for MediaFetch
Advanced deployment strategies and production configurations
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import subprocess
import requests

logger = logging.getLogger(__name__)


class DeploymentManager:
    """Manages advanced deployment strategies"""

    def __init__(self, app_name: str = "mediafetch"):
        self.app_name = app_name
        self.deploy_dir = Path("/opt") / app_name
        self.backup_dir = Path("/opt") / f"{app_name}_backups"
        self.config_dir = Path("/etc") / app_name

        # Create directories
        self.deploy_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Deployment state
        self.current_version = None
        self.previous_version = None
        self.deployment_history: List[Dict[str, Any]] = []

    def blue_green_deployment(self, new_version_path: str, health_check_url: str) -> Dict[str, Any]:
        """Perform blue-green deployment"""
        try:
            new_version_path = Path(new_version_path)

            if not new_version_path.exists():
                raise FileNotFoundError(f"New version not found: {new_version_path}")

            # Create deployment ID
            deployment_id = f"deployment_{int(datetime.now().timestamp())}"

            logger.info(f"Starting blue-green deployment: {deployment_id}")

            # Backup current version
            backup_result = self._backup_current_version(deployment_id)
            if not backup_result['success']:
                raise RuntimeError(f"Backup failed: {backup_result['error']}")

            # Deploy to green environment
            green_env = f"{self.app_name}_green"
            deploy_result = self._deploy_to_environment(new_version_path, green_env, deployment_id)

            if not deploy_result['success']:
                # Rollback on failure
                self._rollback_deployment(backup_result['backup_path'])
                raise RuntimeError(f"Deployment failed: {deploy_result['error']}")

            # Health check on green environment
            health_result = self._wait_for_health(health_check_url, timeout=300)
            if not health_result['success']:
                # Rollback on health check failure
                self._rollback_deployment(backup_result['backup_path'])
                raise RuntimeError(f"Health check failed: {health_result['error']}")

            # Switch traffic to green environment
            switch_result = self._switch_traffic(green_env)
            if not switch_result['success']:
                # Rollback on traffic switch failure
                self._rollback_deployment(backup_result['backup_path'])
                raise RuntimeError(f"Traffic switch failed: {switch_result['error']}")

            # Update deployment state
            self.previous_version = self.current_version
            self.current_version = deployment_id

            # Record deployment
            deployment_record = {
                'id': deployment_id,
                'timestamp': datetime.now().isoformat(),
                'type': 'blue_green',
                'status': 'completed',
                'new_version_path': str(new_version_path),
                'backup_path': backup_result['backup_path'],
                'health_check_url': health_check_url
            }
            self.deployment_history.append(deployment_record)

            logger.info(f"Blue-green deployment completed successfully: {deployment_id}")

            return {
                'success': True,
                'deployment_id': deployment_id,
                'message': 'Blue-green deployment completed successfully'
            }

        except Exception as e:
            logger.error(f"Blue-green deployment failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _backup_current_version(self, deployment_id: str) -> Dict[str, Any]:
        """Backup current version before deployment"""
        try:
            backup_path = self.backup_dir / f"backup_{deployment_id}"
            backup_path.mkdir(exist_ok=True)

            # Backup application files
            if self.deploy_dir.exists():
                # Use rsync for efficient backup
                result = subprocess.run([
                    'rsync', '-a', '--delete',
                    str(self.deploy_dir) + '/',
                    str(backup_path) + '/'
                ], capture_output=True, text=True, timeout=300)

                if result.returncode != 0:
                    raise RuntimeError(f"Backup failed: {result.stderr}")

            return {
                'success': True,
                'backup_path': str(backup_path)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _deploy_to_environment(self, source_path: str, environment: str, deployment_id: str) -> Dict[str, Any]:
        """Deploy application to specific environment"""
        try:
            env_dir = self.deploy_dir.parent / environment
            env_dir.mkdir(exist_ok=True)

            # Copy new version
            result = subprocess.run([
                'rsync', '-a', '--delete',
                f"{source_path}/",
                f"{env_dir}/"
            ], capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                raise RuntimeError(f"Deployment failed: {result.stderr}")

            # Install dependencies if requirements.txt exists
            requirements_path = env_dir / "requirements.txt"
            if requirements_path.exists():
                subprocess.run([
                    'pip', 'install', '-r', str(requirements_path)
                ], cwd=env_dir, timeout=600)

            return {
                'success': True,
                'environment': environment,
                'deploy_path': str(env_dir)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _wait_for_health(self, health_url: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for health check to pass"""
        import time

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.get(health_url, timeout=10)

                if response.status_code == 200:
                    health_data = response.json()
                    if health_data.get('status') == 'healthy':
                        return {
                            'success': True,
                            'message': 'Health check passed'
                        }

                logger.debug(f"Health check failed: {response.status_code}")
                time.sleep(5)

            except Exception as e:
                logger.debug(f"Health check error: {e}")
                time.sleep(5)

        return {
            'success': False,
            'error': f'Health check timeout after {timeout} seconds'
        }

    def _switch_traffic(self, new_environment: str) -> Dict[str, Any]:
        """Switch traffic to new environment"""
        try:
            # This would typically involve:
            # 1. Updating load balancer configuration
            # 2. Updating DNS records
            # 3. Restarting services

            # For demonstration, we'll simulate this with a symlink switch
            current_link = self.deploy_dir / "current"
            new_env_path = self.deploy_dir.parent / new_environment

            # Remove old symlink and create new one
            if current_link.exists():
                current_link.unlink()

            current_link.symlink_to(new_env_path)

            return {
                'success': True,
                'message': f'Traffic switched to {new_environment}'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _rollback_deployment(self, backup_path: str) -> bool:
        """Rollback to previous version"""
        try:
            backup_path = Path(backup_path)

            if not backup_path.exists():
                logger.error(f"Backup not found: {backup_path}")
                return False

            # Restore from backup
            result = subprocess.run([
                'rsync', '-a', '--delete',
                f"{backup_path}/",
                f"{self.deploy_dir}/"
            ], capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                logger.info(f"Rollback completed successfully from {backup_path}")
                return True
            else:
                logger.error(f"Rollback failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Rollback error: {e}")
            return False

    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status"""
        return {
            'current_version': self.current_version,
            'previous_version': self.previous_version,
            'deployment_history': self.deployment_history[-5:],  # Last 5 deployments
            'deploy_dir': str(self.deploy_dir),
            'backup_dir': str(self.backup_dir)
        }


class MonitoringIntegration:
    """Integration with external monitoring services"""

    def __init__(self):
        self.monitoring_configs = {
            'datadog': self._get_datadog_config(),
            'new_relic': self._get_new_relic_config(),
            'prometheus': self._get_prometheus_config()
        }

    def _get_datadog_config(self) -> Dict[str, Any]:
        """Get DataDog configuration"""
        return {
            'api_key': os.getenv('DATADOG_API_KEY'),
            'app_key': os.getenv('DATADOG_APP_KEY'),
            'enabled': bool(os.getenv('DATADOG_API_KEY'))
        }

    def _get_new_relic_config(self) -> Dict[str, Any]:
        """Get New Relic configuration"""
        return {
            'license_key': os.getenv('NEW_RELIC_LICENSE_KEY'),
            'app_name': os.getenv('NEW_RELIC_APP_NAME', 'MediaFetch'),
            'enabled': bool(os.getenv('NEW_RELIC_LICENSE_KEY'))
        }

    def _get_prometheus_config(self) -> Dict[str, Any]:
        """Get Prometheus configuration"""
        return {
            'push_gateway': os.getenv('PROMETHEUS_PUSH_GATEWAY'),
            'job_name': os.getenv('PROMETHEUS_JOB_NAME', 'mediafetch'),
            'enabled': bool(os.getenv('PROMETHEUS_PUSH_GATEWAY'))
        }

    def send_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Send metric to all configured monitoring services"""
        tags = tags or {}

        # DataDog
        if self.monitoring_configs['datadog']['enabled']:
            self._send_datadog_metric(metric_name, value, tags)

        # Prometheus
        if self.monitoring_configs['prometheus']['enabled']:
            self._send_prometheus_metric(metric_name, value, tags)

    def _send_datadog_metric(self, metric_name: str, value: float, tags: Dict[str, str]):
        """Send metric to DataDog"""
        try:
            import datadog

            datadog.initialize(**self.monitoring_configs['datadog'])
            datadog.statsd.gauge(metric_name, value, tags=tags)

        except Exception as e:
            logger.error(f"Failed to send DataDog metric: {e}")

    def _send_prometheus_metric(self, metric_name: str, value: float, tags: Dict[str, str]):
        """Send metric to Prometheus"""
        try:
            from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

            registry = CollectorRegistry()
            gauge = Gauge(metric_name, 'MediaFetch metric', labelnames=list(tags.keys()), registry=registry)
            gauge.labels(**tags).set(value)

            push_to_gateway(
                self.monitoring_configs['prometheus']['push_gateway'],
                job=self.monitoring_configs['prometheus']['job_name'],
                registry=registry
            )

        except Exception as e:
            logger.error(f"Failed to send Prometheus metric: {e}")

    def send_error(self, error_message: str, error_details: Dict[str, Any] = None):
        """Send error to all configured monitoring services"""
        error_details = error_details or {}

        # DataDog
        if self.monitoring_configs['datadog']['enabled']:
            self._send_datadog_error(error_message, error_details)

        # New Relic
        if self.monitoring_configs['new_relic']['enabled']:
            self._send_new_relic_error(error_message, error_details)

    def _send_datadog_error(self, error_message: str, error_details: Dict[str, Any]):
        """Send error to DataDog"""
        try:
            import datadog

            datadog.initialize(**self.monitoring_configs['datadog'])
            datadog.statsd.increment('mediafetch.errors', tags=[f"error:{error_message[:50]}"])

        except Exception as e:
            logger.error(f"Failed to send DataDog error: {e}")

    def _send_new_relic_error(self, error_message: str, error_details: Dict[str, Any]):
        """Send error to New Relic"""
        try:
            import newrelic.agent

            newrelic.agent.record_exception(
                exception=Exception(error_message),
                params=error_details
            )

        except Exception as e:
            logger.error(f"Failed to send New Relic error: {e}")


class ProductionConfigManager:
    """Manages production-specific configurations"""

    def __init__(self):
        self.config_overrides = {}
        self.environment_configs = {
            'production': self._get_production_config(),
            'staging': self._get_staging_config(),
            'development': self._get_development_config()
        }

    def _get_production_config(self) -> Dict[str, Any]:
        """Get production-specific configuration"""
        return {
            'debug': False,
            'testing': False,
            'database_pool_size': 20,
            'cache_ttl': 3600,  # 1 hour
            'rate_limit_per_minute': 1000,
            'monitoring_enabled': True,
            'external_monitoring': True,
            'backup_enabled': True,
            'log_level': 'WARNING'
        }

    def _get_staging_config(self) -> Dict[str, Any]:
        """Get staging-specific configuration"""
        return {
            'debug': False,
            'testing': False,
            'database_pool_size': 10,
            'cache_ttl': 1800,  # 30 minutes
            'rate_limit_per_minute': 500,
            'monitoring_enabled': True,
            'external_monitoring': False,
            'backup_enabled': True,
            'log_level': 'INFO'
        }

    def _get_development_config(self) -> Dict[str, Any]:
        """Get development-specific configuration"""
        return {
            'debug': True,
            'testing': True,
            'database_pool_size': 2,
            'cache_ttl': 300,  # 5 minutes
            'rate_limit_per_minute': 100,
            'monitoring_enabled': False,
            'external_monitoring': False,
            'backup_enabled': False,
            'log_level': 'DEBUG'
        }

    def get_config(self, environment: str = None) -> Dict[str, Any]:
        """Get configuration for specific environment"""
        if environment is None:
            environment = os.getenv('ENVIRONMENT', 'development')

        base_config = self.environment_configs.get(environment, self._get_development_config())

        # Apply overrides
        final_config = {**base_config, **self.config_overrides}

        return final_config

    def set_override(self, key: str, value: Any):
        """Set configuration override"""
        self.config_overrides[key] = value

    def clear_overrides(self):
        """Clear all configuration overrides"""
        self.config_overrides.clear()


# Global instances
_deployment_manager: Optional[DeploymentManager] = None
_monitoring_integration: Optional[MonitoringIntegration] = None
_production_config: Optional[ProductionConfigManager] = None


def get_deployment_manager() -> DeploymentManager:
    """Get global deployment manager"""
    global _deployment_manager

    if _deployment_manager is None:
        _deployment_manager = DeploymentManager()

    return _deployment_manager


def get_monitoring_integration() -> MonitoringIntegration:
    """Get global monitoring integration"""
    global _monitoring_integration

    if _monitoring_integration is None:
        _monitoring_integration = MonitoringIntegration()

    return _monitoring_integration


def get_production_config() -> ProductionConfigManager:
    """Get global production configuration"""
    global _production_config

    if _production_config is None:
        _production_config = ProductionConfigManager()

    return _production_config


def init_production_system():
    """Initialize the complete production system"""
    deployment_manager = get_deployment_manager()
    monitoring_integration = get_monitoring_integration()
    production_config = get_production_config()

    logger.info("Production system initialized")

    return {
        'deployment_manager': deployment_manager,
        'monitoring_integration': monitoring_integration,
        'production_config': production_config
    }


def perform_blue_green_deploy(new_version_path: str, health_check_url: str) -> Dict[str, Any]:
    """Perform blue-green deployment"""
    return get_deployment_manager().blue_green_deployment(new_version_path, health_check_url)


def send_production_metric(name: str, value: float, tags: Dict[str, str] = None):
    """Send metric to production monitoring"""
    get_monitoring_integration().send_metric(name, value, tags)


def report_production_error(error_message: str, error_details: Dict[str, Any] = None):
    """Report error to production monitoring"""
    get_monitoring_integration().send_error(error_message, error_details)
