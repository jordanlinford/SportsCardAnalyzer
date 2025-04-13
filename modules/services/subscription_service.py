from typing import Dict, Optional, Any
import stripe
import os
from datetime import datetime, timedelta
from modules.database.subscription_db import SubscriptionDB
from modules.database.schema import UserSubscription, UserUsage

class SubscriptionService:
    def __init__(self):
        self.stripe = stripe
        self.stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        self.db = SubscriptionDB()
        
        # Define plan limits
        self.plan_limits = {
            'free': {
                'card_limit': 25,
                'display_case_limit': 3,
                'daily_search_limit': 5,
                'features': ['basic_analysis', 'price_tracking']
            },
            'basic': {
                'card_limit': 50,
                'display_case_limit': 5,
                'daily_search_limit': float('inf'),  # unlimited
                'features': ['basic_analysis', 'price_tracking', 'market_insights']
            },
            'premium': {
                'card_limit': float('inf'),  # unlimited
                'display_case_limit': float('inf'),  # unlimited
                'daily_search_limit': float('inf'),  # unlimited
                'features': ['basic_analysis', 'price_tracking', 'market_insights', 
                           'advanced_analytics', 'priority_support', 'bulk_analysis', 
                           'custom_reports']
            }
        }
        
        self.admin_emails = [
            'admin@sportscardanalyzer.com',
            'test@sportscardanalyzer.com',  # for testing
            'jrlinford@gmail.com'  # added personal admin access
        ]
    
    def is_admin(self, email: str) -> bool:
        """Check if the user is an admin"""
        return email in self.admin_emails
    
    def get_user_plan(self, user_id: str) -> Dict[str, Any]:
        """Get user's current subscription plan"""
        subscription = self.db.get_user_subscription(user_id)
        
        # Check if user is admin
        user = self.db.get_user(user_id)
        if user and self.is_admin(user.get('email')):
            return {
                'plan': 'premium',
                'status': 'active',
                'is_admin': True
            }
        
        if not subscription:
            return {
                'plan': 'free',
                'status': 'active',
                'is_admin': False
            }
        
        return {
            'plan': subscription.plan,
            'status': subscription.subscription_status,
            'is_admin': False
        }
    
    def check_card_limit(self, user_id: str, current_count: int) -> bool:
        """Check if user can add more cards"""
        plan = self.get_user_plan(user_id)
        return current_count < plan['limits']['card_limit']
    
    def check_display_case_limit(self, user_id: str, current_count: int) -> bool:
        """Check if user can add more display cases"""
        plan = self.get_user_plan(user_id)
        return current_count < plan['limits']['display_case_limit']
    
    def check_search_limit(self, user_id: str) -> bool:
        """Check if user can perform more searches today"""
        plan = self.get_user_plan(user_id)
        
        # If unlimited searches, return True
        if plan['limits']['daily_search_limit'] == float('inf'):
            return True
            
        # Check and increment search count
        return self.db.increment_search_count(user_id)
    
    def get_available_features(self, user_id: str) -> list:
        """Get list of features available to the user"""
        plan = self.get_user_plan(user_id)
        return plan['limits']['features']
    
    def can_access_feature(self, user_id: str, feature: str) -> bool:
        """Check if user can access a specific feature"""
        available_features = self.get_available_features(user_id)
        return feature in available_features
    
    def update_subscription(self, user_id: str, plan: str, stripe_data: dict) -> None:
        """Update user's subscription information"""
        subscription = UserSubscription(
            user_id=user_id,
            plan=plan,
            stripe_customer_id=stripe_data.get('customer'),
            stripe_subscription_id=stripe_data.get('subscription'),
            subscription_status=stripe_data.get('status', 'active'),
            current_period_end=datetime.fromtimestamp(stripe_data.get('current_period_end', 0))
        )
        self.db.update_subscription(subscription)
    
    def get_usage_stats(self, user_id: str) -> Dict:
        """Get user's current usage statistics"""
        usage = self.db.get_user_usage(user_id)
        if not usage:
            return {
                'card_count': 0,
                'display_case_count': 0,
                'daily_search_count': 0,
                'last_search_reset': datetime.now()
            }
        return usage.dict() 