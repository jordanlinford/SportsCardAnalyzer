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
import ast
from google.cloud import firestore
import numpy as np

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
    
    if 'view_mode' not in st.session_state:
        st.session_state.view_mode = "Grid View"
    
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

def clean_nan_values(data):
    """Clean NaN values from a dictionary or DataFrame row"""
    try:
        if isinstance(data, dict):
            cleaned_data = {}
            for k, v in data.items():
                if pd.isna(v):
                    cleaned_data[k] = None
                elif isinstance(v, (pd.Series, np.ndarray)):
                    # Convert pandas Series/arrays to lists or scalars
                    if hasattr(v, 'size') and v.size == 0:
                        cleaned_data[k] = None
                    elif hasattr(v, 'size') and v.size == 1:
                        # Extract single value
                        cleaned_data[k] = v.item() if hasattr(v, 'item') else v[0]
                    else:
                        # Convert to list
                        cleaned_data[k] = v.tolist() if hasattr(v, 'tolist') else list(v)
                else:
                    cleaned_data[k] = v
            return cleaned_data
        elif isinstance(data, pd.Series):
            # Convert Series to dict with special handling
            result = {}
            for index, value in data.items():
                if pd.isna(value):
                    result[index] = None
                elif isinstance(value, (pd.Series, np.ndarray)):
                    # Handle nested Series/arrays
                    if hasattr(value, 'size') and value.size == 0:
                        result[index] = None
                    elif hasattr(value, 'size') and value.size == 1:
                        result[index] = value.item() if hasattr(value, 'item') else value[0]
                    else:
                        result[index] = value.tolist() if hasattr(value, 'tolist') else list(value)
                else:
                    result[index] = value
            return result
        return data
    except Exception as e:
        print(f"Error in clean_nan_values: {str(e)}")
        # If all else fails, return the original data
        return data

