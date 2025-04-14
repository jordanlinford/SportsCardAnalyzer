import streamlit as st
import pandas as pd
import io
from datetime import datetime, date
from PIL import Image
import base64
import requests
import traceback
from pathlib import Path
import sys
from modules.core.market_analysis import MarketAnalyzer
from modules.core.collection_manager import CollectionManager
from scrapers.ebay_interface import EbayInterface
from modules.database.service import DatabaseService
from modules.database.models import Card, CardCondition
from modules.ui.collection_display import CardDisplay
from modules.ui.theme.theme_manager import ThemeManager
from io import BytesIO
import json
from modules.core.card_value_analyzer import CardValueAnalyzer
from modules.core.firebase_manager import FirebaseManager
from modules.ui.components import CardDisplay
from modules.ui.theme.theme_manager import ThemeManager
import os
from modules.ui.branding import BrandingComponent
from typing import List, Dict, Any, Union
import zipfile
import time

# Add the project root directory to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Set page config must be the first Streamlit command
st.set_page_config(
    page_title="Collection Manager - Sports Card Analyzer Pro",
    page_icon="��",
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

# Initialize Firebase
firebase_manager = FirebaseManager.get_instance()
if not firebase_manager._initialized:
    if not firebase_manager.initialize():
        st.error("Failed to initialize Firebase. Please try again later.")
        st.stop()

# Check if user is authenticated
if not st.session_state.user or not st.session_state.uid:
    st.error("No user ID found. Please log in again.")
    st.info("Redirecting you to the login page...")
    time.sleep(2)  # Give user time to read the message
    st.switch_page("pages/0_login.py")
    st.stop()

# Initialize other session state variables
if 'editing_card' not in st.session_state:
    st.session_state.editing_card = None
if 'editing_data' not in st.session_state:
    st.session_state.editing_data = None

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

def init_session_state():
    """Initialize session state variables"""
    if 'collection' not in st.session_state:
        st.session_state.collection = []
    
    if 'editing_card' not in st.session_state:
        st.session_state.editing_card = None
    
    if 'editing_data' not in st.session_state:
        st.session_state.editing_data = None
    
    if 'total_value' not in st.session_state:
        st.session_state.total_value = 0
    
    if 'total_cost' not in st.session_state:
        st.session_state.total_cost = 0
    
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = "View Collection"
    
    # User authentication state
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'uid' not in st.session_state:
        st.session_state.uid = None
    if 'collection' not in st.session_state:
        st.session_state.collection = load_collection_from_firebase()
    if 'edit_mode' not in st.session_state:
        st.session_state.edit_mode = False
    if 'selected_card' not in st.session_state:
        st.session_state.selected_card = None
    if 'search_query' not in st.session_state:
        st.session_state.search_query = ""
    if 'filter_condition' not in st.session_state:
        st.session_state.filter_condition = "All"
    if 'sort_by' not in st.session_state:
        st.session_state.sort_by = "player_name"

def convert_df_to_excel(df):
    """Convert DataFrame to Excel file"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Collection')
        worksheet = writer.sheets['Collection']
        
        # Set column widths
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(str(col))
            )
            worksheet.set_column(idx, idx, max_length + 2)
    
    return output.getvalue()

def update_card_values():
    """Update card values using the CardValueAnalyzer"""
    try:
        if not st.session_state.collection:
            st.error("No cards in collection")
            return 0, 0
        
        analyzer = CardValueAnalyzer()
        total_value = 0
        total_cost = 0
        
        for idx, card in enumerate(st.session_state.collection):
            try:
                # Get current value
                current_value = analyzer.analyze_card_value(
                    safe_get(card, 'player_name', ''),
                    safe_get(card, 'year', ''),
                    safe_get(card, 'card_set', ''),
                    safe_get(card, 'card_number', ''),
                    safe_get(card, 'variation', ''),
                    safe_get(card, 'condition', '')
                )
                
                # Update card value - handle both Card objects and dictionaries
                if hasattr(card, 'current_value'):
                    card.current_value = current_value
                else:
                    card['current_value'] = current_value
                
                # Calculate ROI
                purchase_price = float(safe_get(card, 'purchase_price', 0))
                roi = ((current_value - purchase_price) / purchase_price * 100) if purchase_price > 0 else 0
                
                # Update ROI - handle both Card objects and dictionaries
                if hasattr(card, 'roi'):
                    card.roi = roi
                else:
                    card['roi'] = roi
                
                # Update totals
                total_value += current_value
                total_cost += purchase_price
                
            except Exception as card_error:
                st.warning(f"Warning: Could not update value for card {idx + 1}. Error: {str(card_error)}")
                continue
        
        # Save updated collection
        if save_collection_to_firebase():
            st.success("Card values updated successfully!")
        else:
            st.error("Failed to save updated values to database.")
        
        return total_value, total_cost
    
    except Exception as e:
        st.error(f"Error updating card values: {str(e)}")
        return 0, 0

def search_card_details(player_name, year, card_set, card_number, variation, condition):
    """Search for card details using the CardValueAnalyzer"""
    try:
        analyzer = CardValueAnalyzer()
        current_value = analyzer.analyze_card_value(
            player_name,
            year,
            card_set,
            card_number,
            variation,
            condition
        )
        
        return {
            'current_value': current_value,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    except Exception as e:
        st.error(f"Error searching card details: {str(e)}")
        return None

def display_add_card_form():
    """Display form for adding a new card"""
    # Check if we have pre-populated data from market analysis
    if 'prefilled_card' in st.session_state:
        st.info("Card details pre-populated from market analysis. Please review and complete the form.")
    
    with st.form("add_card_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Get pre-populated data if available
            prefilled = st.session_state.get('prefilled_card', {})
            
            player_name = st.text_input("Player Name", value=prefilled.get('player_name', ''), key="player_name")
            year = st.text_input("Year", value=prefilled.get('year', ''), key="year")
            card_set = st.text_input("Card Set", value=prefilled.get('card_set', ''), key="card_set")
            card_number = st.text_input("Card Number", value=prefilled.get('card_number', ''), key="card_number")
            variation = st.text_input("Variation", value=prefilled.get('variation', ''), key="variation")
        
        with col2:
            condition = st.selectbox(
                "Condition",
                ["Raw", "PSA 1", "PSA 2", "PSA 3", "PSA 4", "PSA 5", "PSA 6", "PSA 7", "PSA 8", "PSA 9", "PSA 10", "Graded Other"],
                key="condition"
            )
            
            purchase_price = st.number_input(
                "Purchase Price", 
                min_value=0.0, 
                step=0.01, 
                value=float(prefilled.get('purchase_price', 0)), 
                key="purchase_price"
            )
            
            current_value = st.number_input(
                "Current Value", 
                min_value=0.0, 
                step=0.01, 
                value=float(prefilled.get('current_value', 0)), 
                key="current_value"
            )
            
            purchase_date = st.date_input("Purchase Date", value=datetime.now().date(), key="purchase_date")
            notes = st.text_area("Notes", key="notes")
            tags = st.text_input("Tags (comma-separated)", key="tags")
        
        # Display pre-populated image if available
        if prefilled.get('photo'):
            st.image(prefilled['photo'], caption="Card Image from Market Analysis", use_container_width=True)
        else:
            photo = st.file_uploader("Upload Photo", type=["jpg", "jpeg", "png"], key="photo")
        
        # Add submit button
        submitted = st.form_submit_button("Add Card")
        
        if submitted:
            # Validate required fields
            if not player_name or not year or not card_set:
                st.error("Please fill in all required fields (Player Name, Year, Card Set)")
                return
            
            try:
                # Create new card
                new_card = {
                    'player_name': player_name,
                    'year': year,
                    'card_set': card_set,
                    'card_number': card_number,
                    'variation': variation,
                    'condition': condition,
                    'purchase_price': float(purchase_price),
                    'current_value': float(current_value),
                    'purchase_date': purchase_date.strftime('%Y-%m-%d'),
                    'notes': notes,
                    'tags': [tag.strip() for tag in tags.split(',') if tag.strip()],
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Handle photo
                if prefilled.get('photo'):
                    new_card['photo'] = prefilled['photo']
                elif photo:
                    # Process image with PIL
                    img = Image.open(photo)
                    
                    # First try with normal compression
                    buffer = BytesIO()
                    img.thumbnail((400, 500))
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.save(buffer, format="JPEG", quality=50, optimize=True)
                    encoded_image = base64.b64encode(buffer.getvalue()).decode()
                    
                    # If image is still too large, compress more aggressively
                    if len(encoded_image) > 900000:
                        buffer = BytesIO()
                        img.thumbnail((300, 375))  # Reduce dimensions further
                        img.save(buffer, format="JPEG", quality=30, optimize=True)  # Reduce quality further
                        encoded_image = base64.b64encode(buffer.getvalue()).decode()
                        
                        # If still too large, try one more time with even more compression
                        if len(encoded_image) > 900000:
                            buffer = BytesIO()
                            img.thumbnail((200, 250))  # Reduce dimensions even further
                            img.save(buffer, format="JPEG", quality=20, optimize=True)  # Reduce quality even further
                            encoded_image = base64.b64encode(buffer.getvalue()).decode()
                    
                    new_card['photo'] = f"data:image/jpeg;base64,{encoded_image}"
                
                # Initialize collection if not exists
                if 'collection' not in st.session_state:
                    st.session_state.collection = []
                
                # Convert DataFrame to list if needed
                if isinstance(st.session_state.collection, pd.DataFrame):
                    st.session_state.collection = st.session_state.collection.to_dict('records')
                
                # Create a function to check if a card already exists
                def card_exists(card, collection):
                    """Check if a card already exists in the collection"""
                    try:
                        # Get card attributes, handling both Card objects and dictionaries
                        if hasattr(card, 'player_name'):
                            card_name = card.player_name
                            card_year = card.year
                            card_set = card.card_set
                            card_number = card.card_number
                        else:
                            card_name = card.get('player_name')
                            card_year = card.get('year')
                            card_set = card.get('card_set')
                            card_number = card.get('card_number')
                        
                        # Check against existing cards
                        for existing_card in collection:
                            if hasattr(existing_card, 'player_name'):
                                existing_name = existing_card.player_name
                                existing_year = existing_card.year
                                existing_set = existing_card.card_set
                                existing_number = existing_card.card_number
                            else:
                                existing_name = existing_card.get('player_name')
                                existing_year = existing_card.get('year')
                                existing_set = existing_card.get('card_set')
                                existing_number = existing_card.get('card_number')
                            
                            if (card_name == existing_name and 
                                card_year == existing_year and 
                                card_set == existing_set and 
                                card_number == existing_number):
                                return True
                        return False
                    except Exception as e:
                        print(f"Error checking if card exists: {str(e)}")
                        print(f"Card data: {card}")
                        return False
                
                # Filter out duplicates
                new_cards = [card for card in [new_card] if not card_exists(card, st.session_state.collection)]
                
                if len(new_cards) < 1:
                    st.warning("Skipped 0 duplicate cards.")
                
                # Append only new cards to existing collection
                st.session_state.collection = st.session_state.collection + new_cards
                
                # Save to Firebase
                if save_collection_to_firebase():
                    st.success("Card added successfully!")
                    # Clear pre-populated data
                    if 'prefilled_card' in st.session_state:
                        del st.session_state.prefilled_card
                    # Switch back to View Collection tab
                    st.session_state.current_tab = "View Collection"
                    st.rerun()
                else:
                    st.error("Failed to save card to database. Please try again.")
            
            except Exception as e:
                st.error(f"Error adding card: {str(e)}")
                st.write("Debug: Error traceback:", traceback.format_exc())

def generate_share_link(collection_data):
    """Generate a shareable link for the collection"""
    try:
        # Convert collection data to a list of dictionaries
        serializable_collection = []
        for card in collection_data:
            if hasattr(card, 'to_dict'):
                # If it's a Card object, convert to dict
                card_dict = card.to_dict()
            elif isinstance(card, dict):
                # If it's already a dict, use it directly
                card_dict = card.copy()
            else:
                # Skip any other types
                continue
            
            # Ensure all values are JSON serializable
            processed_card = {}
            for key, value in card_dict.items():
                if isinstance(value, (datetime, date)):
                    processed_card[key] = value.isoformat()
                elif isinstance(value, (int, float, str, bool, type(None))):
                    processed_card[key] = value
                elif isinstance(value, list):
                    processed_card[key] = [str(item) for item in value]
                else:
                    processed_card[key] = str(value)
            
            serializable_collection.append(processed_card)
        
        # Convert to JSON
        collection_json = json.dumps(serializable_collection)
        encoded_data = base64.urlsafe_b64encode(collection_json.encode()).decode()
        return f"?share={encoded_data}"
    except Exception as e:
        st.error(f"Error generating share link: {str(e)}")
        return None

def load_shared_collection(share_param):
    """Load a shared collection from URL parameters"""
    try:
        decoded_data = base64.urlsafe_b64decode(share_param.encode())
        shared_collection = json.loads(decoded_data)
        
        # Convert dictionaries back to Card objects
        if isinstance(shared_collection, list):
            from modules.core.card import Card
            shared_collection = [Card.from_dict(card) if isinstance(card, dict) else card for card in shared_collection]
        
        return shared_collection
    except Exception as e:
        st.error("Invalid share link")
        return None

def display_collection_summary(filtered_collection):
    """Display collection summary with responsive metrics"""
    st.subheader("Collection Summary")
    
    if not has_cards(filtered_collection):
        st.info("No cards in collection")
        return
    
    # Calculate summary metrics with proper type conversion
    total_value = sum(
        float(card.get('current_value', 0)) if isinstance(card, dict)
        else float(getattr(card, 'current_value', 0)) if hasattr(card, 'current_value')
        else 0.0
        for card in filtered_collection
    )
    total_cost = sum(
        float(card.get('purchase_price', 0)) if isinstance(card, dict)
        else float(getattr(card, 'purchase_price', 0)) if hasattr(card, 'purchase_price')
        else 0.0
        for card in filtered_collection
    )
    total_roi = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
    
    # Display metrics in a mobile-friendly layout
    metrics_container = st.container()
    with metrics_container:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Cards", len(filtered_collection))
            st.metric("Total Value", f"${total_value:,.2f}")
        with col2:
            st.metric("Total Cost", f"${total_cost:,.2f}")
            st.metric("Overall ROI", f"{total_roi:,.1f}%")

def _convert_condition_to_index(condition):
    """Convert condition string to index in our condition list"""
    condition_map = {
        'PSA 10': 'Mint',
        'PSA 9': 'Near Mint',
        'PSA 8': 'Excellent',
        'PSA 7': 'Very Good',
        'PSA 6': 'Good',
        'PSA 5': 'Poor',
        'Mint': 'Mint',
        'Near Mint': 'Near Mint',
        'Excellent': 'Excellent',
        'Very Good': 'Very Good',
        'Good': 'Good',
        'Poor': 'Poor'
    }
    return condition_map.get(condition, 'Mint')

def _convert_index_to_condition(index):
    """Convert index to condition string"""
    conditions = ["Mint", "Near Mint", "Excellent", "Very Good", "Good", "Poor"]
    return conditions[index]

def _parse_date(date_str):
    """Parse date string in various formats to datetime.date object"""
    if not date_str:
        return datetime.now().date()
    
    # If it's already a datetime object, return its date
    if isinstance(date_str, datetime):
        return date_str.date()
    
    # If it's already a date object, return it
    if isinstance(date_str, date):
        return date_str
    
    try:
        # Try parsing ISO format first
        return datetime.fromisoformat(str(date_str)).date()
    except ValueError:
        try:
            # Try parsing simple date format
            return datetime.strptime(str(date_str), '%Y-%m-%d').date()
        except ValueError:
            # If all parsing fails, return current date
            return datetime.now().date()

def edit_card_form(card_index, card_data):
    """Display form for editing a card"""
    with st.form("edit_card_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Convert Card object to dict if needed
            if hasattr(card_data, 'to_dict'):
                card_dict = card_data.to_dict()
            elif isinstance(card_data, dict):
                card_dict = card_data
            else:
                st.error("Invalid card data format")
                return
                
            player_name = st.text_input("Player Name", value=safe_get(card_dict, 'player_name', ''), key="edit_player_name")
            year = st.text_input("Year", value=safe_get(card_dict, 'year', ''), key="edit_year")
            card_set = st.text_input("Card Set", value=safe_get(card_dict, 'card_set', ''), key="edit_card_set")
            card_number = st.text_input("Card Number", value=safe_get(card_dict, 'card_number', ''), key="edit_card_number")
            variation = st.text_input("Variation", value=safe_get(card_dict, 'variation', ''), key="edit_variation")
        
        with col2:
            # Get the current condition
            current_condition = safe_get(card_dict, 'condition', 'Raw')
            
            # Define all possible conditions
            conditions = ["Raw", "PSA 1", "PSA 2", "PSA 3", "PSA 4", "PSA 5", "PSA 6", "PSA 7", "PSA 8", "PSA 9", "PSA 10", "Graded Other"]
            
            # Find the index of the current condition, default to 0 if not found
            try:
                condition_index = conditions.index(current_condition)
            except ValueError:
                condition_index = 0
            
            condition = st.selectbox(
                "Condition",
                conditions,
                index=condition_index,
                key="edit_condition"
            )
            purchase_price = st.number_input(
                "Purchase Price",
                min_value=0.0,
                step=0.01,
                value=float(safe_get(card_dict, 'purchase_price', 0)),
                key="edit_purchase_price"
            )
            purchase_date = st.date_input(
                "Purchase Date",
                value=_parse_date(safe_get(card_dict, 'purchase_date')),
                key="edit_purchase_date"
            )
            notes = st.text_area("Notes", value=safe_get(card_dict, 'notes', ''), key="edit_notes")
            tags = st.text_input(
                "Tags (comma-separated)",
                value=', '.join(safe_get(card_dict, 'tags', [])),
                key="edit_tags"
            )
        
        photo = st.file_uploader("Upload New Photo", type=["jpg", "jpeg", "png"], key="edit_photo")
        
        # Create two columns for buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            # Add submit button
            submitted = st.form_submit_button("Save Changes")
        
        with col2:
            # Add cancel button
            if st.form_submit_button("Cancel"):
                st.session_state.editing_card = None
                st.session_state.editing_data = None
                st.rerun()
        
        with col3:
            # Add delete button
            if st.form_submit_button("Delete Card"):
                # Generate card_id from the card data
                card_id = f"{card_dict['player_name']}_{card_dict['year']}_{card_dict['card_set']}_{card_dict['card_number']}".replace(" ", "_").lower()
                if delete_card(card_id):
                    st.session_state.editing_card = None
                    st.session_state.editing_data = None
                    st.rerun()
        
        if submitted:
            # Validate required fields
            if not player_name or not year or not card_set:
                st.error("Please fill in all required fields (Player Name, Year, Card Set)")
                return
            
            # Get current value
            card_details = search_card_details(
                player_name,
                year,
                card_set,
                card_number,
                variation,
                condition
            )
            
            if not card_details:
                st.error("Could not determine current value for this card")
                return
            
            # Update card data
            updated_card = {
                'player_name': player_name,
                'year': year,
                'card_set': card_set,
                'card_number': card_number,
                'variation': variation,
                'condition': condition,
                'purchase_price': purchase_price,
                'purchase_date': purchase_date.strftime('%Y-%m-%d'),
                'current_value': card_details['current_value'],
                'last_updated': card_details['last_updated'],
                'notes': notes,
                'roi': ((card_details['current_value'] - purchase_price) / purchase_price * 100) if purchase_price > 0 else 0,
                'tags': [tag.strip() for tag in tags.split(',') if tag.strip()]
            }
            
            # Handle photo upload
            if photo:
                try:
                    # Process image with PIL
                    img = Image.open(photo)
                    
                    # First try with normal compression
                    buffer = BytesIO()
                    img.thumbnail((400, 500))
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.save(buffer, format="JPEG", quality=50, optimize=True)
                    encoded_image = base64.b64encode(buffer.getvalue()).decode()
                    
                    # If image is still too large, compress more aggressively
                    if len(encoded_image) > 900000:
                        buffer = BytesIO()
                        img.thumbnail((300, 375))  # Reduce dimensions further
                        img.save(buffer, format="JPEG", quality=30, optimize=True)  # Reduce quality further
                        encoded_image = base64.b64encode(buffer.getvalue()).decode()
                        
                        # If still too large, try one more time with even more compression
                        if len(encoded_image) > 900000:
                            buffer = BytesIO()
                            img.thumbnail((200, 250))  # Reduce dimensions even further
                            img.save(buffer, format="JPEG", quality=20, optimize=True)  # Reduce quality even further
                            encoded_image = base64.b64encode(buffer.getvalue()).decode()
                    
                    updated_card['photo'] = f"data:image/jpeg;base64,{encoded_image}"
                except Exception as e:
                    st.warning(f"Warning: Could not process uploaded image. Error: {str(e)}")
            
            # Update the card in the collection
            if hasattr(st.session_state.collection[card_index], 'to_dict'):
                # If it's a Card object, update its attributes
                for key, value in updated_card.items():
                    setattr(st.session_state.collection[card_index], key, value)
            else:
                # If it's a dictionary, update it directly
                st.session_state.collection[card_index].update(updated_card)
            
            # Save changes to Firebase
            if save_collection_to_firebase():
                st.success("Card updated successfully!")
                st.session_state.editing_card = None
                st.session_state.editing_data = None
                st.rerun()
            else:
                st.error("Failed to save changes to database.")

def load_collection_from_firebase():
    """Load the collection from Firebase"""
    try:
        if not st.session_state.uid:
            st.error("No user ID found. Please log in again.")
            st.info("Redirecting you to the login page...")
            time.sleep(2)
            st.switch_page("pages/0_login.py")
            return []
        
        # Ensure Firebase is initialized
        if not firebase_manager._initialized:
            if not firebase_manager.initialize():
                st.error("Failed to connect to Firebase. Please try again later.")
                return []
        
        # Get collection using DatabaseService
        collection = DatabaseService.get_user_collection(st.session_state.uid)
        
        if collection is None:
            st.error("Failed to load collection. Please try again.")
            return []
            
        print(f"Successfully loaded {len(collection)} cards from Firebase")
        return collection
        
    except Exception as e:
        print(f"Error loading collection: {str(e)}")
        print("Debug: Error traceback:", traceback.format_exc())
        return []

def save_collection_to_firebase():
    """Save the collection to Firebase"""
    try:
        if not st.session_state.uid:
            st.error("No user ID found. Please log in again.")
            return False
        
        if not st.session_state.collection:
            print("No cards to save")
            return True
        
        # Convert collection to list of Card objects
        cards = []
        for card in st.session_state.collection:
            try:
                if hasattr(card, 'to_dict'):
                    card_dict = card.to_dict()
                else:
                    card_dict = card
                cards.append(Card.from_dict(card_dict))
            except Exception as e:
                print(f"Error converting card to Card object: {str(e)}")
                continue
        
        # Save collection using DatabaseService
        success = DatabaseService.save_user_collection(st.session_state.uid, cards)
        
        if success:
            print(f"Successfully saved {len(cards)} cards to Firebase")
            return True
        else:
            print("Failed to save collection to Firebase")
            return False
        
    except Exception as e:
        print(f"Error saving collection: {str(e)}")
        print("Debug: Error traceback:", traceback.format_exc())
        return False

def display_collection_grid(filtered_collection):
    """Display the collection in a grid format with edit functionality."""
    # Check if collection is empty
    if filtered_collection is None or (isinstance(filtered_collection, pd.DataFrame) and filtered_collection.empty) or (isinstance(filtered_collection, list) and len(filtered_collection) == 0):
        st.info("No cards found matching your filters.")
        return
        
    # Convert to list of dictionaries if it's a DataFrame
    if isinstance(filtered_collection, pd.DataFrame):
        filtered_collection = filtered_collection.to_dict('records')
    
    # Create a list of card indices for reference
    card_indices = list(range(len(filtered_collection)))
    
    # Display grid with proper index handling
    CardDisplay.display_grid(
        filtered_collection,
        on_click=lambda idx: (
            setattr(st.session_state, 'editing_card', idx),
            setattr(st.session_state, 'editing_data', filtered_collection[idx]),
            st.rerun()
        )
    )

def display_collection_table(filtered_collection):
    """Display collection in a table format."""
    if filtered_collection is None or (isinstance(filtered_collection, pd.DataFrame) and filtered_collection.empty) or (isinstance(filtered_collection, list) and len(filtered_collection) == 0):
        st.info("No cards to display")
        return
    
    # Convert collection to DataFrame for display
    df = pd.DataFrame([
        card.to_dict() if hasattr(card, 'to_dict') else card 
        for card in filtered_collection
    ])
    
    # Ensure tags are always lists
    if 'tags' in df.columns:
        df['tags'] = df['tags'].apply(lambda x: x if isinstance(x, list) else [x] if pd.notna(x) else [])
    
    # Define column order and configuration
    column_config = {
        "player_name": st.column_config.TextColumn("Player Name", width="medium"),
        "year": st.column_config.TextColumn("Year", width="small"),
        "card_set": st.column_config.TextColumn("Card Set", width="medium"),
        "card_number": st.column_config.TextColumn("Card #", width="small"),
        "variation": st.column_config.TextColumn("Variation", width="medium"),
        "condition": st.column_config.TextColumn("Condition", width="medium"),
        "purchase_price": st.column_config.NumberColumn("Purchase Price", format="$%.2f", width="small"),
        "current_value": st.column_config.NumberColumn("Current Value", format="$%.2f", width="small"),
        "roi": st.column_config.NumberColumn("ROI", format="%.1f%%", width="small"),
        "purchase_date": st.column_config.DateColumn("Purchase Date", format="YYYY-MM-DD", width="small"),
        "last_updated": st.column_config.DatetimeColumn("Last Updated", format="YYYY-MM-DD HH:mm", width="medium"),
        "notes": st.column_config.TextColumn("Notes", width="large"),
        "tags": st.column_config.ListColumn("Tags", width="medium"),
        "photo": st.column_config.ImageColumn("Photo", width="small")
    }
    
    # Reorder columns to match the desired display order
    column_order = [
        "player_name", "year", "card_set", "card_number", "variation", 
        "condition", "purchase_price", "current_value", "roi", 
        "purchase_date", "last_updated", "notes", "tags", "photo"
    ]
    
    # Filter columns to only those that exist in the DataFrame
    column_order = [col for col in column_order if col in df.columns]
    
    # Display table with specified configuration
    st.dataframe(
        df[column_order],
        use_container_width=True,
        hide_index=True,
        column_config=column_config
    )

def has_cards(collection):
    """Check if collection has any cards"""
    if collection is None:
        return False
    if isinstance(collection, pd.DataFrame):
        return not collection.empty
    return len(collection) > 0

def safe_get(card, key, default=None):
    """Safely get a value from a card, whether it's a Card object or dictionary."""
    if hasattr(card, 'to_dict'):
        card_dict = card.to_dict()
        return card_dict.get(key, default)
    elif isinstance(card, dict):
        return card.get(key, default)
    return default

def display_collection():
    """Display the collection view."""
    # Get collection from session state
    collection = st.session_state.collection if hasattr(st.session_state, 'collection') else []
    
    # Display options
    view_type = st.radio("View Type", ["Grid", "Table"], horizontal=True)
    
    if view_type == "Grid":
        CardDisplay.display_grid(collection, on_click=lambda i: st.session_state.update({
            'editing_card': i,
            'editing_data': collection[i]
        }))
    else:
        CardDisplay.display_table(collection)

def generate_sample_template():
    """Generate a sample Excel template for collection upload"""
    # Create sample data with correct column names
    sample_data = {
        'player_name': ['Michael Jordan', 'LeBron James'],
        'year': ['1986', '2003'],
        'card_set': ['Fleer', 'Topps Chrome'],
        'card_number': ['57', '123'],
        'variation': ['Base', 'Refractor'],
        'condition': ['PSA 9', 'PSA 10'],
        'purchase_date': ['2023-01-15', ''],  # Optional
        'purchase_price': [150.00, ''],  # Optional
        'notes': ['Rookie Card', '']  # Optional
    }
    
    # Create DataFrame
    df = pd.DataFrame(sample_data)
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Collection Template')
        
        # Get workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Collection Template']
        
        # Add formatting
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9E1F2',
            'border': 1
        })
        
        # Format headers
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 15)  # Set column width
        
        # Add instructions
        instructions = [
            "Required Fields:",
            "- player_name: Full name of the player",
            "- year: Year the card was produced (e.g., 1986)",
            "- card_set: Name of the set (e.g., Topps, Panini Prizm)",
            "- card_number: The card number in the set",
            "- variation: Type of card (e.g., Base, Refractor, Prizm)",
            "- condition: Card condition (e.g., PSA 9, Raw)",
            "- purchase_price: How much you paid for the card",
            "- purchase_date: When you bought the card (YYYY-MM-DD)",
            "",
            "Optional Fields:",
            "- notes: Any additional information about the card",
            "",
            "Notes:",
            "- Leave optional fields blank if not applicable",
            "- Dates will default to today's date if left blank",
            "- Purchase amounts will default to 0 if left blank"
        ]
        
        for row_num, instruction in enumerate(instructions, start=len(df) + 3):
            worksheet.write(row_num, 0, instruction)
    
    return output.getvalue()

