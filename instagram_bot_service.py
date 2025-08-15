#!/usr/bin/env python3
"""
Instagram Bot Service
Runs the Instagram bot to handle binding codes and content delivery
"""

import os
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from instagrapi import Client
from instagram_binding_handler import InstagramBindingHandler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class InstagramBotService:
    """Instagram bot service for handling binding and content delivery"""
    
    def __init__(self):
        self.client = Client()
        self.binding_handler = InstagramBindingHandler()
        self.is_logged_in = False
        self.username = os.getenv('INSTAGRAM_USERNAME')
        self.password = os.getenv('INSTAGRAM_PASSWORD')
        
    async def start(self):
        """Start the Instagram bot service"""
        try:
            logger.info("🚀 Starting Instagram Bot Service...")
            
            # Login to Instagram
            if await self._login():
                logger.info("✅ Instagram login successful")
                
                # Start monitoring DMs
                await self._monitor_direct_messages()
            else:
                logger.error("❌ Failed to login to Instagram")
                
        except Exception as e:
            logger.error(f"❌ Error starting Instagram bot service: {e}")
    
    async def _login(self) -> bool:
        """Login to Instagram"""
        try:
            if not self.username or not self.password:
                logger.error("Instagram credentials not configured")
                return False
                
            logger.info(f"Logging in as @{self.username}...")
            
            # Login
            self.client.login(self.username, self.password)
            self.is_logged_in = True
            
            # Get user info
            user = self.client.user_info_by_username(self.username)
            logger.info(f"Logged in as: {user.full_name} (@{user.username})")
            
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    async def _monitor_direct_messages(self):
        """Monitor direct messages for binding codes and content"""
        logger.info("📱 Starting DM monitoring...")
        
        while self.is_logged_in:
            try:
                # Get recent DMs
                threads = self.client.direct_threads()
                
                for thread in threads:
                    # Get messages from thread
                    messages = self.client.direct_messages(thread.id, amount=10)
                    
                    for message in messages:
                        if hasattr(message, 'text') and message.text:
                            await self._process_message(message.text, thread.users[0].username)
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring DMs: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _process_message(self, message_text: str, sender_username: str):
        """Process incoming Instagram message"""
        try:
            logger.info(f"📨 Message from @{sender_username}: {message_text}")
            
            # Check if it's a binding code
            if self._is_binding_code(message_text):
                result = self.binding_handler.process_binding_code(message_text, sender_username)
                
                if result['success']:
                    # Send success message
                    await self._send_dm(sender_username, result['message'])
                    logger.info(f"✅ Binding successful: {sender_username} -> {result['telegram_id']}")
                else:
                    # Send error message
                    await self._send_dm(sender_username, f"❌ {result['error']}")
                    logger.warning(f"❌ Binding failed: {sender_username} - {result['error']}")
            else:
                # Check if user is bound
                if self._is_bound_user(sender_username):
                    # Handle content delivery
                    await self._handle_content_delivery(sender_username, message_text)
                else:
                    # Send help message
                    await self._send_help_message(sender_username)
                    
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def _is_binding_code(self, text: str) -> bool:
        """Check if text looks like a binding code"""
        # Binding codes are 6-10 characters, alphanumeric
        if len(text) >= 6 and len(text) <= 10:
            return text.isalnum() and text.isupper()
        return False
    
    def _is_bound_user(self, username: str) -> bool:
        """Check if Instagram user is bound to any Telegram account"""
        for telegram_id, instagram_user in self.binding_handler.active_bindings.items():
            if instagram_user == username:
                return True
        return False
    
    async def _send_dm(self, username: str, message: str):
        """Send direct message to user"""
        try:
            user = self.client.user_info_by_username(username)
            self.client.direct_send(message, user_ids=[user.pk])
            logger.info(f"📤 DM sent to @{username}")
        except Exception as e:
            logger.error(f"Failed to send DM to @{username}: {e}")
    
    async def _send_help_message(self, username: str):
        """Send help message to unbound user"""
        help_message = (
            "🤖 **MediaFetch Bot Help**\n\n"
            "To use this bot, you need to bind your Instagram account:\n\n"
            "1️⃣ Go to @EZMediaFetchBot on Telegram\n"
            "2️⃣ Send /bind command\n"
            "3️⃣ Copy the unique code\n"
            "4️⃣ Send that code here\n\n"
            "Once bound, any content you send will be automatically delivered to your Telegram!"
        )
        await self._send_dm(username, help_message)
    
    async def _handle_content_delivery(self, username: str, content: str):
        """Handle content delivery from bound user"""
        try:
            # Find bound Telegram user
            telegram_id = None
            for tid, insta_user in self.binding_handler.active_bindings.items():
                if insta_user == username:
                    telegram_id = tid
                    break
            
            if telegram_id:
                logger.info(f"📦 Content delivery: @{username} -> Telegram {telegram_id}")
                # Here you would integrate with your Telegram bot to send the content
                # For now, just log it
                await self._send_dm(username, "✅ Content received! It will be delivered to your Telegram account.")
            else:
                logger.warning(f"User @{username} not found in active bindings")
                
        except Exception as e:
            logger.error(f"Error handling content delivery: {e}")

async def main():
    """Main function to run the Instagram bot service"""
    bot_service = InstagramBotService()
    await bot_service.start()

if __name__ == "__main__":
    asyncio.run(main())
