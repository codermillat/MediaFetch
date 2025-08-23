"""
Binding Manager for MediaFetch Instagram Integration
Handles the sophisticated binding system between Telegram users and Instagram accounts
"""

import secrets
import string
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from supabase_config import SupabaseClient

class MediaFetchError(Exception):
    """Base exception for MediaFetch errors"""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class BindingError(MediaFetchError):
    """Exception for binding-related errors"""
    pass

class ContentDeliveryError(MediaFetchError):
    """Exception for content delivery errors"""
    pass

class BindingManager:
    """Manages the sophisticated binding system between Telegram and Instagram"""
    
    def __init__(self):
        self.supabase_client = SupabaseClient()
        self.binding_code_length = 8
        self.binding_code_expiry_hours = 24
        self.max_binding_attempts = 3
    
    def generate_binding_code(self) -> str:
        """Generate a unique binding code"""
        # Use alphanumeric characters, excluding confusing ones
        characters = string.ascii_uppercase + string.digits
        characters = characters.replace('0', '').replace('O', '').replace('1', '').replace('I', '')
        
        while True:
            code = ''.join(secrets.choice(characters) for _ in range(self.binding_code_length))
            # Check if code already exists (this would be implemented in db_ops)
            if not self.supabase_client.get_binding_code(code).data:
                return code
    
    async def create_binding_request(self, telegram_user_id: int, instagram_username: str) -> Dict[str, Any]:
        """Create a new binding request with unique code"""
        try:
            # Check if user already has an active binding
            existing_binding_response = self.supabase_client.get_user_binding(telegram_user_id, instagram_username)
            if existing_binding_response.data and existing_binding_response.data[0]['binding_status'] == 'confirmed':
                raise BindingError(f"User already bound to @{instagram_username}", "ALREADY_BOUND")
            
            # Get or create user
            user_response = self.supabase_client.get_user_by_telegram_id(telegram_user_id)
            if not user_response.data:
                raise BindingError("User not found", "USER_NOT_FOUND")
            user: Dict[str, Any] = user_response.data[0]
            
            # Generate binding code
            binding_code = self.generate_binding_code()
            
            # Calculate expiry time
            expires_at = datetime.now(timezone.utc) + timedelta(hours=self.binding_code_expiry_hours)
            
            # Create binding record
            binding_data = {
                'user_id': user['id'],
                'telegram_user_id': telegram_user_id,
                'instagram_username': instagram_username,
                'binding_code': binding_code,
                'binding_status': 'pending',
                'expires_at': expires_at.isoformat(),
                'is_active': True
            }
            
            binding = self.supabase_client.create_user_binding(binding_data).data
            if not binding:
                raise BindingError("Failed to create binding", "BINDING_CREATION_FAILED")
            
            # Create binding code record
            code_data = {
                'code': binding_code,
                'telegram_user_id': telegram_user_id,
                'expires_at': expires_at.isoformat(),
                'max_attempts': self.max_binding_attempts
            }
            
            self.supabase_client.create_binding_code(code_data)
            
            return {
                'success': True,
                'binding_code': binding_code,
                'expires_at': expires_at.isoformat(),
                'message': f"Binding code generated: {binding_code}. Send this code to @{instagram_username} on Instagram."
            }
            
        except Exception as e:
            if isinstance(e, BindingError):
                raise
            raise BindingError(f"Failed to create binding request: {e}", "BINDING_REQUEST_FAILED")
    
    async def confirm_binding(self, instagram_username: str, binding_code: str) -> Dict[str, Any]:
        """Confirm a binding when Instagram bot receives the code"""
        try:
            # Find the binding code
            code_record_response = self.supabase_client.get_binding_code(binding_code)
            if not code_record_response.data:
                raise BindingError("Invalid binding code", "INVALID_CODE")
            code_record: Dict[str, Any] = code_record_response.data[0]
            
            # Check if code is expired
            if datetime.fromisoformat(code_record['expires_at']) < datetime.now(timezone.utc):
                raise BindingError("Binding code expired", "CODE_EXPIRED")
            
            # Check if code is already used
            if code_record['is_used']:
                raise BindingError("Binding code already used", "CODE_ALREADY_USED")
            
            # Check attempts
            if code_record['attempts'] >= code_record['max_attempts']:
                raise BindingError("Too many attempts", "TOO_MANY_ATTEMPTS")
            
            # Find the binding record
            binding_response = self.supabase_client.get_binding_by_code(binding_code)
            if not binding_response.data:
                raise BindingError("Binding not found", "BINDING_NOT_FOUND")
            binding: Dict[str, Any] = binding_response.data[0]
            
            # Verify Instagram username matches
            if binding['instagram_username'] != instagram_username:
                raise BindingError("Instagram username mismatch", "USERNAME_MISMATCH")
            
            # Update binding status
            self.supabase_client.update_binding_status(
                binding['id'], 
                'confirmed',
                {'confirmed_at': datetime.now(timezone.utc).isoformat()}
            )
            
            # Mark code as used
            self.supabase_client.mark_binding_code_used(binding_code, code_record['id'])
            
            # Update user binding status
            self.supabase_client.update_user_binding_status(binding['user_id'], 'bound')
            
            return {
                'success': True,
                'telegram_user_id': binding['telegram_user_id'],
                'instagram_username': instagram_username,
                'message': f"Successfully bound @{instagram_username} to Telegram user {binding['telegram_user_id']}"
            }
            
        except Exception as e:
            if isinstance(e, BindingError):
                raise
            raise BindingError(f"Failed to confirm binding: {e}", "BINDING_CONFIRMATION_FAILED")
    
    async def get_user_bindings(self, telegram_user_id: int) -> List[Dict[str, Any]]:
        """Get all bindings for a user"""
        try:
            response = self.supabase_client.get_user_bindings(telegram_user_id)
            return response.data if response else []
        except Exception as e:
            raise BindingError(f"Failed to get user bindings: {e}", "GET_BINDINGS_FAILED")
    
    async def revoke_binding(self, telegram_user_id: int, instagram_username: str) -> bool:
        """Revoke a user's binding"""
        try:
            binding_response = self.supabase_client.get_user_binding(telegram_user_id, instagram_username)
            if not binding_response.data:
                return False
            binding: Dict[str, Any] = binding_response.data[0]
            
            self.supabase_client.update_binding_status(binding['id'], 'revoked', {})
            self.supabase_client.update_user_binding_status(binding['user_id'], 'unbound')
            
            return True
        except Exception as e:
            raise BindingError(f"Failed to revoke binding: {e}", "REVOKE_BINDING_FAILED")

