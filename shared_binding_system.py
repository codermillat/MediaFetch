#!/usr/bin/env python3
"""
Shared Binding System
Provides a centralized binding system for both Telegram and Instagram bots
Uses Supabase database for true persistence across dyno restarts
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List, Any, Set
import requests
import time

logger = logging.getLogger(__name__)

class SharedBindingSystem:
    """Robust, production-ready binding system for cross-bot communication"""

    def __init__(self):
        # Initialize Supabase connection
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        # Rate limiting and spam prevention
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum 1 second between requests
        
        # User state tracking
        self.user_binding_attempts: Dict[int, List[float]] = {}  # Track binding attempts per user
        self.max_binding_attempts = 3  # Max attempts per hour

        # Active bindings cache (telegram_id -> instagram_username)
        self.active_bindings: Dict[int, str] = {}
        
        # Processed codes cache to prevent duplicate processing
        self.processed_codes: Set[str] = set()
        
        # Check if Supabase is configured
        if not self.supabase_url or not self.supabase_key:
            logger.warning("⚠️ Supabase not configured, using in-memory storage")
            self.use_database = False
        else:
            self.use_database = True
            logger.info("✅ Using Supabase database for binding storage")

        # Load existing active bindings on startup
        self._load_active_bindings()

    def _load_active_bindings(self):
        """Load existing active bindings from database"""
        if self.use_database:
            try:
                result = self._make_supabase_request('GET', 'user_bindings?is_active=eq.true')
                if result and isinstance(result, list):
                    for binding in result:
                        telegram_id = binding.get('telegram_user_id')
                        instagram_username = binding.get('instagram_username')
                        if telegram_id and instagram_username:
                            self.active_bindings[telegram_id] = instagram_username
                    logger.info(f"✅ Loaded {len(self.active_bindings)} active bindings from database")
                else:
                    logger.info("ℹ️ No existing active bindings found")
            except Exception as e:
                logger.error(f"❌ Failed to load active bindings: {e}")
                self.active_bindings = {}  # Reset to empty dict on error
        else:
            logger.info("ℹ️ Using in-memory storage - no existing bindings to load")

    def remove_binding(self, telegram_id: int, instagram_username: str = None):
        """Remove a binding from cache"""
        if instagram_username is None:
            # Remove all bindings for this telegram user
            if telegram_id in self.active_bindings:
                del self.active_bindings[telegram_id]
                logger.info(f"✅ Removed binding for Telegram user {telegram_id}")
        else:
            # Remove specific binding
            if telegram_id in self.active_bindings and self.active_bindings[telegram_id] == instagram_username:
                del self.active_bindings[telegram_id]
                logger.info(f"✅ Removed binding: Telegram {telegram_id} -> Instagram @{instagram_username}")

    def get_active_binding(self, telegram_id: int) -> Optional[str]:
        """Get active Instagram binding for a Telegram user"""
        return self.active_bindings.get(telegram_id)

    def get_all_active_bindings(self) -> Dict[int, str]:
        """Get all active bindings (for debugging/admin purposes)"""
        return self.active_bindings.copy()

    def _is_bound_user(self, instagram_username: str) -> bool:
        """Check if an Instagram user is already bound (internal method)"""
        if self.use_database:
            result = self._make_supabase_request('GET', f'user_bindings?instagram_username=eq.{instagram_username}&is_active=eq.true')
            return result is not None and len(result) > 0
        return False

    def _rate_limit(self):
        """Implement rate limiting to prevent API spam"""
        current_time = time.time()
        if current_time - self.last_request_time < self.min_request_interval:
            sleep_time = self.min_request_interval - (current_time - self.last_request_time)
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _make_supabase_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Any:
        """Make rate-limited HTTP request to Supabase"""
        try:
            self._rate_limit()  # Rate limit all requests
            
            url = f"{self.supabase_url}/rest/v1/{endpoint}"
            headers = {
                'Authorization': f'Bearer {self.supabase_key}',
                'Content-Type': 'application/json',
                'apikey': self.supabase_key
            }

            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == 'PATCH':
                response = requests.patch(url, headers=headers, json=data, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            if response.status_code in [200, 201]:
                try:
                    if response.text:
                        return response.json()
                    else:
                        return {'success': True, 'status': response.status_code}
                except:
                    return {'success': True, 'status': response.status_code}
            else:
                logger.error(f"❌ Supabase request failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ Error making Supabase request: {e}")
            return None

    def _check_user_binding_limits(self, telegram_id: int) -> bool:
        """Check if user has exceeded binding attempt limits"""
        current_time = time.time()
        hour_ago = current_time - 3600  # 1 hour ago
        
        # Clean up old attempts
        if telegram_id in self.user_binding_attempts:
            self.user_binding_attempts[telegram_id] = [
                attempt_time for attempt_time in self.user_binding_attempts[telegram_id]
                if attempt_time > hour_ago
            ]
        
        # Check if user has exceeded limits
        if telegram_id in self.user_binding_attempts:
            if len(self.user_binding_attempts[telegram_id]) >= self.max_binding_attempts:
                logger.warning(f"⚠️ User {telegram_id} exceeded binding attempt limit")
                return False
        
        return True

    def _record_binding_attempt(self, telegram_id: int):
        """Record a binding attempt for rate limiting"""
        if telegram_id not in self.user_binding_attempts:
            self.user_binding_attempts[telegram_id] = []
        self.user_binding_attempts[telegram_id].append(time.time())

    def add_pending_binding(self, code: str, telegram_id: int, username: Optional[str] = None) -> Dict[str, Any]:
        """Add a new pending binding code with comprehensive validation"""
        try:
            # Check if user already has an active binding
            if self._has_active_binding(telegram_id):
                return {
                    'success': False,
                    'error': 'User already has an active binding',
                    'code': 'ALREADY_BOUND'
                }
            
            # Check binding attempt limits
            if not self._check_user_binding_limits(telegram_id):
                return {
                    'success': False,
                    'error': 'Too many binding attempts. Please wait 1 hour.',
                    'code': 'RATE_LIMITED'
                }
            
            # Check if user already has a pending code
            if self._has_pending_binding(telegram_id):
                return {
                    'success': False,
                    'error': 'User already has a pending binding code',
                    'code': 'PENDING_EXISTS'
                }
            
            # Check if code already exists
            if self._code_exists(code):
                return {
                    'success': False,
                    'error': 'Binding code already exists',
                    'code': 'CODE_EXISTS'
                }
            
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
            
            if self.use_database:
                # Store in Supabase
                data = {
                    'code': code,
                    'telegram_user_id': telegram_id,
                    'instagram_username': username,
                    'expires_at': expires_at.isoformat(),
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                result = self._make_supabase_request('POST', 'binding_codes', data)
                if result and (isinstance(result, dict) and result.get('success') or result):
                    # Record the attempt
                    self._record_binding_attempt(telegram_id)
                    logger.info(f"✅ Binding code {code} stored in database for user {telegram_id}")
                    return {
                        'success': True,
                        'code': code,
                        'expires_at': expires_at.isoformat()
                    }
                else:
                    logger.error(f"❌ Failed to store binding code {code} in database")
                    return {
                        'success': False,
                        'error': 'Database storage failed',
                        'code': 'DB_ERROR'
                    }
            else:
                # Fallback to in-memory (not recommended for production)
                self._record_binding_attempt(telegram_id)
                logger.warning(f"⚠️ Using in-memory storage for code {code}")
                return {
                    'success': True,
                    'code': code,
                    'expires_at': expires_at.isoformat()
                }

        except Exception as e:
            logger.error(f"Error adding pending binding: {e}")
            return {
                'success': False,
                'error': f'System error: {str(e)}',
                'code': 'SYSTEM_ERROR'
            }

    def _has_active_binding(self, telegram_id: int) -> bool:
        """Check if user already has an active binding"""
        if self.use_database:
            result = self._make_supabase_request('GET', f'user_bindings?telegram_user_id=eq.{telegram_id}&is_active=eq.true')
            return result is not None and len(result) > 0
        return False

    def _has_pending_binding(self, telegram_id: int) -> bool:
        """Check if user already has a pending binding code"""
        if self.use_database:
            current_time = datetime.now(timezone.utc).isoformat()
            result = self._make_supabase_request('GET', f'binding_codes?telegram_user_id=eq.{telegram_id}&expires_at=gt.{current_time}')
            return result is not None and len(result) > 0
        return False

    def _code_exists(self, code: str) -> bool:
        """Check if a binding code already exists"""
        if self.use_database:
            result = self._make_supabase_request('GET', f'binding_codes?code=eq.{code}')
            return result is not None and len(result) > 0
        return False

    def process_binding_code(self, code: str, instagram_username: str) -> Dict[str, Any]:
        """Process a binding code from Instagram with comprehensive validation"""
        try:
            logger.info(f"🔍 Processing binding code: {code} for Instagram user: {instagram_username}")

            # Check if code was already processed (prevent duplicate processing)
            if code in self.processed_codes:
                logger.info(f"ℹ️ Code {code} already processed, skipping")
                return {'success': False, 'error': 'Code already processed'}

            if self.use_database:
                # Query Supabase for the code
                logger.info(f"🔍 Querying database for code: {code}")
                result = self._make_supabase_request('GET', f'binding_codes?code=eq.{code}')
                logger.info(f"🔍 Database query result: {result}")

                if not result or len(result) == 0:
                    logger.warning(f"❌ Code {code} not found in database")
                    return {'success': False, 'error': 'Invalid or expired binding code'}

                binding_data = result[0]
                
                # Check if code is already used
                if binding_data.get('is_used', False):
                    logger.warning(f"❌ Code {code} already used")
                    # Add to processed codes to prevent future processing
                    self.processed_codes.add(code)
                    return {'success': False, 'error': 'Binding code already used'}

                # Check expiration
                expires_at = datetime.fromisoformat(binding_data['expires_at'].replace('Z', '+00:00'))
                if datetime.now(timezone.utc) > expires_at:
                    logger.warning(f"⏰ Binding code {code} has expired")
                    # Add to processed codes to prevent future processing
                    self.processed_codes.add(code)
                    return {'success': False, 'error': 'Binding code has expired'}

                # Check if Instagram user is already bound
                if self._is_bound_user(instagram_username):
                    logger.warning(f"❌ Instagram user @{instagram_username} already bound")
                    # Add to processed codes to prevent future processing
                    self.processed_codes.add(code)
                    return {'success': False, 'error': 'Instagram account already bound to another user'}

                # Check if Telegram user is already bound
                telegram_id = binding_data['telegram_user_id']
                if self._has_active_binding(telegram_id):
                    logger.warning(f"❌ Telegram user {telegram_id} already bound")
                    # Add to processed codes to prevent future processing
                    self.processed_codes.add(code)
                    return {'success': False, 'error': 'Telegram account already bound'}

                # Mark code as used
                self._make_supabase_request('PATCH', f'binding_codes?id=eq.{binding_data["id"]}', {
                    'is_used': True
                })

                # Create active binding
                binding_data_new = {
                    'telegram_user_id': telegram_id,
                    'instagram_username': instagram_username,
                    'binding_code': code,
                    'bound_at': datetime.now(timezone.utc).isoformat(),
                    'is_active': True
                }

                result = self._make_supabase_request('POST', 'user_bindings', binding_data_new)
                if result:
                    logger.info(f"✅ Binding activated in database: Telegram {telegram_id} -> Instagram @{instagram_username}")

                    # Update active bindings cache
                    self.active_bindings[telegram_id] = instagram_username

                    # Add to processed codes to prevent future processing
                    self.processed_codes.add(code)

                    return {
                        'success': True,
                        'telegram_id': telegram_id,
                        'instagram_username': instagram_username,
                        'message': f"✅ Account @{instagram_username} successfully bound to MediaFetch!"
                    }
                else:
                    logger.error(f"❌ Failed to create active binding in database")
                    return {'success': False, 'error': 'Database error'}

            else:
                # Fallback to in-memory (not recommended for production)
                logger.warning("⚠️ Using in-memory storage - not recommended for production")
                return {'success': False, 'error': 'System not properly configured'}

        except Exception as e:
            logger.error(f"Error processing binding code: {e}")
            return {'success': False, 'error': f'Processing error: {str(e)}'}

    def is_bound_user(self, instagram_username: str) -> bool:
        """Check if an Instagram user is bound"""
        if self.use_database:
            result = self._make_supabase_request('GET', f'user_bindings?instagram_username=eq.{instagram_username}&is_active=eq.true')
            return result is not None and len(result) > 0
        return False

    def get_bound_telegram_id(self, instagram_username: str) -> Optional[int]:
        """Get the Telegram ID bound to an Instagram username"""
        if self.use_database:
            result = self._make_supabase_request('GET', f'user_bindings?instagram_username=eq.{instagram_username}&is_active=eq.true')
            if result and len(result) > 0:
                return result[0]['telegram_user_id']
            return None
        return None

    def get_user_bindings(self, telegram_id: int) -> List[Dict[str, Any]]:
        """Get all bindings for a Telegram user"""
        if self.use_database:
            result = self._make_supabase_request('GET', f'user_bindings?telegram_user_id=eq.{telegram_id}&is_active=eq.true')
            return result if result else []
        return []

    def remove_user_binding(self, telegram_id: int, instagram_username: str) -> bool:
        """Remove a specific binding for a user"""
        if self.use_database:
            result = self._make_supabase_request('DELETE', f'user_bindings?telegram_user_id=eq.{telegram_id}&instagram_username=eq.{instagram_username}')
            if result is not None and result.get('success', False):
                # Remove from cache
                self.remove_binding(telegram_id, instagram_username)
                return True
            return False
        return False

    def cleanup_expired_bindings(self):
        """Clean up expired binding codes"""
        try:
            if self.use_database:
                # Clean up expired codes in database
                current_time = datetime.now(timezone.utc).isoformat()
                expired_codes = self._make_supabase_request('GET', f'binding_codes?expires_at=lt.{current_time}')
                
                if expired_codes:
                    for code_data in expired_codes:
                        self._make_supabase_request('DELETE', f'binding_codes?id=eq.{code_data["id"]}')
                    logger.info(f"🧹 Cleaned up {len(expired_codes)} expired binding codes")
            else:
                # Clean up expired codes in memory
                current_time = time.time()
                expired_keys = [k for k, v in self.user_binding_attempts.items() 
                              if current_time - max(v) > 3600]
                for key in expired_keys:
                    del self.user_binding_attempts[key]
                logger.info(f"🧹 Cleaned up {len(expired_keys)} expired user attempts")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Create and export the global instance
shared_binding_system = SharedBindingSystem()
