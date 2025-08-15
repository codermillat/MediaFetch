-- Binding System Tables for MediaFetch Bot
-- Run this in your Supabase SQL Editor

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table for storing pending binding codes
CREATE TABLE IF NOT EXISTS binding_codes (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    telegram_user_id BIGINT NOT NULL,
    instagram_username VARCHAR(255),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_used BOOLEAN DEFAULT FALSE
);

-- Table for storing active user bindings
CREATE TABLE IF NOT EXISTS user_bindings (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,
    instagram_username VARCHAR(255) NOT NULL,
    binding_code VARCHAR(10) NOT NULL,
    bound_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_binding_codes_code ON binding_codes(code);
CREATE INDEX IF NOT EXISTS idx_binding_codes_telegram_id ON binding_codes(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_binding_codes_expires ON binding_codes(expires_at);
CREATE INDEX IF NOT EXISTS idx_binding_codes_used ON binding_codes(is_used);

CREATE INDEX IF NOT EXISTS idx_user_bindings_telegram_id ON user_bindings(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_user_bindings_instagram ON user_bindings(instagram_username);
CREATE INDEX IF NOT EXISTS idx_user_bindings_active ON user_bindings(is_active);

-- Add unique constraint to prevent duplicate bindings
ALTER TABLE user_bindings ADD CONSTRAINT unique_telegram_instagram UNIQUE(telegram_user_id, instagram_username);

-- Add RLS (Row Level Security) policies if needed
-- ALTER TABLE binding_codes ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_bindings ENABLE ROW LEVEL SECURITY;

-- Insert some sample data for testing (optional)
-- INSERT INTO binding_codes (code, telegram_user_id, expires_at) VALUES 
-- ('TEST123', 123456789, NOW() + INTERVAL '24 hours');

-- View to see all pending codes
CREATE OR REPLACE VIEW pending_binding_codes AS
SELECT 
    code,
    telegram_user_id,
    expires_at,
    created_at
FROM binding_codes 
WHERE is_used = FALSE AND expires_at > NOW();

-- View to see all active bindings
CREATE OR REPLACE VIEW active_user_bindings AS
SELECT 
    telegram_user_id,
    instagram_username,
    bound_at
FROM user_bindings 
WHERE is_active = TRUE;

-- Function to cleanup expired codes
CREATE OR REPLACE FUNCTION cleanup_expired_binding_codes()
RETURNS INTEGER AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    UPDATE binding_codes 
    SET is_used = TRUE 
    WHERE expires_at < NOW() AND is_used = FALSE;
    
    GET DIAGNOSTICS expired_count = ROW_COUNT;
    
    RETURN expired_count;
END;
$$ LANGUAGE plpgsql;

-- Create a scheduled job to cleanup expired codes (optional)
-- SELECT cron.schedule('cleanup-expired-codes', '0 */6 * * *', 'SELECT cleanup_expired_binding_codes();');
