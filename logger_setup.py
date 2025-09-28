#!/usr/bin/env python3
"""
Logger Setup Utility
Sets up consistent logging across Pi Player components with rotation
"""

import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from typing import Optional

from config import config


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: str = None,
    console: bool = True,
    max_bytes: int = None,
    backup_count: int = None
) -> logging.Logger:
    """
    Set up a logger with file rotation and optionally console output
    
    Args:
        name: Logger name
        log_file: Log file path (relative to logs dir or absolute)
        level: Log level (defaults to config.LOG_LEVEL)
        console: Whether to log to console
        max_bytes: Max bytes per log file (defaults to config.LOG_MAX_BYTES)
        backup_count: Number of backup files (defaults to config.LOG_BACKUP_COUNT)
    
    Returns:
        Logger instance
    """
    if level is None:
        level = config.LOG_LEVEL
    
    if max_bytes is None:
        max_bytes = config.LOG_MAX_BYTES
    
    if backup_count is None:
        backup_count = config.LOG_BACKUP_COUNT
    
    # Get or create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    
    # Remove existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Set formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Add file handler if specified
    if log_file:
        # Get absolute path if relative path provided
        if not os.path.isabs(log_file):
            log_file = str(config.get_log_path(log_file))
        
        # Create parent directory if needed
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Add rotating file handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


# Set up root logger
def setup_root_logger():
    """Set up the root logger with basic configuration"""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


# Function for centralizing all component loggers
def get_component_logger(component_name: str, console: bool = True) -> logging.Logger:
    """Get a pre-configured component logger with file rotation"""
    return setup_logger(
        name=component_name,
        log_file=f"{component_name}.log",
        level=config.LOG_LEVEL,
        console=console,
        max_bytes=config.LOG_MAX_BYTES,
        backup_count=config.LOG_BACKUP_COUNT
    )


# Example usage
if __name__ == "__main__":
    # Test logger setup
    logger = get_component_logger("logger_test")
    logger.info("Logger test message")
    logger.warning("This is a warning")
    logger.error("This is an error")
    
    print(f"Log file created at: {config.get_log_path('logger_test.log')}")