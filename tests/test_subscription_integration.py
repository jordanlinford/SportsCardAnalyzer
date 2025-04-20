import unittest
from unittest.mock import MagicMock, patch
import json
import stripe
import os
from datetime import datetime, timedelta
from modules.services.webhook_handler import WebhookHandler
from modules.services.payment_service import PaymentService
from modules.services.subscription_service import SubscriptionService

class TestSubscriptionIntegration(unittest.TestCase):
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
        self.test_user_id = 'user_123'
        self.test_customer_id = 'cus_123'
        self.test_subscription_id = 'sub_123'
        self.sig_header = 'test_signature'
        
        # Mock Stripe customer
        self.mock_customer = MagicMock()
        self.mock_customer.id = self.test_customer_id
        self.mock_customer.metadata = {'user_id': self.test_user_id}
        
        # Mock Stripe subscription
        self.mock_subscription = MagicMock()
        self.mock_subscription.id = self.test_subscription_id
        self.mock_subscription.customer = self.test_customer_id
        self.mock_subscription.status = 'active'
        self.mock_subscription.current_period_end = int((datetime.now() + timedelta(days=30)).timestamp())
        self.mock_subscription.metadata = {'plan_type': 'basic'}
        self.mock_subscription.items.data = [MagicMock()]
        self.mock_subscription.items.data[0].price.id = 'price_basic_123'
        self.mock_subscription.items.data[0].price.unit_amount = 1000  # $10.00
        
    def tearDown(self):
        self.env_patcher.stop()

    @patch('stripe.Customer.create')
    @patch('stripe.checkout.Session.create')
    @patch('stripe.Webhook.construct_event')
    def test_complete_subscription_flow(self, mock_construct_event, mock_session_create, mock_customer_create):
        """Test the complete subscription flow from customer creation to active subscription"""
        # Mock customer creation
        mock_customer_create.return_value = self.mock_customer
        
        # Mock checkout session creation
        mock_session = MagicMock()
        mock_session.id = 'sess_123'
        mock_session.url = 'https://checkout.stripe.com/test'
        mock_session_create.return_value = mock_session
        
        # Mock payment service methods
        self.handler.payment_service.create_customer.return_value = self.mock_customer
        self.handler.payment_service.create_checkout_session.return_value = mock_session
        
        # Create customer
        customer = self.handler.payment_service.create_customer(
            email='test@example.com',
            user_id=self.test_user_id
        )
        self.assertEqual(customer.id, self.test_customer_id)
        
        # Create checkout session
        session = self.handler.payment_service.create_checkout_session(
            customer_id=self.test_customer_id,
            price_id='price_basic_123',
            success_url='https://example.com/success',
            cancel_url='https://example.com/cancel'
        )
        self.assertEqual(session.id, 'sess_123')
        
        # Mock webhook event for successful checkout
        event = MagicMock()
        event.type = 'checkout.session.completed'
        event.data = MagicMock()
        event.data.object = {
            'id': 'sess_123',
            'customer': self.test_customer_id,
            'subscription': self.test_subscription_id,
            'client_reference_id': self.test_user_id
        }
        mock_construct_event.return_value = event
        
        # Mock subscription retrieval
        with patch('stripe.Subscription.retrieve') as mock_sub_retrieve:
            mock_sub_retrieve.return_value = self.mock_subscription
            
            # Process webhook
            payload = json.dumps({
                'type': 'checkout.session.completed',
                'data': {'object': event.data.object}
            })
            result = self.handler.handle_event(payload, self.sig_header)
            
            # Verify webhook processing
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['subscription_id'], self.test_subscription_id)
            
            # Verify subscription was updated in database
            self.handler.subscription_service.update_subscription.assert_called_once()
            call_kwargs = self.handler.subscription_service.update_subscription.call_args.kwargs
            self.assertEqual(call_kwargs['user_id'], self.test_user_id)
            self.assertEqual(call_kwargs['plan'], 'basic')
            
            # Verify subscription history was recorded
            self.handler.subscription_service.db.add_subscription_history.assert_called_once()

    @patch('stripe.Subscription.modify')
    @patch('stripe.Webhook.construct_event')
    def test_plan_upgrade_flow(self, mock_construct_event, mock_sub_modify):
        """Test upgrading from basic to premium plan"""
        # Mock subscription modification
        self.mock_subscription.items.data[0].price.id = 'price_premium_456'
        self.mock_subscription.items.data[0].price.unit_amount = 2000  # $20.00
        self.mock_subscription.metadata = {'plan_type': 'premium'}
        mock_sub_modify.return_value = self.mock_subscription
        
        # Mock webhook event for subscription update
        event = MagicMock()
        event.type = 'customer.subscription.updated'
        event.data = MagicMock()
        event.data.object = {
            'id': self.test_subscription_id,
            'customer': self.test_customer_id,
            'status': 'active',
            'current_period_end': int((datetime.now() + timedelta(days=30)).timestamp()),
            'metadata': {
                'user_id': self.test_user_id,
                'plan_type': 'premium'
            },
            'items': {
                'data': [{
                    'price': {
                        'id': 'price_premium_456',
                        'unit_amount': 2000
                    }
                }]
            }
        }
        mock_construct_event.return_value = event
        
        # Mock subscription service
        self.handler.subscription_service.update_subscription.return_value = True
        
        # Process webhook
        payload = json.dumps({
            'type': 'customer.subscription.updated',
            'data': {'object': event.data.object}
        })
        result = self.handler.handle_event(payload, self.sig_header)
        
        # Verify webhook processing
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['subscription_id'], self.test_subscription_id)
        
        # Verify subscription was updated in database
        self.handler.subscription_service.update_subscription.assert_called_once()
        call_kwargs = self.handler.subscription_service.update_subscription.call_args.kwargs
        self.assertEqual(call_kwargs['user_id'], self.test_user_id)
        self.assertEqual(call_kwargs['plan'], 'premium')

    @patch('stripe.Subscription.delete')
    @patch('stripe.Webhook.construct_event')
    def test_subscription_cancellation_flow(self, mock_construct_event, mock_sub_delete):
        """Test subscription cancellation flow"""
        # Mock subscription deletion
        self.mock_subscription.status = 'canceled'
        mock_sub_delete.return_value = self.mock_subscription
        
        # Mock webhook event for subscription deletion
        event = MagicMock()
        event.type = 'customer.subscription.deleted'
        event.data = MagicMock()
        event.data.object = {
            'id': self.test_subscription_id,
            'customer': self.test_customer_id,
            'status': 'canceled',
            'metadata': {
                'user_id': self.test_user_id,
                'plan_type': 'basic'
            }
        }
        mock_construct_event.return_value = event
        
        # Mock subscription service
        self.handler.subscription_service.update_subscription.return_value = True
        
        # Process webhook
        payload = json.dumps({
            'type': 'customer.subscription.deleted',
            'data': {'object': event.data.object}
        })
        result = self.handler.handle_event(payload, self.sig_header)
        
        # Verify webhook processing
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['subscription_id'], self.test_subscription_id)
        
        # Verify subscription was updated to free plan in database
        self.handler.subscription_service.update_subscription.assert_called_once()
        call_kwargs = self.handler.subscription_service.update_subscription.call_args.kwargs
        self.assertEqual(call_kwargs['user_id'], self.test_user_id)
        self.assertEqual(call_kwargs['plan'], 'free')

    @patch('stripe.Invoice.retrieve')
    @patch('stripe.Webhook.construct_event')
    def test_payment_processing_flow(self, mock_construct_event, mock_invoice_retrieve):
        """Test payment processing flow"""
        # Mock invoice
        mock_invoice = MagicMock()
        mock_invoice.id = 'in_123'
        mock_invoice.amount_paid = 1000  # $10.00
        mock_invoice.customer = self.test_customer_id
        mock_invoice.subscription = self.test_subscription_id
        mock_invoice.metadata = {
            'user_id': self.test_user_id,
            'plan_type': 'basic'
        }
        mock_invoice_retrieve.return_value = mock_invoice
        
        # Mock webhook event for successful payment
        event = MagicMock()
        event.type = 'invoice.payment_succeeded'
        event.data = MagicMock()
        event.data.object = {
            'id': 'in_123',
            'amount_paid': 1000,
            'customer': self.test_customer_id,
            'subscription': self.test_subscription_id,
            'metadata': {
                'user_id': self.test_user_id,
                'plan_type': 'basic'
            }
        }
        mock_construct_event.return_value = event
        
        # Mock subscription service
        self.handler.subscription_service.db.add_subscription_history.return_value = True
        
        # Process webhook
        payload = json.dumps({
            'type': 'invoice.payment_succeeded',
            'data': {'object': event.data.object}
        })
        result = self.handler.handle_event(payload, self.sig_header)
        
        # Verify webhook processing
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['invoice_id'], 'in_123')
        
        # Verify payment was recorded in history
        self.handler.subscription_service.db.add_subscription_history.assert_called_once()
        history_call = self.handler.subscription_service.db.add_subscription_history.call_args[0][0]
        self.assertEqual(history_call.user_id, self.test_user_id)
        self.assertEqual(history_call.amount, 10.00)  # Converted from cents
        self.assertEqual(history_call.event_type, 'payment_succeeded')

if __name__ == '__main__':
    unittest.main() 