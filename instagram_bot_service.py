#!/usr/bin/env python3
"""
Instagram Bot Service
Runs the Instagram bot to handle binding codes and content delivery
"""

import os
import logging
import asyncio
import time
from datetime import datetime
from dotenv import load_dotenv
from instagrapi import Client
from shared_binding_system import shared_binding_system

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
        self.is_logged_in = False
        self.username = os.getenv('INSTAGRAM_USERNAME')
        self.password = os.getenv('INSTAGRAM_PASSWORD')
        
        # Message tracking to prevent spam
        self.help_sent_users = set()
        self.last_message_time = {}  # Track last message time per user
        self.min_message_interval = 60  # Minimum 60 seconds between messages to same user
        
        # Rate limiting for API calls
        self.last_api_call = 0
        self.min_api_interval = 2.0  # Minimum 2 seconds between API calls
        
        # User state tracking
        self.user_message_count = {}  # Track message count per user
        self.max_messages_per_hour = 10  # Max messages per user per hour
        
    async def start(self):
        """Start the Instagram bot service"""
        try:
            logger.info("🚀 Starting Instagram Bot Service...")
            
            # Try to login to Instagram
            login_success = await self._try_login()
            
            if login_success:
                logger.info("✅ Instagram login successful")
                # Start monitoring DMs
                await self._monitor_direct_messages()
            else:
                logger.warning("⚠️ Instagram login failed - running in limited mode")
                # Run a simple loop to keep the service alive
                await self._run_limited_mode()
                
        except Exception as e:
            logger.error(f"❌ Error starting Instagram bot service: {e}")
            # Keep the service running even if there's an error
            await self._run_limited_mode()
    
    async def _try_login(self) -> bool:
        """Try to login to Instagram with error handling"""
        try:
            if not self.username or not self.password:
                logger.error("Instagram credentials not configured")
                return False
                
            logger.info(f"Attempting to login as @{self.username}...")
            
            # Set up the client to handle challenges better
            self.client.delay_range = [1, 3]  # Random delay between requests
            
            # Try to login
            try:
                self.client.login(self.username, self.password)
                self.is_logged_in = True
                
                # Get user info to confirm login
                user = self.client.user_info_by_username(self.username)
                logger.info(f"✅ Logged in as: {user.full_name} (@{user.username})")
                return True
                
            except Exception as login_error:
                logger.warning(f"Login attempt failed: {login_error}")
                
                # Check if it's a challenge/verification issue
                if "challenge" in str(login_error).lower() or "verification" in str(login_error).lower():
                    logger.warning("Instagram requires verification/challenge - cannot proceed with automated login")
                    return False
                else:
                    logger.error(f"Login error: {login_error}")
                    return False
                    
        except Exception as e:
            logger.error(f"Login setup failed: {e}")
            return False
    
    def _rate_limit_api(self):
        """Implement rate limiting for API calls"""
        current_time = time.time()
        if current_time - self.last_api_call < self.min_api_interval:
            sleep_time = self.min_api_interval - (current_time - self.last_api_call)
            time.sleep(sleep_time)
        self.last_api_call = time.time()

    def _can_send_message(self, username: str) -> bool:
        """Check if we can send a message to this user (rate limiting)"""
        current_time = time.time()
        
        # Check message interval
        if username in self.last_message_time:
            if current_time - self.last_message_time[username] < self.min_message_interval:
                return False
        
        # Check message count per hour
        if username in self.user_message_count:
            # Clean up old messages (older than 1 hour)
            hour_ago = current_time - 3600
            self.user_message_count[username] = [
                msg_time for msg_time in self.user_message_count[username]
                if msg_time > hour_ago
            ]
            
            if len(self.user_message_count[username]) >= self.max_messages_per_hour:
                return False
        
        return True

    def _record_message_sent(self, username: str):
        """Record that a message was sent to this user"""
        current_time = time.time()
        self.last_message_time[username] = current_time
        
        if username not in self.user_message_count:
            self.user_message_count[username] = []
        self.user_message_count[username].append(current_time)

    async def _run_limited_mode(self):
        """Run the service in limited mode when Instagram login fails"""
        logger.info("🔄 Running in limited mode - Instagram bot will not process messages")
        logger.info("📝 To enable full functionality, complete Instagram verification manually")
        
        # Keep the service running
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                logger.info("💓 Instagram bot service heartbeat - limited mode")
            except Exception as e:
                logger.error(f"Error in limited mode: {e}")
                await asyncio.sleep(60)
    
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
            
            # Check if it's a binding code first
            if self._is_binding_code(message_text):
                logger.info(f"🔐 Processing binding code: {message_text}")
                result = shared_binding_system.process_binding_code(message_text, sender_username)
                
                if result['success']:
                    # Send success message
                    await self._send_dm(sender_username, result['message'])
                    logger.info(f"✅ Binding successful: {sender_username} -> {result['telegram_id']}")
                else:
                    # Send error message
                    await self._send_dm(sender_username, f"❌ {result['error']}")
                    logger.warning(f"❌ Binding failed: {sender_username} - {result['error']}")
                return
            
            # Check if it's a command
            if message_text.lower().startswith(('/help', '/start', '/bind', '/commands')):
                await self._send_help_message(sender_username)
                return
            
            # Check if user is bound
            if self._is_bound_user(sender_username):
                # Handle content delivery
                await self._handle_content_delivery(sender_username, message_text)
            else:
                # Check if we can send a message to this user (rate limiting)
                if not self._can_send_message(sender_username):
                    logger.info(f"🤐 Rate limited: Skipping message for @{sender_username}")
                    return
                
                # Only send help message once per user to avoid spam
                if sender_username not in self.help_sent_users:
                    await self._send_help_message(sender_username)
                    self.help_sent_users.add(sender_username)
                    self._record_message_sent(sender_username)
                    logger.info(f"📝 Help message sent to @{sender_username} (first time)")
                else:
                    # Don't send any message for repeat users to avoid spam
                    logger.info(f"🤐 Skipping message for @{sender_username} (already sent help)")
                    
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Send a generic error message
            try:
                await self._send_dm(sender_username, "❌ Sorry, there was an error processing your message. Please try again.")
            except:
                pass
    
    def _is_binding_code(self, text: str) -> bool:
        """Check if text looks like a binding code"""
        # Remove any extra whitespace
        text = text.strip()
        
        # Binding codes are 6-10 characters, alphanumeric, uppercase
        if len(text) >= 6 and len(text) <= 10:
            # Check if it's all uppercase letters and numbers
            if text.isalnum() and text.isupper():
                # Avoid common words that might be mistaken for codes
                common_words = ['HELP', 'START', 'BIND', 'COMMANDS', 'STATUS', 'INFO', 'FEATURES', 'SUPPORT']
                if text not in common_words:
                    logger.info(f"🔍 Detected potential binding code: {text}")
                    return True
        
        return False
    
    def _is_bound_user(self, username: str) -> bool:
        """Check if Instagram user is bound to any Telegram account"""
        for telegram_id, instagram_user in shared_binding_system.active_bindings.items():
            if instagram_user == username:
                return True
        return False
    
    async def _send_dm(self, username: str, message: str):
        """Send direct message to user with rate limiting"""
        try:
            # Apply rate limiting
            self._rate_limit_api()
            
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
            for tid, insta_user in shared_binding_system.active_bindings.items():
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
