import logging
import os
import tempfile
from datetime import datetime
from typing import Generator, Any
from unittest.mock import patch

import pytest

from joft.logger import configure_logger


@pytest.fixture
def temp_log_dir() -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_configure_logger_stdout(caplog: Any) -> None:
    """Test if logger can be configured for stdout and logs messages correctly."""
    config: dict[str, dict[str, Any]] = {"stdout": {"log_level": "INFO"}}

    configure_logger(config)
    logger = logging.getLogger("joft")

    test_message = "Test stdout message"
    with caplog.at_level(logging.INFO):
        logger.info(test_message)

    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert test_message in caplog.text


def test_configure_logger_file(temp_log_dir: str) -> None:
    """Test if logger can be configured for file logging and logs messages into a file."""
    config: dict[str, dict[str, Any]] = {
        "file": {"log_level": "INFO", "log_dir": temp_log_dir}
    }

    configure_logger(config)
    logger = logging.getLogger("joft")

    test_message = "Test file message"
    logger.info(test_message)

    # Find the log file
    log_files = [f for f in os.listdir(temp_log_dir) if f.startswith("joft_")]
    assert len(log_files) == 1

    log_path = os.path.join(temp_log_dir, log_files[0])
    with open(log_path, "r") as f:
        log_content = f.read()
        assert test_message in log_content


def test_configure_logger_both_handlers(temp_log_dir: str, caplog: Any) -> None:
    """Test if logger can be configured for both stdout and file logging."""
    config: dict[str, dict[str, Any]] = {
        "stdout": {"log_level": "INFO"},
        "file": {"log_level": "INFO", "log_dir": temp_log_dir},
    }

    configure_logger(config)
    logger = logging.getLogger("joft")

    test_message = "Test both handlers message"
    logger.info(test_message)

    # Check stdout
    assert test_message in caplog.text

    # Check file
    log_files = [f for f in os.listdir(temp_log_dir) if f.startswith("joft_")]
    assert len(log_files) == 1

    log_path = os.path.join(temp_log_dir, log_files[0])
    with open(log_path, "r") as f:
        log_content = f.read()
        assert test_message in log_content


def test_configure_logger_different_levels(temp_log_dir: str, caplog: Any) -> None:
    """Test if logger handles different log levels correctly for both handlers."""
    config: dict[str, dict[str, Any]] = {
        "stdout": {"log_level": "WARNING"},
        "file": {"log_level": "DEBUG", "log_dir": temp_log_dir},
    }

    configure_logger(config)
    logger = logging.getLogger("joft")

    debug_msg = "Debug message"
    info_msg = "Info message"
    warning_msg = "Warning message"

    with caplog.at_level(logging.WARNING):
        logger.debug(debug_msg)
        logger.info(info_msg)
        logger.warning(warning_msg)

    # Check stdout (should only contain warning)
    assert debug_msg not in caplog.text
    assert info_msg not in caplog.text
    assert warning_msg in caplog.text

    # Check file (should contain all messages)
    log_files = [f for f in os.listdir(temp_log_dir) if f.startswith("joft_")]
    log_path = os.path.join(temp_log_dir, log_files[0])
    with open(log_path, "r") as f:
        log_content = f.read()
        assert debug_msg in log_content
        assert info_msg in log_content
        assert warning_msg in log_content


def test_configure_logger_missing_log_dir() -> None:
    """Test if logger uses current working directory when log_dir is not specified."""
    config: dict[str, dict[str, Any]] = {"file": {"log_level": "INFO"}}

    configure_logger(config)
    logger = logging.getLogger("joft")

    test_message = "Test message"
    logger.info(test_message)

    # Find the log file in current directory
    log_files = [f for f in os.listdir() if f.startswith("joft_")]
    assert len(log_files) == 1

    log_path = os.path.join(os.getcwd(), log_files[0])
    with open(log_path, "r") as f:
        log_content = f.read()
        assert test_message in log_content

    # Cleanup the log file
    os.remove(log_path)


def test_configure_logger_timestamp_format(temp_log_dir: str) -> None:
    """Test if logger creates log files with correct timestamp format."""
    config: dict[str, dict[str, Any]] = {
        "file": {"log_level": "INFO", "log_dir": temp_log_dir}
    }

    current_time = datetime(2024, 3, 15, 10, 30, 45)
    expected_timestamp = current_time.strftime("%Y%m%d_%H%M%S")

    with patch("joft.logger.datetime") as mock_datetime:
        mock_datetime.now.return_value = current_time
        configure_logger(config)
        logger = logging.getLogger("joft")
        logger.info("Test message")

    log_files = [f for f in os.listdir(temp_log_dir) if f.startswith("joft_")]
    assert len(log_files) == 1
    assert f"joft_{expected_timestamp}.log" in log_files


@pytest.fixture(autouse=True)
def cleanup_handlers() -> Generator[None, None, None]:
    """Cleanup fixture to remove handlers after each test."""
    yield
    logger = logging.getLogger("joft")
    logger.handlers.clear()
