"""Centralized logging factory for AgenticOs."""

import logging
import os
import sys

from kernel.settings import load_cfg

# Reconfigure standard streams to UTF-8 on Windows to prevent UnicodeEncodeErrors
if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

_CACHED_LOG_LEVEL = None

def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger with standard formatting.

    Args:
        name: The name of the logger to construct or retrieve.

    Returns:
        logging.Logger: A configured, standard-compliant logger.
    """
    global _CACHED_LOG_LEVEL
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    if _CACHED_LOG_LEVEL is None:
        try:
            cfg = load_cfg()
            level_str = cfg.get("log_level", "INFO").upper()
            _CACHED_LOG_LEVEL = getattr(logging, level_str, logging.INFO)
        except Exception:
            _CACHED_LOG_LEVEL = logging.INFO

    level = _CACHED_LOG_LEVEL
    logger.setLevel(level)
    logger.propagate = False
    
    # Console Handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    console_formatter = logging.Formatter("%(message)s")
    ch.setFormatter(console_formatter)
    logger.addHandler(ch)
    
    # File Handler
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(base_dir, "data", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "agenticos.log")
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        file_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        fh.setFormatter(file_formatter)
        logger.addHandler(fh)
    except Exception:
        # Prevent logging configuration failure from aborting execution
        pass

    return logger
