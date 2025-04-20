from typing import Dict, Optional, Any
import stripe
import os
from datetime import datetime, timedelta
from modules.core.models import UserSubscription, UserUsage
from modules.core.firebase_manager import FirebaseManager
import logging

class SubscriptionService:
    def __init__(self):
        self.stripe = stripe
        self.stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        self.db = FirebaseManager.get_instance()
        self.logger = logging.getLogger(__name__)
        
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
    
    def _convert_timestamp(self, timestamp):
        """Convert various timestamp formats to integer"""
        if timestamp is None:
            return None
        try:
            if isinstance(timestamp, datetime):
                return int(timestamp.timestamp())
            elif isinstance(timestamp, (int, float)):
                return int(timestamp)
            else:
                self.logger.warning(f"Invalid timestamp format: {timestamp}")
                return None
        except Exception as e:
            self.logger.error(f"Error converting timestamp: {str(e)}")
            return None

    def _validate_subscription_data(self, data):
        """Validate subscription data"""
        if not data.get('customer') or not data.get('subscription'):
            raise ValueError("Missing required Stripe data")
        return True

    def get_user_plan(self, user_id: str) -> Dict:
        """Get user's current subscription plan"""
        try:
            subscription_doc = self.db.collection('subscriptions').document(user_id).get()
            if not subscription_doc.exists:
                return {
                    'plan': 'free',
                    'limits': self.plan_limits['free'],
                    'status': 'active'
                }
            
            subscription_data = subscription_doc.to_dict()
            
            # Ensure limits are properly set
            if 'limits' not in subscription_data:
                subscription_data['limits'] = self.plan_limits.get(subscription_data.get('plan', 'free'), self.plan_limits['free'])
            
            # Ensure status is set
            if 'status' not in subscription_data:
                subscription_data['status'] = 'active'
            
            return subscription_data
        except Exception as e:
            self.logger.error(f"Error getting user plan: {str(e)}")
            return {
                'plan': 'free',
                'limits': self.plan_limits['free'],
                'status': 'active'
            }
    
    def check_card_limit(self, user_id: str, current_count: int) -> bool:
        """Check if user can add more cards"""
        plan = self.get_user_plan(user_id)
        return current_count < plan['limits']['card_limit']
    
    def check_display_case_limit(self, user_id: str, current_count: int) -> bool:
        """Check if user can add more display cases"""
        plan = self.get_user_plan(user_id)
        return current_count < plan['limits']['display_case_limit']
    
    def check_search_limit(self, user_id: str, current_count: int, last_reset: datetime = None) -> bool:
        """Check if user can perform more searches"""
        try:
            plan = self.get_user_plan(user_id)
            
            # Handle timezone-naive datetime
            if last_reset and last_reset.tzinfo is not None:
                last_reset = last_reset.replace(tzinfo=None)
            
            # Check if we need to reset the counter
            if last_reset and datetime.now().replace(tzinfo=None) - last_reset > timedelta(days=1):
                # Update the reset time atomically
                self.db.collection('usage').document(user_id).update({
                    'daily_search_count': 0,
                    'last_search_reset': datetime.now().replace(tzinfo=None)
                })
                return True
            
            return current_count < plan['limits']['daily_search_limit']
        except Exception as e:
            self.logger.error(f"Error checking search limit: {str(e)}")
            return False
    
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
        try:
            # Validate plan type
            if plan not in self.plan_limits:
                raise ValueError(f"Invalid plan type: {plan}")
            
            # Handle current_period_end timestamp conversion
            current_period_end = stripe_data.get('current_period_end')
            if current_period_end is not None:
                try:
                    if isinstance(current_period_end, datetime):
                        current_period_end = int(current_period_end.timestamp())
                    elif isinstance(current_period_end, (int, float)):
                        current_period_end = int(current_period_end)
                    else:
                        self.logger.warning(f"Invalid current_period_end format: {current_period_end}")
                        current_period_end = 0
                except Exception as e:
                    self.logger.error(f"Error converting current_period_end: {str(e)}")
                    current_period_end = 0

            subscription_data = {
                'user_id': user_id,
                'plan': plan,
                'stripe_customer_id': stripe_data.get('customer'),
                'stripe_subscription_id': stripe_data.get('subscription'),
                'subscription_status': stripe_data.get('status', 'active'),
                'current_period_end': datetime.fromtimestamp(current_period_end) if current_period_end else None,
                'limits': self.plan_limits[plan],
                'last_updated': datetime.now()
            }
            
            # Add validation for required fields
            if not subscription_data['stripe_customer_id'] or not subscription_data['stripe_subscription_id']:
                raise ValueError("Missing required Stripe data")
            
            self.db.collection('subscriptions').document(user_id).set(subscription_data)
            self.logger.info(f"Successfully updated subscription for user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error updating subscription: {str(e)}")
            raise
    
    def get_usage_stats(self, user_id: str) -> Dict:
        """Get user's current usage statistics"""
        try:
            usage_doc = self.db.collection('usage').document(user_id).get()
            if not usage_doc.exists:
                return {
                    'card_count': 0,
                    'display_case_count': 0,
                    'daily_search_count': 0,
                    'last_search_reset': datetime.now().replace(tzinfo=None)
                }
            
            usage_data = usage_doc.to_dict()
            
            # Ensure last_search_reset is timezone-naive
            if 'last_search_reset' in usage_data and usage_data['last_search_reset'].tzinfo is not None:
                usage_data['last_search_reset'] = usage_data['last_search_reset'].replace(tzinfo=None)
            
            return usage_data
        except Exception as e:
            self.logger.error(f"Error getting usage stats: {str(e)}")
            return {
                'card_count': 0,
                'display_case_count': 0,
                'daily_search_count': 0,
                'last_search_reset': datetime.now().replace(tzinfo=None)
            } 