"""
Error handling module for the Sports Card Analyzer application.
This module provides consistent error handling across the application.
"""

from config.environment import Environment
import logging
import traceback
from functools import wraps
import time
import functools
from typing import Callable, Any
import streamlit as st

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

class DisplayError(Exception):
    """Raised when display operations fail"""
    pass

def handle_error(func: Callable) -> Callable:
    """
    Decorator for consistent error handling
    
    Args:
        func: The function to wrap with error handling
        
    Returns:
        The wrapped function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {str(e)}")
            st.warning(str(e))
            return None
        except DatabaseError as e:
            logger.error(f"Database error in {func.__name__}: {str(e)}")
            st.error(f"Database error: {str(e)}")
            return None
        except AuthenticationError as e:
            logger.error(f"Authentication error in {func.__name__}: {str(e)}")
            st.error(f"Authentication error: {str(e)}")
            return None
        except DisplayError as e:
            logger.error(f"Display error in {func.__name__}: {str(e)}")
            st.error(f"Display error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            st.error(f"An unexpected error occurred: {str(e)}")
            return None
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

def log_error(error: Exception, context: str = None) -> None:
    """
    Log an error with context
    
    Args:
        error: The exception to log
        context: Additional context about the error
    """
    error_msg = str(error)
    if context:
        error_msg = f"{context}: {error_msg}"
    
    logger.error(error_msg)
    st.error(error_msg)

def display_error_message(message: str, error_type: str = "error") -> None:
    """
    Display an error message to the user
    
    Args:
        message: The error message to display
        error_type: Type of error (error, warning, info)
    """
    if error_type == "error":
        st.error(message)
    elif error_type == "warning":
        st.warning(message)
    elif error_type == "info":
        st.info(message)
    else:
        st.error(message)
    
    logger.error(f"Displayed {error_type} message: {message}")

def validate_input(data: Any, required_fields: list = None) -> bool:
    """
    Validate input data
    
    Args:
        data: The data to validate
        required_fields: List of required fields
        
    Returns:
        bool: True if validation passes
        
    Raises:
        ValidationError: If validation fails
    """
    if data is None:
        raise ValidationError("Input data cannot be None")
    
    if required_fields:
        if not isinstance(data, dict):
            raise ValidationError("Input data must be a dictionary")
        
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
    
    return True 