def delete_card(card_id: str) -> bool:
    """Delete a card from the collection"""
    try:
        # Get Firebase client
        firebase_manager = FirebaseManager.get_instance()
        if not firebase_manager._initialized:
            if not firebase_manager.initialize():
                print("Error: Failed to initialize Firebase")
                return False
                
        db = firebase_manager.db
        if not db:
            print("Error: Firestore client not initialized")
            return False

        # Get the user's cards collection reference
        cards_ref = db.collection('users').document(st.session_state.uid).collection('cards')
        
        # Ensure card_id is a string
        if not isinstance(card_id, str):
            card_id = str(card_id)
        
        # Delete the card document from Firebase
        try:
            doc_ref = cards_ref.document(card_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_ref.delete()
                print(f"Successfully deleted card {card_id} from Firebase")
            else:
                print(f"Card {card_id} not found in Firebase")
        except Exception as firebase_error:
            print(f"Error deleting from Firebase: {str(firebase_error)}")
            return False
        
        # Remove the card from the local collection
        if hasattr(st.session_state, 'collection'):
            # Find the card in the collection and remove it
            for i, card in enumerate(st.session_state.collection):
                # Generate the card's ID to compare
                if hasattr(card, 'to_dict'):
                    card_dict = card.to_dict()
                else:
                    card_dict = card
                current_card_id = f"{card_dict['player_name']}_{card_dict['year']}_{card_dict['card_set']}_{card_dict['card_number']}".replace(" ", "_").lower()
                if current_card_id == card_id:
                    st.session_state.collection.pop(i)
                    print(f"Successfully removed card {card_id} from local collection")
                    break
        
        # Clear the cache to ensure the collection is reloaded
        st.cache_data.clear()
        
        return True
    except Exception as e:
        print(f"Error deleting card: {str(e)}")
        print(f"Debug: Error traceback: {traceback.format_exc()}")
        return False

def update_card(card_index, updated_data):
    """Update a card in the collection"""
    try:
        if not st.session_state.collection:
            st.error("No cards in collection")
            return False
        
        # Get the card to update
        card = st.session_state.collection[card_index]
        
        # Generate the card ID
        if hasattr(card, 'to_dict'):
            card_dict = card.to_dict()
        else:
            card_dict = card
        
        card_id = f"{card_dict['player_name']}_{card_dict['year']}_{card_dict['card_set']}_{card_dict['card_number']}".replace(" ", "_").lower()
        
        # Update the card in the subcollection
        cards_ref = db.collection('users').document(st.session_state.uid).collection('cards')
        cards_ref.document(card_id).set(updated_data)
        
        # Update the card in the local collection
        st.session_state.collection[card_index] = updated_data
        
        # Update the user document's last_updated timestamp
        db.collection('users').document(st.session_state.uid).update({
            'last_updated': datetime.now().isoformat()
        })
        
        st.success("Card updated successfully!")
        return True
        
    except Exception as e:
        st.error(f"Error updating card: {str(e)}")
        st.write("Debug: Error traceback:", traceback.format_exc())
        return False

def add_card(card_data):
    """Add a new card to the collection"""
    try:
        # Generate a unique ID for the card
        card_id = f"{card_data['player_name']}_{card_data['year']}_{card_data['card_set']}_{card_data['card_number']}".replace(" ", "_").lower()
        
        # Add the card to the subcollection
        cards_ref = db.collection('users').document(st.session_state.uid).collection('cards')
        cards_ref.document(card_id).set(card_data)
        
        # Add the card to the local collection
        if not hasattr(st.session_state, 'collection'):
            st.session_state.collection = []
        st.session_state.collection.append(card_data)
        
        # Update the user document's last_updated timestamp
        db.collection('users').document(st.session_state.uid).update({
            'last_updated': datetime.now().isoformat()
        })
        
        st.success("Card added successfully!")
        return True
        
    except Exception as e:
        st.error(f"Error adding card: {str(e)}")
        st.write("Debug: Error traceback:", traceback.format_exc())
        return False

def import_collection(file):
    """Import a collection from an Excel file"""
    try:
        # Read the Excel file
        df = pd.read_excel(file)
        
        # Validate required columns
        required_columns = ['player_name', 'year', 'card_set', 'card_number', 'variation', 'condition']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Missing required columns: {', '.join(missing_columns)}")
            return False
        
        # Convert DataFrame to list of dictionaries
        cards = df.to_dict('records')
        
        # Process each card
        for card in cards:
            # Add default values for optional fields
            if 'purchase_date' not in card or pd.isna(card['purchase_date']):
                card['purchase_date'] = datetime.now().isoformat()
            if 'purchase_price' not in card or pd.isna(card['purchase_price']):
                card['purchase_price'] = 0.0
            if 'notes' not in card or pd.isna(card['notes']):
                card['notes'] = ""
            if 'photo' not in card or pd.isna(card['photo']):
                card['photo'] = "https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image"
            if 'tags' not in card or pd.isna(card['tags']):
                card['tags'] = []
            if 'last_updated' not in card or pd.isna(card['last_updated']):
                card['last_updated'] = datetime.now().isoformat()
            
            # Add the card to the subcollection
            card_id = f"{card['player_name']}_{card['year']}_{card['card_set']}_{card['card_number']}".replace(" ", "_").lower()
            cards_ref = db.collection('users').document(st.session_state.uid).collection('cards')
            cards_ref.document(card_id).set(card)
            
            # Add the card to the local collection
            if not hasattr(st.session_state, 'collection'):
                st.session_state.collection = []
            st.session_state.collection.append(card)
        
        # Update the user document's last_updated timestamp
        db.collection('users').document(st.session_state.uid).update({
            'last_updated': datetime.now().isoformat()
        })
        
        st.success(f"Successfully imported {len(cards)} cards!")
        return True
        
    except Exception as e:
        st.error(f"Error importing collection: {str(e)}")
        st.write("Debug: Error traceback:", traceback.format_exc())
        return False

def export_collection():
    """Export the collection to an Excel file"""
    try:
        if not st.session_state.collection:
            st.error("No cards in collection")
            return None
        
        # Convert collection to DataFrame
        df = pd.DataFrame([
            card.to_dict() if hasattr(card, 'to_dict') else card 
            for card in st.session_state.collection
        ])
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Collection')
            
            # Get workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Collection']
            
            # Add formatting
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D9E1F2',
                'border': 1
            })
            
            # Format headers
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 15)  # Set column width
        
        return output.getvalue()
        
    except Exception as e:
        st.error(f"Error exporting collection: {str(e)}")
        st.write("Debug: Error traceback:", traceback.format_exc())
        return None