def update_card_values():
    """Update card values using the CardValueAnalyzer"""
    try:
        if not st.session_state.collection:
            st.error("No cards in collection")
            return 0, 0
        
        analyzer = CardValueAnalyzer()
        total_value = 0.0
        total_cost = 0.0
        
        # Create a copy of the collection to modify
        updated_collection = st.session_state.collection.copy()
        
        for idx, card in enumerate(updated_collection):
            try:
                # Clean NaN values from the card
                card = clean_nan_values(card)
                
                # Get eBay sale value
                ebay_value = analyzer.analyze_card_value(
                    safe_get(card, 'player_name', ''),
                    safe_get(card, 'year', ''),
                    safe_get(card, 'card_set', ''),
                    safe_get(card, 'card_number', ''),
                    safe_get(card, 'variation', ''),
                    safe_get(card, 'condition', '')
                )
                
                # Only update if eBay value is greater than 0
                if ebay_value > 0:
                    # Update card value - handle both Card objects and dictionaries
                    if hasattr(card, 'current_value'):
                        card.current_value = float(ebay_value)
                        card.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        card['current_value'] = float(ebay_value)
                        card['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Get purchase price and current value as floats
                purchase_price = float(safe_get(card, 'purchase_price', 0))
                current_value = float(safe_get(card, 'current_value', 0))
                
                # Calculate ROI
                roi = ((current_value - purchase_price) / purchase_price * 100) if purchase_price > 0 else 0
                
                # Update ROI - handle both Card objects and dictionaries
                if hasattr(card, 'roi'):
                    card.roi = float(roi)
                else:
                    card['roi'] = float(roi)
                
                # Update totals
                total_value += current_value
                total_cost += purchase_price
                
            except Exception as card_error:
                st.warning(f"Warning: Could not update value for card {idx + 1}. Error: {str(card_error)}")
                continue
        
        # Update the session state with the modified collection
        st.session_state.collection = updated_collection
        
        # Save changes to Firebase
        if save_collection_to_firebase():
            st.success("Collection values updated successfully!")
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
    
    # Create form
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
            # Create placeholder for status messages
            status_message = st.empty()
            
            # Validate required fields
            if not player_name or not year or not card_set:
                status_message.error("Please fill in all required fields (Player Name, Year, Card Set)")
                return
            
            try:
                with st.spinner("Adding card to collection..."):
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
                        'last_updated': datetime.now().isoformat(),
                        'created_at': datetime.now().strftime('%Y-%m-%d')  # Consistent format for recent additions
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
                    
                    # Check for duplicates more efficiently
                    is_duplicate = False
                    for existing_card in st.session_state.collection:
                        existing_player = safe_get(existing_card, 'player_name', '')
                        existing_year = safe_get(existing_card, 'year', '')
                        existing_set = safe_get(existing_card, 'card_set', '')
                        existing_number = safe_get(existing_card, 'card_number', '')
                        
                        if (player_name == existing_player and 
                            year == existing_year and 
                            card_set == existing_set and 
                            card_number == existing_number):
                            is_duplicate = True
                            status_message.warning(f"This card already exists in your collection: {player_name} {year} {card_set} #{card_number}")
                            time.sleep(2)  # Give time to read the message
                            break
                    
                    if not is_duplicate:
                        # Add the new card
                        st.session_state.collection.append(new_card)
                        
                        # Save to Firebase
                        if save_collection_to_firebase():
                            # Show success message
                            status_message.success(f"Card added successfully: {player_name} {year} {card_set} #{card_number}")
                            
                            # Update the Firebase version and modified timestamp
                            db = firebase_manager.db
                            db.collection('users').document(st.session_state.uid).update({
                                'last_modified': datetime.now().isoformat(),
                                'collection_version': firestore.Increment(1),  # Increment version number
                                'last_card_added_at': datetime.now().isoformat()  # Add timestamp for recent activity
                            })
                            
                            # Force a refresh of the collection data on next load
                            if 'last_refresh' in st.session_state:
                                del st.session_state.last_refresh
                            
                            # Clear pre-populated data
                            if 'prefilled_card' in st.session_state:
                                del st.session_state.prefilled_card
                            
                            # Set up for redirection to View Collection tab with Grid View
                            st.session_state.current_tab = "View Collection"
                            st.session_state.view_mode = "Grid View"
                            st.session_state.refresh_required = True
                            
                            # Give user time to see success message
                            time.sleep(1.5)
                            
                            # Rerun the app to apply changes
                            st.rerun()
                        else:
                            status_message.error("Failed to save card to database. Please try again.")
                    else:
                        # Already showed duplicate warning
                        pass
                
            except Exception as e:
                status_message.error(f"Error adding card: {str(e)}")
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
    total_value = 0.0
    total_cost = 0.0
    
    for card in filtered_collection:
        # Get purchase price and current value using safe_get
        purchase_price = safe_get(card, 'purchase_price', 0)
        current_value = safe_get(card, 'current_value', 0)
        
        # Add to totals (safe_get now handles float conversion)
        total_cost += float(purchase_price or 0)  # Handle None values
        total_value += float(current_value or 0)  # Handle None values
    
    # Calculate ROI
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
            st.metric("Total ROI", f"{total_roi:.1f}%")

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
            condition = st.selectbox(
                "Condition",
                options=["Raw", "PSA 1", "PSA 2", "PSA 3", "PSA 4", "PSA 5", "PSA 6", "PSA 7", "PSA 8", "PSA 9", "PSA 10"],
                index=["Raw", "PSA 1", "PSA 2", "PSA 3", "PSA 4", "PSA 5", "PSA 6", "PSA 7", "PSA 8", "PSA 9", "PSA 10"].index(safe_get(card_dict, 'condition', 'Raw')),
                key="edit_condition"
            )
            
        with col2:
            purchase_price = st.number_input(
                "Purchase Price ($)",
                min_value=0.0,
                value=float(safe_get(card_dict, 'purchase_price', 0)),
                key="edit_purchase_price"
            )
            current_value = st.number_input(
                "Current Value ($)",
                min_value=0.0,
                value=float(safe_get(card_dict, 'current_value', 0)),
                key="edit_current_value"
            )
            
            # Handle purchase date with proper parsing
            purchase_date_str = safe_get(card_dict, 'purchase_date', datetime.now().strftime('%Y-%m-%d'))
            try:
                # Try to parse the date, handling different formats
                if 'T' in purchase_date_str:
                    purchase_date = datetime.fromisoformat(purchase_date_str.split('T')[0]).date()
                else:
                    purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                purchase_date = datetime.now().date()
                
            purchase_date = st.date_input(
                "Purchase Date",
                value=purchase_date,
                key="edit_purchase_date"
            )
            
            notes = st.text_area("Notes", value=safe_get(card_dict, 'notes', ''), key="edit_notes")
            
            # Handle tags with proper default value
            tags_value = safe_get(card_dict, 'tags', [])
            if not isinstance(tags_value, list):
                tags_value = []
            tags = st.text_input(
                "Tags (comma-separated)", 
                value=','.join(tags_value), 
                key="edit_tags",
                help="Enter tags separated by commas"
            )
            
            # Display current image if exists
            current_photo = safe_get(card_dict, 'photo', '')
            if current_photo:
                st.image(current_photo, caption="Current Card Image", use_container_width=True)
            
            # Add image upload
            new_photo = st.file_uploader("Upload New Photo", type=["jpg", "jpeg", "png"], key="edit_photo")
        
        # Create two columns for the buttons
        button_col1, button_col2 = st.columns(2)
        
        with button_col1:
            update_button = st.form_submit_button("Update Card")
        with button_col2:
            delete_button = st.form_submit_button("🗑️ Delete Card", type="secondary")
        
        if update_button:
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
                'current_value': current_value,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'notes': notes,
                'roi': ((current_value - purchase_price) / purchase_price * 100) if purchase_price > 0 else 0,
                'tags': [tag.strip() for tag in tags.split(',') if tag.strip()]
            }
            
            # Handle photo update
            if new_photo:
                try:
                    # Process image with PIL
                    img = Image.open(new_photo)
                    
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
                    st.error(f"Error processing image: {str(e)}")
                    return
            elif current_photo:
                # Keep existing photo if no new one uploaded
                updated_card['photo'] = current_photo
            
            # Update the card in the collection
            if update_card(card_index, updated_card):
                st.success("Card updated successfully!")
                st.session_state.editing_card = None
                st.session_state.editing_data = None
                # Set redirection to View Collection tab with Grid View
                st.session_state.current_tab = "View Collection"
                st.session_state.view_mode = "Grid View"
                st.rerun()
            else:
                st.error("Failed to update card.")
                
        if delete_button:
            # Generate card_id for deletion
            card_id = f"{player_name}_{year}_{card_set}_{card_number}".replace(" ", "_").lower()
            
            # Attempt to delete the card
            if delete_card(card_id):
                st.success("Card deleted successfully!")
                st.session_state.editing_card = None
                st.session_state.editing_data = None
                # Set redirection to View Collection tab with Grid View
                st.session_state.current_tab = "View Collection"
                st.session_state.view_mode = "Grid View"
                st.rerun()
            else:
                st.error("Failed to delete card.")

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
        
        # Check if we need to skip cache
        force_reload = False
        if 'refresh_required' in st.session_state and st.session_state.refresh_required:
            force_reload = True
            st.session_state.refresh_required = False
        
        # Track the last time we refreshed the collection
        if 'last_refresh' not in st.session_state or force_reload:
            st.session_state.last_refresh = time.time()
            
            # Get collection using DatabaseService
            cards = DatabaseService.get_user_collection(st.session_state.uid)
            
            if cards is None:
                st.error("Failed to load collection. Please try again.")
                return []
            
            # Convert Card objects to dictionaries to prevent dataclass conversion errors
            collection = []
            for card in cards:
                try:
                    card_dict = None
                    if hasattr(card, 'to_dict') and callable(getattr(card, 'to_dict')):
                        # Handle Card objects
                        try:
                            card_dict = card.to_dict()
                        except Exception as dict_err:
                            print(f"Error in Card.to_dict(): {str(dict_err)}")
                            # Fallback: try converting the object to dict directly
                            card_dict = {k: getattr(card, k) for k in dir(card) 
                                        if not k.startswith('_') and not callable(getattr(card, k))}
                    elif isinstance(card, dict):
                        # Already a dict
                        card_dict = card.copy()
                    else:
                        # Try to convert object to dict
                        try:
                            card_dict = {k: getattr(card, k) for k in dir(card) 
                                        if not k.startswith('_') and not callable(getattr(card, k))}
                        except:
                            print(f"Could not convert object of type {type(card)} to dictionary")
                            continue
                    
                    # Clean and normalize the card data
                    if card_dict:
                        # Ensure all fields are proper Python types (not pandas/numpy)
                        cleaned_dict = clean_nan_values(card_dict)
                        
                        # Ensure basic fields exist
                        if 'player_name' not in cleaned_dict or cleaned_dict['player_name'] is None:
                            print(f"Skipping card with no player_name")
                            continue
                            
                        collection.append(cleaned_dict)
                    
                except Exception as e:
                    print(f"Error converting card: {str(e)}")
                    print(f"Card type: {type(card)}")
                    if hasattr(card, '__dict__'):
                        print(f"Card attributes: {card.__dict__}")
                    continue
            
            print(f"Successfully loaded {len(collection)} cards from Firebase")
            return collection
        else:
            # Check if it's been more than 5 minutes since last refresh
            current_time = time.time()
            if current_time - st.session_state.last_refresh > 300:  # 300 seconds = 5 minutes
                st.session_state.last_refresh = current_time
                cards = DatabaseService.get_user_collection(st.session_state.uid)
                if cards is None:
                    return []
                    
                # Convert Card objects to dictionaries with same robust handling
                collection = []
                for card in cards:
                    try:
                        card_dict = None
                        if hasattr(card, 'to_dict') and callable(getattr(card, 'to_dict')):
                            try:
                                card_dict = card.to_dict()
                            except Exception as dict_err:
                                print(f"Error in Card.to_dict(): {str(dict_err)}")
                                card_dict = {k: getattr(card, k) for k in dir(card) 
                                           if not k.startswith('_') and not callable(getattr(card, k))}
                        elif isinstance(card, dict):
                            card_dict = card.copy()
                        else:
                            try:
                                card_dict = {k: getattr(card, k) for k in dir(card) 
                                           if not k.startswith('_') and not callable(getattr(card, k))}
                            except:
                                continue
                        
                        if card_dict:
                            cleaned_dict = clean_nan_values(card_dict)
                            
                            # Ensure basic fields exist
                            if 'player_name' not in cleaned_dict or cleaned_dict['player_name'] is None:
                                continue
                                
                            collection.append(cleaned_dict)
                    except Exception as e:
                        print(f"Error auto-refresh converting card: {str(e)}")
                        continue
                
                print(f"Auto-refreshed {len(collection)} cards from Firebase")
                return collection
            else:
                # Use existing collection
                if hasattr(st.session_state, 'collection') and st.session_state.collection:
                    return st.session_state.collection
                else:
                    cards = DatabaseService.get_user_collection(st.session_state.uid)
                    if cards is None:
                        return []
                        
                    # Convert Card objects to dictionaries with same robust handling
                    collection = []
                    for card in cards:
                        try:
                            card_dict = None
                            if hasattr(card, 'to_dict') and callable(getattr(card, 'to_dict')):
                                try:
                                    card_dict = card.to_dict()
                                except Exception as dict_err:
                                    print(f"Error in Card.to_dict(): {str(dict_err)}")
                                    card_dict = {k: getattr(card, k) for k in dir(card) 
                                               if not k.startswith('_') and not callable(getattr(card, k))}
                            elif isinstance(card, dict):
                                card_dict = card.copy()
                            else:
                                try:
                                    card_dict = {k: getattr(card, k) for k in dir(card) 
                                               if not k.startswith('_') and not callable(getattr(card, k))}
                                except:
                                    continue
                            
                            if card_dict:
                                cleaned_dict = clean_nan_values(card_dict)
                                
                                # Ensure basic fields exist
                                if 'player_name' not in cleaned_dict or cleaned_dict['player_name'] is None:
                                    continue
                                    
                                collection.append(cleaned_dict)
                        except Exception as e:
                            print(f"Error fallback converting card: {str(e)}")
                            continue
                    
                    print(f"Loading {len(collection)} cards from Firebase (no cached collection)")
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
                # Prepare card dictionary
                if hasattr(card, 'to_dict'):
                    card_dict = card.to_dict()
                else:
                    card_dict = card.copy() if isinstance(card, dict) else {}
                
                # Clean up card data before conversion
                try:
                    # Ensure dates are in the correct format
                    for date_field in ['purchase_date', 'last_updated', 'created_at']:
                        if date_field in card_dict:
                            if isinstance(card_dict[date_field], (pd.Series, np.ndarray)):
                                # Convert array to string
                                if hasattr(card_dict[date_field], 'size') and card_dict[date_field].size > 0:
                                    card_dict[date_field] = str(card_dict[date_field].item(0))
                                else:
                                    card_dict[date_field] = datetime.now().isoformat()
                            elif pd.isna(card_dict[date_field]) or card_dict[date_field] is None:
                                card_dict[date_field] = datetime.now().isoformat()
                    
                    # Ensure tags is a list
                    if 'tags' in card_dict:
                        if isinstance(card_dict['tags'], (pd.Series, np.ndarray)):
                            # Convert to list
                            card_dict['tags'] = card_dict['tags'].tolist() if hasattr(card_dict['tags'], 'tolist') else list(card_dict['tags'])
                        elif isinstance(card_dict['tags'], str):
                            # Parse string to list
                            card_dict['tags'] = [tag.strip() for tag in card_dict['tags'].split(',') if tag.strip()]
                        elif card_dict['tags'] is None:
                            card_dict['tags'] = []
                    else:
                        card_dict['tags'] = []
                    
                    # Ensure numeric fields are proper numbers
                    for num_field in ['purchase_price', 'current_value', 'roi']:
                        if num_field in card_dict:
                            if isinstance(card_dict[num_field], (pd.Series, np.ndarray)):
                                # Convert array to float
                                if hasattr(card_dict[num_field], 'size') and card_dict[num_field].size > 0:
                                    card_dict[num_field] = float(card_dict[num_field].item(0))
                                else:
                                    card_dict[num_field] = 0.0
                            elif pd.isna(card_dict[num_field]) or card_dict[num_field] is None:
                                card_dict[num_field] = 0.0
                            else:
                                # Try to convert to float
                                try:
                                    card_dict[num_field] = float(card_dict[num_field])
                                except:
                                    card_dict[num_field] = 0.0
                
                    # Finally convert to Card object
                    card_obj = Card.from_dict(card_dict)
                    cards.append(card_obj)
                
                except Exception as prep_err:
                    print(f"Error preparing card data: {str(prep_err)}")
                    print(f"Card data that failed preparation: {card_dict}")
                    continue
                
            except Exception as e:
                print(f"Error converting card to Card object: {str(e)}")
                print(f"Card data that failed conversion: {card if isinstance(card, dict) else 'Non-dict card'}")
                continue
        
        # Save collection using DatabaseService
        if not cards:
            print("Warning: No valid Card objects to save")
            return False
            
        print(f"Attempting to save {len(cards)} cards to Firebase")
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

