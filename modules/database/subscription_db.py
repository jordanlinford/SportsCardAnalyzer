from typing import Optional, List, Dict
from datetime import datetime, timedelta
from modules.database.schema import UserSubscription, UserUsage, SubscriptionHistory
from modules.core.firebase_manager import FirebaseManager
from modules.core.repository import BaseRepository

class SubscriptionDB(BaseRepository[UserSubscription]):
    """Repository for managing subscription data"""
    
    def __init__(self):
        super().__init__("subscriptions", UserSubscription)
        self.db = FirebaseManager.get_firestore_client()
        self.subscriptions_collection = self.db.collection('subscriptions')
        self.usage_collection = self.db.collection('usage_stats')
        self.history_collection = self.db.collection('subscription_history')
    
    def get_user_subscription(self, user_id: str) -> Optional[UserSubscription]:
        """Get user's subscription information"""
        doc = self.subscriptions_collection.document(user_id).get()
        if doc.exists:
            return UserSubscription(**doc.to_dict())
        return None
    
    def get_user_usage(self, user_id: str) -> Dict:
        """Get user's usage statistics"""
        doc = self.usage_collection.document(user_id).get()
        if doc.exists:
            return doc.to_dict()
        return {
            'cards_analyzed': 0,
            'display_cases_created': 0,
            'searches_performed': 0,
            'last_updated': datetime.now()
        }
    
    def update_subscription(self, subscription: UserSubscription) -> bool:
        """Update user's subscription information"""
        try:
            subscription_dict = subscription.model_dump()
            self.subscriptions_collection.document(subscription.user_id).set(subscription_dict)
            return True
        except Exception as e:
            self.logger.error(f"Error updating subscription: {str(e)}")
            return False
    
    def update_usage(self, usage: UserUsage) -> bool:
        """Update user's usage statistics"""
        try:
            usage_dict = usage.model_dump()
            self.usage_collection.document(usage.user_id).set(usage_dict, merge=True)
            return True
        except Exception as e:
            self.logger.error(f"Error updating usage stats: {str(e)}")
            return False
    
    def get_subscription_history(self, user_id: str) -> List[Dict]:
        """Get user's subscription history"""
        docs = self.subscriptions_collection.document(user_id).collection('history').get()
        return [doc.to_dict() for doc in docs]
    
    def add_subscription_history(self, user_id: str, history_data: Dict) -> bool:
        """Add an entry to user's subscription history"""
        try:
            self.subscriptions_collection.document(user_id).collection('history').add(history_data)
            return True
        except Exception as e:
            self.logger.error(f"Error adding subscription history: {str(e)}")
            return False
    
    def increment_search_count(self, user_id: str) -> bool:
        """Increment search count and check if within limits"""
        usage = self.get_user_usage(user_id)
        if not usage:
            usage = UserUsage(user_id=user_id)
        
        # Check if we need to reset the counter
        if datetime.now() - usage['last_updated'] > timedelta(days=1):
            usage['searches_performed'] = 0
            usage['last_updated'] = datetime.now()
        
        usage['searches_performed'] += 1
        self.update_usage(usage)
        return usage['searches_performed'] <= 5  # Free tier limit
    
    def increment_card_count(self, user_id: str) -> bool:
        """Increment card count and check if within limits"""
        usage = self.get_user_usage(user_id)
        if not usage:
            usage = UserUsage(user_id=user_id)
        
        usage['cards_analyzed'] += 1
        self.update_usage(usage)
        return usage['cards_analyzed'] <= 25  # Free tier limit
    
    def increment_display_case_count(self, user_id: str) -> bool:
        """Increment display case count and check if within limits"""
        usage = self.get_user_usage(user_id)
        if not usage:
            usage = UserUsage(user_id=user_id)
        
        usage['display_cases_created'] += 1
        self.update_usage(usage)
        return usage['display_cases_created'] <= 3  # Free tier limit
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user information from Firebase"""
        try:
            doc = self.db.collection('users').document(user_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            self.logger.error(f"Error getting user: {str(e)}")
            return None 