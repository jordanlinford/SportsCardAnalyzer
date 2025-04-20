import unittest
from modules.services.subscription_service import SubscriptionService
from datetime import datetime, timedelta

class TestSubscriptionService(unittest.TestCase):
    def setUp(self):
        self.service = SubscriptionService()
        self.test_user_id = "test_user_123"
    
    def test_free_plan_limits(self):
        """Test free plan limits"""
        plan = self.service.get_user_plan(self.test_user_id)
        self.assertEqual(plan['plan'], 'free')
        self.assertEqual(plan['limits']['card_limit'], 25)
        self.assertEqual(plan['limits']['display_case_limit'], 3)
        self.assertEqual(plan['limits']['daily_search_limit'], 5)
    
    def test_card_limit_check(self):
        """Test card limit checking"""
        # Test within limit
        self.assertTrue(self.service.check_card_limit(self.test_user_id, 20))
        # Test at limit
        self.assertFalse(self.service.check_card_limit(self.test_user_id, 25))
        # Test over limit
        self.assertFalse(self.service.check_card_limit(self.test_user_id, 30))
    
    def test_display_case_limit_check(self):
        """Test display case limit checking"""
        # Test within limit
        self.assertTrue(self.service.check_display_case_limit(self.test_user_id, 2))
        # Test at limit
        self.assertFalse(self.service.check_display_case_limit(self.test_user_id, 3))
        # Test over limit
        self.assertFalse(self.service.check_display_case_limit(self.test_user_id, 4))
    
    def test_search_limit_check(self):
        """Test search limit checking"""
        # Test within daily limit
        self.assertTrue(self.service.check_search_limit(
            self.test_user_id, 
            4, 
            datetime.now() - timedelta(hours=1)
        ))
        
        # Test at daily limit
        self.assertFalse(self.service.check_search_limit(
            self.test_user_id, 
            5, 
            datetime.now() - timedelta(hours=1)
        ))
        
        # Test over daily limit
        self.assertFalse(self.service.check_search_limit(
            self.test_user_id, 
            6, 
            datetime.now() - timedelta(hours=1)
        ))
        
        # Test limit reset after 24 hours
        self.assertTrue(self.service.check_search_limit(
            self.test_user_id, 
            5, 
            datetime.now() - timedelta(days=1, hours=1)
        ))
    
    def test_feature_access(self):
        """Test feature access checking"""
        # Test basic features
        self.assertTrue(self.service.can_access_feature(self.test_user_id, 'basic_analysis'))
        self.assertTrue(self.service.can_access_feature(self.test_user_id, 'price_tracking'))
        
        # Test premium features
        self.assertFalse(self.service.can_access_feature(self.test_user_id, 'advanced_analytics'))
        self.assertFalse(self.service.can_access_feature(self.test_user_id, 'priority_support'))

if __name__ == '__main__':
    unittest.main() 