from datetime import datetime
import logging
import os
from typing import Dict, Any

if os.getenv("JOFT_DEBUG"):
    log_level = logging.DEBUG
else:
    log_level = logging.WARNING

logger = logging.getLogger("joft")
logger.setLevel(log_level)


def configure_logger(logging_config: Dict[str, Any]) -> None:
    """
    Configure the logger for the application according to the logging configuration.

    Args:
        logging_config: The logging configuration.
    """

    logger = logging.getLogger("joft")
    # Clear existing handlers
    logger.handlers.clear()

    # Track minimum level across all handlers
    min_level = logging.CRITICAL

    if "stdout" in logging_config:
        log_level = getattr(logging, logging_config["stdout"]["log_level"])
        min_level = min(min_level, log_level)
        stdout_handler = logging.StreamHandler()
        stdout_handler.setLevel(log_level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)

    if "file" in logging_config:
        log_level = getattr(logging, logging_config["file"]["log_level"])
        min_level = min(min_level, log_level)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Use current working directory if log_dir is not specified
        log_dir = logging_config["file"].get("log_dir", os.getcwd())
        log_file = os.path.join(log_dir, f"joft_{timestamp}.log")

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Set logger to minimum level from handlers
    logger.setLevel(min_level)
