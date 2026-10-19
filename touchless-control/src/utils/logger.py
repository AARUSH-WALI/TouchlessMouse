"""Touchless Computer Control System - Logging Setup."""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler


def setup_logger(name="touchless", log_file=None, level="INFO", max_bytes=5242880, backup_count=3):
    """
    Configures and returns a thread-safe rotating file and console logger.
    """
    logger = logging.getLogger(name)
    log_level = getattr(logging, str(level).upper(), logging.INFO)
    logger.setLevel(log_level)

    # Avoid duplicate handlers if setup_logger is called multiple times
    if logger.hasHandlers():
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - [%(threadName)s] - %(levelname)s - %(name)s - %(message)s"
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)

    # File Handler
    if log_file:
        try:
            log_dir = os.path.dirname(os.path.abspath(log_file))
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Failed to create file log handler at {log_file}: {e}")

    return logger