def display_collection_table(collection: List[Dict]):
    """Display collection in a table format."""
    if not collection:
        st.info("No cards to display")
        return
    
    # Convert the collection to a list of dictionaries first
    try:
        # Convert each item to a dictionary regardless of its type
        collection_dicts = []
        for card in collection:
            if hasattr(card, 'to_dict') and callable(getattr(card, 'to_dict')):
                # Card objects with to_dict method
                collection_dicts.append(card.to_dict())
            elif isinstance(card, dict):
                # Already a dictionary
                collection_dicts.append(card)
            elif hasattr(card, '__dict__'):
                # General object with attributes
                collection_dicts.append(card.__dict__)
            else:
                # Skip items that can't be converted
                st.warning(f"Skipped item of type {type(card)} that cannot be converted to dictionary")
                continue
        
        # Convert to DataFrame only after ensuring all items are dictionaries
        df = pd.DataFrame(collection_dicts)
        
        if df.empty:
            st.warning("No valid cards to display after conversion")
            return
            
    except Exception as e:
        st.error(f"Error converting collection to DataFrame: {str(e)}")
        st.write("Debug info: Collection type:", type(collection))
        if collection:
            st.write(f"First item type: {type(collection[0])}")
        return
    
    # Ensure all required columns exist
    required_columns = ['player_name', 'year', 'card_set', 'condition', 'purchase_price', 'current_value', 'tags']
    for col in required_columns:
        if col not in df.columns:
            df[col] = None
    
    # Format the DataFrame for display
    df_display = df.copy()
    
    # Format numeric columns
    df_display['purchase_price'] = df_display['purchase_price'].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")
    # Use current_value instead of ebay_value
    if 'current_value' in df_display.columns:
        df_display['current_value'] = df_display['current_value'].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")
    
    # Process tags column
    def format_tags(tags):
        if pd.isna(tags):
            return ""
        if isinstance(tags, str):
            try:
                # Try to parse as JSON/list
                parsed = ast.literal_eval(tags)
                if isinstance(parsed, list):
                    return ", ".join(str(tag).strip() for tag in parsed if tag)
                else:
                    return tags
            except:
                return tags
        elif isinstance(tags, list):
            return ", ".join(str(tag).strip() for tag in tags if tag)
        return str(tags)
    
    df_display['tags'] = df_display['tags'].apply(format_tags)
    
    # Select and order columns for display (use current_value instead of ebay_value)
    display_columns = ['player_name', 'year', 'card_set', 'condition', 'purchase_price', 'current_value', 'tags']
    # Ensure all columns exist
    for col in display_columns:
        if col not in df_display.columns:
            df_display[col] = ""
            
    df_display = df_display[display_columns]
    
    # Rename columns for display
    column_names = {
        'player_name': 'Player',
        'year': 'Year',
        'card_set': 'Set',
        'condition': 'Condition',
        'purchase_price': 'Purchase Price',
        'current_value': 'Current Value',
        'tags': 'Tags'
    }
    df_display = df_display.rename(columns=column_names)
    
    # Display the table
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Player": st.column_config.TextColumn("Player", width="medium"),
            "Year": st.column_config.TextColumn("Year", width="small"),
            "Set": st.column_config.TextColumn("Set", width="medium"),
            "Condition": st.column_config.TextColumn("Condition", width="small"),
            "Purchase Price": st.column_config.TextColumn("Purchase Price", width="small"),
            "Current Value": st.column_config.TextColumn("Current Value", width="small"),
            "Tags": st.column_config.TextColumn("Tags", width="large")
        }
    )

def has_cards(collection):
    """Check if collection has any cards"""
    try:
        if collection is None:
            return False
            
        if isinstance(collection, pd.DataFrame):
            # Explicit check to avoid DataFrame truthiness issues
            return len(collection) > 0 and not collection.empty
            
        if isinstance(collection, list):
            return len(collection) > 0
            
        # Handle other iterable types
        try:
            return len(collection) > 0
        except (TypeError, AttributeError):
            # Not an iterable or doesn't have a length
            return False
    except Exception as e:
        print(f"Error in has_cards: {str(e)}")
        return False

