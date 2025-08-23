"""
Security Tests for MediaFetch
Tests security utilities, input validation, and protection mechanisms
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import security modules
from security_utils import SecurityUtils, ValidationError
from input_validation import InputValidator, ValidationError as ValidationError2


class TestSecurityUtils:
    """Test security utility functions"""

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization"""
        assert SecurityUtils.sanitize_filename("test file.jpg") == "test file.jpg"
        assert SecurityUtils.sanitize_filename("test<file>.exe") == "testfile.exe"
        assert SecurityUtils.sanitize_filename("") == "unnamed_file"
        assert SecurityUtils.sanitize_filename("file with spaces") == "file with spaces"

    def test_sanitize_filename_long(self):
        """Test filename sanitization with long names"""
        long_name = "a" * 300 + ".txt"
        sanitized = SecurityUtils.sanitize_filename(long_name)
        assert len(sanitized) <= 255
        assert sanitized.endswith(".txt")

    def test_sanitize_filename_dangerous(self):
        """Test sanitization of dangerous filenames"""
        assert SecurityUtils.sanitize_filename("../../../etc/passwd") == "etcpasswd"
        assert SecurityUtils.sanitize_filename("file\x00name.txt") == "filename.txt"
        assert SecurityUtils.sanitize_filename("file\nname.txt") == "filename.txt"

    def test_validate_file_path_safe(self):
        """Test validation of safe file paths"""
        with tempfile.TemporaryDirectory() as temp_dir:
            safe_path = os.path.join(temp_dir, "test.txt")
            assert SecurityUtils.validate_file_path(safe_path, temp_dir) == True

    def test_validate_file_path_traversal(self):
        """Test validation of path traversal attempts"""
        with tempfile.TemporaryDirectory() as temp_dir:
            dangerous_path = os.path.join(temp_dir, "../../../etc/passwd")
            assert SecurityUtils.validate_file_path(dangerous_path, temp_dir) == False

    def test_validate_url_safe(self):
        """Test validation of safe URLs"""
        safe_urls = [
            "https://youtube.com/watch?v=test",
            "https://instagram.com/user",
            "http://example.com/path"
        ]
        for url in safe_urls:
            assert SecurityUtils.validate_url(url) == True

    def test_validate_url_dangerous(self):
        """Test validation of dangerous URLs"""
        dangerous_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "ftp://example.com/file",
            "http://localhost/../../etc/passwd",
            "https://127.0.0.1:8080"
        ]
        for url in dangerous_urls:
            assert SecurityUtils.validate_url(url) == False

    def test_validate_username(self):
        """Test username validation"""
        assert SecurityUtils.validate_username("validuser123") == True
        assert SecurityUtils.validate_username("user_name") == True
        assert SecurityUtils.validate_username("user-name") == True
        assert SecurityUtils.validate_username("user.name") == True

        assert SecurityUtils.validate_username("") == False
        assert SecurityUtils.validate_username("ab") == False  # too short
        assert SecurityUtils.validate_username("a" * 50) == False  # too long
        assert SecurityUtils.validate_username("user@domain.com") == False  # invalid chars

    def test_sanitize_text_input(self):
        """Test text input sanitization"""
        # Basic sanitization
        assert SecurityUtils.sanitize_text_input("Hello World") == "Hello World"

        # XSS prevention
        xss_input = '<script>alert("xss")</script>Hello'
        sanitized = SecurityUtils.sanitize_text_input(xss_input)
        assert '<script>' not in sanitized
        assert 'alert' not in sanitized
        assert 'Hello' in sanitized

        # Length limiting
        long_text = "a" * 2000
        assert len(SecurityUtils.sanitize_text_input(long_text, 100)) == 100

    def test_rate_limit_check(self):
        """Test rate limiting functionality"""
        cache = {}

        # First few requests should pass
        assert SecurityUtils.rate_limit_check("user1", 3, 60, cache) == True
        assert SecurityUtils.rate_limit_check("user1", 3, 60, cache) == True
        assert SecurityUtils.rate_limit_check("user1", 3, 60, cache) == True

        # Fourth request should be blocked
        assert SecurityUtils.rate_limit_check("user1", 3, 60, cache) == False

    def test_generate_secure_token(self):
        """Test secure token generation"""
        token1 = SecurityUtils.generate_secure_token(32)
        token2 = SecurityUtils.generate_secure_token(32)

        # Tokens should be different
        assert token1 != token2

        # Token should be URL-safe
        assert all(c.isalnum() or c in '-_' for c in token1)

        # Test custom length
        token_short = SecurityUtils.generate_secure_token(16)
        assert len(token_short) >= 16  # URL-safe encoding may increase length


