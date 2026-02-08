import logging
import logging.handlers
from pathlib import Path
from app.core.config_settings import settings


def setup_logging():
    """Configure logging for the application"""

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))

    # File handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "payment_service.log",
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Avoid duplicate logs if setup_logging() is called more than once
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

    # --- Silence watchfiles (uvicorn reload) spam ---
    watchfiles_logger = logging.getLogger("watchfiles")
    watchfiles_main_logger = logging.getLogger("watchfiles.main")
    watchfiles_logger.setLevel(logging.WARNING)
    watchfiles_main_logger.setLevel(logging.WARNING)
    watchfiles_logger.propagate = False
    watchfiles_main_logger.propagate = False

    # Silence Stripe logging in development
    stripe_logger = logging.getLogger("stripe")
    stripe_logger.setLevel(logging.WARNING)

    return root_logger
