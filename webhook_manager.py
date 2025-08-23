"""
Webhook Manager for MediaFetch
Provides external notifications and alerting for system events
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional, List
import aiohttp
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


class WebhookEvent:
    """Represents a webhook event"""

    def __init__(self, event_type: str, data: Dict[str, Any], severity: str = 'info'):
        self.event_type = event_type
        self.data = data
        self.severity = severity
        self.timestamp = datetime.utcnow().isoformat()
        self.id = f"{event_type}_{int(datetime.utcnow().timestamp())}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'data': self.data,
            'severity': self.severity,
            'timestamp': self.timestamp
        }


class WebhookManager:
    """Manages webhook notifications and external integrations"""

    def __init__(self, max_retries: int = 3, timeout: int = 10):
        self.webhooks: Dict[str, str] = {}
        self.max_retries = max_retries
        self.timeout = timeout
        self._lock = threading.RLock()

        # Event queue for async processing
        self.event_queue: List[WebhookEvent] = []
        self.queue_lock = threading.RLock()

        # Start event processor
        self._processor_thread = threading.Thread(target=self._process_events, daemon=True)
        self._processor_thread.start()

        logger.info("Webhook manager initialized")

    def register_webhook(self, name: str, url: str) -> bool:
        """Register a webhook endpoint"""
        if not self._validate_url(url):
            logger.error(f"Invalid webhook URL: {url}")
            return False

        with self._lock:
            self.webhooks[name] = url
            logger.info(f"Webhook '{name}' registered: {url}")
            return True

    def unregister_webhook(self, name: str) -> bool:
        """Unregister a webhook endpoint"""
        with self._lock:
            if name in self.webhooks:
                del self.webhooks[name]
                logger.info(f"Webhook '{name}' unregistered")
                return True
            return False

    def send_event(self, event_type: str, data: Dict[str, Any], severity: str = 'info'):
        """Send an event to all registered webhooks"""
        event = WebhookEvent(event_type, data, severity)

        with self.queue_lock:
            self.event_queue.append(event)

        logger.info(f"Event queued: {event_type} ({severity})")

    def _process_events(self):
        """Background event processor"""
        while True:
            try:
                # Get events from queue
                events_to_process = []
                with self.queue_lock:
                    if self.event_queue:
                        events_to_process = self.event_queue.copy()
                        self.event_queue.clear()

                # Process events
                for event in events_to_process:
                    asyncio.run(self._send_to_all_webhooks(event))

                # Sleep before next iteration
                threading.Event().wait(1)

            except Exception as e:
                logger.error(f"Event processing error: {e}")
                threading.Event().wait(5)  # Wait longer on error

    async def _send_to_all_webhooks(self, event: WebhookEvent):
        """Send event to all registered webhooks"""
        webhooks_copy = {}
        with self._lock:
            webhooks_copy = self.webhooks.copy()

        for name, url in webhooks_copy.items():
            try:
                await self._send_webhook(url, event)
                logger.debug(f"Event sent to webhook '{name}': {event.event_type}")
            except Exception as e:
                logger.error(f"Failed to send event to webhook '{name}': {e}")

    async def _send_webhook(self, url: str, event: WebhookEvent):
        """Send event to a single webhook endpoint"""
        payload = event.to_dict()

        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json=payload,
                        headers={'Content-Type': 'application/json'},
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status == 200:
                            return  # Success
                        else:
                            logger.warning(f"Webhook returned status {response.status}: {await response.text()}")

            except asyncio.TimeoutError:
                logger.warning(f"Webhook timeout (attempt {attempt + 1}/{self.max_retries})")
            except Exception as e:
                logger.warning(f"Webhook error (attempt {attempt + 1}/{self.max_retries}): {e}")

            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        logger.error(f"Failed to send webhook after {self.max_retries} attempts")

    def _validate_url(self, url: str) -> bool:
        """Validate webhook URL"""
        if not url or not url.startswith(('http://', 'https://')):
            return False

        # Basic URL validation - in production, you might want more sophisticated validation
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return bool(parsed.netloc and parsed.scheme in ['http', 'https'])
        except:
            return False

    def get_registered_webhooks(self) -> Dict[str, str]:
        """Get list of registered webhooks"""
        with self._lock:
            return self.webhooks.copy()

    def get_queue_status(self) -> Dict[str, Any]:
        """Get event queue status"""
        with self.queue_lock:
            return {
                'queued_events': len(self.event_queue),
                'webhooks_count': len(self.webhooks)
            }


# Global webhook manager instance
_webhook_manager: Optional[WebhookManager] = None


def get_webhook_manager() -> WebhookManager:
    """Get the global webhook manager instance"""
    global _webhook_manager

    if _webhook_manager is None:
        _webhook_manager = WebhookManager()

    return _webhook_manager


def alert_critical_error(error_message: str, error_details: Dict[str, Any] = None):
    """Send critical error alert"""
    manager = get_webhook_manager()
    manager.send_event(
        'critical_error',
        {
            'message': error_message,
            'details': error_details or {},
            'service': 'MediaFetch'
        },
        severity='critical'
    )


def alert_system_health(health_data: Dict[str, Any]):
    """Send system health alert"""
    manager = get_webhook_manager()
    manager.send_event(
        'system_health',
        health_data,
        severity='info'
    )


def alert_security_event(event_type: str, event_data: Dict[str, Any]):
    """Send security event alert"""
    manager = get_webhook_manager()
    manager.send_event(
        'security_event',
        {
            'event_type': event_type,
            'event_data': event_data
        },
        severity='warning'
    )


def alert_database_issue(issue_type: str, issue_details: Dict[str, Any]):
    """Send database issue alert"""
    manager = get_webhook_manager()
    manager.send_event(
        'database_issue',
        {
            'issue_type': issue_type,
            'details': issue_details
        },
        severity='error'
    )


def init_webhook_system():
    """Initialize the webhook system with common webhooks"""
    import os

    manager = get_webhook_manager()

    # Register webhooks from environment variables
    webhook_configs = {
        'health': os.getenv('HEALTH_WEBHOOK_URL'),
        'error': os.getenv('ERROR_WEBHOOK_URL'),
        'security': os.getenv('SECURITY_WEBHOOK_URL'),
        'database': os.getenv('DATABASE_WEBHOOK_URL')
    }

    registered = 0
    for name, url in webhook_configs.items():
        if url:
            if manager.register_webhook(name, url):
                registered += 1

    if registered > 0:
        logger.info(f"Webhook system initialized with {registered} webhooks")
    else:
        logger.info("Webhook system initialized (no webhooks configured)")


def get_webhook_health() -> Dict[str, Any]:
    """Get webhook system health"""
    manager = get_webhook_manager()

    return {
        'healthy': True,
        'status': 'Webhook system is operational',
        'registered_webhooks': manager.get_registered_webhooks(),
        'queue_status': manager.get_queue_status()
    }


# Slack webhook integration
class SlackWebhook:
    """Slack webhook integration"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.manager = get_webhook_manager()

    def send_message(self, message: str, channel: str = None, username: str = 'MediaFetch'):
        """Send message to Slack"""
        payload = {
            'text': message,
            'username': username
        }

        if channel:
            payload['channel'] = channel

        try:
            # This would integrate with the webhook manager
            # For now, just log
            logger.info(f"Slack message: {message}")
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")


# Discord webhook integration
class DiscordWebhook:
    """Discord webhook integration"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.manager = get_webhook_manager()

    def send_embed(self, title: str, description: str, color: int = 0xff0000):
        """Send embed message to Discord"""
        payload = {
            'embeds': [{
                'title': title,
                'description': description,
                'color': color,
                'timestamp': datetime.utcnow().isoformat()
            }]
        }

        try:
            # This would integrate with the webhook manager
            # For now, just log
            logger.info(f"Discord embed: {title} - {description}")
        except Exception as e:
            logger.error(f"Failed to send Discord embed: {e}")
