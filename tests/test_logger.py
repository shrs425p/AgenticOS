import logging
import sys
from unittest import mock

import pytest

from core.logger import get_logger

@pytest.fixture(autouse=True)
def reset_cached_log_level():
    """Reset the cached log level before and after each test."""
    import core.logger
    core.logger._CACHED_LOG_LEVEL = None

    # We also need to clear handlers so subsequent get_logger calls actually add handlers again
    logger = logging.getLogger("test_stream_handler")
    logger.handlers.clear()

    logger = logging.getLogger("test_file_handler")
    logger.handlers.clear()

    yield
    core.logger._CACHED_LOG_LEVEL = None

def test_get_logger_returns_standard_logger():
    """Verify get_logger returns a standard logger instance."""
    logger = get_logger("test_returns_standard")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_returns_standard"

def test_logger_propagate_is_false():
    """Verify the logger is configured with propagate = False."""
    logger = get_logger("test_propagate")
    assert logger.propagate is False

def test_get_logger_caches_instance():
    """Verify calling get_logger twice with the same name returns the same instance and does not add duplicate handlers."""
    logger1 = get_logger("test_cache")
    logger2 = get_logger("test_cache")
    assert logger1 is logger2

    # It should have a StreamHandler and a FileHandler (so 2 handlers in total)
    # We just ensure the number of handlers doesn't grow on the second call.
    assert len(logger1.handlers) == len(logger2.handlers)

@mock.patch("core.logger.load_config")
def test_fallback_logging_info_on_exception(mock_load_config):
    """Verify that if load_config raises an Exception, _CACHED_LOG_LEVEL falls back to INFO."""
    mock_load_config.side_effect = Exception("Config error")

    logger = get_logger("test_fallback")

    import core.logger
    assert core.logger._CACHED_LOG_LEVEL == logging.INFO
    assert logger.level == logging.INFO

def test_stream_handler_is_added():
    """Verify that a StreamHandler is added to the logger."""
    logger = get_logger("test_stream_handler")

    # The logger should have a StreamHandler pointing to sys.stdout
    has_stream_handler = any(isinstance(h, logging.StreamHandler) and h.stream == sys.stdout for h in logger.handlers)
    assert has_stream_handler

@mock.patch("core.logger.logging.FileHandler")
@mock.patch("core.logger.os.makedirs")
def test_file_handler_is_added(mock_makedirs, mock_file_handler_class):
    """Verify that a FileHandler is added to the logger."""
    logger = get_logger("test_file_handler")

    # makedirs should be called to ensure log directory exists
    mock_makedirs.assert_called_once()

    # FileHandler should be instantiated
    mock_file_handler_class.assert_called_once()

    # The returned mock should be in the logger's handlers
    assert mock_file_handler_class.return_value in logger.handlers
