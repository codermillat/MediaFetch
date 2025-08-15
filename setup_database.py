#!/usr/bin/env python3
"""
Database Setup Script for MediaFetch Bot
Creates all necessary tables in Supabase
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_database():
    """Set up the database tables using Supabase REST API"""
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not configured")
        return False
    
    headers = {
        'Authorization': f'Bearer {supabase_key}',
        'Content-Type': 'application/json',
        'apikey': supabase_key
    }
    
    # SQL commands to create tables
    sql_commands = [
        # Enable UUID extension
        'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";',
        
        # Create binding_codes table
        '''CREATE TABLE IF NOT EXISTS binding_codes (
            id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
            code VARCHAR(10) UNIQUE NOT NULL,
            telegram_user_id BIGINT NOT NULL,
            instagram_username VARCHAR(255),
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            is_used BOOLEAN DEFAULT FALSE
        );''',
        
        # Create user_bindings table
        '''CREATE TABLE IF NOT EXISTS user_bindings (
            id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
            telegram_user_id BIGINT NOT NULL,
            instagram_username VARCHAR(255) NOT NULL,
            binding_code VARCHAR(10) NOT NULL,
            bound_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            is_active BOOLEAN DEFAULT TRUE
        );''',
        
        # Create content_deliveries table
        '''CREATE TABLE IF NOT EXISTS content_deliveries (
            id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
            telegram_user_id BIGINT NOT NULL,
            instagram_username VARCHAR(255) NOT NULL,
            content_type VARCHAR(50) NOT NULL,
            content_url TEXT,
            content_text TEXT,
            delivery_status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            delivered_at TIMESTAMP WITH TIME ZONE,
            error_message TEXT
        );''',
        
        # Create system_config table
        '''CREATE TABLE IF NOT EXISTS system_config (
            key VARCHAR(100) PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );''',
        
        # Create indexes
        'CREATE INDEX IF NOT EXISTS idx_binding_codes_code ON binding_codes(code);',
        'CREATE INDEX IF NOT EXISTS idx_binding_codes_telegram_user_id ON binding_codes(telegram_user_id);',
        'CREATE INDEX IF NOT EXISTS idx_binding_codes_expires_at ON binding_codes(expires_at);',
        'CREATE INDEX IF NOT EXISTS idx_user_bindings_telegram_user_id ON user_bindings(telegram_user_id);',
        'CREATE INDEX IF NOT EXISTS idx_user_bindings_instagram_username ON user_bindings(instagram_username);',
        'CREATE INDEX IF NOT EXISTS idx_content_deliveries_telegram_user_id ON content_deliveries(telegram_user_id);',
        'CREATE INDEX IF NOT EXISTS idx_content_deliveries_delivery_status ON content_deliveries(delivery_status);',
        
        # Insert default system configuration
        '''INSERT INTO system_config (key, value) VALUES 
            ('binding_code_expiry_hours', '24'),
            ('max_binding_attempts', '5'),
            ('content_delivery_retry_count', '3')
        ON CONFLICT (key) DO NOTHING;'''
    ]
    
    print("🚀 Setting up MediaFetch database...")
    
    # Try to execute SQL commands using the REST API
    # Note: This approach might not work for DDL commands
    # We'll need to use the Supabase dashboard or a different method
    
    print("⚠️  DDL commands cannot be executed via REST API")
    print("📋 Please execute the following SQL in your Supabase dashboard:")
    print("\n" + "="*50)
    
    for i, sql in enumerate(sql_commands, 1):
        print(f"\n-- Command {i}:")
        print(sql)
    
    print("\n" + "="*50)
    print("\n📝 Instructions:")
    print("1. Go to https://supabase.com/dashboard")
    print("2. Select your project: vtbrkmnizkyeflhwypfm")
    print("3. Go to SQL Editor")
    print("4. Copy and paste the SQL commands above")
    print("5. Click Run")
    
    return False

if __name__ == "__main__":
    setup_database()
