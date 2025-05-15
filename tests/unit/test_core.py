"""
Unit tests for core functionality of the Sports Card Analyzer application.
"""

import pytest
from modules.core.error_handler import (
    handle_error,
    ValidationError,
    DatabaseError,
    AuthenticationError,
    DisplayError,
    validate_input,
    log_error,
    display_error_message
)
from config.feature_flags import FeatureFlags, is_feature_enabled, enable_feature, disable_feature
from config.environment import Environment

def test_handle_error():
    """Test error handling decorator"""
    
    @handle_error
    def test_func():
        raise ValidationError("Test validation error")
    
    @handle_error
    def test_func2():
        raise DatabaseError("Test database error")
    
    @handle_error
    def test_func3():
        raise Exception("Test unexpected error")
    
    # Test validation error
    result = test_func()
    assert result is None
    
    # Test database error
    result = test_func2()
    assert result is None
    
    # Test unexpected error
    result = test_func3()
    assert result is None

def test_validate_input():
    """Test input validation"""
    # Test None input
    with pytest.raises(ValidationError):
        validate_input(None)
    
    # Test valid input without required fields
    assert validate_input({"test": "value"}) is True
    
    # Test valid input with required fields
    assert validate_input(
        {"field1": "value1", "field2": "value2"},
        ["field1", "field2"]
    ) is True
    
    # Test invalid input with required fields
    with pytest.raises(ValidationError):
        validate_input(
            {"field1": "value1"},
            ["field1", "field2"]
        )

def test_feature_flags():
    """Test feature flag functionality"""
    # Test core features
    assert FeatureFlags.is_feature_enabled('basic_display') is True
    assert FeatureFlags.is_feature_enabled('collection_management') is True
    
    # Test experimental features
    assert FeatureFlags.is_feature_enabled('advanced_search') is False
    assert FeatureFlags.is_feature_enabled('market_analysis') is False
    
    # Test unknown feature
    assert FeatureFlags.is_feature_enabled('unknown_feature') is False

def test_environment_settings():
    """Test environment settings"""
    # Test getting settings
    assert Environment.get_setting('DEBUG_MODE') is not None
    assert Environment.get_setting('CARDS_PER_ROW') is not None
    
    # Test UI settings
    ui_settings = Environment.get_ui_settings()
    assert 'cards_per_row' in ui_settings
    assert 'max_image_size' in ui_settings
    
    # Test cache settings
    cache_settings = Environment.get_cache_settings()
    assert 'enabled' in cache_settings
    assert 'ttl' in cache_settings

def test_error_logging():
    """Test error logging functionality"""
    # Test log_error
    try:
        raise ValueError("Test error")
    except Exception as e:
        log_error(e, "Test context")
    
    # Test display_error_message
    display_error_message("Test error message", "error")
    display_error_message("Test warning message", "warning")
    display_error_message("Test info message", "info")

def test_environment_validation():
    """Test environment validation"""
    # Test configuration validation
    assert Environment.validate_config() is True
    
    # Test getting Firebase config
    firebase_config = Environment.get_firebase_config()
    assert isinstance(firebase_config, dict)
    
    # Test getting database settings
    db_settings = Environment.get_database_settings()
    assert isinstance(db_settings, dict)
    assert 'url' in db_settings
    assert 'timeout' in db_settings

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