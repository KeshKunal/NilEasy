"""
app/core/logging.py

Purpose: Logging configuration

- Standardizes log format
- Controls log levels
- Enables observability in production
- Structured logging for easy parsing
- Context tracking (user_id, session_id, state)
"""

import logging
import sys
import json
from datetime import datetime
from typing import Optional, Dict, Any
from app.core.config import settings


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured JSON logging in production.
    Makes logs easily parseable by monitoring tools.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra context if available
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id
        if hasattr(record, "state"):
            log_data["state"] = record.state
        if hasattr(record, "gstin"):
            log_data["gstin"] = record.gstin
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class DevelopmentFormatter(logging.Formatter):
    """
    Human-readable formatter for development environment.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        # Color codes for different log levels
        colors = {
            "DEBUG": "\033[36m",      # Cyan
            "INFO": "\033[32m",       # Green
            "WARNING": "\033[33m",    # Yellow
            "ERROR": "\033[31m",      # Red
            "CRITICAL": "\033[35m",   # Magenta
        }
        reset = "\033[0m"
        
        color = colors.get(record.levelname, reset)
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        
        # Base message
        message = f"{color}[{timestamp}] {record.levelname:<8}{reset} {record.name}: {record.getMessage()}"
        
        # Add context if available
        context_parts = []
        if hasattr(record, "user_id"):
            context_parts.append(f"user={record.user_id}")
        if hasattr(record, "state"):
            context_parts.append(f"state={record.state}")
        
        if context_parts:
            message += f" [{', '.join(context_parts)}]"
        
        # Add exception if present
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)
        
        return message


def setup_logging():
    """
    Configures application-wide logging with appropriate formatters.
    Uses JSON format in production, human-readable in development.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Choose formatter based on environment
    if settings.is_production:
        formatter = StructuredFormatter()
    else:
        formatter = DevelopmentFormatter()
    
    handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # Create app logger
    logger = logging.getLogger("nileasy")
    logger.info(
        f"Logging configured",
        extra={
            "environment": settings.ENVIRONMENT,
            "log_level": settings.LOG_LEVEL,
            "debug_mode": settings.DEBUG
        }
    )
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(f"nileasy.{name}")


class LogContext:
    """
    Context manager for adding structured context to logs.
    
    Usage:
        with LogContext(user_id="123", state="ASK_GSTIN"):
            logger.info("Processing GSTIN input")
    """
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self._old_factory = None
    
    def __enter__(self):
        self._old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self._old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self._old_factory)
