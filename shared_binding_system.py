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

logger = logging.getLogger(__name__)

class SharedBindingSystem:
    """Database-based binding system for cross-bot communication"""
    
    def __init__(self):
        # Initialize Supabase client
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        # CRITICAL: Initialize ALL attributes here to prevent AttributeError
        self.pending_bindings: Dict[str, Dict] = {}
        self.active_bindings: Dict[int, str] = {}  # telegram_id -> instagram_username
        
        if not self.supabase_url or not self.supabase_key:
            logger.error("❌ Supabase credentials not configured")
            self.client = None
            logger.info("🔄 Using in-memory storage due to missing Supabase credentials")
            return
        
        try:
            # Try to initialize Supabase client
            from supabase import create_client, Client
            self.client = create_client(self.supabase_url, self.supabase_key)
            logger.info("✅ Supabase client initialized successfully")
            
            # Test database connection
            try:
                # Try a simple query to test connection
                result = self.client.table('binding_codes').select('*').limit(1).execute()
                logger.info("✅ Database connection test successful")
            except Exception as e:
                logger.warning(f"⚠️ Database connection test failed: {e}")
                logger.info("🔄 Falling back to in-memory storage")
                self.client = None
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {e}")
            logger.info("🔄 Falling back to in-memory storage due to Supabase error")
            self.client = None
        
        logger.info(f"SharedBindingSystem initialized with {'database' if self.client else 'in-memory'} storage")
        logger.info(f"📊 Initial state: {len(self.pending_bindings)} pending, {len(self.active_bindings)} active bindings")

    def add_pending_binding(self, code: str, telegram_id: int, username: str = None) -> bool:
        """Add a new pending binding code"""
        try:
            expires_at = datetime.utcnow() + timedelta(hours=24)
            binding_data = {
                'telegram_id': telegram_id,
                'instagram_username': username,
                'expires_at': expires_at.isoformat(),
                'created_at': datetime.utcnow().isoformat()
            }
            
            if self.client:
                # Try database first
                try:
                    result = self.client.table('binding_codes').insert({
                        'code': code,
                        'telegram_user_id': telegram_id,
                        'instagram_username': username,
                        'expires_at': expires_at.isoformat(),
                        'is_used': False
                    }).execute()
                    logger.info(f"✅ Binding code {code} saved to database for user {telegram_id}")
                    return True
                except Exception as e:
                    logger.warning(f"⚠️ Database save failed: {e}, falling back to memory")
                    self.client = None
            
            # Fallback to in-memory storage
            self.pending_bindings[code] = binding_data
            logger.info(f"➕ Added pending binding to memory: Code {code} for Telegram user {telegram_id}")
            logger.info(f"📊 Total pending bindings: {len(self.pending_bindings)}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding pending binding: {e}")
            return False

    def process_binding_code(self, code: str, instagram_username: str) -> Dict:
        """Process a binding code from Instagram"""
        try:
            logger.info(f"🔍 Processing binding code: {code} for Instagram user: {instagram_username}")
            
            if self.client:
                # Try database first
                try:
                    # Check if code exists and is not expired
                    result = self.client.table('binding_codes').select('*').eq('code', code).eq('is_used', False).execute()
                    
                    if result.data:
                        binding = result.data[0]
                        expires_at = datetime.fromisoformat(binding['expires_at'])
                        
                        if datetime.utcnow() > expires_at:
                            # Mark as expired
                            self.client.table('binding_codes').update({'is_used': True}).eq('code', code).execute()
                            return {
                                'success': False,
                                'error': 'Binding code has expired'
                            }
                        
                        # Activate binding
                        telegram_id = binding['telegram_user_id']
                        
                        # Save to active bindings table
                        self.client.table('user_bindings').insert({
                            'telegram_user_id': telegram_id,
                            'instagram_username': instagram_username,
                            'binding_code': code,
                            'bound_at': datetime.utcnow().isoformat()
                        }).execute()
                        
                        # Mark code as used
                        self.client.table('binding_codes').update({'is_used': True}).eq('code', code).execute()
                        
                        # Update local cache
                        self.active_bindings[telegram_id] = instagram_username
                        
                        logger.info(f"✅ Binding activated via database: Telegram {telegram_id} -> Instagram @{instagram_username}")
                        return {
                            'success': True,
                            'telegram_id': telegram_id,
                            'instagram_username': instagram_username,
                            'message': f"✅ Account @{instagram_username} successfully bound to MediaFetch!"
                        }
                        
                except Exception as e:
                    logger.warning(f"⚠️ Database processing failed: {e}, falling back to memory")
                    self.client = None
            
            # Fallback to in-memory storage
            if code not in self.pending_bindings:
                logger.warning(f"❌ Code {code} not found in pending bindings")
                return {
                    'success': False,
                    'error': 'Invalid or expired binding code'
                }
            
            binding = self.pending_bindings[code]
            logger.info(f"✅ Found pending binding: {binding}")
            
            # Check if expired
            expires_at = datetime.fromisoformat(binding['expires_at'])
            if datetime.utcnow() > expires_at:
                del self.pending_bindings[code]
                logger.warning(f"⏰ Binding code {code} has expired")
                return {
                    'success': False,
                    'error': 'Binding code has expired'
                }
            
            # Activate binding
            telegram_id = binding['telegram_id']
            self.active_bindings[telegram_id] = instagram_username
            
            # Remove from pending
            del self.pending_bindings[code]
            
            logger.info(f"✅ Binding activated via memory: Telegram {telegram_id} -> Instagram @{instagram_username}")
            logger.info(f"📊 Updated state: {len(self.pending_bindings)} pending, {len(self.active_bindings)} active")
            
            return {
                'success': True,
                'telegram_id': telegram_id,
                'instagram_username': instagram_username,
                'message': f"✅ Account @{instagram_username} successfully bound to MediaFetch!"
            }
            
        except Exception as e:
            logger.error(f"Error processing binding code: {e}")
            return {
                'success': False,
                'error': f'Processing error: {str(e)}'
            }

    def is_bound_user(self, instagram_username: str) -> bool:
        """Check if an Instagram user is bound"""
        try:
            if self.client:
                # Try database first
                try:
                    result = self.client.table('user_bindings').select('*').eq('instagram_username', instagram_username).execute()
                    if result.data:
                        # Update local cache
                        for binding in result.data:
                            self.active_bindings[binding['telegram_user_id']] = instagram_username
                        return True
                except Exception as e:
                    logger.warning(f"⚠️ Database check failed: {e}, falling back to memory")
                    self.client = None
            
            # Fallback to in-memory storage
            return instagram_username in self.active_bindings.values()
            
        except Exception as e:
            logger.error(f"Error checking bound user: {e}")
            return False

    def get_bound_telegram_id(self, instagram_username: str) -> Optional[int]:
        """Get the Telegram ID for a bound Instagram user"""
        try:
            if self.client:
                # Try database first
                try:
                    result = self.client.table('user_bindings').select('telegram_user_id').eq('instagram_username', instagram_username).execute()
                    if result.data:
                        telegram_id = result.data[0]['telegram_user_id']
                        # Update local cache
                        self.active_bindings[telegram_id] = instagram_username
                        return telegram_id
                except Exception as e:
                    logger.warning(f"⚠️ Database lookup failed: {e}, falling back to memory")
                    self.client = None
            
            # Fallback to in-memory storage
            for telegram_id, username in self.active_bindings.items():
                if username == instagram_username:
                    return telegram_id
            return None
            
        except Exception as e:
            logger.error(f"Error getting bound Telegram ID: {e}")
            return None

    def get_all_bindings(self) -> Dict:
        """Get all current bindings"""
        try:
            if self.client:
                # Try database first
                try:
                    result = self.client.table('user_bindings').select('*').execute()
                    if result.data:
                        # Update local cache
                        for binding in result.data:
                            self.active_bindings[binding['telegram_user_id']] = binding['instagram_username']
                except Exception as e:
                    logger.warning(f"⚠️ Database fetch failed: {e}, using memory cache")
            
            return {
                'pending': self.pending_bindings,
                'active': self.active_bindings
            }
            
        except Exception as e:
            logger.error(f"Error getting all bindings: {e}")
            return {
                'pending': self.pending_bindings,
                'active': self.active_bindings
            }

# Global instance
shared_binding_system = SharedBindingSystem()
