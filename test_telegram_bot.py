#!/usr/bin/env python3
"""
Test script to launch and test the actual Telegram bot
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

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
    
    # Create welcome message with binding options
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
        "• `/bind @username` - Bind to Instagram account\n"
        "• `/bindings` - View your active bindings\n"
        "• `/help` - Get help and instructions"
    )
    
    # Create inline keyboard for binding
    keyboard = [
        [InlineKeyboardButton("🔗 Start Binding", callback_data="start_binding")],
        [InlineKeyboardButton("📱 View Bindings", callback_data="view_bindings")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def bind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bind command"""
    if not context.args:
        await update.message.reply_text(
            "❌ **Usage:** `/bind @username`\n\n"
            "**Example:** `/bind @natgeo`\n\n"
            "This will generate a unique binding code for you to send to that Instagram account."
        )
        return
    
    username = context.args[0]
    if not username.startswith('@'):
        username = '@' + username
    
    # Generate a simple binding code (in production, use the binding manager)
    import secrets
    import string
    characters = string.ascii_uppercase + string.digits
    characters = characters.replace('0', '').replace('O', '').replace('1', '').replace('I', '')
    binding_code = ''.join(secrets.choice(characters) for _ in range(8))
    
    binding_message = (
        f"✅ **Binding Code Generated!**\n\n"
        f"**Instagram Account:** {username}\n"
        f"**Your Code:** `{binding_code}`\n"
        f"**Expires:** 24 hours\n\n"
        f"📱 **Next Steps:**\n"
        f"1. Go to Instagram\n"
        f"2. Send this code to {username}\n"
        f"3. Wait for confirmation\n\n"
        f"🔒 **Security:** This code is unique to you and expires in 24 hours."
    )
    
    await update.message.reply_text(binding_message, parse_mode='Markdown')

async def bindings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bindings command"""
    # Mock bindings for testing
    bindings_message = (
        "📱 **Your Active Bindings**\n\n"
        "**No active bindings found.**\n\n"
        "To create a binding:\n"
        "• Use `/bind @username` to start\n"
        "• Follow the confirmation steps\n"
        "• Enjoy automatic content delivery!"
    )
    
    await update.message.reply_text(bindings_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "❓ **MediaFetch Help**\n\n"
        "**Instagram Binding Commands:**\n"
        "• `/bind @username` - Bind to Instagram account\n"
        "• `/bindings` - View your active bindings\n"
        "• `/unbind @username` - Remove binding\n\n"
        "**Media Download:**\n"
        "• Send any media URL (YouTube, TikTok, Instagram, etc.)\n"
        "• I'll download and send it back optimized\n\n"
        "**Binding Process:**\n"
        "1. Use `/bind @username`\n"
        "2. Get unique binding code\n"
        "3. Send code to Instagram account\n"
        "4. Enjoy automatic content delivery!\n\n"
        "**Need help?** Contact support or check our documentation."
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages (media URLs)"""
    text = update.message.text
    
    # Check if it's a URL
    if any(domain in text.lower() for domain in ['youtube.com', 'tiktok.com', 'instagram.com', 'vimeo.com', 'twitter.com', 'reddit.com']):
        await update.message.reply_text(
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
        await update.message.reply_text(
            "💬 **Message Received!**\n\n"
            "**Available Commands:**\n"
            "• `/start` - Welcome and options\n"
            "• `/bind @username` - Bind Instagram account\n"
            "• `/bindings` - View bindings\n"
            "• `/help` - Get help\n\n"
            "**Media Download:** Send any media URL and I'll download it for you!"
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "start_binding":
        await query.edit_message_text(
            "🔗 **Start Instagram Binding**\n\n"
            "**How it works:**\n"
            "1. Use `/bind @username` command\n"
            "2. Get unique binding code\n"
            "3. Send code to Instagram account\n"
            "4. Enjoy automatic content delivery!\n\n"
            "**Example:** `/bind @natgeo`"
        )
    elif query.data == "view_bindings":
        await query.edit_message_text(
            "📱 **Your Bindings**\n\n"
            "**No active bindings found.**\n\n"
            "To create your first binding:\n"
            "• Type `/bind @username`\n"
            "• Follow the confirmation steps\n"
            "• Start receiving content automatically!"
        )
    elif query.data == "help":
        await query.edit_message_text(
            "❓ **Help & Support**\n\n"
            "**Quick Start:**\n"
            "• `/bind @username` - Bind Instagram account\n"
            "• Send media URLs - Download any content\n\n"
            "**Need Help?**\n"
            "• Use `/help` for detailed instructions\n"
            "• Contact support for assistance\n\n"
            "**Features:**\n"
            "• Instagram content delivery\n"
            "• Multi-platform media download\n"
            "• Automatic optimization"
        )

async def main():
    """Main function to start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("bind", bind_command))
    application.add_handler(CommandHandler("bindings", bindings_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("Starting MediaFetch Telegram Bot...")
    logger.info("Bot will respond to commands and messages")
    logger.info("Use /start to begin testing")
    
    # Start the bot
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
