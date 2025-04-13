from asyncio import all_tasks
from cmath import e
import traceback
import streamlit as st
import pandas as pd
from PIL import Image
import io
import base64
import json
from datetime import datetime
import os
import zipfile
from pathlib import Path
from modules.display_case.manager import DisplayCaseManager
import ast
from modules.database.service import DatabaseService
import requests
from modules.core.firebase_manager import FirebaseManager
from modules.ui.components.CardDisplay import CardDisplay
from modules.ui.branding import BrandingComponent
from modules.ui.theme.theme_manager import ThemeManager
import sys
from modules.core.collection_manager import CollectionManager

# Add the project root directory to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Set page config must be the first Streamlit command
st.set_page_config(
    page_title="Display Case",
    page_icon="image",
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

def display_case_grid(display_case):
    """Display cards in a grid using the CardDisplay component"""
    if not display_case:
        st.info("No display case selected")
        return

    if not display_case.get('cards'):
        st.info("No cards found in this display case")
        return

    # Use the CardDisplay component to show the cards
    CardDisplay.display_grid(display_case['cards'])

def create_new_display_case(display_case_manager, collection):
    """Create a new display case"""
    st.subheader("Create New Display Case")
    
    # Get all unique tags from the collection
    all_tags = set()
    if isinstance(collection, pd.DataFrame):
        # Handle DataFrame collection
        if 'tags' in collection.columns:
            for tags in collection['tags'].dropna():
                if isinstance(tags, str):
                    try:
                        parsed = ast.literal_eval(tags)
                        if isinstance(parsed, list):
                            all_tags.update(str(tag).strip().lower() for tag in parsed if tag)
                        else:
                            all_tags.update(tag.strip().lower() for tag in tags.split(',') if tag.strip())
                    except:
                        all_tags.update(tag.strip().lower() for tag in tags.split(',') if tag.strip())
    else:
        # Handle list collection
        for card in collection:
            if isinstance(card, dict):
                tags = card.get('tags', [])
            else:
                tags = card.tags if hasattr(card, 'tags') else []
            
            if isinstance(tags, str):
                try:
                    parsed = ast.literal_eval(tags)
                    if isinstance(parsed, list):
                        all_tags.update(str(tag).strip().lower() for tag in parsed if tag)
                    else:
                        all_tags.update(tag.strip().lower() for tag in tags.split(',') if tag.strip())
                except:
                    all_tags.update(tag.strip().lower() for tag in tags.split(',') if tag.strip())
            elif isinstance(tags, list):
                all_tags.update(str(tag).strip().lower() for tag in tags if tag)
    
    # Create form for new display case
    with st.form("new_display_case"):
        name = st.text_input("Display Case Name")
        description = st.text_area("Description")
        selected_tags = st.multiselect("Select Tags", sorted(list(all_tags)))
        
        submitted = st.form_submit_button("Create Display Case")
        
        if submitted:
            if not name:
                st.error("Please enter a name for the display case")
                return
                
            if not selected_tags:
                st.error("Please select at least one tag")
                return
                
            # Create the display case
            success = display_case_manager.create_display_case(name, description, selected_tags)
            if success:
                st.success(f"Display case '{name}' created successfully!")
                st.rerun()
            else:
                st.error("Failed to create display case")

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
    
    st.title("Display Case")
    
    # Get user ID
    uid = st.session_state.uid
    if not uid:
        st.error("User ID not found")
        return

    # Get user's collection
    collection = DatabaseService.get_user_collection(uid)
    if collection is None:
        st.error("Failed to load collection")
        return

    # Initialize display case manager
    display_case_manager = DisplayCaseManager(uid, collection)

    # Create tabs for different sections
    tab1, tab2 = st.tabs(["View Display Cases", "Create New Display Case"])
    
    with tab1:
        # Load display cases
        display_cases = display_case_manager.load_display_cases()
        if not display_cases:
            st.info("No display cases found. Create one to get started!")
        else:
            # Display case selection
            case_names = list(display_cases.keys())
            selected_case = st.selectbox("Select Display Case", case_names)

            if selected_case:
                # Get the selected display case
                display_case = display_cases[selected_case]
                
                # Display case info
                st.markdown(f"### {display_case['name']}")
                st.markdown(f"**Description:** {display_case.get('description', 'No description')}")
                st.markdown(f"**Total Value:** ${display_case.get('total_value', 0):,.2f}")
                st.markdown(f"**Number of Cards:** {len(display_case.get('cards', []))}")
                
                # Add delete button
                if st.button("Delete Display Case", type="secondary"):
                    if display_case_manager.delete_display_case(selected_case):
                        st.success(f"Display case '{selected_case}' deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete display case")
                
                # Display the grid
                display_case_grid(display_case)
    
    with tab2:
        create_new_display_case(display_case_manager, collection)

if __name__ == "__main__":
    main()
