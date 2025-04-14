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
    """Render the subscription management page"""
    try:
        # Initialize session state if needed
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'uid' not in st.session_state:
            st.session_state.uid = None

        # Check if user is logged in
        if not st.session_state.user or not st.session_state.uid:
            st.warning("Please log in to manage your subscription")
            return

        # Initialize services
        subscription_service = SubscriptionService()
        payment_service = PaymentService()

        # Get user's current plan
        plan = subscription_service.get_user_plan(st.session_state.uid)
        usage_stats = subscription_service.get_usage_stats(st.session_state.uid)

        # Display current plan and usage
        st.header("Your Subscription")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Current Plan")
            st.write(f"Plan: {plan['plan'].capitalize()}")
            if plan['plan'] != 'free':
                st.write(f"Status: {plan.get('status', 'active')}")
                if 'current_period_end' in plan:
                    end_date = datetime.fromtimestamp(plan['current_period_end'])
                    st.write(f"Renews on: {end_date.strftime('%B %d, %Y')}")

        with col2:
            st.subheader("Usage")
            st.write(f"Cards: {usage_stats['card_count']}/{plan['limits']['card_limit']}")
            st.write(f"Display Cases: {usage_stats['display_case_count']}/{plan['limits']['display_case_limit']}")
            st.write(f"Daily Searches: {usage_stats['daily_search_count']}/{plan['limits']['daily_search_limit']}")

        # Display available features
        st.subheader("Available Features")
        features = subscription_service.get_available_features(st.session_state.uid)
        for feature in features:
            st.write(f"✓ {feature.replace('_', ' ').title()}")

        # Upgrade options for free plan users
        if plan['plan'] == 'free':
            st.subheader("Upgrade Your Plan")
            st.write("Get access to more features and higher limits!")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Basic Plan**")
                st.write("- 100 cards")
                st.write("- 10 display cases")
                st.write("- 20 daily searches")
                st.write("- Advanced analysis")
                st.write("$9.99/month")
                
                if st.button("Upgrade to Basic", key="basic_upgrade"):
                    try:
                        session = payment_service.create_checkout_session(
                            user_id=st.session_state.uid,
                            plan='basic'
                        )
                        st.markdown(f"[Click here to complete your payment]({session.url})")
                    except Exception as e:
                        st.error(f"Error creating checkout session: {str(e)}")

            with col2:
                st.write("**Premium Plan**")
                st.write("- Unlimited cards")
                st.write("- Unlimited display cases")
                st.write("- Unlimited searches")
                st.write("- All features")
                st.write("$19.99/month")
                
                if st.button("Upgrade to Premium", key="premium_upgrade"):
                    try:
                        session = payment_service.create_checkout_session(
                            user_id=st.session_state.uid,
                            plan='premium'
                        )
                        st.markdown(f"[Click here to complete your payment]({session.url})")
                    except Exception as e:
                        st.error(f"Error creating checkout session: {str(e)}")

        # Manage subscription for paid plan users
        else:
            st.subheader("Manage Subscription")
            
            if st.button("Cancel Subscription"):
                try:
                    payment_service.cancel_subscription(st.session_state.uid)
                    st.success("Your subscription has been cancelled")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error cancelling subscription: {str(e)}")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.stop()

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
        st.page_link("app.py", label="Home")
        st.page_link("pages/1_market_analysis.py", label="Market Analysis")
        st.page_link("pages/4_display_case.py", label="Display Case")
        st.page_link("pages/3_collection_manager.py", label="Collection Manager")
        st.page_link("pages/2_trade_analyzer.py", label="Trade Analyzer")
        st.page_link("pages/subscription.py", label="Subscription", icon="💎")
        st.page_link("pages/6_profile_management.py", label="Profile")
        
        # Logout button
        if st.button("Logout", type="primary"):
            st.session_state.user = None
            st.session_state.uid = None
            st.switch_page("pages/0_login.py")
    
    # Render the subscription page
    render_subscription_page()

if __name__ == "__main__":
    main() 