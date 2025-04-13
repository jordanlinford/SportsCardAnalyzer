import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys
import json
from pathlib import Path
from modules.firebase.user_management import UserManager
from modules.core.firebase_manager import FirebaseManager
from modules.ui.components import CardDisplay
from modules.ui.theme.theme_manager import ThemeManager
from modules.ui.branding import BrandingComponent

# Add the project root directory to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Set page config must be the first Streamlit command
st.set_page_config(
    page_title="Profile Management",
    page_icon="person",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply theme styles
ThemeManager.apply_theme_styles()

# Initialize session state variables
if 'user' not in st.session_state:
    st.session_state.user = None
if 'uid' not in st.session_state:
    st.session_state.uid = None

# Display branding
BrandingComponent.display_vertical_logo()

# Add custom CSS for persistent branding
st.markdown("""
    <style>
        /* Header container */
        .stApp > header {
            background-color: white;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* Sidebar container */
        .stSidebar {
            background-color: white;
            padding: 1rem;
        }
        
        /* Logo container in header */
        .stApp > header .logo-container {
            margin: 0;
            padding: 0;
        }
        
        /* Logo container in sidebar */
        .stSidebar .logo-container {
            margin-bottom: 1rem;
            padding: 0.5rem;
            border-bottom: 1px solid rgba(0,0,0,0.1);
        }
        
        /* Dark mode overrides */
        @media (prefers-color-scheme: dark) {
            .stApp > header {
                background-color: #111111;
            }
            
            .stSidebar {
                background-color: #111111;
            }
            
            .stSidebar .logo-container {
                border-bottom-color: rgba(255,255,255,0.1);
            }
        }
    </style>
""", unsafe_allow_html=True)

# Apply theme and branding styles
ThemeManager.apply_theme_styles()
BrandingComponent.add_branding_styles()

def update_user_profile(uid, profile_data):
    """Update user profile in Firebase"""
    try:
        # Update user profile in Firebase
        FirebaseManager.update_user_profile(uid, profile_data)
        return True, "Profile updated successfully!"
    except Exception as e:
        return False, f"Error updating profile: {str(e)}"

def main():
    # Initialize session state for user if not exists
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'uid' not in st.session_state:
        st.session_state.uid = None
    
    # If user is not logged in, redirect to login page
    if not st.session_state.user:
        st.switch_page("pages/0_login.py")
    
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
            st.rerun()
    
    st.title("Profile Management")
    
    # Get current user data
    user_data = st.session_state.user
    
    with ThemeManager.styled_card():
        st.subheader("Personal Information")
        
        # Create two columns for the form
        col1, col2 = st.columns(2)
        
        with col1:
            display_name = st.text_input(
                "Display Name",
                value=user_data.get('displayName', ''),
                help="This is the name that will be shown to other users"
            )
            
            email = st.text_input(
                "Email",
                value=user_data.get('email', ''),
                disabled=True,  # Email can't be changed directly
                help="Contact support to change your email address"
            )
            
            phone = st.text_input(
                "Phone Number",
                value=user_data.get('phoneNumber', ''),
                help="Optional: Add your phone number for account recovery"
            )
        
        with col2:
            location = st.text_input(
                "Location",
                value=user_data.get('location', ''),
                help="Optional: Your general location for regional pricing"
            )
            
            timezone = st.selectbox(
                "Timezone",
                options=[
                    "Pacific Time (PT)",
                    "Mountain Time (MT)",
                    "Central Time (CT)",
                    "Eastern Time (ET)"
                ],
                index=0,
                help="Select your timezone for accurate market timing"
            )
            
            notifications = st.checkbox(
                "Enable Notifications",
                value=user_data.get('notifications', True),
                help="Receive updates about your collection and market changes"
            )
        
        # Save changes button
        if st.button("Save Changes", type="primary", use_container_width=True):
            profile_data = {
                'displayName': display_name,
                'phoneNumber': phone,
                'location': location,
                'timezone': timezone,
                'notifications': notifications
            }
            
            success, message = update_user_profile(st.session_state.uid, profile_data)
            if success:
                st.success(message)
                # Update session state
                st.session_state.user.update(profile_data)
            else:
                st.error(message)
    
    # Preferences section
    with ThemeManager.styled_card():
        st.subheader("App Preferences")
        
        col1, col2 = st.columns(2)
        
        with col1:
            theme = st.selectbox(
                "Theme",
                options=["Light", "Dark", "System Default"],
                index=2,
                help="Choose your preferred app theme"
            )
            
            currency = st.selectbox(
                "Currency",
                options=["USD", "EUR", "GBP", "CAD", "AUD"],
                index=0,
                help="Your preferred currency for prices"
            )
        
        with col2:
            default_view = st.selectbox(
                "Default Collection View",
                options=["Grid", "List", "Table"],
                index=0,
                help="Choose how you want to view your collection by default"
            )
            
            price_alerts = st.checkbox(
                "Price Alerts",
                value=True,
                help="Get notified when cards in your collection change significantly in value"
            )
        
        if st.button("Save Preferences", type="primary", use_container_width=True):
            preferences = {
                'theme': theme.lower(),
                'currency': currency,
                'default_view': default_view.lower(),
                'price_alerts': price_alerts
            }
            
            # Save preferences to session state
            st.session_state.preferences = preferences
            st.success("Preferences saved successfully!")
    
    # Account Management section
    with ThemeManager.styled_card():
        st.subheader("Account Management")
        
        st.warning("WARNING: Important Account Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Change Password", use_container_width=True):
                # TODO: Implement password change flow
                st.info("Password change functionality coming soon!")
            
            if st.button("Export Data", use_container_width=True):
                # TODO: Implement data export
                st.info("Data export functionality coming soon!")
        
        with col2:
            if st.button("Delete Account", type="secondary", use_container_width=True):
                # TODO: Implement account deletion
                st.error("Please contact support to delete your account.")
    
    # Future Billing Section (commented out for now)
    """
    with ThemeManager.styled_card():
        st.subheader("Billing")
        st.info("Billing management coming soon!")
        
        # Placeholder for future billing features
        st.markdown('''
        **Coming Soon:**
        - Subscription management
        - Payment history
        - Billing preferences
        ''')
    """

if __name__ == "__main__":
    main() 