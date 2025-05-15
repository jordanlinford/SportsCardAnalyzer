"""
Feature flag configuration for safe feature management
"""

from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class FeatureFlags:
    """Manages feature flags for the application"""
    
    # Core features that should always be enabled
    CORE_FEATURES = {
        'basic_display': True,
        'collection_management': True,
        'card_deletion': True,
        'user_authentication': True
    }
    
    # Experimental features that can be toggled
    EXPERIMENTAL_FEATURES = {
        'advanced_search': False,
        'market_analysis': False,
        'grading_suggestions': False,
        'price_tracking': False
    }
    
    # Feature dependencies
    FEATURE_DEPENDENCIES = {
        'market_analysis': ['basic_display'],
        'grading_suggestions': ['market_analysis'],
        'price_tracking': ['market_analysis']
    }
    
    @staticmethod
    def is_feature_enabled(feature_name: str) -> bool:
        """Check if a feature is enabled"""
        try:
            # Check core features first
            if feature_name in FeatureFlags.CORE_FEATURES:
                return FeatureFlags.CORE_FEATURES[feature_name]
            
            # Check experimental features
            if feature_name in FeatureFlags.EXPERIMENTAL_FEATURES:
                # Check dependencies
                if feature_name in FeatureFlags.FEATURE_DEPENDENCIES:
                    for dependency in FeatureFlags.FEATURE_DEPENDENCIES[feature_name]:
                        if not FeatureFlags.is_feature_enabled(dependency):
                            logger.warning(f"Feature {feature_name} disabled due to missing dependency: {dependency}")
                            return False
                return FeatureFlags.EXPERIMENTAL_FEATURES[feature_name]
            
            logger.warning(f"Unknown feature: {feature_name}")
            return False
        except Exception as e:
            logger.error(f"Error checking feature {feature_name}: {str(e)}")
            return False
    
    @staticmethod
    def get_enabled_features() -> List[str]:
        """Get list of all enabled features"""
        enabled_features = []
        
        # Add core features
        for feature, enabled in FeatureFlags.CORE_FEATURES.items():
            if enabled:
                enabled_features.append(feature)
        
        # Add experimental features
        for feature, enabled in FeatureFlags.EXPERIMENTAL_FEATURES.items():
            if enabled and FeatureFlags.is_feature_enabled(feature):
                enabled_features.append(feature)
        
        return enabled_features
    
    @staticmethod
    def set_feature_state(feature_name: str, enabled: bool) -> bool:
        """Set the state of a feature"""
        try:
            if feature_name in FeatureFlags.CORE_FEATURES:
                logger.warning(f"Cannot modify core feature: {feature_name}")
                return False
            
            if feature_name in FeatureFlags.EXPERIMENTAL_FEATURES:
                FeatureFlags.EXPERIMENTAL_FEATURES[feature_name] = enabled
                logger.info(f"Feature {feature_name} set to {enabled}")
                return True
            
            logger.warning(f"Unknown feature: {feature_name}")
            return False
        except Exception as e:
            logger.error(f"Error setting feature {feature_name}: {str(e)}")
            return False 