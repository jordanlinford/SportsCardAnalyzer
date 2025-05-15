import streamlit as st
import json
import time
import streamlit_cookies_manager
from modules.core.firebase_manager import FirebaseManager
from modules.ui.theme.theme_manager import ThemeManager
from modules.ui.branding import BrandingComponent
import webbrowser
import threading

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
    """Load user preferences from Firestore."""
    try:
        users_collection = FirebaseManager.get_collection('users')
        if not users_collection:
            return None
            
        user_doc = users_collection.document(uid).get()
        if not user_doc.exists:
            return None
            
        user_data = user_doc.to_dict()
        return user_data.get('preferences')
    except Exception:
        return None

def save_auth_to_cookies(user_data, uid):
    """Save authentication data to cookies."""
    try:
        cookies = streamlit_cookies_manager.CookieManager()
        if cookies.ready():
            # Extract just the essential authentication data to avoid cookie size limits
            essential_data = {
                'localId': user_data.get('localId'),
                'email': user_data.get('email'),
                'displayName': user_data.get('displayName'),
                'idToken': user_data.get('idToken'),
                'refreshToken': user_data.get('refreshToken'),
                'expiresIn': user_data.get('expiresIn'),
                # Include custom profile fields
                'phoneNumber': user_data.get('phoneNumber'),
                'location': user_data.get('location'),
                'timezone': user_data.get('timezone'),
                'notifications': user_data.get('notifications', True)
            }
            
            cookies['user'] = json.dumps(essential_data)
            cookies['uid'] = uid
            cookies['last_login'] = str(int(time.time()))
            cookies.save()
            return True
    except Exception as e:
        print(f"Error saving auth to cookies: {str(e)}")
    return False

def restore_session_from_cookies():
    """Restore session from cookies if available."""
    try:
        cookies = streamlit_cookies_manager.CookieManager()
        if not cookies.ready():
            return False
            
        user_cookie = cookies.get('user')
        uid_cookie = cookies.get('uid')
        last_login = cookies.get('last_login')
        
        if not all([user_cookie, uid_cookie, last_login]):
            return False
            
        # Check if session is still valid (less than 7 days old)
        if int(time.time()) - int(last_login) > 7 * 24 * 60 * 60:
            return False
            
        # Restore session
        st.session_state.user = json.loads(user_cookie)
        st.session_state.uid = uid_cookie
        st.session_state.preferences = load_user_preferences(uid_cookie)
        
        # Refresh cookies
        save_auth_to_cookies(st.session_state.user, st.session_state.uid)
        return True
    except Exception:
        return False

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
    if 'cookies_checked' not in st.session_state:
        st.session_state.cookies_checked = False
    
    # Sidebar
    with st.sidebar:
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        BrandingComponent.display_horizontal_logo()
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("Clear Cookies"):
            cookies = streamlit_cookies_manager.CookieManager()
            if cookies.ready():
                cookies['user'] = ''
                cookies['uid'] = ''
                cookies['last_login'] = ''
                cookies.save()
            st.session_state.user = None
            st.session_state.preferences = None
            st.session_state.uid = None
            st.session_state.is_new_user = False
            st.session_state.cookies_checked = False
            st.rerun()
    
    # Main content
    st.title("Sign In to Sports Card Analyzer Pro")
    
    # Try to restore session from cookies
    if not st.session_state.user and not st.session_state.cookies_checked:
        if restore_session_from_cookies():
            st.success(f"Welcome back, {st.session_state.user.get('displayName', 'User')}!")
            st.info("Redirecting you to your dashboard...")
            time.sleep(1)
            st.switch_page("pages/0_Home.py")
            return
        st.session_state.cookies_checked = True
    
    # If user is logged in, redirect to dashboard
    if st.session_state.user and st.session_state.uid:
        st.success(f"Welcome back, {st.session_state.user.get('displayName', 'User')}!")
        st.info("Redirecting you to your dashboard...")
        time.sleep(1)
        st.switch_page("pages/0_Home.py")
        return
    
    # Initialize Firebase
    if not initialize_firebase():
        st.error("Unable to connect to authentication service. Please try again later.")
        return
    
    # Create tabs for login and signup
    tab1, tab2 = st.tabs(["Sign In", "Create Account"])
    
    with tab1:
        st.header("Sign In to Your Account")
        st.markdown("Enter your credentials to access your collection and analysis tools.")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            email = st.text_input("Email Address", placeholder="your@email.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            
            if st.button("Sign In", type="primary", use_container_width=True):
                with st.spinner("Signing in..."):
                    try:
                        firebase = FirebaseManager.get_instance()
                        user = firebase.sign_in(email, password)
                        
                        # Ensure we have all the necessary user data
                        if not isinstance(user, dict):
                            st.error("Invalid user data received. Please try again.")
                            return
                            
                        st.session_state.user = user
                        st.session_state.uid = user.get('localId')
                        st.session_state.preferences = load_user_preferences(st.session_state.uid)
                        
                        # Log the user data for debugging
                        print(f"Login successful - User data: {user.keys()}")
                        
                        # Save auth to cookies
                        if save_auth_to_cookies(user, st.session_state.uid):
                            st.success("Login successful! Redirecting...")
                            time.sleep(1)
                            st.switch_page("pages/0_Home.py")
                        else:
                            st.error("Login successful but failed to save session. Please try again.")
                    except Exception as e:
                        st.error(f"Login failed: {handle_auth_error(e)}")
        
        with col2:
            st.markdown("### Or sign in with")
            if st.button("Google", key="google_signin", use_container_width=True):
                try:
                    # Get an instance of FirebaseManager first
                    firebase = FirebaseManager.get_instance()
                    user = firebase.sign_in_with_google()
                    st.session_state.user = user
                    st.session_state.uid = user.get('localId')
                    st.session_state.preferences = load_user_preferences(st.session_state.uid)
                    st.session_state.is_new_user = True
                    
                    # Save to cookies
                    if save_auth_to_cookies(user, st.session_state.uid):
                        st.success("Google sign-in successful!")
                        st.rerun()
                    else:
                        st.error("Google sign-in successful but failed to save session. Please try again.")
                except Exception as e:
                    st.error(f"Google sign-in failed: {handle_auth_error(e)}")
    
    with tab2:
        st.header("Create Your Account")
        st.markdown("Join Sports Card Analyzer Pro to start managing your collection today.")
        
        email = st.text_input("Email Address", key="signup_email", placeholder="your@email.com")
        password = st.text_input("Password", type="password", key="signup_password", placeholder="••••••••")
        display_name = st.text_input("Display Name", key="signup_display_name", placeholder="Your Name")
        
        if st.button("Create Account", type="primary", use_container_width=True):
            with st.spinner("Creating your account..."):
                try:
                    # Get an instance of FirebaseManager first
                    firebase = FirebaseManager.get_instance()
                    user = firebase.sign_up(email, password, display_name)
                    st.session_state.user = user
                    st.session_state.uid = user.get('localId')
                    st.session_state.is_new_user = True
                    
                    # Save to cookies
                    if save_auth_to_cookies(user, st.session_state.uid):
                        st.success("Account created successfully! Redirecting to your dashboard...")
                        time.sleep(1)
                        st.switch_page("pages/0_Home.py")
                    else:
                        st.error("Account created successfully but failed to save session. Please try again.")
                except Exception as e:
                    st.error(f"Account creation failed: {handle_auth_error(e)}")

if __name__ == "__main__":
    main() 