-- MediaFetch Database Schema
-- Run this in your Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    telegram_user_id BIGINT UNIQUE NOT NULL,
    telegram_username VARCHAR(255),
    telegram_first_name VARCHAR(255),
    telegram_last_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    preferences JSONB DEFAULT '{}'::jsonb,
    binding_status VARCHAR(50) DEFAULT 'unbound' -- unbound, pending, bound, expired
);

-- Instagram accounts table
CREATE TABLE IF NOT EXISTS instagram_accounts (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    username VARCHAR(255) NOT NULL,
    is_private BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    follower_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    post_count INTEGER DEFAULT 0,
    profile_picture_url TEXT,
    bio TEXT,
    external_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_monitored TIMESTAMP WITH TIME ZONE,
    monitoring_enabled BOOLEAN DEFAULT TRUE
);

-- User Binding System
CREATE TABLE IF NOT EXISTS user_bindings (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    telegram_user_id BIGINT NOT NULL,
    instagram_username VARCHAR(255) NOT NULL,
    binding_code VARCHAR(10) UNIQUE NOT NULL, -- 6-10 character unique code
    binding_status VARCHAR(50) DEFAULT 'pending', -- pending, confirmed, expired, revoked
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    confirmed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(telegram_user_id, instagram_username)
);

-- Binding Codes (for tracking and security)
CREATE TABLE IF NOT EXISTS binding_codes (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    telegram_user_id BIGINT NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3
);

