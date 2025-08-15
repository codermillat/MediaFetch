-- MediaFetch Database Schema
-- Run this in your Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    telegram_user_id BIGINT UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    preferences JSONB DEFAULT '{}'::jsonb
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

-- Create indexes for better performance
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

-- Insert some sample data for testing
INSERT INTO users (username, email) VALUES 
    ('testuser', 'test@example.com'),
    ('demo_user', 'demo@example.com')
ON CONFLICT (username) DO NOTHING;

-- Create a view for recent activity
CREATE OR REPLACE VIEW recent_activity AS
SELECT 
    'new_post' as activity_type,
    ia.username as account_name,
    ip.caption as description,
    ip.created_at as activity_time
FROM instagram_posts ip
JOIN instagram_accounts ia ON ip.instagram_account_id = ia.id
WHERE ip.created_at > NOW() - INTERVAL '7 days'
UNION ALL
SELECT 
    'download_completed' as activity_type,
    u.username as account_name,
    CONCAT('Downloaded ', COUNT(*), ' files') as description,
    MAX(mf.downloaded_at) as activity_time
FROM media_files mf
JOIN instagram_posts ip ON mf.post_id = ip.id
JOIN instagram_accounts ia ON ip.instagram_account_id = ia.id
JOIN users u ON ia.user_id = u.id
WHERE mf.download_status = 'completed' 
    AND mf.downloaded_at > NOW() - INTERVAL '7 days'
GROUP BY u.username
ORDER BY activity_time DESC;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO anon;
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
