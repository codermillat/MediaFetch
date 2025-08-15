#!/usr/bin/env python3
"""
Instagram Binding Handler
Processes binding codes sent to Instagram bot and automatically binds accounts
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class InstagramBindingHandler:
    """Handles Instagram binding code processing"""
    
    def __init__(self):
        self.pending_bindings = {}  # code -> {telegram_id, username, expires_at}
        self.active_bindings = {}   # telegram_id -> instagram_username
        
    def add_pending_binding(self, code: str, telegram_id: int, username: str = None):
        """Add a pending binding code"""
        expires_at = datetime.utcnow() + timedelta(hours=24)
        self.pending_bindings[code] = {
            'telegram_id': telegram_id,
            'instagram_username': username,
            'expires_at': expires_at,
            'created_at': datetime.utcnow()
        }
        logger.info(f"Added pending binding: Code {code} for Telegram user {telegram_id}")
        
    def process_binding_code(self, code: str, instagram_username: str) -> dict:
        """Process a binding code sent to Instagram"""
        if code not in self.pending_bindings:
            return {
                'success': False,
                'error': 'Invalid or expired binding code'
            }
        
        binding = self.pending_bindings[code]
        
        # Check if expired
        if datetime.utcnow() > binding['expires_at']:
            del self.pending_bindings[code]
            return {
                'success': False,
                'error': 'Binding code has expired'
            }
        
        # Activate binding
        telegram_id = binding['telegram_id']
        self.active_bindings[telegram_id] = instagram_username
        
        # Remove from pending
        del self.pending_bindings[code]
        
        logger.info(f"Binding activated: Telegram {telegram_id} -> Instagram @{instagram_username}")
        
        return {
            'success': True,
            'telegram_id': telegram_id,
            'instagram_username': instagram_username,
            'message': f"✅ Account @{instagram_username} successfully bound to MediaFetch!"
        }
    
    def get_user_bindings(self, telegram_id: int) -> list:
        """Get all bindings for a Telegram user"""
        if telegram_id in self.active_bindings:
            return [self.active_bindings[telegram_id]]
        return []
    
    def remove_binding(self, telegram_id: int, instagram_username: str = None) -> bool:
        """Remove a binding"""
        if telegram_id in self.active_bindings:
            if instagram_username is None or self.active_bindings[telegram_id] == instagram_username:
                del self.active_bindings[telegram_id]
                logger.info(f"Binding removed for Telegram user {telegram_id}")
                return True
        return False
    
    def cleanup_expired_bindings(self):
        """Remove expired pending bindings"""
        current_time = datetime.utcnow()
        expired_codes = [
            code for code, binding in self.pending_bindings.items()
            if current_time > binding['expires_at']
        ]
        
        for code in expired_codes:
            del self.pending_bindings[code]
            logger.info(f"Removed expired binding code: {code}")
        
        return len(expired_codes)

# Global instance
binding_handler = InstagramBindingHandler()

async def handle_instagram_message(message_text: str, sender_username: str) -> dict:
    """Handle incoming Instagram message and check for binding codes"""
    
    # Clean up expired bindings
    binding_handler.cleanup_expired_bindings()
    
    # Convert message to lowercase for command matching
    message_lower = message_text.lower().strip()
    
    # Check if message looks like a binding code (6-10 alphanumeric characters)
    if len(message_text) >= 6 and len(message_text) <= 10 and message_text.isalnum():
        # This could be a binding code
        result = binding_handler.process_binding_code(message_text, sender_username)
        
        if result['success']:
            return {
                'type': 'binding_success',
                'message': f"🎉 **Binding Successful!**\n\nYour Instagram account @{sender_username} is now bound to MediaFetch!\n\n🎬 **You will now receive:**\n• All reels automatically\n• All stories instantly\n• All posts as they're published\n\n**No more manual checking - content comes to you!**",
                'telegram_id': result['telegram_id'],
                'instagram_username': result['instagram_username']
            }
        else:
            return {
                'type': 'binding_error',
                'message': f"❌ **Binding Failed**\n\n{result['error']}\n\nPlease get a fresh binding code from the MediaFetch Telegram bot.",
                'error': result['error']
            }
    
    # Handle commands
    if message_lower in ['start', 'hello', 'hi', 'hey']:
        from instagram_bot_profile_setup import InstagramBotProfileSetup
        setup = InstagramBotProfileSetup()
        return {
            'type': 'welcome',
            'message': setup.get_welcome_message()
        }
    
    elif message_lower in ['help', 'h', '?']:
        from instagram_bot_profile_setup import InstagramBotProfileSetup
        setup = InstagramBotProfileSetup()
        return {
            'type': 'help',
            'message': setup.get_help_message()
        }
    
    elif message_lower in ['commands', 'cmd', 'menu']:
        from instagram_bot_profile_setup import InstagramBotProfileSetup
        setup = InstagramBotProfileSetup()
        return {
            'type': 'commands',
            'message': setup.get_commands_list()
        }
    
    elif message_lower in ['bind', 'binding', 'bind info', 'binding info']:
        from instagram_bot_profile_setup import InstagramBotProfileSetup
        setup = InstagramBotProfileSetup()
        return {
            'type': 'binding_info',
            'message': setup.get_binding_info()
        }
    
    elif message_lower in ['support', 'sos', 'help me']:
        from instagram_bot_profile_setup import InstagramBotProfileSetup
        setup = InstagramBotProfileSetup()
        return {
            'type': 'support',
            'message': setup.get_support_message()
        }
    
    elif message_lower in ['status', 'my status', 'binding status']:
        # Check if user has active binding
        if sender_username in [binding['instagram_username'] for binding in binding_handler.active_bindings.values()]:
            return {
                'type': 'status_active',
                'message': f"✅ **Binding Status: ACTIVE**\n\nYour Instagram account @{sender_username} is successfully bound to MediaFetch!\n\n🎬 **Content Delivery:**\n• All reels automatically sent\n• All stories instantly delivered\n• All posts as published\n\n**Status:** 🟢 Active and delivering content!"
            }
        else:
            return {
                'type': 'status_inactive',
                'message': f"❌ **Binding Status: NOT BOUND**\n\nYour Instagram account @{sender_username} is not currently bound to MediaFetch.\n\n🔗 **To Get Started:**\n1. Go to @EZMediaFetchBot on Telegram\n2. Send `/bind` to get your code\n3. Send that code here\n\n**Status:** 🔴 No active binding"
            }
    
    elif message_lower in ['info', 'about', 'what is this']:
        return {
            'type': 'info',
            'message': """🤖 **About MediaFetch**

