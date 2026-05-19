import pytest
from core.logger import get_logger

def test_logger(tmp_path):
    from unittest.mock import patch
    with patch("os.path.dirname", return_value=str(tmp_path)):
        logger = get_logger("test_logger")
        assert logger.name == "test_logger"
        logger.info("info message")

        # Should not add handlers twice
        logger2 = get_logger("test_logger")
        assert len(logger2.handlers) == 2

def test_get_logger_exception():
    from unittest.mock import patch
    with patch("os.makedirs", side_effect=Exception("Failed")):
        logger = get_logger("test_logger_err")
        assert logger.name == "test_logger_err"
        # Only console handler since file handler failed
        assert len(logger.handlers) == 1
