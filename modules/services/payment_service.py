import stripe
import os
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta, timezone
from modules.core.models import UserSubscription, UserUsage, SubscriptionHistory
from modules.core.firebase_manager import FirebaseManager
import logging

class PaymentService:
    def __init__(self):
        self.stripe = stripe
        self.stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        self.db = FirebaseManager.get_instance()
        self.logger = logging.getLogger(__name__)
        
    def create_customer(self, user_id: str, email: str, name: str = "") -> stripe.Customer:
        """Create a new Stripe customer"""
        try:
            # For test users, use a valid test email format
            if user_id.startswith('test_'):
                email = f"test_{user_id}@example.com"
            
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={
                    'user_id': user_id
                }
            )
            return customer
        except Exception as e:
            self.logger.error(f"Error creating customer: {str(e)}")
            raise
    
    def create_subscription(self, customer_id: str, price_id: str) -> stripe.Subscription:
        """Create a new subscription"""
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price_id}],
                payment_behavior='default_incomplete',
                payment_settings={'save_default_payment_method': 'on_subscription'},
                expand=['latest_invoice.payment_intent']
            )
            return subscription
        except Exception as e:
            self.logger.error(f"Error creating subscription: {str(e)}")
            raise
    
    def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            subscription.delete()
            return True
        except Exception as e:
            self.logger.error(f"Error cancelling subscription: {str(e)}")
            return False
    
    def get_subscription(self, subscription_id: str) -> Optional[stripe.Subscription]:
        """Get subscription details"""
        try:
            return stripe.Subscription.retrieve(subscription_id)
        except Exception as e:
            self.logger.error(f"Error getting subscription: {str(e)}")
            return None
    
    def create_checkout_session(self, user_id: str, plan: str) -> stripe.checkout.Session:
        """Create a Stripe checkout session"""
        try:
            # For test users, use a valid test email format
            if user_id.startswith('test_'):
                email = f"test_{user_id}@example.com"
            else:
                email = None  # Will be set by Stripe based on customer

            price_id = os.getenv(f'STRIPE_{plan.upper()}_PLAN_PRICE_ID')
            if not price_id:
                raise ValueError(f"Price ID not found for plan: {plan}")

            session = stripe.checkout.Session.create(
                customer_email=email,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=os.getenv('STRIPE_SUCCESS_URL', 'https://sportscardanalyzer.streamlit.app/subscription?success=true'),
                cancel_url=os.getenv('STRIPE_CANCEL_URL', 'https://sportscardanalyzer.streamlit.app/subscription?canceled=true'),
                metadata={
                    'user_id': user_id,
                    'plan': plan
                }
            )
            return session
        except Exception as e:
            self.logger.error(f"Error creating checkout session: {str(e)}")
            raise

    def verify_payment(self, session_id: str) -> bool:
        """Verify if a payment was successful"""
        session = self.stripe.checkout.Session.retrieve(session_id)
        return session.payment_status == 'paid'
    
    def get_customer_subscriptions(self, customer_id: str) -> Dict:
        """Get all subscriptions for a customer"""
        return self.stripe.Subscription.list(
            customer=customer_id,
            status='all'
        )
    
    def update_subscription(self, user_id: str, subscription_data: Dict[str, Any]) -> None:
        """Update user subscription with Stripe webhook data"""
        current_period_end = self._convert_timestamp_to_datetime(
            subscription_data.get('current_period_end', 0)
        )
        
        subscription_data = {
            'user_id': user_id,
            'plan': subscription_data.get('plan', 'free'),
            'stripe_customer_id': subscription_data.get('customer'),
            'stripe_subscription_id': subscription_data.get('subscription'),
            'subscription_status': subscription_data.get('status', 'active'),
            'current_period_end': current_period_end,
            'updated_at': datetime.now(timezone.utc)
        }
        
        self.db.collection('subscriptions').document(user_id).set(subscription_data)

        # Record subscription history
        history_data = {
            'user_id': user_id,
            'event_type': 'subscription_updated',
            'plan': subscription_data['plan'],
            'amount': subscription_data.get('amount', 0.0),
            'status': subscription_data['subscription_status'],
            'event_time': datetime.now(timezone.utc),
            'metadata': subscription_data
        }
        self.db.collection('subscription_history').add(history_data)

    def check_search_limit(self, user_id: str) -> bool:
        """Check if user has exceeded their daily search limit"""
        usage_doc = self.db.collection('usage').document(user_id).get()
        if not usage_doc.exists:
            return True

        usage = usage_doc.to_dict()
        now = datetime.now(timezone.utc)
        last_updated = usage['last_updated'].replace(tzinfo=timezone.utc)
        
        # Reset count if last update was yesterday
        if last_updated.date() < now.date():
            usage['daily_search_count'] = 0
            usage['last_updated'] = now
            self.db.collection('usage').document(user_id).set(usage)
            return True

        subscription_doc = self.db.collection('subscriptions').document(user_id).get()
        plan = subscription_doc.get('plan') if subscription_doc.exists else 'free'
        limit = self._get_search_limit(plan)
        return usage['daily_search_count'] < limit

    def _get_search_limit(self, plan: str) -> int:
        """Get daily search limit based on subscription plan"""
        limits = {
            'free': 10,
            'basic': 50,
            'premium': 200
        }
        return limits.get(plan, 10)
    
    def get_payment_methods(self, customer_id: str) -> Dict:
        """Get all payment methods for a customer"""
        return self.stripe.PaymentMethod.list(
            customer=customer_id,
            type='card'
        )
    
    def create_payment_intent(self, amount: int, currency: str, customer_id: str) -> Dict:
        """Create a payment intent for one-time payments"""
        return self.stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            customer=customer_id,
            automatic_payment_methods={
                'enabled': True,
            },
        )

    def _convert_timestamp_to_datetime(self, timestamp: int) -> datetime:
        """Convert Unix timestamp to UTC aware datetime"""
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    def validate_promo_code(self, code: str) -> Dict:
        """Validate a promotion code and return its details"""
        try:
            promo_codes = self.stripe.PromotionCode.list(code=code, active=True)
            if not promo_codes.data:
                raise ValueError("Promotion code not found or inactive")
            return promo_codes.data[0]
        except Exception as e:
            self.logger.error(f"Error validating promo code: {str(e)}")
            raise

    def list_payments(self, customer_id: str) -> List[Dict]:
        """List customer's payment history"""
        try:
            charges = stripe.Charge.list(customer=customer_id)
            return [{
                'amount': charge.amount / 100,  # Convert from cents to dollars
                'currency': charge.currency,
                'status': charge.status,
                'created': datetime.fromtimestamp(charge.created)
            } for charge in charges]
        except Exception as e:
            self.logger.error(f"Error listing payments: {str(e)}")
            return [] 