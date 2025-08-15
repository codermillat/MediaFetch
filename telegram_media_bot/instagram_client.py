#!/usr/bin/env python3
"""
Instagram client for MediaFetch bot
Handles fetching messages, posts, and stories from Instagram accounts
"""

import os
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

from .config import Config
from .utils import validate_url, extract_platform

logger = logging.getLogger(__name__)

class InstagramClient:
    """Instagram API client for fetching messages and content"""
    
    def __init__(self):
        """Initialize Instagram client"""
        self.config = Config()
        self.access_token = self.config.get_instagram_token()
        self.base_url = "https://graph.instagram.com/v12.0"
        
        if not self.access_token:
            logger.warning("Instagram access token not configured")
        
        self.session = None
        self.last_fetch = {}
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes cache
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """Make authenticated request to Instagram API"""
        if not self.access_token:
            logger.error("Instagram access token not available")
            return None
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            # Add access token to params
            if params is None:
                params = {}
            params['access_token'] = self.access_token
            
            url = f"{self.base_url}/{endpoint}"
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"Instagram API request failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Instagram API request error: {e}")
            return None
    
    async def get_user_profile(self, user_id: str = "me") -> Optional[Dict]:
        """Get Instagram user profile information"""
        try:
            endpoint = f"{user_id}"
            params = {
                'fields': 'id,username,account_type,media_count'
            }
            
            data = await self._make_request(endpoint, params)
            if data and 'id' in data:
                logger.info(f"Fetched profile for user: {data.get('username', 'Unknown')}")
                return data
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            return None
    
    async def get_user_media(self, user_id: str = "me", limit: int = 10) -> List[Dict]:
        """Get user's media posts"""
        try:
            endpoint = f"{user_id}/media"
            params = {
                'fields': 'id,caption,media_type,media_url,thumbnail_url,permalink,timestamp',
                'limit': limit
            }
            
            data = await self._make_request(endpoint, params)
            if data and 'data' in data:
                media_items = data['data']
                logger.info(f"Fetched {len(media_items)} media items")
                return media_items
            return []
            
        except Exception as e:
            logger.error(f"Failed to get user media: {e}")
            return []
    
    async def get_media_comments(self, media_id: str) -> List[Dict]:
        """Get comments for a specific media post"""
        try:
            endpoint = f"{media_id}/comments"
            params = {
                'fields': 'id,text,username,timestamp',
                'limit': 100
            }
            
            data = await self._make_request(endpoint, params)
            if data and 'data' in data:
                comments = data['data']
                logger.info(f"Fetched {len(comments)} comments for media {media_id}")
                return comments
            return []
            
        except Exception as e:
            logger.error(f"Failed to get media comments: {e}")
            return []
    
    async def get_stories(self, user_id: str = "me") -> List[Dict]:
        """Get user's stories"""
        try:
            endpoint = f"{user_id}/stories"
            params = {
                'fields': 'id,media_type,media_url,permalink,timestamp',
                'limit': 50
            }
            
            data = await self._make_request(endpoint, params)
            if data and 'data' in data:
                stories = data['data']
                logger.info(f"Fetched {len(stories)} stories")
                return stories
            return []
            
        except Exception as e:
            logger.error(f"Failed to get stories: {e}")
            return []
    
    async def search_hashtag(self, hashtag: str, limit: int = 20) -> List[Dict]:
        """Search for posts with specific hashtag"""
        try:
            # Note: This requires different permissions and may not be available
            endpoint = f"ig_hashtag_search"
            params = {
                'q': hashtag,
                'limit': limit
            }
            
            data = await self._make_request(endpoint, params)
            if data and 'data' in data:
                posts = data['data']
                logger.info(f"Found {len(posts)} posts with hashtag #{hashtag}")
                return posts
            return []
            
        except Exception as e:
            logger.error(f"Failed to search hashtag: {e}")
            return []
    
    async def get_mentions(self, user_id: str = "me", limit: int = 20) -> List[Dict]:
        """Get posts where user is mentioned"""
        try:
            # This would require additional permissions
            endpoint = f"{user_id}/tags"
            params = {
                'fields': 'id,caption,media_type,media_url,permalink,timestamp',
                'limit': limit
            }
            
            data = await self._make_request(endpoint, params)
            if data and 'data' in data:
                mentions = data['data']
                logger.info(f"Found {len(mentions)} posts mentioning user")
                return mentions
            return []
            
        except Exception as e:
            logger.error(f"Failed to get mentions: {e}")
            return []
    
    async def monitor_account(self, account_username: str, check_interval: int = 300) -> Dict[str, Any]:
        """Monitor an Instagram account for new content"""
        try:
            # Get account info
            profile = await self.get_user_profile(account_username)
            if not profile:
                return {'error': 'Account not found or inaccessible'}
            
            # Get recent media
            media = await self.get_user_media(account_username, limit=5)
            
            # Get stories
            stories = await self.get_stories(account_username)
            
            # Check for new content since last fetch
            last_fetch_key = f"last_fetch_{account_username}"
            last_fetch_time = self.last_fetch.get(last_fetch_key)
            
            new_content = []
            if last_fetch_time:
                for item in media:
                    item_time = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
                    if item_time > last_fetch_time:
                        new_content.append(item)
            
            # Update last fetch time
            self.last_fetch[last_fetch_key] = datetime.utcnow()
            
            return {
                'account': profile,
                'recent_media': media,
                'stories': stories,
                'new_content': new_content,
                'last_fetch': last_fetch_time.isoformat() if last_fetch_time else None
            }
            
        except Exception as e:
            logger.error(f"Failed to monitor account {account_username}: {e}")
            return {'error': str(e)}
    
    async def fetch_direct_messages(self) -> List[Dict]:
        """Fetch direct messages (requires additional permissions)"""
        try:
            # Note: Direct messages require special permissions and may not be available
            # through the Basic Display API
            logger.warning("Direct message fetching may not be available with current permissions")
            return []
            
        except Exception as e:
            logger.error(f"Failed to fetch direct messages: {e}")
            return []
    
    def extract_media_urls(self, content: List[Dict]) -> List[str]:
        """Extract media URLs from Instagram content"""
        media_urls = []
        
        for item in content:
            if 'media_url' in item and item['media_url']:
                media_urls.append(item['media_url'])
            elif 'thumbnail_url' in item and item['thumbnail_url']:
                media_urls.append(item['thumbnail_url'])
        
        return media_urls
    
    def format_content_summary(self, content: List[Dict]) -> str:
        """Format content summary for display"""
        if not content:
            return "No content found"
        
        summary = f"Found {len(content)} items:\n\n"
        
        for i, item in enumerate(content[:5], 1):  # Show first 5 items
            media_type = item.get('media_type', 'Unknown')
            timestamp = item.get('timestamp', 'Unknown')
            
            if 'caption' in item and item['caption']:
                caption = item['caption'][:100] + "..." if len(item['caption']) > 100 else item['caption']
            else:
                caption = "No caption"
            
            summary += f"{i}. **{media_type.title()}** - {caption}\n"
            summary += f"   📅 {timestamp}\n"
            
            if 'permalink' in item:
                summary += f"   🔗 [View on Instagram]({item['permalink']})\n"
            summary += "\n"
        
        if len(content) > 5:
            summary += f"... and {len(content) - 5} more items"
        
        return summary
    
    async def get_account_insights(self, account_username: str) -> Dict[str, Any]:
        """Get account insights and statistics"""
        try:
            profile = await self.get_user_profile(account_username)
            if not profile:
                return {'error': 'Account not accessible'}
            
            media = await self.get_user_media(account_username, limit=100)
            
            # Calculate basic insights
            media_types = {}
            engagement_estimates = {}
            
            for item in media:
                media_type = item.get('media_type', 'unknown')
                media_types[media_type] = media_types.get(media_type, 0) + 1
            
            return {
                'account': profile,
                'total_media': len(media),
                'media_breakdown': media_types,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get account insights: {e}")
            return {'error': str(e)}
    
    def is_token_valid(self) -> bool:
        """Check if Instagram access token is valid"""
        return bool(self.access_token)
    
    def get_token_info(self) -> Dict[str, Any]:
        """Get information about the current access token"""
        if not self.access_token:
            return {'valid': False, 'message': 'No token configured'}
        
        return {
            'valid': True,
            'token_length': len(self.access_token),
            'configured': True
        }
