"""
Error handling module for the Sports Card Analyzer application.
This module provides consistent error handling across the application.
"""

from config.environment import Environment
import logging
import traceback
from functools import wraps
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AppError(Exception):
    """Base exception class for application errors"""
    def __init__(self, message, error_code=None, details=None):
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)

class DatabaseError(AppError):
    """Database-related errors"""
    pass

class AuthenticationError(AppError):
    """Authentication-related errors"""
    pass

class ValidationError(AppError):
    """Data validation errors"""
    pass

def handle_error(func):
    """
    Decorator for consistent error handling
    
    Args:
        func: Function to wrap with error handling
        
    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AppError as e:
            # Log application-specific errors
            logger.error(f"Application error: {e.message}")
            if Environment.DEBUG_MODE:
                logger.error(f"Error details: {e.details}")
            raise
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error: {str(e)}")
            if Environment.DEBUG_MODE:
                logger.error(f"Traceback: {traceback.format_exc()}")
            raise AppError(
                "An unexpected error occurred",
                error_code="UNEXPECTED_ERROR",
                details=str(e)
            )
    return wrapper

def retry_on_error(max_retries=None, delay=1):
    """
    Decorator for retrying operations on failure
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        Wrapped function with retry logic
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = max_retries or Environment.ERROR_HANDLING['max_retries']
            last_error = None
            
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                        time.sleep(delay)
                    else:
                        logger.error(f"All {retries} attempts failed")
                        raise last_error
        return wrapper
    return decorator

def log_error(error, context=None):
    """
    Log an error with context
    
    Args:
        error: The error to log
        context: Additional context information
    """
    error_message = str(error)
    if context:
        error_message += f" | Context: {context}"
    
    logger.error(error_message)
    if Environment.DEBUG_MODE:
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    return {
        'success': False,
        'message': error_message,
        'error_code': getattr(error, 'error_code', 'UNKNOWN_ERROR'),
        'details': getattr(error, 'details', None) if Environment.DEBUG_MODE else None
    } 