import logging
import sys

from config import settings


def get_logger(name: str) -> logging.Logger:
    """
    Configures and returns a logger with a standard format.
    The logging level is read from application settings (LOG_LEVEL env var).
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
        logger.setLevel(log_level)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
