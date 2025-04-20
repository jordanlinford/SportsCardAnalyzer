from typing import Dict, Optional
import stripe
from datetime import datetime
import logging
from modules.core.firebase_manager import FirebaseManager

logger = logging.getLogger(__name__)

class SubscriptionService:
    """Service for handling subscription operations."""
    
    def __init__(self):
        """Initialize the subscription service."""
        self._db = FirebaseManager().get_firestore_client()
        self._stripe = stripe
        self._stripe.api_key = "sk_test_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # Replace with your Stripe secret key
        
    def get_subscription(self, uid: str) -> Optional[Dict]:
        """
        Get user's subscription data.
        
        Args:
            uid (str): User ID
            
        Returns:
            Optional[Dict]: Subscription data
        """
        try:
            doc = self._db.collection('users').document(uid).get()
            if doc.exists:
                data = doc.to_dict()
                return data.get('subscription')
            return None
        except Exception as e:
            logger.error(f"Error getting subscription: {str(e)}")
            return None
            
    def update_subscription(self, uid: str, subscription_data: Dict) -> bool:
        """
        Update user's subscription data.
        
        Args:
            uid (str): User ID
            subscription_data (Dict): Subscription data to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert current_period_end to datetime if it's a timestamp
            if 'current_period_end' in subscription_data:
                try:
                    if isinstance(subscription_data['current_period_end'], (int, float)):
                        subscription_data['current_period_end'] = datetime.fromtimestamp(
                            subscription_data['current_period_end']
                        )
                except Exception as e:
                    logger.warning(f"Error converting current_period_end: {str(e)}")
                    subscription_data['current_period_end'] = None
                    
            self._db.collection('users').document(uid).set({
                'subscription': subscription_data
            }, merge=True)
            return True
        except Exception as e:
            logger.error(f"Error updating subscription: {str(e)}")
            return False
            
    def create_checkout_session(self, price_id: str, success_url: str, cancel_url: str) -> Optional[str]:
        """
        Create a Stripe checkout session.
        
        Args:
            price_id (str): Stripe price ID
            success_url (str): Success URL after checkout
            cancel_url (str): Cancel URL after checkout
            
        Returns:
            Optional[str]: Checkout session URL if successful, None otherwise
        """
        try:
            session = self._stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return session.url
        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            return None
            
    def cancel_subscription(self, subscription_id: str) -> bool:
        """
        Cancel a Stripe subscription.
        
        Args:
            subscription_id (str): Stripe subscription ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._stripe.Subscription.delete(subscription_id)
            return True
        except Exception as e:
            logger.error(f"Error canceling subscription: {str(e)}")
            return False
            
    def handle_webhook(self, payload: bytes, sig_header: str) -> Dict:
        """
        Handle Stripe webhook events.
        
        Args:
            payload (bytes): Webhook payload
            sig_header (str): Stripe signature header
            
        Returns:
            Dict: Response data
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, FirebaseManager.get_stripe_webhook_secret()
            )
            
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                uid = session['customer']
                subscription = stripe.Subscription.retrieve(session['subscription'])
                
                self.update_subscription(uid, {
                    'stripe_subscription_id': subscription.id,
                    'status': subscription.status,
                    'current_period_end': subscription.current_period_end,
                    'plan': subscription.plan.id
                })
                
            elif event['type'] == 'customer.subscription.updated':
                subscription = event['data']['object']
                uid = subscription['customer']
                
                self.update_subscription(uid, {
                    'status': subscription.status,
                    'current_period_end': subscription.current_period_end
                })
                
            elif event['type'] == 'customer.subscription.deleted':
                subscription = event['data']['object']
                uid = subscription['customer']
                
                self.update_subscription(uid, {
                    'status': 'canceled',
                    'canceled_at': int(datetime.now().timestamp())
                })
                
            return {'status': 'success'}
        except Exception as e:
            logger.error(f"Error handling webhook: {str(e)}")
            return {'status': 'error', 'message': str(e)} 