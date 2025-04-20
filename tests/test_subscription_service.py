import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from modules.services.subscription_service import SubscriptionService

class TestSubscriptionService(unittest.TestCase):
    def setUp(self):
        # Create mock Firebase instance
        self.mock_db = MagicMock()
        self.mock_doc = MagicMock()
        self.mock_doc.exists = False
        self.mock_db.collection().document().get.return_value = self.mock_doc
        
        # Patch FirebaseManager
        patcher = patch('modules.services.subscription_service.FirebaseManager')
        self.addCleanup(patcher.stop)
        mock_firebase = patcher.start()
        mock_firebase.get_instance.return_value = self.mock_db
        
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
        
        # Test search limits with current count
        self.assertTrue(self.service.check_search_limit(self.test_user_id, 4))  # Within limit
        self.assertFalse(self.service.check_search_limit(self.test_user_id, 6))  # Exceeds limit
        
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
        # Mock document set method
        self.mock_db.collection().document().set = MagicMock()
        
        # Update to basic plan
        stripe_data = {
            'customer': 'cus_test123',
            'subscription': 'sub_test123',
            'status': 'active',
            'current_period_end': datetime.now() + timedelta(days=30)
        }
        
        # Update subscription
        self.service.update_subscription(self.test_user_id, 'basic', stripe_data)
        
        # Verify the document.set was called
        self.mock_db.collection().document().set.assert_called_once()
        
        # Mock the get_user_plan response for basic plan
        mock_basic_doc = MagicMock()
        mock_basic_doc.exists = True
        mock_basic_doc.to_dict.return_value = {
            'plan': 'basic',
            'subscription_status': 'active',
            'limits': self.service.plan_limits['basic']
        }
        self.mock_db.collection().document().get.return_value = mock_basic_doc
        
        # Verify update
        plan = self.service.get_user_plan(self.test_user_id)
        self.assertEqual(plan['plan'], 'basic')
        self.assertEqual(plan['subscription_status'], 'active')

    def test_timestamp_conversion(self):
        """Test various timestamp conversion scenarios"""
        test_cases = [
            {
                'input': datetime.now(),
                'expected_type': int
            },
            {
                'input': 1234567890,
                'expected_type': int
            },
            {
                'input': 1234567890.0,
                'expected_type': int
            },
            {
                'input': 'invalid',
                'expected_type': type(None)
            }
        ]
        
        for case in test_cases:
            with self.subTest(input=case['input']):
                result = self.service._convert_timestamp(case['input'])
                self.assertIsInstance(result, case['expected_type'])
                
    def test_subscription_validation(self):
        """Test subscription data validation"""
        valid_data = {
            'customer': 'cus_123',
            'subscription': 'sub_123',
            'current_period_end': datetime.now().timestamp()
        }
        
        invalid_data = {
            'customer': None,
            'subscription': 'sub_123',
            'current_period_end': datetime.now().timestamp()
        }
        
        # Test valid data
        self.assertTrue(self.service._validate_subscription_data(valid_data))
        
        # Test invalid data
        with self.assertRaises(ValueError):
            self.service._validate_subscription_data(invalid_data)

if __name__ == '__main__':
    unittest.main() 