import unittest
from datetime import datetime, timedelta
from modules.services.subscription_service import SubscriptionService

class TestSubscriptionService(unittest.TestCase):
    def setUp(self):
        self.service = SubscriptionService()
        self.test_user_id = "test_user_123"
        
    def test_get_user_plan(self):
        """Test getting user's plan"""
        plan = self.service.get_user_plan(self.test_user_id)
        self.assertIsNotNone(plan)
        self.assertEqual(plan['plan'], 'free')  # Default plan
        
    def test_plan_limits(self):
        """Test plan limits"""
        # Test free plan limits
        self.assertTrue(self.service.check_card_limit(self.test_user_id, 24))
        self.assertFalse(self.service.check_card_limit(self.test_user_id, 26))
        
        self.assertTrue(self.service.check_display_case_limit(self.test_user_id, 2))
        self.assertFalse(self.service.check_display_case_limit(self.test_user_id, 4))
        
        # Test search limits
        for _ in range(5):
            self.assertTrue(self.service.check_search_limit(self.test_user_id))
        self.assertFalse(self.service.check_search_limit(self.test_user_id))
        
    def test_feature_access(self):
        """Test feature access control"""
        # Test free plan features
        self.assertTrue(self.service.can_access_feature(self.test_user_id, 'basic_analysis'))
        self.assertTrue(self.service.can_access_feature(self.test_user_id, 'price_tracking'))
        self.assertFalse(self.service.can_access_feature(self.test_user_id, 'market_insights'))
        
    def test_usage_stats(self):
        """Test usage statistics"""
        stats = self.service.get_usage_stats(self.test_user_id)
        self.assertIsNotNone(stats)
        self.assertEqual(stats['card_count'], 0)
        self.assertEqual(stats['display_case_count'], 0)
        self.assertEqual(stats['daily_search_count'], 0)
        
    def test_subscription_update(self):
        """Test subscription updates"""
        # Update to basic plan
        stripe_data = {
            'customer': 'cus_test123',
            'subscription': 'sub_test123',
            'status': 'active',
            'current_period_end': datetime.now() + timedelta(days=30)
        }
        self.service.update_subscription(self.test_user_id, 'basic', stripe_data)
        
        # Verify update
        plan = self.service.get_user_plan(self.test_user_id)
        self.assertEqual(plan['plan'], 'basic')
        self.assertEqual(plan['subscription_status'], 'active')

if __name__ == '__main__':
    unittest.main() 