#!/usr/bin/env python3
"""
Utility functions for MediaFetch bot
Common helper functions used throughout the application
"""

import re
import hashlib
import logging
from typing import Optional, List
from urllib.parse import urlparse, parse_qs
from pathlib import Path

logger = logging.getLogger(__name__)

def validate_url(url: str) -> bool:
    """
    Validate if the given string is a valid media URL
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    # Basic URL format validation
    try:
        parsed = urlparse(url.strip())
        if not parsed.scheme or not parsed.netloc:
            return False
    except Exception:
        return False
    
    # Check for supported platforms
    supported_domains = [
        'youtube.com', 'youtu.be', 'm.youtube.com',
        'tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com',
        'instagram.com', 'www.instagram.com',
        'vimeo.com', 'player.vimeo.com',
        'twitter.com', 'x.com', 'mobile.twitter.com',
        'facebook.com', 'm.facebook.com', 'fb.com',
        'reddit.com', 'm.reddit.com', 'old.reddit.com',
        'soundcloud.com', 'm.soundcloud.com',
        'open.spotify.com', 'spotify.com',
        'music.apple.com', 'itunes.apple.com'
    ]
    
    domain = parsed.netloc.lower()
    if domain.startswith('www.'):
        domain = domain[4:]
    
    return any(supported_domain in domain for supported_domain in supported_domains)

def extract_platform(url: str) -> Optional[str]:
    """
    Extract platform name from URL
    
    Args:
        url: Media URL
        
    Returns:
        Platform name or None if unknown
    """
    if not validate_url(url):
        return None
    
    domain = urlparse(url).netloc.lower()
    
    if 'youtube' in domain or 'youtu.be' in domain:
        return 'YouTube'
    elif 'tiktok' in domain:
        return 'TikTok'
    elif 'instagram' in domain:
        return 'Instagram'
    elif 'vimeo' in domain:
        return 'Vimeo'
    elif 'twitter' in domain or 'x.com' in domain:
        return 'Twitter'
    elif 'facebook' in domain or 'fb.com' in domain:
        return 'Facebook'
    elif 'reddit' in domain:
        return 'Reddit'
    elif 'soundcloud' in domain:
        return 'SoundCloud'
    elif 'spotify' in domain:
        return 'Spotify'
    elif 'apple.com' in domain:
        return 'Apple Music'
    else:
        return 'Unknown'

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file system operations
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    if not filename:
        return "unnamed_file"
    
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Limit length
    if len(filename) > 200:
        name, ext = Path(filename).stem, Path(filename).suffix
        filename = name[:200-len(ext)] + ext
    
    # Ensure it's not empty
    if not filename.strip():
        filename = "unnamed_file"
    
    return filename.strip()

def generate_file_hash(file_path: str) -> Optional[str]:
    """
    Generate SHA-256 hash of a file
    
    Args:
        file_path: Path to the file
        
    Returns:
        Hex digest of the file hash or None if failed
    """
    try:
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        logger.error(f"Failed to generate file hash: {e}")
        return None

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def format_duration(seconds: int) -> str:
    """
    Format duration in human-readable format
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60
        return f"{hours}h {remaining_minutes}m {remaining_seconds}s"

def extract_video_id(url: str, platform: str) -> Optional[str]:
    """
    Extract video ID from various platform URLs
    
    Args:
        url: Media URL
        platform: Platform name
        
    Returns:
        Video ID or None if not found
    """
    try:
        parsed = urlparse(url)
        
        if platform == 'YouTube':
            if 'youtube.com' in parsed.netloc:
                query_params = parse_qs(parsed.query)
                return query_params.get('v', [None])[0]
            elif 'youtu.be' in parsed.netloc:
                return parsed.path[1:]  # Remove leading slash
        
        elif platform == 'TikTok':
            # TikTok URLs are complex, try to extract ID
            path_parts = parsed.path.split('/')
            for part in path_parts:
                if part and len(part) > 10:  # TikTok IDs are usually long
                    return part
        
        elif platform == 'Instagram':
            # Instagram post IDs are in the path
            path_parts = parsed.path.split('/')
            for part in path_parts:
                if part and part.isalnum() and len(part) > 10:
                    return part
        
        elif platform == 'Vimeo':
            # Vimeo IDs are numeric and in the path
            path_parts = parsed.path.split('/')
            for part in path_parts:
                if part.isdigit():
                    return part
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to extract video ID: {e}")
        return None

def is_valid_file_extension(filename: str, allowed_extensions: List[str] = None) -> bool:
    """
    Check if file has valid extension
    
    Args:
        filename: Filename to check
        allowed_extensions: List of allowed extensions (default: common media formats)
        
    Returns:
        True if valid, False otherwise
    """
    if allowed_extensions is None:
        allowed_extensions = [
            '.mp4', '.avi', '.mov', '.mkv', '.webm',  # Video
            '.mp3', '.m4a', '.wav', '.flac', '.aac',  # Audio
            '.jpg', '.jpeg', '.png', '.gif', '.bmp'   # Image
        ]
    
    file_ext = Path(filename).suffix.lower()
    return file_ext in allowed_extensions

def create_temp_filename(prefix: str = "mediafetch", suffix: str = "") -> str:
    """
    Create a temporary filename
    
    Args:
        prefix: Filename prefix
        suffix: Filename suffix
        
    Returns:
        Temporary filename
    """
    import tempfile
    import uuid
    
    temp_dir = tempfile.gettempdir()
    unique_id = str(uuid.uuid4())[:8]
    
    if suffix and not suffix.startswith('.'):
        suffix = '.' + suffix
    
    return Path(temp_dir) / f"{prefix}_{unique_id}{suffix}"

def cleanup_old_files(directory: str, max_age_hours: int = 24):
    """
    Clean up old files in a directory
    
    Args:
        directory: Directory to clean
        max_age_hours: Maximum age of files in hours
    """
    try:
        import time
        from pathlib import Path
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        dir_path = Path(directory)
        if not dir_path.exists():
            return
        
        for file_path in dir_path.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                        logger.debug(f"Cleaned up old file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup file {file_path}: {e}")
                        
    except Exception as e:
        logger.error(f"Failed to cleanup old files: {e}")

def rate_limit_check(user_id: int, action: str, limit: int, window_seconds: int) -> bool:
    """
    Check if user has exceeded rate limit for an action
    
    Args:
        user_id: User ID
        action: Action type
        limit: Maximum allowed actions
        window_seconds: Time window in seconds
        
    Returns:
        True if within limit, False if exceeded
    """
    try:
        import time
        from collections import defaultdict
        
        # This is a simple in-memory rate limiter
        # In production, use Redis or database
        if not hasattr(rate_limit_check, '_action_history'):
            rate_limit_check._action_history = defaultdict(list)
        
        current_time = time.time()
        key = f"{user_id}:{action}"
        
        # Remove old entries
        rate_limit_check._action_history[key] = [
            timestamp for timestamp in rate_limit_check._action_history[key]
            if current_time - timestamp < window_seconds
        ]
        
        # Check if limit exceeded
        if len(rate_limit_check._action_history[key]) >= limit:
            return False
        
        # Add current action
        rate_limit_check._action_history[key].append(current_time)
        return True
        
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        return True  # Allow action if check fails
