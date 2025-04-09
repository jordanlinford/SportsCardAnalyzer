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
from modules.ui.components.CardGrid import render_card_grid # type: ignore
from modules.ui.components.DisplayCaseHeader import render_display_case_header # type: ignore
from modules.core.firebase_manager import FirebaseManager
from modules.ui.components.LikeButton import render_like_button # type: ignore
from modules.ui.components.CommentsSection import render_comments_section

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
        
    # Check if user is logged in
    if st.session_state.user is None:
        try:
            # Get current user from Firebase
            current_user = FirebaseManager.get_current_user()
            if current_user:
                st.session_state.user = {
                    'uid': current_user.uid,
                    'email': current_user.email
                }
                st.session_state.uid = current_user.uid
        except Exception as e:
            st.error(f"Error initializing user session: {str(e)}")
            st.session_state.user = None
            st.session_state.uid = None
            
    # Initialize DisplayCaseManager if we have a user and collection
    if st.session_state.uid and not st.session_state.display_case_manager:
        try:
            st.session_state.display_case_manager = DisplayCaseManager(
                uid=st.session_state.uid,
                collection=st.session_state.collection
            )
        except Exception as e:
            st.error(f"Error initializing DisplayCaseManager: {str(e)}")
            st.session_state.display_case_manager = None