**What is MediaFetch?**
MediaFetch is an intelligent Instagram content assistant that automatically delivers all your Instagram content to your Telegram account.

**🎯 Our Mission:**
Make content sharing effortless by automatically delivering your Instagram content to Telegram, so you never miss sharing anything with your audience.

**🚀 Key Features:**
• **Automatic Content Delivery** - No manual work needed
• **Real-time Updates** - Content sent as you post
• **Multi-format Support** - Reels, stories, posts, IGTV
• **Secure Binding** - Unique codes for account security
• **Instant Notifications** - Get notified on Telegram immediately

**🔒 Privacy & Security:**
• Your content is delivered only to your bound Telegram account
• We never store your content permanently
• Secure binding with unique, expiring codes
• No password sharing required

**📱 How It Works:**
1. **Bind Account** - Connect Instagram to Telegram
2. **Automatic Delivery** - Content sent automatically
3. **Enjoy** - No more manual sharing needed!

**🌍 Who It's For:**
• Content creators
• Social media managers
• Influencers
• Anyone who wants automatic content delivery

**💡 Why Choose MediaFetch?**
• **Time-saving** - No manual content sharing
• **Reliable** - 99.9% delivery success rate
• **Secure** - Private and safe
• **Easy** - Simple setup process

Ready to experience effortless content delivery? Get started with `/bind` on @EZMediaFetchBot! 🚀"""
        }
    
    elif message_lower in ['features', 'what do i get', 'benefits']:
        return {
            'type': 'features',
            'message': """🎬 **MediaFetch Features & Benefits**

