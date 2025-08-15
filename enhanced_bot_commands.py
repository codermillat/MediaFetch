"""
Enhanced Bot Commands for MediaFetch
Integrates the sophisticated binding system with the Telegram bot
"""

import logging
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from binding_manager import BindingManager, BindingError, ContentDeliveryError

logger = logging.getLogger(__name__)

class EnhancedBotCommands:
    """Enhanced bot commands with binding system integration"""
    
    def __init__(self, bot_instance, db_ops):
        self.bot = bot_instance
        self.db_ops = db_ops
        self.binding_manager = BindingManager(db_ops)
    
    async def handle_bind_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /bind command - start the binding process"""
        try:
            user = update.effective_user
            user_id = user.id
            
            # Check if user provided Instagram username
            if not context.args:
                await update.message.reply_text(
                    "🔗 **Instagram Binding**\n\n"
                    "To bind your Telegram account to an Instagram account:\n\n"
                    "1️⃣ Use: `/bind @username`\n"
                    "2️⃣ You'll receive a unique code\n"
                    "3️⃣ Send that code to @username on Instagram\n"
                    "4️⃣ Once confirmed, you'll receive all their reels automatically!\n\n"
                    "**Example:** `/bind @natgeo`"
                )
                return
            
            instagram_username = context.args[0].lstrip('@')
            
            # Validate Instagram username format
            if not self._is_valid_instagram_username(instagram_username):
                await update.message.reply_text(
                    "❌ **Invalid Instagram Username**\n\n"
                    "Please provide a valid Instagram username:\n"
                    "• Use letters, numbers, dots, and underscores\n"
                    "• Example: `/bind natgeo` or `/bind @natgeo`"
                )
                return
            
            # Show processing message
            processing_msg = await update.message.reply_text(
                f"⏳ Processing binding request for @{instagram_username}..."
            )
            
            try:
                # Create binding request
                result = await self.binding_manager.create_binding_request(user_id, instagram_username)
                
                # Update processing message with success
                await processing_msg.edit_text(
                    f"✅ **Binding Code Generated!**\n\n"
                    f"**Instagram Account:** @{instagram_username}\n"
                    f"**Your Code:** `{result['binding_code']}`\n"
                    f"**Expires:** {result['expires_at']}\n\n"
                    f"📱 **Next Steps:**\n"
                    f"1. Go to Instagram\n"
                    f"2. Send this code to @{instagram_username}\n"
                    f"3. Wait for confirmation\n\n"
                    f"🔒 **Security:** This code is unique to you and expires in 24 hours."
                )
                
                # Log the binding request
                logger.info(f"User {user_id} requested binding to @{instagram_username}")
                
            except BindingError as e:
                if e.error_code == "ALREADY_BOUND":
                    await processing_msg.edit_text(
                        f"ℹ️ **Already Bound**\n\n"
                        f"You are already bound to @{instagram_username}.\n"
                        f"Use `/bindings` to see your current bindings."
                    )
                else:
                    await processing_msg.edit_text(
                        f"❌ **Binding Failed**\n\n"
                        f"Error: {e.message}\n\n"
                        f"Please try again or contact support."
                    )
                    logger.error(f"Binding failed for user {user_id}: {e}")
            
            except Exception as e:
                await processing_msg.edit_text(
                    "❌ **Unexpected Error**\n\n"
                    "Something went wrong. Please try again later."
                )
                logger.error(f"Unexpected error in bind command for user {user_id}: {e}")
                
        except Exception as e:
            logger.error(f"Error in bind command: {e}")
            await update.message.reply_text(
                "❌ **Command Error**\n\n"
                "Something went wrong. Please try again."
            )
    
    async def handle_bindings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /bindings command - show user's current bindings"""
        try:
            user = update.effective_user
            user_id = user.id
            
            # Get user's bindings
            bindings = await self.binding_manager.get_user_bindings(user_id)
            
            if not bindings:
                await update.message.reply_text(
                    "🔗 **Your Bindings**\n\n"
                    "You don't have any active Instagram bindings yet.\n\n"
                    "Use `/bind @username` to start binding to Instagram accounts!"
                )
                return
            
            # Create binding list message
            binding_text = "🔗 **Your Active Bindings**\n\n"
            
            for binding in bindings:
                status_emoji = "✅" if binding['binding_status'] == 'confirmed' else "⏳"
                status_text = "Active" if binding['binding_status'] == 'confirmed' else "Pending"
                
                binding_text += (
                    f"{status_emoji} **@{binding['instagram_username']}**\n"
                    f"   Status: {status_text}\n"
                    f"   Since: {binding['created_at'][:10]}\n\n"
                )
            
            binding_text += (
                "💡 **Commands:**\n"
                "• `/unbind @username` - Remove a binding\n"
                "• `/bind @username` - Add new binding\n"
                "• `/help` - See all commands"
            )
            
            # Create inline keyboard for management
            keyboard = []
            for binding in bindings:
                if binding['binding_status'] == 'confirmed':
                    keyboard.append([
                        InlineKeyboardButton(
                            f"❌ Unbind @{binding['instagram_username']}",
                            callback_data=f"unbind:{binding['instagram_username']}"
                        )
                    ])
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            await update.message.reply_text(
                binding_text,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in bindings command: {e}")
            await update.message.reply_text(
                "❌ **Command Error**\n\n"
                "Something went wrong. Please try again."
            )
    
    async def handle_unbind_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unbind command - remove a binding"""
        try:
            user = update.effective_user
            user_id = user.id
            
            if not context.args:
                await update.message.reply_text(
                    "❌ **Unbind Command**\n\n"
                    "To remove a binding:\n"
                    "`/unbind @username`\n\n"
                    "**Example:** `/unbind @natgeo`\n\n"
                    "Use `/bindings` to see your current bindings."
                )
                return
            
            instagram_username = context.args[0].lstrip('@')
            
            # Show processing message
            processing_msg = await update.message.reply_text(
                f"⏳ Removing binding to @{instagram_username}..."
            )
            
            try:
                # Revoke binding
                success = await self.binding_manager.revoke_binding(user_id, instagram_username)
                
                if success:
                    await processing_msg.edit_text(
                        f"✅ **Binding Removed**\n\n"
                        f"You are no longer bound to @{instagram_username}.\n"
                        f"You will no longer receive automatic content from this account."
                    )
                    logger.info(f"User {user_id} removed binding to @{instagram_username}")
                else:
                    await processing_msg.edit_text(
                        f"ℹ️ **No Binding Found**\n\n"
                        f"You don't have an active binding to @{instagram_username}."
                    )
                
            except Exception as e:
                await processing_msg.edit_text(
                    "❌ **Unbind Failed**\n\n"
                    "Something went wrong. Please try again."
                )
                logger.error(f"Unbind failed for user {user_id}: {e}")
                
        except Exception as e:
            logger.error(f"Error in unbind command: {e}")
            await update.message.reply_text(
                "❌ **Command Error**\n\n"
                "Something went wrong. Please try again."
            )
    
    async def handle_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command - show enhanced help with binding system"""
        help_text = (
            "🎬 **MediaFetch Bot - Complete Guide**\n\n"
            "**🔗 Binding System (NEW!)**\n"
            "• `/bind @username` - Bind to Instagram account\n"
            "• `/bindings` - View your active bindings\n"
            "• `/unbind @username` - Remove a binding\n\n"
            "**📥 Media Downloads**\n"
            "• Send any media link (YouTube, TikTok, Instagram, etc.)\n"
            "• Bot will download and send the media back\n\n"
            "**📊 Status & Info**\n"
            "• `/status` - Check download progress\n"
            "• `/cancel` - Cancel current download\n"
            "• `/help` - Show this help message\n\n"
            "**🔒 How Binding Works**\n"
            "1. Use `/bind @username` to get a unique code\n"
            "2. Send that code to @username on Instagram\n"
            "3. Once confirmed, you'll receive ALL their reels automatically!\n"
            "4. No more manual checking - content comes to you!\n\n"
            "**💡 Pro Tips**\n"
            "• You can bind to multiple Instagram accounts\n"
            "• Bindings are permanent until you remove them\n"
            "• All content is automatically processed and optimized\n\n"
            "**🆘 Support**\n"
            "If you need help, contact the bot administrator."
        )
        
        await update.message.reply_text(help_text)
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data.startswith("unbind:"):
                instagram_username = query.data.split(":")[1]
                user_id = query.from_user.id
                
                # Show confirmation
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_unbind:{instagram_username}"),
                        InlineKeyboardButton("❌ Cancel", callback_data="cancel_unbind")
                    ]
                ]
                
                await query.edit_message_text(
                    f"⚠️ **Confirm Unbinding**\n\n"
                    f"Are you sure you want to remove your binding to @{instagram_username}?\n\n"
                    f"This will stop automatic content delivery from this account.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            
            elif query.data.startswith("confirm_unbind:"):
                instagram_username = query.data.split(":")[1]
                user_id = query.from_user.id
                
                try:
                    success = await self.binding_manager.revoke_binding(user_id, instagram_username)
                    
                    if success:
                        await query.edit_message_text(
                            f"✅ **Binding Removed**\n\n"
                            f"You are no longer bound to @{instagram_username}.\n"
                            f"Use `/bindings` to see your remaining bindings."
                        )
                    else:
                        await query.edit_message_text(
                            f"ℹ️ **No Binding Found**\n\n"
                            f"You don't have an active binding to @{instagram_username}."
                        )
                        
                except Exception as e:
                    await query.edit_message_text(
                        "❌ **Unbind Failed**\n\n"
                        "Something went wrong. Please try again."
                    )
                    logger.error(f"Callback unbind failed for user {user_id}: {e}")
            
            elif query.data == "cancel_unbind":
                await query.edit_message_text(
                    "❌ **Unbinding Cancelled**\n\n"
                    "Your binding remains active."
                )
                
        except Exception as e:
            logger.error(f"Error in callback query handler: {e}")
            try:
                await query.answer("❌ Error occurred")
            except:
                pass
    
    def _is_valid_instagram_username(self, username: str) -> bool:
        """Validate Instagram username format"""
        import re
        # Instagram usernames: 1-30 characters, letters, numbers, dots, underscores
        pattern = r'^[a-zA-Z0-9._]{1,30}$'
        return bool(re.match(pattern, username))
    
    async def handle_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced /start command with binding system introduction"""
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
            "**🚀 Quick Start:**\n"
            "1. `/bind @username` - Bind to an Instagram account\n"
            "2. Send any media link to download\n"
            "3. `/help` - See all available commands\n\n"
            "**💡 Pro Tip:** Once you bind to Instagram accounts, you'll receive "
            "every new reel automatically - set it and forget it! 🎯"
        )
        
        # Create inline keyboard for quick actions
        keyboard = [
            [
                InlineKeyboardButton("🔗 Start Binding", callback_data="start_binding"),
                InlineKeyboardButton("📥 Download Media", callback_data="download_media")
            ],
            [
                InlineKeyboardButton("📚 Help", callback_data="show_help"),
                InlineKeyboardButton("🔗 My Bindings", callback_data="show_bindings")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup
        )
    
    async def handle_start_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle start command callback queries"""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == "start_binding":
                await query.edit_message_text(
                    "🔗 **Instagram Binding Guide**\n\n"
                    "**Step 1:** Choose an Instagram account to bind to\n"
                    "**Step 2:** Use `/bind @username` (replace @username)\n"
                    "**Step 3:** You'll receive a unique code\n"
                    "**Step 4:** Send that code to @username on Instagram\n"
                    "**Step 5:** Once confirmed, you'll get ALL their reels automatically!\n\n"
                    "**Example:** `/bind @natgeo`\n\n"
                    "💡 **Pro Tip:** You can bind to multiple accounts!"
                )
            
            elif query.data == "download_media":
                await query.edit_message_text(
                    "📥 **Media Download Guide**\n\n"
                    "Simply send me any media link from:\n\n"
                    "• **YouTube** - Videos, shorts, playlists\n"
                    "• **TikTok** - All TikTok videos\n"
                    "• **Instagram** - Posts, reels, stories\n"
                    "• **Twitter/X** - Videos and media\n"
                    "• **Reddit** - Video posts\n"
                    "• **Vimeo** - Professional videos\n"
                    "• **SoundCloud** - Audio tracks\n\n"
                    "**Just paste the link and I'll handle the rest!** 🚀"
                )
            
            elif query.data == "show_help":
                await self.handle_help_command(update, context)
            
            elif query.data == "show_bindings":
                await self.handle_bindings_command(update, context)
                
        except Exception as e:
            logger.error(f"Error in start callback handler: {e}")
            try:
                await query.answer("❌ Error occurred")
            except:
                pass
