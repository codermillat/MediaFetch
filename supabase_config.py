"""
Supabase configuration for MediaFetch project
Enhanced with binding system and production-quality error handling
"""
import os
import secrets
import string
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from supabase import create_client, Client
import asyncio

class MediaFetchError(Exception):
    """Base exception for MediaFetch errors"""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
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

class SupabaseConfig:
    """Configuration class for Supabase connection"""
    
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL', 'https://vtbrkmnizkyeflhwypfm.supabase.co')
        self.key = os.getenv('SUPABASE_ANON_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ0YnJrbW5pemt5ZWZsaHd5cGZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTUyNjYxMTMsImV4cCI6MjA3MDg0MjExM30.TsLEx0E2NwZdbAN92eDCWkFiP9-vios3Q5aZY8VFjgA')
        self.service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        self.client: Optional[Client] = None
        
    def get_client(self) -> Client:
        """Get or create Supabase client"""
        if self.client is None:
            self.client = create_client(self.url, self.key)
        return self.client
    
    def test_connection(self) -> bool:
        """Test the Supabase connection"""
        try:
            client = self.get_client()
            # Try to access a simple endpoint
            response = client.table('users').select('id').limit(1).execute()
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

# Database table names
TABLES = {
    'users': 'users',
    'user_bindings': 'user_bindings',
    'binding_codes': 'binding_codes',
    'content_deliveries': 'content_deliveries',
    'instagram_accounts': 'instagram_accounts',
    'instagram_posts': 'instagram_posts',
    'media_files': 'media_files',
    'download_tasks': 'download_tasks',
    'monitoring_logs': 'monitoring_logs',
    'telegram_sessions': 'telegram_sessions',
    'user_preferences': 'user_preferences',
    'system_config': 'system_config'
}

class BindingManager:
    """Manages the sophisticated binding system"""
    
    def __init__(self, db_ops: 'SupabaseOperations'):
        self.db_ops = db_ops
        self.config = db_ops.config
    
    def generate_binding_code(self, length: int = 8) -> str:
        """Generate a unique binding code"""
        # Use alphanumeric characters, excluding confusing ones
        characters = string.ascii_uppercase + string.digits
        characters = characters.replace('0', '').replace('O', '').replace('1', '').replace('I', '')
        
        while True:
            code = ''.join(secrets.choice(characters) for _ in range(length))
            # Check if code already exists
            if not self.db_ops.get_binding_code(code):
                return code
    
    async def create_binding_request(self, telegram_user_id: int, instagram_username: str) -> Dict[str, Any]:
        """Create a new binding request with unique code"""
        try:
            # Check if user already has an active binding
            existing_binding = await self.db_ops.get_user_binding(telegram_user_id, instagram_username)
            if existing_binding and existing_binding['binding_status'] == 'confirmed':
                raise BindingError(f"User already bound to @{instagram_username}", "ALREADY_BOUND")
            
            # Get or create user
            user = await self.db_ops.get_user_by_telegram_id(telegram_user_id)
            if not user:
                raise BindingError("User not found", "USER_NOT_FOUND")
            
            # Generate binding code
            binding_code = self.generate_binding_code()
            
            # Calculate expiry time (24 hours from now)
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
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
            
            binding = await self.db_ops.create_user_binding(binding_data)
            if not binding:
                raise BindingError("Failed to create binding", "BINDING_CREATION_FAILED")
            
            # Create binding code record
            code_data = {
                'code': binding_code,
                'telegram_user_id': telegram_user_id,
                'expires_at': expires_at.isoformat(),
                'max_attempts': 3
            }
            
            await self.db_ops.create_binding_code(code_data)
            
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
            code_record = await self.db_ops.get_binding_code(binding_code)
            if not code_record:
                raise BindingError("Invalid binding code", "INVALID_CODE")
            
            # Check if code is expired
            if datetime.fromisoformat(code_record['expires_at']) < datetime.utcnow():
                raise BindingError("Binding code expired", "CODE_EXPIRED")
            
            # Check if code is already used
            if code_record['is_used']:
                raise BindingError("Binding code already used", "CODE_ALREADY_USED")
            
            # Check attempts
            if code_record['attempts'] >= code_record['max_attempts']:
                raise BindingError("Too many attempts", "TOO_MANY_ATTEMPTS")
            
            # Find the binding record
            binding = await self.db_ops.get_binding_by_code(binding_code)
            if not binding:
                raise BindingError("Binding not found", "BINDING_NOT_FOUND")
            
            # Verify Instagram username matches
            if binding['instagram_username'] != instagram_username:
                raise BindingError("Instagram username mismatch", "USERNAME_MISMATCH")
            
            # Update binding status
            updated_binding = await self.db_ops.update_binding_status(
                binding['id'], 
                'confirmed',
                {'confirmed_at': datetime.utcnow().isoformat()}
            )
            
            # Mark code as used
            await self.db_ops.mark_binding_code_used(binding_code, code_record['id'])
            
            # Update user binding status
            await self.db_ops.update_user_binding_status(binding['user_id'], 'bound')
            
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
            return await self.db_ops.get_user_bindings(telegram_user_id)
        except Exception as e:
            raise BindingError(f"Failed to get user bindings: {e}", "GET_BINDINGS_FAILED")
    
    async def revoke_binding(self, telegram_user_id: int, instagram_username: str) -> bool:
        """Revoke a user's binding"""
        try:
            binding = await self.db_ops.get_user_binding(telegram_user_id, instagram_username)
            if not binding:
                return False
            
            await self.db_ops.update_binding_status(binding['id'], 'revoked')
            await self.db_ops.update_user_binding_status(binding['user_id'], 'unbound')
            
            return True
        except Exception as e:
            raise BindingError(f"Failed to revoke binding: {e}", "REVOKE_BINDING_FAILED")