def safe_get(card, key, default=None):
    """Safely get a value from a card, whether it's a Card object or dictionary."""
    try:
        # Handle Card objects
        if hasattr(card, 'to_dict'):
            card_dict = card.to_dict()
            value = card_dict.get(key, default)
        # Handle dictionaries
        elif isinstance(card, dict):
            value = card.get(key, default)
        else:
            value = getattr(card, key, default)
        
        # Handle numeric values specifically
        if key in ['purchase_price', 'current_value']:
            try:
                # Handle various types of numeric values
                if value is None or pd.isna(value):
                    return float(default or 0)
                if isinstance(value, str):
                    # Remove any currency symbols and commas
                    value = value.replace('$', '').replace(',', '').strip()
                return float(value)
            except (ValueError, TypeError) as e:
                print(f"Error converting {key} value '{value}' to float: {str(e)}")
                return float(default or 0)
        
        return value
    except Exception as e:
        print(f"Error in safe_get for key {key}: {str(e)}")
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
                st.error("Failed to initialize Firebase")
                return False
                
        db = firebase_manager.db
        if not db:
            st.error("Firestore client not initialized")
            return False

        # Log deletion attempt (for debugging purposes)
        print(f"Starting deletion for card ID: {card_id}")
        
        # Get the user's cards collection reference
        cards_ref = db.collection('users').document(st.session_state.uid).collection('cards')
        
        # SIMPLE APPROACH: Try direct deletion first with minimal processing
        deletion_successful = False
        try:
            # Try a few common ID formats
            potential_ids = [
                card_id,  # Original ID
                card_id.lower(),  # Lowercase
                card_id.replace(' ', '_').lower(),  # Replace spaces with underscores
                "_".join([p.title() for p in card_id.split('_')]),  # Title case
                "_".join([p.lower() for p in card_id.split('_')])  # All lowercase
            ]
            
            for potential_id in potential_ids:
                try:
                    doc_ref = cards_ref.document(potential_id)
                    doc = doc_ref.get()
                    if doc.exists:
                        print(f"Found exact document match with ID: {potential_id}")
                        doc_ref.delete()
                        print(f"Deleted card from Firebase with ID: {potential_id}")
                        deletion_successful = True
                        break
                except Exception as e:
                    print(f"Error trying ID format {potential_id}: {str(e)}")
                    continue
                    
            if deletion_successful:
                # Update local collection if card exists there
                if hasattr(st.session_state, 'collection') and st.session_state.collection:
                    # Create a new list excluding the deleted card
                    st.session_state.collection = [
                        card for card in st.session_state.collection 
                        if not (isinstance(card, dict) and f"{card.get('player_name')}_{card.get('year')}_{card.get('card_set')}_{card.get('card_number')}".replace(" ", "_").lower() == card_id.lower())
                    ]
                
                # Add a timestamp to track the last modification time
                db.collection('users').document(st.session_state.uid).update({
                    'last_modified': datetime.now().isoformat(),
                    'collection_version': firestore.Increment(1)  # Increment version number
                })
                
                # Force a refresh of the collection data on next load
                if 'last_refresh' in st.session_state:
                    del st.session_state.last_refresh
                
                st.success(f"Card deleted successfully!")
                # Clear cache and return to view collection
                st.cache_data.clear()
                st.session_state.current_tab = "View Collection"
                st.session_state.view_mode = "Grid View"
                # Set flag for refreshing on next load
                st.session_state.refresh_required = True
                return True
        except Exception as e:
            print(f"Error in direct document deletion attempt: {str(e)}")
            # Continue to the more complex approach if direct deletion failed
            
        # BACKUP APPROACH: Parse card details from ID for more complex search
        parts = card_id.split('_')
        
        # Handle different ID formats more robustly
        if len(parts) < 3:  # At minimum need player_year_set
            st.warning(f"Invalid card ID format: {card_id}. Please try deleting a different card.")
            return False
            
        # Extract components - this is a more flexible approach
        # First try to find the year part which is most recognizable
        year_index = None
        for i, part in enumerate(parts):
            if part.isdigit() and (len(part) == 4 or len(part) == 2):
                year_index = i
                break
        
        if year_index is not None:
            # We found a year, use it to split other components
            player_name_parts = parts[:year_index]
            year = parts[year_index]
            
            # The rest might be set and number
            rest_parts = parts[year_index+1:]
            
            # If we have at least 2 more parts, assume the last is card number
            if len(rest_parts) >= 1:
                card_set_parts = rest_parts[:-1] if len(rest_parts) > 1 else rest_parts
                card_number = rest_parts[-1] if len(rest_parts) > 1 else ""
            else:
                card_set_parts = rest_parts
                card_number = ""
        else:
            # No obvious year, use a fallback approach
            if len(parts) >= 3:
                player_name_parts = [parts[0]]
                year = parts[1]
                card_set_parts = parts[2:-1] if len(parts) > 3 else [parts[2]]
                card_number = parts[-1] if len(parts) > 3 else ""
            else:
                # Not enough parts for a valid ID
                st.warning(f"Cannot parse card ID: {card_id}. Please try a different card.")
                return False
        
        # Reconstruct the components
        player_name = " ".join(player_name_parts).replace('_', ' ')
        card_set = " ".join(card_set_parts).replace('_', ' ')
        
        print(f"Parsed card details - Player: '{player_name}', Year: '{year}', Set: '{card_set}', Number: '{card_number}'")
        
        # Search for the card in Firebase by field values
        try:
            found = False
            all_cards = list(cards_ref.stream())
            print(f"Found {len(all_cards)} cards in Firebase to search")
            
            for doc in all_cards:
                try:
                    card_data = doc.to_dict()
                    
                    # Get card attributes for comparison
                    db_player = str(card_data.get('player_name', '')).lower()
                    db_year = str(card_data.get('year', ''))
                    db_set = str(card_data.get('card_set', '')).lower()
                    db_number = str(card_data.get('card_number', ''))
                    
                    # Check if this is a match (more flexible matching)
                    player_match = player_name.lower() in db_player or db_player in player_name.lower()
                    year_match = (
                        db_year == year or 
                        (len(year) == 2 and db_year[-2:] == year) or
                        (len(db_year) == 2 and year[-2:] == db_year)
                    )
                    set_match = card_set.lower() in db_set or db_set in card_set.lower()
                    number_match = not card_number or card_number == db_number
                    
                    # More flexible matching for better success rates
                    if (player_match and year_match) and (set_match or number_match):
                        try:
                            print(f"Found matching card with ID: {doc.id}")
                            cards_ref.document(doc.id).delete()
                            print(f"Deleted card from Firebase with ID: {doc.id}")
                            found = True
                            
                            # Update local collection
                            if hasattr(st.session_state, 'collection') and st.session_state.collection:
                                # Create a new list excluding the deleted card
                                st.session_state.collection = [
                                    card for card in st.session_state.collection 
                                    if not (isinstance(card, dict) and 
                                            (player_name.lower() in str(card.get('player_name', '')).lower() and
                                             year == str(card.get('year', '')) and
                                             (card_set.lower() in str(card.get('card_set', '')).lower() or
                                              (card_number and card_number == str(card.get('card_number', ''))))))
                                ]
                            
                            # Add a timestamp to track the last modification time
                            db.collection('users').document(st.session_state.uid).update({
                                'last_modified': datetime.now().isoformat(),
                                'collection_version': firestore.Increment(1)  # Increment version number
                            })
                            
                            # Force a refresh of the collection data on next load
                            if 'last_refresh' in st.session_state:
                                del st.session_state.last_refresh
                            
                            st.success(f"Successfully deleted {player_name} {year} {card_set} #{card_number or 'N/A'}")
                            # Clear cache and return to view collection
                            st.cache_data.clear()
                            st.session_state.current_tab = "View Collection"
                            st.session_state.view_mode = "Grid View"
                            # Set flag to refresh UI
                            st.session_state.refresh_required = True
                            return True
                        except Exception as delete_error:
                            print(f"Error deleting document {doc.id}: {str(delete_error)}")
                            continue
                except Exception as card_error:
                    print(f"Error checking Firebase card {doc.id}: {str(card_error)}")
                    continue
            
            if not found:
                st.warning(f"Card not found: {player_name} {year} {card_set} #{card_number or 'N/A'}")
                st.info("Try refreshing your collection by going to a different tab and back.")
                return False
                
        except Exception as e:
            print(f"Error in Firebase search: {str(e)}")
            st.warning(f"Error searching Firebase: {str(e)}")
            return False
    
    except Exception as e:
        print(f"Exception in delete_card: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        st.warning(f"Error while trying to delete card. Please try again.")
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
        
        # Update the card in the subcollection using firebase_manager
        firebase_manager = FirebaseManager.get_instance()
        if not firebase_manager._initialized:
            if not firebase_manager.initialize():
                st.error("Failed to initialize Firebase. Please try again later.")
                return False
        
        # Update the card in Firebase
        success = firebase_manager.update_card(st.session_state.uid, card_id, updated_data)
        if not success:
            st.error("Failed to update card in database")
            return False
        
        # Update the card in the local collection
        st.session_state.collection[card_index] = updated_data
        
        st.success("Card updated successfully!")
        return True
        
    except Exception as e:
        st.error(f"Error updating card: {str(e)}")
        st.write("Debug: Error traceback:", traceback.format_exc())
        return False

def add_card(card_data):
    """Add a new card to the collection"""
    try:
        # Add created_at field for tracking recently added cards
        current_date = datetime.now()
        card_data['created_at'] = current_date.strftime('%Y-%m-%d')
        
        # Ensure last_updated is also set
        card_data['last_updated'] = current_date.isoformat()
            
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
            'last_updated': current_date.isoformat(),
            'last_card_added_at': current_date.isoformat()
        })
        
        # Clear caches and refresh flags to ensure the dashboard updates
        if 'last_refresh' in st.session_state:
            del st.session_state.last_refresh
        st.cache_data.clear()
        st.session_state.refresh_required = True
        
        st.success("Card added successfully!")
        # Switch to View Collection tab
        st.session_state.current_tab = "View Collection"
        st.rerun()
        return True
        
    except Exception as e:
        st.error(f"Error adding card: {str(e)}")
        print(f"Debug - Error adding card: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
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
        
        # Convert DataFrame to list of dictionaries and clean NaN values
        cards = [clean_nan_values(row) for _, row in df.iterrows()]
        
        # Process each card
        for card in cards:
            # Add default values for optional fields
            if 'purchase_date' not in card or card['purchase_date'] is None:
                card['purchase_date'] = datetime.now().isoformat()
            if 'purchase_price' not in card or card['purchase_price'] is None:
                card['purchase_price'] = 0.0
            if 'notes' not in card or card['notes'] is None:
                card['notes'] = ""
            if 'photo' not in card or card['photo'] is None:
                card['photo'] = "https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image"
            if 'tags' not in card or card['tags'] is None:
                card['tags'] = []
            if 'last_updated' not in card or card['last_updated'] is None:
                card['last_updated'] = datetime.now().isoformat()
            # Add created_at field if it doesn't exist for imported cards
            if 'created_at' not in card or card['created_at'] is None:
                card['created_at'] = datetime.now().strftime('%Y-%m-%d')
            
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
            'last_updated': datetime.now().isoformat(),
            'collection_version': firestore.Increment(1),
            'last_card_added_at': datetime.now().isoformat()
        })
        
        # Clear caches and refresh flags to ensure the dashboard updates
        if 'last_refresh' in st.session_state:
            del st.session_state.last_refresh
        st.cache_data.clear()
        st.session_state.refresh_required = True
        
        st.success(f"Successfully imported {len(cards)} cards!")
        return True
        
    except Exception as e:
        st.error(f"Error importing collection: {str(e)}")
        st.write("Debug: Error traceback:", traceback.format_exc())
        return False