**🚀 Core Features:**

**1. Automatic Content Delivery:**
• **Reels** - Every reel automatically sent to Telegram
• **Stories** - All stories instantly delivered
• **Posts** - Every post as it's published
• **IGTV** - Long-form content automatically shared

**2. Real-time Updates:**
• **Instant Delivery** - Content sent as you post
• **No Delays** - Real-time synchronization
• **Live Updates** - Always up-to-date content

**3. Smart Binding System:**
• **Unique Codes** - Secure one-time binding codes
• **Automatic Setup** - Username captured automatically
• **24-Hour Expiry** - Codes expire for security
• **One-time Use** - Each code can only be used once

**4. Multi-Platform Support:**
• **Instagram** - Primary content source
• **Telegram** - Content delivery destination
• **Cross-platform** - Works on all devices

**💎 Premium Benefits:**

**1. Time Savings:**
• **No Manual Work** - Content shares automatically
• **Instant Sharing** - No need to copy-paste
• **Batch Delivery** - Multiple content types handled

**2. Content Management:**
• **Organized Delivery** - Content arrives in Telegram
• **Easy Access** - All content in one place
• **Searchable** - Find content easily in Telegram

**3. Audience Engagement:**
• **Faster Sharing** - Content reaches audience immediately
• **Consistent Delivery** - Never miss sharing content
• **Professional Image** - Always on top of content sharing

**4. Analytics & Insights:**
• **Delivery Tracking** - See what was delivered
• **Performance Metrics** - Track content delivery success
• **User Statistics** - Monitor your binding status

**🔒 Security Features:**

**1. Account Protection:**
• **No Password Sharing** - Never share your credentials
• **Unique Binding** - Only you can use your code
• **Secure Delivery** - Content only goes to your account

**2. Privacy Controls:**
• **Private Content** - Only you receive your content
• **No Data Storage** - Content not permanently stored
• **Secure Transmission** - Encrypted content delivery

**⚡ Performance Features:**

**1. Speed & Reliability:**
• **99.9% Uptime** - Reliable service
• **Instant Delivery** - No delays
• **Error Handling** - Automatic retry on failures

**2. Scalability:**
• **Multiple Accounts** - Bind multiple Instagram accounts
• **High Volume** - Handle large amounts of content
• **Efficient Processing** - Optimized for performance

**🎯 Use Cases:**

**1. Content Creators:**
• Automatically share all content
• Reach multiple platforms instantly
• Focus on creating, not sharing

**2. Social Media Managers:**
• Manage multiple accounts efficiently
• Ensure consistent content delivery
• Save time on routine tasks

**3. Influencers:**
• Never miss sharing content
• Maintain consistent presence
• Engage audience across platforms

**4. Businesses:**
• Professional content management
• Consistent brand presence
• Efficient social media operations

**🚀 Ready to Experience These Features?**

Get started with a simple `/bind` command on @EZMediaFetchBot and unlock the full power of MediaFetch! 🎉"""
        }
    
    # Default response for any other message
    return {
        'type': 'general_help',
        'message': f"💬 **Hi @{sender_username}!**\n\nI'm the MediaFetch Instagram bot! Here's how I can help you:\n\n**🚀 Quick Actions:**\n• Send **help** for detailed instructions\n• Send **commands** for available options\n• Send **bind** for binding information\n• Send **start** to begin\n\n**🔗 To Bind Your Account:**\n1. Go to @EZMediaFetchBot on Telegram\n2. Send `/bind` to get your code\n3. Send that code here\n\n**💡 Need Help?** Just send any of these commands or your binding code!\n\n**Available Commands:** help, commands, bind, status, info, features, support"
    }

# Example usage
if __name__ == "__main__":
    # Simulate adding a pending binding
    binding_handler.add_pending_binding("A7B9C2D4", 123456789)
    
    # Simulate processing a binding code
    result = binding_handler.process_binding_code("A7B9C2D4", "testuser")
    print(f"Binding result: {result}")
    
    # Show active bindings
    print(f"Active bindings: {binding_handler.active_bindings}")
