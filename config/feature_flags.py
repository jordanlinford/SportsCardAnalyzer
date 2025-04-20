"""
Feature flags configuration for the Sports Card Analyzer application.
This file controls which features are enabled/disabled in the application.
"""

# Core Features (Always Enabled)
CORE_FEATURES = {
    'authentication': True,
    'collection_management': True,
    'basic_display': True,
    'firebase_integration': True
}

# Experimental Features (Can be toggled)
EXPERIMENTAL_FEATURES = {
    'advanced_analytics': False,
    'market_analysis': False,
    'card_grading': False,
    'collection_sharing': False
}

# Feature Dependencies
FEATURE_DEPENDENCIES = {
    'advanced_analytics': ['collection_management'],
    'market_analysis': ['collection_management'],
    'card_grading': ['collection_management'],
    'collection_sharing': ['collection_management', 'authentication']
}

def is_feature_enabled(feature_name):
    """
    Check if a feature is enabled.
    
    Args:
        feature_name (str): Name of the feature to check
        
    Returns:
        bool: True if feature is enabled, False otherwise
    """
    # Check if it's a core feature
    if feature_name in CORE_FEATURES:
        return CORE_FEATURES[feature_name]
    
    # Check if it's an experimental feature
    if feature_name in EXPERIMENTAL_FEATURES:
        # Check dependencies first
        if feature_name in FEATURE_DEPENDENCIES:
            for dependency in FEATURE_DEPENDENCIES[feature_name]:
                if not is_feature_enabled(dependency):
                    return False
        return EXPERIMENTAL_FEATURES[feature_name]
    
    return False

def enable_feature(feature_name):
    """
    Enable a feature if it's experimental.
    
    Args:
        feature_name (str): Name of the feature to enable
    """
    if feature_name in EXPERIMENTAL_FEATURES:
        EXPERIMENTAL_FEATURES[feature_name] = True

def disable_feature(feature_name):
    """
    Disable a feature if it's experimental.
    
    Args:
        feature_name (str): Name of the feature to disable
    """
    if feature_name in EXPERIMENTAL_FEATURES:
        EXPERIMENTAL_FEATURES[feature_name] = False 