import streamlit as st
from modules.firebase.firebase_init import initialize_all, get_firestore_client
from modules.firebase.user_management import UserManager
import traceback

# Configure the page
st.set_page_config(
    page_title="Login - Sports Card Analyzer Pro",
    page_icon="🔑",
    layout="centered"
)

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

def main():
    st.title("Sports Card Analyzer Pro")
    
    # Initialize session state
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'preferences' not in st.session_state:
        st.session_state.preferences = None
    if 'uid' not in st.session_state:
        st.session_state.uid = None
    
    # Check if user is already logged in
    if st.session_state.user is not None:
        st.success(f"Welcome back, {st.session_state.user.get('displayName', 'User')}!")
        st.write("You are currently logged in.")
        st.write("Your preferences:")
        st.json(st.session_state.preferences)
        
        if st.button("Logout"):
            st.session_state.user = None
            st.session_state.preferences = None
            st.session_state.uid = None
            st.rerun()
        return
    
    # Initialize Firebase components
    if not initialize_all():
        st.error("Failed to initialize Firebase services. Please try again later.")
        return
    
    # Create tabs for login and signup
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.header("Login")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                try:
                    if not email or not password:
                        st.error("Please enter both email and password")
                        return
                        
                    result = UserManager.sign_in(email, password)
                    if result['success']:
                        st.session_state.user = result['user']
                        st.session_state.uid = result['uid']
                        st.session_state.preferences = result['user'].get('preferences')
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error(f"Login failed: {result['error']}")
                except Exception as e:
                    print(f"Error during login: {str(e)}")
                    print(f"Traceback: {traceback.format_exc()}")
                    st.error(f"Login failed: {str(e)}")
    
    with tab2:
        st.header("Sign Up")
        with st.form("signup_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            display_name = st.text_input("Display Name")
            submit = st.form_submit_button("Sign Up")
            
            if submit:
                if not email or not password or not confirm_password or not display_name:
                    st.error("Please fill in all fields")
                    return
                    
                if password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    try:
                        result = UserManager.create_user(email, password, display_name)
                        if result['success']:
                            st.session_state.user = result['user']
                            st.session_state.uid = result['uid']
                            st.session_state.preferences = result['user'].get('preferences')
                            st.success("Sign up successful!")
                            st.rerun()
                        else:
                            st.error(f"Sign up failed: {result['error']}")
                    except Exception as e:
                        print(f"Error during sign up: {str(e)}")
                        print(f"Traceback: {traceback.format_exc()}")
                        st.error(f"Sign up failed: {str(e)}")

if __name__ == "__main__":
    main() 