def display_case_grid(display_case):
    """Display cards in a grid format, dynamically filtered from current collection"""
    if not display_case:
        st.info("No display case selected")
        return

    if not display_case.get('cards'):
        st.info("No cards found in this display case")
        return

    # Add custom CSS for fixed width container
    st.markdown("""
        <style>
        .fixed-width-container {
            width: 100%;
            min-width: 800px;
            margin: 0 auto;
        }
        </style>
        """, unsafe_allow_html=True)

    # Create a container for the grid
    with st.container():
        st.markdown('<div class="fixed-width-container">', unsafe_allow_html=True)
        
        # Process cards in groups of 3
        for i in range(0, len(display_case['cards']), 3):
            # Create a row with 3 columns
            cols = st.columns(3)
            
            # Display up to 3 cards in this row
            for j in range(3):
                if i + j < len(display_case['cards']):
                    card = display_case['cards'][i + j]
                    with cols[j]:
                        try:
                            if card.get('photo'):
                                photo = card['photo']
                                # Check if the photo is a base64 string
                                if isinstance(photo, str) and photo.startswith('data:image'):
                                    try:
                                        # Extract the base64 part
                                        base64_data = photo.split(',')[1]
                                        # Decode the base64 string
                                        image_data = base64.b64decode(base64_data)
                                        # Create an image from the bytes
                                        image = Image.open(io.BytesIO(image_data))
                                        # Display the image
                                        st.image(image, use_container_width=True)
                                    except Exception as e:
                                        st.error(f"Failed to load base64 image: {str(e)}")
                                # Check if the photo is a URL
                                elif isinstance(photo, str) and (photo.startswith('http://') or photo.startswith('https://')):
                                    # Display the image from URL
                                    st.image(photo, use_container_width=True)
                                else:
                                    st.warning("Invalid image format")
                        except Exception as e:
                            st.error(f"Failed to display card: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)

def export_display_case(display_case):
    """Export display case data as a JSON file with enhanced card details."""
    try:
        export_data = {
            'display_case': {
                'name': display_case.get('name', ''),
                'description': display_case.get('description', ''),
                'tags': display_case.get('tags', []),
                'created_date': display_case.get('created_date', ''),
                'total_value': display_case.get('total_value', 0),
                'total_cards': len(display_case.get('cards', []))
            },
            'cards': []
        }
        
        for card in display_case.get('cards', []):
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
        # Log the error and return error response
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

def display_card(card):
    """Display a single card in the display case"""
    try:
        # Create columns for the card display
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Display card image
            if 'photo' in card and card['photo']:
                if card['photo'].startswith('data:image'):
                    # Handle base64 images
                    try:
                        st.image(card['photo'], use_container_width=True)
                    except Exception as e:
                        st.error(f"Error displaying image: {str(e)}")
                        st.image("https://via.placeholder.com/300x400?text=Image+Error", use_container_width=True)
                elif card['photo'].startswith('http'):
                    # Handle URL images
                    try:
                        response = requests.head(card['photo'], timeout=5)
                        if response.status_code == 200:
                            st.image(card['photo'], use_container_width=True)
                        else:
                            st.image("https://via.placeholder.com/300x400?text=Image+Not+Available", use_container_width=True)
                    except:
                        st.image("https://via.placeholder.com/300x400?text=Image+Not+Available", use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/300x400?text=No+Image", use_container_width=True)
            else:
                st.image("https://via.placeholder.com/300x400?text=No+Image", use_container_width=True)
        
        with col2:
            # Display card details
            st.markdown(f"""
            <div style="padding: 1rem;">
                <h2>{card.get('player_name', 'Unknown Player')}</h2>
                <p><strong>Year:</strong> {card.get('year', '')}</p>
                <p><strong>Set:</strong> {card.get('card_set', '')}</p>
                <p><strong>Number:</strong> {card.get('card_number', '')}</p>
                <p><strong>Condition:</strong> {card.get('condition', '')}</p>
                <p><strong>Purchase Price:</strong> ${card.get('purchase_price', 0):.2f}</p>
                <p><strong>Current Value:</strong> ${card.get('current_value', 0):.2f}</p>
                <p><strong>ROI:</strong> {card.get('roi', 0):.1f}%</p>
                <p><strong>Notes:</strong> {card.get('notes', '')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Add action buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Edit Card", use_container_width=True):
                    st.session_state.editing_card = card
                    st.session_state.current_tab = "View Collection"
                    st.rerun()
            with col2:
                if st.button("Remove from Display", use_container_width=True):
                    remove_card_from_display(card)
                    st.rerun()
    
    except Exception as e:
        st.error(f"Failed to display card: {str(e)}")
        st.write("Debug: Error traceback:", traceback.format_exc())

def handle_card_click(card):
    """Handle card click event"""
    st.session_state['selected_card'] = card
    st.session_state['show_card_details'] = True

def get_share_url(display_case):
    """Generate share URL for display case"""
    base_url = st.query_params.get('base_url', [''])[0]
    # Check if user information is available
    if 'user' in st.session_state and st.session_state.user and 'uid' in st.session_state.user:
        return f"{base_url}/case/{st.session_state.user['uid']}/{display_case['name'].lower().replace(' ', '-')}"
    else:
        # Return a default URL or handle the case where user is not logged in
        return f"{base_url}/case/public/{display_case['name'].lower().replace(' ', '-')}"

def handle_like(case_id: str, like: bool):
    """Handle like button click"""
    if st.session_state['display_case_manager'].like_display_case(case_id, like):
        st.rerun()

def main():
    st.title("Display Cases")
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
                case = display_cases[selected_case]
                
                # Render header
                render_display_case_header(
                    case,
                    on_share=get_share_url
                )
                
                # Add like button if case has an ID
                if 'id' in case:
                    likes, is_liked = st.session_state['display_case_manager'].get_case_likes(case['id'])
                    render_like_button(
                        case['id'],
                        initial_likes=likes,
                        is_liked=is_liked,
                        on_like=handle_like
                    )
                
                # Sorting options
                col1, col2 = st.columns([1, 3])
                with col1:
                    sort_by = st.selectbox(
                        "Sort by",
                        ["ROI", "Value", "Year", "Player"],
                        index=0
                    )
                with col2:
                    sort_order = st.radio(
                        "Order",
                        ["Descending", "Ascending"],
                        horizontal=True
                    )
                
                # Sort cards
                cards = case.get('cards', [])
                if sort_by == "ROI":
                    cards.sort(key=lambda x: x.get('roi', 0), reverse=(sort_order == "Descending"))
                elif sort_by == "Value":
                    cards.sort(key=lambda x: x.get('current_value', 0), reverse=(sort_order == "Descending"))
                elif sort_by == "Year":
                    cards.sort(key=lambda x: x.get('year', ''), reverse=(sort_order == "Descending"))
                elif sort_by == "Player":
                    cards.sort(key=lambda x: x.get('player_name', ''), reverse=(sort_order == "Descending"))
                
                # Render card grid
                render_card_grid(
                    cards,
                    on_click=handle_card_click
                )
                
                # Card details modal
                if st.session_state.get('show_card_details', False):
                    with st.expander("Card Details", expanded=True):
                        card = st.session_state['selected_card']
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.image(card.get('photo', ''), use_column_width=True)
                        with col2:
                            st.subheader(card.get('player_name', ''))
                            st.write(f"**Year:** {card.get('year', '')}")
                            st.write(f"**Card Set:** {card.get('card_set', '')}")
                            st.write(f"**Card Number:** {card.get('card_number', '')}")
                            st.write(f"**Variation:** {card.get('variation', '')}")
                            st.write(f"**Condition:** {card.get('condition', '')}")
                            st.write(f"**Purchase Price:** ${card.get('purchase_price', 0):,.2f}")
                            st.write(f"**Current Value:** ${card.get('current_value', 0):,.2f}")
                            st.write(f"**ROI:** {card.get('roi', 0):.1f}%")
                            st.write(f"**Purchase Date:** {card.get('purchase_date', '')}")
                            st.write(f"**Notes:** {card.get('notes', '')}")
                            st.write(f"**Tags:** {', '.join(card.get('tags', []))}")
                        
                            if st.button("Close"):
                                st.session_state['show_card_details'] = False
                                st.rerun()

                # Comments section if case has an ID
                if 'id' in case:
                    comments = st.session_state.display_case_manager.get_comments(case['id'])
                    render_comments_section(
                        case_id=case['id'],
                        comments=comments,
                        on_add_comment=st.session_state.display_case_manager.add_comment,
                        on_delete_comment=st.session_state.display_case_manager.delete_comment,
                        current_user_id=st.session_state['user']['uid'] if 'user' in st.session_state and st.session_state.user and 'uid' in st.session_state.user else None
                    )
        else:
            st.info("No display cases found. Create one using the form above!")

if __name__ == "__main__":
    main() 
