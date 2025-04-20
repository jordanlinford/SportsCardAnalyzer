import streamlit as st
from modules.core.firebase_manager import FirebaseManager
from modules.ui.theme.theme_manager import ThemeManager
from modules.ui.branding import BrandingComponent
from modules.utils.helpers import setup_page_config

# Setup page
setup_page_config()

# Inject theme + branding
ThemeManager.apply_theme_styles()
BrandingComponent.add_branding_styles()

# Show branding/logo only (no nav)
with st.sidebar:
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    BrandingComponent.display_horizontal_logo()
    st.markdown('</div>', unsafe_allow_html=True)

# Main content
st.title("Welcome to Sports Card Analyzer Pro")
st.markdown("""
    Your all-in-one platform for managing and analyzing your sports card collection.
    
    Features include:
    - 📊 Market Analysis
    - 📸 Display Case
    - 📋 Collection Manager
    - 🔄 Trade Analyzer
    - 💎 Premium Features
    
    Please sign in to access your account.
""")

# Show loading state while checking auth
with st.spinner("Checking authentication..."):
    # Auth
    firebase_manager = FirebaseManager.get_instance()
    user = firebase_manager.get_current_user()

    if user:
        st.success(f"Welcome back, {user.get('displayName', 'User')}!")
        st.switch_page("pages/0_Home.py")
    else:
        st.info("Please sign in to continue")
        st.switch_page("pages/0_login.py") 