class TestInputValidator:
    """Test input validation functions"""

    def test_validate_binding_request_valid(self):
        """Test validation of valid binding requests"""
        result = InputValidator.validate_binding_request(123456789, "validuser123")
        assert result['telegram_user_id'] == 123456789
        assert result['instagram_username'] == "validuser123"

    def test_validate_binding_request_invalid_user_id(self):
        """Test validation of invalid user IDs"""
        with pytest.raises(ValidationError2):
            InputValidator.validate_binding_request(-1, "validuser")

    def test_validate_binding_request_invalid_username(self):
        """Test validation of invalid usernames"""
        invalid_usernames = ["", "ab", "user@domain.com", "user" * 50]

        for username in invalid_usernames:
            with pytest.raises(ValidationError2):
                InputValidator.validate_binding_request(123456789, username)

    def test_validate_binding_code_valid(self):
        """Test validation of valid binding codes"""
        valid_codes = ["ABC12345", "XYZ98765", "123ABC789"]

        for code in valid_codes:
            assert InputValidator.validate_binding_code(code) == code.upper()

    def test_validate_binding_code_invalid(self):
        """Test validation of invalid binding codes"""
        invalid_codes = [
            "", "ABC", "ABC123", "abc12345",  # wrong length or case
            "ABC123@#", "123-456-789",  # invalid characters
            "ABCDEFGHI"  # too long
        ]

        for code in invalid_codes:
            with pytest.raises(ValidationError2):
                InputValidator.validate_binding_code(code)

    def test_validate_url_valid(self):
        """Test validation of valid URLs"""
        valid_urls = [
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://instagram.com/username",
            "http://example.com/path/to/resource"
        ]

        for url in valid_urls:
            result = InputValidator.validate_url(url)
            assert result == url

    def test_validate_url_invalid(self):
        """Test validation of invalid URLs"""
        invalid_urls = [
            "", "not a url", "javascript:alert(1)",
            "ftp://example.com", "http://localhost/path",
            "https://127.0.0.1/path"
        ]

        for url in invalid_urls:
            with pytest.raises(ValidationError2):
                InputValidator.validate_url(url)

    def test_validate_file_upload_valid(self):
        """Test validation of valid file uploads"""
        result = InputValidator.validate_file_upload(
            "test_image.jpg",
            1024 * 1024,  # 1MB
            "image/jpeg"
        )

        assert result['filename'] == "test_image.jpg"
        assert result['file_size'] == 1024 * 1024
        assert result['content_type'] == "image/jpeg"

    def test_validate_file_upload_invalid_filename(self):
        """Test validation of invalid filenames"""
        invalid_filenames = [
            "", "../../../etc/passwd", "file\x00name.jpg",
            "a" * 300 + ".txt"  # too long
        ]

        for filename in invalid_filenames:
            with pytest.raises(ValidationError2):
                InputValidator.validate_file_upload(filename, 1024, "image/jpeg")

    def test_validate_file_upload_too_large(self):
        """Test validation of oversized files"""
        with pytest.raises(ValidationError2):
            InputValidator.validate_file_upload(
                "large_file.jpg",
                100 * 1024 * 1024,  # 100MB (over limit)
                "image/jpeg"
            )

    def test_validate_file_upload_invalid_mime(self):
        """Test validation of invalid MIME types"""
        with pytest.raises(ValidationError2):
            InputValidator.validate_file_upload(
                "script.php",
                1024,
                "application/x-php"
            )

    def test_validate_user_message_valid(self):
        """Test validation of valid user messages"""
        result = InputValidator.validate_user_message("Hello World")
        assert result == "Hello World"

    def test_validate_user_message_too_long(self):
        """Test validation of overly long messages"""
        long_message = "a" * 5000
        with pytest.raises(ValidationError2):
            InputValidator.validate_user_message(long_message)

    def test_validate_pagination_params(self):
        """Test pagination parameter validation"""
        # Valid parameters
        result = InputValidator.validate_pagination_params(10, 50)
        assert result == {'offset': 10, 'limit': 50}

        # Invalid offset
        with pytest.raises(ValidationError2):
            InputValidator.validate_pagination_params(-1, 50)

        # Invalid limit
        with pytest.raises(ValidationError2):
            InputValidator.validate_pagination_params(0, 200)

    def test_validate_search_query(self):
        """Test search query validation"""
        # Valid query
        result = InputValidator.validate_search_query("test search query")
        assert result == "test search query"

        # Empty query
        with pytest.raises(ValidationError2):
            InputValidator.validate_search_query("")

        # Too long query
        with pytest.raises(ValidationError2):
            InputValidator.validate_search_query("a" * 300)
