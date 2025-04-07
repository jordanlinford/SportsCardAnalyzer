import streamlit as st
from modules.core.firebase_manager import FirebaseManager
from modules.ui.theme.theme_manager import ThemeManager
from modules.ui.branding import BrandingComponent
from modules.ui.theme.theme_config import FAVICON_PATH
import traceback
import json
import webbrowser
import time
import threading

# Set page config
st.set_page_config(
    page_title="Login - Sports Card Analyzer Pro",
    page_icon="🏈",
    layout="centered"
)

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
        firestore_client = FirebaseManager.get_firestore_client()
        if firestore_client is None:
            print("ERROR: Firestore client is not initialized")
            return None
            
        user_doc = firestore_client.collection('users').document(uid).get()
        if not user_doc.exists:
            print(f"User document not found for UID: {uid}")
            return None
            
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
    # Display logo at the top
    BrandingComponent.display_vertical_logo()
    
    # Initialize session state variables
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
    
    # Check if user is already logged in
    if st.session_state.user:
        st.success(f"Welcome back, {st.session_state.user['displayName']}!")
        if st.button("Logout"):
            st.session_state.user = None
            st.session_state.preferences = None
            st.session_state.uid = None
            st.session_state.is_new_user = False
            st.rerun()
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
                st.session_state.uid = user.uid
                st.session_state.preferences = load_user_preferences(user.uid)
                st.session_state.is_new_user = False
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
                st.session_state.uid = user.uid
                st.session_state.preferences = load_user_preferences(user.uid)
                st.session_state.is_new_user = True
                st.success("Sign up successful!")
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
            st.session_state.uid = user.uid
            st.session_state.preferences = load_user_preferences(user.uid)
            st.session_state.is_new_user = True
            st.success("Google sign-in successful!")
            st.rerun()
        except Exception as e:
            st.error(f"Google sign-in failed: {str(e)}")

if __name__ == "__main__":
    main() 