class ContentDeliveryManager:
    """Manages content delivery from Instagram to Telegram"""
    
    def __init__(self):
        self.supabase_client = SupabaseClient()
    
    async def create_delivery_task(self, instagram_username: str, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a content delivery task"""
        try:
            # Find all users bound to this Instagram account
            bindings_response = self.supabase_client.get_bindings_by_instagram_username(instagram_username)
            bindings = bindings_response.data if bindings_response else []
            
            if not bindings:
                return {
                    'success': True,
                    'message': f"No users bound to @{instagram_username}",
                    'deliveries_created': 0
                }
            
            deliveries_created = 0
            
            for binding in bindings:
                if binding['binding_status'] == 'confirmed' and binding['is_active']:
                    # Create delivery record for each bound user
                    delivery_data = {
                        'binding_id': binding['id'],
                        'instagram_username': instagram_username,
                        'telegram_user_id': binding['telegram_user_id'],
                        'content_type': content_data.get('content_type', 'reel'),
                        'instagram_content_id': content_data.get('content_id'),
                        'content_url': content_data.get('content_url'),
                        'delivery_status': 'pending',
                        'metadata': content_data.get('metadata', {})
                    }
                    
                    delivery = self.supabase_client.create_content_delivery(delivery_data).data
                    if delivery:
                        deliveries_created += 1
            
            return {
                'success': True,
                'message': f"Created {deliveries_created} delivery tasks for @{instagram_username}",
                'deliveries_created': deliveries_created
            }
            
        except Exception as e:
            raise ContentDeliveryError(f"Failed to create delivery task: {e}", "DELIVERY_TASK_CREATION_FAILED")
    
    async def mark_delivery_completed(self, delivery_id: str, file_path: str = None, file_size: int = None) -> bool:
        """Mark a delivery as completed"""
        try:
            update_data = {
                'delivery_status': 'delivered',
                'delivered_at': datetime.now(timezone.utc).isoformat()
            }
            
            if file_path:
                update_data['local_file_path'] = file_path
            if file_size:
                update_data['file_size'] = file_size
            
            response = self.supabase_client.update_content_delivery(delivery_id, update_data)
            return bool(response.data) if response else False
            
        except Exception as e:
            raise ContentDeliveryError(f"Failed to mark delivery completed: {e}", "MARK_DELIVERY_COMPLETED_FAILED")
    
    async def mark_delivery_failed(self, delivery_id: str, error_message: str) -> bool:
        """Mark a delivery as failed"""
        try:
            update_data = {
                'delivery_status': 'failed',
                'error_message': error_message
            }
            
            response = self.supabase_client.update_content_delivery(delivery_id, update_data)
            return bool(response.data) if response else False
            
        except Exception as e:
            raise ContentDeliveryError(f"Failed to mark delivery failed: {e}", "MARK_DELIVERY_FAILED_FAILED")
