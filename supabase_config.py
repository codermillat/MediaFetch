"""
Supabase configuration for MediaFetch project
"""
import os
from typing import Optional
from supabase import create_client, Client

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
    'instagram_accounts': 'instagram_accounts',
    'instagram_posts': 'instagram_posts',
    'media_files': 'media_files',
    'download_tasks': 'download_tasks',
    'monitoring_logs': 'monitoring_logs',
    'telegram_sessions': 'telegram_sessions',
    'user_preferences': 'user_preferences'
}

# Database operations
class SupabaseOperations:
    """Common database operations for MediaFetch"""
    
    def __init__(self):
        self.config = SupabaseConfig()
        self.client = self.config.get_client()
    
    def create_user(self, username: str, email: str = None, telegram_user_id: int = None) -> dict:
        """Create a new user"""
        try:
            data = {
                'username': username,
                'email': email,
                'telegram_user_id': telegram_user_id
            }
            response = self.client.table(TABLES['users']).insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> dict:
        """Get user by username"""
        try:
            response = self.client.table(TABLES['users']).select('*').eq('username', username).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def create_instagram_account(self, user_id: str, username: str, **kwargs) -> dict:
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
            print(f"Error creating Instagram account: {e}")
            return None
    
    def add_instagram_post(self, instagram_account_id: str, post_data: dict) -> dict:
        """Add a new Instagram post"""
        try:
            data = {
                'instagram_account_id': instagram_account_id,
                **post_data
            }
            response = self.client.table(TABLES['instagram_posts']).insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error adding Instagram post: {e}")
            return None
    
    def update_download_status(self, post_id: str, status: str, **kwargs) -> bool:
        """Update download status for a post"""
        try:
            data = {
                'download_status': status,
                **kwargs
            }
            response = self.client.table(TABLES['instagram_posts']).update(data).eq('id', post_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error updating download status: {e}")
            return False
    
    def get_pending_downloads(self, limit: int = 10) -> list:
        """Get posts pending download"""
        try:
            response = self.client.table(TABLES['instagram_posts']).select('*').eq('download_status', 'pending').limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error getting pending downloads: {e}")
            return []
    
    def log_monitoring_event(self, instagram_account_id: str, action: str, details: dict = None, status: str = 'success') -> bool:
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
            print(f"Error logging monitoring event: {e}")
            return False

# Example usage
if __name__ == "__main__":
    # Test the connection
    config = SupabaseConfig()
    if config.test_connection():
        print("✅ Supabase connection successful!")
        
        # Test basic operations
        ops = SupabaseOperations()
        
        # Create a test user
        user = ops.create_user('testuser_from_python', 'test@python.com')
        if user:
            print(f"✅ Created user: {user['username']}")
        
        # Get pending downloads
        pending = ops.get_pending_downloads(5)
        print(f"📥 Pending downloads: {len(pending)}")
        
    else:
        print("❌ Supabase connection failed!")
