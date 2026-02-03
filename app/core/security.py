from __future__ import annotations

import hashlib
import secrets
import time
from collections import defaultdict
from typing import Dict, Optional

from fastapi import Header, HTTPException, Request, status
from loguru import logger

from app.core.config import settings


class SecurityError(Exception):
    """Base exception for security-related errors."""


class RateLimiter:
    """Token bucket rate limiter for API endpoints."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list[float]] = defaultdict(list)
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()

    def _cleanup_old_entries(self) -> None:
        """Remove old entries to prevent memory leaks."""
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            cutoff = current_time - 60
            for key in list(self.requests.keys()):
                self.requests[key] = [t for t in self.requests[key] if t > cutoff]
                if not self.requests[key]:
                    del self.requests[key]
            self.last_cleanup = current_time

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed based on rate limit.

        Args:
            key: Unique identifier (IP address, user ID, etc.)

        Returns:
            True if request is allowed, False otherwise.
        """
        current_time = time.time()
        cutoff = current_time - 60  # 1 minute window

        # Clean old entries
        self._cleanup_old_entries()

        # Filter requests in current window
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]

        if len(self.requests[key]) >= self.requests_per_minute:
            return False

        self.requests[key].append(current_time)
        return True


class APIKeyValidator:
    """Validates API keys for authentication."""

    def __init__(self, api_keys: Optional[list[str]] = None):
        """Initialize with list of valid API keys (hashed)."""
        self.api_keys: set[str] = set()
        if api_keys:
            for key in api_keys:
                self.api_keys.add(self._hash_key(key))

    @staticmethod
    def _hash_key(key: str) -> str:
        """Hash an API key for secure storage."""
        return hashlib.sha256(key.encode()).hexdigest()

    def validate(self, api_key: str) -> bool:
        """Validate an API key.

        Args:
            api_key: The API key to validate.

        Returns:
            True if valid, False otherwise.
        """
        if not self.api_keys:
            # If no keys configured, allow all (development mode)
            return True
        return self._hash_key(api_key) in self.api_keys

    @classmethod
    def generate_key(cls) -> str:
        """Generate a secure random API key."""
        return secrets.token_urlsafe(32)


# Global instances
rate_limiter = RateLimiter(requests_per_minute=settings.rate_limit_per_minute)
api_key_validator = APIKeyValidator(
    [settings.api_key] if settings.api_key_enabled and settings.api_key else None
)


async def verify_api_key(x_api_key: str = Header(None)) -> str:
    """Dependency to verify API key from request header.

    Args:
        x_api_key: API key from X-API-Key header.

    Returns:
        The validated API key.

    Raises:
        HTTPException: If API key is missing or invalid.
    """
    if not settings.api_key_enabled:
        return "disabled"

    if not x_api_key:
        logger.warning("Request missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
        )

    if not api_key_validator.validate(x_api_key):
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return x_api_key


async def check_rate_limit(request: Request) -> None:
    """Dependency to enforce rate limiting per IP.

    Args:
        request: The incoming request.

    Raises:
        HTTPException: If rate limit is exceeded.
    """
    if not settings.rate_limit_enabled:
        return

    client_ip = request.client.host if request.client else "unknown"

    if not rate_limiter.is_allowed(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )


def validate_file_upload(filename: str, file_size: int) -> None:
    """Validate uploaded file.

    Args:
        filename: Name of the file.
        file_size: Size of the file in bytes.

    Raises:
        SecurityError: If file validation fails.
    """
    # Check file extension
    allowed_extensions = {".pdf"}
    file_ext = filename[filename.rfind(".") :].lower() if "." in filename else ""

    if file_ext not in allowed_extensions:
        raise SecurityError(f"File type not allowed: {file_ext}")

    # Check file size
    max_size = settings.max_file_size_mb * 1024 * 1024
    if file_size > max_size:
        raise SecurityError(f"File too large: {file_size} bytes (max: {max_size})")

    # Check for path traversal in filename
    if ".." in filename or "/" in filename or "\\" in filename:
        raise SecurityError("Invalid filename: path traversal detected")


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """Sanitize user input text.

    Args:
        text: Input text to sanitize.
        max_length: Maximum allowed length.

    Returns:
        Sanitized text.

    Raises:
        SecurityError: If input is invalid.
    """
    if not text or not isinstance(text, str):
        raise SecurityError("Input must be a non-empty string")

    if len(text) > max_length:
        raise SecurityError(f"Input too long: {len(text)} chars (max: {max_length})")

    # Remove null bytes and other control characters
    sanitized = "".join(char for char in text if char.isprintable() or char.isspace())

    return sanitized.strip()
