#!/usr/bin/env python3
"""
MediaFetch Telegram Bot - Main Bot Implementation
Production-ready bot with proper error handling, validation, and monitoring
"""

import os
import logging
import asyncio
import tempfile
import shutil
from typing import Optional, Dict, Any
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from telegram.error import TelegramError

from .config import Config
from .media_downloader import MediaDownloader
from .media_processor import MediaProcessor
from .metrics import MetricsCollector
from .instagram_client import InstagramClient
from .instagram_monitor import InstagramMonitor
from .utils import validate_url, sanitize_filename

logger = logging.getLogger(__name__)

class MediaFetchBot:
    """Main MediaFetch bot class with production-ready features"""
    
    def __init__(self):
        """Initialize the bot with configuration and components"""
        self.config = Config()
        self.metrics = MetricsCollector()
        self.downloader = MediaDownloader()
        self.processor = MediaProcessor()
        self.instagram_client = InstagramClient()
        self.instagram_monitor = InstagramMonitor()
        
        # Initialize bot application
        self.application = Application.builder().token(self.config.get_telegram_token()).build()
        
        # Set up handlers
        self._setup_handlers()
        
        # Bot state
        self.is_running = False
        self.user_sessions: Dict[int, Dict[str, Any]] = {}
        self.monitored_accounts: Dict[int, List[str]] = {}  # user_id -> list of accounts
        
        logger.info("MediaFetch bot initialized successfully")
    
    def _setup_handlers(self):
        """Set up all bot command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("help", self._help_command))
        self.application.add_handler(CommandHandler("status", self._status_command))
        self.application.add_handler(CommandHandler("cancel", self._cancel_command))
        self.application.add_handler(CommandHandler("instagram", self._instagram_command))
        self.application.add_handler(CommandHandler("monitor", self._monitor_command))
        self.application.add_handler(CommandHandler("unmonitor", self._unmonitor_command))
        self.application.add_handler(CommandHandler("auto", self._auto_command))
        self.application.add_handler(CommandHandler("preferences", self._preferences_command))
        
        # Message handlers
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self._handle_message
        ))
        
        # Callback query handlers
        self.application.add_handler(CallbackQueryHandler(self._handle_callback))
        
        # Error handler
        self.application.add_error_handler(self._error_handler)
        
        logger.info("Bot handlers configured")
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        user_id = user.id
        
        # Initialize user session
        self.user_sessions[user_id] = {
            'state': 'idle',
            'current_download': None,
            'downloads_count': 0
        }
        
        welcome_text = (
            f"🎬 Welcome to MediaFetch, {user.first_name}!\n\n"
            "I can download media from:\n"
            "• YouTube\n"
            "• TikTok\n"
            "• Instagram\n"
            "• Vimeo\n"
            "• And many more platforms!\n\n"
            "📱 Simply send me a media link to get started.\n"
            "❓ Use /help for more information."
        )
        
        await update.message.reply_text(welcome_text)
        self.metrics.increment_command_usage('start')
        logger.info(f"User {user_id} started the bot")
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "🔧 **MediaFetch Bot Help**\n\n"
            "**Basic Commands:**\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/status - Check your download status\n"
            "/cancel - Cancel current download\n\n"
            "**Instagram Commands:**\n"
            "/instagram - Instagram integration help\n"
            "/instagram profile [username] - Get account profile\n"
            "/instagram media [username] [limit] - Get recent media\n"
            "/instagram stories [username] - Get stories\n"
            "/instagram insights [username] - Get account insights\n\n"
            "**Monitoring Commands:**\n"
            "/monitor [username] - Start monitoring an account\n"
            "/monitor list - List monitored accounts\n"
            "/monitor check - Check for new content\n"
            "/unmonitor [username] - Stop monitoring\n\n"
            "**🤖 Automatic Content Delivery:**\n"
            "/auto start - Start automatic monitoring\n"
            "/auto stop - Stop automatic monitoring\n"
            "/auto status - Check monitoring status\n"
            "/auto check [username] - Force check account\n"
            "/preferences - Set delivery preferences\n\n"
            "**Usage:**\n"
            "1. Send any media link (YouTube, TikTok, Instagram, etc.)\n"
            "2. Wait for processing and download\n"
            "3. Receive your media file\n\n"
            "**Supported Formats:**\n"
            "• Videos (MP4, AVI, MOV)\n"
            "• Audio (MP3, M4A)\n"
            "• Images (JPG, PNG)\n\n"
            "**Note:** Large files (>50MB) may take longer to process."
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
        self.metrics.increment_command_usage('help')
    
    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user_id = update.effective_user.id
        session = self.user_sessions.get(user_id, {})
        
        status_text = (
            f"📊 **Download Status**\n\n"
            f"**Current State:** {session.get('state', 'idle').title()}\n"
            f"**Downloads Completed:** {session.get('downloads_count', 0)}\n"
            f"**Current Download:** {session.get('current_download', 'None')}\n\n"
            f"**Bot Status:** {'🟢 Running' if self.is_running else '🔴 Stopped'}"
        )
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
        self.metrics.increment_command_usage('status')
    
    async def _cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel command"""
        user_id = update.effective_user.id
        session = self.user_sessions.get(user_id, {})
        
        if session.get('state') == 'downloading':
            session['state'] = 'idle'
            session['current_download'] = None
            await update.message.reply_text("✅ Download cancelled successfully.")
            self.metrics.increment_command_usage('cancel')
        else:
            await update.message.reply_text("ℹ️ No active download to cancel.")
    
    async def _instagram_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /instagram command for Instagram-related operations"""
        if not self.instagram_client.is_token_valid():
            await update.message.reply_text(
                "❌ Instagram integration not configured. "
                "Please set INSTAGRAM_ACCESS_TOKEN environment variable."
            )
            return
        
        if not context.args:
            await update.message.reply_text(
                "📱 **Instagram Commands**\n\n"
                "`/instagram profile [username]` - Get account profile\n"
                "`/instagram media [username] [limit]` - Get recent media\n"
                "`/instagram stories [username]` - Get stories\n"
                "`/instagram monitor [username]` - Start monitoring account\n"
                "`/instagram insights [username]` - Get account insights\n\n"
                "**Note**: Replace [username] with the Instagram username you want to check.",
                parse_mode='Markdown'
            )
            return
        
        subcommand = context.args[0].lower()
        
        if subcommand == "profile":
            await self._handle_instagram_profile(update, context)
        elif subcommand == "media":
            await self._handle_instagram_media(update, context)
        elif subcommand == "stories":
            await self._handle_instagram_stories(update, context)
        elif subcommand == "monitor":
            await self._handle_instagram_monitor(update, context)
        elif subcommand == "insights":
            await self._handle_instagram_insights(update, context)
        else:
            await update.message.reply_text(
                f"❌ Unknown Instagram subcommand: {subcommand}\n"
                "Use `/instagram` to see available commands."
            )
    
    async def _monitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /monitor command to start monitoring Instagram accounts"""
        if not context.args:
            await update.message.reply_text(
                "📊 **Monitoring Commands**\n\n"
                "`/monitor [username]` - Start monitoring an Instagram account\n"
                "`/unmonitor [username]` - Stop monitoring an account\n"
                "`/monitor list` - List monitored accounts\n"
                "`/monitor check` - Check all monitored accounts for new content\n\n"
                "**Example**: `/monitor instagram`",
                parse_mode='Markdown'
            )
            return
        
        subcommand = context.args[0].lower()
        
        if subcommand == "list":
            await self._handle_monitor_list(update, context)
        elif subcommand == "check":
            await self._handle_monitor_check(update, context)
        else:
            # Assume it's a username to monitor
            await self._handle_monitor_add(update, context)
    
    async def _unmonitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unmonitor command to stop monitoring accounts"""
        if not context.args:
            await update.message.reply_text(
                "❌ Please specify a username to stop monitoring.\n"
                "**Example**: `/unmonitor instagram`",
                parse_mode='Markdown'
            )
            return
        
        username = context.args[0].lower()
        await self._handle_unmonitor(update, context, username)
    
    async def _handle_instagram_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Instagram profile command"""
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Please specify a username.\n"
                "**Example**: `/instagram profile instagram`",
                parse_mode='Markdown'
            )
            return
        
        username = context.args[1]
        await update.message.reply_text(f"🔍 Fetching profile for @{username}...")
        
        try:
            profile = await self.instagram_client.get_user_profile(username)
            if profile:
                profile_text = (
                    f"📱 **@{username} Profile**\n\n"
                    f"**Account Type**: {profile.get('account_type', 'Unknown')}\n"
                    f"**Media Count**: {profile.get('media_count', 'Unknown')}\n"
                    f"**ID**: {profile.get('id', 'Unknown')}"
                )
                await update.message.reply_text(profile_text, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ Could not fetch profile for @{username}")
        except Exception as e:
            await update.message.reply_text(f"❌ Error fetching profile: {str(e)}")
    
    async def _handle_instagram_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Instagram media command"""
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Please specify a username.\n"
                "**Example**: `/instagram media instagram 5`",
                parse_mode='Markdown'
            )
            return
        
        username = context.args[1]
        limit = int(context.args[2]) if len(context.args) > 2 else 5
        
        await update.message.reply_text(f"📸 Fetching recent media from @{username}...")
        
        try:
            media = await self.instagram_client.get_user_media(username, limit)
            if media:
                summary = self.instagram_client.format_content_summary(media)
                await update.message.reply_text(summary, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ No media found for @{username}")
        except Exception as e:
            await update.message.reply_text(f"❌ Error fetching media: {str(e)}")
    
    async def _handle_instagram_stories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Instagram stories command"""
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Please specify a username.\n"
                "**Example**: `/instagram stories instagram`",
                parse_mode='Markdown'
            )
            return
        
        username = context.args[1]
        await update.message.reply_text(f"📖 Fetching stories from @{username}...")
        
        try:
            stories = await self.instagram_client.get_stories(username)
            if stories:
                summary = self.instagram_client.format_content_summary(stories)
                await update.message.reply_text(summary, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ No stories found for @{username}")
        except Exception as e:
            await update.message.reply_text(f"❌ Error fetching stories: {str(e)}")
    
    async def _handle_instagram_monitor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Instagram monitor command"""
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Please specify a username to monitor.\n"
                "**Example**: `/instagram monitor instagram`",
                parse_mode='Markdown'
            )
            return
        
        username = context.args[1].lower()
        user_id = update.effective_user.id
        
        # Initialize user's monitored accounts list
        if user_id not in self.monitored_accounts:
            self.monitored_accounts[user_id] = []
        
        if username in self.monitored_accounts[user_id]:
            await update.message.reply_text(f"ℹ️ Already monitoring @{username}")
            return
        
        # Add to monitored accounts
        self.monitored_accounts[user_id].append(username)
        
        await update.message.reply_text(
            f"✅ Now monitoring @{username}\n"
            f"Use `/monitor check` to check for new content\n"
            f"Use `/unmonitor {username}` to stop monitoring"
        )
    
    async def _handle_instagram_insights(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Instagram insights command"""
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Please specify a username.\n"
                "**Example**: `/instagram insights instagram`",
                parse_mode='Markdown'
            )
            return
        
        username = context.args[1]
        await update.message.reply_text(f"📊 Fetching insights for @{username}...")
        
        try:
            insights = await self.instagram_client.get_account_insights(username)
            if 'error' not in insights:
                account = insights['account']
                insights_text = (
                    f"📊 **@{username} Insights**\n\n"
                    f"**Total Media**: {insights['total_media']}\n"
                    f"**Account Type**: {account.get('account_type', 'Unknown')}\n"
                    f"**Last Updated**: {insights['last_updated']}"
                )
                await update.message.reply_text(insights_text, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ {insights['error']}")
        except Exception as e:
            await update.message.reply_text(f"❌ Error fetching insights: {str(e)}")
    
    async def _handle_monitor_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle monitor list command"""
        user_id = update.effective_user.id
        
        if user_id not in self.monitored_accounts or not self.monitored_accounts[user_id]:
            await update.message.reply_text("📋 You're not monitoring any accounts yet.")
            return
        
        accounts = self.monitored_accounts[user_id]
        accounts_text = "📋 **Monitored Accounts**\n\n"
        
        for i, account in enumerate(accounts, 1):
            accounts_text += f"{i}. @{account}\n"
        
        accounts_text += f"\nUse `/monitor check` to check for new content"
        await update.message.reply_text(accounts_text, parse_mode='Markdown')
    
    async def _handle_monitor_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle monitor check command"""
        user_id = update.effective_user.id
        
        if user_id not in self.monitored_accounts or not self.monitored_accounts[user_id]:
            await update.message.reply_text("📋 You're not monitoring any accounts yet.")
            return
        
        accounts = self.monitored_accounts[user_id]
        await update.message.reply_text(f"🔍 Checking {len(accounts)} monitored accounts...")
        
        new_content_found = False
        
        for account in accounts:
            try:
                result = await self.instagram_client.monitor_account(account)
                if 'error' not in result and result.get('new_content'):
                    new_content_found = True
                    content_count = len(result['new_content'])
                    await update.message.reply_text(
                        f"🆕 **New content from @{account}**\n\n"
                        f"Found {content_count} new items!\n\n"
                        f"Use `/instagram media {account}` to see the content",
                        parse_mode='Markdown'
                    )
            except Exception as e:
                logger.error(f"Error checking account {account}: {e}")
        
        if not new_content_found:
            await update.message.reply_text("✅ No new content found from monitored accounts.")
    
    async def _handle_monitor_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle adding an account to monitor"""
        username = context.args[0].lower()
        user_id = update.effective_user.id
        
        # Initialize user's monitored accounts list
        if user_id not in self.monitored_accounts:
            self.monitored_accounts[user_id] = []
        
        if username in self.monitored_accounts[user_id]:
            await update.message.reply_text(f"ℹ️ Already monitoring @{username}")
            return
        
        # Add to monitored accounts
        self.monitored_accounts[user_id].append(username)
        
        await update.message.reply_text(
            f"✅ Now monitoring @{username}\n"
            f"Use `/monitor check` to check for new content\n"
            f"Use `/unmonitor {username}` to stop monitoring"
        )
    
    async def _handle_unmonitor(self, update: Update, context: ContextTypes.DEFAULT_TYPE, username: str):
        """Handle unmonitor command"""
        user_id = update.effective_user.id
        
        if user_id not in self.monitored_accounts:
            await update.message.reply_text("📋 You're not monitoring any accounts.")
            return
        
        if username not in self.monitored_accounts[user_id]:
            await update.message.reply_text(f"❌ Not monitoring @{username}")
            return
        
        # Remove from monitored accounts
        self.monitored_accounts[user_id].remove(username)
        
        await update.message.reply_text(f"✅ Stopped monitoring @{username}")
    
    async def _auto_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /auto command for automatic content delivery"""
        if not context.args:
            await update.message.reply_text(
                "🤖 **Automatic Content Delivery**\n\n"
                "`/auto start` - Start automatic monitoring\n"
                "`/auto stop` - Stop automatic monitoring\n"
                "`/auto status` - Check monitoring status\n"
                "`/auto check [username]` - Force check account\n"
                "`/auto preferences` - Set delivery preferences\n\n"
                "**How it works:**\n"
                "1. Monitor Instagram accounts for new content\n"
                "2. Automatically download new reels/posts\n"
                "3. Send directly to your Telegram\n\n"
                "**Example:** `/auto start`",
                parse_mode='Markdown'
            )
            return
        
        subcommand = context.args[0].lower()
        
        if subcommand == "start":
            await self._handle_auto_start(update, context)
        elif subcommand == "stop":
            await self._handle_auto_stop(update, context)
        elif subcommand == "status":
            await self._handle_auto_status(update, context)
        elif subcommand == "check":
            await self._handle_auto_check(update, context)
        elif subcommand == "preferences":
            await self._handle_auto_preferences(update, context)
        else:
            await update.message.reply_text(
                f"❌ Unknown auto subcommand: {subcommand}\n"
                "Use `/auto` to see available commands."
            )
    
    async def _preferences_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /preferences command for user preferences"""
        if not context.args:
            await update.message.reply_text(
                "⚙️ **User Preferences**\n\n"
                "`/preferences content [type] [on/off]` - Set content type preferences\n"
                "`/preferences notifications [type] [on/off]` - Set notification preferences\n"
                "`/preferences view` - View current preferences\n"
                "`/preferences reset` - Reset to defaults\n\n"
                "**Content Types:** media, story\n"
                "**Notification Types:** immediate, daily_summary\n\n"
                "**Examples:**\n"
                "`/preferences content story off` - Don't send stories\n"
                "`/preferences notifications daily_summary on` - Enable daily summaries",
                parse_mode='Markdown'
            )
            return
        
        subcommand = context.args[0].lower()
        
        if subcommand == "content":
            await self._handle_content_preferences(update, context)
        elif subcommand == "notifications":
            await self._handle_notification_preferences(update, context)
        elif subcommand == "view":
            await self._handle_view_preferences(update, context)
        elif subcommand == "reset":
            await self._handle_reset_preferences(update, context)
        else:
            await update.message.reply_text(
                f"❌ Unknown preferences subcommand: {subcommand}\n"
                "Use `/preferences` to see available commands."
            )
    
    async def _handle_auto_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start automatic Instagram monitoring"""
        user_id = update.effective_user.id
        
        # Check if user has any monitored accounts
        if user_id not in self.monitored_accounts or not self.monitored_accounts[user_id]:
            await update.message.reply_text(
                "❌ You need to monitor at least one account first!\n\n"
                "**Steps:**\n"
                "1. Use `/monitor [username]` to add accounts\n"
                "2. Then use `/auto start` to begin automatic delivery"
            )
            return
        
        try:
            # Start the monitoring service
            await self.instagram_monitor.start_monitoring()
            
            # Add user to monitoring system
            for username in self.monitored_accounts[user_id]:
                self.instagram_monitor.add_user_monitoring(user_id, username)
            
            await update.message.reply_text(
                "🤖 **Automatic monitoring started!**\n\n"
                f"Monitoring {len(self.monitored_accounts[user_id])} accounts:\n"
                + "\n".join([f"• @{username}" for username in self.monitored_accounts[user_id]]) +
                "\n\n**What happens now:**\n"
                "• Bot checks for new content every 5 minutes\n"
                "• New reels/posts are automatically downloaded\n"
                "• Content is sent directly to your Telegram\n"
                "\nUse `/auto status` to check status\n"
                "Use `/auto stop` to stop monitoring"
            )
            
        except Exception as e:
            logger.error(f"Failed to start auto monitoring: {e}")
            await update.message.reply_text(f"❌ Failed to start monitoring: {str(e)}")
    
    async def _handle_auto_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop automatic Instagram monitoring"""
        user_id = update.effective_user.id
        
        try:
            # Remove user from monitoring system
            if user_id in self.monitored_accounts:
                for username in self.monitored_accounts[user_id]:
                    self.instagram_monitor.remove_user_monitoring(user_id, username)
            
            # Check if any other users are monitoring
            global_status = self.instagram_monitor.get_global_monitoring_status()
            if global_status['total_users'] == 0:
                await self.instagram_monitor.stop_monitoring()
            
            await update.message.reply_text(
                "🛑 **Automatic monitoring stopped!**\n\n"
                "You will no longer receive automatic content delivery.\n"
                "Your monitored accounts are still saved.\n\n"
                "Use `/auto start` to resume monitoring"
            )
            
        except Exception as e:
            logger.error(f"Failed to stop auto monitoring: {e}")
            await update.message.reply_text(f"❌ Failed to stop monitoring: {str(e)}")
    
    async def _handle_auto_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show automatic monitoring status"""
        user_id = update.effective_user.id
        
        # Get user's monitoring status
        user_status = self.instagram_monitor.get_user_monitoring_status(user_id)
        global_status = self.instagram_monitor.get_global_monitoring_status()
        
        status_text = "🤖 **Automatic Monitoring Status**\n\n"
        
        if user_status['monitoring']:
            status_text += "✅ **Your Status:** Active\n"
            status_text += f"📋 **Monitored Accounts:** {len(user_status['accounts'])}\n"
            for account in user_status['accounts']:
                status_text += f"   • @{account}\n"
        else:
            status_text += "❌ **Your Status:** Inactive\n"
            status_text += "Use `/auto start` to begin monitoring\n"
        
        status_text += f"\n🌐 **Global Status:**\n"
        status_text += f"• Total Users: {global_status['total_users']}\n"
        status_text += f"• Total Accounts: {global_status['total_accounts']}\n"
        status_text += f"• Monitoring Active: {'Yes' if global_status['is_monitoring'] else 'No'}\n"
        status_text += f"• Check Interval: {global_status['check_interval']} seconds\n"
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def _handle_auto_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Force check a specific account"""
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Please specify an account to check.\n"
                "**Example:** `/auto check instagram`"
            )
            return
        
        username = context.args[1].lower()
        user_id = update.effective_user.id
        
        # Check if user is monitoring this account
        if user_id not in self.monitored_accounts or username not in self.monitored_accounts[user_id]:
            await update.message.reply_text(
                f"❌ You're not monitoring @{username}\n"
                "Use `/monitor {username}` to start monitoring"
            )
            return
        
        await update.message.reply_text(f"🔍 Force checking @{username} for new content...")
        
        try:
            result = await self.instagram_monitor.force_check_account(username)
            
            if 'error' not in result:
                await update.message.reply_text(
                    f"✅ **Force check completed!**\n\n"
                    f"Account: @{username}\n"
                    f"Status: {result['message']}\n"
                    f"Time: {result['timestamp']}"
                )
            else:
                await update.message.reply_text(f"❌ {result['error']}")
                
        except Exception as e:
            logger.error(f"Force check failed: {e}")
            await update.message.reply_text(f"❌ Force check failed: {str(e)}")
    
    async def _handle_auto_preferences(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set automatic delivery preferences"""
        await update.message.reply_text(
            "⚙️ **Automatic Delivery Preferences**\n\n"
            "Use these commands to customize your experience:\n\n"
            "**Content Types:**\n"
            "`/preferences content media on` - Receive posts/reels\n"
            "`/preferences content story off` - Don't receive stories\n\n"
            "**Notifications:**\n"
            "`/preferences notifications immediate on` - Instant delivery\n"
            "`/preferences notifications daily_summary on` - Daily summaries\n\n"
            "**View Current Settings:**\n"
            "`/preferences view`"
        )
    
    async def _handle_content_preferences(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle content type preferences"""
        if len(context.args) < 3:
            await update.message.reply_text(
                "❌ Please specify content type and setting.\n"
                "**Example:** `/preferences content story off`"
            )
            return
        
        content_type = context.args[1].lower()
        setting = context.args[2].lower()
        
        if content_type not in ['media', 'story']:
            await update.message.reply_text(
                "❌ Invalid content type. Use: media, story"
            )
            return
        
        if setting not in ['on', 'off']:
            await update.message.reply_text(
                "❌ Invalid setting. Use: on, off"
            )
            return
        
        user_id = update.effective_user.id
        enabled = setting == 'on'
        
        # Update user preferences
        self.instagram_monitor.update_user_preferences(user_id, {
            'content_types': {content_type: enabled}
        })
        
        status = "enabled" if enabled else "disabled"
        await update.message.reply_text(
            f"✅ **Content preference updated!**\n\n"
            f"**{content_type.title()}** content is now **{status}**\n\n"
            f"Use `/preferences view` to see all settings"
        )
    
    async def _handle_notification_preferences(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle notification preferences"""
        if len(context.args) < 3:
            await update.message.reply_text(
                "❌ Please specify notification type and setting.\n"
                "**Example:** `/preferences notifications immediate on`"
            )
            return
        
        notification_type = context.args[1].lower()
        setting = context.args[2].lower()
        
        if notification_type not in ['immediate', 'daily_summary']:
            await update.message.reply_text(
                "❌ Invalid notification type. Use: immediate, daily_summary"
            )
            return
        
        if setting not in ['on', 'off']:
            await update.message.reply_text(
                "❌ Invalid setting. Use: on, off"
            )
            return
        
        user_id = update.effective_user.id
        enabled = setting == 'on'
        
        # Update user preferences
        self.instagram_monitor.update_user_preferences(user_id, {
            'notification_preferences': {notification_type: enabled}
        })
        
        status = "enabled" if enabled else "disabled"
        await update.message.reply_text(
            f"✅ **Notification preference updated!**\n\n"
            f"**{notification_type.replace('_', ' ').title()}** notifications are now **{status}**\n\n"
            f"Use `/preferences view` to see all settings"
        )
    
    async def _handle_view_preferences(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View current user preferences"""
        user_id = update.effective_user.id
        user_status = self.instagram_monitor.get_user_monitoring_status(user_id)
        
        if not user_status['monitoring']:
            await update.message.reply_text(
                "❌ You don't have any preferences set yet.\n"
                "Start monitoring accounts first with `/monitor [username]`"
            )
            return
        
        preferences = user_status['preferences']
        
        preferences_text = "⚙️ **Your Current Preferences**\n\n"
        
        # Content type preferences
        preferences_text += "**Content Types:**\n"
        content_types = preferences.get('content_types', {})
        preferences_text += f"• Posts/Reels: {'✅' if content_types.get('media', True) else '❌'}\n"
        preferences_text += f"• Stories: {'✅' if content_types.get('story', True) else '❌'}\n\n"
        
        # Notification preferences
        preferences_text += "**Notifications:**\n"
        notification_prefs = preferences.get('notification_preferences', {})
        preferences_text += f"• Immediate: {'✅' if notification_prefs.get('immediate', True) else '❌'}\n"
        preferences_text += f"• Daily Summary: {'✅' if notification_prefs.get('daily_summary', False) else '❌'}\n\n"
        
        # Monitored accounts
        preferences_text += f"**Monitored Accounts:** {len(user_status['accounts'])}\n"
        for account in user_status['accounts']:
            preferences_text += f"• @{account}\n"
        
        await update.message.reply_text(preferences_text, parse_mode='Markdown')
    
    async def _handle_reset_preferences(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reset user preferences to defaults"""
        user_id = update.effective_user.id
        
        # Reset to default preferences
        default_preferences = {
            'content_types': {
                'media': True,
                'story': True
            },
            'notification_preferences': {
                'immediate': True,
                'daily_summary': False
            }
        }
        
        self.instagram_monitor.update_user_preferences(user_id, default_preferences)
        
        await update.message.reply_text(
            "🔄 **Preferences reset to defaults!**\n\n"
            "**Default Settings:**\n"
            "• Posts/Reels: ✅ Enabled\n"
            "• Stories: ✅ Enabled\n"
            "• Immediate Notifications: ✅ Enabled\n"
            "• Daily Summaries: ❌ Disabled\n\n"
            "Use `/preferences view` to see current settings"
        )
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages (media links)"""
        user_id = update.effective_user.id
        message_text = update.message.text.strip()
        
        # Validate URL
        if not validate_url(message_text):
            await update.message.reply_text(
                "❌ Please send a valid media link (YouTube, TikTok, Instagram, etc.)"
            )
            return
        
        # Check if user is already downloading
        session = self.user_sessions.get(user_id, {})
        if session.get('state') == 'downloading':
            await update.message.reply_text(
                "⏳ You already have a download in progress. Please wait or use /cancel."
            )
            return
        
        # Start download process
        await self._process_download(update, context, message_text, user_id)
    
    async def _process_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               url: str, user_id: int):
        """Process media download with proper error handling"""
        session = self.user_sessions.get(user_id, {})
        session['state'] = 'downloading'
        session['current_download'] = url
        
        # Send initial response
        status_message = await update.message.reply_text(
            f"🔄 Processing your media link...\n\n"
            f"📎 URL: {url}\n"
            f"⏱️ This may take a few moments..."
        )
        
        try:
            # Download media
            download_info = await self.downloader.download_media(url)
            
            if not download_info or not download_info.get('file_path'):
                raise Exception("Download failed - no file received")
            
            file_path = download_info['file_path']
            file_size = download_info.get('file_size', 0)
            
            # Process media if needed
            processed_file = await self.processor.process_media(file_path, file_size)
            
            # Send media file
            await self._send_media_file(update, context, processed_file, download_info)
            
            # Update metrics and session
            session['downloads_count'] += 1
            session['state'] = 'idle'
            session['current_download'] = None
            
            self.metrics.increment_successful_downloads()
            logger.info(f"User {user_id} successfully downloaded media from {url}")
            
        except Exception as e:
            error_msg = f"❌ Failed to download media: {str(e)}"
            await update.message.reply_text(error_msg)
            
            session['state'] = 'idle'
            session['current_download'] = None
            
            self.metrics.increment_failed_downloads()
            logger.error(f"Download failed for user {user_id}, URL {url}: {e}")
        
        finally:
            # Clean up temporary files
            await self._cleanup_files([url])
    
    async def _send_media_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                              file_path: str, download_info: Dict[str, Any]):
        """Send media file to user with proper formatting"""
        try:
            file_size = download_info.get('file_size', 0)
            title = download_info.get('title', 'Unknown')
            
            # Format file size
            if file_size > 1024 * 1024 * 1024:  # > 1GB
                size_str = f"{file_size / (1024**3):.1f} GB"
            elif file_size > 1024 * 1024:  # > 1MB
                size_str = f"{file_size / (1024**2):.1f} MB"
            else:
                size_str = f"{file_size / 1024:.1f} KB"
            
            # Send file with caption
            caption = (
                f"✅ **Download Complete!**\n\n"
                f"📹 **Title:** {title}\n"
                f"📏 **Size:** {size_str}\n"
                f"🎯 **Quality:** {download_info.get('quality', 'Best available')}"
            )
            
            with open(file_path, 'rb') as file:
                await update.message.reply_document(
                    document=file,
                    caption=caption,
                    parse_mode='Markdown'
                )
            
            # Send success message
            await update.message.reply_text(
                "🎉 Your media has been downloaded and sent successfully!\n"
                "💡 Send another link to download more media."
            )
            
        except Exception as e:
            logger.error(f"Failed to send media file: {e}")
            await update.message.reply_text(
                "❌ File downloaded but failed to send. Please try again."
            )
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()
        
        # Handle different callback actions
        if query.data == 'help':
            await self._help_command(update, context)
        elif query.data == 'status':
            await self._status_command(update, context)
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors gracefully"""
        logger.error(f"Exception while handling an update: {context.error}")
        
        # Send user-friendly error message
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred while processing your request. "
                "Please try again later or contact support if the problem persists."
            )
        
        self.metrics.increment_errors()
    
    async def _cleanup_files(self, file_paths: list):
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup file {file_path}: {e}")
    
    def start(self):
        """Start the bot"""
        if self.is_running:
            logger.warning("Bot is already running")
            return
        
        try:
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            self.is_running = True
            logger.info("Bot started successfully")
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise
    
    def stop(self):
        """Stop the bot"""
        if not self.is_running:
            logger.warning("Bot is not running")
            return
        
        try:
            self.application.stop()
            self.is_running = False
            logger.info("Bot stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop bot: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get bot status information"""
        return {
            'is_running': self.is_running,
            'active_users': len(self.user_sessions),
            'total_downloads': sum(
                session.get('downloads_count', 0) 
                for session in self.user_sessions.values()
            ),
            'metrics': self.metrics.get_summary()
        }
