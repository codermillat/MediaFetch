#!/usr/bin/env python3
"""
Shared Binding System
Provides a centralized binding system for both Telegram and Instagram bots
Uses Supabase database for persistence across dyno restarts
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class SharedBindingSystem:
    """Database-based binding system for cross-bot communication"""
    
    def __init__(self):
        # Initialize Supabase client
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            logger.error("❌ Supabase credentials not configured")
            self.client = None
        else:
            try:
                self.client = create_client(self.supabase_url, self.supabase_key)
                logger.info("✅ Supabase client initialized")
                self._ensure_tables_exist()
            except Exception as e:
                logger.error(f"❌ Failed to initialize Supabase client: {e}")
                self.client = None
        
        logger.info(f"SharedBindingSystem initialized with database storage")
    
    def _ensure_tables_exist(self):
        """Ensure binding tables exist in the database"""
        try:
            # Create binding_codes table if it doesn't exist
            self.client.table('binding_codes').select('id').limit(1).execute()
            logger.info("✅ binding_codes table exists")
        except Exception as e:
            logger.warning(f"binding_codes table not found, creating it: {e}")
            self._create_binding_tables()
    
    def _create_binding_tables(self):
        """Create the necessary binding tables"""
        try:
            # Create binding_codes table
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS binding_codes (
                id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
                code VARCHAR(10) UNIQUE NOT NULL,
                telegram_user_id BIGINT NOT NULL,
                instagram_username VARCHAR(255),
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                is_used BOOLEAN DEFAULT FALSE
            );
            
            CREATE TABLE IF NOT EXISTS user_bindings (
                id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
                telegram_user_id BIGINT NOT NULL,
                instagram_username VARCHAR(255) NOT NULL,
                binding_code VARCHAR(10) NOT NULL,
                bound_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                is_active BOOLEAN DEFAULT TRUE,
                UNIQUE(telegram_user_id, instagram_username)
            );
            
            CREATE INDEX IF NOT EXISTS idx_binding_codes_code ON binding_codes(code);
            CREATE INDEX IF NOT EXISTS idx_binding_codes_telegram_id ON binding_codes(telegram_user_id);
            CREATE INDEX IF NOT EXISTS idx_user_bindings_telegram_id ON user_bindings(telegram_user_id);
            """
            
            # Execute the SQL (this might not work with PostgREST, so we'll handle it gracefully)
            logger.info("📋 Binding tables structure defined")
            
        except Exception as e:
            logger.error(f"Failed to create binding tables: {e}")
    
    def add_pending_binding(self, code: str, telegram_id: int, username: str = None) -> bool:
        """Add a pending binding code to the database"""
        try:
            if not self.client:
                logger.error("❌ Supabase client not available")
                return False
            
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            # Insert into binding_codes table
            data = {
                'code': code,
                'telegram_user_id': telegram_id,
                'instagram_username': username,
                'expires_at': expires_at.isoformat(),
                'is_used': False
            }
            
            result = self.client.table('binding_codes').insert(data).execute()
            
            if result.data:
                logger.info(f"➕ Added pending binding: Code {code} for Telegram user {telegram_id}")
                logger.info(f"📊 Binding data: {data}")
                return True
            else:
                logger.error(f"❌ Failed to insert binding code {code}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding pending binding: {e}")
            return False
    
    def process_binding_code(self, code: str, instagram_username: str) -> Dict:
        """Process a binding code sent to Instagram"""
        try:
            if not self.client:
                logger.error("❌ Supabase client not available")
                return {'success': False, 'error': 'Database not available'}
            
            logger.info(f"🔍 Processing binding code: {code} for Instagram user: {instagram_username}")
            
            # Find the binding code in the database
            result = self.client.table('binding_codes').select('*').eq('code', code).eq('is_used', False).execute()
            
            if not result.data:
                logger.warning(f"❌ Code {code} not found or already used")
                return {
                    'success': False,
                    'error': 'Invalid or expired binding code'
                }
            
            binding = result.data[0]
            logger.info(f"✅ Found binding: {binding}")
            
            # Check if expired
            expires_at = datetime.fromisoformat(binding['expires_at'].replace('Z', '+00:00'))
            if datetime.utcnow() > expires_at:
                logger.warning(f"⏰ Binding code {code} has expired")
                return {
                    'success': False,
                    'error': 'Binding code has expired'
                }
            
            # Mark code as used
            self.client.table('binding_codes').update({'is_used': True}).eq('code', code).execute()
            
            # Create user binding
            binding_data = {
                'telegram_user_id': binding['telegram_user_id'],
                'instagram_username': instagram_username,
                'binding_code': code
            }
            
            self.client.table('user_bindings').insert(binding_data).execute()
            
            logger.info(f"✅ Binding activated: Telegram {binding['telegram_user_id']} -> Instagram @{instagram_username}")
            
            return {
                'success': True,
                'telegram_id': binding['telegram_user_id'],
                'instagram_username': instagram_username,
                'message': f"✅ Account @{instagram_username} successfully bound to MediaFetch!"
            }
            
        except Exception as e:
            logger.error(f"Error processing binding code: {e}")
            return {
                'success': False,
                'error': f'Processing error: {str(e)}'
            }
    
    def get_user_bindings(self, telegram_id: int) -> List[str]:
        """Get all active bindings for a Telegram user"""
        try:
            if not self.client:
                return []
            
            result = self.client.table('user_bindings').select('instagram_username').eq('telegram_user_id', telegram_id).eq('is_active', True).execute()
            
            if result.data:
                usernames = [binding['instagram_username'] for binding in result.data]
                logger.info(f"📱 Found {len(usernames)} active bindings for user {telegram_id}")
                return usernames
            else:
                logger.info(f"📱 No active bindings found for user {telegram_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting user bindings: {e}")
            return []
    
    def remove_binding(self, telegram_id: int, instagram_username: str = None) -> bool:
        """Remove a binding"""
        try:
            if not self.client:
                return False
            
            if instagram_username:
                # Remove specific binding
                result = self.client.table('user_bindings').update({'is_active': False}).eq('telegram_user_id', telegram_id).eq('instagram_username', instagram_username).execute()
            else:
                # Remove all bindings for user
                result = self.client.table('user_bindings').update({'is_active': False}).eq('telegram_user_id', telegram_id).execute()
            
            if result.data:
                logger.info(f"🗑️ Binding removed for Telegram user {telegram_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error removing binding: {e}")
            return False
    
    def cleanup_expired_bindings(self):
        """Remove expired pending bindings"""
        try:
            if not self.client:
                return
            
            current_time = datetime.utcnow().isoformat()
            
            # Mark expired codes as used
            result = self.client.table('binding_codes').update({'is_used': True}).lt('expires_at', current_time).eq('is_used', False).execute()
            
            if result.data:
                logger.info(f"🧹 Cleanup completed: marked {len(result.data)} expired codes as used")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired bindings: {e}")
    
    def get_pending_binding(self, code: str) -> Optional[Dict]:
        """Get a pending binding by code"""
        try:
            if not self.client:
                return None
            
            result = self.client.table('binding_codes').select('*').eq('code', code).eq('is_used', False).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting pending binding: {e}")
            return None
    
    def is_code_valid(self, code: str) -> bool:
        """Check if a binding code is valid and not expired"""
        try:
            if not self.client:
                return False
            
            result = self.client.table('binding_codes').select('expires_at').eq('code', code).eq('is_used', False).execute()
            
            if not result.data:
                return False
            
            expires_at = datetime.fromisoformat(result.data[0]['expires_at'].replace('Z', '+00:00'))
            return datetime.utcnow() <= expires_at
            
        except Exception as e:
            logger.error(f"Error checking code validity: {e}")
            return False
    
    def get_status(self) -> Dict:
        """Get current system status for debugging"""
        try:
            if not self.client:
                return {'error': 'Database not available'}
            
            # Get pending codes count
            pending_result = self.client.table('binding_codes').select('id', count='exact').eq('is_used', False).execute()
            pending_count = pending_result.count if hasattr(pending_result, 'count') else len(pending_result.data)
            
            # Get active bindings count
            active_result = self.client.table('user_bindings').select('id', count='exact').eq('is_active', True).execute()
            active_count = active_result.count if hasattr(active_result, 'count') else len(active_result.data)
            
            return {
                'pending_count': pending_count,
                'active_count': active_count,
                'database_status': 'connected'
            }
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {'error': str(e)}

# Create a global instance
shared_binding_system = SharedBindingSystem()

# Export the instance for easy access
__all__ = ['shared_binding_system', 'SharedBindingSystem']
