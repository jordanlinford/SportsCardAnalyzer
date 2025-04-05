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

st.set_page_config(
    page_title="Display Case - Sports Card Analyzer Pro",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

backgrounds = {
    "Minimal Dark": {
        "gradient": "linear-gradient(135deg, #1c1c1c, #2a2a2a)",
        "text": "#ffffff",
        "text_shadow": "2px 2px 4px rgba(0,0,0,0.5)"
    },
    "Steel Gray": {
        "gradient": "linear-gradient(135deg, #3e3e3e, #1f1f1f)",
        "text": "#ffffff",
        "text_shadow": "2px 2px 4px rgba(0,0,0,0.5)"
    },
    "Soft Light": {
        "gradient": "linear-gradient(135deg, #f0f0f0, #e0e0e0)",
        "text": "#000000",
        "text_shadow": "none"
    },
    "Blue Night": {
        "gradient": "linear-gradient(135deg, #1a2a6c, #b21f1f, #fdbb2d)",
        "text": "#ffffff",
        "text_shadow": "2px 2px 4px rgba(0,0,0,0.5)"
    }
}

def init_session_state():
    if 'display_case_manager' not in st.session_state:
        st.session_state.display_case_manager = None
    if 'collection' not in st.session_state:
        st.session_state.collection = pd.DataFrame(columns=[
            'player_name', 'year', 'card_set', 'card_number', 'variation',
            'condition', 'purchase_price', 'purchase_date', 'current_value',
            'last_updated', 'notes', 'photo', 'roi', 'tags'
        ])
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'uid' not in st.session_state:
        st.session_state.uid = None
    if 'bg_choice' not in st.session_state:
        st.session_state.bg_choice = "Minimal Dark"
    if 'last_uid' not in st.session_state:
        st.session_state.last_uid = None

def display_case_grid(display_case):
    """Display cards in a grid format, dynamically filtered from current collection"""
    if not display_case:
        st.info("No display case selected")
        return

    if not display_case.get('cards'):
        st.info("No cards found in this display case")
        return

    # Create a container for the grid
    with st.container():
        # Create a grid of columns
        cols = st.columns(3)
        
        for idx, card in enumerate(display_case['cards']):
            col = cols[idx % 3]  # Cycle through columns
            with col:
                try:
                    # Display only the card image
                    if card.get('photo'):
                        st.image(card['photo'], use_container_width=True)
                except Exception as e:
                    st.error(f"Failed to load image: {str(e)}")

def export_display_case(display_case):
    """Export display case data as a JSON file with enhanced card details."""
    try:
        export_data = {
            'display_case': {
                'name': display_case.get('name', ''),
                'description': display_case.get('description', ''),
                'tags': display_case['tags'],
                'created_date': display_case['created_date'],
                'total_value': display_case['total_value'],
                'total_cards': len(display_case['cards'])
            },
            'cards': []
        }
        
        for card in display_case['cards']:
            # Create a new dictionary with only serializable data
            card_data = {
                'player_name': str(card.get('player_name', '')),
                'year': str(card.get('year', '')),
                'card_set': str(card.get('card_set', '')),
                'card_number': str(card.get('card_number', '')),
                'variation': str(card.get('variation', '')),
                'condition': str(card.get('condition', '')),
                'current_value': float(card.get('current_value', 0)),
                'purchase_price': float(card.get('purchase_price', 0)),
                'purchase_date': str(card.get('purchase_date', '')),
                'roi': float(card.get('roi', 0)),
                'notes': str(card.get('notes', '')),
                'photo': str(card.get('photo', '')),
                'tags': [str(tag) for tag in card.get('tags', [])]
            }
            export_data['cards'].append(card_data)
        
        # Format the JSON with indentation for better readability
        return json.dumps(export_data, indent=2)
    except Exception as e:
        print(f"Error in export_display_case: {str(e)}")
        traceback.print_exc()
        return json.dumps({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, indent=2)

def create_backup():
    """Create a backup of all display cases and save as a zip file on desktop."""
    try:
        # Get the desktop path
        desktop = str(Path.home() / "Desktop")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(desktop, f"Sports_Card_Analyzer_Pro_Backup_{timestamp}")
        
        # Create backup directory
        os.makedirs(backup_dir, exist_ok=True)
        
        # Export each display case
        for case_name, display_case in st.session_state.display_case_manager.display_cases.items():
            # Create a safe filename
            safe_name = case_name.lower().replace(' ', '_')
            file_path = os.path.join(backup_dir, f"{safe_name}.json")
            
            # Export the display case data
            export_data = export_display_case(display_case)
            
            # Save to file
            with open(file_path, 'w') as f:
                f.write(export_data)
        
        # Create zip file
        zip_path = f"{backup_dir}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, backup_dir)
                    zipf.write(file_path, arcname)
        
        # Clean up the backup directory
        for root, dirs, files in os.walk(backup_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(backup_dir)
        
        return zip_path
    except Exception as e:
        st.error(f"Failed to create backup: {str(e)}")
        return None

def create_display_case_form():
    """Display form for creating a new display case"""
    st.subheader("Create New Display Case")
    
    # Show debug information
    if st.button("Show Collection Debug Info"):
        st.session_state.display_case_manager.debug_collection()
    
    # Get all available tags
    all_tags = st.session_state.display_case_manager.get_all_tags()
    
    # Create two columns for the form
    col1, col2 = st.columns(2)
    
    with col1:
        # Display case name
        name = st.text_input("Display Case Name")
        
        # Tag selection
        selected_tag = st.selectbox("Select Tag", options=all_tags)
        
        # Preview button
        if st.button("Preview Cards"):
            if selected_tag:
                matching_cards = []
                
                # Handle both DataFrame and list formats
                if isinstance(st.session_state.collection, pd.DataFrame):
                    for idx, card in st.session_state.collection.iterrows():
                        card_dict = card.to_dict()
                        card_tags = card_dict.get('tags', [])
                        
                        # Convert tags to list if it's a string
                        if isinstance(card_tags, str):
                            card_tags = [t.strip() for t in card_tags.split(',')]
                        elif not isinstance(card_tags, list):
                            card_tags = []
                        
                        # Check if the tag exists in the card's tags
                        if selected_tag.lower() in [t.lower() for t in card_tags]:
                            matching_cards.append(card_dict)
                else:
                    # Handle list format
                    for card in st.session_state.collection:
                        # Convert Card object to dictionary if needed
                        if hasattr(card, 'to_dict'):
                            card_dict = card.to_dict()
                        else:
                            card_dict = card
                        
                        card_tags = card_dict.get('tags', [])
                        
                        # Convert tags to list if it's a string
                        if isinstance(card_tags, str):
                            card_tags = [t.strip() for t in card_tags.split(',')]
                        elif not isinstance(card_tags, list):
                            card_tags = []
                        
                        # Check if the tag exists in the card's tags
                        if selected_tag.lower() in [t.lower() for t in card_tags]:
                            matching_cards.append(card_dict)
                
                if matching_cards:
                    st.success(f"Found {len(matching_cards)} cards with tag '{selected_tag}'")
                    
                    # Display preview grid
                    cols = st.columns(3)
                    for idx, card in enumerate(matching_cards):
                        col = cols[idx % 3]
                        with col:
                            try:
                                # Display card image if available
                                if card.get('photo'):
                                    st.image(card['photo'], use_container_width=True)
                                
                                # Display card details
                                st.markdown(f"""
                                    **{card.get('player_name', 'Unknown')}**
                                    - Year: {card.get('year', 'N/A')}
                                    - Value: ${card.get('current_value', 0):,.2f}
                                """)
                            except Exception as e:
                                st.error(f"Error displaying card: {str(e)}")
                else:
                    st.warning(f"No cards found with tag '{selected_tag}'")
    
    with col2:
        # Create display case button
        if st.button("Create Display Case"):
            if not name:
                st.error("Please enter a name for the display case")
                return
            
            if not selected_tag:
                st.error("Please select a tag")
                return
            
            try:
                # Debug logging
                st.write("Debug: Creating display case...")
                st.write(f"Debug: Name: {name}")
                st.write(f"Debug: Tag: {selected_tag}")
                st.write(f"Debug: Collection type: {type(st.session_state.collection)}")
                
                # Create the display case
                display_case = st.session_state.display_case_manager.create_simple_display_case(
                    name=name,
                    tag=selected_tag
                )
                
                if display_case:
                    st.success(f"Created display case '{name}' with {len(display_case.get('cards', []))} cards")
                    st.session_state.current_display_case = display_case
                else:
                    st.error("Failed to create display case. Please check the debug information above.")
            except Exception as e:
                st.error(f"Error creating display case: {str(e)}")
                st.write("Debug: Error details:")
                st.write(f"Error type: {type(e).__name__}")
                st.write(f"Error message: {str(e)}")
                import traceback
                st.write("Debug: Full traceback:")
                st.code(traceback.format_exc())

def has_cards(collection):
    """Helper function to check if collection has any cards."""
    if collection is None:
        return False
    if isinstance(collection, pd.DataFrame):
        return not collection.empty
    if isinstance(collection, list):
        return len(collection) > 0
    return False

def main():
    st.title("Display Case")
    init_session_state()
    
    # Check if user has changed
    if st.session_state.uid != st.session_state.last_uid:
        st.session_state.display_case_manager = None
        st.session_state.last_uid = st.session_state.uid

    # Load collection if needed
    if st.session_state.uid:
        if not has_cards(st.session_state.collection):
            db = DatabaseService()
            collection_data = db.get_user_collection(st.session_state.uid)
            
            if isinstance(collection_data, list) and len(collection_data) > 0:
                # Convert Card objects to dictionaries, ensuring tags are properly handled
                cards_dict = []
                for card in collection_data:
                    try:
                        if hasattr(card, 'to_dict'):
                            card_dict = card.to_dict()
                        else:
                            card_dict = dict(card)
                        # Ensure tags are in list format
                        if isinstance(card_dict.get('tags'), str):
                            card_dict['tags'] = [tag.strip() for tag in card_dict['tags'].split(',') if tag.strip()]
                        elif not isinstance(card_dict.get('tags'), list):
                            card_dict['tags'] = []
                        cards_dict.append(card_dict)
                    except Exception as e:
                        st.error(f"Error processing card: {str(e)}")
                
                st.session_state.collection = pd.DataFrame(cards_dict)
            elif isinstance(collection_data, pd.DataFrame) and not collection_data.empty:
                st.session_state.collection = collection_data
            else:
                st.session_state.collection = pd.DataFrame()

    # Initialize display case manager with the loaded collection
    if st.session_state.display_case_manager is None and st.session_state.uid:
        if has_cards(st.session_state.collection):
            st.session_state.display_case_manager = DisplayCaseManager(
                st.session_state.uid,
                st.session_state.collection
            )
            # Force refresh to ensure tags are loaded
            st.session_state.display_case_manager.load_display_cases(force_refresh=True)

    if not st.session_state.uid:
        st.error("Please log in to view and manage your display cases")
        return

    tab1, tab2 = st.tabs(["Create Display Case", "View Display Cases"])

    with tab1:
        # Display case creation section
        with st.expander("Create New Display Case", expanded=True):
            st.subheader("Create New Display Case")
            
            # Get display case name
            display_case_name = st.text_input("Display Case Name", key="new_display_case_name")
            
            # Get available tags
            if st.session_state.display_case_manager:
                available_tags = st.session_state.display_case_manager.get_all_tags()
                if available_tags:
                    tag = st.selectbox("Select Tag", options=available_tags, key="new_display_case_tag")
                else:
                    st.warning("No tags found in your collection. Please add tags to your cards first.")
                    return
            
            if st.button("Create Display Case", key="create_display_case"):
                if display_case_name and tag:
                    try:
                        # Create the display case
                        display_case = st.session_state.display_case_manager.create_simple_display_case(display_case_name, tag)
                        
                        if display_case:
                            st.success(f"Successfully created display case '{display_case_name}' with {len(display_case['cards'])} cards")
                            st.rerun()  # Refresh the page to show the new display case
                        else:
                            st.error("Failed to create display case. Please try again.")
                    except Exception as e:
                        st.error(f"Error creating display case: {str(e)}")
                else:
                    st.warning("Please enter both a display case name and select a tag")

    with tab2:
        if st.session_state.display_case_manager is None:
            st.info("Please add some cards to your collection first to create display cases.")
            return
            
        display_cases = st.session_state.display_case_manager.display_cases
        if display_cases:
            selected_case = st.selectbox("Select Display Case", options=list(display_cases.keys()))
            if selected_case:
                display_case = display_cases[selected_case]
                
                # Display case details
                st.subheader(display_case['name'])
                if display_case.get('description'):
                    st.write(display_case['description'])
                if display_case.get('tags'):
                    st.write(f"Tags: {', '.join(display_case['tags'])}")
                st.write(f"Total Value: ${display_case.get('total_value', 0):,.2f}")
                
                # Display case actions
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🔄 Refresh"):
                        st.session_state.display_case_manager.load_display_cases(force_refresh=True)
                        st.rerun()
                
                with col2:
                    if st.button("🗑️ Delete"):
                        if st.session_state.display_case_manager.delete_display_case(selected_case):
                            st.success(f"Deleted display case: {selected_case}")
                            st.rerun()
                        else:
                            st.error("Failed to delete display case")
                
                with col3:
                    share_url = st.session_state.display_case_manager.get_share_url(selected_case)
                    if share_url:
                        st.markdown(f"[🔗 Share]({share_url})")
                
                # Display the cards in a grid
                display_case_grid(display_case)
        else:
            st.info("No display cases found. Create one using the form above!")

if __name__ == "__main__":
    main() 
