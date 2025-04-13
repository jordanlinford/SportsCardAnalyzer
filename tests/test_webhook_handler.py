import unittest
from unittest.mock import MagicMock, patch
import json
import stripe
import os
from modules.services.webhook_handler import WebhookHandler

class TestWebhookHandler(unittest.TestCase):
    def setUp(self):
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'STRIPE_SECRET_KEY': 'sk_test_123',
            'STRIPE_WEBHOOK_SECRET': 'whsec_test'
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
        
    def test_handle_invalid_payload(self):
        """Test handling of invalid JSON payload"""
        result = self.handler.handle_event('invalid payload', self.sig_header)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error'], 'Invalid payload')
        
    @patch('stripe.Webhook.construct_event')
    def test_handle_invalid_signature(self, mock_construct_event):
        """Test handling of invalid signature"""
        mock_construct_event.side_effect = stripe.error.SignatureVerificationError('Invalid signature', 'sig_header')
        payload = json.dumps({'type': 'test.event'})
        result = self.handler.handle_event(payload, self.sig_header)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error'], 'Invalid signature')
        
    @patch('stripe.Webhook.construct_event')
    @patch('stripe.Subscription.retrieve')
    def test_handle_checkout_completed(self, mock_subscription_retrieve, mock_construct_event):
        """Test handling of successful checkout session"""
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
        
        # Create test session data
        event = MagicMock()
        event.type = 'checkout.session.completed'
        event.data = MagicMock()
        event.data.object = {
            'subscription': 'sub_123',
            'client_reference_id': 'user_123'
        }
        mock_construct_event.return_value = event
        
        # Mock successful service calls
        self.handler.subscription_service.update_subscription.return_value = True
        self.handler.subscription_service.db.add_subscription_history.return_value = True
        
        payload = json.dumps({
            'type': 'checkout.session.completed',
            'data': {'object': event.data.object}
        })
        result = self.handler.handle_event(payload, self.sig_header)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['subscription_id'], 'sub_123')
        self.assertIn('message', result)
        
    @patch('stripe.Webhook.construct_event')
    def test_handle_subscription_updated(self, mock_construct_event):
        """Test handling of subscription update"""
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
            },
            'items': {
                'data': [{
                    'price': {'unit_amount': 2000}
                }]
            }
        }
        mock_construct_event.return_value = event
        
        # Mock successful service calls
        self.handler.subscription_service.update_subscription.return_value = True
        self.handler.subscription_service.db.add_subscription_history.return_value = True
        
        payload = json.dumps({
            'type': 'customer.subscription.updated',
            'data': {'object': event.data.object}
        })
        result = self.handler.handle_event(payload, self.sig_header)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['subscription_id'], 'sub_123')
        
    @patch('stripe.Webhook.construct_event')
    def test_handle_subscription_deleted(self, mock_construct_event):
        """Test handling of subscription deletion"""
        event = MagicMock()
        event.type = 'customer.subscription.deleted'
        event.data = MagicMock()
        event.data.object = {
            'id': 'sub_123',
            'customer': 'cus_123',
            'status': 'canceled',
            'current_period_end': 1234567890,
            'metadata': {
                'user_id': 'user_123',
                'plan_type': 'premium'
            }
        }
        mock_construct_event.return_value = event
        
        # Mock successful service calls
        self.handler.subscription_service.update_subscription.return_value = True
        self.handler.subscription_service.db.add_subscription_history.return_value = True
        
        payload = json.dumps({
            'type': 'customer.subscription.deleted',
            'data': {'object': event.data.object}
        })
        result = self.handler.handle_event(payload, self.sig_header)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['subscription_id'], 'sub_123')
        
    @patch('stripe.Webhook.construct_event')
    def test_handle_invoice_payment_succeeded(self, mock_construct_event):
        """Test handling of successful invoice payment"""
        event = MagicMock()
        event.type = 'invoice.payment_succeeded'
        event.data = MagicMock()
        event.data.object = {
            'id': 'in_123',
            'amount_paid': 2000,
            'metadata': {
                'user_id': 'user_123',
                'plan_type': 'premium'
            }
        }
        mock_construct_event.return_value = event
        
        # Mock successful service calls
        self.handler.subscription_service.db.add_subscription_history.return_value = True
        
        payload = json.dumps({
            'type': 'invoice.payment_succeeded',
            'data': {'object': event.data.object}
        })
        result = self.handler.handle_event(payload, self.sig_header)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['invoice_id'], 'in_123')
        
    @patch('stripe.Webhook.construct_event')
    def test_handle_invoice_payment_failed(self, mock_construct_event):
        """Test handling of failed invoice payment"""
        event = MagicMock()
        event.type = 'invoice.payment_failed'
        event.data = MagicMock()
        event.data.object = {
            'id': 'in_123',
            'amount_due': 2000,
            'metadata': {
                'user_id': 'user_123',
                'plan_type': 'premium'
            }
        }
        mock_construct_event.return_value = event
        
        # Mock successful service calls
        self.handler.subscription_service.db.add_subscription_history.return_value = True
        
        payload = json.dumps({
            'type': 'invoice.payment_failed',
            'data': {'object': event.data.object}
        })
        result = self.handler.handle_event(payload, self.sig_header)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['invoice_id'], 'in_123')
        
    @patch('stripe.Webhook.construct_event')
    def test_handle_unhandled_event(self, mock_construct_event):
        """Test handling of unhandled event type"""
        event = MagicMock()
        event.type = 'unhandled.event.type'
        event.data = MagicMock()
        event.data.object = {}
        mock_construct_event.return_value = event
        
        payload = json.dumps({
            'type': 'unhandled.event.type',
            'data': {'object': {}}
        })
        result = self.handler.handle_event(payload, self.sig_header)
        
        self.assertEqual(result['status'], 'unhandled')
        self.assertEqual(result['type'], 'unhandled.event.type')

if __name__ == '__main__':
    unittest.main() 