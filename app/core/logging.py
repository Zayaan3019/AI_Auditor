from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings


def configure_logging(level: str = None) -> None:
    """Configure Loguru logger for the application.

    Args:
        level: Minimum logging level. If None, uses settings.log_level.
    """
    level = level or settings.log_level

    # Remove default handler
    logger.remove()

    # Console handler with colors
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
        level=level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # File handler for production
    if settings.is_production():
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # Rotating log file
        logger.add(
            log_dir / "ai_auditor_{time:YYYY-MM-DD}.log",
            rotation="00:00",  # New file at midnight
            retention="30 days",  # Keep for 30 days
            compression="zip",  # Compress old logs
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            backtrace=True,
            diagnose=False,  # Don't include sensitive info in production
        )

        # Error log file
        logger.add(
            log_dir / "errors_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="90 days",
            compression="zip",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            backtrace=True,
            diagnose=True,
        )

    logger.info(f"Logging configured at {level} level")


# Configure on module import
configure_logging()
