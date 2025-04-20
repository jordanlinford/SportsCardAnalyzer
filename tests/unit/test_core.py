"""
Unit tests for core functionality of the Sports Card Analyzer application.
"""

import pytest
from modules.core.error_handler import AppError, DatabaseError, AuthenticationError, ValidationError
from config.feature_flags import is_feature_enabled, enable_feature, disable_feature
from config.environment import Environment

def test_error_handling():
    """Test error handling functionality"""
    # Test AppError
    with pytest.raises(AppError) as exc_info:
        raise AppError("Test error", "TEST_ERROR", {"detail": "test"})
    assert str(exc_info.value) == "Test error"
    assert exc_info.value.error_code == "TEST_ERROR"
    assert exc_info.value.details == {"detail": "test"}
    
    # Test DatabaseError
    with pytest.raises(DatabaseError):
        raise DatabaseError("Database error")
    
    # Test AuthenticationError
    with pytest.raises(AuthenticationError):
        raise AuthenticationError("Auth error")
    
    # Test ValidationError
    with pytest.raises(ValidationError):
        raise ValidationError("Validation error")

def test_feature_flags():
    """Test feature flag functionality"""
    # Test core features
    assert is_feature_enabled('authentication') is True
    assert is_feature_enabled('collection_management') is True
    
    # Test experimental features
    assert is_feature_enabled('advanced_analytics') is False
    
    # Enable and test experimental feature
    enable_feature('advanced_analytics')
    assert is_feature_enabled('advanced_analytics') is True
    
    # Disable and test experimental feature
    disable_feature('advanced_analytics')
    assert is_feature_enabled('advanced_analytics') is False

def test_environment_settings():
    """Test environment settings"""
    # Test production check
    assert isinstance(Environment.is_production(), bool)
    
    # Test Firebase config
    firebase_config = Environment.get_firebase_config()
    assert isinstance(firebase_config, dict)
    assert all(key in firebase_config for key in [
        'apiKey', 'authDomain', 'projectId',
        'storageBucket', 'messagingSenderId', 'appId'
    ])
    
    # Test database settings
    db_settings = Environment.get_database_settings()
    assert isinstance(db_settings, dict)
    assert 'collection_name' in db_settings
    assert 'max_retries' in db_settings
    
    # Test UI settings
    ui_settings = Environment.get_ui_settings()
    assert isinstance(ui_settings, dict)
    assert 'cards_per_row' in ui_settings
    assert 'default_sort' in ui_settings
    
    # Test error handling settings
    error_settings = Environment.get_error_handling_settings()
    assert isinstance(error_settings, dict)
    assert 'max_retries' in error_settings
    assert 'show_detailed_errors' in error_settings

def test_error_handler_decorator():
    """Test error handler decorator"""
    from modules.core.error_handler import handle_error
    
    @handle_error
    def test_function():
        raise AppError("Test error")
    
    with pytest.raises(AppError):
        test_function()

def test_retry_decorator():
    """Test retry decorator"""
    from modules.core.error_handler import retry_on_error
    
    attempts = []
    
    @retry_on_error(max_retries=3, delay=0.1)
    def test_function():
        attempts.append(1)
        raise Exception("Test error")
    
    with pytest.raises(Exception):
        test_function()
    
    assert len(attempts) == 3  # Should have tried 3 times 