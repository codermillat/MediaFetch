#!/usr/bin/env python3
"""
Enhanced Instagram monitoring system for MediaFetch bot
Automatically detects new reels and sends them to monitoring users
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
import json
import hashlib

from .instagram_client import InstagramClient
from .media_downloader import MediaDownloader
from .media_processor import MediaProcessor
from .config import Config

logger = logging.getLogger(__name__)

class InstagramMonitor:
    """Enhanced Instagram monitoring with automatic content delivery"""
    
    def __init__(self):
        """Initialize the Instagram monitor"""
        self.config = Config()
        self.instagram_client = InstagramClient()
        self.downloader = MediaDownloader()
        self.processor = MediaProcessor()
        
        # Monitoring state
        self.monitored_accounts: Dict[str, Dict[str, Any]] = {}
        self.user_preferences: Dict[int, Dict[str, Any]] = {}
        self.content_cache: Dict[str, Set[str]] = {}  # account -> set of content hashes
        self.last_check: Dict[str, datetime] = {}
        
        # Monitoring intervals (in seconds)
        self.check_interval = 300  # 5 minutes
        self.is_monitoring = False
        self.monitor_task = None
        
        logger.info("Instagram Monitor initialized")
    
    async def start_monitoring(self):
        """Start the monitoring service"""
        if self.is_monitoring:
            logger.warning("Monitoring already started")
            return
        
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Instagram monitoring started")
    
    async def stop_monitoring(self):
        """Stop the monitoring service"""
        if not self.is_monitoring:
            logger.warning("Monitoring not started")
            return
        
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Instagram monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                await self._check_all_accounts()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _check_all_accounts(self):
        """Check all monitored accounts for new content"""
        if not self.monitored_accounts:
            return
        
        logger.info(f"Checking {len(self.monitored_accounts)} monitored accounts")
        
        for account_username, account_info in self.monitored_accounts.items():
            try:
                await self._check_account(account_username, account_info)
            except Exception as e:
                logger.error(f"Error checking account {account_username}: {e}")
    
    async def _check_account(self, username: str, account_info: Dict[str, Any]):
        """Check a specific account for new content"""
        try:
            # Get recent media from the account
            media = await self.instagram_client.get_user_media(username, limit=10)
            if not media:
                return
            
            # Get stories if user wants them
            stories = []
            if account_info.get('include_stories', False):
                stories = await self.instagram_client.get_stories(username)
            
            # Process new content
            new_content = await self._process_new_content(username, media, stories)
            
            if new_content:
                await self._notify_users(username, new_content)
                
        except Exception as e:
            logger.error(f"Error checking account {username}: {e}")
    
    async def _process_new_content(self, username: str, media: List[Dict], stories: List[Dict]) -> List[Dict]:
        """Process and identify new content"""
        new_content = []
        current_time = datetime.utcnow()
        
        # Initialize content cache for this account
        if username not in self.content_cache:
            self.content_cache[username] = set()
        
        # Process media posts
        for item in media:
            content_hash = self._generate_content_hash(item)
            
            if content_hash not in self.content_cache[username]:
                # This is new content
                self.content_cache[username].add(content_hash)
                new_content.append({
                    'type': 'media',
                    'data': item,
                    'hash': content_hash,
                    'timestamp': current_time
                })
        
        # Process stories
        for story in stories:
            content_hash = self._generate_content_hash(story)
            
            if content_hash not in self.content_cache[username]:
                # This is new content
                self.content_cache[username].add(content_hash)
                new_content.append({
                    'type': 'story',
                    'data': story,
                    'hash': content_hash,
                    'timestamp': current_time
                })
        
        # Keep cache size manageable (last 100 items)
        if len(self.content_cache[username]) > 100:
            # Remove oldest items (this is a simple approach)
            items_to_remove = len(self.content_cache[username]) - 100
            for _ in range(items_to_remove):
                self.content_cache[username].pop()
        
        return new_content
    
    def _generate_content_hash(self, content: Dict) -> str:
        """Generate a unique hash for content"""
        # Create a unique identifier based on content properties
        hash_data = {
            'id': content.get('id', ''),
            'media_type': content.get('media_type', ''),
            'timestamp': content.get('timestamp', ''),
            'permalink': content.get('permalink', '')
        }
        
        hash_string = json.dumps(hash_data, sort_keys=True)
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    async def _notify_users(self, username: str, new_content: List[Dict]):
        """Notify users about new content"""
        if not new_content:
            return
        
        # Find users monitoring this account
        monitoring_users = self._get_users_monitoring_account(username)
        
        for user_id in monitoring_users:
            try:
                await self._send_content_to_user(user_id, username, new_content)
            except Exception as e:
                logger.error(f"Failed to send content to user {user_id}: {e}")
    
    def _get_users_monitoring_account(self, username: str) -> List[int]:
        """Get list of user IDs monitoring a specific account"""
        monitoring_users = []
        
        for user_id, preferences in self.user_preferences.items():
            monitored_accounts = preferences.get('monitored_accounts', [])
            if username in monitored_accounts:
                monitoring_users.append(user_id)
        
        return monitoring_users
    
    async def _send_content_to_user(self, user_id: int, username: str, new_content: List[Dict]):
        """Send new content to a specific user"""
        try:
            # This would integrate with your bot's message sending system
            # For now, we'll log what would be sent
            logger.info(f"Sending {len(new_content)} new content items to user {user_id} from {username}")
            
            for content_item in new_content:
                await self._process_and_send_content(user_id, username, content_item)
                
        except Exception as e:
            logger.error(f"Error sending content to user {user_id}: {e}")
    
    async def _process_and_send_content(self, user_id: int, username: str, content_item: Dict):
        """Process and send individual content item"""
        try:
            content_data = content_item['data']
            content_type = content_item['type']
            
            # Check if user wants this type of content
            if not self._should_send_content_type(user_id, content_type):
                return
            
            # Get media URL
            media_url = content_data.get('media_url') or content_data.get('thumbnail_url')
            if not media_url:
                logger.warning(f"No media URL found for content {content_data.get('id')}")
                return
            
            # Download the media
            download_info = await self.downloader.download_media(media_url)
            if not download_info:
                logger.error(f"Failed to download media from {media_url}")
                return
            
            # Process the media
            processed_file = await self.processor.process_media(
                download_info['file_path'], 
                download_info['file_size']
            )
            
            # Send to user (this would integrate with your bot)
            await self._send_media_to_telegram_user(user_id, username, content_data, processed_file)
            
        except Exception as e:
            logger.error(f"Error processing content for user {user_id}: {e}")
    
    def _should_send_content_type(self, user_id: int, content_type: str) -> bool:
        """Check if user wants to receive this type of content"""
        if user_id not in self.user_preferences:
            return True  # Default to sending everything
        
        preferences = self.user_preferences[user_id]
        content_preferences = preferences.get('content_types', {})
        
        # Default to True if not specified
        return content_preferences.get(content_type, True)
    
    async def _send_media_to_telegram_user(self, user_id: int, username: str, content_data: Dict, file_path: str):
        """Send media to Telegram user (placeholder for bot integration)"""
        # This is a placeholder - in your actual bot, you would:
        # 1. Get the user's chat ID
        # 2. Send the media file
        # 3. Include caption with content info
        
        caption = (
            f"🆕 **New {content_data.get('media_type', 'content')} from @{username}**\n\n"
        )
        
        if content_data.get('caption'):
            caption += f"📝 {content_data.get('caption')[:200]}...\n\n"
        
        caption += (
            f"📅 {content_data.get('timestamp', 'Unknown')}\n"
            f"🔗 [View on Instagram]({content_data.get('permalink', '')})"
        )
        
        logger.info(f"Would send to user {user_id}: {caption}")
        logger.info(f"File: {file_path}")
        
        # TODO: Integrate with your bot's message sending system
        # await bot.send_document(chat_id=user_id, document=open(file_path, 'rb'), caption=caption)
    
    # User management methods
    def add_user_monitoring(self, user_id: int, username: str, preferences: Dict[str, Any] = None):
        """Add a user to monitor a specific account"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {
                'monitored_accounts': [],
                'content_types': {
                    'media': True,
                    'story': True
                },
                'notification_preferences': {
                    'immediate': True,
                    'daily_summary': False
                }
            }
        
        # Add account to user's monitored list
        if username not in self.user_preferences[user_id]['monitored_accounts']:
            self.user_preferences[user_id]['monitored_accounts'].append(username)
        
        # Update preferences if provided
        if preferences:
            self.user_preferences[user_id].update(preferences)
        
        # Add account to global monitoring if not already there
        if username not in self.monitored_accounts:
            self.monitored_accounts[username] = {
                'added_by': user_id,
                'added_at': datetime.utcnow(),
                'include_stories': True,
                'check_interval': self.check_interval
            }
        
        logger.info(f"User {user_id} now monitoring @{username}")
    
    def remove_user_monitoring(self, user_id: int, username: str):
        """Remove a user from monitoring a specific account"""
        if user_id in self.user_preferences:
            if username in self.user_preferences[user_id]['monitored_accounts']:
                self.user_preferences[user_id]['monitored_accounts'].remove(username)
                logger.info(f"User {user_id} stopped monitoring @{username}")
        
        # Check if any other users are monitoring this account
        other_monitors = [
            uid for uid, prefs in self.user_preferences.items()
            if username in prefs.get('monitored_accounts', [])
        ]
        
        # If no users are monitoring, remove from global monitoring
        if not other_monitors and username in self.monitored_accounts:
            del self.monitored_accounts[username]
            logger.info(f"No users monitoring @{username}, removed from global monitoring")
    
    def get_user_monitoring_status(self, user_id: int) -> Dict[str, Any]:
        """Get monitoring status for a specific user"""
        if user_id not in self.user_preferences:
            return {'monitoring': False, 'accounts': []}
        
        return {
            'monitoring': True,
            'accounts': self.user_preferences[user_id]['monitored_accounts'],
            'preferences': self.user_preferences[user_id]
        }
    
    def get_global_monitoring_status(self) -> Dict[str, Any]:
        """Get global monitoring status"""
        return {
            'total_accounts': len(self.monitored_accounts),
            'total_users': len(self.user_preferences),
            'is_monitoring': self.is_monitoring,
            'check_interval': self.check_interval,
            'accounts': list(self.monitored_accounts.keys())
        }
    
    async def force_check_account(self, username: str) -> Dict[str, Any]:
        """Force check a specific account immediately"""
        try:
            if username not in self.monitored_accounts:
                return {'error': f'Account @{username} is not being monitored'}
            
            account_info = self.monitored_accounts[username]
            await self._check_account(username, account_info)
            
            return {
                'success': True,
                'message': f'Forced check completed for @{username}',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Force check failed for {username}: {e}")
            return {'error': str(e)}
    
    def update_user_preferences(self, user_id: int, preferences: Dict[str, Any]):
        """Update user monitoring preferences"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        
        self.user_preferences[user_id].update(preferences)
        logger.info(f"Updated preferences for user {user_id}")
    
    def cleanup_old_content(self, max_age_hours: int = 24):
        """Clean up old content cache entries"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        for username in list(self.content_cache.keys()):
            # This is a simple cleanup - in production you might want more sophisticated logic
            if len(self.content_cache[username]) > 200:
                # Keep only the most recent 200 items
                items_to_remove = len(self.content_cache[username]) - 200
                for _ in range(items_to_remove):
                    self.content_cache[username].pop()
        
        logger.info("Content cache cleanup completed")
