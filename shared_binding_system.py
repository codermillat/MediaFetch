#!/usr/bin/env python3
"""
Shared Binding System
Provides a centralized binding system for both Telegram and Instagram bots
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

class SharedBindingSystem:
    """Centralized binding system for cross-bot communication"""
    
    def __init__(self, storage_file: str = None):
        # For now, use in-memory storage to avoid file sharing issues
        # In production, this should be replaced with a database
        self.pending_bindings: Dict[str, Dict] = {}
        self.active_bindings: Dict[int, str] = {}  # telegram_id -> instagram_username
        
        logger.info(f"SharedBindingSystem initialized with in-memory storage")
        logger.info(f"📊 Initial state: {len(self.pending_bindings)} pending, {len(self.active_bindings)} active bindings")
    
    def add_pending_binding(self, code: str, telegram_id: int, username: str = None) -> bool:
        """Add a pending binding code"""
        try:
            expires_at = datetime.utcnow() + timedelta(hours=24)
            binding_data = {
                'telegram_id': telegram_id,
                'instagram_username': username,
                'expires_at': expires_at.isoformat(),
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.pending_bindings[code] = binding_data
            logger.info(f"➕ Adding pending binding: Code {code} for Telegram user {telegram_id}")
            logger.info(f"📊 Binding data: {binding_data}")
            logger.info(f"📊 Total pending bindings: {len(self.pending_bindings)}")
            logger.info(f"📊 All pending codes: {list(self.pending_bindings.keys())}")
            
            return True
        except Exception as e:
            logger.error(f"Error adding pending binding: {e}")
            return False
    
    def process_binding_code(self, code: str, instagram_username: str) -> Dict:
        """Process a binding code sent to Instagram"""
        try:
            logger.info(f"🔍 Processing binding code: {code} for Instagram user: {instagram_username}")
            logger.info(f"📊 Current pending bindings: {list(self.pending_bindings.keys())}")
            logger.info(f"📊 Current active bindings: {self.active_bindings}")
            
            if code not in self.pending_bindings:
                logger.warning(f"❌ Code {code} not found in pending bindings")
                return {
                    'success': False,
                    'error': 'Invalid or expired binding code'
                }
            
            binding = self.pending_bindings[code]
            logger.info(f"✅ Found binding: {binding}")
            
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
            
            logger.info(f"✅ Binding activated: Telegram {telegram_id} -> Instagram @{instagram_username}")
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
    
    def get_user_bindings(self, telegram_id: int) -> List[str]:
        """Get all bindings for a Telegram user"""
        if telegram_id in self.active_bindings:
            return [self.active_bindings[telegram_id]]
        return []
    
    def remove_binding(self, telegram_id: int, instagram_username: str = None) -> bool:
        """Remove a binding"""
        try:
            if telegram_id in self.active_bindings:
                if instagram_username is None or self.active_bindings[telegram_id] == instagram_username:
                    del self.active_bindings[telegram_id]
                    logger.info(f"🗑️ Binding removed for Telegram user {telegram_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error removing binding: {e}")
            return False
    
    def cleanup_expired_bindings(self):
        """Remove expired pending bindings"""
        try:
            current_time = datetime.utcnow()
            expired_codes = []
            
            for code, binding in self.pending_bindings.items():
                expires_at = datetime.fromisoformat(binding['expires_at'])
                if current_time > expires_at:
                    expired_codes.append(code)
            
            for code in expired_codes:
                del self.pending_bindings[code]
                logger.info(f"⏰ Removed expired binding code: {code}")
            
            if expired_codes:
                logger.info(f"🧹 Cleanup completed: removed {len(expired_codes)} expired codes")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired bindings: {e}")
    
    def get_pending_binding(self, code: str) -> Optional[Dict]:
        """Get a pending binding by code"""
        return self.pending_bindings.get(code)
    
    def is_code_valid(self, code: str) -> bool:
        """Check if a binding code is valid and not expired"""
        if code not in self.pending_bindings:
            return False
        
        binding = self.pending_bindings[code]
        expires_at = datetime.fromisoformat(binding['expires_at'])
        return datetime.utcnow() <= expires_at
    
    def get_status(self) -> Dict:
        """Get current system status for debugging"""
        return {
            'pending_count': len(self.pending_bindings),
            'active_count': len(self.active_bindings),
            'pending_codes': list(self.pending_bindings.keys()),
            'active_bindings': self.active_bindings.copy()
        }

# Create a global instance
shared_binding_system = SharedBindingSystem()

# Export the instance for easy access
__all__ = ['shared_binding_system', 'SharedBindingSystem']
