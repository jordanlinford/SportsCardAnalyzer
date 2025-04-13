import stripe
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from modules.services.payment_service import PaymentService
from modules.services.subscription_service import SubscriptionService
from modules.database.schema import SubscriptionHistory

class WebhookHandler:
    def __init__(self):
        self.stripe = stripe
        self.stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        self.payment_service = PaymentService()
        self.subscription_service = SubscriptionService()
        
    def handle_event(self, payload: str, sig_header: str) -> Dict[str, Any]:
        """Handle incoming Stripe webhook events"""
        try:
            # First try to parse the JSON payload
            event_data = json.loads(payload)
        except json.JSONDecodeError:
            return {'status': 'error', 'error': 'Invalid payload'}

        try:
            # Then verify the signature
            payload_bytes = payload.encode('utf-8')
            event = self.stripe.Webhook.construct_event(
                payload_bytes, sig_header, self.webhook_secret
            )
        except stripe.error.SignatureVerificationError:
            return {'status': 'error', 'error': 'Invalid signature'}
        except Exception:
            return {'status': 'error', 'error': 'Invalid payload'}

        event_handlers = {
            'checkout.session.completed': self._handle_checkout_session_completed,
            'customer.subscription.updated': self._handle_subscription_updated,
            'customer.subscription.deleted': self._handle_subscription_deleted,
            'invoice.payment_succeeded': self._handle_invoice_payment_succeeded,
            'invoice.payment_failed': self._handle_invoice_payment_failed
        }

        handler = event_handlers.get(event.type)
        if handler:
            return handler(event.data.object)
        return {'status': 'unhandled', 'type': event.type}

    def _handle_checkout_session_completed(self, session: Dict) -> Dict[str, Any]:
        """Handle successful checkout session"""
        try:
            # Validate required fields
            client_reference_id = session.get('client_reference_id')
            subscription_id = session.get('subscription')
            
            if not client_reference_id:
                return {'status': 'error', 'message': 'Missing client_reference_id in checkout session'}
                
            if not subscription_id:
                return {'status': 'error', 'message': 'Missing subscription in checkout session'}
            
            # Get the subscription
            subscription = self.stripe.Subscription.retrieve(subscription_id)
            
            # Get the plan type from metadata
            plan_type = subscription.metadata.get('plan_type', 'basic')
            
            # Update user's subscription status
            self.subscription_service.update_subscription(
                user_id=client_reference_id,
                plan=plan_type,
                stripe_data={
                    'customer': subscription.customer,
                    'subscription': subscription.id,
                    'status': subscription.status,
                    'current_period_end': subscription.current_period_end
                }
            )
            
            # Add to subscription history
            history = SubscriptionHistory(
                user_id=client_reference_id,
                event_type='subscription_created',
                plan=plan_type,
                amount=subscription.items.data[0].price.unit_amount / 100,
                status=subscription.status
            )
            self.subscription_service.db.add_subscription_history(history)
            
            return {
                'status': 'success',
                'message': 'Checkout session completed successfully',
                'subscription_id': subscription.id
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _handle_subscription_updated(self, subscription: Dict) -> Dict[str, Any]:
        """Handle subscription updates"""
        try:
            # Get the plan type from metadata
            plan_type = subscription.get('metadata', {}).get('plan_type', 'basic')
            user_id = subscription.get('metadata', {}).get('user_id')
            
            if not user_id:
                return {'status': 'error', 'message': 'Missing user_id in metadata'}
            
            # Update user's subscription status
            self.subscription_service.update_subscription(
                user_id=user_id,
                plan=plan_type,
                stripe_data={
                    'customer': subscription.get('customer'),
                    'subscription': subscription.get('id'),
                    'status': subscription.get('status'),
                    'current_period_end': subscription.get('current_period_end')
                }
            )
            
            # Add to subscription history
            history = SubscriptionHistory(
                user_id=user_id,
                event_type='subscription_updated',
                plan=plan_type,
                amount=subscription.get('items', {}).get('data', [{}])[0].get('price', {}).get('unit_amount', 0) / 100,
                status=subscription.get('status')
            )
            self.subscription_service.db.add_subscription_history(history)
            
            return {
                'status': 'success',
                'message': 'Subscription updated successfully',
                'subscription_id': subscription.get('id')
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
            
    def _handle_subscription_deleted(self, subscription: Dict) -> Dict[str, Any]:
        """Handle subscription cancellations"""
        try:
            user_id = subscription.get('metadata', {}).get('user_id')
            
            if not user_id:
                return {'status': 'error', 'message': 'Missing user_id in metadata'}
            
            # Update user's subscription status
            self.subscription_service.update_subscription(
                user_id=user_id,
                plan='free',  # Revert to free plan
                stripe_data={
                    'customer': subscription.get('customer'),
                    'subscription': subscription.get('id'),
                    'status': 'canceled',
                    'current_period_end': subscription.get('current_period_end')
                }
            )
            
            # Add to subscription history
            history = SubscriptionHistory(
                user_id=user_id,
                event_type='subscription_canceled',
                plan='free',
                amount=0,
                status='canceled'
            )
            self.subscription_service.db.add_subscription_history(history)
            
            return {
                'status': 'success',
                'message': 'Subscription cancelled successfully',
                'subscription_id': subscription.get('id')
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
            
    def _handle_invoice_payment_succeeded(self, invoice: Dict) -> Dict[str, Any]:
        """Handle successful invoice payments"""
        try:
            user_id = invoice.get('metadata', {}).get('user_id')
            
            if not user_id:
                return {'status': 'error', 'message': 'Missing user_id in metadata'}
            
            # Add to subscription history
            history = SubscriptionHistory(
                user_id=user_id,
                event_type='payment_succeeded',
                plan=invoice.get('metadata', {}).get('plan_type', 'basic'),
                amount=invoice.get('amount_paid', 0) / 100,
                status='paid'
            )
            self.subscription_service.db.add_subscription_history(history)
            
            return {
                'status': 'success',
                'message': 'Invoice payment processed successfully',
                'invoice_id': invoice.get('id')
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
            
    def _handle_invoice_payment_failed(self, invoice: Dict) -> Dict[str, Any]:
        """Handle failed invoice payments"""
        try:
            user_id = invoice.get('metadata', {}).get('user_id')
            
            if not user_id:
                return {'status': 'error', 'message': 'Missing user_id in metadata'}
            
            # Add to subscription history
            history = SubscriptionHistory(
                user_id=user_id,
                event_type='payment_failed',
                plan=invoice.get('metadata', {}).get('plan_type', 'basic'),
                amount=invoice.get('amount_due', 0) / 100,
                status='failed'
            )
            self.subscription_service.db.add_subscription_history(history)
            
            return {
                'status': 'success',
                'message': 'Invoice payment failure processed',
                'invoice_id': invoice.get('id')
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _get_plan_from_price(self, price_id: Optional[str]) -> str:
        """Get plan name from Stripe price ID"""
        if not price_id:
            return 'free'
        price_to_plan = {
            os.getenv('STRIPE_BASIC_PRICE_ID'): 'basic',
            os.getenv('STRIPE_PREMIUM_PRICE_ID'): 'premium'
        }
        return price_to_plan.get(price_id, 'free')

    def _get_user_id_from_customer(self, customer_id: str) -> str:
        """Get user ID from Stripe customer ID"""
        customer = self.stripe.Customer.retrieve(customer_id)
        return customer.get('metadata', {}).get('user_id', '') 