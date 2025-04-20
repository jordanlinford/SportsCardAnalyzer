"""
Environment configuration for the Sports Card Analyzer application.
This file manages environment-specific settings and configurations.
"""

import os
from typing import Dict, Any
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class Environment:
    """Environment configuration class"""
    
    # Application Settings
    APP_NAME = "Sports Card Analyzer"
    APP_VERSION = "1.0.0"
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
    
    # Firebase Settings
    FIREBASE_CONFIG = {
        'apiKey': os.getenv('FIREBASE_API_KEY'),
        'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN'),
        'projectId': os.getenv('FIREBASE_PROJECT_ID'),
        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET'),
        'messagingSenderId': os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
        'appId': os.getenv('FIREBASE_APP_ID')
    }
    
    # Database Settings
    DATABASE_URL = os.getenv('DATABASE_URL')
    DATABASE_TIMEOUT = int(os.getenv('DATABASE_TIMEOUT', '30'))
    
    # UI Settings
    UI_SETTINGS = {
        'cards_per_row': int(os.getenv('CARDS_PER_ROW', '5')),
        'max_image_size': int(os.getenv('MAX_IMAGE_SIZE', '1024')),
        'default_currency': os.getenv('DEFAULT_CURRENCY', 'USD'),
        'date_format': os.getenv('DATE_FORMAT', '%Y-%m-%d')
    }
    
    # Cache Settings
    CACHE_SETTINGS = {
        'enabled': os.getenv('CACHE_ENABLED', 'True').lower() == 'true',
        'ttl': int(os.getenv('CACHE_TTL', '3600')),
        'max_size': int(os.getenv('CACHE_MAX_SIZE', '1000'))
    }
    
    # Logging Settings
    LOGGING_CONFIG = {
        'level': os.getenv('LOG_LEVEL', 'INFO'),
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file': os.getenv('LOG_FILE', 'app.log')
    }
    
    # Error Handling
    ERROR_HANDLING = {
        'max_retries': 3,
        'retry_delay': 1,
        'show_detailed_errors': DEBUG_MODE
    }
    
    @classmethod
    def is_production(cls):
        """Check if running in production environment"""
        return not cls.DEBUG_MODE
    
    @classmethod
    def get_setting(cls, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        try:
            # Check environment variables first
            value = os.getenv(key)
            if value is not None:
                return value
            
            # Check UI settings
            if key in cls.UI_SETTINGS:
                return cls.UI_SETTINGS[key]
            
            # Check cache settings
            if key in cls.CACHE_SETTINGS:
                return cls.CACHE_SETTINGS[key]
            
            # Check Firebase config
            if key in cls.FIREBASE_CONFIG:
                return cls.FIREBASE_CONFIG[key]
            
            return default
        except Exception as e:
            logger.error(f"Error getting setting {key}: {str(e)}")
            return default
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate the configuration"""
        try:
            # Check required Firebase settings
            required_firebase = ['apiKey', 'authDomain', 'projectId']
            for key in required_firebase:
                if not cls.FIREBASE_CONFIG.get(key):
                    logger.error(f"Missing required Firebase setting: {key}")
                    return False
            
            # Check database settings
            if not cls.DATABASE_URL:
                logger.error("Missing database URL")
                return False
            
            # Validate UI settings
            if cls.UI_SETTINGS['cards_per_row'] < 1:
                logger.error("Invalid cards per row setting")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            return False
    
    @classmethod
    def get_firebase_config(cls):
        """Get Firebase configuration"""
        return cls.FIREBASE_CONFIG
    
    @classmethod
    def get_database_settings(cls):
        """Get database settings"""
        return {
            'url': cls.DATABASE_URL,
            'timeout': cls.DATABASE_TIMEOUT
        }
    
    @classmethod
    def get_ui_settings(cls):
        """Get UI settings"""
        return cls.UI_SETTINGS.copy()
    
    @classmethod
    def get_cache_settings(cls):
        """Get cache settings"""
        return cls.CACHE_SETTINGS.copy()
    
    @classmethod
    def get_error_handling_settings(cls):
        """Get error handling settings"""
        return cls.ERROR_HANDLING 