def main():
    # Initialize session state
    init_session_state()
    
    # Initialize session state for user if not exists
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'uid' not in st.session_state:
        st.session_state.uid = None
    
    # If user is not logged in, redirect to login page
    if not st.session_state.user:
        st.switch_page("pages/0_login.py")
    
    st.title("Collection Manager")
    
    # Load collection from Firebase if needed
    if not has_cards(st.session_state.collection):
        st.session_state.collection = load_collection_from_firebase()
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Add Cards", "View Collection", "Share Collection", "Import/Export"])
    
    # If we're editing a card, show the edit form first
    if st.session_state.editing_card is not None and st.session_state.editing_data is not None:
        st.subheader("Edit Card")
        edit_card_form(st.session_state.editing_card, st.session_state.editing_data)
        if st.button("Cancel Edit", use_container_width=True):
            st.session_state.editing_card = None
            st.session_state.editing_data = None
            st.rerun()
        return  # Exit early to prevent showing other content
    
    # Tab 1: Add Cards
    with tab1:
        st.subheader("Add New Card")
        display_add_card_form()
    
    # Tab 2: View Collection
    with tab2:
        if has_cards(st.session_state.collection):
            # Search and filter section
            with st.container():
                st.markdown('<div class="search-filters">', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    search_term = st.text_input(
                        "Search Collection",
                        help="Search by player name, year, set, or tags"
                    )
                with col2:
                    tag_filter = st.text_input(
                        "Filter by Tag",
                        help="Enter a tag to filter the collection"
                    )
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Update values button
            if st.button("Update All Values", use_container_width=True):
                with st.spinner("Updating collection values..."):
                    total_value, total_cost = update_card_values()
                    st.success("Collection values updated successfully!")
            
            # Filter collection
            filtered_collection = st.session_state.collection.copy()
            if search_term:
                filtered_collection = [
                    card for card in filtered_collection
                    if search_term.lower() in str(card).lower()
                ]
            if tag_filter:
                filtered_collection = [
                    card for card in filtered_collection
                    if any(tag_filter.lower() in tag.lower() for tag in safe_get(card, 'tags', []))
                ]
            
            # Display collection summary
            display_collection_summary(filtered_collection)
            
            # Display collection with view toggle
            st.subheader("Your Collection")
            
            # Add view toggle
            view_mode = st.radio(
                "View Mode",
                ["Grid View", "Table View"],
                horizontal=True,
                label_visibility="collapsed"
            )
            
            if view_mode == "Grid View":
                display_collection_grid(filtered_collection)
            else:
                display_collection_table(filtered_collection)
        
        else:
            st.info("Your collection is empty. Add some cards to get started!")
    
    # Tab 3: Share Collection
    with tab3:
        st.subheader("Share Your Collection")
        
        # Generate share link for the entire collection
        if has_cards(st.session_state.collection):
            share_link = generate_share_link(st.session_state.collection)
            st.markdown(f"""
            <div class="share-section">
                <p>Share your collection with others using this link:</p>
                <a href="?{share_link}" class="share-button" target="_blank">
                    📤 Share Collection
                </a>
            </div>
            """, unsafe_allow_html=True)
            
            # Option to share filtered collection
            st.write("---")
            st.subheader("Share Filtered Collection")
            
            # Add filter options
            player_filter = st.text_input("Filter by Player Name")
            year_filter = st.text_input("Filter by Year")
            set_filter = st.text_input("Filter by Card Set")
            tag_filter = st.text_input("Filter by Tags")
            
            # Apply filters
            filtered_collection = st.session_state.collection.copy()
            if player_filter:
                filtered_collection = [
                    card for card in filtered_collection
                    if player_filter.lower() in str(safe_get(card, 'player_name', '')).lower()
                ]
            if year_filter:
                filtered_collection = [
                    card for card in filtered_collection
                    if year_filter.lower() in str(safe_get(card, 'year', '')).lower()
                ]
            if set_filter:
                filtered_collection = [
                    card for card in filtered_collection
                    if set_filter.lower() in str(safe_get(card, 'card_set', '')).lower()
                ]
            if tag_filter:
                filtered_collection = [
                    card for card in filtered_collection
                    if any(tag_filter.lower() in tag.lower() for tag in safe_get(card, 'tags', []))
                ]
            
            if isinstance(filtered_collection, pd.DataFrame):
                if not filtered_collection.empty:
                    filtered_share_link = generate_share_link(filtered_collection)
                    st.markdown(f"""
                    <div class="share-section">
                        <p>Share your filtered collection ({len(filtered_collection)} cards):</p>
                        <a href="?{filtered_share_link}" class="share-button" target="_blank">
                            📤 Share Filtered Collection
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("No cards match your filters.")
            else:
                if filtered_collection:  # For list type collections
                    filtered_share_link = generate_share_link(filtered_collection)
                    st.markdown(f"""
                    <div class="share-section">
                        <p>Share your filtered collection ({len(filtered_collection)} cards):</p>
                        <a href="?{filtered_share_link}" class="share-button" target="_blank">
                            📤 Share Filtered Collection
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("No cards match your filters.")
        else:
            st.info("Add some cards to your collection to generate a share link.")
    
    # Tab 4: Import/Export
    with tab4:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Export Collection")
            if has_cards(st.session_state.collection):
                # Export format selection
                export_format = st.radio(
                    "Export Format",
                    ["Excel", "CSV", "JSON"],
                    horizontal=True,
                    help="Choose the format for your exported collection"
                )
                
                # Convert collection to DataFrame for export
                df = pd.DataFrame([
                    card.to_dict() if hasattr(card, 'to_dict') else card 
                    for card in st.session_state.collection
                ])
                
                # Handle different export formats
                if export_format == "Excel":
                    excel_data = export_collection()
                    if excel_data:
                        st.download_button(
                            label="Download Excel",
                            data=excel_data,
                            file_name=f"card_collection_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                elif export_format == "CSV":
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv_data,
                        file_name=f"card_collection_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:  # JSON
                    json_data = df.to_json(orient='records', date_format='iso')
                    st.download_button(
                        label="Download JSON",
                        data=json_data,
                        file_name=f"card_collection_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
            else:
                st.info("Add some cards to your collection to enable export.")
        
        with col2:
            st.subheader("Import Collection")
            
            # Import format selection
            import_format = st.radio(
                "Import Format",
                ["Excel", "CSV", "JSON"],
                horizontal=True,
                help="Choose the format of your collection file"
            )
            
            # File uploader with format-specific accept parameter
            accept = {
                "Excel": ".xlsx",
                "CSV": ".csv",
                "JSON": ".json"
            }[import_format]
            
            uploaded_file = st.file_uploader(
                f"Upload {import_format} file",
                type=[accept],
                help=f"Upload your collection in {import_format} format"
            )
            
            if uploaded_file:
                try:
                    # Progress indicator
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Read file based on format
                    status_text.text("Reading file...")
                    if import_format == "Excel":
                        imported_df = pd.read_excel(uploaded_file)
                    elif import_format == "CSV":
                        imported_df = pd.read_csv(uploaded_file)
                    else:  # JSON
                        imported_df = pd.read_json(uploaded_file)
                    
                    progress_bar.progress(20)
                    status_text.text("Validating data...")
                    
                    # Validate required columns
                    required_columns = ['player_name', 'year', 'card_set']
                    missing_columns = [col for col in required_columns if col not in imported_df.columns]
                    if missing_columns:
                        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
                    
                    # Add missing optional columns with default values
                    optional_columns = {
                        'card_number': '',
                        'variation': '',
                        'condition': 'Raw',
                        'purchase_price': 0.0,
                        'current_value': 0.0,
                        'purchase_date': datetime.now().strftime('%Y-%m-%d'),
                        'notes': '',
                        'photo': None,
                        'tags': '',
                        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    for col, default in optional_columns.items():
                        if col not in imported_df.columns:
                            imported_df[col] = default
                    
                    progress_bar.progress(40)
                    status_text.text("Processing data...")
                    
                    # Convert DataFrame to list of dictionaries
                    imported_collection = imported_df.to_dict('records')
                    
                    # Get existing collection
                    existing_collection = st.session_state.collection
                    if not isinstance(existing_collection, list):
                        existing_collection = []
                    
                    # Enhanced duplicate detection
                    def card_exists(card, collection):
                        """Check if a card already exists in the collection"""
                        try:
                            # Get card attributes, handling both Card objects and dictionaries
                            if hasattr(card, 'player_name'):
                                card_name = card.player_name
                                card_year = card.year
                                card_set = card.card_set
                                card_number = card.card_number
                            else:
                                card_name = card.get('player_name')
                                card_year = card.get('year')
                                card_set = card.get('card_set')
                                card_number = card.get('card_number')
                            
                            # Check against existing cards
                            for existing_card in collection:
                                if hasattr(existing_card, 'player_name'):
                                    existing_name = existing_card.player_name
                                    existing_year = existing_card.year
                                    existing_set = existing_card.card_set
                                    existing_number = existing_card.card_number
                                else:
                                    existing_name = existing_card.get('player_name')
                                    existing_year = existing_card.get('year')
                                    existing_set = existing_card.get('card_set')
                                    existing_number = existing_card.get('card_number')
                                
                                if (card_name == existing_name and 
                                    card_year == existing_year and 
                                    card_set == existing_set and 
                                    card_number == existing_number):
                                    return True
                            return False
                        except Exception as e:
                            print(f"Error checking if card exists: {str(e)}")
                            print(f"Card data: {card}")
                            return False
                    
                    progress_bar.progress(60)
                    status_text.text("Checking for duplicates...")
                    
                    # Filter out duplicates
                    new_cards = [card for card in imported_collection 
                               if not card_exists(card, existing_collection)]
                    
                    if len(new_cards) < len(imported_collection):
                        st.warning(f"Skipped {len(imported_collection) - len(new_cards)} duplicate cards.")
                    
                    progress_bar.progress(80)
                    status_text.text("Saving to database...")
                    
                    # Append only new cards to existing collection
                    updated_collection = existing_collection + new_cards
                    
                    # Save to Firebase
                    if save_collection_to_firebase():
                        progress_bar.progress(100)
                        status_text.text("Import complete!")
                        st.success(f"Successfully imported {len(new_cards)} new cards!")
                        st.balloons()
                        # Force refresh the collection from Firebase
                        st.session_state.collection = load_collection_from_firebase()
                        st.rerun()  # Force a rerun to update the UI
                    else:
                        st.error("Failed to save imported collection to database. Please try again.")
                
                except Exception as e:
                    st.error(f"Error importing file: {str(e)}")
                    st.write("Debug: Error traceback:", traceback.format_exc())
        
        # Add download template button
        st.download_button(
            label="Download Collection Template",
            data=generate_sample_template(),
            file_name="collection_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Download a template to help format your collection data for upload"
        )

if __name__ == "__main__":
    main()

