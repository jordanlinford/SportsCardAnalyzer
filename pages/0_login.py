import streamlit as st
from modules.firebase.firebase_init import initialize_all, get_firestore_client, get_pyrebase_auth
from modules.firebase.user_management import UserManager
from modules.ui.theme.theme_manager import ThemeManager
from modules.ui.branding import BrandingComponent
from modules.ui.theme.theme_config import FAVICON_PATH
import traceback
import json
import webbrowser
import time
import threading

# Configure the page
st.set_page_config(
    page_title="Login - Sports Card Analyzer Pro",
    page_icon=FAVICON_PATH,
    layout="centered"
)

# Apply theme and branding styles
ThemeManager.apply_theme_styles()
BrandingComponent.add_branding_styles()

def initialize_firebase():
    """
    Initialize Firebase components and return the auth instance.
    """
    try:
        # Initialize all Firebase components
        if not initialize_all():
            st.error("Failed to initialize Firebase. Please try again later.")
            return None
            
        # Get the auth instance
        auth = get_pyrebase_auth()
        if auth is None:
            st.error("Failed to initialize authentication. Please try again later.")
            return None
            
        return auth
    except Exception as e:
        st.error(f"Error initializing Firebase: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return None

def load_user_preferences(uid):
    """
    Load user preferences from Firestore.
    
    Args:
        uid: User's unique identifier
        
    Returns:
        Dict with user preferences or None if not found
    """
    try:
        firestore_client = get_firestore_client()
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
    # Display logo centered at the top
    st.markdown('<div class="logo-container vertical" style="display: flex; flex-direction: column; align-items: center; gap: 12px; text-align: center; padding: 1rem;">', unsafe_allow_html=True)
    BrandingComponent.display_vertical_logo()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Initialize session state
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
    
    # Initialize Firebase
    auth = initialize_firebase()
    if auth is None:
        return
    
    # Check if user is already logged in
    if st.session_state.user is not None:
        if st.session_state.is_new_user:
            st.success("Welcome to Sports Card Analyzer Pro! Your account has been created successfully.")
            st.write("You can now start managing your sports card collection.")
            st.session_state.is_new_user = False  # Reset the flag
        else:
            st.success(f"Welcome back! You are currently logged in.")
        
        if st.button("Logout"):
            st.session_state.user = None
            st.session_state.preferences = None
            st.session_state.uid = None
            st.session_state.is_new_user = False
            st.rerun()
        return
    
    # Create tabs for login and signup
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    # Add Google Sign-In button
    st.markdown("---")
    st.markdown("### Or sign in with")
    if st.button("Sign in with Google", key="google_signin"):
        try:
            # Open Google sign-in page in a new browser window
            auth_url = "https://sports-card-analyzer.web.app"  # Firebase Hosting URL
            st.session_state.auth_window = webbrowser.open_new_tab(auth_url)
            
            # Show instructions to the user
            st.info("Please complete the Google sign-in process in the browser window that just opened. Once signed in, return to this page.")
            
            # Create a placeholder for the status message
            status_placeholder = st.empty()
            
            # Check for authentication response
            if 'auth_response' in st.session_state:
                response = st.session_state.auth_response
                if response.get('type') == 'auth_success':
                    try:
                        # Verify the ID token
                        user = auth.get_account_info(response['token'])
                        if user:
                            st.session_state.user = {
                                'localId': response['user']['uid'],
                                'email': response['user']['email'],
                                'displayName': response['user']['displayName'],
                                'idToken': response['token']
                            }
                            st.session_state.uid = response['user']['uid']
                            st.session_state.preferences = load_user_preferences(response['user']['uid'])
                            st.session_state.is_new_user = True
                            status_placeholder.success("Google sign-in successful!")
                            st.rerun()
                    except Exception as e:
                        status_placeholder.error(f"Error verifying authentication: {str(e)}")
                else:
                    status_placeholder.error("Authentication failed. Please try again.")
                
                # Clear the response
                del st.session_state.auth_response
        except Exception as e:
            st.error(f"Google sign-in failed: {str(e)}")
    
    with tab1:
        st.subheader("Login")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login"):
            if not email or not password:
                st.error("Please enter both email and password")
            else:
                try:
                    user = auth.sign_in_with_email_and_password(email, password)
                    st.session_state.user = user
                    st.session_state.uid = user['localId']
                    st.session_state.preferences = load_user_preferences(user['localId'])
                    st.session_state.is_new_user = False
                    st.success("Login successful!")
                    st.rerun()
                except Exception as e:
                    st.error(handle_auth_error(e))
                
    with tab2:
        st.subheader("Sign Up")
        new_email = st.text_input("Email", key="signup_email")
        new_password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password")
        
        if st.button("Sign Up"):
            if not new_email or not new_password or not confirm_password:
                st.error("Please fill in all fields")
            elif new_password != confirm_password:
                st.error("Passwords do not match")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters long")
            else:
                try:
                    # Try to sign in first to check if user exists
                    try:
                        auth.sign_in_with_email_and_password(new_email, new_password)
                        st.error("This email is already registered. Please try logging in instead.")
                    except:
                        # If sign in fails, create new user
                        user = auth.create_user_with_email_and_password(new_email, new_password)
                        st.session_state.user = user
                        st.session_state.uid = user['localId']
                        st.session_state.preferences = load_user_preferences(user['localId'])
                        st.session_state.is_new_user = True
                        st.success("Sign up successful!")
                        st.rerun()
                except Exception as e:
                    st.error(handle_auth_error(e))

if __name__ == "__main__":
    main() 