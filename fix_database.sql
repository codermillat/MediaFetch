-- Fix MediaFetch Database Schema
-- Run this in your Supabase SQL Editor

-- Add missing is_used column to binding_codes table
ALTER TABLE binding_codes 
ADD COLUMN IF NOT EXISTS is_used BOOLEAN DEFAULT FALSE;

-- Add missing created_at column if it doesn't exist
ALTER TABLE binding_codes 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Add missing is_active column to user_bindings table
ALTER TABLE user_bindings 
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Update existing records to set is_used = false for codes that haven't been used
UPDATE binding_codes 
SET is_used = FALSE 
WHERE is_used IS NULL;

-- Update existing records to set is_active = true for existing bindings
UPDATE user_bindings 
SET is_active = TRUE 
WHERE is_active IS NULL;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_binding_codes_is_used ON binding_codes(is_used);
CREATE INDEX IF NOT EXISTS idx_user_bindings_is_active ON user_bindings(is_active);

-- Verify the changes
SELECT 
    table_name, 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name IN ('binding_codes', 'user_bindings')
ORDER BY table_name, ordinal_position;
