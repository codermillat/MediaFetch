"""
Security Utilities for MediaFetch
Provides comprehensive security functions for input validation, sanitization, and protection
"""

import os
import re
import hashlib
import secrets
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import bleach
from pathlib import Path


class SecurityUtils:
    """Comprehensive security utilities for MediaFetch"""

    # File security constants
    MAX_FILENAME_LENGTH = 255
    ALLOWED_FILE_EXTENSIONS = {
        'video': ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v'],
        'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'],
        'document': ['.txt', '.pdf', '.doc', '.docx', '.json', '.log']
    }

    # Content type validation
    ALLOWED_MIME_TYPES = {
        'video/mp4', 'video/avi', 'video/quicktime', 'video/x-msvideo',
        'audio/mpeg', 'audio/wav', 'audio/flac',
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'application/pdf', 'text/plain'
    }

    # Input validation patterns
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{3,30}$')
    INSTAGRAM_USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_.]{1,30}$')
    TELEGRAM_USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{5,32}$')
    URL_PATTERN = re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE)

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename to prevent path traversal and injection attacks"""
        if not filename:
            return "unnamed_file"

        # Remove path separators and dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)

        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')

        # Limit length
        if len(sanitized) > cls.MAX_FILENAME_LENGTH:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:cls.MAX_FILENAME_LENGTH - len(ext)] + ext

        # Ensure we have a valid filename
        if not sanitized:
            return "unnamed_file"

        return sanitized

    @classmethod
    def validate_file_path(cls, file_path: str, base_dir: str = None) -> bool:
        """Validate file path to prevent directory traversal attacks"""
        if not file_path:
            return False

        try:
            # Convert to Path object for safe handling
            path = Path(file_path).resolve()

            # Check for null bytes
            if '\x00' in file_path:
                return False

            # Check for path traversal attempts
            if '..' in file_path or file_path.startswith('/'):
                return False

            # If base_dir is provided, ensure path is within it
            if base_dir:
                base_path = Path(base_dir).resolve()
                if not path.is_relative_to(base_path):
                    return False

            return True
        except (ValueError, OSError):
            return False

    @classmethod
    def get_secure_file_path(cls, filename: str, upload_dir: str) -> str:
        """Generate a secure file path with sanitized filename"""
        sanitized_filename = cls.sanitize_filename(filename)
        secure_path = os.path.join(upload_dir, sanitized_filename)

        # Validate the final path
        if not cls.validate_file_path(secure_path, upload_dir):
            raise ValueError("Invalid file path generated")

        return secure_path

    @classmethod
    def validate_file_extension(cls, filename: str, allowed_types: List[str] = None) -> bool:
        """Validate file extension against allowed types"""
        if not filename:
            return False

        _, ext = os.path.splitext(filename.lower())

        if allowed_types:
            return ext in allowed_types

        # Check against all allowed extensions
        for category_extensions in cls.ALLOWED_FILE_EXTENSIONS.values():
            if ext in category_extensions:
                return True

        return False

    @classmethod
    def validate_mime_type(cls, mime_type: str) -> bool:
        """Validate MIME type against allowed types"""
        return mime_type.lower() in cls.ALLOWED_MIME_TYPES

    @classmethod
    def validate_url(cls, url: str) -> bool:
        """Validate URL format and security"""
        if not url or len(url) > 2048:  # Reasonable URL length limit
            return False

        # Basic URL pattern match
        if not cls.URL_PATTERN.match(url):
            return False

        try:
            parsed = urlparse(url)

            # Only allow http/https
            if parsed.scheme not in ['http', 'https']:
                return False

            # Prevent localhost/private network access
            if cls._is_private_network(parsed.hostname):
                return False

            return True
        except Exception:
            return False

    @classmethod
    def _is_private_network(cls, hostname: str) -> bool:
        """Check if hostname is a private network address"""
        if not hostname:
            return True

        # List of private IP ranges and localhost
        private_ranges = [
            'localhost', '127.0.0.1', '::1',
            '10.', '172.', '192.168.',
            '169.254.'  # Link-local
        ]

        return any(hostname.startswith(prefix) for prefix in private_ranges)

    @classmethod
    def validate_username(cls, username: str, username_type: str = 'generic') -> bool:
        """Validate username based on type"""
        if not username or len(username) > 100:
            return False

        patterns = {
            'instagram': cls.INSTAGRAM_USERNAME_PATTERN,
            'telegram': cls.TELEGRAM_USERNAME_PATTERN,
            'generic': cls.USERNAME_PATTERN
        }

        pattern = patterns.get(username_type, cls.USERNAME_PATTERN)
        return bool(pattern.match(username))

    @classmethod
    def sanitize_text_input(cls, text: str, max_length: int = 1000) -> str:
        """Sanitize text input to prevent XSS and injection attacks"""
        if not text:
            return ""

        # Limit length
        if len(text) > max_length:
            text = text[:max_length]

        # Remove null bytes and control characters
        text = text.replace('\x00', '').replace('\r', '').replace('\n', ' ')

        # Use bleach to clean HTML and prevent XSS
        cleaned = bleach.clean(text, tags=[], attributes={}, strip=True)

        return cleaned.strip()

    @classmethod
    def generate_secure_token(cls, length: int = 32) -> str:
        """Generate a secure random token"""
        return secrets.token_urlsafe(length)

    @classmethod
    def hash_content(cls, content: str, salt: str = None) -> str:
        """Generate a secure hash of content for integrity checking"""
        if salt is None:
            salt = secrets.token_hex(16)

        content_with_salt = f"{salt}:{content}"
        return hashlib.sha256(content_with_salt.encode()).hexdigest()

    @classmethod
    def validate_binding_code(cls, code: str) -> bool:
        """Validate binding code format and security"""
        if not code or len(code) > 10:
            return False

        # Only allow alphanumeric characters
        return bool(re.match(r'^[A-Z0-9]{6,10}$', code))

    @classmethod
    def rate_limit_check(cls, identifier: str, max_requests: int, window_seconds: int,
                        cache: Dict[str, List[float]]) -> bool:
        """Check if request is within rate limits"""
        current_time = __import__('time').time()
        window_start = current_time - window_seconds

        # Clean old entries
        if identifier in cache:
            cache[identifier] = [t for t in cache[identifier] if t > window_start]

        # Check if under limit
        if identifier not in cache or len(cache[identifier]) < max_requests:
            if identifier not in cache:
                cache[identifier] = []
            cache[identifier].append(current_time)
            return True

        return False

    @classmethod
    def escape_telegram_markdown(cls, text: str) -> str:
        """Escape special characters for Telegram Markdown"""
        if not text:
            return ""

        # Characters to escape in Telegram Markdown
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

        for char in escape_chars:
            text = text.replace(char, f'\\{char}')

        return text
