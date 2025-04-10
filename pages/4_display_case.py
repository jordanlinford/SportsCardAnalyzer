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

# Initialize session state variables
if 'user' not in st.session_state:
    st.session_state.user = None
if 'uid' not in st.session_state:
    st.session_state.uid = None

st.set_page_config(
    page_title="Display Case - Sports Card Analyzer Pro",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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

def main():
    """Main function to display the display case page"""
    # Check if user is logged in
    if not st.session_state.user:
        st.warning("Please log in to view your display cases")
        st.switch_page("pages/0_login.py")
        return

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

    # Load display cases
    display_cases = display_case_manager.load_display_cases()
    if not display_cases:
        st.info("No display cases found. Create one to get started!")
        return

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
        
        # Display the grid
        display_case_grid(display_case)

if __name__ == "__main__":
    main()
