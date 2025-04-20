import unittest
from datetime import datetime, timedelta
from modules.services.payment_service import PaymentService

class TestPaymentService(unittest.TestCase):
    def setUp(self):
        self.service = PaymentService()
        self.test_user_id = "test_user_123"
        self.test_email = "test@example.com"
        
    def test_create_customer(self):
        """Test creating a new customer"""
        customer = self.service.create_customer(self.test_user_id, self.test_email)
        self.assertIsNotNone(customer)
        self.assertEqual(customer.email, self.test_email)
        
    def test_create_subscription(self):
        """Test creating a subscription"""
        customer = self.service.create_customer(self.test_user_id, self.test_email)
        subscription = self.service.create_subscription(customer.id, "price_test123")
        self.assertIsNotNone(subscription)
        self.assertEqual(subscription.status, "active")
        
    def test_cancel_subscription(self):
        """Test canceling a subscription"""
        customer = self.service.create_customer(self.test_user_id, self.test_email)
        subscription = self.service.create_subscription(customer.id, "price_test123")
        canceled = self.service.cancel_subscription(subscription.id)
        self.assertTrue(canceled)
        
    def test_get_subscription(self):
        """Test retrieving subscription details"""
        customer = self.service.create_customer(self.test_user_id, self.test_email)
        subscription = self.service.create_subscription(customer.id, "price_test123")
        retrieved = self.service.get_subscription(subscription.id)
        self.assertEqual(retrieved.id, subscription.id)
        
    def test_list_payments(self):
        """Test listing payment history"""
        customer = self.service.create_customer(self.test_user_id, self.test_email)
        payments = self.service.list_payments(customer.id)
        self.assertIsInstance(payments, list)

if __name__ == '__main__':
    unittest.main() 