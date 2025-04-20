import unittest
from unittest.mock import MagicMock, patch
import json
import stripe
import os
from modules.services.webhook_handler import WebhookHandler

class TestWebhookHandlerEdgeCases(unittest.TestCase):
    def setUp(self):
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'STRIPE_SECRET_KEY': 'sk_test_123',
            'STRIPE_WEBHOOK_SECRET': 'whsec_test',
            'STRIPE_BASIC_PRICE_ID': 'price_basic_123',
            'STRIPE_PREMIUM_PRICE_ID': 'price_premium_456'
        })
        self.env_patcher.start()
        
        # Create handler instance
        self.handler = WebhookHandler()
        
        # Mock services
        self.handler.payment_service = MagicMock()
        self.handler.subscription_service = MagicMock()
        self.handler.subscription_service.db = MagicMock()
        
        # Test data
        self.sig_header = 'test_signature'
        
    def tearDown(self):
        self.env_patcher.stop()

    @patch('stripe.Webhook.construct_event')
    @patch('stripe.Subscription.retrieve')
    def test_checkout_missing_client_reference_id(self, mock_subscription_retrieve, mock_construct_event):
        """Test handling of checkout session without client_reference_id"""
        # Create test subscription data
        subscription = MagicMock()
        subscription.id = 'sub_123'
        subscription.customer = 'cus_123'
        subscription.status = 'active'
        subscription.current_period_end = 1234567890
        subscription.metadata = {'plan_type': 'premium'}
        subscription.items.data = [MagicMock()]
        subscription.items.data[0].price.unit_amount = 2000
        mock_subscription_retrieve.return_value = subscription
        
        # Create test session data without client_reference_id
        event = MagicMock()
        event.type = 'checkout.session.completed'
        event.data = MagicMock()
        event.data.object = {
            'subscription': 'sub_123'
            # client_reference_id is missing
        }
        mock_construct_event.return_value = event
        
        payload = json.dumps({
            'type': 'checkout.session.completed',
            'data': {'object': event.data.object}
        })
        result = self.handler.handle_event(payload, self.sig_header)
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('client_reference_id', result.get('message', '').lower())

    @patch('stripe.Webhook.construct_event')
    @patch('stripe.Subscription.retrieve')
    def test_checkout_failed_subscription_retrieval(self, mock_subscription_retrieve, mock_construct_event):
        """Test handling of failed subscription retrieval"""
        # Mock subscription retrieval failure
        mock_subscription_retrieve.side_effect = stripe.error.InvalidRequestError(
            'No such subscription: sub_123',
            'sub_123'
        )
        
        # Create test session data
        event = MagicMock()
        event.type = 'checkout.session.completed'
        event.data = MagicMock()
        event.data.object = {
            'subscription': 'sub_123',
            'client_reference_id': 'user_123'
        }
        mock_construct_event.return_value = event
        
        payload = json.dumps({
            'type': 'checkout.session.completed',
            'data': {'object': event.data.object}
        })
        result = self.handler.handle_event(payload, self.sig_header)
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('no such subscription', result.get('message', '').lower())

    @patch('stripe.Webhook.construct_event')
    def test_subscription_update_failed_service_call(self, mock_construct_event):
        """Test handling of failed subscription service update"""
        event = MagicMock()
        event.type = 'customer.subscription.updated'
        event.data = MagicMock()
        event.data.object = {
            'id': 'sub_123',
            'customer': 'cus_123',
            'status': 'active',
            'current_period_end': 1234567890,
            'metadata': {
                'user_id': 'user_123',
                'plan_type': 'premium'
            }
        }
        mock_construct_event.return_value = event
        
        # Mock service failure
        self.handler.subscription_service.update_subscription.side_effect = Exception('Database error')
        
        payload = json.dumps({
            'type': 'customer.subscription.updated',
            'data': {'object': event.data.object}
        })
        result = self.handler.handle_event(payload, self.sig_header)
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('database error', result.get('message', '').lower())

    @patch('stripe.Webhook.construct_event')
    def test_subscription_various_statuses(self, mock_construct_event):
        """Test handling of different subscription statuses"""
        statuses = ['trialing', 'past_due', 'incomplete', 'incomplete_expired']
        
        for status in statuses:
            event = MagicMock()
            event.type = 'customer.subscription.updated'
            event.data = MagicMock()
            event.data.object = {
                'id': 'sub_123',
                'customer': 'cus_123',
                'status': status,
                'current_period_end': 1234567890,
                'metadata': {
                    'user_id': 'user_123',
                    'plan_type': 'premium'
                }
            }
            mock_construct_event.return_value = event
            
            payload = json.dumps({
                'type': 'customer.subscription.updated',
                'data': {'object': event.data.object}
            })
            result = self.handler.handle_event(payload, self.sig_header)
            
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['subscription_id'], 'sub_123')

    @patch('stripe.Webhook.construct_event')
    def test_invoice_decimal_amounts(self, mock_construct_event):
        """Test handling of decimal amounts in invoice payments"""
        event = MagicMock()
        event.type = 'invoice.payment_succeeded'
        event.data = MagicMock()
        event.data.object = {
            'id': 'in_123',
            'amount_paid': 1999,  # $19.99
            'metadata': {
                'user_id': 'user_123',
                'plan_type': 'basic'
            }
        }
        mock_construct_event.return_value = event
        
        payload = json.dumps({
            'type': 'invoice.payment_succeeded',
            'data': {'object': event.data.object}
        })
        result = self.handler.handle_event(payload, self.sig_header)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['invoice_id'], 'in_123')
        
        # Verify the amount was properly converted to dollars
        history_call = self.handler.subscription_service.db.add_subscription_history.call_args[0][0]
        self.assertEqual(history_call.amount, 19.99)

    def test_get_plan_from_price(self):
        """Test plan identification from price IDs"""
        test_cases = [
            ('price_basic_123', 'basic'),
            ('price_premium_456', 'premium'),
            ('price_unknown_789', 'free'),
            (None, 'free'),
            ('', 'free')
        ]
        
        for price_id, expected_plan in test_cases:
            plan = self.handler._get_plan_from_price(price_id)
            self.assertEqual(plan, expected_plan)

    @patch('stripe.Customer.retrieve')
    def test_get_user_id_from_customer(self, mock_customer_retrieve):
        """Test user ID retrieval from customer data"""
        test_cases = [
            ({'metadata': {'user_id': 'user_123'}}, 'user_123'),
            ({'metadata': {}}, ''),
            ({}, ''),
            ({'metadata': {'user_id': ''}}, '')
        ]
        
        for customer_data, expected_user_id in test_cases:
            mock_customer_retrieve.return_value = customer_data
            user_id = self.handler._get_user_id_from_customer('cus_123')
            self.assertEqual(user_id, expected_user_id)

if __name__ == '__main__':
    unittest.main() 