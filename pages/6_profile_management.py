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
        # Get Firebase Manager instance and ensure it's initialized
        firebase_manager = FirebaseManager.get_instance()
        if not firebase_manager._initialized:
            if not firebase_manager.initialize():
                return False, "Failed to initialize Firebase connection"
        
        # Update user profile in Firebase using the static method
        success = FirebaseManager.update_user_profile(uid, profile_data)
        
        if success:
            return True, "Profile updated successfully!"
        else:
            return False, "Error updating profile. Please try again."
    except Exception as e:
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
    with ThemeManager.styled_card():
        st.subheader("Account Management")
        
        st.warning("WARNING: Important Account Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Create a password update section
            if st.button("Change Password", use_container_width=True):
                password_method = st.radio(
                    "Choose password reset method:",
                    ["Send Reset Email", "Set New Password Directly"]
                )
                
                if password_method == "Send Reset Email":
                    # Get user email from session state
                    user_email = st.session_state.user.get('email')
                    if not user_email:
                        st.error("User email not found. Please try again later.")
                    else:
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
            
            if st.button("Export Data", use_container_width=True):
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
        
        with col2:
            if st.button("Delete Account", type="secondary", use_container_width=True):
                # Confirm deletion with a modal
                confirm_deletion = st.checkbox("I understand this will permanently delete all my data", key="confirm_deletion")
                
                if confirm_deletion:
                    if st.button("CONFIRM DELETION", type="primary", use_container_width=True):
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

if __name__ == "__main__":
    main() 