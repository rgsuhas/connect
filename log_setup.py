#!/usr/bin/env python3
"""
Comprehensive Logging Setup for Pi Player
Standardized logging with JSON format, rotation, and syslog integration
"""

import json
import logging
import logging.handlers
import sys
import syslog
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Create base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add process info
        log_entry["process"] = {
            "pid": record.process,
            "thread": record.thread,
            "thread_name": record.threadName
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None
            }
        
        # Add custom fields if present
        if hasattr(record, 'custom_fields'):
            log_entry["custom"] = record.custom_fields
            
        return json.dumps(log_entry, default=str)

class SyslogHandler(logging.Handler):
    """Custom handler to send critical events to syslog"""
    
    def __init__(self):
        super().__init__()
        self.setLevel(logging.WARNING)  # Only send warnings and above to syslog
        
    def emit(self, record):
        try:
            # Map Python logging levels to syslog priorities
            level_map = {
                logging.DEBUG: syslog.LOG_DEBUG,
                logging.INFO: syslog.LOG_INFO, 
                logging.WARNING: syslog.LOG_WARNING,
                logging.ERROR: syslog.LOG_ERR,
                logging.CRITICAL: syslog.LOG_CRIT
            }
            
            priority = level_map.get(record.levelno, syslog.LOG_INFO)
            message = f"pi-player[{record.name}]: {record.getMessage()}"
            
            syslog.openlog("pi-player", syslog.LOG_PID, syslog.LOG_USER)
            syslog.syslog(priority, message)
            syslog.closelog()
            
        except Exception:
            # Don't let syslog errors break the application
            pass

def setup_logging(
    component_name: str,
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    enable_console: bool = True,
    enable_syslog: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 14,  # Keep 14 days
    custom_fields: Optional[Dict[str, Any]] = None
) -> logging.Logger:
    """
    Set up comprehensive logging for a Pi Player component
    
    Args:
        component_name: Name of the component (used for logger name and log file)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files (defaults to ./logs)
        enable_console: Whether to log to console/stdout
        enable_syslog: Whether to send critical events to syslog
        max_bytes: Maximum size per log file before rotation
        backup_count: Number of backup log files to keep
        custom_fields: Additional fields to include in every log entry
        
    Returns:
        Configured logger instance
    """
    
    # Set log directory
    if log_dir is None:
        log_dir = Path.cwd() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(component_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create JSON formatter
    json_formatter = JsonFormatter()
    
    # File handler with rotation
    log_file = log_dir / f"{component_name}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)
    
    # Console handler (human-readable format)
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # Syslog handler for critical events
    if enable_syslog:
        try:
            syslog_handler = SyslogHandler()
            logger.addHandler(syslog_handler)
        except Exception as e:
            # Syslog might not be available in all environments
            logger.warning(f"Could not set up syslog handler: {e}")
    
    # Add custom fields to all log entries
    if custom_fields:
        old_factory = logging.getLogRecordFactory()
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.custom_fields = custom_fields
            return record
        logging.setLogRecordFactory(record_factory)
    
    # Log startup message
    logger.info(f"Logging initialized for {component_name}", extra={
        "custom_fields": {
            "event_type": "logging_initialized",
            "log_file": str(log_file),
            "log_level": log_level,
            "max_bytes": max_bytes,
            "backup_count": backup_count
        }
    })
    
    return logger

def get_system_info() -> Dict[str, Any]:
    """Get system information for logging context"""
    import platform
    import psutil
    import os
    
    try:
        return {
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "disk_usage": psutil.disk_usage('/').total,
            "user": os.getenv('USER', 'unknown'),
            "working_directory": str(Path.cwd())
        }
    except Exception:
        return {"error": "Could not gather system info"}

def log_system_startup(logger: logging.Logger):
    """Log system startup information"""
    system_info = get_system_info()
    logger.info("Pi Player system startup", extra={
        "custom_fields": {
            "event_type": "system_startup",
            "system_info": system_info
        }
    })

# Convenience function for quick logger setup
def get_logger(component_name: str, **kwargs) -> logging.Logger:
    """Quick logger setup with default settings"""
    return setup_logging(component_name, **kwargs)

if __name__ == "__main__":
    # Test the logging setup
    print("🔍 Testing Pi Player Logging Setup")
    print("=" * 50)
    
    # Test logger
    test_logger = setup_logging("test", log_level="DEBUG")
    
    # Test different log levels
    test_logger.debug("This is a debug message")
    test_logger.info("This is an info message")
    test_logger.warning("This is a warning message")
    test_logger.error("This is an error message")
    
    # Test with custom fields
    test_logger.info("Custom fields test", extra={
        "custom_fields": {
            "event_type": "test",
            "test_data": {"key": "value", "count": 123}
        }
    })
    
    # Test exception logging
    try:
        raise ValueError("Test exception for logging")
    except Exception as e:
        test_logger.exception("Exception occurred during test")
    
    print(f"\n✅ Test complete! Check logs/test.log for JSON output")
    
    # Log system startup
    log_system_startup(test_logger)