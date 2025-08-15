"""
Instagram Bot Integration for MediaFetch
Handles binding confirmations and content delivery from Instagram to Telegram
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from instagrapi import Client
from binding_manager import BindingManager, ContentDeliveryManager, BindingError, ContentDeliveryError

logger = logging.getLogger(__name__)

class InstagramBotIntegration:
    """Integrates Instagram bot with MediaFetch binding system"""
    
    def __init__(self, db_ops, telegram_bot):
        self.db_ops = db_ops
        self.telegram_bot = telegram_bot
        self.binding_manager = BindingManager(db_ops)
        self.content_delivery_manager = ContentDeliveryManager(db_ops)
        
        # Instagram client
        self.instagram_client = Client()
        self.is_logged_in = False
        
        # Configuration
        self.instagram_username = None
        self.instagram_password = None
        
    async def initialize(self, username: str, password: str):
        """Initialize Instagram client"""
        try:
            self.instagram_username = username
            self.instagram_password = password
            
            # Login to Instagram
            await self._login_to_instagram()
            
            logger.info(f"Instagram bot integration initialized for @{username}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Instagram bot integration: {e}")
            raise
    
    async def _login_to_instagram(self):
        """Login to Instagram"""
        try:
            # Login
            self.instagram_client.login(self.instagram_username, self.instagram_password)
            self.is_logged_in = True
            
            logger.info(f"Successfully logged in to Instagram as @{self.instagram_username}")
            
        except Exception as e:
            logger.error(f"Failed to login to Instagram: {e}")
            self.is_logged_in = False
            raise
    
    async def handle_direct_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming direct messages"""
        try:
            if not self.is_logged_in:
                return {'error': 'Instagram client not logged in'}
            
            # Extract message information
            sender_username = message_data.get('sender_username')
            message_text = message_data.get('text', '')
            media_urls = message_data.get('media_urls', [])
            message_type = message_data.get('type', 'text')
            
            logger.info(f"Received {message_type} message from @{sender_username}")
            
            # Check if this is a binding code
            if message_type == 'text' and self._is_binding_code(message_text):
                return await self._handle_binding_code(sender_username, message_text)
            
            # Check if this is content to deliver
            elif message_type in ['media', 'reel', 'story'] and media_urls:
                return await self._handle_content_delivery(sender_username, message_data)
            
            # Regular message (could be forwarded to bound users)
            else:
                return await self._handle_regular_message(sender_username, message_data)
                
        except Exception as e:
            logger.error(f"Error handling direct message: {e}")
            return {'error': str(e)}
    
    def _is_binding_code(self, text: str) -> bool:
        """Check if the text looks like a binding code"""
        # Binding codes are 6-10 characters, alphanumeric
        import re
        pattern = r'^[A-Z0-9]{6,10}$'
        return bool(re.match(pattern, text.strip()))
    
    async def _handle_binding_code(self, sender_username: str, binding_code: str) -> Dict[str, Any]:
        """Handle binding code confirmation"""
        try:
            logger.info(f"Processing binding code {binding_code} from @{sender_username}")
            
            # Confirm the binding
            result = await self.binding_manager.confirm_binding(sender_username, binding_code)
            
            if result['success']:
                # Send confirmation message to the user on Instagram
                await self._send_instagram_message(
                    sender_username,
                    f"✅ **Binding Confirmed!**\n\n"
                    f"Your Instagram account @{sender_username} is now bound to "
                    f"Telegram user {result['telegram_user_id']}.\n\n"
                    f"🎬 **What happens next:**\n"
                    f"• Every reel you post will be automatically sent to this user\n"
                    f"• Stories and posts can also be delivered\n"
                    f"• No action needed from you - it's fully automatic!\n\n"
                    f"🔒 **Security:** This binding is permanent until the user removes it.\n"
                    f"💡 **Pro Tip:** You can continue using Instagram normally!"
                )
                
                # Send confirmation to Telegram user
                await self._notify_telegram_user_binding_confirmed(
                    result['telegram_user_id'],
                    sender_username
                )
                
                logger.info(f"Binding confirmed for @{sender_username} to Telegram user {result['telegram_user_id']}")
                
                return {
                    'success': True,
                    'action': 'binding_confirmed',
                    'telegram_user_id': result['telegram_user_id'],
                    'instagram_username': sender_username,
                    'message': 'Binding confirmed successfully'
                }
            
            else:
                # Send error message to Instagram user
                await self._send_instagram_message(
                    sender_username,
                    f"❌ **Binding Failed**\n\n"
                    f"Could not confirm binding with code: {binding_code}\n\n"
                    f"**Possible reasons:**\n"
                    f"• Code has expired\n"
                    f"• Code has already been used\n"
                    f"• Invalid code format\n\n"
                    f"Please ask the user to generate a new binding code."
                )
                
                return {
                    'success': False,
                    'action': 'binding_failed',
                    'error': 'Binding confirmation failed'
                }
                
        except BindingError as e:
            # Send specific error message
            error_message = self._get_binding_error_message(e.error_code)
            await self._send_instagram_message(sender_username, error_message)
            
            return {
                'success': False,
                'action': 'binding_error',
                'error': e.message,
                'error_code': e.error_code
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in binding code handling: {e}")
            
            await self._send_instagram_message(
                sender_username,
                "❌ **System Error**\n\n"
                "An unexpected error occurred while processing your binding code.\n"
                "Please try again later or contact support."
            )
            
            return {
                'success': False,
                'action': 'system_error',
                'error': str(e)
            }
    
    def _get_binding_error_message(self, error_code: str) -> str:
        """Get user-friendly error message for binding errors"""
        error_messages = {
            'INVALID_CODE': (
                "❌ **Invalid Binding Code**\n\n"
                "The code you sent is not valid.\n"
                "Please check the code and try again."
            ),
            'CODE_EXPIRED': (
                "⏰ **Code Expired**\n\n"
                "This binding code has expired.\n"
                "Please ask the user to generate a new code."
            ),
            'CODE_ALREADY_USED': (
                "🔄 **Code Already Used**\n\n"
                "This binding code has already been used.\n"
                "Please ask the user to generate a new code."
            ),
            'TOO_MANY_ATTEMPTS': (
                "🚫 **Too Many Attempts**\n\n"
                "Too many failed attempts with this code.\n"
                "Please ask the user to generate a new code."
            ),
            'BINDING_NOT_FOUND': (
                "🔍 **Binding Not Found**\n\n"
                "Could not find the binding request for this code.\n"
                "Please ask the user to generate a new code."
            ),
            'USERNAME_MISMATCH': (
                "👤 **Username Mismatch**\n\n"
                "The binding code doesn't match your username.\n"
                "Please use the code sent to your specific account."
            )
        }
        
        return error_messages.get(error_code, "❌ **Unknown Error**\n\nAn unexpected error occurred.")
    
    async def _handle_content_delivery(self, sender_username: str, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle content delivery from Instagram to bound Telegram users"""
        try:
            logger.info(f"Processing content delivery from @{sender_username}")
            
            # Create delivery tasks for all bound users
            delivery_result = await self.content_delivery_manager.create_delivery_task(
                sender_username, content_data
            )
            
            if delivery_result['deliveries_created'] > 0:
                # Send confirmation to Instagram user
                await self._send_instagram_message(
                    sender_username,
                    f"✅ **Content Queued for Delivery**\n\n"
                    f"Your {content_data.get('content_type', 'content')} has been queued for delivery to "
                    f"{delivery_result['deliveries_created']} bound user(s).\n\n"
                    f"📱 **Delivery Process:**\n"
                    f"• Content is being downloaded and processed\n"
                    f"• Will be automatically sent to bound users\n"
                    f"• No action needed from you\n\n"
                    f"🎬 **Keep creating great content!**"
                )
                
                # Process the actual delivery
                await self._process_content_delivery(sender_username, content_data)
                
                return {
                    'success': True,
                    'action': 'content_delivery_queued',
                    'deliveries_created': delivery_result['deliveries_created'],
                    'message': f"Content queued for {delivery_result['deliveries_created']} users"
                }
            
            else:
                # No bound users
                await self._send_instagram_message(
                    sender_username,
                    "ℹ️ **No Bound Users**\n\n"
                    "You don't have any users bound to your Instagram account yet.\n\n"
                    "**To get started:**\n"
                    "• Users need to bind to your account first\n"
                    "• They'll send you a binding code\n"
                    "• Once confirmed, they'll receive all your content automatically!\n\n"
                    f"💡 **Current Status:** No active bindings found for @{sender_username}"
                )
                
                return {
                    'success': True,
                    'action': 'no_bound_users',
                    'message': 'No users bound to this account'
                }
                
        except Exception as e:
            logger.error(f"Error handling content delivery: {e}")
            
            await self._send_instagram_message(
                sender_username,
                "❌ **Delivery Error**\n\n"
                "An error occurred while processing your content for delivery.\n"
                "Please try again later."
            )
            
            return {
                'success': False,
                'action': 'delivery_error',
                'error': str(e)
            }
    
    async def _process_content_delivery(self, instagram_username: str, content_data: Dict[str, Any]):
        """Process the actual content delivery to Telegram users"""
        try:
            # Get all bound users for this Instagram account
            bindings = await self.db_ops.get_bindings_by_instagram_username(instagram_username)
            
            for binding in bindings:
                if binding['binding_status'] == 'confirmed' and binding['is_active']:
                    try:
                        # Download and process the content
                        processed_content = await self._download_and_process_content(content_data)
                        
                        if processed_content:
                            # Send to Telegram user
                            await self._send_content_to_telegram_user(
                                binding['telegram_user_id'],
                                instagram_username,
                                processed_content,
                                content_data
                            )
                            
                            # Mark delivery as completed
                            await self.content_delivery_manager.mark_delivery_completed(
                                binding['id'],
                                processed_content.get('file_path'),
                                processed_content.get('file_size')
                            )
                            
                            logger.info(f"Content delivered to Telegram user {binding['telegram_user_id']}")
                        
                    except Exception as e:
                        logger.error(f"Failed to deliver content to user {binding['telegram_user_id']}: {e}")
                        
                        # Mark delivery as failed
                        await self.content_delivery_manager.mark_delivery_failed(
                            binding['id'],
                            str(e)
                        )
                        
        except Exception as e:
            logger.error(f"Error processing content delivery: {e}")
    
    async def _download_and_process_content(self, content_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Download and process Instagram content"""
        try:
            # This would integrate with your existing media downloader
            # For now, return a placeholder
            return {
                'file_path': '/tmp/placeholder.mp4',
                'file_size': 1024,
                'content_type': content_data.get('content_type', 'reel')
            }
        except Exception as e:
            logger.error(f"Error downloading/processing content: {e}")
            return None
    
    async def _send_content_to_telegram_user(self, telegram_user_id: int, instagram_username: str, 
                                           processed_content: Dict[str, Any], original_content: Dict[str, Any]):
        """Send processed content to Telegram user"""
        try:
            # Create caption
            caption = self._create_content_caption(instagram_username, original_content)
            
            # Send the content based on type
            if processed_content['content_type'] == 'reel':
                await self.telegram_bot.send_video(
                    chat_id=telegram_user_id,
                    video=open(processed_content['file_path'], 'rb'),
                    caption=caption
                )
            elif processed_content['content_type'] == 'story':
                await self.telegram_bot.send_photo(
                    chat_id=telegram_user_id,
                    photo=open(processed_content['file_path'], 'rb'),
                    caption=caption
                )
            else:
                # Default to document
                await self.telegram_bot.send_document(
                    chat_id=telegram_user_id,
                    document=open(processed_content['file_path'], 'rb'),
                    caption=caption
                )
                
        except Exception as e:
            logger.error(f"Failed to send content to Telegram user {telegram_user_id}: {e}")
            raise
    
    def _create_content_caption(self, instagram_username: str, content_data: Dict[str, Any]) -> str:
        """Create caption for content delivery"""
        content_type = content_data.get('content_type', 'content')
        caption = content_data.get('caption', '')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        caption_text = f"🎬 **New {content_type.title()} from @{instagram_username}**\n\n"
        
        if caption:
            caption_text += f"💬 {caption}\n\n"
        
        caption_text += f"📅 **Posted:** {timestamp}\n"
        caption_text += f"🔗 **Instagram:** @{instagram_username}\n"
        caption_text += f"✅ **Auto-delivered via MediaFetch**"
        
        return caption_text
    
    async def _handle_regular_message(self, sender_username: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle regular text messages"""
        try:
            # Check if this user has any bound Telegram users
            bindings = await self.db_ops.get_bindings_by_instagram_username(sender_username)
            
            if bindings:
                # Forward message to bound users
                for binding in bindings:
                    if binding['binding_status'] == 'confirmed' and binding['is_active']:
                        await self._forward_message_to_telegram_user(
                            binding['telegram_user_id'],
                            sender_username,
                            message_data
                        )
                
                return {
                    'success': True,
                    'action': 'message_forwarded',
                    'forwarded_to': len(bindings),
                    'message': f"Message forwarded to {len(bindings)} bound users"
                }
            
            else:
                # No bound users, send helpful message
                await self._send_instagram_message(
                    sender_username,
                    "ℹ️ **Welcome to MediaFetch!**\n\n"
                    "I'm a bot that helps deliver your Instagram content to Telegram users.\n\n"
                    "**To get started:**\n"
                    "• Users need to bind to your account first\n"
                    "• They'll send you a binding code\n"
                    "• Once confirmed, they'll receive all your content automatically!\n\n"
                    f"💡 **Current Status:** No users bound to @{sender_username} yet"
                )
                
                return {
                    'success': True,
                    'action': 'welcome_message_sent',
                    'message': 'Welcome message sent to new user'
                }
                
        except Exception as e:
            logger.error(f"Error handling regular message: {e}")
            return {'error': str(e)}
    
    async def _forward_message_to_telegram_user(self, telegram_user_id: int, instagram_username: str, 
                                              message_data: Dict[str, Any]):
        """Forward Instagram message to Telegram user"""
        try:
            message_text = message_data.get('text', '')
            sender_name = message_data.get('sender_name', instagram_username)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            forward_text = (
                f"💬 **New DM from @{instagram_username}**\n\n"
                f"📝 **Message:**\n{message_text}\n\n"
                f"👤 **Sender:** {sender_name}\n"
                f"📅 **Time:** {timestamp}\n"
                f"🔗 **Instagram:** @{instagram_username}"
            )
            
            await self.telegram_bot.send_message(
                chat_id=telegram_user_id,
                text=forward_text
            )
            
        except Exception as e:
            logger.error(f"Failed to forward message to Telegram user {telegram_user_id}: {e}")
    
    async def _send_instagram_message(self, recipient_username: str, message_text: str):
        """Send message to Instagram user"""
        try:
            # This would use Instagram's API to send messages
            # For now, just log the message
            logger.info(f"Would send to @{recipient_username}: {message_text}")
            
        except Exception as e:
            logger.error(f"Failed to send Instagram message: {e}")
    
    async def _notify_telegram_user_binding_confirmed(self, telegram_user_id: int, instagram_username: str):
        """Notify Telegram user that binding was confirmed"""
        try:
            notification_text = (
                f"✅ **Binding Confirmed!**\n\n"
                f"Your Telegram account is now bound to @{instagram_username} on Instagram.\n\n"
                f"🎬 **What happens next:**\n"
                f"• Every reel @{instagram_username} posts will be automatically sent to you\n"
                f"• Stories and posts can also be delivered\n"
                f"• No more manual checking - content comes to you!\n\n"
                f"🔒 **Security:** This binding is permanent until you remove it.\n"
                f"💡 **Manage bindings:** Use `/bindings` to see all your active bindings."
            )
            
            await self.telegram_bot.send_message(
                chat_id=telegram_user_id,
                text=notification_text
            )
            
        except Exception as e:
            logger.error(f"Failed to notify Telegram user {telegram_user_id}: {e}")
    
    async def start_monitoring(self):
        """Start monitoring Instagram for new content and messages"""
        try:
            logger.info("Starting Instagram monitoring...")
            
            # This would start a monitoring loop
            # For now, just log that monitoring is ready
            logger.info("Instagram monitoring ready - waiting for messages")
            
        except Exception as e:
            logger.error(f"Failed to start Instagram monitoring: {e}")
            raise
    
    async def stop_monitoring(self):
        """Stop Instagram monitoring"""
        try:
            logger.info("Stopping Instagram monitoring...")
            
            # Cleanup and stop monitoring
            logger.info("Instagram monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Instagram monitoring: {e}")
            raise
