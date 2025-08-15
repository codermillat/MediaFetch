#!/usr/bin/env python3
"""
Enhanced Instagram DM monitoring system
Automatically detects when someone sends you content and delivers it to their Telegram
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
import json
import hashlib

from .instagram_dm_client import InstagramDMClient
from .config import Config

logger = logging.getLogger(__name__)

class InstagramDMMonitor:
    """Instagram Direct Message monitoring with automatic content delivery"""
    
    def __init__(self):
        """Initialize the Instagram DM monitor"""
        self.config = Config()
        self.dm_client = InstagramDMClient()
        
        # Monitoring state
        self.is_monitoring = False
        self.monitor_task = None
        self.check_interval = 60  # Check every 1 minute for DMs
        
        # User mapping cache
        self.telegram_to_instagram: Dict[int, str] = {}  # telegram_id -> instagram_username
        self.instagram_to_telegram: Dict[str, int] = {}  # instagram_username -> telegram_id
        
        # Message tracking
        self.processed_messages: Set[str] = set()
        self.last_check_time = None
        
        # Content delivery preferences
        self.delivery_preferences: Dict[int, Dict[str, Any]] = {}
        
        logger.info("Instagram DM Monitor initialized")
    
    async def start_monitoring(self, instagram_username: str, instagram_password: str):
        """Start monitoring Instagram DMs"""
        try:
            # Authenticate with Instagram
            auth_success = await self.dm_client.authenticate(instagram_username, instagram_password)
            if not auth_success:
                raise Exception("Failed to authenticate with Instagram")
            
            # Start monitoring loop
            self.is_monitoring = True
            self.monitor_task = asyncio.create_task(self._monitoring_loop())
            
            logger.info(f"Instagram DM monitoring started for @{instagram_username}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start DM monitoring: {e}")
            return False
    
    async def stop_monitoring(self):
        """Stop monitoring Instagram DMs"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        # Close Instagram client
        await self.dm_client.close()
        logger.info("Instagram DM monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop for DMs"""
        while self.is_monitoring:
            try:
                await self._check_new_dms()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"DM monitoring loop error: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds on error
    
    async def _check_new_dms(self):
        """Check for new direct messages"""
        try:
            new_messages = await self.dm_client.get_new_messages()
            
            if new_messages:
                logger.info(f"Found {len(new_messages)} new DM messages")
                await self._process_new_messages(new_messages)
            
            self.last_check_time = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Failed to check new DMs: {e}")
    
    async def _process_new_messages(self, messages: List[Dict[str, Any]]):
        """Process new DM messages and deliver content"""
        for message in messages:
            try:
                await self._process_single_message(message)
            except Exception as e:
                logger.error(f"Failed to process message {message.get('id')}: {e}")
    
    async def _process_single_message(self, message: Dict[str, Any]):
        """Process a single DM message"""
        message_id = message.get('id')
        sender_username = message.get('sender_username')
        message_type = message.get('message_type')
        
        if not sender_username:
            logger.warning(f"Message {message_id} has no sender username")
            return
        
        # Check if we have a mapping for this Instagram user
        telegram_user_id = await self.dm_client.get_telegram_user_id(sender_username)
        
        if not telegram_user_id:
            logger.info(f"No Telegram mapping found for @{sender_username}")
            return
        
        # Check if user wants this type of content
        if not self._should_deliver_content(telegram_user_id, message_type):
            logger.info(f"User {telegram_user_id} doesn't want {message_type} content")
            return
        
        # Process the message based on type
        if message_type == 'media':
            await self._process_media_message(message, telegram_user_id, sender_username)
        elif message_type == 'reel_share':
            await self._process_reel_share(message, telegram_user_id, sender_username)
        elif message_type == 'story_reply':
            await self._process_story_reply(message, telegram_user_id, sender_username)
        else:
            # Text message or other type
            await self._process_text_message(message, telegram_user_id, sender_username)
    
    async def _process_media_message(self, message: Dict[str, Any], telegram_user_id: int, sender_username: str):
        """Process media message (photo/video)"""
        try:
            # Download and process the media
            media_info = await self.dm_client.download_message_media(message)
            
            if not media_info:
                logger.warning(f"Failed to download media from message {message.get('id')}")
                return
            
            # Prepare delivery info
            delivery_info = {
                'type': 'media_delivery',
                'instagram_username': sender_username,
                'message_id': message.get('id'),
                'media_type': media_info.get('download_info', {}).get('media_type', 'unknown'),
                'file_path': media_info.get('processed_file'),
                'caption': message.get('text', ''),
                'timestamp': message.get('timestamp'),
                'sender_full_name': message.get('sender_full_name', sender_username)
            }
            
            # Deliver to Telegram user
            await self._deliver_to_telegram_user(telegram_user_id, delivery_info)
            
            logger.info(f"Delivered media message from @{sender_username} to Telegram user {telegram_user_id}")
            
        except Exception as e:
            logger.error(f"Failed to process media message: {e}")
    
    async def _process_reel_share(self, message: Dict[str, Any], telegram_user_id: int, sender_username: str):
        """Process reel share message"""
        try:
            reel_url = message.get('reel_media_url')
            if not reel_url:
                logger.warning(f"No reel URL in message {message.get('id')}")
                return
            
            # Download the reel
            download_info = await self.dm_client.downloader.download_media(reel_url)
            if not download_info:
                logger.warning(f"Failed to download reel from {reel_url}")
                return
            
            # Process the media
            processed_file = await self.dm_client.processor.process_media(
                download_info['file_path'],
                download_info['file_size']
            )
            
            # Prepare delivery info
            delivery_info = {
                'type': 'reel_delivery',
                'instagram_username': sender_username,
                'message_id': message.get('id'),
                'media_type': 'reel',
                'file_path': processed_file,
                'caption': message.get('text', ''),
                'timestamp': message.get('timestamp'),
                'sender_full_name': message.get('sender_full_name', sender_username),
                'reel_id': message.get('reel_id')
            }
            
            # Deliver to Telegram user
            await self._deliver_to_telegram_user(telegram_user_id, delivery_info)
            
            logger.info(f"Delivered reel from @{sender_username} to Telegram user {telegram_user_id}")
            
        except Exception as e:
            logger.error(f"Failed to process reel share: {e}")
    
    async def _process_story_reply(self, message: Dict[str, Any], telegram_user_id: int, sender_username: str):
        """Process story reply message"""
        try:
            story_url = message.get('story_media_url')
            if not story_url:
                logger.warning(f"No story URL in message {message.get('id')}")
                return
            
            # Download the story
            download_info = await self.dm_client.downloader.download_media(story_url)
            if not download_info:
                logger.warning(f"Failed to download story from {story_url}")
                return
            
            # Process the media
            processed_file = await self.dm_client.processor.process_media(
                download_info['file_path'],
                download_info['file_size']
            )
            
            # Prepare delivery info
            delivery_info = {
                'type': 'story_delivery',
                'instagram_username': sender_username,
                'message_id': message.get('id'),
                'media_type': 'story',
                'file_path': processed_file,
                'caption': message.get('text', ''),
                'timestamp': message.get('timestamp'),
                'sender_full_name': message.get('sender_full_name', sender_username),
                'story_id': message.get('story_id')
            }
            
            # Deliver to Telegram user
            await self._deliver_to_telegram_user(telegram_user_id, delivery_info)
            
            logger.info(f"Delivered story reply from @{sender_username} to Telegram user {telegram_user_id}")
            
        except Exception as e:
            logger.error(f"Failed to process story reply: {e}")
    
    async def _process_text_message(self, message: Dict[str, Any], telegram_user_id: int, sender_username: str):
        """Process text message"""
        try:
            # Prepare delivery info
            delivery_info = {
                'type': 'text_delivery',
                'instagram_username': sender_username,
                'message_id': message.get('id'),
                'text': message.get('text', ''),
                'timestamp': message.get('timestamp'),
                'sender_full_name': message.get('sender_full_name', sender_username)
            }
            
            # Deliver to Telegram user
            await self._deliver_to_telegram_user(telegram_user_id, delivery_info)
            
            logger.info(f"Delivered text message from @{sender_username} to Telegram user {telegram_user_id}")
            
        except Exception as e:
            logger.error(f"Failed to process text message: {e}")
    
    async def _deliver_to_telegram_user(self, telegram_user_id: int, delivery_info: Dict[str, Any]):
        """Deliver content to Telegram user (placeholder for bot integration)"""
        try:
            # This is a placeholder - in your actual bot, you would:
            # 1. Get the bot instance
            # 2. Send the content to the user
            # 3. Include all the delivery information
            
            content_type = delivery_info.get('type', 'unknown')
            instagram_username = delivery_info.get('instagram_username', 'unknown')
            
            # Log what would be delivered
            logger.info(f"Would deliver {content_type} to Telegram user {telegram_user_id}")
            logger.info(f"Content from @{instagram_username}: {delivery_info}")
            
            # TODO: Integrate with your bot's message sending system
            # Example:
            # if content_type == 'media_delivery':
            #     await bot.send_document(
            #         chat_id=telegram_user_id,
            #         document=open(delivery_info['file_path'], 'rb'),
            #         caption=self._format_delivery_caption(delivery_info)
            #     )
            # elif content_type == 'text_delivery':
            #     await bot.send_message(
            #         chat_id=telegram_user_id,
            #         text=self._format_delivery_text(delivery_info)
            #     )
            
        except Exception as e:
            logger.error(f"Failed to deliver to Telegram user {telegram_user_id}: {e}")
    
    def _format_delivery_caption(self, delivery_info: Dict[str, Any]) -> str:
        """Format caption for media delivery"""
        instagram_username = delivery_info.get('instagram_username', 'unknown')
        sender_name = delivery_info.get('sender_full_name', instagram_username)
        caption = delivery_info.get('caption', '')
        timestamp = delivery_info.get('timestamp', 'Unknown')
        
        caption_text = f"📱 **Content from @{instagram_username}**\n\n"
        
        if caption:
            caption_text += f"💬 {caption}\n\n"
        
        caption_text += f"👤 **Sender:** {sender_name}\n"
        caption_text += f"📅 **Time:** {timestamp}\n"
        caption_text += f"🔗 **Instagram:** @{instagram_username}"
        
        return caption_text
    
    def _format_delivery_text(self, delivery_info: Dict[str, Any]) -> str:
        """Format text for text message delivery"""
        instagram_username = delivery_info.get('instagram_username', 'unknown')
        sender_name = delivery_info.get('sender_full_name', instagram_username)
        text = delivery_info.get('text', '')
        timestamp = delivery_info.get('timestamp', 'Unknown')
        
        message_text = f"💬 **New DM from @{instagram_username}**\n\n"
        message_text += f"📝 **Message:**\n{text}\n\n"
        message_text += f"👤 **Sender:** {sender_name}\n"
        message_text += f"📅 **Time:** {timestamp}\n"
        message_text += f"🔗 **Instagram:** @{instagram_username}"
        
        return message_text
    
    # User mapping methods
    async def map_user(self, telegram_user_id: int, instagram_username: str):
        """Map Telegram user to Instagram username"""
        try:
            # Add to our mapping
            self.telegram_to_instagram[telegram_user_id] = instagram_username
            self.instagram_to_telegram[instagram_username] = telegram_user_id
            
            # Add to Instagram client mapping
            await self.dm_client.map_user_to_telegram(instagram_username, telegram_user_id)
            
            logger.info(f"Mapped Telegram user {telegram_user_id} to @{instagram_username}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to map user: {e}")
            return False
    
    async def unmap_user(self, telegram_user_id: int):
        """Remove user mapping"""
        try:
            instagram_username = self.telegram_to_instagram.get(telegram_user_id)
            
            if instagram_username:
                # Remove from our mappings
                del self.telegram_to_instagram[telegram_user_id]
                del self.instagram_to_telegram[instagram_username]
                
                # Remove from Instagram client
                await self.dm_client.remove_user_mapping(instagram_username)
                
                logger.info(f"Unmapped Telegram user {telegram_user_id} from @{instagram_username}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to unmap user: {e}")
            return False
    
    async def get_user_mapping(self, telegram_user_id: int) -> Optional[str]:
        """Get Instagram username for Telegram user"""
        return self.telegram_to_instagram.get(telegram_user_id)
    
    async def get_telegram_user(self, instagram_username: str) -> Optional[int]:
        """Get Telegram user ID for Instagram username"""
        return self.instagram_to_telegram.get(instagram_username)
    
    async def get_all_mappings(self) -> Dict[int, str]:
        """Get all user mappings"""
        return self.telegram_to_instagram.copy()
    
    # Content delivery preferences
    def set_delivery_preferences(self, telegram_user_id: int, preferences: Dict[str, Any]):
        """Set content delivery preferences for a user"""
        self.delivery_preferences[telegram_user_id] = preferences
        logger.info(f"Set delivery preferences for user {telegram_user_id}")
    
    def get_delivery_preferences(self, telegram_user_id: int) -> Dict[str, Any]:
        """Get content delivery preferences for a user"""
        return self.delivery_preferences.get(telegram_user_id, {
            'media': True,
            'reels': True,
            'stories': True,
            'text': True,
            'notifications': True
        })
    
    def _should_deliver_content(self, telegram_user_id: int, content_type: str) -> bool:
        """Check if content should be delivered to user"""
        preferences = self.get_delivery_preferences(telegram_user_id)
        
        if content_type == 'media':
            return preferences.get('media', True)
        elif content_type == 'reel_share':
            return preferences.get('reels', True)
        elif content_type == 'story_reply':
            return preferences.get('stories', True)
        elif content_type == 'text':
            return preferences.get('text', True)
        
        return True
    
    # Monitoring status and control
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        try:
            stats = await self.dm_client.get_message_statistics()
            
            return {
                'is_monitoring': self.is_monitoring,
                'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
                'check_interval': self.check_interval,
                'user_mappings': len(self.telegram_to_instagram),
                'instagram_stats': stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get monitoring status: {e}")
            return {
                'is_monitoring': self.is_monitoring,
                'error': str(e)
            }
    
    async def force_check_dms(self) -> Dict[str, Any]:
        """Force check for new DMs immediately"""
        try:
            if not self.is_monitoring:
                return {'error': 'Monitoring not started'}
            
            await self._check_new_dms()
            
            return {
                'success': True,
                'message': 'Force check completed',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Force check failed: {e}")
            return {'error': str(e)}
    
    async def cleanup_old_data(self, max_age_hours: int = 24):
        """Clean up old data"""
        try:
            # Clean up Instagram client
            await self.dm_client.cleanup_old_messages(max_age_hours)
            
            # Clean up our tracking data
            if len(self.processed_messages) > 1000:
                items_to_remove = len(self.processed_messages) - 1000
                for _ in range(items_to_remove):
                    if self.processed_messages:
                        self.processed_messages.pop()
            
            logger.info("DM monitor cleanup completed")
            
        except Exception as e:
            logger.error(f"DM monitor cleanup failed: {e}")
    
    async def close(self):
        """Close the DM monitor"""
        await self.stop_monitoring()
        logger.info("Instagram DM Monitor closed")