def export_collection():
    """Export the collection to an Excel file"""
    try:
        # Check if collection exists
        if not hasattr(st.session_state, 'collection'):
            st.error("No collection found in session state")
            return None
        
        # Create a DataFrame representation of the collection, handling different collection types
        if isinstance(st.session_state.collection, pd.DataFrame):
            if st.session_state.collection.empty:  # Use .empty instead of direct boolean evaluation
                st.error("Collection DataFrame is empty - nothing to export")
                return None
            df = st.session_state.collection.copy()
        elif isinstance(st.session_state.collection, list):
            if not st.session_state.collection:  # Check if list is empty
                st.error("Collection list is empty - nothing to export")
                return None
            
            # Try to safely convert list of objects/dicts to DataFrame
            try:
                collection_dicts = []
                for card in st.session_state.collection:
                    if hasattr(card, 'to_dict') and callable(getattr(card, 'to_dict')):
                        collection_dicts.append(card.to_dict())
                    elif isinstance(card, dict):
                        collection_dicts.append(card)
                    else:
                        st.warning(f"Skipped card of type {type(card)} that cannot be converted")
                
                if not collection_dicts:
                    st.error("No valid cards to export after conversion")
                    return None
                
                df = pd.DataFrame(collection_dicts)
            except Exception as e:
                st.error(f"Failed to convert collection to DataFrame: {str(e)}")
                st.write("Debug info:", traceback.format_exc())
                return None
        else:
            st.error(f"Unsupported collection type: {type(st.session_state.collection)}")
            return None
            
        # Verify DataFrame is valid
        if df is None:
            st.error("Failed to create a valid DataFrame")
            return None
            
        if df.empty:  # Use .empty instead of direct boolean evaluation
            st.error("DataFrame is empty after processing - nothing to export")
            return None
        
        # Create Excel file in memory
        output = io.BytesIO()
        try:
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
        except Exception as excel_err:
            st.error(f"Error creating Excel file: {str(excel_err)}")
            # Try a simpler export without formatting as fallback
            try:
                output = io.BytesIO()
                df.to_excel(output, index=False)
                output.seek(0)
                st.info("Used simplified Excel export due to formatting error")
            except Exception as simple_err:
                st.error(f"Even simplified Excel export failed: {str(simple_err)}")
                return None
        
        # Reset the buffer position
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        st.error(f"Error exporting collection: {str(e)}")
        st.write("Debug: Error traceback:", traceback.format_exc())
        # Provide additional debugging information
        if hasattr(st.session_state, 'collection'):
            st.write(f"Collection type: {type(st.session_state.collection)}")
            if isinstance(st.session_state.collection, pd.DataFrame):
                st.write(f"DataFrame shape: {st.session_state.collection.shape}")
                st.write(f"DataFrame columns: {list(st.session_state.collection.columns)}")
            elif isinstance(st.session_state.collection, list):
                st.write(f"List length: {len(st.session_state.collection)}")
                if st.session_state.collection:
                    st.write(f"First item type: {type(st.session_state.collection[0])}")
        return None

def debug_firebase_connection():
    """Diagnostic function to check Firebase connectivity and card structure"""
    try:
        # Get Firebase client
        firebase_manager = FirebaseManager.get_instance()
        if not firebase_manager._initialized:
            if not firebase_manager.initialize():
                st.error("Firebase initialization failed. Please check your connection.")
                return False
                
        db = firebase_manager.db
        if not db:
            st.error("Firestore client not available. Please check Firebase configuration.")
            return False
        
        # Get the user's cards collection reference
        st.write("### Firebase Connection Diagnostics")
        st.write("Attempting to connect to Firebase...")
        
        try:
            cards_ref = db.collection('users').document(st.session_state.uid).collection('cards')
            all_cards = list(cards_ref.stream())
            st.success(f"✅ Successfully connected to Firebase. Found {len(all_cards)} cards.")
            
            # Display document IDs
            st.write("### Document ID Structure")
            st.write("Here are the actual document IDs in your Firebase collection:")
            for i, doc in enumerate(all_cards[:10]):  # Show first 10 for brevity
                st.write(f"{i+1}. `{doc.id}`")
                
            # Show a sample document structure
            if all_cards:
                st.write("### Sample Document Structure")
                sample_data = all_cards[0].to_dict()
                sample_id = all_cards[0].id
                st.write(f"Document ID: `{sample_id}`")
                
                # Create a cleaner display of the card data
                st.json(sample_data)
                
                # Generate what the ID would be with our algorithm
                if 'player_name' in sample_data and 'year' in sample_data and 'card_set' in sample_data:
                    generated_id = f"{sample_data['player_name']}_{sample_data['year']}_{sample_data['card_set']}_{sample_data.get('card_number', '')}".replace(" ", "_").lower()
                    st.write(f"Generated ID using our algorithm: `{generated_id}`")
                    
                    if generated_id != sample_id:
                        st.warning("⚠️ The generated ID doesn't match the actual Firebase document ID.")
                        st.write("This explains why card deletion might fail - we're looking for documents with IDs that don't match what's in Firebase.")
                    else:
                        st.success("✅ The generated ID matches the actual Firebase document ID.")
                
            return True
            
        except Exception as e:
            st.error(f"Firebase query error: {str(e)}")
            st.write("Check your Firebase security rules to ensure read access is permitted.")
            return False
            
    except Exception as e:
        st.error(f"Diagnostic failed: {str(e)}")
        st.write(f"Error details: {traceback.format_exc()}")
        return False

