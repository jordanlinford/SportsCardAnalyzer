"""
Environment configuration for the Sports Card Analyzer application.
This file manages environment-specific settings and configurations.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Environment:
    """Environment configuration class"""
    
    # Application Settings
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
    DATABASE_SETTINGS = {
        'collection_name': 'collections',
        'cards_subcollection': 'cards',
        'max_retries': 3,
        'timeout': 30
    }
    
    # UI Settings
    UI_SETTINGS = {
        'cards_per_row': 5,
        'default_sort': 'player_name',
        'default_view': 'grid'
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
    def get_firebase_config(cls):
        """Get Firebase configuration"""
        return cls.FIREBASE_CONFIG
    
    @classmethod
    def get_database_settings(cls):
        """Get database settings"""
        return cls.DATABASE_SETTINGS
    
    @classmethod
    def get_ui_settings(cls):
        """Get UI settings"""
        return cls.UI_SETTINGS
    
    @classmethod
    def get_error_handling_settings(cls):
        """Get error handling settings"""
        return cls.ERROR_HANDLING 