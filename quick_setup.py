#!/usr/bin/env python3
"""
Quick Database Setup Test for MediaFetch Bot
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connection():
    """Test the Supabase connection"""
    
    # Get credentials from environment or use the ones from your logs
    supabase_url = os.getenv('SUPABASE_URL', 'https://vtbrkmnizkyeflhwypfm.supabase.co')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ0YnJrbW5pemt5ZWZsaHd5cGZtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTI2NjExMywiZXhwIjoyMDcwODQyMTEzfQ.ZXPc8GwbU3lLq8g1OT2rf24IMNGI-aSikWXoZEze9pk')
    
    print("🔍 Testing Supabase connection...")
    print(f"URL: {supabase_url}")
    print(f"Key: {supabase_key[:20]}...")
    
    headers = {
        'Authorization': f'Bearer {supabase_key}',
        'Content-Type': 'application/json',
        'apikey': supabase_key
    }
    
    try:
        # Test basic connection
        response = requests.get(f"{supabase_url}/rest/v1/", headers=headers)
        if response.status_code == 200:
            print("✅ Connection successful!")
            
            # Try to create a test table (this will fail, but shows the error)
            test_data = {
                'code': 'TEST123',
                'telegram_user_id': 123456,
                'instagram_username': 'testuser',
                'expires_at': '2025-08-16T20:36:00Z',
                'is_used': False
            }
            
            response = requests.post(f"{supabase_url}/rest/v1/binding_codes", 
                                  headers=headers, json=test_data)
            
            if response.status_code == 404:
                print("❌ Table 'binding_codes' does not exist yet")
                print("\n📋 You need to create the database tables first!")
                print("\n" + "="*60)
                print("🚀 QUICK SETUP INSTRUCTIONS:")
                print("="*60)
                print("\n1. Go to: https://supabase.com/dashboard")
                print("2. Select project: vtbrkmnizkyeflhwypfm")
                print("3. Click 'SQL Editor' in left sidebar")
                print("4. Click 'New Query'")
                print("5. Copy and paste the SQL from 'binding_tables.sql'")
                print("6. Click 'Run' button")
                print("\n" + "="*60)
                
                # Show the SQL commands
                print("\n📝 SQL COMMANDS TO EXECUTE:")
                print("="*60)
                
                sql_commands = [
                    "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";",
                    """CREATE TABLE IF NOT EXISTS binding_codes (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    telegram_user_id BIGINT NOT NULL,
    instagram_username VARCHAR(255),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_used BOOLEAN DEFAULT FALSE
);""",
                    """CREATE TABLE IF NOT EXISTS user_bindings (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,
    instagram_username VARCHAR(255) NOT NULL,
    binding_code VARCHAR(10) NOT NULL,
    bound_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);""",
                    "CREATE INDEX IF NOT EXISTS idx_binding_codes_code ON binding_codes(code);",
                    "CREATE INDEX IF NOT EXISTS idx_binding_codes_telegram_id ON binding_codes(telegram_user_id);",
                    "CREATE INDEX IF NOT EXISTS idx_user_bindings_telegram_id ON user_bindings(telegram_user_id);",
                    "CREATE INDEX IF NOT EXISTS idx_user_bindings_instagram ON user_bindings(instagram_username);"
                ]
                
                for i, sql in enumerate(sql_commands, 1):
                    print(f"\n-- Command {i}:")
                    print(sql)
                
                print("\n" + "="*60)
                print("🎯 After creating tables, your binding system will work!")
                print("="*60)
                
            else:
                print(f"❌ Unexpected response: {response.status_code}")
                print(response.text)
                
        else:
            print(f"❌ Connection failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_connection()
