import streamlit as st
from modules.services.payment_service import PaymentService
from modules.services.subscription_service import SubscriptionService
import os
from datetime import datetime
from modules.ui.theme.theme_manager import ThemeManager
from modules.ui.branding import BrandingComponent

# Set page config must be the first Streamlit command
st.set_page_config(
    page_title="Subscription Management",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply theme styles
ThemeManager.apply_theme_styles()

def create_checkout_session_with_promo(payment_service, price_id, customer_id, promo_code=None):
    """Helper function to create checkout session with optional promo code"""
    session_params = {
        'price_id': price_id,
        'customer_id': customer_id,
    }
    if promo_code:
        session_params['promotion_code'] = promo_code
    return payment_service.create_checkout_session(**session_params)

def render_subscription_page():
    st.title("Subscription Management")
    
    # Initialize services
    payment_service = PaymentService()
    subscription_service = SubscriptionService()
    
    # Get current user's subscription status
    if st.session_state.user and st.session_state.uid:
        user = st.session_state.user
        user_id = st.session_state.uid
        customer_id = user.get('stripe_customer_id')
        
        # Get current plan
        current_plan = subscription_service.get_user_plan(user_id)
        
        # Display current plan status
        st.header("Current Plan")
        
        # Handle admin users
        if current_plan.get('is_admin'):
            st.success("🔑 Admin Account - Full Access")
            st.info("As an admin, you have access to all premium features.")
            return  # Stop here for admin users
            
        if current_plan['plan'] == 'free':
            st.info("You are currently on the Free plan")
        else:
            st.success(f"✅ You are currently subscribed to the {current_plan['plan'].title()} plan")
            if customer_id:
                subscriptions = payment_service.get_customer_subscriptions(customer_id)
                active_subscription = next((sub for sub in subscriptions.data if sub.status == 'active'), None)
                if active_subscription:
                    st.write(f"Next billing date: {datetime.fromtimestamp(active_subscription.current_period_end).strftime('%B %d, %Y')}")
                    
                    # Use a form for the cancel button to handle the state properly
                    with st.form("cancel_subscription_form"):
                        if st.form_submit_button("Cancel Subscription"):
                            if payment_service.cancel_subscription(active_subscription.id):
                                st.success("Subscription cancelled successfully")
                                # Update the current plan to free
                                subscription_service.update_subscription(
                                    user_id=user_id,
                                    plan='free',
                                    stripe_data={'status': 'canceled'}
                                )
                                # Force a page refresh
                                st.experimental_rerun()
                            else:
                                st.error("Failed to cancel subscription")
    else:
        st.warning("Please log in to access subscription features")
        st.stop()
        
    # Only show plan comparison for non-admin users
    if not current_plan.get('is_admin'):
        # Display plan comparison
        st.header("Available Plans")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Free Plan")
            st.write("$0/month")
            st.write("✅ Up to 25 cards in collection")
            st.write("✅ Up to 3 display cases")
            st.write("✅ 5 searches per day")
            st.write("✅ Basic card analysis")
            st.write("✅ Price tracking")
            st.write("❌ Advanced analytics")
            st.write("❌ Priority support")
            
            if current_plan['plan'] == 'free':
                st.success("Current Plan")
        
        with col2:
            st.subheader("Basic Plan")
            st.write("$9.99/month")
            st.write("✅ Up to 50 cards in collection")
            st.write("✅ Up to 5 display cases")
            st.write("✅ Unlimited searches")
            st.write("✅ Basic card analysis")
            st.write("✅ Price tracking")
            st.write("✅ Market insights")
            st.write("❌ Advanced analytics")
            st.write("❌ Priority support")
            
            if current_plan['plan'] != 'premium':
                # Create a form for basic plan upgrade with promo code
                with st.form(key="basic_plan_form"):
                    promo_code_basic = st.text_input("Promo Code (Optional)", key="promo_basic")
                    if st.form_submit_button("Upgrade to Basic"):
                        if not customer_id:
                            # Create Stripe customer
                            customer = payment_service.create_customer(
                                email=user['email'],
                                name=user.get('display_name', '')
                            )
                            customer_id = customer.id
                        
                        try:
                            # Create checkout session with promo code if provided
                            session = create_checkout_session_with_promo(
                                payment_service,
                                os.getenv('STRIPE_BASIC_PLAN_PRICE_ID'),
                                customer_id,
                                promo_code_basic if promo_code_basic else None
                            )
                            st.markdown(f'<a href="{session.url}" target="_blank">Complete Payment</a>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        
        with col3:
            st.subheader("Premium Plan")
            st.write("$19.99/month")
            st.write("✅ Unlimited cards in collection")
            st.write("✅ Unlimited display cases")
            st.write("✅ Unlimited searches")
            st.write("✅ All Basic features")
            st.write("✅ Advanced analytics")
            st.write("✅ Priority support")
            st.write("✅ Bulk card analysis")
            st.write("✅ Custom reports")
            
            if current_plan['plan'] != 'premium':
                # Create a form for premium plan upgrade with promo code
                with st.form(key="premium_plan_form"):
                    promo_code_premium = st.text_input("Promo Code (Optional)", key="promo_premium")
                    if st.form_submit_button("Upgrade to Premium"):
                        if not customer_id:
                            # Create Stripe customer
                            customer = payment_service.create_customer(
                                email=user['email'],
                                name=user.get('display_name', '')
                            )
                            customer_id = customer.id
                        
                        try:
                            # Create checkout session with promo code if provided
                            session = create_checkout_session_with_promo(
                                payment_service,
                                os.getenv('STRIPE_PREMIUM_PLAN_PRICE_ID'),
                                customer_id,
                                promo_code_premium if promo_code_premium else None
                            )
                            st.markdown(f'<a href="{session.url}" target="_blank">Complete Payment</a>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        
        # Payment History
        st.header("Payment History")
        if customer_id:
            # Get payment history
            # TODO: Implement payment history display
            st.info("Payment history will be displayed here")
        else:
            st.warning("No payment history available")

def main():
    # Initialize session state for user if not exists
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'uid' not in st.session_state:
        st.session_state.uid = None
    
    # Check if user is properly logged in
    if not st.session_state.user or not st.session_state.uid:
        st.warning("Please log in to access subscription features")
        # Add a login button
        if st.button("Go to Login Page"):
            st.switch_page("pages/0_login.py")
        st.stop()
    
    # Sidebar
    with st.sidebar:
        # Sidebar header with branding
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        BrandingComponent.display_horizontal_logo()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Navigation
        st.page_link("app.py", label="Home", icon="🏠")
        st.page_link("pages/1_market_analysis.py", label="Market Analysis", icon="📊")
        st.page_link("pages/4_display_case.py", label="Display Case", icon="🖼️")
        st.page_link("pages/3_collection_manager.py", label="Collection Manager", icon="📋")
        st.page_link("pages/2_trade_analyzer.py", label="Trade Analyzer", icon="🔄")
        st.page_link("pages/subscription_7.py", label="Subscription", icon="💎")
        st.page_link("pages/6_profile_management.py", label="Profile", icon="👤")
        
        # Logout button
        if st.button("Logout", type="primary"):
            st.session_state.user = None
            st.session_state.uid = None
            st.switch_page("pages/0_login.py")
    
    # Render the subscription page
    render_subscription_page()

if __name__ == "__main__":
    main() 