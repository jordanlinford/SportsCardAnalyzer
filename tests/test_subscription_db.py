import unittest
from datetime import datetime, timedelta
from modules.database.subscription_db import SubscriptionDB
from modules.database.schema import UserSubscription, UserUsage, SubscriptionHistory

class TestSubscriptionDB(unittest.TestCase):
    def setUp(self):
        self.db = SubscriptionDB()
        self.test_user_id = "test_user_123"
        
    def test_user_subscription(self):
        """Test user subscription operations"""
        # Create test subscription
        subscription = UserSubscription(
            user_id=self.test_user_id,
            plan='basic',
            stripe_customer_id='cus_test123',
            stripe_subscription_id='sub_test123',
            subscription_status='active',
            current_period_end=datetime.now() + timedelta(days=30)
        )
        
        # Save subscription
        self.db.update_subscription(subscription)
        
        # Retrieve subscription
        retrieved = self.db.get_user_subscription(self.test_user_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.plan, 'basic')
        self.assertEqual(retrieved.stripe_customer_id, 'cus_test123')
        
    def test_user_usage(self):
        """Test user usage tracking"""
        # Create test usage
        usage = UserUsage(
            user_id=self.test_user_id,
            card_count=10,
            display_case_count=2,
            daily_search_count=3
        )
        
        # Save usage
        self.db.update_usage(usage)
        
        # Retrieve usage
        retrieved = self.db.get_user_usage(self.test_user_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.card_count, 10)
        self.assertEqual(retrieved.display_case_count, 2)
        
    def test_search_limit(self):
        """Test search limit functionality"""
        # Test within limit
        for i in range(5):
            self.assertTrue(self.db.increment_search_count(self.test_user_id))
        
        # Test over limit
        self.assertFalse(self.db.increment_search_count(self.test_user_id))
        
    def test_card_limit(self):
        """Test card limit functionality"""
        # Test within limit
        for i in range(25):
            self.assertTrue(self.db.increment_card_count(self.test_user_id))
        
        # Test over limit
        self.assertFalse(self.db.increment_card_count(self.test_user_id))
        
    def test_display_case_limit(self):
        """Test display case limit functionality"""
        # Test within limit
        for i in range(3):
            self.assertTrue(self.db.increment_display_case_count(self.test_user_id))
        
        # Test over limit
        self.assertFalse(self.db.increment_display_case_count(self.test_user_id))
        
    def test_subscription_history(self):
        """Test subscription history tracking"""
        # Create test history
        history = SubscriptionHistory(
            user_id=self.test_user_id,
            event_type='subscription_created',
            plan='basic',
            amount=9.99,
            status='active'
        )
        
        # Add history
        self.db.add_subscription_history(history)
        
        # Retrieve history
        history_list = self.db.get_subscription_history(self.test_user_id)
        self.assertGreater(len(history_list), 0)
        self.assertEqual(history_list[0].plan, 'basic')
        self.assertEqual(history_list[0].amount, 9.99)

if __name__ == '__main__':
    unittest.main() 