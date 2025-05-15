import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys
import json
import io
import traceback
import time
from pathlib import Path
from firebase_admin import auth as admin_auth
from modules.firebase.user_management import UserManager, delete_user_data
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

# Add branding to sidebar
with st.sidebar:
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    BrandingComponent.display_horizontal_logo()
    st.markdown('</div>', unsafe_allow_html=True)

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
        
        /* Card styling enhancement */
        .card {
            background-color: #ffffff;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
        }
        
        /* Form field styling */
        .stTextInput > div > div > input,
        .stSelectbox > div > div,
        .stCheckbox > div > div,
        .stTextArea > div > div > textarea {
            background-color: #f8fafc;
            border-radius: 4px;
            border: 1px solid #cbd5e1;
            padding: 8px 12px;
            font-size: 1rem;
            box-shadow: none !important;
            transition: all 0.2s;
        }
        
        .stTextInput > div > div > input:focus,
        .stSelectbox > div > div:focus,
        .stCheckbox > div > div:focus,
        .stTextArea > div > div > textarea:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2) !important;
        }
        
        /* Button styling enhancement */
        .stButton > button {
            background-color: #3b82f6;
            color: white;
            border-radius: 4px;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: 500;
            transition: all 0.2s;
        }
        
        .stButton > button:hover {
            background-color: #2563eb;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
            
            .card {
                background-color: #1e293b;
                border-color: #334155;
            }
            
            .stTextInput > div > div > input,
            .stSelectbox > div > div,
            .stCheckbox > div > div,
            .stTextArea > div > div > textarea {
                background-color: #0f172a;
                border-color: #334155;
                color: #f8fafc;
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
        print(f"Starting update_user_profile with UID: {uid} and data: {profile_data}")
        
        # Validate inputs
        if not uid:
            print("Error: No UID provided")
            return False, "No user ID provided"
        
        if not profile_data or not isinstance(profile_data, dict):
            print(f"Error: Invalid profile data: {profile_data}")
            return False, "Invalid profile data format"
        
        # Get Firebase Manager instance and ensure it's initialized
        firebase_manager = FirebaseManager.get_instance()
        if not firebase_manager:
            print("Error: Failed to get Firebase Manager instance")
            return False, "Failed to initialize Firebase connection"
            
        if not firebase_manager._initialized:
            print("Firebase Manager not initialized, attempting to initialize")
            if not firebase_manager.initialize():
                print("Error: Failed to initialize Firebase Manager")
                return False, "Failed to initialize Firebase connection"
        
        print(f"Firebase initialized successfully, updating profile for user {uid}")
        
        # Check if update_user_profile is available as a static method
        if hasattr(FirebaseManager, 'update_user_profile'):
            # Update user profile in Firebase using the static method
            success = FirebaseManager.update_user_profile(uid, profile_data)
        else:
            # Fall back to the update_user method if the static method isn't available
            print("Static update_user_profile not found, falling back to update_user")
            success = firebase_manager.update_user(uid, profile_data)
        
        if success:
            print(f"Profile updated successfully for user {uid}")
            return True, "Profile updated successfully!"
        else:
            print(f"Error updating profile for user {uid}")
            return False, "Error updating profile. Please try again."
    except Exception as e:
        print(f"Exception in update_user_profile: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False, f"Error updating profile: {str(e)}"

def send_password_reset_email(email):
    """Send password reset email to the user"""
    try:
        # Get Firebase Manager instance and ensure it's initialized
        firebase_manager = FirebaseManager.get_instance()
        if not firebase_manager._initialized:
            if not firebase_manager.initialize():
                return False, "Failed to initialize Firebase connection"
        
        # Send password reset email
        firebase_manager._firebase.auth().send_password_reset_email(email)
        
        # Return success with detailed instructions
        return True, f"""
        Password reset email sent to {email}!
        
        If you don't receive the email:
        1. Check your spam/junk folder
        2. Verify this is the correct email: {email}
        3. Try the manual reset method: Go to https://firebase.google.com/docs/auth/web/manage-users#send_a_password_reset_email
        
        Note: If this is a development environment, email delivery might not be fully configured.
        """
    except Exception as e:
        return False, f"Error sending password reset email: {str(e)}"

def set_user_password(uid, new_password):
    """Directly set a new password for the user using Admin SDK"""
    try:
        # Update the user's password
        admin_auth.update_user(uid, password=new_password)
        return True, "Password updated successfully! You'll need to sign in again with your new password."
    except Exception as e:
        print(f"Error updating password: {str(e)}")
        print(traceback.format_exc())
        return False, f"Error updating password: {str(e)}"

def export_user_data(uid):
    """Export all user data as JSON"""
    try:
        # Get Firebase Manager instance and ensure it's initialized
        firebase_manager = FirebaseManager.get_instance()
        if not firebase_manager._initialized:
            if not firebase_manager.initialize():
                return False, "Failed to initialize Firebase connection", None
        
        # Get user data from Firestore
        user_doc = firebase_manager.db.collection('users').document(uid).get()
        if not user_doc.exists:
            return False, "User data not found", None
            
        user_data = user_doc.to_dict()
        
        # Get user's card collection
        collection_data = []
        cards_ref = firebase_manager.db.collection('users').document(uid).collection('cards')
        if cards_ref:
            cards = cards_ref.get()
            for card in cards:
                collection_data.append(card.to_dict())
        
        # Combine all data
        export_data = {
            "user_profile": user_data,
            "collection": collection_data
        }
        
        # Convert to JSON
        json_data = json.dumps(export_data, default=str, indent=4)
        return True, "Data exported successfully", json_data
    except Exception as e:
        print(f"Error exporting user data: {str(e)}")
        print(traceback.format_exc())
        return False, f"Error exporting user data: {str(e)}", None

def delete_user_account(uid):
    """Delete user account and all associated data"""
    try:
        # Get Firebase Manager instance and ensure it's initialized
        firebase_manager = FirebaseManager.get_instance()
        if not firebase_manager._initialized:
            if not firebase_manager.initialize():
                return False, "Failed to initialize Firebase connection"
        
        # First, delete user's card collection
        cards_ref = firebase_manager.db.collection('users').document(uid).collection('cards')
        if cards_ref:
            batch = firebase_manager.db.batch()
            cards = cards_ref.get()
            for card in cards:
                batch.delete(card.reference)
            batch.commit()
        
        # Delete user data from Firestore
        if not delete_user_data(uid):
            return False, "Error deleting user data"
        
        # Delete user from Firebase Auth
        if not firebase_manager.delete_user(uid):
            return False, "Error deleting user authentication data"
            
        return True, "Account deleted successfully"
    except Exception as e:
        print(f"Error deleting user account: {str(e)}")
        print(traceback.format_exc())
        return False, f"Error deleting user account: {str(e)}"

def main():
    # Initialize session state for user if not exists
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'uid' not in st.session_state:
        st.session_state.uid = None
    
    # If user is not logged in, redirect to login page
    if not st.session_state.user:
        st.switch_page("pages/0_login.py")
    
    # Add CSS to ensure card styling and form elements are properly displayed
    st.markdown("""
    <style>
    /* Force card visibility */
    div.card {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        background-color: white !important;
        padding: 20px !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        margin-bottom: 20px !important;
    }
    
    /* Target all elements inside the card to ensure they're visible */
    div.card > div {
        opacity: 1 !important;
        visibility: visible !important;
        display: block !important;
    }
    
    /* Fix for blank space below Profile Management header */
    h1 + div {
        display: block !important;
        visibility: visible !important;
    }
    
    /* Fix for blank areas around buttons */
    button, .stButton, .stButton > button {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        width: 100% !important;
        background-color: #3b82f6 !important;
        color: white !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 10px 15px !important;
        margin: 10px 0 !important;
        cursor: pointer !important;
        font-weight: 500 !important;
    }
    
    /* Ensure form field containers are visible */
    div[data-testid="stVerticalBlock"] > div {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    
    /* Add explicit styling for input fields */
    input, select, textarea {
        display: block !important;
        width: 100% !important;
        padding: 8px 12px !important;
        margin-bottom: 10px !important;
        font-size: 16px !important;
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 4px !important;
    }
    
    /* Force display for label elements */
    label, .stSelectbox label, .stTextInput label {
        display: block !important;
        margin-bottom: 5px !important;
        font-weight: 500 !important;
        color: #1a365d !important;
    }
    
    /* Ensure column visibility */
    [data-testid="column"] {
        display: block !important;
        padding: 0 10px !important;
    }
    
    /* Ensure stSubheader is visible */
    .stSubheader {
        display: block !important;
        visibility: visible !important;
        margin-top: 10px !important;
        margin-bottom: 20px !important;
        font-weight: 600 !important;
        color: #1a365d !important;
    }
    
    /* Dark mode adjustments */
    @media (prefers-color-scheme: dark) {
        div.card {
            background-color: #1e293b !important;
            border-color: #334155 !important;
        }
        
        input, select, textarea {
            background-color: #0f172a !important;
            border-color: #334155 !important;
            color: #f8fafc !important;
        }
        
        label, .stSelectbox label, .stTextInput label {
            color: #f1f5f9 !important;
        }
        
        .stSubheader {
            color: #f1f5f9 !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("Profile Management")
    
    # Get current user data
    user_data = st.session_state.user
    print(f"Raw user data: {user_data}")
    
    # Ensure user_data is a dictionary
    if user_data is None:
        user_data = {}
    elif not isinstance(user_data, dict):
        try:
            user_data = dict(user_data)
        except (TypeError, ValueError):
            # If conversion fails, create an empty dict
            user_data = {}
            print(f"Failed to convert user data to dictionary: {st.session_state.user}")
    
    # Create a simple container instead of ThemeManager.styled_card()
    st.markdown("""
    <div class="card" style="display:block !important; visibility:visible !important; opacity:1 !important; background-color:white; padding:20px; border:1px solid #e2e8f0; border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.1); margin-bottom:20px;">
        <h3 style="margin-top:0; margin-bottom:20px; font-weight:600; color:#1a365d;">Personal Information</h3>
    </div>
    """, unsafe_allow_html=True)

    # Create two columns for the form
    col1, col2 = st.columns(2)

    with col1:
        # Safely get values with defaults
        display_name = user_data.get('displayName', '')
        if not display_name and 'display_name' in user_data:
            display_name = user_data.get('display_name', '')
        
        email = user_data.get('email', '')
        phone = user_data.get('phoneNumber', '')
        if not phone and 'phone_number' in user_data:
            phone = user_data.get('phone_number', '')
        
        display_name = st.text_input(
            "Display Name",
            value=display_name,
            help="This is the name that will be shown to other users"
        )
        
        email = st.text_input(
            "Email",
            value=email,
            disabled=True,  # Email can't be changed directly
            help="Contact support to change your email address"
        )
        
        phone = st.text_input(
            "Phone Number",
            value=phone,
            help="Optional: Add your phone number for account recovery"
        )
    
    with col2:
        # Safely get values with defaults
        location = user_data.get('location', '')
        
        # Default timezone index
        timezone_options = [
            "Pacific Time (PT)",
            "Mountain Time (MT)",
            "Central Time (CT)",
            "Eastern Time (ET)"
        ]
        timezone_index = 0
        current_timezone = user_data.get('timezone', '')
        if current_timezone:
            try:
                timezone_index = timezone_options.index(current_timezone)
            except ValueError:
                timezone_index = 0
        
        # Default notification value
        notifications_value = bool(user_data.get('notifications', True))
        
        location = st.text_input(
            "Location",
            value=location,
            help="Optional: Your general location for regional pricing"
        )
        
        timezone = st.selectbox(
            "Timezone",
            options=timezone_options,
            index=timezone_index,
            help="Select your timezone for accurate market timing"
        )
        
        notifications = st.checkbox(
            "Enable Notifications",
            value=notifications_value,
            help="Receive updates about your collection and market changes"
        )
    
    # Save changes button with custom HTML for enhanced visibility
    st.markdown("""
    <style>
    .save-button {
        background-color: #3b82f6 !important; 
        color: white !important; 
        border: none !important; 
        border-radius: 4px !important;
        padding: 12px 20px !important;
        width: 100% !important;
        font-weight: 600 !important;
        cursor: pointer !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        margin: 20px 0 !important;
        text-align: center !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if st.button("Save Changes", type="primary", use_container_width=True, key="save_profile_changes"):
        profile_data = {
            'displayName': display_name,
            'phoneNumber': phone,
            'location': location,
            'timezone': timezone,
            'notifications': notifications
        }
        
        # Add debug info
        print(f"Attempting to update profile with data: {profile_data}")
        print(f"Current user data before update: {st.session_state.user}")
        
        success, message = update_user_profile(st.session_state.uid, profile_data)
        if success:
            st.success(message)
            # Update session state with the new values
            if not isinstance(st.session_state.user, dict):
                st.session_state.user = {}
            
            # Update all fields in session state
            for key, value in profile_data.items():
                st.session_state.user[key] = value
            
            print(f"Updated user data in session state: {st.session_state.user}")
            
            # Force a rerun to refresh the form with new values
            st.rerun()
        else:
            st.error(message)
            print(f"Profile update failed: {message}")
    
    # Account Management section
    st.markdown("""
    <div class="card" style="display:block !important; visibility:visible !important; opacity:1 !important; background-color:white; padding:20px; border:1px solid #e2e8f0; border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.1); margin-bottom:20px;">
        <h3 style="margin-top:0; margin-bottom:20px; font-weight:600; color:#1a365d;">Account Management</h3>
    </div>
    """, unsafe_allow_html=True)

    # Initialize session state for account management tab
    if 'account_management_tab' not in st.session_state:
        st.session_state.account_management_tab = 0
        
    # Create tabs for different account actions
    tab_titles = ["Change Password", "Export Data", "Delete Account"]
    account_tabs = st.tabs(tab_titles)

    # Password tab
    with account_tabs[0]:
        st.markdown("""
        <div style="display:block !important; visibility:visible !important; opacity:1 !important;">
        """, unsafe_allow_html=True)
        
        password_method = st.radio(
            "Choose password reset method:",
            ["Send Reset Email", "Set New Password Directly"]
        )
        
        if password_method == "Send Reset Email":
            # Get user email from session state
            user_email = user_data.get('email', '')
            if not user_email:
                st.error("User email not found. Please try again later.")
            else:
                if st.button("Send Reset Email", key="send_reset_email", use_container_width=True):
                    # Send password reset email
                    with st.spinner("Sending password reset email..."):
                        success, message = send_password_reset_email(user_email)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
        else:
            # Direct password setting form
            with st.form("direct_password_reset"):
                new_password = st.text_input("New Password", type="password", 
                                            help="Must be at least 6 characters")
                confirm_password = st.text_input("Confirm Password", type="password")
                
                if st.form_submit_button("Update Password"):
                    if not new_password or len(new_password) < 6:
                        st.error("Password must be at least 6 characters")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        with st.spinner("Updating password..."):
                            success, message = set_user_password(st.session_state.uid, new_password)
                            if success:
                                st.success(message)
                                st.info("You'll be logged out in 5 seconds...")
                                time.sleep(5)
                                st.session_state.user = None
                                st.session_state.uid = None
                                st.switch_page("pages/0_login.py")
                            else:
                                st.error(message)
        
        st.markdown("</div>", unsafe_allow_html=True)

    # Export data tab
    with account_tabs[1]:
        st.markdown("""
        <div style="display:block !important; visibility:visible !important; opacity:1 !important;">
        """, unsafe_allow_html=True)
        
        st.write("Export your data and collection to various formats.")
        if st.button("Export User Data", key="export_data_btn", use_container_width=True):
            # Export user data
            with st.spinner("Exporting your data..."):
                success, message, data = export_user_data(st.session_state.uid)
                if success and data:
                    st.success(message)
                    # Create download button
                    st.download_button(
                        label="Download Your Data (JSON)",
                        data=data,
                        file_name="user_data_export.json",
                        mime="application/json",
                        use_container_width=True
                    )
                    
                    # Check if the user has a collection and offer Excel export
                    try:
                        export_data = json.loads(data)
                        if export_data.get("collection"):
                            # Convert collection to DataFrame
                            df = pd.DataFrame(export_data["collection"])
                            excel_data = io.BytesIO()
                            df.to_excel(excel_data, index=False)
                            excel_data.seek(0)
                            
                            st.download_button(
                                label="Download Collection (Excel)",
                                data=excel_data,
                                file_name="collection_export.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                    except Exception as e:
                        st.warning(f"Could not create Excel export: {str(e)}")
                else:
                    st.error(message)
        
        st.markdown("</div>", unsafe_allow_html=True)

    # Delete account tab
    with account_tabs[2]:
        st.markdown("""
        <div style="display:block !important; visibility:visible !important; opacity:1 !important;">
        """, unsafe_allow_html=True)
        
        st.error("⚠️ Warning: This action cannot be undone!")
        st.write("Deleting your account will permanently remove all your data, including your collection and saved trades.")
        
        confirm_deletion = st.checkbox("I understand this will permanently delete all my data", key="confirm_deletion")
        
        if confirm_deletion:
            if st.button("DELETE MY ACCOUNT", type="primary", key="confirm_delete_btn", use_container_width=True):
                # Delete user account
                with st.spinner("Deleting your account..."):
                    success, message = delete_user_account(st.session_state.uid)
                    if success:
                        st.success(message)
                        st.session_state.user = None
                        st.session_state.uid = None
                        st.info("Redirecting to login page...")
                        time.sleep(2)
                        st.switch_page("pages/0_login.py")
                    else:
                        st.error(message)
        else:
            st.info("Please confirm that you want to delete your account by checking the box above.")
        
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main() 