def repair_firebase_collection():
    """Utility to repair and synchronize Firebase collection with local collection"""
    try:
        # Get Firebase client
        firebase_manager = FirebaseManager.get_instance()
        if not firebase_manager._initialized:
            if not firebase_manager.initialize():
                st.error("Firebase initialization failed. Please check your connection.")
                return False
                
        db = firebase_manager.db
        if not db:
            st.error("Firestore client not available. Please check Firebase configuration.")
            return False
            
        st.write("### Firebase Collection Repair Utility")
        st.write("This tool will help fix synchronization issues between your local collection and Firebase.")
        
        # Get all cards from Firebase
        cards_ref = db.collection('users').document(st.session_state.uid).collection('cards')
        firebase_cards = list(cards_ref.stream())
        
        # Get local collection
        local_collection = st.session_state.collection
        
        # Compare counts
        st.write(f"Found {len(firebase_cards)} cards in Firebase and {len(local_collection)} cards in your local collection.")
        
        # Create mappings and identify issues
        firebase_ids = [doc.id for doc in firebase_cards]
        firebase_data = {doc.id: doc.to_dict() for doc in firebase_cards}
        
        # Create a mapping of local cards to expected Firebase IDs
        local_expected_ids = []
        local_data = []
        
        for card in local_collection:
            if hasattr(card, 'to_dict'):
                card_dict = card.to_dict()
            else:
                card_dict = card.copy() if isinstance(card, dict) else {}
                
            # Generate expected ID
            player_name = str(card_dict.get('player_name', ''))
            year = str(card_dict.get('year', ''))
            card_set = str(card_dict.get('card_set', ''))
            card_number = str(card_dict.get('card_number', ''))
            
            expected_id = f"{player_name}_{year}_{card_set}_{card_number}".replace(" ", "_").lower()
            local_expected_ids.append(expected_id)
            local_data.append(card_dict)
        
        # Find cards in local collection but not in Firebase
        local_only = []
        for i, expected_id in enumerate(local_expected_ids):
            if expected_id not in firebase_ids:
                # Check if a similar card exists in Firebase
                card_data = local_data[i]
                player_name = str(card_data.get('player_name', '')).lower()
                year = str(card_data.get('year', ''))
                card_set = str(card_data.get('card_set', '')).lower()
                card_number = str(card_data.get('card_number', ''))
                
                # Check if a similar card exists with a different ID
                similar_found = False
                similar_id = None
                
                for fb_id, fb_data in firebase_data.items():
                    fb_player = str(fb_data.get('player_name', '')).lower()
                    fb_year = str(fb_data.get('year', ''))
                    fb_set = str(fb_data.get('card_set', '')).lower()
                    fb_number = str(fb_data.get('card_number', ''))
                    
                    if (fb_player == player_name and 
                        fb_year == year and 
                        fb_set == card_set and 
                        (not card_number or fb_number == card_number)):
                        similar_found = True
                        similar_id = fb_id
                        break
                
                if similar_found:
                    # Found in Firebase but with a different ID
                    local_only.append({
                        'card': card_data,
                        'expected_id': expected_id,
                        'similar_id': similar_id,
                        'similar': True
                    })
                else:
                    # Not found in Firebase at all
                    local_only.append({
                        'card': card_data,
                        'expected_id': expected_id,
                        'similar': False
                    })
        
        # Find cards in Firebase but not in local collection
        firebase_only = []
        for fb_id, fb_data in firebase_data.items():
            if fb_id not in local_expected_ids:
                firebase_only.append({
                    'id': fb_id,
                    'data': fb_data
                })
        
        # Show results
        st.write("### Synchronization Issues")
        
        if not local_only and not firebase_only:
            st.success("✅ Your collection is fully synchronized! No issues found.")
            return True
        
        # Show local cards not in Firebase
        if local_only:
            st.warning(f"Found {len(local_only)} cards in your local collection that are not properly synchronized with Firebase:")
            
            for i, item in enumerate(local_only):
                card = item['card']
                display_name = f"{card.get('player_name', '')} {card.get('year', '')} {card.get('card_set', '')} #{card.get('card_number', '')}"
                expected_id = item['expected_id']
                
                with st.expander(f"{i+1}. {display_name}"):
                    if item['similar']:
                        st.write(f"Found in Firebase but with a different ID: `{item['similar_id']}` instead of `{expected_id}`")
                    else:
                        st.write(f"Not found in Firebase. Expected ID: `{expected_id}`")
                    st.json(card)
        
        # Show Firebase cards not in local collection
        if firebase_only:
            st.warning(f"Found {len(firebase_only)} cards in Firebase that are not in your local collection:")
            
            for i, item in enumerate(firebase_only):
                fb_data = item['data']
                fb_id = item['id']
                display_name = f"{fb_data.get('player_name', '')} {fb_data.get('year', '')} {fb_data.get('card_set', '')} #{fb_data.get('card_number', '')}"
                
                with st.expander(f"{i+1}. {display_name} (ID: {fb_id})"):
                    st.json(fb_data)
        
        # Repair options
        st.write("### Repair Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if local_only:
                if st.button("Upload Missing Cards to Firebase", type="primary"):
                    count = 0
                    for item in local_only:
                        try:
                            card = item['card']
                            doc_id = item['expected_id']
                            cards_ref.document(doc_id).set(card)
                            count += 1
                        except Exception as e:
                            st.error(f"Error uploading card: {str(e)}")
                    
                    st.success(f"Successfully uploaded {count} cards to Firebase")
                    if count > 0:
                        st.balloons()
        
        with col2:
            if firebase_only:
                if st.button("Download Missing Cards from Firebase", type="primary"):
                    count = 0
                    for item in firebase_only:
                        try:
                            fb_data = item['data']
                            local_collection.append(fb_data)
                            count += 1
                        except Exception as e:
                            st.error(f"Error adding card to local collection: {str(e)}")
                    
                    st.session_state.collection = local_collection
                    st.success(f"Successfully added {count} cards to your local collection")
                    if count > 0:
                        st.balloons()
        
        # Complete resync option
        if local_only or firebase_only:
            st.write("### Complete Resynchronization")
            resync_option = st.radio(
                "Choose a complete resync direction:",
                ["Firebase → Local (Overwrites local collection with Firebase data)",
                 "Local → Firebase (Uploads entire local collection to Firebase, may create duplicates)"],
                index=0
            )
            
            if st.button("Perform Complete Resynchronization", type="secondary"):
                if "Firebase → Local" in resync_option:
                    # Overwrite local with Firebase
                    new_collection = [doc.to_dict() for doc in firebase_cards]
                    st.session_state.collection = new_collection
                    st.success(f"Successfully replaced local collection with {len(new_collection)} cards from Firebase")
                else:
                    # Overwrite Firebase with local
                    # First clear Firebase collection
                    batch_size = 500  # Firestore limit
                    deleted = 0
                    
                    # Get all documents
                    docs = list(cards_ref.limit(batch_size).stream())
                    
                    # Delete in batches
                    while docs:
                        batch = db.batch()
                        for doc in docs:
                            batch.delete(doc.reference)
                            deleted += 1
                        batch.commit()
                        
                        # Get next batch
                        docs = list(cards_ref.limit(batch_size).stream())
                    
                    # Upload local collection
                    uploaded = 0
                    for card in local_collection:
                        try:
                            if hasattr(card, 'to_dict'):
                                card_dict = card.to_dict()
                            else:
                                card_dict = card.copy() if isinstance(card, dict) else {}
                                
                            # Generate ID
                            player_name = str(card_dict.get('player_name', ''))
                            year = str(card_dict.get('year', ''))
                            card_set = str(card_dict.get('card_set', ''))
                            card_number = str(card_dict.get('card_number', ''))
                            
                            doc_id = f"{player_name}_{year}_{card_set}_{card_number}".replace(" ", "_").lower()
                            
                            # Add to Firebase
                            cards_ref.document(doc_id).set(card_dict)
                            uploaded += 1
                        except Exception as e:
                            st.error(f"Error uploading card: {str(e)}")
                    
                    st.success(f"Successfully deleted {deleted} cards and uploaded {uploaded} cards to Firebase")
                
                st.balloons()
        
        return True
            
    except Exception as e:
        st.error(f"Repair failed: {str(e)}")
        st.write(f"Error details: {traceback.format_exc()}")
        return False

def main():
    # Initialize session state
    init_session_state()
    
    # Check for refresh flag
    if hasattr(st.session_state, 'refresh_required') and st.session_state.refresh_required:
        st.session_state.refresh_required = False
        st.session_state.collection = load_collection_from_firebase()
        st.rerun()
    
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
    
    # Define the tab titles
    tab_titles = ["Add Cards", "View Collection", "Share Collection", "Import/Export"]
    
    # If a current tab is set, select that tab
    current_tab_index = 0  # Default to first tab (Add Cards)
    if hasattr(st.session_state, 'current_tab') and st.session_state.current_tab in tab_titles:
        current_tab_index = tab_titles.index(st.session_state.current_tab)
    
    # Create the tabs
    tabs = st.tabs(tab_titles)
    
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
    with tabs[0]:
        st.subheader("Add New Card")
        display_add_card_form()
    
    # Tab 2: View Collection
    with tabs[1]:
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
            
            # Use the view mode from session state if available (for redirections)
            default_view = "Grid View"
            if hasattr(st.session_state, 'view_mode'):
                default_view = st.session_state.view_mode
            
            # Add view toggle
            view_mode = st.radio(
                "View Mode",
                ["Grid View", "Table View"],
                index=0 if default_view == "Grid View" else 1,
                horizontal=True,
                label_visibility="collapsed"
            )
            
            # Save the view mode selection to session state
            st.session_state.view_mode = view_mode
            
            if view_mode == "Grid View":
                display_collection_grid(filtered_collection)
            else:
                display_collection_table(filtered_collection)
        
        else:
            st.info("Your collection is empty. Add some cards to get started!")
    
    # Tab 3: Share Collection
    with tabs[2]:
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
            
            # Use has_cards to check if filtered collection has cards
            if has_cards(filtered_collection):
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
    with tabs[3]:
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
                
                # Status container for export messages
                export_status = st.empty()
                
                try:
                    # Safely convert collection to DataFrame for export
                    if isinstance(st.session_state.collection, pd.DataFrame):
                        if st.session_state.collection.empty:
                            export_status.warning("Collection DataFrame is empty.")
                            return
                        df = st.session_state.collection.copy()
                    else:
                        # Check if it's a list and not empty
                        if not isinstance(st.session_state.collection, list) or len(st.session_state.collection) == 0:
                            export_status.warning("No cards to export.")
                            return
                        
                        # Safely create DataFrame with error handling
                        try:
                            collection_dicts = []
                            for card in st.session_state.collection:
                                if hasattr(card, 'to_dict') and callable(getattr(card, 'to_dict')):
                                    collection_dicts.append(card.to_dict())
                                elif isinstance(card, dict):
                                    collection_dicts.append(card)
                                else:
                                    st.warning(f"Skipped card of type {type(card)} that cannot be converted to dictionary")
                            
                            if not collection_dicts:
                                export_status.error("No valid cards to export after conversion")
                                return
                            
                            df = pd.DataFrame(collection_dicts)
                            if df.empty:  # Use .empty instead of direct boolean evaluation
                                export_status.error("Resulting DataFrame is empty")
                                return
                        except Exception as df_err:
                            export_status.error(f"Error preparing collection data: {str(df_err)}")
                            st.write("Debug info:", traceback.format_exc())
                            # Skip the rest of the export process
                            return
                    
                    # Handle different export formats with error handling for each
                    if export_format == "Excel":
                        with st.spinner("Preparing Excel export..."):
                            try:
                                excel_data = export_collection()
                                if excel_data:
                                    st.download_button(
                                        label="Download Excel",
                                        data=excel_data,
                                        file_name=f"card_collection_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        use_container_width=True
                                    )
                                    export_status.success(f"Excel export ready with {len(df)} cards")
                                else:
                                    export_status.error("Excel export failed. Try another format.")
                                    
                                    # Offer CSV as fallback
                                    st.info("You can try CSV format as an alternative")
                            except Exception as excel_err:
                                export_status.error(f"Excel export error: {str(excel_err)}")
                                st.write("Debug traceback:", traceback.format_exc())
                                st.info("Please try CSV format as an alternative")
                    elif export_format == "CSV":
                        with st.spinner("Preparing CSV export..."):
                            try:
                                # Handle date columns for CSV export
                                export_df = df.copy()
                                
                                # Process each column to ensure CSV compatibility
                                for col in export_df.columns:
                                    # Convert date objects to strings for CSV export
                                    if export_df[col].dtype == 'object':
                                        export_df[col] = export_df[col].apply(
                                            lambda x: x.isoformat() if isinstance(x, (datetime, date)) else x
                                        )
                                
                                # Safe CSV conversion
                                csv_data = export_df.to_csv(index=False)
                                st.download_button(
                                    label="Download CSV",
                                    data=csv_data,
                                    file_name=f"card_collection_{datetime.now().strftime('%Y%m%d')}.csv",
                                    mime="text/csv",
                                    use_container_width=True
                                )
                                export_status.success(f"CSV export ready with {len(df)} cards")
                            except Exception as csv_err:
                                export_status.error(f"CSV export error: {str(csv_err)}")
                                st.write("Debug traceback:", traceback.format_exc())
                                st.warning("Try JSON format instead")
                    else:  # JSON
                        with st.spinner("Preparing JSON export..."):
                            try:
                                # Convert the DataFrame to a list of dictionaries first
                                records = df.to_dict(orient='records')
                                
                                # Process each record to ensure JSON compatibility
                                for record in records:
                                    for key, value in record.items():
                                        if isinstance(value, (datetime, date)):
                                            record[key] = value.isoformat()
                                        elif pd.isna(value):
                                            record[key] = None
                                        elif not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                                            record[key] = str(value)
                                
                                # Use the built-in json module for better control
                                json_data = json.dumps(records, default=str)
                                st.download_button(
                                    label="Download JSON",
                                    data=json_data,
                                    file_name=f"card_collection_{datetime.now().strftime('%Y%m%d')}.json",
                                    mime="application/json",
                                    use_container_width=True
                                )
                                export_status.success(f"JSON export ready with {len(records)} cards")
                            except Exception as json_err:
                                export_status.error(f"JSON export error: {str(json_err)}")
                                st.write("Debug traceback:", traceback.format_exc())
                                
                                # Try a more robust approach for JSON
                                try:
                                    # Convert to simpler dictionaries first
                                    simple_list = []
                                    for card in st.session_state.collection:
                                        if hasattr(card, 'to_dict'):
                                            card_dict = card.to_dict()
                                        else:
                                            card_dict = card if isinstance(card, dict) else {}
                                        
                                        # Ensure all values are JSON serializable
                                        for k, v in list(card_dict.items()):
                                            if isinstance(v, (datetime, date)):
                                                card_dict[k] = v.isoformat()
                                            elif not isinstance(v, (str, int, float, bool, list, dict, type(None))):
                                                card_dict[k] = str(v)
                                        
                                        simple_list.append(card_dict)
                                    
                                    safe_json = json.dumps(simple_list)
                                    st.download_button(
                                        label="Download JSON (Simple Format)",
                                        data=safe_json,
                                        file_name=f"card_collection_simple_{datetime.now().strftime('%Y%m%d')}.json",
                                        mime="application/json",
                                        use_container_width=True
                                    )
                                    export_status.success(f"Simple JSON export ready with {len(simple_list)} cards")
                                except Exception as simple_json_err:
                                    export_status.error(f"All JSON export attempts failed: {str(simple_json_err)}")
                                    st.write("Debug traceback:", traceback.format_exc())
                except Exception as e:
                    export_status.error(f"Export error: {str(e)}")
                    st.write("Debug info:", traceback.format_exc())
            else:
                st.info("Add some cards to your collection to enable export.")
                
                # Provide a sample template even if collection is empty
                st.download_button(
                    label="Download Empty Template",
                    data=generate_sample_template(),
                    file_name="empty_collection_template.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                
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
                "Excel": "xlsx",
                "CSV": "csv",
                "JSON": "json"
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
                        try:
                            imported_df = pd.read_excel(uploaded_file)
                            st.write(f"Debug: Successfully read Excel file with shape: {imported_df.shape}")
                        except Exception as excel_err:
                            st.error(f"Error reading Excel file: {str(excel_err)}")
                            st.info("Make sure the file is a valid Excel file (.xlsx format)")
                            return
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
                    imported_df = imported_df.copy()
                    
                    # Ensure all data is properly processed
                    for col in imported_df.columns:
                        # Convert all values to strings for consistency (except numeric columns)
                        if col not in ['purchase_price', 'current_value']:
                            imported_df[col] = imported_df[col].astype(str)
                            # Clean up missing values
                            imported_df[col] = imported_df[col].replace('nan', '').replace('None', '')
                            imported_df[col] = imported_df[col].replace('NaN', '').replace('NaT', '')
                    
                    # Handle numeric columns
                    for num_col in ['purchase_price', 'current_value']:
                        if num_col in imported_df.columns:
                            # Convert to float, handling errors
                            imported_df[num_col] = pd.to_numeric(imported_df[num_col], errors='coerce').fillna(0.0)
                    
                    # Add created_at column if it doesn't exist
                    if 'created_at' not in imported_df.columns:
                        current_date_str = datetime.now().strftime('%Y-%m-%d')
                        imported_df['created_at'] = current_date_str
                    else:
                        # Ensure created_at is properly formatted
                        for i, value in enumerate(imported_df['created_at']):
                            if pd.isna(value) or not value:
                                imported_df.at[i, 'created_at'] = datetime.now().strftime('%Y-%m-%d')
                    
                    # Properly convert to records with explicit handling
                    try:
                        imported_collection = imported_df.to_dict('records')
                        print(f"Successfully converted DataFrame to {len(imported_collection)} records")
                    except Exception as conv_err:
                        st.error(f"Error converting DataFrame to records: {str(conv_err)}")
                        st.write(f"Debug traceback: {traceback.format_exc()}")
                        return
                    
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
                                card_name = str(card.player_name) if card.player_name is not None else ''
                                card_year = str(card.year) if card.year is not None else ''
                                card_set = str(card.card_set) if card.card_set is not None else ''
                                card_number = str(card.card_number) if card.card_number is not None else ''
                            else:
                                card_name = str(card.get('player_name', '')) if card.get('player_name') is not None else ''
                                card_year = str(card.get('year', '')) if card.get('year') is not None else ''
                                card_set = str(card.get('card_set', '')) if card.get('card_set') is not None else ''
                                card_number = str(card.get('card_number', '')) if card.get('card_number') is not None else ''
                            
                            # Handle pandas Series objects - convert to scalar if needed
                            if hasattr(card_name, 'iloc') and len(card_name) > 0:
                                card_name = str(card_name.iloc[0])
                            if hasattr(card_year, 'iloc') and len(card_year) > 0:
                                card_year = str(card_year.iloc[0])
                            if hasattr(card_set, 'iloc') and len(card_set) > 0:
                                card_set = str(card_set.iloc[0])
                            if hasattr(card_number, 'iloc') and len(card_number) > 0:
                                card_number = str(card_number.iloc[0])
                                
                            # Check if any value is a pandas Series/array and handle accordingly
                            if any(isinstance(val, (pd.Series, np.ndarray)) for val in [card_name, card_year, card_set, card_number]):
                                print(f"Warning: card data contains Series/array objects that may cause comparison issues")
                                # Attempt to convert all to scalar strings
                                card_name = str(card_name)
                                card_year = str(card_year)
                                card_set = str(card_set)
                                card_number = str(card_number)
                            
                            # Check against existing cards
                            for existing_card in collection:
                                if hasattr(existing_card, 'player_name'):
                                    existing_name = str(existing_card.player_name) if existing_card.player_name is not None else ''
                                    existing_year = str(existing_card.year) if existing_card.year is not None else ''
                                    existing_set = str(existing_card.card_set) if existing_card.card_set is not None else ''
                                    existing_number = str(existing_card.card_number) if existing_card.card_number is not None else ''
                                else:
                                    existing_name = str(existing_card.get('player_name', '')) if existing_card.get('player_name') is not None else ''
                                    existing_year = str(existing_card.get('year', '')) if existing_card.get('year') is not None else ''
                                    existing_set = str(existing_card.get('card_set', '')) if existing_card.get('card_set') is not None else ''
                                    existing_number = str(existing_card.get('card_number', '')) if existing_card.get('card_number') is not None else ''
                                
                                # Convert Series/array objects to strings if needed
                                if hasattr(existing_name, 'iloc') and len(existing_name) > 0:
                                    existing_name = str(existing_name.iloc[0])
                                if hasattr(existing_year, 'iloc') and len(existing_year) > 0:
                                    existing_year = str(existing_year.iloc[0])
                                if hasattr(existing_set, 'iloc') and len(existing_set) > 0:
                                    existing_set = str(existing_set.iloc[0])
                                if hasattr(existing_number, 'iloc') and len(existing_number) > 0:
                                    existing_number = str(existing_number.iloc[0])
                                
                                # Perform string comparison for safety
                                if (card_name.lower() == existing_name.lower() and 
                                    card_year.lower() == existing_year.lower() and 
                                    card_set.lower() == existing_set.lower() and 
                                    card_number.lower() == existing_number.lower()):
                                    return True
                            return False
                        except Exception as e:
                            print(f"Error checking if card exists: {str(e)}")
                            print(f"Card data: {card}")
                            print(f"Error traceback: {traceback.format_exc()}")
                            return False
                    
                    progress_bar.progress(60)
                    status_text.text("Checking for duplicates...")
                    
                    # Filter out duplicates
                    try:
                        new_cards = []
                        duplicate_count = 0
                        
                        # Process cards in smaller batches with updates
                        total_cards = len(imported_collection)
                        batch_size = max(1, min(20, total_cards // 5))  # Adaptive batch size
                        
                        for i, card in enumerate(imported_collection):
                            # Update progress periodically
                            if i % batch_size == 0:
                                progress_percent = 60 + (i / total_cards * 20)
                                progress_bar.progress(int(progress_percent))
                                status_text.text(f"Checking for duplicates... ({i}/{total_cards})")
                            
                            if not card_exists(card, existing_collection):
                                new_cards.append(card)
                            else:
                                duplicate_count += 1
                        
                        if duplicate_count > 0:
                            st.warning(f"Skipped {duplicate_count} duplicate cards.")
                            
                        if not new_cards:
                            st.info("No new cards to import. All cards already exist in your collection.")
                            progress_bar.progress(100)
                            status_text.text("No new cards to import.")
                            return
                    except Exception as dup_err:
                        st.error(f"Error checking for duplicates: {str(dup_err)}")
                        st.write(f"Debug traceback: {traceback.format_exc()}")
                        return
                    
                    progress_bar.progress(80)
                    status_text.text(f"Saving {len(new_cards)} cards to database...")
                    
                    # Append only new cards to existing collection
                    updated_collection = existing_collection + new_cards
                    
                    # Update session state
                    st.session_state.collection = updated_collection
                    
                    # Save to Firebase with better error handling
                    try:
                        status_text.text(f"Saving {len(new_cards)} cards to Firebase...")
                        # Attempt to save to Firebase
                        save_success = save_collection_to_firebase()
                        
                        if save_success:
                            progress_bar.progress(100)
                            status_text.text("Import complete!")
                            st.success(f"Successfully imported {len(new_cards)} new cards!")
                            
                            # Redirect to View Collection tab with Grid View after successful import
                            st.session_state.current_tab = "View Collection"
                            st.session_state.view_mode = "Grid View"
                            st.rerun()
                        else:
                            progress_bar.progress(100)
                            status_text.text("Import partially complete")
                            st.error("Failed to save imported collection to Firebase, but cards were added to your local collection.")
                            st.info("Try refreshing the page or reopening the app to sync with Firebase.")
                    except Exception as firebase_err:
                        progress_bar.progress(100)
                        status_text.text("Import partially complete")
                        st.error(f"Error saving to Firebase: {str(firebase_err)}")
                        st.write(f"Debug traceback: {traceback.format_exc()}")
                        st.info("Your cards were added locally but may not be saved to Firebase. Please check your collection.")
                    
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
    
    # Set the active tab based on session state (this is just for selecting the correct tab visually)
    # It's important to understand that this doesn't affect which tab's content is shown
    if hasattr(st.session_state, 'current_tab') and st.session_state.current_tab in tab_titles:
        st.session_state.active_tab = current_tab_index

if __name__ == "__main__":
    main()