class ContentDeliveryManager:
    """Manages content delivery from Instagram to Telegram"""
    
    def __init__(self, db_ops: 'SupabaseOperations'):
        self.db_ops = db_ops
    
    async def create_delivery_task(self, instagram_username: str, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a content delivery task"""
        try:
            # Find all users bound to this Instagram account
            bindings = await self.db_ops.get_bindings_by_instagram_username(instagram_username)
            
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
                    
                    delivery = await self.db_ops.create_content_delivery(delivery_data)
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
                'delivered_at': datetime.utcnow().isoformat()
            }
            
            if file_path:
                update_data['local_file_path'] = file_path
            if file_size:
                update_data['file_size'] = file_size
            
            return await self.db_ops.update_content_delivery(delivery_id, update_data)
            
        except Exception as e:
            raise ContentDeliveryError(f"Failed to mark delivery completed: {e}", "MARK_DELIVERY_COMPLETED_FAILED")
    
    async def mark_delivery_failed(self, delivery_id: str, error_message: str) -> bool:
        """Mark a delivery as failed"""
        try:
            update_data = {
                'delivery_status': 'failed',
                'error_message': error_message
            }
            
            return await self.db_ops.update_content_delivery(delivery_id, update_data)
            
        except Exception as e:
            raise ContentDeliveryError(f"Failed to mark delivery failed: {e}", "MARK_DELIVERY_FAILED_FAILED")

# Database operations
class SupabaseOperations:
    """Enhanced database operations for MediaFetch with binding system"""
    
    def __init__(self):
        self.config = SupabaseConfig()
        self.client = self.config.get_client()
        self.binding_manager = BindingManager(self)
        self.content_delivery_manager = ContentDeliveryManager(self)
    
    # User management
    async def create_user(self, username: str, telegram_user_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        try:
            data = {
                'username': username,
                'telegram_user_id': telegram_user_id,
                'telegram_username': kwargs.get('telegram_username'),
                'telegram_first_name': kwargs.get('telegram_first_name'),
                'telegram_last_name': kwargs.get('telegram_last_name'),
                'email': kwargs.get('email'),
                'binding_status': 'unbound'
            }
            response = self.client.table(TABLES['users']).insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            raise MediaFetchError(f"Error creating user: {e}", "USER_CREATION_ERROR")
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        try:
            response = self.client.table(TABLES['users']).select('*').eq('username', username).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            raise MediaFetchError(f"Error getting user: {e}", "USER_GET_ERROR")
    
    async def get_user_by_telegram_id(self, telegram_user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Telegram ID"""
        try:
            response = self.client.table(TABLES['users']).select('*').eq('telegram_user_id', telegram_user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            raise MediaFetchError(f"Error getting user by Telegram ID: {e}", "USER_GET_BY_TELEGRAM_ERROR")
    
    # Binding management
    async def create_user_binding(self, binding_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a user binding"""
        try:
            response = self.client.table(TABLES['user_bindings']).insert(binding_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            raise MediaFetchError(f"Error creating user binding: {e}", "BINDING_CREATION_ERROR")
    
    async def get_user_binding(self, telegram_user_id: int, instagram_username: str) -> Optional[Dict[str, Any]]:
        """Get a specific user binding"""
        try:
            response = self.client.table(TABLES['user_bindings']).select('*').eq('telegram_user_id', telegram_user_id).eq('instagram_username', instagram_username).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            raise MediaFetchError(f"Error getting user binding: {e}", "BINDING_GET_ERROR")
    
    async def get_user_bindings(self, telegram_user_id: int) -> List[Dict[str, Any]]:
        """Get all bindings for a user"""
        try:
            response = self.client.table(TABLES['user_bindings']).select('*').eq('telegram_user_id', telegram_user_id).eq('is_active', True).execute()
            return response.data if response.data else []
        except Exception as e:
            raise MediaFetchError(f"Error getting user bindings: {e}", "BINDINGS_GET_ERROR")
    
    async def update_binding_status(self, binding_id: str, status: str, additional_data: Dict[str, Any] = None) -> bool:
        """Update binding status"""
        try:
            update_data = {
                'binding_status': status,
                'updated_at': datetime.utcnow().isoformat()
            }
            if additional_data:
                update_data.update(additional_data)
            
            response = self.client.table(TABLES['user_bindings']).update(update_data).eq('id', binding_id).execute()
            return bool(response.data)
        except Exception as e:
            raise MediaFetchError(f"Error updating binding status: {e}", "BINDING_STATUS_UPDATE_ERROR")
    
    # Binding codes
    async def create_binding_code(self, code_data: Dict[str, Any]) -> bool:
        """Create a binding code record"""
        try:
            response = self.client.table(TABLES['binding_codes']).insert(code_data).execute()
            return bool(response.data)
        except Exception as e:
            raise MediaFetchError(f"Error creating binding code: {e}", "BINDING_CODE_CREATION_ERROR")
    
    async def get_binding_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get a binding code record"""
        try:
            response = self.client.table(TABLES['binding_codes']).select('*').eq('code', code).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            raise MediaFetchError(f"Error getting binding code: {e}", "BINDING_CODE_GET_ERROR")
    
    async def mark_binding_code_used(self, code: str, code_id: str) -> bool:
        """Mark a binding code as used"""
        try:
            update_data = {
                'is_used': True,
                'used_at': datetime.utcnow().isoformat()
            }
            response = self.client.table(TABLES['binding_codes']).update(update_data).eq('id', code_id).execute()
            return bool(response.data)
        except Exception as e:
            raise MediaFetchError(f"Error marking binding code used: {e}", "BINDING_CODE_MARK_USED_ERROR")
    
    # Content delivery
    async def create_content_delivery(self, delivery_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a content delivery record"""
        try:
            response = self.client.table(TABLES['content_deliveries']).insert(delivery_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            raise MediaFetchError(f"Error creating content delivery: {e}", "CONTENT_DELIVERY_CREATION_ERROR")
    
    async def get_bindings_by_instagram_username(self, instagram_username: str) -> List[Dict[str, Any]]:
        """Get all bindings for a specific Instagram username"""
        try:
            response = self.client.table(TABLES['user_bindings']).select('*').eq('instagram_username', instagram_username).eq('is_active', True).execute()
            return response.data if response.data else []
        except Exception as e:
            raise MediaFetchError(f"Error getting bindings by Instagram username: {e}", "BINDINGS_BY_INSTAGRAM_ERROR")
    
    async def update_content_delivery(self, delivery_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a content delivery record"""
        try:
            update_data['updated_at'] = datetime.utcnow().isoformat()
            response = self.client.table(TABLES['content_deliveries']).update(update_data).eq('id', delivery_id).execute()
            return bool(response.data)
        except Exception as e:
            raise MediaFetchError(f"Error updating content delivery: {e}", "CONTENT_DELIVERY_UPDATE_ERROR")
    
    # User binding status
    async def update_user_binding_status(self, user_id: str, status: str) -> bool:
        """Update user binding status"""
        try:
            update_data = {
                'binding_status': status,
                'updated_at': datetime.utcnow().isoformat()
            }
            response = self.client.table(TABLES['users']).update(update_data).eq('id', user_id).execute()
            return bool(response.data)
        except Exception as e:
            raise MediaFetchError(f"Error updating user binding status: {e}", "USER_BINDING_STATUS_UPDATE_ERROR")
    
    # Instagram accounts
    async def create_instagram_account(self, user_id: str, username: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Create a new Instagram account to monitor"""
        try:
            data = {
                'user_id': user_id,
                'username': username,
                **kwargs
            }
            response = self.client.table(TABLES['instagram_accounts']).insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            raise MediaFetchError(f"Error creating Instagram account: {e}", "INSTAGRAM_ACCOUNT_CREATION_ERROR")
    
    async def add_instagram_post(self, instagram_account_id: str, post_data: dict) -> Optional[Dict[str, Any]]:
        """Add a new Instagram post"""
        try:
            data = {
                'instagram_account_id': instagram_account_id,
                **post_data
            }
            response = self.client.table(TABLES['instagram_posts']).insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            raise MediaFetchError(f"Error adding Instagram post: {e}", "INSTAGRAM_POST_ADDITION_ERROR")
    
    async def update_download_status(self, post_id: str, status: str, **kwargs) -> bool:
        """Update download status for a post"""
        try:
            data = {
                'download_status': status,
                **kwargs
            }
            response = self.client.table(TABLES['instagram_posts']).update(data).eq('id', post_id).execute()
            return bool(response.data)
        except Exception as e:
            raise MediaFetchError(f"Error updating download status: {e}", "DOWNLOAD_STATUS_UPDATE_ERROR")
    
    async def get_pending_downloads(self, limit: int = 10) -> list:
        """Get posts pending download"""
        try:
            response = self.client.table(TABLES['instagram_posts']).select('*').eq('download_status', 'pending').limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            raise MediaFetchError(f"Error getting pending downloads: {e}", "PENDING_DOWNLOADS_GET_ERROR")
    
    async def log_monitoring_event(self, instagram_account_id: str, action: str, details: dict = None, status: str = 'success') -> bool:
        """Log a monitoring event"""
        try:
            data = {
                'instagram_account_id': instagram_account_id,
                'action': action,
                'details': details or {},
                'status': status
            }
            response = self.client.table(TABLES['monitoring_logs']).insert(data).execute()
            return bool(response.data)
        except Exception as e:
            raise MediaFetchError(f"Error logging monitoring event: {e}", "MONITORING_EVENT_LOGGING_ERROR")

# Example usage
if __name__ == "__main__":
    # Test the connection
    config = SupabaseConfig()
    if config.test_connection():
        print("✅ Supabase connection successful!")
        
        # Test basic operations
        ops = SupabaseOperations()
        
        # Test binding system
        try:
            # This would be called when user wants to bind
            binding_result = asyncio.run(ops.binding_manager.create_binding_request(123456789, "test_instagram"))
            print(f"✅ Binding request created: {binding_result}")
            
        except Exception as e:
            print(f"❌ Binding test failed: {e}")
        
    else:
        print("❌ Supabase connection failed!")
