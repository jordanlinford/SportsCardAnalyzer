import streamlit as st
import os
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def setup_page_config():
    """Set up the Streamlit page configuration."""
    try:
        st.set_page_config(
            page_title="Sports Card Analyzer",
            page_icon="🏈",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Add custom CSS
        st.markdown("""
            <style>
                .main {
                    padding: 2rem;
                }
                .stButton>button {
                    width: 100%;
                }
                .stTextInput>div>div>input {
                    background-color: #f0f2f6;
                }
                .stSelectbox>div>div>select {
                    background-color: #f0f2f6;
                }
                .stNumberInput>div>div>input {
                    background-color: #f0f2f6;
                }
                .stDateInput>div>div>input {
                    background-color: #f0f2f6;
                }
                .stTextArea>div>div>textarea {
                    background-color: #f0f2f6;
                }
            </style>
        """, unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error setting up page config: {str(e)}")
        
def get_user_id() -> str:
    """
    Get the current user's ID from session state.
    
    Returns:
        str: User ID or empty string if not logged in
    """
    try:
        return st.session_state.get('user', {}).get('uid', '')
    except Exception as e:
        logger.error(f"Error getting user ID: {str(e)}")
        return ''
        
def format_currency(amount: float) -> str:
    """
    Format a number as currency.
    
    Args:
        amount (float): Amount to format
        
    Returns:
        str: Formatted currency string
    """
    try:
        return f"${amount:,.2f}"
    except Exception as e:
        logger.error(f"Error formatting currency: {str(e)}")
        return '$0.00'
        
def format_date(date_str: str) -> str:
    """
    Format a date string.
    
    Args:
        date_str (str): Date string to format
        
    Returns:
        str: Formatted date string
    """
    try:
        from datetime import datetime
        date = datetime.strptime(date_str, '%Y-%m-%d')
        return date.strftime('%B %d, %Y')
    except Exception as e:
        logger.error(f"Error formatting date: {str(e)}")
        return date_str
        
def validate_card_data(data: Dict[str, Any]) -> bool:
    """
    Validate card data.
    
    Args:
        data (Dict[str, Any]): Card data to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        required_fields = ['player_name', 'year', 'card_set', 'card_number']
        for field in required_fields:
            if not data.get(field):
                return False
                
        # Validate year
        try:
            year = int(data['year'])
            if year < 1900 or year > datetime.now().year:
                return False
        except ValueError:
            return False
            
        # Validate value if present
        if 'value' in data and data['value'] is not None:
            try:
                value = float(data['value'])
                if value < 0:
                    return False
            except ValueError:
                return False
                
        return True
    except Exception as e:
        logger.error(f"Error validating card data: {str(e)}")
        return False
        
def clear_cache():
    """Clear Streamlit's cache."""
    try:
        st.cache_data.clear()
        st.cache_resource.clear()
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        
def show_error(message: str):
    """
    Display an error message.
    
    Args:
        message (str): Error message to display
    """
    try:
        st.error(message)
    except Exception as e:
        logger.error(f"Error showing error message: {str(e)}")
        
def show_success(message: str):
    """
    Display a success message.
    
    Args:
        message (str): Success message to display
    """
    try:
        st.success(message)
    except Exception as e:
        logger.error(f"Error showing success message: {str(e)}")
        
def show_warning(message: str):
    """
    Display a warning message.
    
    Args:
        message (str): Warning message to display
    """
    try:
        st.warning(message)
    except Exception as e:
        logger.error(f"Error showing warning message: {str(e)}")
        
def show_info(message: str):
    """
    Display an info message.
    
    Args:
        message (str): Info message to display
    """
    try:
        st.info(message)
    except Exception as e:
        logger.error(f"Error showing info message: {str(e)}") 