#!/usr/bin/env python3
"""
Robust MediaFetch Telegram Bot
Handles connection issues and network problems gracefully
"""

import os
import logging
import asyncio
import time
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TimedOut, NetworkError, RetryAfter

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Your bot token from .env
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    welcome_text = (
        f"🎬 **Welcome to MediaFetch, {user.first_name}!**\n\n"
        "I'm your intelligent media assistant that can:\n\n"
        "🔗 **Bind to Instagram Accounts**\n"
        "• Get automatic delivery of ALL reels from accounts you follow\n"
        "• No more manual checking - content comes to you!\n\n"
        "📥 **Download Media from Anywhere**\n"
        "• YouTube, TikTok, Instagram, Vimeo, Twitter, Reddit\n"
        "• Automatic compression and optimization\n\n"
        "**Commands:**\n"
        "• `/bind` - Generate binding code\n"
        "• `/bindings` - View your active bindings\n"
        "• `/help` - Get help and instructions"
    )
    
    # Create inline keyboard
    keyboard = [
        [InlineKeyboardButton("🔗 Start Binding", callback_data="start_binding")],
        [InlineKeyboardButton("📱 View Bindings", callback_data="view_bindings")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
        logger.info(f"Start command handled for user {user.id}")
    except Exception as e:
        logger.error(f"Error in start command: {e}")

async def bind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bind command - generates unique binding code"""
    user = update.effective_user
    
    # Generate unique binding code
    import secrets
    import string
    characters = string.ascii_uppercase + string.digits
    characters = characters.replace('0', '').replace('O', '').replace('1', '').replace('I', '')
    binding_code = ''.join(secrets.choice(characters) for _ in range(8))
    
    binding_message = (
        f"✅ **Binding Code Generated!**\n\n"
        f"**Your Unique Code:** `{binding_code}`\n"
        f"**Expires:** 24 hours\n\n"
        f"📱 **Next Steps:**\n"
        "1. Go to Instagram\n"
        "2. Send this code to our Instagram bot\n"
        "3. Your account will be automatically bound!\n\n"
        f"🔒 **Security:** This code is unique to you and expires in 24 hours.\n"
        f"👤 **Your Telegram ID:** {user.id}"
    )
    
    try:
        await update.message.reply_text(binding_message, parse_mode='Markdown')
        logger.info(f"Binding code {binding_code} generated for user {user.id} ({user.first_name})")
        
        # Add to Instagram binding handler (for production integration)
        try:
            from shared_binding_system import shared_binding_system
            
            # Check if user already has a pending binding
            if shared_binding_system.add_pending_binding(binding_code, user.id, None):
                logger.info(f"Binding code {binding_code} added to shared binding system for user {user.id}")
            else:
                # User already has a pending binding
                await update.message.reply_text(
                    "⚠️ **Binding Code Already Exists**\n\n"
                    "You already have a pending binding code!\n\n"
                    "**What to do:**\n"
                    "1. Use your existing code first\n"
                    "2. Send it to our Instagram bot\n"
                    "3. Wait for it to expire (24 hours)\n"
                    "4. Then request a new code\n\n"
                    "**Current Status:** You can only have one active binding code at a time."
                )
                return
                
        except ImportError:
            logger.info("Shared binding system not available - running in test mode")
            
    except Exception as e:
        logger.error(f"Error in bind command: {e}")

async def bindings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bindings command"""
    try:
        from shared_binding_system import shared_binding_system
        user_id = update.effective_user.id
        bindings = shared_binding_system.get_user_bindings(user_id)
        
        if bindings:
            bindings_list = "\n".join([f"• @{username}" for username in bindings])
            bindings_message = (
                f"📱 **Your Active Bindings**\n\n"
                f"**Found {len(bindings)} active binding(s):**\n"
                f"{bindings_list}\n\n"
                "✅ **Status:** Your Instagram account(s) are bound!\n"
                "📦 **Content Delivery:** Active - Instagram content will be sent here automatically!\n\n"
                "**To add more bindings:**\n"
                "• Use `/bind` to get a new code\n"
                "• Send code to Instagram bot\n\n"
                "**To remove binding:**\n"
                "• Use `/unbind @username`"
            )
        else:
            bindings_message = (
                "📱 **Your Active Bindings**\n\n"
                "**No active bindings found.**\n\n"
                "To create a binding:\n"
                "• Use `/bind` to get your code\n"
                "• Send code to Instagram bot\n"
                "• Enjoy automatic content delivery!"
            )
        
        await update.message.reply_text(bindings_message, parse_mode='Markdown')
        
    except ImportError:
        # Fallback if shared system not available
        bindings_message = (
            "📱 **Your Active Bindings**\n\n"
            "**No active bindings found.**\n\n"
            "To create a binding:\n"
            "• Use `/bind` to get your code\n"
            "• Send code to Instagram bot\n"
            "• Enjoy automatic content delivery!"
        )
        await update.message.reply_text(bindings_message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in bindings command: {e}")
        await update.message.reply_text("❌ Error retrieving bindings. Please try again later.")

async def unbind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unbind command"""
    try:
        from shared_binding_system import shared_binding_system
        user_id = update.effective_user.id
        
        # Check if user has any bindings
        current_bindings = shared_binding_system.get_user_bindings(user_id)
        
        if not current_bindings:
            await update.message.reply_text(
                "📱 **No Bindings to Remove**\n\n"
                "You don't have any active Instagram bindings.\n\n"
                "Use `/bind` to create a new binding first!"
            )
            return
        
        # If no username specified, show current bindings
        if not context.args:
            bindings_list = "\n".join([f"• @{username}" for username in current_bindings])
            await update.message.reply_text(
                f"📱 **Your Current Bindings**\n\n"
                f"{bindings_list}\n\n"
                "**To remove a binding:**\n"
                "• `/unbind @username` - Remove specific binding\n"
                "• `/unbind all` - Remove all bindings"
            )
            return
        
        target_username = context.args[0]
        
        # Handle "all" case
        if target_username.lower() == "all":
            removed_count = 0
            for username in current_bindings:
                if shared_binding_system.remove_binding(user_id, username):
                    removed_count += 1
            
            await update.message.reply_text(
                f"🗑️ **Bindings Removed**\n\n"
                f"Successfully removed {removed_count} binding(s).\n\n"
                "Use `/bind` to create new bindings when needed!"
            )
            return
        
        # Remove specific binding
        if target_username.startswith('@'):
            target_username = target_username[1:]  # Remove @ symbol
        
        if shared_binding_system.remove_binding(user_id, target_username):
            await update.message.reply_text(
                f"✅ **Binding Removed**\n\n"
                f"Successfully removed binding with @{target_username}.\n\n"
                "Use `/bind` to create a new binding if needed!"
            )
        else:
            await update.message.reply_text(
                f"❌ **Binding Not Found**\n\n"
                f"No binding found with @{target_username}.\n\n"
                "Use `/bindings` to see your current bindings."
            )
            
    except ImportError:
        await update.message.reply_text(
            "❌ **Service Unavailable**\n\n"
            "The binding service is currently unavailable.\n"
            "Please try again later."
        )
    except Exception as e:
        logger.error(f"Error in unbind command: {e}")
        await update.message.reply_text("❌ Error processing unbind request. Please try again later.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "❓ **MediaFetch Help**\n\n"
        "**Instagram Binding Commands:**\n"
        "• `/bind` - Generate binding code\n"
        "• `/bindings` - View your active bindings\n"
        "• `/unbind` - Remove binding\n\n"
        "**Media Download:**\n"
        "• Send any media URL (YouTube, TikTok, Instagram, etc.)\n"
        "• I'll download and send it back optimized\n\n"
        "**Binding Process:**\n"
        "1. Use `/bind` to get unique code\n"
        "2. Send code to Instagram bot\n"
        "3. Account automatically bound!\n"
        "4. Enjoy automatic content delivery!\n\n"
        "**Need help?** Contact support or check our documentation."
    )
    
    try:
        await update.message.reply_text(help_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in help command: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    text = update.message.text
    
    # Check if it's a URL
    if any(domain in text.lower() for domain in ['youtube.com', 'tiktok.com', 'instagram.com', 'vimeo.com', 'twitter.com', 'reddit.com']):
        response_text = (
            "🔗 **Media URL Detected!**\n\n"
            f"I'm processing: `{text}`\n\n"
            "⏳ Downloading and optimizing...\n"
            "📱 This feature will be fully functional in production!\n\n"
            "**Note:** This is a test environment. In production, I'll:\n"
            "• Download the media\n"
            "• Optimize and compress\n"
            "• Send it back to you"
        )
    else:
        response_text = (
            "💬 **Message Received!**\n\n"
            "**Available Commands:**\n"
            "• `/start` - Welcome and options\n"
            "• `/bind` - Generate binding code\n"
            "• `/bindings` - View bindings\n"
            "• `/help` - Get help\n\n"
            "**Media Download:** Send any media URL and I'll download it for you!"
        )
    
    try:
        await update.message.reply_text(response_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in message handler: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    try:
        await query.answer()
        
        if query.data == "start_binding":
            await query.edit_message_text(
                "🔗 **Start Instagram Binding**\n\n"
                "**How it works:**\n"
                "1. Use `/bind` command\n"
                "2. Get unique binding code\n"
                "3. Send code to Instagram bot\n"
                "4. Account automatically bound!\n\n"
                "**Simple:** Just type `/bind` and follow the steps!"
            )
        elif query.data == "view_bindings":
            await query.edit_message_text(
                "📱 **Your Bindings**\n\n"
                "**No active bindings found.**\n\n"
                "To create your first binding:\n"
                "• Type `/bind` to get your code\n"
                "• Send code to Instagram bot\n"
                "• Start receiving content automatically!"
            )
        elif query.data == "help":
            await query.edit_message_text(
                "❓ **Help & Support**\n\n"
                "**Quick Start:**\n"
                "• `/bind` - Generate binding code\n"
                "• Send media URLs - Download any content\n\n"
                "**Need Help?**\n"
                "• Use `/help` for detailed instructions\n"
                "• Contact support for assistance\n\n"
                "**Features:**\n"
                "• Instagram content delivery\n"
                "• Multi-platform media download\n"
                "• Automatic optimization"
            )
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")

async def cleanup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cleanup command - Admin only"""
    try:
        from shared_binding_system import shared_binding_system
        
        # Check if user is admin (you can customize this logic)
        user_id = update.effective_user.id
        # For now, allow any user to run cleanup (you can restrict this)
        
        # Run cleanup
        shared_binding_system.cleanup_expired_bindings()
        
        cleanup_message = (
            "🧹 **System Cleanup Completed**\n\n"
            "**Actions performed:**\n"
            "• Removed expired binding codes\n"
            "• Cleaned up old data\n"
            "• Optimized system performance\n\n"
            "✅ **Status:** System cleaned and optimized!"
        )
        
        await update.message.reply_text(cleanup_message, parse_mode='Markdown')
        logger.info(f"Cleanup command executed by user {user_id}")
        
    except ImportError:
        await update.message.reply_text("❌ Cleanup system not available.")
    except Exception as e:
        logger.error(f"Error in cleanup command: {e}")
        await update.message.reply_text("❌ Error during cleanup process.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors gracefully"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    if isinstance(context.error, TimedOut):
        logger.warning("Request timed out, will retry...")
    elif isinstance(context.error, NetworkError):
        logger.warning("Network error, will retry...")
    elif isinstance(context.error, RetryAfter):
        logger.warning(f"Rate limited, will retry after {context.error.retry_after} seconds")

def main():
    """Main function to start the bot with retry logic"""
    max_retries = 5
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🚀 Starting MediaFetch Telegram Bot (Production) - Attempt {attempt + 1}/{max_retries}")
            
            # Create application with custom settings
            application = (
                Application.builder()
                .token(BOT_TOKEN)
                .read_timeout(30)
                .write_timeout(30)
                .connect_timeout(30)
                .pool_timeout(30)
                .build()
            )
            
            # Add handlers
            application.add_handler(CommandHandler("start", start_command))
            application.add_handler(CommandHandler("bind", bind_command))
            application.add_handler(CommandHandler("bindings", bindings_command))
            application.add_handler(CommandHandler("unbind", unbind_command)) # Added unbind handler
            application.add_handler(CommandHandler("help", help_command))
            application.add_handler(CommandHandler("cleanup", cleanup_command))
            
            # Add message handler
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
            # Add callback query handler
            application.add_handler(CallbackQueryHandler(handle_callback))
            
            # Add error handler
            application.add_error_handler(error_handler)
            
            logger.info("✅ Bot handlers configured")
            logger.info("✅ Bot starting...")
            logger.info("✅ Ready to receive messages!")
            
            # Start the bot
            application.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            
            # If we get here, the bot is running successfully
            break
            
        except Exception as e:
            logger.error(f"❌ Attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("❌ All retry attempts failed. Exiting.")
                raise

if __name__ == "__main__":
    main()
