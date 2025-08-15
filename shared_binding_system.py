#!/usr/bin/env python3
"""
Shared Binding System
Provides a centralized binding system for both Telegram and Instagram bots
Uses Supabase database for true persistence across dyno restarts
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List
import requests

logger = logging.getLogger(__name__)

class SharedBindingSystem:
    """Database-based binding system for cross-bot communication"""
    
    def __init__(self):
        # Initialize Supabase connection
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        # Always initialize these attributes for fallback
        self.pending_bindings: Dict[str, Dict] = {}
        self.active_bindings: Dict[int, str] = {}
        
        # Check if Supabase is configured
        if not self.supabase_url or not self.supabase_key:
            logger.warning("⚠️ Supabase not configured, using in-memory storage")
            self.use_database = False
        else:
            self.use_database = True
            logger.info("✅ Using Supabase database for binding storage")
    
    def _make_supabase_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make direct HTTP request to Supabase"""
        try:
            url = f"{self.supabase_url}/rest/v1/{endpoint}"
            headers = {
                'Authorization': f'Bearer {self.supabase_key}',
                'Content-Type': 'application/json',
                'apikey': self.supabase_key
            }
            
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method == 'PATCH':
                response = requests.patch(url, headers=headers, json=data)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            
                            if response.status_code in [200, 201]:  # 201 = Created, 200 = OK
                    try:
                        if response.text:
                            return response.json()
                        else:
                            # Empty response but successful status
                            return {'success': True, 'status': response.status_code}
                    except:
                        return {'success': True, 'status': response.status_code}
                else:
                    logger.error(f"❌ Supabase request failed: {response.status_code} - {response.text}")
                    return None
                
        except Exception as e:
            logger.error(f"❌ Error making Supabase request: {e}")
            return None
    
    def add_pending_binding(self, code: str, telegram_id: int, username: str = None) -> bool:
        """Add a new pending binding code"""
        try:
            # Check if user already has a pending binding
            if self.use_database:
                existing_binding = self._make_supabase_request('GET', f'binding_codes?telegram_user_id=eq.{telegram_id}&is_used=eq.false')
                if existing_binding and len(existing_binding) > 0:
                    logger.warning(f"⚠️ User {telegram_id} already has a pending binding code")
                    return False
            else:
                # Check in-memory for existing bindings
                for existing_code, binding_data in self.pending_bindings.items():
                    if binding_data['telegram_id'] == telegram_id:
                        logger.warning(f"⚠️ User {telegram_id} already has a pending binding code: {existing_code}")
                        return False
            
                                    expires_at = datetime.utcnow() + timedelta(hours=24)
                        
                        if self.use_database:
                            # Store in Supabase - fix timestamp format
                            data = {
                                'code': code,
                                'telegram_user_id': telegram_id,
                                'instagram_username': username,
                                'expires_at': expires_at.replace(tzinfo=timezone.utc).isoformat(),
                                'is_used': False
                            }
                
                result = self._make_supabase_request('POST', 'binding_codes', data)
                logger.info(f"🔍 Database response for code {code}: {result}")
                if result and (isinstance(result, dict) and result.get('success') or result):
                    logger.info(f"✅ Binding code {code} stored in database for user {telegram_id}")
                    return True
                else:
                    logger.error(f"❌ Failed to store binding code {code} in database")
                    return False
            else:
                # Fallback to in-memory
                self.pending_bindings[code] = {
                    'telegram_id': telegram_id,
                    'instagram_username': username,
                    'expires_at': expires_at.isoformat(),
                    'created_at': datetime.utcnow().isoformat()
                }
                logger.info(f"➕ Added pending binding to memory: Code {code} for Telegram user {telegram_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error adding pending binding: {e}")
            return False
    
    def process_binding_code(self, code: str, instagram_username: str) -> Dict:
        """Process a binding code from Instagram"""
        try:
            logger.info(f"🔍 Processing binding code: {code} for Instagram user: {instagram_username}")
            
                                    if self.use_database:
                            # Query Supabase for the code
                            logger.info(f"🔍 Querying database for code: {code}")
                            result = self._make_supabase_request('GET', f'binding_codes?code=eq.{code}&is_used=eq.false')
                            logger.info(f"🔍 Database query result: {result}")
                
                if not result or len(result) == 0:
                    logger.warning(f"❌ Code {code} not found in database")
                    return {'success': False, 'error': 'Invalid or expired binding code'}
                
                binding_data = result[0]
                expires_at = datetime.fromisoformat(binding_data['expires_at'].replace('Z', '+00:00'))
                
                if datetime.utcnow().replace(tzinfo=timezone.utc) > expires_at:
                    logger.warning(f"⏰ Binding code {code} has expired")
                    return {'success': False, 'error': 'Binding code has expired'}
                
                # Mark as used and create active binding
                telegram_id = binding_data['telegram_user_id']
                
                # Update code as used
                self._make_supabase_request('PATCH', f'binding_codes?id=eq.{binding_data["id"]}', {
                    'is_used': True
                })
                
                # Check if user is already bound to prevent duplicates
                existing_binding = self._make_supabase_request('GET', f'user_bindings?telegram_user_id=eq.{telegram_id}')
                if existing_binding and len(existing_binding) > 0:
                    logger.warning(f"⚠️ User {telegram_id} is already bound to Instagram")
                    return {'success': False, 'error': 'User is already bound to another Instagram account'}
                
                # Check if Instagram username is already bound to prevent duplicates
                existing_instagram = self._make_supabase_request('GET', f'user_bindings?instagram_username=eq.{instagram_username}')
                if existing_instagram and len(existing_instagram) > 0:
                    logger.warning(f"⚠️ Instagram @{instagram_username} is already bound to another user")
                    return {'success': False, 'error': 'Instagram account is already bound to another user'}
                
                # Create active binding
                binding_data = {
                    'telegram_user_id': telegram_id,
                    'instagram_username': instagram_username,
                    'binding_code': code,
                    'bound_at': datetime.utcnow().isoformat()
                }
                
                result = self._make_supabase_request('POST', 'user_bindings', binding_data)
                if result:
                    logger.info(f"✅ Binding activated in database: Telegram {telegram_id} -> Instagram @{instagram_username}")
                    return {
                        'success': True,
                        'telegram_id': telegram_id,
                        'telegram_id': telegram_id,
                        'instagram_username': instagram_username,
                        'message': f"✅ Account @{instagram_username} successfully bound to MediaFetch!"
                    }
                else:
                    logger.error(f"❌ Failed to create active binding in database")
                    return {'success': False, 'error': 'Database error'}
                    
            else:
                # Fallback to in-memory
                if code not in self.pending_bindings:
                    logger.warning(f"❌ Code {code} not found in pending bindings")
                    return {'success': False, 'error': 'Invalid or expired binding code'}
                
                binding = self.pending_bindings[code]
                expires_at = datetime.fromisoformat(binding['expires_at'])
                
                if datetime.utcnow().replace(tzinfo=timezone.utc) > expires_at:
                    del self.pending_bindings[code]
                    logger.warning(f"⏰ Binding code {code} has expired")
                    return {'success': False, 'error': 'Binding code has expired'}
                
                # Activate binding
                telegram_id = binding['telegram_id']
                self.active_bindings[telegram_id] = instagram_username
                del self.pending_bindings[code]
                
                logger.info(f"✅ Binding activated: Telegram {telegram_id} -> Instagram @{instagram_username}")
                return {
                    'success': True,
                    'telegram_id': telegram_id,
                    'instagram_username': instagram_username,
                    'message': f"✅ Account @{instagram_username} successfully bound to MediaFetch!"
                }
                
        except Exception as e:
            logger.error(f"Error processing binding code: {e}")
            return {'success': False, 'error': f'Processing error: {str(e)}'}
    
    def is_bound_user(self, instagram_username: str) -> bool:
        """Check if an Instagram user is bound"""
        if self.use_database:
            result = self._make_supabase_request('GET', f'user_bindings?instagram_username=eq.{instagram_username}')
            return result is not None and len(result) > 0
        else:
            return instagram_username in self.active_bindings.values()
    
    def get_bound_telegram_id(self, instagram_username: str) -> Optional[int]:
        """Get the Telegram ID bound to an Instagram username"""
        if self.use_database:
            result = self._make_supabase_request('GET', f'user_bindings?instagram_username=eq.{instagram_username}')
            if result and len(result) > 0:
                return result[0]['telegram_user_id']
            return None
        else:
            for telegram_id, username in self.active_bindings.items():
                if username == instagram_username:
                    return telegram_id
            return None
    
    def get_user_bindings(self, telegram_user_id: int) -> List[str]:
        """Get all Instagram usernames bound to a Telegram user"""
        try:
            if self.use_database:
                result = self._make_supabase_request('GET', f'user_bindings?telegram_user_id=eq.{telegram_user_id}&is_active=eq.true')
                if result:
                    return [binding['instagram_username'] for binding in result]
                return []
            else:
                # Fallback to in-memory
                if telegram_user_id in self.active_bindings:
                    return [self.active_bindings[telegram_user_id]]
                return []
        except Exception as e:
            logger.error(f"Error getting user bindings: {e}")
            return []

    def cleanup_expired_bindings(self):
        """Clean up expired binding codes"""
        try:
            if self.use_database:
                # Clean up expired codes in database
                current_time = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
                expired_codes = self._make_supabase_request('GET', f'binding_codes?expires_at=lt.{current_time}')
                
                if expired_codes:
                    for code_data in expired_codes:
                        self._make_supabase_request('DELETE', f'binding_codes?id=eq.{code_data["id"]}')
                    logger.info(f"🧹 Cleaned up {len(expired_codes)} expired binding codes")
            else:
                # Clean up expired codes in memory
                current_time = datetime.utcnow()
                expired_codes = []
                
                for code, binding_data in self.pending_bindings.items():
                    expires_at = datetime.fromisoformat(binding_data['expires_at'])
                    if current_time > expires_at:
                        expired_codes.append(code)
                
                for code in expired_codes:
                    del self.pending_bindings[code]
                
                if expired_codes:
                    logger.info(f"🧹 Cleaned up {len(expired_codes)} expired binding codes from memory")
                    
        except Exception as e:
            logger.error(f"Error cleaning up expired bindings: {e}")

# Create and export the global instance
shared_binding_system = SharedBindingSystem()