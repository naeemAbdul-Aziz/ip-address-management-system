import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Ensure logs directory exists
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Log file path
LOG_FILE = os.path.join(LOG_DIR, f"ipam_app_{datetime.now().strftime('%Y-%m-%d')}.log")

# Create custom logger
logger = logging.getLogger("ipam_core")
logger.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s:%(lineno)d | %(message)s"
)

# File Handler (Rotating)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Console Handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# Add handlers
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def log_operation(operation: str, status: str, details: dict = None):
    """Structured logging for business operations."""
    msg = f"OP: {operation} | STATUS: {status}"
    if details:
        msg += f" | DETAILS: {details}"
    
    if status == "success":
        logger.info(msg)
    else:
        logger.warning(msg)

def log_database_operation(op_type: str, model: str, status: str, details: dict = None, count: int = None):
    """Structured logging for DB operations."""
    msg = f"DB: {op_type} {model} | STATUS: {status}"
    if count is not None:
        msg += f" | COUNT: {count}"
    if details:
        msg += f" | DETAILS: {details}"
    logger.info(msg)

def log_request(method: str, path: str, status_code: int, duration_ms: float):
    """Log HTTP request details."""
    logger.info(f"REQ: {method} {path} | STATUS: {status_code} | DURATION: {duration_ms:.2f}ms")

def log_error(error: Exception, context: str, details: dict = None):
    """Standardized error logging."""
    msg = f"ERROR in {context}: {str(error)}"
    if details:
        msg += f" | DETAILS: {details}"
    logger.error(msg, exc_info=True)
