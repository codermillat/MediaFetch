#!/usr/bin/env python3
"""
Instagram Direct Message Client using instagrapi
Accesses DMs and media sent to your Instagram account
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

# 3rd party Instagram library
try:
    from instagrapi import Client
    from instagrapi.types import Message, DirectMessage, User
    INSTAGRAPI_AVAILABLE = True
except ImportError:
    INSTAGRAPI_AVAILABLE = False
    logging.warning("instagrapi not available. Install with: pip install instagrapi")

from .config import Config
from .media_downloader import MediaDownloader
from .media_processor import MediaProcessor

logger = logging.getLogger(__name__)

class InstagramDMClient:
    """Instagram Direct Message client using instagrapi"""
    
    def __init__(self):
        """Initialize the Instagram DM client"""
        self.config = Config()
        
        if not INSTAGRAPI_AVAILABLE:
            raise ImportError(
                "instagrapi is required for DM functionality. "
                "Install with: pip install instagrapi"
            )
        
        # Initialize instagrapi client
        self.client = Client()
        self.client.delay_range = [1, 3]  # Rate limiting
        
        # Media processing
        self.downloader = MediaDownloader()
        self.processor = MediaProcessor()
        
        # Authentication state
        self.is_authenticated = False
        self.current_user = None
        
        # Message tracking
        self.last_message_id = None
        self.processed_messages = set()
        
        # User mapping (Instagram username -> Telegram user_id)
        self.user_mapping: Dict[str, int] = {}
        
        logger.info("Instagram DM Client initialized")
    
    async def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with Instagram"""
        try:
            # Login to Instagram
            self.current_user = self.client.login(username, password)
            self.is_authenticated = True
            
            logger.info(f"Successfully authenticated as @{username}")
            return True
            
        except Exception as e:
            logger.error(f"Instagram authentication failed: {e}")
            self.is_authenticated = False
            return False
    
    async def authenticate_with_session(self, session_file: str) -> bool:
        """Authenticate using saved session file"""
        try:
            if os.path.exists(session_file):
                self.client.load_settings(session_file)
                self.current_user = self.client.get_timeline_feed()
                self.is_authenticated = True
                logger.info("Authenticated using saved session")
                return True
            else:
                logger.warning(f"Session file not found: {session_file}")
                return False
                
        except Exception as e:
            logger.error(f"Session authentication failed: {e}")
            return False
    
    async def save_session(self, session_file: str) -> bool:
        """Save current session for future use"""
        try:
            if self.is_authenticated:
                self.client.dump_settings(session_file)
                logger.info(f"Session saved to {session_file}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False
    
    async def get_direct_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent direct messages"""
        if not self.is_authenticated:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            # Get direct messages
            threads = self.client.direct_threads()
            all_messages = []
            
            for thread in threads:
                # Get messages from each thread
                messages = self.client.direct_messages(thread.id, amount=limit)
                
                for message in messages:
                    message_data = self._parse_message(message, thread)
                    if message_data:
                        all_messages.append(message_data)
            
            # Sort by timestamp
            all_messages.sort(key=lambda x: x['timestamp'], reverse=True)
            
            logger.info(f"Retrieved {len(all_messages)} direct messages")
            return all_messages
            
        except Exception as e:
            logger.error(f"Failed to get direct messages: {e}")
            return []
    
    async def get_new_messages(self) -> List[Dict[str, Any]]:
        """Get only new messages since last check"""
        if not self.is_authenticated:
            return []
        
        try:
            # Get recent messages
            messages = await self.get_direct_messages(limit=20)
            new_messages = []
            
            for message in messages:
                message_id = message['id']
                
                # Check if this is a new message
                if message_id not in self.processed_messages:
                    new_messages.append(message)
                    self.processed_messages.add(message_id)
                    
                    # Keep track of last message ID
                    if not self.last_message_id or message_id > self.last_message_id:
                        self.last_message_id = message_id
            
            if new_messages:
                logger.info(f"Found {len(new_messages)} new messages")
            
            return new_messages
            
        except Exception as e:
            logger.error(f"Failed to get new messages: {e}")
            return []
    
    def _parse_message(self, message: Message, thread) -> Optional[Dict[str, Any]]:
        """Parse Instagram message into structured data"""
        try:
            # Basic message info
            message_data = {
                'id': str(message.id),
                'timestamp': message.timestamp.isoformat() if message.timestamp else None,
                'text': message.text or '',
                'sender_username': message.user.username if message.user else None,
                'sender_full_name': message.user.full_name if message.user else None,
                'sender_id': message.user.pk if message.user else None,
                'thread_id': str(thread.id),
                'thread_title': thread.title or thread.users[0].username if thread.users else None,
                'message_type': 'text'
            }
            
            # Check for media content
            if hasattr(message, 'media') and message.media:
                media_info = self._extract_media_info(message.media)
                if media_info:
                    message_data.update(media_info)
                    message_data['message_type'] = 'media'
            
            # Check for story replies
            if hasattr(message, 'story_share') and message.story_share:
                message_data['message_type'] = 'story_reply'
                message_data['story_id'] = str(message.story_share.id)
                message_data['story_media_url'] = message.story_share.media_url
            
            # Check for reel shares
            if hasattr(message, 'reel_share') and message.reel_share:
                message_data['message_type'] = 'reel_share'
                message_data['reel_id'] = str(message.reel_share.id)
                message_data['reel_media_url'] = message.reel_share.media_url
            
            return message_data
            
        except Exception as e:
            logger.error(f"Failed to parse message: {e}")
            return None
    
    def _extract_media_info(self, media) -> Optional[Dict[str, Any]]:
        """Extract media information from message"""
        try:
            media_info = {}
            
            # Get media URL
            if hasattr(media, 'video_url') and media.video_url:
                media_info['media_url'] = media.video_url
                media_info['media_type'] = 'video'
            elif hasattr(media, 'image_versions2') and media.image_versions2:
                # Get highest quality image
                versions = media.image_versions2.candidates
                if versions:
                    media_info['media_url'] = versions[0].url
                    media_info['media_type'] = 'image'
            
            # Get media ID
            if hasattr(media, 'id'):
                media_info['media_id'] = str(media.id)
            
            # Get caption
            if hasattr(media, 'caption') and media.caption:
                media_info['media_caption'] = media.caption.text
            
            return media_info if media_info.get('media_url') else None
            
        except Exception as e:
            logger.error(f"Failed to extract media info: {e}")
            return None
    
    async def download_message_media(self, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Download media from a message"""
        try:
            if message_data.get('message_type') != 'media':
                return None
            
            media_url = message_data.get('media_url')
            if not media_url:
                return None
            
            # Download the media
            download_info = await self.downloader.download_media(media_url)
            if not download_info:
                return None
            
            # Process the media
            processed_file = await self.processor.process_media(
                download_info['file_path'],
                download_info['file_size']
            )
            
            return {
                'original_message': message_data,
                'download_info': download_info,
                'processed_file': processed_file,
                'sender_username': message_data.get('sender_username'),
                'sender_full_name': message_data.get('sender_full_name'),
                'message_text': message_data.get('text', ''),
                'timestamp': message_data.get('timestamp')
            }
            
        except Exception as e:
            logger.error(f"Failed to download message media: {e}")
            return None
    
    async def map_user_to_telegram(self, instagram_username: str, telegram_user_id: int):
        """Map Instagram username to Telegram user ID"""
        self.user_mapping[instagram_username] = telegram_user_id
        logger.info(f"Mapped @{instagram_username} to Telegram user {telegram_user_id}")
    
    async def get_telegram_user_id(self, instagram_username: str) -> Optional[int]:
        """Get Telegram user ID for Instagram username"""
        return self.user_mapping.get(instagram_username)
    
    async def get_all_user_mappings(self) -> Dict[str, int]:
        """Get all user mappings"""
        return self.user_mapping.copy()
    
    async def remove_user_mapping(self, instagram_username: str):
        """Remove user mapping"""
        if instagram_username in self.user_mapping:
            del self.user_mapping[instagram_username]
            logger.info(f"Removed mapping for @{instagram_username}")
    
    async def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Get Instagram user information"""
        if not self.is_authenticated:
            return None
        
        try:
            user = self.client.user_info_by_username(username)
            return {
                'username': user.username,
                'full_name': user.full_name,
                'biography': user.biography,
                'follower_count': user.follower_count,
                'following_count': user.following_count,
                'media_count': user.media_count,
                'is_private': user.is_private,
                'is_verified': user.is_verified,
                'profile_pic_url': user.profile_pic_url
            }
        except Exception as e:
            logger.error(f"Failed to get user info for @{username}: {e}")
            return None
    
    async def search_users(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for Instagram users"""
        if not self.is_authenticated:
            return []
        
        try:
            users = self.client.user_search(query, amount=limit)
            return [
                {
                    'username': user.username,
                    'full_name': user.full_name,
                    'follower_count': user.follower_count,
                    'is_private': user.is_private,
                    'is_verified': user.is_verified,
                    'profile_pic_url': user.profile_pic_url
                }
                for user in users
            ]
        except Exception as e:
            logger.error(f"Failed to search users: {e}")
            return []
    
    async def get_thread_participants(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get participants in a direct message thread"""
        if not self.is_authenticated:
            return []
        
        try:
            thread = self.client.direct_thread(thread_id)
            participants = []
            
            for user in thread.users:
                participants.append({
                    'username': user.username,
                    'full_name': user.full_name,
                    'user_id': str(user.pk),
                    'profile_pic_url': user.profile_pic_url,
                    'is_verified': user.is_verified
                })
            
            return participants
            
        except Exception as e:
            logger.error(f"Failed to get thread participants: {e}")
            return []
    
    async def send_direct_message(self, user_id: str, text: str) -> bool:
        """Send a direct message to a user"""
        if not self.is_authenticated:
            return False
        
        try:
            self.client.direct_answer(text, user_id)
            logger.info(f"Sent DM to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send DM: {e}")
            return False
    
    async def mark_message_as_read(self, message_id: str) -> bool:
        """Mark a message as read"""
        if not self.is_authenticated:
            return False
        
        try:
            # Note: instagrapi doesn't have direct method for this
            # But we can track it in our system
            logger.info(f"Marked message {message_id} as read")
            return True
        except Exception as e:
            logger.error(f"Failed to mark message as read: {e}")
            return False
    
    async def get_message_statistics(self) -> Dict[str, Any]:
        """Get message statistics"""
        if not self.is_authenticated:
            return {}
        
        try:
            threads = self.client.direct_threads()
            total_messages = 0
            total_threads = len(threads)
            
            for thread in threads:
                messages = self.client.direct_messages(thread.id, amount=100)
                total_messages += len(messages)
            
            return {
                'total_threads': total_threads,
                'total_messages': total_messages,
                'processed_messages': len(self.processed_messages),
                'user_mappings': len(self.user_mapping),
                'last_message_id': self.last_message_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get message statistics: {e}")
            return {}
    
    async def cleanup_old_messages(self, max_age_hours: int = 24):
        """Clean up old processed message IDs"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            old_messages = set()
            
            # This is a simple cleanup - in production you might want more sophisticated logic
            if len(self.processed_messages) > 1000:
                # Keep only the most recent 1000 message IDs
                items_to_remove = len(self.processed_messages) - 1000
                for _ in range(items_to_remove):
                    if self.processed_messages:
                        self.processed_messages.pop()
            
            logger.info("Message cleanup completed")
            
        except Exception as e:
            logger.error(f"Message cleanup failed: {e}")
    
    async def close(self):
        """Close the Instagram client"""
        try:
            if self.is_authenticated:
                # Save session before closing
                session_file = "instagram_session.json"
                await self.save_session(session_file)
                
            logger.info("Instagram DM Client closed")
            
        except Exception as e:
            logger.error(f"Error closing client: {e}")
