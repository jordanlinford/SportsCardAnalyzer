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
    """Display cards in a grid with hover effects"""
    if not display_case:
        st.info("No display case selected")
        return

    # Add refresh button
    if st.button("🔄 Refresh Display Case"):
        # Get the display case manager with required parameters
        uid = st.session_state.uid
        collection = DatabaseService.get_user_collection(uid)
        display_case_manager = DisplayCaseManager(uid, collection)
        # Refresh the display case
        display_case_manager.refresh_display_case(display_case['name'])
        st.success("Display case refreshed!")
        st.rerun()

    if not display_case.get('cards'):
        st.info("No cards found in this display case")
        return

    # Add custom CSS for hover effects
    st.markdown("""
        <style>
        .card-container {
            position: relative;
            width: 100%;
            margin-bottom: 1rem;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .card-image {
            width: 100%;
            height: 300px;
            object-fit: cover;
            transition: 0.3s;
        }
        .card-info {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 1rem;
            display: none;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            opacity: 0;
            transition: opacity 0.3s;
        }
        .card-container:hover .card-info {
            display: flex;
            opacity: 1;
        }
        .card-container:hover .card-image {
            transform: scale(1.05);
        }
        .card-title {
            font-size: 1.2rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        .card-details {
            font-size: 0.9rem;
            margin-bottom: 0.25rem;
        }
        .card-value {
            font-size: 1rem;
            font-weight: bold;
            color: #4CAF50;
        }
        </style>
    """, unsafe_allow_html=True)

    # Display cards in a grid with 4 columns
    cols = st.columns(4)
    for idx, card in enumerate(display_case['cards']):
        col = cols[idx % 4]
        with col:
            # Create card container with hover effect
            st.markdown(f"""
                <div class="card-container">
                    <img class="card-image" src="{card.get('photo', 'https://placehold.co/300x400/e6e6e6/666666.png?text=No+Image')}" alt="Card Image">
                    <div class="card-info">
                        <div class="card-title">{card.get('player_name', 'Unknown')}</div>
                        <div class="card-details">{card.get('year', '')} {card.get('card_set', '')}</div>
                        <div class="card-value">${card.get('value', 0):,.2f}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

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
            case_names = [case['name'] for case in display_cases]
            selected_case_name = st.selectbox("Select Display Case", case_names)

            if selected_case_name:
                # Get the selected display case
                selected_case = next((case for case in display_cases if case['name'] == selected_case_name), None)
                if selected_case:
                    # Display case details
                    st.subheader(selected_case['name'])
                    if selected_case.get('description'):
                        st.write(selected_case['description'])
                    
                    # Add delete button
                    if st.button("Delete Display Case", type="secondary"):
                        if display_case_manager.delete_display_case(selected_case_name):
                            st.success(f"Display case '{selected_case_name}' deleted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to delete display case")
                    
                    # Display cards in the case
                    if selected_case.get('cards'):
                        st.write(f"Total Cards: {len(selected_case['cards'])}")
                        st.write(f"Total Value: ${selected_case.get('total_value', 0):,.2f}")
                        
                        # Display cards in a grid
                        display_case_grid(selected_case)
                    else:
                        st.info("No cards in this display case yet.")
    
    with tab2:
        create_new_display_case(display_case_manager, collection)

if __name__ == "__main__":
    main()
