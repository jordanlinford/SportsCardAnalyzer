import streamlit as st

# Set page config - must be first Streamlit command
st.set_page_config(
    page_title="Login - Sports Card Analyzer Pro",
    page_icon="🏈",
    layout="centered"
)

from modules.core.firebase_manager import FirebaseManager
from modules.ui.theme.theme_manager import ThemeManager
from modules.ui.branding import BrandingComponent
from modules.ui.theme.theme_config import FAVICON_PATH
import traceback
import json
import webbrowser
import time
import threading
import streamlit_cookies_manager

# Initialize debug mode in session state first
if 'debug_mode' not in st.session_state:
    st.session_state.debug_mode = False

# Add debug mode toggle in sidebar immediately
st.sidebar.checkbox("Debug Mode (Prevent Auto Login)", 
                   value=st.session_state.debug_mode,
                   key='debug_mode',
                   on_change=lambda: st.rerun())

# Apply theme and branding styles
ThemeManager.apply_theme_styles()
BrandingComponent.add_branding_styles()

def initialize_firebase():
    """Initialize Firebase components."""
    try:
        FirebaseManager.initialize()
        return True
    except Exception as e:
        st.error(f"Error initializing Firebase: {str(e)}")
        return False

def load_user_preferences(uid):
    """
    Load user preferences from Firestore.
    
    Args:
        uid: User's unique identifier
        
    Returns:
        Dict with user preferences or None if not found
    """
    try:
        # Ensure Firebase is initialized
        if not FirebaseManager.initialize():
            print("Failed to initialize Firebase")
            return None
            
        # Get the users collection
        users_collection = FirebaseManager.get_collection('users')
        if not users_collection:
            print("Failed to get users collection")
            return None
            
        # Get the user document
        user_doc = users_collection.document(uid).get()
        if not user_doc.exists:
            print(f"User document not found for UID: {uid}")
            return None
            
        # Get user data and preferences
        user_data = user_doc.to_dict()
        return user_data.get('preferences')
    except Exception as e:
        print(f"Error loading user preferences: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return None

def handle_auth_error(e):
    """
    Handle authentication errors and return user-friendly messages.
    """
    try:
        error_data = json.loads(str(e))
        error_code = error_data.get('error', {}).get('code')
        error_message = error_data.get('error', {}).get('message')
        
        if error_code == 400:
            if error_message == "EMAIL_EXISTS":
                return "This email address is already registered. Please try logging in instead."
            elif error_message == "INVALID_EMAIL":
                return "Please enter a valid email address."
            elif error_message == "WEAK_PASSWORD":
                return "Please choose a stronger password (at least 6 characters)."
            elif error_message == "INVALID_PASSWORD":
                return "Invalid password. Please try again."
            elif error_message == "USER_DISABLED":
                return "This account has been disabled. Please contact support."
            elif error_message == "USER_NOT_FOUND":
                return "No account found with this email. Please sign up instead."
            elif error_message == "INVALID_LOGIN_CREDENTIALS":
                return "Invalid email or password. Please check your credentials and try again."
        return f"Authentication error: {error_message}"
    except:
        return f"An error occurred: {str(e)}"

def main():
    # Initialize session state for user if not exists
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'preferences' not in st.session_state:
        st.session_state.preferences = None
    if 'uid' not in st.session_state:
        st.session_state.uid = None
    if 'is_new_user' not in st.session_state:
        st.session_state.is_new_user = False
    if 'auth_window' not in st.session_state:
        st.session_state.auth_window = None
    if 'cookies_checked' not in st.session_state:
        st.session_state.cookies_checked = False
    
    # Initialize cookies manager
    cookies = streamlit_cookies_manager.CookieManager()
    
    # Sidebar
    with st.sidebar:
        # Sidebar header with branding
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        BrandingComponent.display_horizontal_logo()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Navigation
        st.page_link("app.py", label="Home", icon="🏠")
        st.page_link("pages/1_market_analysis.py", label="Market Analysis", icon="📊")
        st.page_link("pages/4_display_case.py", label="Display Case", icon="📸")
        st.page_link("pages/3_collection_manager.py", label="Collection Manager", icon="📋")
        st.page_link("pages/2_trade_analyzer.py", label="Trade Analyzer", icon="🔄")
        st.page_link("pages/6_profile_management.py", label="Profile", icon="👤")
    
    st.title("Login")
    
    # Add clear cookies button in sidebar
    if st.sidebar.button("Clear Cookies"):
        if cookies.ready():
            del cookies['user']
            del cookies['uid']
            cookies.save()
        st.session_state.user = None
        st.session_state.preferences = None
        st.session_state.uid = None
        st.session_state.is_new_user = False
        st.session_state.cookies_checked = False
        st.rerun()
    
    # Handle logout if requested
    if st.session_state.user and st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.preferences = None
        st.session_state.uid = None
        st.session_state.is_new_user = False
        st.session_state.cookies_checked = False
        if cookies.ready():
            del cookies['user']
            del cookies['uid']
            cookies.save()
        st.rerun()
    
    # Check if user is already logged in (either through session state or cookies)
    if not st.session_state.user and not st.session_state.cookies_checked and cookies.ready():
        try:
            user_cookie = cookies.get('user')
            uid_cookie = cookies.get('uid')
            if user_cookie and uid_cookie:
                # Restore session from cookies
                st.session_state.user = json.loads(user_cookie)
                st.session_state.uid = uid_cookie
                st.session_state.preferences = load_user_preferences(st.session_state.uid)
        except Exception as e:
            print(f"[Cookies] Restore error: {str(e)}")
            if cookies.ready():
                cookies['user'] = ''
                cookies['uid'] = ''
                cookies.save()
        finally:
            st.session_state.cookies_checked = True
    
    # If user is logged in, show welcome message
    if st.session_state.user:
        st.success(f"Welcome back, {st.session_state.user['displayName']}!")
        return
    
    # Initialize Firebase
    if not initialize_firebase():
        return
    
    # Create tabs for login and signup
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.header("Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            try:
                user = FirebaseManager.sign_in(email, password)
                st.session_state.user = user
                st.session_state.uid = user.get('localId')
                st.session_state.preferences = load_user_preferences(st.session_state.uid)
                st.session_state.is_new_user = False
                
                # Save to cookies
                if cookies.ready():
                    cookies['user'] = json.dumps(user)
                    cookies['uid'] = st.session_state.uid
                    cookies.save()
                
                st.success("Login successful!")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {str(e)}")
    
    with tab2:
        st.header("Sign Up")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        display_name = st.text_input("Display Name", key="signup_display_name")
        
        if st.button("Sign Up"):
            try:
                user = FirebaseManager.sign_up(email, password, display_name)
                st.session_state.user = user
                st.session_state.uid = user.get('localId')
                st.session_state.preferences = load_user_preferences(st.session_state.uid)
                st.session_state.is_new_user = True
                
                # Save to cookies
                if cookies.ready():
                    cookies['user'] = json.dumps(user)
                    cookies['uid'] = st.session_state.uid
                    cookies.save()
                
                st.success("Account created successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Sign up failed: {str(e)}")
    
    # Add Google Sign-In
    st.markdown("---")
    st.markdown("### Or sign in with")
    if st.button("Google", key="google_signin"):
        try:
            user = FirebaseManager.sign_in_with_google()
            st.session_state.user = user
            st.session_state.uid = user.get('localId')
            st.session_state.preferences = load_user_preferences(st.session_state.uid)
            st.session_state.is_new_user = True
            
            # Save to cookies
            if cookies.ready():
                cookies['user'] = json.dumps(user)
                cookies['uid'] = st.session_state.uid
                cookies.save()
            
            st.success("Google sign-in successful!")
            st.rerun()
        except Exception as e:
            st.error(f"Google sign-in failed: {str(e)}")

if __name__ == "__main__":
    main() 