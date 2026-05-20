"""Centralized logging factory for AgenticOs."""

import logging
import os
import sys

from core.runtime_config import load_config

def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger with standard formatting.

    Args:
        name: The name of the logger to construct or retrieve.

    Returns:
        logging.Logger: A configured, standard-compliant logger.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    try:
        cfg = load_config()
        level_str = cfg.get("log_level", "INFO").upper()
        level = getattr(logging, level_str, logging.INFO)
    except Exception:
        level = logging.INFO

    logger.setLevel(level)
    
    # Console Handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # File Handler
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(base_dir, "data", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "agenticos.log")
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except Exception:
        # Prevent logging configuration failure from aborting execution
        pass

    return logger
