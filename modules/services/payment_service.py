import stripe
import os
from typing import Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from modules.database.subscription_db import SubscriptionDB
from modules.database.schema import UserSubscription, UserUsage, SubscriptionHistory

class PaymentService:
    def __init__(self):
        self.stripe = stripe
        self.stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        self.db = SubscriptionDB()
        
    def create_customer(self, email: str, name: str) -> Dict:
        """Create a new Stripe customer"""
        return self.stripe.Customer.create(
            email=email,
            name=name
        )
    
    def create_subscription(self, customer_id: str, price_id: str) -> Dict:
        """Create a subscription for a customer"""
        return self.stripe.Subscription.create(
            customer=customer_id,
            items=[{'price': price_id}],
            payment_behavior='default_incomplete',
            expand=['latest_invoice.payment_intent']
        )
    
    def cancel_subscription(self, subscription_id: str) -> Dict:
        """Cancel a subscription"""
        return self.stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )
    
    def get_subscription_status(self, subscription_id: str) -> Dict:
        """Get the status of a subscription"""
        return self.stripe.Subscription.retrieve(subscription_id)
    
    def create_checkout_session(self, price_id: str, customer_id: str, promotion_code: Optional[str] = None) -> Dict:
        """Create a Stripe Checkout session with optional promo code"""
        session_params = {
            'customer': customer_id,
            'payment_method_types': ['card'],
            'line_items': [{
                'price': price_id,
                'quantity': 1,
            }],
            'mode': 'subscription',
            'success_url': os.getenv('STRIPE_SUCCESS_URL'),
            'cancel_url': os.getenv('STRIPE_CANCEL_URL'),
            'allow_promotion_codes': True,  # Enable promo code field in checkout
        }
        
        if promotion_code:
            # Validate the promotion code first
            try:
                promo = self.stripe.PromotionCode.list(code=promotion_code).data[0]
                session_params['discounts'] = [{
                    'promotion_code': promo.id
                }]
            except (IndexError, stripe.error.InvalidRequestError) as e:
                raise ValueError(f"Invalid promotion code: {promotion_code}")
        
        return self.stripe.checkout.Session.create(**session_params)

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
        
        subscription = UserSubscription(
            user_id=user_id,
            plan=subscription_data.get('plan', 'free'),
            stripe_customer_id=subscription_data.get('customer'),
            stripe_subscription_id=subscription_data.get('subscription'),
            subscription_status=subscription_data.get('status', 'active'),
            current_period_end=current_period_end,
            updated_at=datetime.now(timezone.utc)
        )
        
        self.db.update_subscription(subscription)

        # Record subscription history
        history = SubscriptionHistory(
            user_id=user_id,
            event_type='subscription_updated',
            plan=subscription.plan,
            amount=subscription_data.get('amount', 0.0),
            status=subscription.subscription_status,
            event_time=datetime.now(timezone.utc),
            metadata=subscription_data
        )
        self.db.add_subscription_history(history)

    def check_search_limit(self, user_id: str) -> bool:
        """Check if user has exceeded their daily search limit"""
        usage = self.db.get_user_usage(user_id)
        if not usage:
            return True

        now = datetime.now(timezone.utc)
        last_updated = usage.last_updated.replace(tzinfo=timezone.utc)
        
        # Reset count if last update was yesterday
        if last_updated.date() < now.date():
            usage.daily_search_count = 0
            usage.last_updated = now
            self.db.update_usage(usage)
            return True

        subscription = self.db.get_user_subscription(user_id)
        limit = self._get_search_limit(subscription.plan if subscription else 'free')
        return usage.daily_search_count < limit

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
            
            promo = promo_codes.data[0]
            coupon = promo.coupon
            
            return {
                'valid': True,
                'id': promo.id,
                'code': promo.code,
                'amount_off': coupon.amount_off,
                'percent_off': coupon.percent_off,
                'duration': coupon.duration,
                'duration_in_months': coupon.duration_in_months
            }
        except stripe.error.StripeError as e:
            raise ValueError(f"Error validating promotion code: {str(e)}") 