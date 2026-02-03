from __future__ import annotations

import pytest
from app.core.security import (
    RateLimiter,
    APIKeyValidator,
    validate_file_upload,
    sanitize_input,
    SecurityError,
)


def test_rate_limiter_allows_requests():
    """Test that rate limiter allows requests within limit."""
    limiter = RateLimiter(requests_per_minute=5)

    # Should allow first 5 requests
    for i in range(5):
        assert limiter.is_allowed("test_key")

    # Should block 6th request
    assert not limiter.is_allowed("test_key")


def test_rate_limiter_different_keys():
    """Test that rate limiter tracks different keys separately."""
    limiter = RateLimiter(requests_per_minute=2)

    assert limiter.is_allowed("key1")
    assert limiter.is_allowed("key1")
    assert limiter.is_allowed("key2")
    assert limiter.is_allowed("key2")

    # Both should be at limit now
    assert not limiter.is_allowed("key1")
    assert not limiter.is_allowed("key2")


def test_api_key_validator():
    """Test API key validation."""
    validator = APIKeyValidator(["secret123", "secret456"])

    assert validator.validate("secret123")
    assert validator.validate("secret456")
    assert not validator.validate("wrong")
    assert not validator.validate("secret")


def test_api_key_generation():
    """Test API key generation."""
    key = APIKeyValidator.generate_key()

    assert isinstance(key, str)
    assert len(key) > 20  # Should be reasonably long


def test_validate_file_upload_valid():
    """Test file upload validation with valid PDF."""
    # Should not raise
    validate_file_upload("document.pdf", 1024 * 1024)  # 1 MB


def test_validate_file_upload_invalid_extension():
    """Test file upload validation with invalid extension."""
    with pytest.raises(SecurityError, match="File type not allowed"):
        validate_file_upload("document.exe", 1024)


def test_validate_file_upload_too_large():
    """Test file upload validation with oversized file."""
    with pytest.raises(SecurityError, match="File too large"):
        validate_file_upload("document.pdf", 100 * 1024 * 1024)  # 100 MB


def test_validate_file_upload_path_traversal():
    """Test file upload validation blocks path traversal."""
    with pytest.raises(SecurityError, match="path traversal"):
        validate_file_upload("../etc/passwd.pdf", 1024)

    with pytest.raises(SecurityError, match="path traversal"):
        validate_file_upload("subdir/../../file.pdf", 1024)


def test_sanitize_input_valid():
    """Test input sanitization with valid input."""
    result = sanitize_input("  Hello World  ")
    assert result == "Hello World"


def test_sanitize_input_too_long():
    """Test input sanitization with oversized input."""
    with pytest.raises(SecurityError, match="Input too long"):
        sanitize_input("a" * 20000, max_length=1000)


def test_sanitize_input_removes_control_chars():
    """Test that sanitization removes control characters."""
    result = sanitize_input("Hello\x00World\x01Test")
    assert "\x00" not in result
    assert "\x01" not in result


def test_sanitize_input_empty():
    """Test input sanitization with empty input."""
    with pytest.raises(SecurityError, match="non-empty"):
        sanitize_input("")

    with pytest.raises(SecurityError, match="non-empty"):
        sanitize_input("   ")
