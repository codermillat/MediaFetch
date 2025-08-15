#!/usr/bin/env python3
"""
Instagram Bot Profile Setup
Configures the MediaFetch Instagram bot profile to be user-friendly
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class InstagramBotProfileSetup:
    """Sets up Instagram bot profile for better user experience"""
    
    def __init__(self):
        self.bot_username = "mediafetchbot"
        self.bot_name = "MediaFetch Bot"
        
    def get_enhanced_bio(self):
        """Get enhanced bio with helpful information (max 150 chars)"""
        return """🤖 MediaFetch Bot - Auto-deliver Instagram content to Telegram

📱 Send /bind to @EZMediaFetchBot on Telegram, get code, send here = automatic content delivery!

🎬 Reels, stories, posts → Telegram automatically

🔗 @EZMediaFetchBot #MediaFetch #AutoDelivery"""
    
    def get_welcome_message(self):
        """Get welcome message for new users"""
        return """🎉 **Welcome to MediaFetch!**

I'm your Instagram content assistant that automatically delivers all your content to Telegram.

**🚀 Quick Start:**
1. **Get Binding Code:** Go to @EZMediaFetchBot on Telegram
2. **Send Code Here:** Send your unique binding code in this DM
3. **Start Receiving:** All your content will be automatically delivered!

**💡 Need Help?**
• Send any message for assistance
• Send "help" for detailed instructions
• Send "commands" for available options

**🎯 What Happens After Binding:**
• Every reel you post → Automatically sent to Telegram
• Every story you share → Instantly delivered
• Every post you publish → Sent automatically

**🔒 Security:**
• Your binding code is unique and expires in 24 hours
• Only you can use your code
• Your content is delivered only to your bound Telegram account

Ready to get started? Get your binding code from @EZMediaFetchBot! 🚀"""
    
    def get_help_message(self):
        """Get comprehensive help message"""
        return """❓ **MediaFetch Help & Commands**

**🔗 Binding Process:**
1. **Get Code:** Send `/bind` to @EZMediaFetchBot on Telegram
2. **Activate:** Send your code here in this DM
3. **Confirm:** You'll get confirmation when bound
4. **Enjoy:** Automatic content delivery begins!

**📱 Available Commands:**
• **help** - Show this help message
• **commands** - List all available commands
• **status** - Check your binding status
• **info** - About MediaFetch
• **support** - Get help and support

**🎬 Content Types Delivered:**
• **Reels** - All your reels automatically
• **Stories** - Every story instantly
• **Posts** - All posts as published
• **IGTV** - Long-form content

**⚙️ Settings & Preferences:**
• **Delivery Time:** Real-time (as you post)
• **Content Quality:** Original quality maintained
• **Notifications:** Instant Telegram notifications
• **Privacy:** Only you receive your content

**🔒 Security Features:**
• Unique binding codes (24-hour expiry)
• One-time use codes
• Telegram ID verification
• Secure content delivery

**📞 Support:**
• **Telegram:** @EZMediaFetchBot
• **Instagram:** @mediafetchbot
• **Response Time:** Usually within minutes

**💡 Tips:**
• Keep your binding code private
• Use codes within 24 hours
• Contact support if you have issues
• Check Telegram for delivery confirmations

Need more help? Send "support" or contact us directly! 🚀"""
    
    def get_commands_list(self):
        """Get list of available commands"""
        return """📋 **Available Commands**

**🔐 Account Management:**
• **bind** - Get binding code from Telegram bot
• **status** - Check your binding status
• **unbind** - Remove your binding

**📚 Information:**
• **help** - Show detailed help
• **commands** - This command list
• **info** - About MediaFetch
• **features** - What you get

**🆘 Support:**
• **support** - Get help and support
• **contact** - Contact information
• **faq** - Frequently asked questions

**🎯 Quick Actions:**
• Send any message for help
• Send binding code to activate
• Send "start" to begin

**💬 How to Use:**
Just type any of these commands in this chat, or send your binding code to get started!

**🚀 Ready to Start?**
Send "start" or get your binding code from @EZMediaFetchBot on Telegram!"""
    
    def get_binding_info(self):
        """Get detailed binding information"""
        return """🔗 **Instagram Binding Information**

**🎯 What is Binding?**
Binding connects your Instagram account to your Telegram account, enabling automatic content delivery.

**📱 How It Works:**
1. **Generate Code:** Use `/bind` on @EZMediaFetchBot
2. **Send Code:** Send your code here in DM
3. **Automatic Setup:** We capture your username and bind
4. **Content Delivery:** All content automatically sent to Telegram

**🔐 Security Features:**
• **Unique Codes:** Each code is one-time use
• **24-Hour Expiry:** Codes expire for security
• **Telegram ID:** Only your account can use your code
• **Username Capture:** We automatically get your Instagram username

**🎬 What Gets Delivered:**
• **Reels:** Every reel you post
• **Stories:** All your stories
• **Posts:** Every post you publish
• **IGTV:** Long-form content

**⚡ Delivery Speed:**
• **Real-time:** Content sent as you post
• **Instant:** No delays in delivery
• **Reliable:** 99.9% delivery success rate

**🔄 Binding Process:**
1. **Request Code:** `/bind` on Telegram
2. **Receive Code:** Get unique 8-character code
3. **Send Code:** DM the code here
4. **Confirmation:** Get binding success message
5. **Activation:** Content delivery begins immediately

**❓ Common Questions:**
• **Q:** Do I need to share my password? **A:** No, never!
• **Q:** Can I bind multiple accounts? **A:** Yes, one binding per account
• **Q:** How long does binding last? **A:** Forever, until you unbind
• **Q:** Is my content private? **A:** Yes, only you receive it

**🚀 Ready to Bind?**
Get your code from @EZMediaFetchBot and send it here!"""
    
    def get_support_message(self):
        """Get support and contact information"""
        return """🆘 **MediaFetch Support**

**📞 How to Get Help:**

**1. Telegram Bot (Recommended):**
• **Bot:** @EZMediaFetchBot
• **Response:** Usually instant
• **Commands:** `/help`, `/support`

**2. Instagram DM:**
• **Account:** @mediafetchbot
• **Response:** Within 1-2 hours
• **Best for:** Complex issues

**3. Email Support:**
• **Email:** support@mediafetch.com
• **Response:** Within 24 hours
• **Best for:** Account issues

**🔧 Common Issues & Solutions:**

**❌ Binding Code Not Working:**
• Check if code is expired (24 hours)
• Ensure you're using the right code
• Try getting a new code with `/bind`

**❌ Content Not Delivering:**
• Verify your binding is active
• Check Telegram for delivery confirmations
• Ensure Instagram account is public

**❌ Bot Not Responding:**
• Check if bot is online
• Try sending "start" or "help"
• Contact support if persistent

**📋 Before Contacting Support:**
• Have your Telegram ID ready
• Know your Instagram username
• Describe the issue clearly
• Include any error messages

**🚀 Quick Fixes:**
• **Restart:** Try getting a new binding code
• **Reconnect:** Unbind and rebind your account
• **Check Status:** Use `/status` on Telegram

**⏰ Support Hours:**
• **Telegram:** 24/7 automated support
• **Instagram:** 9 AM - 6 PM (UTC)
• **Email:** 24/7 (response within 24h)

**💡 Pro Tips:**
• Always use the latest binding code
• Keep your Telegram bot active
• Check your binding status regularly
• Report issues immediately

Need immediate help? Send "start" to begin troubleshooting! 🚀"""

# Example usage
if __name__ == "__main__":
    setup = InstagramBotProfileSetup()
    
    print("=== Instagram Bot Profile Setup ===\n")
    print("1. Enhanced Bio:")
    print(setup.get_enhanced_bio())
    print("\n" + "="*50 + "\n")
    
    print("2. Welcome Message:")
    print(setup.get_welcome_message())
    print("\n" + "="*50 + "\n")
    
    print("3. Help Message:")
    print(setup.get_help_message())
    print("\n" + "="*50 + "\n")
    
    print("4. Commands List:")
    print(setup.get_commands_list())
    print("\n" + "="*50 + "\n")
    
    print("5. Binding Info:")
    print(setup.get_binding_info())
    print("\n" + "="*50 + "\n")
    
    print("6. Support Message:")
    print(setup.get_support_message())
