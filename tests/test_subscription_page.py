import unittest
from unittest.mock import patch, MagicMock
import streamlit as st
from pages.subscription_7 import render_subscription_page
from modules.services.payment_service import PaymentService
from modules.database.subscription_db import SubscriptionDB
from datetime import datetime, timedelta

class TestSubscriptionPage(unittest.TestCase):
    @patch('stripe.Customer')
    @patch('stripe.Subscription')
    @patch('stripe.checkout.Session')
    def setUp(self, mock_checkout_session, mock_subscription, mock_customer):
        # Mock Stripe Customer
        self.mock_customer = MagicMock()
        self.mock_customer.id = "cus_test123"
        mock_customer.create.return_value = self.mock_customer
        mock_customer.retrieve.return_value = self.mock_customer
        
        # Mock Stripe Subscription
        self.mock_subscription = MagicMock()
        self.mock_subscription.id = "sub_test123"
        self.mock_subscription.status = "active"
        mock_subscription.create.return_value = self.mock_subscription
        mock_subscription.retrieve.return_value = self.mock_subscription
        
        # Mock Checkout Session
        self.mock_session = MagicMock()
        self.mock_session.id = "cs_test123"
        self.mock_session.url = "https://checkout.stripe.com/test"
        mock_checkout_session.create.return_value = self.mock_session
        
        # Set up test user data
        self.test_user_id = "test_user_123"
        self.test_email = "test@example.com"
        
        # Mock session state
        if not hasattr(st, 'session_state'):
            setattr(st, 'session_state', {})
        
        st.session_state.user = {
            'uid': self.test_user_id,
            'email': self.test_email,
            'display_name': self.test_user_id,
            'stripe_customer_id': self.mock_customer.id
        }
        
        # Mock Firebase
        self.db_patcher = patch('modules.database.subscription_db.FirebaseManager')
        self.mock_firebase = self.db_patcher.start()
        self.mock_db = MagicMock()
        self.mock_firebase.get_db.return_value = self.mock_db
        
        # Mock Streamlit components
        self.mock_streamlit()
        
    def mock_streamlit(self):
        """Mock Streamlit components"""
        st.title = MagicMock()
        st.header = MagicMock()
        st.subheader = MagicMock()
        st.write = MagicMock()
        st.button = MagicMock(return_value=False)
        st.error = MagicMock()
        st.success = MagicMock()
        st.columns = MagicMock(return_value=[MagicMock(), MagicMock(), MagicMock()])
        
    def tearDown(self):
        self.db_patcher.stop()
        
    @patch('stripe.checkout.Session')
    def test_render_subscription_page_free_plan(self, mock_checkout_session):
        """Test rendering subscription page for free plan user"""
        # Mock subscription data
        self.mock_db.collection().document().get().to_dict.return_value = {
            'user_id': self.test_user_id,
            'plan': 'free',
            'subscription_status': 'active',
            'stripe_customer_id': self.mock_customer.id,
            'current_period_end': datetime.now() + timedelta(days=30)
        }
        
        # Mock checkout session
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/test"
        mock_checkout_session.create.return_value = mock_session
        
        render_subscription_page()
        
        # Verify page components were rendered
        st.title.assert_called_with("Subscription Management")
        st.button.assert_any_call("Upgrade to Basic")
        st.button.assert_any_call("Upgrade to Premium")
        
    @patch('stripe.Subscription')
    def test_render_subscription_page_basic_plan(self, mock_subscription):
        """Test rendering subscription page for basic plan user"""
        # Mock subscription data
        self.mock_db.collection().document().get().to_dict.return_value = {
            'user_id': self.test_user_id,
            'plan': 'basic',
            'subscription_status': 'active',
            'stripe_customer_id': self.mock_customer.id,
            'stripe_subscription_id': self.mock_subscription.id,
            'current_period_end': datetime.now() + timedelta(days=30)
        }
        
        # Mock subscription retrieval
        mock_subscription.retrieve.return_value = self.mock_subscription
        
        render_subscription_page()
        
        # Verify page components were rendered
        st.title.assert_called_with("Subscription Management")
        st.button.assert_any_call("Cancel Subscription")
        st.button.assert_any_call("Upgrade to Premium")
        
    def test_error_handling(self):
        """Test error handling when subscription data is missing"""
        # Mock missing subscription data
        self.mock_db.collection().document().get().to_dict.return_value = None
        
        render_subscription_page()
        
        # Verify error was displayed
        st.error.assert_called_with("Error loading subscription data")

if __name__ == '__main__':
    unittest.main() 