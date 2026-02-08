"""
Logger Configuration
"""

__author__ = "Mohammad Saifan"

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.core.config_settings import settings


def setup_logging(log_level: str = "INFO", log_dir: str = "logs"):
    """
    Setup logger object with console and file handlers.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
    
    Returns:
        Logger object
    """
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Formatters
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(formatter)

    # Detect environment
    environment = settings.ENVIRONMENT.lower()

    # File handlers
    if environment == "development":
        # Simple FileHandler to avoid file locking during reloads
        file_handler = logging.FileHandler(log_path / "app.log", encoding="utf-8")
        error_handler = logging.FileHandler(log_path / "error.log", encoding="utf-8")
    else:
        # RotatingFileHandler for production
        file_handler = RotatingFileHandler(
            filename=log_path / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=50,
            encoding="utf-8"
        )
        error_handler = RotatingFileHandler(
            filename=log_path / "error.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=50,
            encoding="utf-8"
        )

    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()  # Remove existing handlers

    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

    # Reduce noise from dependencies
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logging.info(f"Logging initialized - Level: {log_level} - Environment: {environment}")


class Logger:
    """Add logging capability to any class inheriting from this."""

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        return logging.getLogger(name)