"""
Input Validation Module for MediaFetch
Provides comprehensive validation for all user inputs and API data
"""

import re
from typing import Dict, Any, Optional, List, Union
from urllib.parse import urlparse
from security_utils import SecurityUtils


class ValidationError(Exception):
    """Exception raised for validation errors"""
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"Validation error for {field}: {message}")


class InputValidator:
    """Comprehensive input validation for MediaFetch"""

    # Validation rules
    MAX_USERNAME_LENGTH = 30
    MAX_TEXT_LENGTH = 4096
    MAX_URL_LENGTH = 2048
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    # Instagram specific validation
    INSTAGRAM_USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_.]{1,30}$')
    INSTAGRAM_POST_PATTERN = re.compile(r'^[a-zA-Z0-9_]{11}$')  # Instagram post ID pattern

    # Telegram specific validation
    TELEGRAM_USER_ID_PATTERN = re.compile(r'^-?\d{8,10}$')  # Telegram user IDs
    TELEGRAM_USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{5,32}$')

    # URL validation patterns
    SUPPORTED_DOMAINS = {
        'youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com',
        'instagram.com', 'tiktok.com', 'twitter.com', 'facebook.com',
        'reddit.com', 'soundcloud.com', 'spotify.com'
    }

    @classmethod
    def validate_binding_request(cls, telegram_user_id: int, instagram_username: str) -> Dict[str, Any]:
        """Validate binding request parameters"""
        errors = []

        # Validate Telegram user ID
        if not cls._validate_telegram_user_id(telegram_user_id):
            errors.append(ValidationError('telegram_user_id', 'Invalid Telegram user ID format'))

        # Validate Instagram username
        if not cls._validate_instagram_username(instagram_username):
            errors.append(ValidationError('instagram_username', 'Invalid Instagram username format'))

        if errors:
            raise ValidationError('binding_request', f"Validation failed: {len(errors)} errors", errors)

        return {
            'telegram_user_id': telegram_user_id,
            'instagram_username': SecurityUtils.sanitize_text_input(instagram_username, 30)
        }

    @classmethod
    def validate_binding_code(cls, code: str) -> str:
        """Validate binding code"""
        if not SecurityUtils.validate_binding_code(code):
            raise ValidationError('binding_code', 'Invalid binding code format')

        return code.upper()

    @classmethod
    def validate_url(cls, url: str) -> str:
        """Validate and sanitize URL"""
        if not SecurityUtils.validate_url(url):
            raise ValidationError('url', 'Invalid URL format or security violation')

        # Additional domain validation
        if not cls._validate_supported_domain(url):
            raise ValidationError('url', 'Domain not supported for media downloads')

        return url.strip()

    @classmethod
    def validate_file_upload(cls, filename: str, file_size: int, content_type: str = None) -> Dict[str, Any]:
        """Validate file upload parameters"""
        errors = []

        # Validate filename
        if not filename or len(filename) > SecurityUtils.MAX_FILENAME_LENGTH:
            errors.append(ValidationError('filename', 'Invalid filename or filename too long'))

        # Validate file extension
        if not SecurityUtils.validate_file_extension(filename):
            errors.append(ValidationError('filename', 'File extension not allowed'))

        # Validate file size
        if file_size > cls.MAX_FILE_SIZE:
            errors.append(ValidationError('file_size', f'File size exceeds maximum {cls.MAX_FILE_SIZE} bytes'))

        # Validate content type if provided
        if content_type and not SecurityUtils.validate_mime_type(content_type):
            errors.append(ValidationError('content_type', 'MIME type not allowed'))

        if errors:
            raise ValidationError('file_upload', f"File validation failed: {len(errors)} errors", errors)

        return {
            'filename': SecurityUtils.sanitize_filename(filename),
            'file_size': file_size,
            'content_type': content_type
        }

    @classmethod
    def validate_user_message(cls, text: str, message_type: str = 'text') -> str:
        """Validate user message content"""
        if message_type == 'text':
            if not text or len(text) > cls.MAX_TEXT_LENGTH:
                raise ValidationError('message', 'Message text is empty or too long')

            # Sanitize text input
            sanitized = SecurityUtils.sanitize_text_input(text, cls.MAX_TEXT_LENGTH)
            return sanitized

        elif message_type == 'media':
            # For media messages, validate the URL or file info
            if not text:
                raise ValidationError('media_url', 'Media URL is required')

            return cls.validate_url(text)

        return text

    @classmethod
    def validate_instagram_content(cls, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Instagram content data"""
        errors = []

        required_fields = ['content_type', 'media_urls']
        for field in required_fields:
            if field not in content_data:
                errors.append(ValidationError(field, f'Required field {field} is missing'))

        # Validate content type
        content_type = content_data.get('content_type', '')
        if content_type not in ['reel', 'post', 'story', 'carousel']:
            errors.append(ValidationError('content_type', 'Invalid content type'))

        # Validate media URLs
        media_urls = content_data.get('media_urls', [])
        if not isinstance(media_urls, list) or not media_urls:
            errors.append(ValidationError('media_urls', 'Media URLs must be a non-empty list'))

        # Validate each URL
        for i, url in enumerate(media_urls):
            try:
                cls.validate_url(url)
            except ValidationError as e:
                errors.append(ValidationError(f'media_urls[{i}]', f'Invalid media URL: {e.message}'))

        # Validate Instagram username if provided
        if 'instagram_username' in content_data:
            username = content_data['instagram_username']
            if not cls._validate_instagram_username(username):
                errors.append(ValidationError('instagram_username', 'Invalid Instagram username'))

        if errors:
            raise ValidationError('instagram_content', f"Instagram content validation failed: {len(errors)} errors", errors)

        # Sanitize and return validated data
        return {
            'content_type': content_type,
            'media_urls': media_urls,
            'instagram_username': SecurityUtils.sanitize_text_input(
                content_data.get('instagram_username', ''), 30
            ),
            'caption': SecurityUtils.sanitize_text_input(
                content_data.get('caption', ''), 2200  # Instagram caption limit
            ),
            'metadata': content_data.get('metadata', {})
        }

    @classmethod
    def _validate_telegram_user_id(cls, user_id: Union[int, str]) -> bool:
        """Validate Telegram user ID"""
        try:
            user_id_str = str(user_id)
            return bool(cls.TELEGRAM_USER_ID_PATTERN.match(user_id_str))
        except (ValueError, TypeError):
            return False

    @classmethod
    def _validate_instagram_username(cls, username: str) -> bool:
        """Validate Instagram username"""
        if not username or len(username) > cls.MAX_USERNAME_LENGTH:
            return False
        return bool(cls.INSTAGRAM_USERNAME_PATTERN.match(username))

    @classmethod
    def _validate_supported_domain(cls, url: str) -> bool:
        """Check if URL domain is supported"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]

            # Check against supported domains
            return domain in cls.SUPPORTED_DOMAINS
        except Exception:
            return False

    @classmethod
    def sanitize_callback_data(cls, callback_data: str) -> str:
        """Sanitize callback data from inline keyboards"""
        if not callback_data or len(callback_data) > 64:  # Telegram callback data limit
            raise ValidationError('callback_data', 'Invalid callback data format')

        # Only allow alphanumeric characters, underscores, and colons
        if not re.match(r'^[a-zA-Z0-9_:]+$', callback_data):
            raise ValidationError('callback_data', 'Callback data contains invalid characters')

        return callback_data

    @classmethod
    def validate_pagination_params(cls, offset: int = 0, limit: int = 50) -> Dict[str, int]:
        """Validate pagination parameters"""
        errors = []

        if offset < 0:
            errors.append(ValidationError('offset', 'Offset must be non-negative'))

        if limit < 1 or limit > 100:
            errors.append(ValidationError('limit', 'Limit must be between 1 and 100'))

        if errors:
            raise ValidationError('pagination', f"Pagination validation failed: {len(errors)} errors", errors)

        return {'offset': offset, 'limit': limit}

    @classmethod
    def validate_search_query(cls, query: str) -> str:
        """Validate and sanitize search query"""
        if not query or len(query) > 200:
            raise ValidationError('search_query', 'Search query is empty or too long')

        # Remove potentially dangerous characters
        sanitized = SecurityUtils.sanitize_text_input(query, 200)

        # Remove excessive whitespace
        sanitized = ' '.join(sanitized.split())

        return sanitized