-- Content Delivery Log
CREATE TABLE IF NOT EXISTS content_deliveries (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    binding_id UUID REFERENCES user_bindings(id) ON DELETE CASCADE,
    instagram_username VARCHAR(255) NOT NULL,
    telegram_user_id BIGINT NOT NULL,
    content_type VARCHAR(50) NOT NULL, -- reel, story, post, dm_text
    instagram_content_id VARCHAR(255), -- Instagram's content ID
    content_url TEXT,
    local_file_path TEXT,
    file_size BIGINT,
    delivery_status VARCHAR(50) DEFAULT 'pending', -- pending, downloading, processing, delivered, failed
    delivery_attempts INTEGER DEFAULT 0,
    max_delivery_attempts INTEGER DEFAULT 3,
    error_message TEXT,
    delivered_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Instagram posts table
CREATE TABLE IF NOT EXISTS instagram_posts (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    instagram_account_id UUID REFERENCES instagram_accounts(id) ON DELETE CASCADE,
    post_id VARCHAR(255) UNIQUE NOT NULL,
    shortcode VARCHAR(255),
    caption TEXT,
    media_type VARCHAR(50), -- IMAGE, VIDEO, CAROUSEL_ALBUM
    media_count INTEGER DEFAULT 1,
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    post_url TEXT,
    thumbnail_url TEXT,
    is_video BOOLEAN DEFAULT FALSE,
    video_url TEXT,
    video_duration REAL,
    location_name VARCHAR(255),
    location_id VARCHAR(255),
    posted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_downloaded BOOLEAN DEFAULT FALSE,
    download_status VARCHAR(50) DEFAULT 'pending' -- pending, downloading, completed, failed
);

-- Media files table
CREATE TABLE IF NOT EXISTS media_files (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    post_id UUID REFERENCES instagram_posts(id) ON DELETE CASCADE,
    file_url TEXT NOT NULL,
    local_file_path TEXT,
    file_name VARCHAR(255),
    file_size BIGINT,
    file_type VARCHAR(50), -- image, video
    mime_type VARCHAR(100),
    width INTEGER,
    height INTEGER,
    duration REAL, -- for videos
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    downloaded_at TIMESTAMP WITH TIME ZONE,
    download_status VARCHAR(50) DEFAULT 'pending', -- pending, downloading, completed, failed
    processing_status VARCHAR(50) DEFAULT 'pending' -- pending, processing, completed, failed
);

-- Download tasks table
CREATE TABLE IF NOT EXISTS download_tasks (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    post_id UUID REFERENCES instagram_posts(id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL, -- post_download, story_download, highlight_download
    status VARCHAR(50) DEFAULT 'pending', -- pending, in_progress, completed, failed
    priority INTEGER DEFAULT 1,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Monitoring logs table
CREATE TABLE IF NOT EXISTS monitoring_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    instagram_account_id UUID REFERENCES instagram_accounts(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL, -- new_post, new_story, profile_update
    details JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(50) DEFAULT 'success', -- success, warning, error
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Telegram bot sessions table
CREATE TABLE IF NOT EXISTS telegram_sessions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    telegram_user_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    preferences JSONB DEFAULT '{}'::jsonb
);

-- User preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    preference_key VARCHAR(255) NOT NULL,
    preference_value TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, preference_key)
);

-- System Configuration
CREATE TABLE IF NOT EXISTS system_config (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    config_key VARCHAR(255) UNIQUE NOT NULL,
    config_value TEXT,
    config_type VARCHAR(50) DEFAULT 'string', -- string, integer, boolean, json
    description TEXT,
    is_editable BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_users_binding_status ON users(binding_status);
CREATE INDEX IF NOT EXISTS idx_user_bindings_telegram_id ON user_bindings(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_user_bindings_instagram_username ON user_bindings(instagram_username);
CREATE INDEX IF NOT EXISTS idx_user_bindings_status ON user_bindings(binding_status);
CREATE INDEX IF NOT EXISTS idx_binding_codes_code ON binding_codes(code);
CREATE INDEX IF NOT EXISTS idx_binding_codes_telegram_id ON binding_codes(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_content_deliveries_telegram_id ON content_deliveries(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_content_deliveries_status ON content_deliveries(delivery_status);
CREATE INDEX IF NOT EXISTS idx_instagram_posts_post_id ON instagram_posts(post_id);
CREATE INDEX IF NOT EXISTS idx_instagram_posts_instagram_account_id ON instagram_posts(instagram_account_id);
CREATE INDEX IF NOT EXISTS idx_instagram_posts_posted_at ON instagram_posts(posted_at);
CREATE INDEX IF NOT EXISTS idx_media_files_post_id ON media_files(post_id);
CREATE INDEX IF NOT EXISTS idx_download_tasks_user_id ON download_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_download_tasks_status ON download_tasks(status);
CREATE INDEX IF NOT EXISTS idx_monitoring_logs_instagram_account_id ON monitoring_logs(instagram_account_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_logs_created_at ON monitoring_logs(created_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_instagram_accounts_updated_at BEFORE UPDATE ON instagram_accounts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_instagram_posts_updated_at BEFORE UPDATE ON instagram_posts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON user_preferences FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_bindings_updated_at BEFORE UPDATE ON user_bindings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_content_deliveries_updated_at BEFORE UPDATE ON content_deliveries FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert system configuration
INSERT INTO system_config (config_key, config_value, config_type, description) VALUES 
    ('binding_code_length', '8', 'integer', 'Length of binding codes generated for users'),
    ('binding_code_expiry_hours', '24', 'integer', 'Hours until binding code expires'),
    ('max_binding_attempts', '3', 'integer', 'Maximum attempts to use a binding code'),
    ('content_delivery_retries', '3', 'integer', 'Maximum retries for content delivery'),
    ('cleanup_old_bindings_days', '30', 'integer', 'Days to keep old binding records'),
    ('max_file_size_mb', '50', 'integer', 'Maximum file size in MB for downloads'),
    ('instagram_monitoring_interval_minutes', '5', 'integer', 'Interval to check Instagram for new content')
ON CONFLICT (config_key) DO NOTHING;

-- Insert some sample data for testing
INSERT INTO users (username, telegram_user_id, telegram_username, telegram_first_name, binding_status) VALUES 
    ('testuser', 123456789, 'testuser', 'Test', 'unbound'),
    ('demo_user', 987654321, 'demo_user', 'Demo', 'unbound')
ON CONFLICT (telegram_user_id) DO NOTHING;

-- Create a view for active bindings
CREATE OR REPLACE VIEW active_bindings AS
SELECT 
    ub.id,
    u.username as telegram_username,
    u.telegram_user_id,
    ub.instagram_username,
    ub.binding_status,
    ub.confirmed_at,
    ub.last_activity,
    COUNT(cd.id) as total_deliveries,
    COUNT(CASE WHEN cd.delivery_status = 'delivered' THEN 1 END) as successful_deliveries
FROM user_bindings ub
JOIN users u ON ub.user_id = u.id
LEFT JOIN content_deliveries cd ON ub.id = cd.binding_id
WHERE ub.is_active = TRUE AND ub.binding_status = 'confirmed'
GROUP BY ub.id, u.username, u.telegram_user_id, ub.instagram_username, ub.binding_status, ub.confirmed_at, ub.last_activity;

-- Create a view for recent activity
CREATE OR REPLACE VIEW recent_activity AS
SELECT 
    'new_binding' as activity_type,
    u.username as telegram_username,
    CONCAT('Bound to @', ub.instagram_username) as description,
    ub.confirmed_at as activity_time
FROM user_bindings ub
JOIN users u ON ub.user_id = u.id
WHERE ub.binding_status = 'confirmed' AND ub.confirmed_at > NOW() - INTERVAL '7 days'
UNION ALL
SELECT 
    'content_delivered' as activity_type,
    u.username as telegram_username,
    CONCAT('Delivered ', cd.content_type, ' from @', cd.instagram_username) as description,
    cd.delivered_at as activity_time
FROM content_deliveries cd
JOIN users u ON cd.telegram_user_id = u.telegram_user_id
WHERE cd.delivery_status = 'delivered' AND cd.delivered_at > NOW() - INTERVAL '7 days'
ORDER BY activity_time DESC;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO anon;
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
