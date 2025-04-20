import streamlit as st
import pandas as pd
import numpy as np
import io
from io import BytesIO
from PIL import Image
import os
import json
import time
import traceback
import uuid
import platform
import sys
from datetime import datetime
import logging
import base64
import pyrebase
import re
import xlsxwriter
from firebase_admin import firestore
import math

from modules.core.firebase_manager import FirebaseManager
from modules.core.card_value_analyzer import CardValueAnalyzer

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set pandas options for better display
pd.set_option('display.max_columns', None)
pd.set_option('display.expand_frame_repr', False)

# Set page config - this must be the first Streamlit command
st.set_page_config(
    page_title="Collection Manager",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add the project root directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import project modules
from modules.core.firebase_manager import FirebaseManager
from modules.core.card_value_analyzer import CardValueAnalyzer
from modules.ui.components import CardDisplay
from modules.core.market_analysis import MarketAnalyzer
from modules.database.service import DatabaseService
from modules.database.models import Card, CardCondition
from modules.ui.theme.theme_manager import ThemeManager
from modules.ui.branding import BrandingComponent
from scrapers.ebay_interface import EbayInterface

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
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Initialize Firebase
firebase_manager = FirebaseManager.get_instance()
if not firebase_manager._initialized:
    if not firebase_manager.initialize():
        st.error("Failed to initialize Firebase. Please try again later.")
        st.stop()

# Utility functions for formatting values
def format_currency(value):
    """Format a numeric value as a currency string"""
    try:
        if value is None:
            return "$0.00"
        return f"${float(value):.2f}"
    except (ValueError, TypeError):
        return "$0.00"
        
def calculate_roi(cost, value):
    """Calculate Return on Investment percentage"""
    try:
        cost = float(cost) if cost is not None else 0
        value = float(value) if value is not None else 0
        if cost <= 0:
            return "N/A"
        roi = (value - cost) / cost * 100
        return f"{roi:.1f}%"
    except (ValueError, TypeError):
        return "N/A"

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
    """Initialize session state variables with robust error handling."""
    # Core session state variables - these must always be present
    essential_vars = {
        'authenticated': False,  # Add the missing authenticated flag
        'user': None,
        'uid': None,
        'collection': [],
        'edit_mode': False,
        'edit_index': None,
        'query': '',
        'filter_player': '',
        'filter_year': '',
        'filter_set': '',
        'sort_by': 'date_added',
        'sort_order': 'descending',
        'view_mode': 'grid',
        'loading_collection': False,
        'collection_loaded': False,
        'last_firebase_sync': None
    }
    
    # Initialize all essential variables if not present
    for var, default in essential_vars.items():
        if var not in st.session_state:
            st.session_state[var] = default
    
    # Ensure sort_order is always lowercase for internal consistency
    if 'sort_order' in st.session_state and isinstance(st.session_state.sort_order, str):
        st.session_state.sort_order = st.session_state.sort_order.lower()
    
    # Ensure collection is always a list
    if not isinstance(st.session_state.collection, list):
        st.warning("Collection was in an invalid state. Resetting.")
        st.session_state.collection = []
    
    # Force collection_loaded to False if collection is empty but user is logged in
    if (st.session_state.user and st.session_state.uid and 
        not st.session_state.collection and 
        not st.session_state.loading_collection and
        st.session_state.collection_loaded):
        st.session_state.collection_loaded = False
    
    # Set collection_loaded to True if we have cards but it's marked as not loaded
    if (st.session_state.collection and 
        not st.session_state.loading_collection and 
        not st.session_state.collection_loaded):
        st.session_state.collection_loaded = True
    
    # Recovery: If we're stuck in loading state, reset it
    if st.session_state.loading_collection:
        st.session_state.loading_collection = False

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
    """Clean NaN values in card data to prevent errors.
    
    Args:
        data: Dict or DataFrame row containing card data
        
    Returns:
        Dict with cleaned values
    """
    import numpy as np
    import pandas as pd
    
    # Handle both dict and DataFrame row inputs
    if isinstance(data, pd.Series):
        data = data.to_dict()
    elif not isinstance(data, dict):
        print(f"Warning: clean_nan_values received unexpected type: {type(data)}")
        return data
    
    cleaned_data = {}
    
    for key, value in data.items():
        try:
            # Handle arrays and pandas Series first - this prevents the boolean ambiguity error
            if isinstance(value, (np.ndarray, pd.Series)):
                # For arrays/Series, convert to list or scalar value
                if hasattr(value, 'size') and value.size == 0:
                    cleaned_data[key] = None  # Empty array becomes None
                elif hasattr(value, 'size') and value.size == 1:
                    # Single value array - extract the value
                    try:
                        extracted_value = value.item() if hasattr(value, 'item') else value[0]
                        # Now check if it's nan
                        if pd.isna(extracted_value):
                            if key in ['purchase_price', 'current_value', 'high_value', 'low_value']:
                                cleaned_data[key] = 0.0
                            elif key == 'tags':
                                cleaned_data[key] = []
                            else:
                                cleaned_data[key] = ''
                        else:
                            cleaned_data[key] = extracted_value
                    except Exception as e:
                        print(f"Error extracting from array for key {key}: {str(e)}")
                        cleaned_data[key] = None
                else:
                    # Multi-element array - convert to list with extra safety
                    try:
                        # Extra safety for potentially problematic arrays
                        if isinstance(value, np.ndarray) and value.dtype == bool:
                            # Boolean arrays need special handling
                            cleaned_data[key] = value.tolist() if hasattr(value, 'tolist') else list(value)
                        else:
                            # Convert to list and filter out NaN values
                            array_list = value.tolist() if hasattr(value, 'tolist') else list(value)
                            # Safely filter out NaN values one by one
                            filtered_list = []
                            for item in array_list:
                                try:
                                    if not pd.isna(item):  # This handles each item individually
                                        filtered_list.append(item)
                                except Exception as item_error:
                                    print(f"Error checking item in array for key {key}: {str(item_error)}")
                                    # Skip problematic items
                                    continue
                            cleaned_data[key] = filtered_list
                    except Exception as e:
                        print(f"Error converting array to list for key {key}: {str(e)}")
                        # Fallback for arrays we can't process
                        if key in ['purchase_price', 'current_value', 'high_value', 'low_value']:
                            cleaned_data[key] = 0.0
                        elif key == 'tags':
                            cleaned_data[key] = []
                        else:
                            cleaned_data[key] = ''
                    
            # Handle scalar NaN values
            elif pd.isna(value) or value is None:
                # Use appropriate default values based on field type
                if key in ['purchase_price', 'current_value', 'high_value', 'low_value']:
                    cleaned_data[key] = 0.0
                elif key in ['year', 'card_number']:
                    cleaned_data[key] = ''
                elif key == 'tags':
                    cleaned_data[key] = []
                else:
                    cleaned_data[key] = ''
            # Handle lists that might contain NaN
            elif isinstance(value, list):
                # Safely filter list items
                filtered_list = []
                for item in value:
                    try:
                        if not pd.isna(item):
                            filtered_list.append(item)
                    except Exception as item_error:
                        print(f"Error checking list item for key {key}: {str(item_error)}")
                        # Skip problematic items
                        continue
                cleaned_data[key] = filtered_list
            # Ensure numerical values are proper numbers
            elif key in ['purchase_price', 'current_value', 'high_value', 'low_value']:
                try:
                    cleaned_data[key] = float(value) if value is not None else 0.0
                except (ValueError, TypeError):
                    print(f"Warning: Could not convert {key}={value} to float, using 0.0")
                    cleaned_data[key] = 0.0
            # Default case - keep the value as is
            else:
                cleaned_data[key] = value
        except Exception as key_error:
            print(f"Unexpected error processing key {key}: {str(key_error)}")
            # Use safe defaults for any keys with errors
            if key in ['purchase_price', 'current_value', 'high_value', 'low_value']:
                cleaned_data[key] = 0.0
            elif key == 'tags':
                cleaned_data[key] = []
            else:
                cleaned_data[key] = ''
    
    return cleaned_data

def update_card_values(collection):
    """Update card values from recent eBay sales"""
    try:
        if not collection or len(collection) == 0:
            st.error("No cards in collection to update")
            return False
        
        # Import the eBay interface directly
        from scrapers.ebay_interface import EbayInterface
        ebay = EbayInterface()
        
        # Create progress bar
        progress_bar = st.progress(0)
        total_cards = len(collection)
        st.write(f"Updating values for {total_cards} cards...")
        
        # Clean all cards first to ensure valid data
        cleaned_collection = [clean_nan_values(card) for card in collection]
        
        # Process each card, updating its value
        updated_cards = []
        updated_count = 0
        
        for i, card in enumerate(cleaned_collection):
            try:
                # Update progress
                progress = (i + 1) / total_cards
                progress_bar.progress(progress)
                
                # Extract card details
                player = card.get('player_name')
                year = card.get('year')
                card_set = card.get('card_set')
                number = card.get('card_number')
                variation = card.get('variation', '')
                condition = card.get('condition', 'Raw')
                
                # Skip cards with missing info
                if not all([player, year, card_set]):
                    st.warning(f"Skipping card with incomplete info: {player} {year} {card_set}")
                    updated_cards.append(card)
                    continue
                
                # Debug info
                print(f"Searching eBay for: {player} {year} {card_set} #{number} {variation} {condition}")
                
                # Get the latest sales from eBay
                sales_results = ebay.search_cards(
                    player_name=player,
                    year=year,
                    card_set=card_set,
                    card_number=number,
                    variation=variation,
                    scenario=condition
                )
                
                # Debug the result
                print(f"Found {len(sales_results)} sales for {player} {year} {card_set}")
                
                # Calculate the average sale price if sales were found
                if sales_results and len(sales_results) > 0:
                    # Get prices of all sales
                    prices = [sale.get('price', 0) for sale in sales_results if sale.get('price', 0) > 0]
                    
                    if prices:
                        # Calculate average price, removing outliers (prices outside 2 standard deviations)
                        if len(prices) >= 3:
                            # Calculate mean and standard deviation
                            mean_price = sum(prices) / len(prices)
                            std_dev = (sum((x - mean_price) ** 2 for x in prices) / len(prices)) ** 0.5
                            
                            # Filter out outliers
                            filtered_prices = [p for p in prices if abs(p - mean_price) <= 2 * std_dev]
                            
                            # Recalculate average with filtered prices
                            if filtered_prices:
                                avg_price = sum(filtered_prices) / len(filtered_prices)
                            else:
                                avg_price = mean_price
                        else:
                            # Not enough data points for outlier removal
                            avg_price = sum(prices) / len(prices)
                        
                        # Update card value
                        card['current_value'] = round(float(avg_price), 2)
                        card['last_value_update'] = datetime.now().isoformat()
                        updated_count += 1
                        
                        # Store the most recent sale details
                        if len(sales_results) > 0:
                            most_recent_sale = sales_results[0]
                            card['last_sale_price'] = most_recent_sale.get('price', 0)
                            card['last_sale_date'] = most_recent_sale.get('date', '')
                            card['last_sale_link'] = most_recent_sale.get('link', '')
                        
                        # Calculate ROI if purchase price exists
                        purchase_price = float(card.get('purchase_price', 0) or 0)
                        if purchase_price > 0:
                            card['roi'] = ((card['current_value'] - purchase_price) / purchase_price) * 100
                        else:
                            card['roi'] = 0
                        
                        print(f"Updated value for {player} to ${card['current_value']:.2f}")
                    else:
                        print(f"No valid prices found for {player}")
                else:
                    print(f"No sales results found for {player}")
                
                updated_cards.append(card)
                
            except Exception as card_error:
                st.warning(f"Error updating card {card.get('player_name', 'Unknown')}: {str(card_error)}")
                print(f"Exception updating card: {str(card_error)}")
                # Ensure the card has valid numeric values before adding it back
                if 'current_value' not in card or card['current_value'] is None:
                    card['current_value'] = 0.0
                updated_cards.append(card)
        
        # Hide progress bar when done
        progress_bar.empty()
        
        # Update session state with modified collection
        st.session_state.collection = updated_cards
        
        # Save to Firebase
        save_collection_to_firebase()
        
        st.success(f"Successfully updated values for {updated_count} cards")
        return updated_cards
        
    except Exception as e:
        st.error(f"Error updating card values: {str(e)}")
        print(f"Exception in update_card_values: {str(e)}")
        return False

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
    """Display collection summary with responsive metrics and enhanced styling"""
    if not has_cards(filtered_collection):
        st.info("No cards in collection")
        return
    
    # Calculate summary metrics with proper type conversion
    total_value = 0.0
    total_cost = 0.0
    total_cards = len(filtered_collection)
    
    for card in filtered_collection:
        # Get purchase price and current value using safe_get
        purchase_price = safe_get(card, 'purchase_price', 0)
        current_value = safe_get(card, 'current_value', 0)
        
        # Add to totals (safe_get now handles float conversion)
        total_cost += float(purchase_price or 0)  # Handle None values
        total_value += float(current_value or 0)  # Handle None values
    
    # Calculate ROI
    total_roi = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
    
    # Custom CSS for enhanced metrics
    st.markdown("""
    <style>
    /* Container for all metrics */
    .metrics-container {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 20px;
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    
    /* Individual metric card */
    .metric-card {
        flex: 1;
        min-width: 120px;
        background-color: white;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    /* Metric label */
    .metric-label {
        font-size: 14px;
        color: #718096;
        margin-bottom: 8px;
        font-weight: 500;
    }
    
    /* Metric value */
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 4px;
    }
    
    /* Value colors */
    .positive {
        color: #48bb78;
    }
    
    .negative {
        color: #f56565;
    }
    
    .neutral {
        color: #3182ce;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # HTML for metrics container
    metrics_html = f"""
    <div class="metrics-container">
        <div class="metric-card">
            <div class="metric-label">Total Cards</div>
            <div class="metric-value neutral">{total_cards}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Total Cost</div>
            <div class="metric-value neutral">${total_cost:,.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Total Value</div>
            <div class="metric-value neutral">${total_value:,.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Return on Investment</div>
            <div class="metric-value {'positive' if total_roi >= 0 else 'negative'}">{total_roi:.1f}%</div>
        </div>
    </div>
    """
    
    # Display metrics
    st.markdown(metrics_html, unsafe_allow_html=True)

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
    # Debug information
    st.markdown("<details><summary>Debug Information</summary>", unsafe_allow_html=True)
    st.write(f"Card Index: {card_index}")
    st.write(f"Session State: editing_card={st.session_state.get('editing_card')}, edit_mode={st.session_state.get('edit_mode')}")
    st.markdown("</details>", unsafe_allow_html=True)
    
    # Add a prominent delete button outside the form
    st.markdown("<hr>", unsafe_allow_html=True)
    delete_container = st.container()
    with delete_container:
        st.markdown("<h3 style='color: #d62728;'>Danger Zone</h3>", unsafe_allow_html=True)
        delete_col1, delete_col2 = st.columns([3, 1])
        with delete_col1:
            st.markdown("Delete this card permanently from your collection")
        with delete_col2:
            delete_card_clicked = st.button("🗑️ DELETE", type="primary", use_container_width=True, key="delete_card_button")
            
            if delete_card_clicked:
                # Get the card's unique ID
                card_id = card_data.get('id')
                if not card_id:
                    # Generate card_id from card details if not available
                    player_name = card_data.get('player_name', '')
                    year = card_data.get('year', '')
                    card_set = card_data.get('card_set', '')
                    card_number = card_data.get('card_number', '')
                    card_id = f"{player_name}_{year}_{card_set}_{card_number}".replace(" ", "_").lower()
                
                # Find corresponding card in main collection
                main_collection_index = None
                if 'collection' in st.session_state:
                    for i, main_card in enumerate(st.session_state.collection):
                        if main_card.get('id') == card_id:
                            main_collection_index = i
                            break
                
                # Debug information
                with st.expander("Debug Information", expanded=False):
                    st.markdown(f"**Card Selected:**")
                    st.write(f"Player: {card_data.get('player_name', '')}")
                    st.write(f"Year: {card_data.get('year', '')}")
                    st.write(f"Set: {card_data.get('card_set', '')}")
                    st.write(f"Number: {card_data.get('card_number', '')}")
                    st.write(f"Card ID: {card_id}")
                    st.write(f"Index in main collection: {main_collection_index}")
                
                # Call delete_card with card_id and main_collection_index
                result = delete_card(card_id, main_collection_index)
                
                if result['success']:
                    st.success(result['message'])
                    # Clear edit state
                    st.session_state.edit_mode = False
                    st.session_state.editing_card = False
                    
                    if 'edit_index' in st.session_state:
                        del st.session_state.edit_index
                    if 'edit_card_data' in st.session_state:
                        del st.session_state.edit_card_data
                    if 'editing_card_index' in st.session_state:
                        del st.session_state.editing_card_index
                    
                    # Force a full refresh of the page
                    st.session_state['force_refresh'] = True
                    st.rerun()
                else:
                    st.error(f"Failed to delete card: {result['message']}")
                    with st.expander("Error Details"):
                        st.write(result)
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
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
        
        update_button = st.form_submit_button("Update Card", use_container_width=True)
        
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
                # Set a session state flag to indicate successful edit
                st.session_state.edit_completed = True
                # Update session state
                st.session_state.edit_mode = False
                if 'edit_index' in st.session_state:
                    del st.session_state.edit_index
                if 'edit_card_data' in st.session_state:
                    del st.session_state.edit_card_data
                if 'edit_card_id' in st.session_state:
                    del st.session_state.edit_card_id
                # Clear the query parameter
                st.query_params.clear()
                # Rerun to redirect back to collection view
                st.rerun()
            else:
                st.error("Failed to update card.")

def load_collection_from_firebase():
    """Load the user's collection from Firebase with robust error handling and retries.
    Returns a dict with success status, message, and collection data."""
    
    try:
        # 1. First, check if user is logged in
        if not st.session_state.user or not st.session_state.uid:
            print("No user is logged in, cannot load collection")
            return {'success': False, 'message': 'No user is logged in', 'collection': []}
            
        # 2. Use existing collection data if we have it, while attempting to refresh
        fallback_collection = st.session_state.get('collection', []) 
        
        # 3. Prevent concurrent loading requests
        if st.session_state.get('loading_collection', False):
            print("Collection loading already in progress")
            return {
                'success': True, 
                'message': 'Collection loading in progress', 
                'collection': fallback_collection
            }
        
        # 4. Set loading flag
        st.session_state.loading_collection = True
        
        # 5. Check Firebase connection first
        try:
            firebase_manager = FirebaseManager.get_instance()
            if not firebase_manager:
                print("Could not get FirebaseManager instance")
                st.session_state.loading_collection = False
                return {
                    'success': False, 
                    'message': 'Could not get FirebaseManager instance', 
                    'collection': fallback_collection
                }
                
            if not firebase_manager.is_initialized():
                print("Firebase not initialized, attempting to initialize...")
                firebase_manager.initialize()
                
                if not firebase_manager.is_initialized():
                    print("Failed to initialize Firebase")
                    st.session_state.loading_collection = False
                    return {
                        'success': False, 
                        'message': 'Failed to initialize Firebase', 
                        'collection': fallback_collection
                    }
        except Exception as e:
            print(f"Error checking Firebase initialization: {str(e)}")
            st.session_state.loading_collection = False
            return {
                'success': False, 
                'message': f'Error checking Firebase: {str(e)}', 
                'collection': fallback_collection
            }
                
        # 6. Get user data from Firestore
        try:
            firestore_db = firebase_manager.get_firestore_client()
            if not firestore_db:
                print("Could not get Firestore client")
                st.session_state.loading_collection = False
                return {
                    'success': False, 
                    'message': 'Could not get Firestore client', 
                    'collection': fallback_collection
                }
        except Exception as e:
            print(f"Error getting Firestore client: {str(e)}")
            st.session_state.loading_collection = False
            return {
                'success': False, 
                'message': f'Error getting Firestore client: {str(e)}', 
                'collection': fallback_collection
            }
            
        # 7. Attempt to load data with retries
        max_retries = 3
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                print(f"Firebase load attempt {retry_count + 1}/{max_retries}")
                
                # 7.1 Get the user document
                try:
                    user_doc = firestore_db.collection('users').document(st.session_state.uid).get()
                except Exception as e:
                    print(f"Error getting user document: {str(e)}")
                    retry_count += 1
                    last_error = e
                    time.sleep(1)  # Wait before retrying
                    continue
                
                # 7.2 Check if user document exists
                if not user_doc.exists:
                    print(f"User document not found for UID: {st.session_state.uid}")
                    st.session_state.loading_collection = False
                    return {
                        'success': False, 
                        'message': 'User document not found', 
                        'collection': fallback_collection
                    }
                
                # 7.3 Convert user document to dict
                try:
                    user_data = user_doc.to_dict()
                    print(f"User data keys: {list(user_data.keys())}")
                except Exception as e:
                    print(f"Error converting user document to dict: {str(e)}")
                    retry_count += 1
                    last_error = e
                    time.sleep(1)
                    continue
                
                # 7.4 Initialize empty collection
                cleaned_collection = []
                
                # 7.5 Try to load from in-document collection field first
                if 'collection' in user_data and user_data['collection']:
                    print(f"Found collection array in user document with {len(user_data['collection'])} items")
                    
                    # Validate and clean collection data
                    for card in user_data['collection']:
                        # Skip invalid cards
                        if not isinstance(card, dict):
                            print(f"Skipping non-dict card: {type(card)}")
                            continue
                            
                        # Ensure required fields exist
                        if 'player_name' not in card or not card['player_name']:
                            print(f"Skipping card without player_name: {card.get('id', 'Unknown ID')}")
                            continue
                        
                        # Add to cleaned collection
                        cleaned_collection.append(clean_nan_values(card))
                    
                    print(f"Successfully loaded {len(cleaned_collection)} cards from user document")
                else:
                    print("No collection array found in user document, checking cards subcollection...")
                    
                    # 7.6 If no in-document collection, try to load from cards subcollection
                    try:
                        cards_ref = firestore_db.collection('users').document(st.session_state.uid).collection('cards')
                        card_docs = list(cards_ref.stream())
                    except Exception as e:
                        print(f"Error getting cards subcollection: {str(e)}")
                        retry_count += 1
                        last_error = e
                        time.sleep(1)
                        continue
                    
                    if card_docs:
                        print(f"Found {len(card_docs)} cards in 'cards' subcollection")
                        for doc in card_docs:
                            try:
                                card_data = doc.to_dict()
                                if card_data and isinstance(card_data, dict):
                                    # Ensure the card has a player name
                                    if 'player_name' not in card_data or not card_data['player_name']:
                                        print(f"Skipping card without player_name: {doc.id}")
                                        continue
                                
                                    # Add ID to the card
                                    card_data['id'] = doc.id
                                    
                                    # Clean data and add to collection
                                    cleaned_collection.append(clean_nan_values(card_data))
                                else:
                                    print(f"Invalid card data in subcollection: {doc.id}")
                            except Exception as card_err:
                                print(f"Error loading card {doc.id}: {str(card_err)}")
                                continue
                    else:
                        print("No cards found in subcollection")
                
                # 7.7 Try to get cards from savedCards array as well (another possible location)
                if not cleaned_collection and 'savedCards' in user_data and user_data['savedCards']:
                    print(f"Found 'savedCards' array with {len(user_data['savedCards'])} items")
                    for card in user_data['savedCards']:
                        if isinstance(card, dict) and 'player_name' in card and card['player_name']:
                            cleaned_collection.append(clean_nan_values(card))
                
                # 7.8 Final check - use existing collection if nothing loaded from Firebase
                if not cleaned_collection and fallback_collection:
                    print(f"No cards found in Firebase, using existing collection ({len(fallback_collection)} cards)")
                    cleaned_collection = fallback_collection
                    # Update session state
                    st.session_state.collection = cleaned_collection
                    st.session_state.collection_loaded = True
                    st.session_state.loading_collection = False
                    
                    return {
                        'success': True, 
                        'message': 'Using existing collection (Firebase load failed)',
                        'collection': cleaned_collection,
                        'count': len(cleaned_collection)
                    }
                
                # 7.9 Update session state with loaded collection
                elif cleaned_collection:
                    print(f"Successfully loaded a total of {len(cleaned_collection)} cards")
                    
                    # Update session state
                    st.session_state.last_firebase_sync = datetime.now()
                    st.session_state.collection = cleaned_collection
                    st.session_state.collection_loaded = True
                    st.session_state.loading_collection = False
                    
                    return {
                        'success': True, 
                        'message': f'Successfully loaded {len(cleaned_collection)} cards',
                        'collection': cleaned_collection,
                        'count': len(cleaned_collection)
                    }
                else:
                    # 7.10 No cards found anywhere
                    print("No cards found in any location (document array, subcollection, or savedCards)")
                    st.session_state.collection = []
                    st.session_state.loading_collection = False
                    st.session_state.collection_loaded = True
                    st.session_state.last_firebase_sync = datetime.now()
                    
                    return {
                        'success': True, 
                        'message': 'No cards found in your collection',
                        'collection': [],
                        'count': 0
                    }
                
            except Exception as e:
                retry_count += 1
                last_error = e
                print(f"Error loading collection (attempt {retry_count}/{max_retries}): {str(e)}")
                print(traceback.format_exc())
                time.sleep(1)  # Wait before retrying
        
        # 8. If we get here, all retries failed
        print(f"All {max_retries} attempts to load collection failed. Last error: {str(last_error)}")
        
        # 8.1 Check if we have fallback data to use
        if fallback_collection:
            st.warning(f"Failed to refresh collection from Firebase. Using cached data ({len(fallback_collection)} cards).")
            st.session_state.loading_collection = False
            return {
                'success': True,  # Mark as success so UI shows something
                'message': 'Using cached collection (Firebase refresh failed)',
                'collection': fallback_collection,
                'count': len(fallback_collection)
            }
        else:
            # 8.2 No fallback data either
            st.error("Failed to load your collection after multiple attempts. Please refresh the page.")
            st.session_state.loading_collection = False
            return {
                'success': False, 
                'message': 'Failed to load collection after multiple attempts',
                'collection': []
            }
        
    except Exception as e:
        # 9. Unexpected error in outer try block
        print(f"Unexpected error loading collection: {str(e)}")
        print(traceback.format_exc())
        
        # 9.1 Check if we have fallback data to use
        if fallback_collection := st.session_state.get('collection', []):
            st.warning(f"Error refreshing collection. Using cached data ({len(fallback_collection)} cards).")
            st.session_state.loading_collection = False
            return {
                'success': True,  # Mark as success so UI shows something
                'message': f'Using cached collection. Error: {str(e)}',
                'collection': fallback_collection,
                'count': len(fallback_collection)
            }
        else:
            # 9.2 No fallback data either
            st.session_state.loading_collection = False
            return {
                'success': False, 
                'message': f'Unexpected error: {str(e)}',
                'collection': []
            }

def save_collection_to_firebase():
    """Save the collection to Firebase"""
    try:
        if not st.session_state.uid:
            st.error("No user ID found. Please log in again.")
            return False
        
        if not has_cards(st.session_state.collection):
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

def display_collection_grid(filtered_collection, show_filters=True):
    """Display the collection in a grid layout with 5 cards per row"""
    
    # Check if collection is empty
    if not filtered_collection or len(filtered_collection) == 0:
        st.warning("No cards found in your collection with the current filters.")
        return
    
    # Check if new display manager is enabled
    if is_feature_enabled('new_display_manager'):
        try:
            from modules.core.display_manager import DisplayManager
            
            # Define the edit card handler function
            def edit_card_handler(idx):
                st.session_state.edit_mode = True
                st.session_state.edit_index = idx
                st.session_state.edit_card_data = filtered_collection[idx]
                st.session_state.editing_card = True
                st.session_state.editing_card_index = idx
                st.rerun()
            
            # Use the new DisplayManager
            DisplayManager.display_collection_grid(filtered_collection, on_card_click=edit_card_handler)
            
        except Exception as e:
            st.error(f"Error using new display manager: {str(e)}")
            st.info("Falling back to original display implementation")
            # Fall through to original implementation
    else:
        # Original implementation
        try:
            from modules.ui.components.CardDisplay import CardDisplay
            
            # Define the edit card handler function
            def edit_card_handler(idx):
                st.session_state.edit_mode = True
                st.session_state.edit_index = idx
                st.session_state.edit_card_data = filtered_collection[idx]
                st.session_state.editing_card = True
                st.session_state.editing_card_index = idx
                st.rerun()
            
            # Use the original CardDisplay component
            CardDisplay.display_grid(filtered_collection, on_click=edit_card_handler)
            
        except Exception as e:
            st.error(f"Error displaying collection: {str(e)}")
            return
    
    # Add delete buttons below the grid (works with both implementations)
    st.markdown("### Delete Cards")
    st.markdown("Select a card to delete from your collection:")
    
    # Create a dropdown to select card with more descriptive options
    card_options = [f"{i+1}. {card.get('player_name', 'Unknown')} - {card.get('year', '')} {card.get('card_set', '')} #{card.get('card_number', '')}" 
                    for i, card in enumerate(filtered_collection)]
    
    if not card_options:
        st.info("No cards available to delete.")
        return
        
    selected_idx = st.selectbox("Select card to delete", 
                               range(len(card_options)), 
                               format_func=lambda i: card_options[i],
                               help="Select a card from the dropdown to delete")

def display_collection_table(collection):
    """Display the collection in a table format"""
    try:
        if not collection:
            st.info("No cards to display in table view.")
            return
            
        # Create a dataframe from the collection with safe conversion
        try:
            df = pd.DataFrame(collection)
            
            # Add an Edit button column
            df['_edit'] = range(len(df))
            df['_edit'] = df['_edit'].apply(lambda x: f"edit_{x}")
            
        except Exception as e:
            st.error(f"Error converting collection to DataFrame: {str(e)}")
            print(f"Error creating DataFrame: {str(e)}")
            # Attempt to create a more simplified DataFrame
            try:
                # Create a simplified version with just essential columns
                simplified_data = []
                for card in collection:
                    if isinstance(card, dict):
                        simplified_data.append({
                            'player_name': card.get('player_name', 'Unknown'),
                            'year': card.get('year', ''),
                            'card_set': card.get('card_set', ''),
                            'purchase_price': card.get('purchase_price', 0),
                            'current_value': card.get('current_value', 0)
                        })
                df = pd.DataFrame(simplified_data)
                # Add an Edit button column
                df['_edit'] = range(len(df))
                df['_edit'] = df['_edit'].apply(lambda x: f"edit_{x}")
            except Exception as e2:
                st.error(f"Failed to create even a simplified DataFrame: {str(e2)}")
                return
        
        # Select columns to display
        display_columns = ['player_name', 'year', 'card_set', 'card_number', 'variation', 
                         'condition', 'purchase_price', 'current_value']
                          
        # Only include columns that exist in the DataFrame
        display_columns = [col for col in display_columns if col in df.columns]
        
        if not display_columns:
            st.error("No valid columns found in collection data.")
            return
            
        # Add ROI calculation if both price columns exist
        if 'purchase_price' in df.columns and 'current_value' in df.columns:
            try:
                # Convert to numeric, forcing errors to NaN
                df['purchase_price'] = pd.to_numeric(df['purchase_price'], errors='coerce')
                df['current_value'] = pd.to_numeric(df['current_value'], errors='coerce')
                
                # Calculate ROI where purchase_price > 0
                df['roi'] = df.apply(
                    lambda x: ((x['current_value'] - x['purchase_price']) / x['purchase_price'] * 100) 
                    if pd.notnull(x['purchase_price']) and x['purchase_price'] > 0 
                    else None, 
                    axis=1
                )
                
                # Format as percentage with 1 decimal
                df['roi'] = df['roi'].apply(
                    lambda x: f"{x:.1f}%" if pd.notnull(x) else "N/A"
                )
                
                display_columns.append('roi')
            except Exception as e:
                print(f"Error calculating ROI: {str(e)}")
                # Continue without ROI if there's an error
        
        # Format currency columns
        for col in ['purchase_price', 'current_value']:
            if col in df.columns:
                try:
                    df[col] = df[col].apply(
                        lambda x: f"${float(x):.2f}" if pd.notnull(x) and x != '' else "$0.00"
                    )
                except Exception as e:
                    print(f"Error formatting {col}: {str(e)}")
                    # Try a more robust approach
                    df[col] = df[col].apply(
                        lambda x: f"${float(x):.2f}" if pd.notnull(x) and str(x).strip() and str(x).strip() != 'nan' 
                        else "$0.00"
                    )
        
        # Add edit column to display columns
        display_columns.append('_edit')
        
        # Create a copy of the DataFrame with only display columns
        display_df = df[display_columns].copy()
    
        # Rename columns for display
        column_map = {
            'player_name': 'Player',
            'year': 'Year',
            'card_set': 'Set',
            'card_number': 'Number',
            'variation': 'Variation',
            'condition': 'Condition',
            'purchase_price': 'Cost',
            'current_value': 'Value',
            'roi': 'ROI',
            '_edit': 'Edit'
        }
        
        # Only rename columns that exist
        rename_dict = {k: v for k, v in column_map.items() if k in display_df.columns}
        display_df = display_df.rename(columns=rename_dict)
    
        # Display the table
        st.dataframe(
            display_df,
            use_container_width=True,
            column_config={
                "ROI": st.column_config.TextColumn(
                    "ROI",
                    help="Return on Investment",
                    width="medium"
                ),
                "Edit": st.column_config.ButtonColumn(
                    "Edit",
                    help="Edit this card",
                    width="small"
                )
            }
        )
        
        # Handle edit button clicks
        button_clicked = st.session_state.get("dataframe_clicked_row")
        if button_clicked and button_clicked.get("column_name") == "Edit":
            row_index = button_clicked["row_index"]
            # Set edit mode
            st.session_state.edit_index = row_index
            st.session_state.edit_mode = True
            # Use query parameters to preserve state
            st.query_params["edit"] = str(row_index)
            st.rerun()
        
        # Add action buttons for the entire collection
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Export to Excel", key="export_excel_btn"):
                export_to_excel(df)
                
    except Exception as e:
        st.error(f"Error displaying collection table: {str(e)}")
        print(f"Error in display_collection_table: {str(e)}")
        print(traceback.format_exc())

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

def display_collection(collection_data):
    """Display the user's collection with improved filtering and sorting options."""
    try:
        # Initialize session state variables if they don't exist
        if 'filtered_collection' not in st.session_state:
            st.session_state.filtered_collection = collection_data
        
        if 'sort_field' not in st.session_state:
            st.session_state.sort_field = 'player_name'
            
        if 'sort_order' not in st.session_state:
            st.session_state.sort_order = 'Ascending'
            
        # Header and collection summary
        st.markdown("## Your Collection", unsafe_allow_html=True)
        
        # Display collection summary
        if collection_data and len(collection_data) > 0:
            display_collection_summary(collection_data)
        
        # Add Update All Values button
        if collection_data and len(collection_data) > 0:
            col1, col2 = st.columns([0.7, 0.3])
            with col2:
                if st.button("Update All Values", use_container_width=True):
                    with st.spinner("Updating card values from recent eBay sales..."):
                        updated_collection = update_card_values(collection_data)
                        if updated_collection:
                            # Force a refresh to show new values
                            st.session_state.collection = updated_collection
                            st.success("Values updated from recent eBay sales!")
                            st.rerun()
                        else:
                            st.error("Failed to update values. Please try again.")
                    
        # Create search and filter section
        st.markdown("### Search & Filter", unsafe_allow_html=True)
        
        # Create columns for search and tags
        col1, col2 = st.columns(2)
        
        with col1:
            # Search filter
            search_term = st.text_input("Search Cards", key="search_cards")
            
        with col2:
            # Get all unique tags from collection
            all_tags = []
            for card in collection_data:
                tags = card.get('tags', [])
                if tags and isinstance(tags, list):
                    all_tags.extend(tags)
                elif tags and isinstance(tags, str):
                    all_tags.append(tags)
            
            # Remove duplicates and sort
            unique_tags = sorted(list(set([tag for tag in all_tags if tag])))
            
            # Multi-select for tags
            selected_tags = st.multiselect(
                "Filter by Tags",
                options=unique_tags,
                default=None,
                key="filter_tags"
            )
        
        # Create sort options
        st.markdown("### Sort Options", unsafe_allow_html=True)
        sort_col1, sort_col2 = st.columns(2)
        
        # Use the session state values as defaults, but don't modify session state after widget creation
        with sort_col1:
            sort_options = [
                "player_name", "year", "card_set", "card_number",
                "purchase_price", "current_value", "roi", "purchase_date"
            ]
            sort_labels = {
                "player_name": "Player Name",
                "year": "Year",
                "card_set": "Card Set",
                "card_number": "Card Number",
                "purchase_price": "Purchase Price",
                "current_value": "Current Value",
                "roi": "ROI",
                "purchase_date": "Purchase Date"
            }
            
            sort_field = st.selectbox(
                "Sort By",
                options=sort_options,
                format_func=lambda x: sort_labels.get(x, x.replace('_', ' ').title()),
                index=sort_options.index(st.session_state.sort_field) if st.session_state.sort_field in sort_options else 0,
                key="sort_field_widget"
            )
            
        with sort_col2:
            sort_order = st.selectbox(
                "Sort Order",
                options=["Ascending", "Descending"],
                index=0 if st.session_state.sort_order.lower() == "ascending" else 1,
                key="sort_order_widget"
            )
            
        # Apply filters based on search term and tags
        filtered_data = collection_data
        
        # Filter by search term
        if search_term:
            filtered_data = [
                card for card in filtered_data 
                if search_term.lower() in str(card.get('player_name', '')).lower() or
                search_term.lower() in str(card.get('card_set', '')).lower() or
                search_term.lower() in str(card.get('year', '')).lower() or
                search_term.lower() in str(card.get('card_number', '')).lower() or
                (card.get('notes') and search_term.lower() in str(card.get('notes')).lower())
            ]
            
        # Filter by selected tags
        if selected_tags:
            filtered_tags_data = []
            for card in filtered_data:
                card_tags = card.get('tags', [])
                
                # Handle different tag formats
                if isinstance(card_tags, str):
                    card_tags = [tag.strip() for tag in card_tags.split(',') if tag.strip()]
                elif not isinstance(card_tags, list):
                    card_tags = []
                    
                # Check if any selected tag is in this card's tags
                if any(tag in card_tags for tag in selected_tags):
                    filtered_tags_data.append(card)
            
            filtered_data = filtered_tags_data
            
        # Store filtered data in session state
        st.session_state.filtered_collection = filtered_data
        
        # Store current sort selections in session state for next run
        st.session_state.sort_field = sort_field 
        st.session_state.sort_order = sort_order
                
        # Sort the filtered data
        if filtered_data:
            try:
                # For numeric fields, convert to float for proper sorting
                numeric_fields = ['current_value', 'purchase_price', 'roi', 'year']
                
                if sort_field in numeric_fields:
                    # Sort by numeric value
                    filtered_data = sorted(
                        filtered_data,
                        key=lambda x: float(x.get(sort_field, 0) or 0),
                        reverse=(sort_order == "Descending")
                    )
                else:
                    # For text fields, use string comparison
                    filtered_data = sorted(
                        filtered_data,
                        key=lambda x: str(x.get(sort_field, '')).lower(),
                        reverse=(sort_order == "Descending")
                    )
            except Exception as e:
                st.error(f"Error sorting collection: {str(e)}")
                print(f"Error sorting collection: {str(e)}")
        
        # Display empty state message if no cards
        if not filtered_data:
            st.warning("No cards found in your collection. Use the 'Add Cards' tab to add cards.")
            return
        
        # Display view options and cards
        view_options = ["Grid View", "Table View"]
        selected_view = st.radio("View As", view_options, horizontal=True)
        
        if selected_view == "Grid View":
            display_collection_grid(filtered_data)
        else:
            display_collection_table(filtered_data)
    
    except Exception as e:
        st.error(f"Error displaying collection: {str(e)}")
        print(f"Error in display_collection: {str(e)}")
        print(traceback.format_exc())

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
    
    return output.getvalue(), "card_collection_template.xlsx"

def delete_card(card_id, card_index=None):
    """
    Delete a card from the collection and Firebase using its unique ID
    
    Args:
        card_id: ID of the card to delete
        card_index: Index of the card in the collection (optional)
    
    Returns:
        dict: Result with success status and message
    """
    print(f"======= DELETE CARD FUNCTION CALLED =======")
    print(f"Card ID: {card_id}")
    print(f"Card Index: {card_index}")
    
    # Check for authentication
    if not st.session_state.get('user') or not st.session_state.get('uid'):
        return {'success': False, 'message': 'Not logged in. Please log in first.'}
    
    # Get user ID
    user_id = st.session_state.get('uid')
    
    # Ensure we have a collection
    if 'collection' not in st.session_state or not st.session_state.collection:
        return {'success': False, 'message': 'No collection found in session state.'}
    
    try:
        # STEP 1: Find the card by index or ID
        card_to_delete = None
        card_unique_id = None
        
        # If we have an index, use it to find the card
        if card_index is not None and 0 <= card_index < len(st.session_state.collection):
            card_to_delete = st.session_state.collection[card_index]
            # Get the card's unique ID if available
            if 'id' in card_to_delete:
                card_unique_id = card_to_delete['id']
                print(f"Found card by index with ID: {card_unique_id}")
        
        # If no card was found by index or no unique ID, try to use the provided card_id
        if not card_unique_id and card_id:
            card_unique_id = card_id
            print(f"Using provided card_id: {card_unique_id}")
            
            # Try to find the card in the collection to get complete data
            for i, card in enumerate(st.session_state.collection):
                if card.get('id') == card_unique_id:
                    card_to_delete = card
                    card_index = i
                    print(f"Found card by ID in collection at index {i}")
                    break
        
        # If we still don't have a card to delete, return error
        if not card_to_delete:
            return {'success': False, 'message': 'Card not found in collection.'}
        
        # STEP 2: Delete from Firebase
        try:
            # Initialize Firebase connection
            from firebase_admin import firestore
            db = firestore.client()
            
            # Try to delete from the user's collection field first
            user_ref = db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                # Get the current collection data
                user_data = user_doc.to_dict()
                collection = user_data.get('collection', [])
                
                # Remove the card from the collection array
                updated_collection = [card for card in collection if card.get('id') != card_unique_id]
                
                # Update the document with the new collection and metadata
                user_ref.update({
                    'collection': updated_collection,
                    'last_modified': datetime.now().isoformat(),
                    'collection_version': firestore.Increment(1)
                })
                
                # Also try to delete from the cards subcollection if it exists
                try:
                    card_ref = user_ref.collection('cards').document(card_unique_id)
                    card_ref.delete()
                except Exception as e:
                    print(f"Note: Could not delete from cards subcollection: {str(e)}")
            
            # STEP 3: Update local collection
            if card_index is not None:
                st.session_state.collection.pop(card_index)
            
            # Force a refresh of the collection data
            if 'last_refresh' in st.session_state:
                del st.session_state.last_refresh
            
            return {'success': True, 'message': 'Card deleted successfully!'}
            
        except Exception as e:
            print(f"Error deleting from Firebase: {str(e)}")
            return {'success': False, 'message': f'Error deleting card from database: {str(e)}'}
            
    except Exception as e:
        print(f"Error in delete_card: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return {'success': False, 'message': f'Error while trying to delete card: {str(e)}'}

def update_card(card_index, updated_data):
    """Update a card in the collection"""
    try:
        if not st.session_state.collection:
            st.error("No cards in collection")
            return False
            
        # Check if we have a valid index within range
        if card_index < 0 or card_index >= len(st.session_state.collection):
            st.error(f"Invalid card index: {card_index}")
            return False
        
        # Get the card to update
        card = st.session_state.collection[card_index]
        
        # Get the card ID from the card or from the updated data
        card_id = updated_data.get('id', None)
        if not card_id:
            # Generate the card ID
            if hasattr(card, 'to_dict'):
                card_dict = card.to_dict()
            else:
                card_dict = card
            
            # Construct an ID from the original card attributes
            card_id = f"{card_dict['player_name']}_{card_dict['year']}_{card_dict['card_set']}_{card_dict['card_number']}".replace(" ", "_").lower()
        
        # Make sure the updated data has an ID
        updated_data['id'] = card_id
        
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
        return False

def add_card(card_data):
    """Add a new card to the collection"""
    try:
        # Add created_at field for tracking recently added cards
        current_date = datetime.now()
        
        # Store created_at as ISO format for better compatibility across the app
        # This ensures a standard timestamp format that's easier to parse
        card_data['created_at'] = current_date.isoformat()
        
        # Ensure last_updated is also set
        card_data['last_updated'] = current_date.isoformat()
            
        # Generate a unique ID for the card
        card_id = f"{card_data['player_name']}_{card_data['year']}_{card_data['card_set']}_{card_data['card_number']}".replace(" ", "_").lower()
        card_data['id'] = card_id
        
        # Add the card to the subcollection
        cards_ref = db.collection('users').document(st.session_state.uid).collection('cards')
        cards_ref.document(card_id).set(card_data)
        
        # Add the card to the local collection
        if 'collection' not in st.session_state:
            st.session_state.collection = []
        
        # Make a copy of the card data to avoid reference issues
        st.session_state.collection.append(card_data.copy())
        
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
        
        # Update last_firebase_sync time
        st.session_state.last_firebase_sync = current_date
        
        # Set collection_loaded flag
        st.session_state.collection_loaded = True
        
        # Log the collection state
        logger.info(f"Card added successfully. Collection now has {len(st.session_state.collection)} cards.")
        
        st.success("Card added successfully!")
        # Switch to View Collection tab
        st.session_state.current_tab = "View Collection"
        st.rerun()
        return True
        
    except Exception as e:
        st.error(f"Error adding card: {str(e)}")
        logger.error(f"Error adding card: {str(e)}", exc_info=True)
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
            return {'success': False, 'message': f"Missing required columns: {', '.join(missing_columns)}"}
        
        # Convert DataFrame to list of dictionaries and clean NaN values
        cards = [clean_nan_values(row) for _, row in df.iterrows()]
        
        # Ensure the collection exists in session state
        if 'collection' not in st.session_state:
            st.session_state.collection = []
            
        # Keep track of imported cards
        imported_count = 0
            
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
                card['created_at'] = datetime.now().isoformat()  # Use ISO format for consistency
            
            # Add the card to the subcollection
            card_id = f"{card['player_name']}_{card['year']}_{card['card_set']}_{card['card_number']}".replace(" ", "_").lower()
            card['id'] = card_id
            
            try:
                cards_ref = db.collection('users').document(st.session_state.uid).collection('cards')
                cards_ref.document(card_id).set(card)
                
                # Make a copy of the card to avoid reference issues
                st.session_state.collection.append(card.copy())
                imported_count += 1
            except Exception as import_error:
                logger.error(f"Error importing card {card_id}: {str(import_error)}")
                # Continue with the next card
                continue
        
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
        
        # Update last_firebase_sync time
        st.session_state.last_firebase_sync = datetime.now()
        
        # Set collection_loaded flag
        st.session_state.collection_loaded = True
        
        logger.info(f"Successfully imported {imported_count} of {len(cards)} cards. Collection now has {len(st.session_state.collection)} cards.")
        st.success(f"Successfully imported {imported_count} cards!")
        
        return {
            'success': True, 
            'message': f"Successfully imported {imported_count} cards", 
            'count': imported_count
        }
        
    except Exception as e:
        logger.error(f"Error importing collection: {str(e)}", exc_info=True)
        st.error(f"Error importing collection: {str(e)}")
        return {'success': False, 'message': str(e)}

def export_collection():
    """Export the collection to Excel with improved reliability and error handling.
    Returns a tuple of (success, buffer) where buffer is the Excel file binary."""
    try:
        # Validate the collection first
        if not st.session_state.collection:
            return False, None
            
        collection = st.session_state.collection
        
        # Convert collection to DataFrame with proper error handling
        if isinstance(collection, pd.DataFrame):
            df = collection.copy()
        else:
            try:
                # Convert list to DataFrame - handle various card formats
                collection_dicts = []
                for card in collection:
                    # Handle Card objects, dictionaries, or other formats
                    if hasattr(card, 'to_dict') and callable(getattr(card, 'to_dict')):
                        # If it's a Card object with to_dict method
                        card_dict = card.to_dict()
                    elif isinstance(card, dict):
                        # If it's already a dictionary
                        card_dict = card
                    else:
                        # Try to convert to dict if possible
                        try:
                            card_dict = dict(card)
                        except (TypeError, ValueError):
                            print(f"Skipping card of type {type(card)} that cannot be converted to dictionary")
                            continue
                    
                    # Clean NaN values
                    card_dict = clean_nan_values(card_dict)
                    collection_dicts.append(card_dict)
                
                if not collection_dicts:
                    return False, None
                
                df = pd.DataFrame(collection_dicts)
            except Exception as e:
                print(f"Error converting collection to DataFrame: {str(e)}")
                print(traceback.format_exc())
                return False, None
        
        # Ensure the DataFrame is not empty
        if df.empty:
            return False, None
        
        # Format date columns properly
        date_columns = ['purchase_date', 'last_updated']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                df[col] = df[col].dt.strftime('%Y-%m-%d')
        
        # Handle tags column which might be a list
        if 'tags' in df.columns:
            df['tags'] = df['tags'].apply(
                lambda x: ', '.join(x) if isinstance(x, list) else x
            )
        
        # Create Excel file in memory
        output = io.BytesIO()
        
        try:
            # Convert DataFrame to Excel
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Collection', index=False)
                
                # Get the xlsxwriter workbook and worksheet objects
                workbook = writer.book
                worksheet = writer.sheets['Collection']
                
                # Add some formatting
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#D0E0F5',
                    'border': 1
                })
                
                # Write the column headers with the defined format
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    
                # Auto-adjust column widths
                for i, col in enumerate(df.columns):
                    max_len = max(
                        df[col].astype(str).map(len).max(),
                        len(str(col))
                    ) + 2
                    worksheet.set_column(i, i, max_len)
        except Exception as e:
            print(f"Error writing Excel file: {str(e)}")
            print(traceback.format_exc())
            return False, None
        
        # Seek to the beginning of the stream
        output.seek(0)
        
        return True, output
    except Exception as e:
        print(f"Unexpected error in export_collection: {str(e)}")
        print(traceback.format_exc())
        return False, None

def check_firebase_connection():
    """Diagnostic function to check Firebase connectivity and card structure"""
    try:
        st.subheader("Firebase Connection Status")
        
        # Get Firebase client
        with st.spinner("Checking Firebase connection..."):
            firebase_manager = FirebaseManager.get_instance()
            if not firebase_manager._initialized:
                if not firebase_manager.initialize():
                    st.error("❌ Firebase connection failed. Please check your internet connection or try again later.")
                    return {"success": False, "message": "Firebase initialization failed"}
                
        # Check database connection
        db = firebase_manager.db
        if not db:
            st.error("❌ Firestore database connection failed")
            return {"success": False, "message": "Firestore database connection failed"}
            
        # Check user auth
        if not st.session_state.user or not st.session_state.uid:
            st.error("❌ User not authenticated. Please log in again.")
            return {"success": False, "message": "User not authenticated"}
            
        # Check user document
        user_doc = db.collection('users').document(st.session_state.uid).get()
        if not user_doc.exists:
            st.error("❌ User document not found in database")
            return {"success": False, "message": "User document not found"}
            
        # Check cards collection
        cards_ref = db.collection('users').document(st.session_state.uid).collection('cards')
        card_docs = list(cards_ref.stream())
        
        if card_docs:
            st.success(f"✅ Found {len(card_docs)} cards in your collection")
        else:
            # Check if cards are stored in the user document instead
            user_data = user_doc.to_dict()
            if 'collection' in user_data and user_data['collection']:
                st.success(f"✅ Found {len(user_data['collection'])} cards in your user document")
            else:
                st.warning("⚠️ No cards found in your collection")
        
        st.success("✅ Firebase connection successful")
        return {"success": True, "message": "Firebase connection OK"}
            
    except Exception as e:
        st.error(f"❌ Connection check failed: {str(e)}")
        return {"success": False, "message": f"Connection check failed: {str(e)}"}

def repair_firebase_collection():
    """Diagnostic function to repair Firebase collection issues"""
    try:
        # Get Firebase client
        with st.spinner("Connecting to Firebase..."):
            firebase_manager = FirebaseManager.get_instance()
            if not firebase_manager._initialized:
                if not firebase_manager.initialize():
                    st.error("Firebase initialization failed. Please check your connection.")
                    return {"success": False, "message": "Firebase initialization failed"}
                
        db = firebase_manager.db
        if not db:
            st.error("Firestore client not available. Please check Firebase configuration.")
            return {"success": False, "message": "Firestore client not available"}
            
        st.subheader("Firebase Collection Repair Utility")
        st.write("This tool will help fix synchronization issues between your local collection and Firebase.")

        # Get all cards from Firebase
        with st.spinner("Retrieving cards from Firebase..."):
            cards_ref = db.collection('users').document(st.session_state.uid).collection('cards')
            firebase_cards = list(cards_ref.stream())
        
        # Get local collection
        local_collection = st.session_state.collection if hasattr(st.session_state, 'collection') else []
        
        # Compare counts
        st.write(f"Found {len(firebase_cards)} cards in Firebase and {len(local_collection)} cards in your local collection.")
        
        # Check for discrepancies
        if abs(len(firebase_cards) - len(local_collection)) > 5:
            st.warning(f"⚠️ Large difference detected between Firebase ({len(firebase_cards)} cards) and local collection ({len(local_collection)} cards)")
        elif len(firebase_cards) == len(local_collection):
            st.success("✅ Firebase and local collection have the same number of cards.")
        else:
            st.info(f"ℹ️ Small difference detected: {abs(len(firebase_cards) - len(local_collection))} cards")
            
        # Provide repair options
        repair_options = st.radio(
            "Repair Options",
            ["Check for Issues Only", "Download All Firebase Cards", "Upload Local Collection to Firebase", "Clean Up Duplicate Cards"]
        )
        
        # Create mappings and identify issues
        with st.spinner("Analyzing synchronization issues..."):
            firebase_ids = [doc.id for doc in firebase_cards]
            firebase_data = {doc.id: doc.to_dict() for doc in firebase_cards}
        
        # Create a mapping of local cards to expected Firebase IDs
        local_card_keys = []
        for card in local_collection:
            # Try to create a key for matching
            player = card.get('player_name', '')
            year = card.get('year', '')
            card_set = card.get('card_set', '')
            num = card.get('card_number', '')
            
            if player and year and card_set:
                key = f"{player}_{year}_{card_set}_{num}".lower().replace(' ', '_')
                local_card_keys.append(key)
                
        # Find issues
        firebase_only = []
        for doc_id, card_data in firebase_data.items():
            player = card_data.get('player_name', '')
            year = card_data.get('year', '')
            card_set = card_data.get('card_set', '')
            num = card_data.get('card_number', '')
            
            if player and year and card_set:
                key = f"{player}_{year}_{card_set}_{num}".lower().replace(' ', '_')
                if key not in local_card_keys:
                    firebase_only.append({
                        'id': doc_id,
                        'data': card_data
                    })
        
        # Show diagnosis results
        if firebase_only:
            st.warning(f"Found {len(firebase_only)} cards in Firebase that aren't in your local collection.")
            
            # Show example of missing card
            if len(firebase_only) > 0:
                example = firebase_only[0]['data']
                st.write("Example card missing from local collection:")
                st.write(f"- Player: {example.get('player_name', 'Unknown')}")
                st.write(f"- Year: {example.get('year', 'Unknown')}")
                st.write(f"- Set: {example.get('card_set', 'Unknown')}")
        else:
            st.success("✅ All Firebase cards are present in your local collection.")
            
        # Execute repairs based on selection
        if st.button("Execute Selected Repair"):
            if repair_options == "Download All Firebase Cards":
                with st.spinner("Downloading all cards from Firebase..."):
                    result = download_all_firebase_cards()
                    if result:
                        st.success("✅ Successfully downloaded all Firebase cards!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to download Firebase cards.")
                        
            elif repair_options == "Upload Local Collection to Firebase":
                with st.spinner("Uploading local collection to Firebase..."):
                    success = save_collection_to_firebase()
                    if success:
                        st.success("✅ Successfully uploaded local collection to Firebase!")
                    else:
                        st.error("❌ Failed to upload collection.")
                        
            elif repair_options == "Clean Up Duplicate Cards":
                st.info("This function will be implemented in a future update.")
                
        return {"success": True, "message": "Collection diagnosis complete"}
        
    except Exception as e:
        st.error(f"Error diagnosing collection: {str(e)}")
        print(traceback.format_exc())
        return {"success": False, "message": str(e)}

def inspect_card_dates():
    """Inspect card dates for any issues and provide repair options."""
    try:
        collection = st.session_state.collection if hasattr(st.session_state, 'collection') else []
        
        if not collection:
            st.warning("No cards in collection to inspect")
            return
            
        date_fields = ['purchase_date', 'last_updated', 'created_at']
        date_issues = []
        
        for i, card in enumerate(collection):
            for field in date_fields:
                if field in card and card[field]:
                    try:
                        # Handle different date formats
                        date_str = str(card[field])
                        
                        # Try parsing with different formats
                        try:
                            # Try ISO format with time component
                            if ' ' in date_str:  # Format like "2025-04-19 16:09:53"
                                datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                            else:  # Format like "2025-04-19"
                                datetime.strptime(date_str, '%Y-%m-%d')
                        except ValueError as e:
                            # If parsing fails, record the issue
                            player_name = card.get('player_name', f'Card {i}')
                            card_year = card.get('year', '')
                            card_set = card.get('card_set', '')
                            date_issues.append({
                                'card_index': i,
                                'card': f"{player_name} {card_year} {card_set}",
                                'field': field,
                                'value': date_str,
                                'issue': f"Invalid date format: {str(e)}"
                            })
                    except Exception as e:
                        player_name = card.get('player_name', f'Card {i}')
                        card_year = card.get('year', '')
                        card_set = card.get('card_set', '')
                        date_issues.append({
                            'card_index': i,
                            'card': f"{player_name} {card_year} {card_set}",
                            'field': field,
                            'value': card.get(field, ''),
                            'issue': f"Error processing date: {str(e)}"
                        })
        
        if not date_issues:
            st.success("✅ All card dates are valid!")
            return
            
        st.warning(f"Found {len(date_issues)} date issues in your collection")
        
        # Display issues in a table
        issue_df = pd.DataFrame(date_issues)
        st.dataframe(issue_df)
        
        # Provide repair options
        if st.button("Fix Date Issues"):
            with st.spinner("Fixing date issues..."):
                fixed_count = 0
                for i, issue in enumerate(date_issues):
                    try:
                        card_index = issue['card_index']
                        field = issue['field']
                        
                        # Set to today's date in ISO format
                        st.session_state.collection[card_index][field] = datetime.now().date().isoformat()
                        fixed_count += 1
                    except Exception as e:
                        st.error(f"Error fixing date for {issue['card']}: {str(e)}")
                
                if fixed_count > 0:
                    st.success(f"Fixed {fixed_count} date issues!")
                    st.rerun()
                else:
                    st.error("Failed to fix any date issues.")
    
    except Exception as e:
        st.error(f"Error inspecting card dates: {str(e)}")
        import traceback
        st.write(traceback.format_exc())

def download_all_firebase_cards():
    """Download all cards from Firebase to the local collection, checking all possible locations."""
    try:
        st.info("Starting Firebase card download process...")
        
        # Check if user is logged in
        if not hasattr(st.session_state, 'uid') or not st.session_state.uid:
            st.error("You must be logged in to download cards.")
            return {'success': False, 'message': 'You must be logged in to download cards.'}
        
        # Get Firebase client
        firebase_manager = FirebaseManager.get_instance()
        if not firebase_manager._initialized:
            st.info("Initializing Firebase connection...")
            if not firebase_manager.initialize():
                st.error("Firebase initialization failed. Please check your connection.")
                return {'success': False, 'message': 'Firebase initialization failed.'}
                
        db = firebase_manager.db
        if not db:
            st.error("Firestore client not available. Please check Firebase configuration.")
            return {'success': False, 'message': 'Firestore client not available.'}

        # Create a completely new collection (don't try to merge)
        new_collection = []
        
        # 1. First try to get the user document and check for an embedded collection
        st.info("Checking user document for embedded collection...")
        user_ref = db.collection('users').document(st.session_state.uid)
        
        try:
            user_doc = user_ref.get()
            if not user_doc.exists:
                st.error("User document not found in Firestore.")
                return {'success': False, 'message': 'User document not found in Firestore.'}
                
            user_data = user_doc.to_dict()
            
            # Check for collection in user document
            if 'collection' in user_data and isinstance(user_data['collection'], list) and user_data['collection']:
                st.info(f"Found {len(user_data['collection'])} cards in user document 'collection' field.")
                
                # Process each card in the collection
                for i, card in enumerate(user_data['collection']):
                    try:
                        # Special handling for card 17 which is causing issues
                        if i == 17:  # Card at index 17
                            st.info(f"Special handling for problematic card at index 17")
                            # Print the card data to help identify the issue
                            print(f"Card 17 data structure: {type(card)}")
                            print(f"Card 17 keys: {card.keys() if isinstance(card, dict) else 'Not a dict'}")
                            
                            # Force-handle potential problem fields
                            if isinstance(card, dict) and 'player_name' in card:
                                # Create a safe copy and manually clean fields that might be arrays
                                safe_card = {}
                                for k, v in card.items():
                                    try:
                                        # Special handling for array values
                                        if isinstance(v, (np.ndarray, pd.Series)):
                                            print(f"Card 17 field {k} is an array/series of shape {getattr(v, 'shape', 'unknown')}")
                                            if hasattr(v, 'size') and v.size > 0:
                                                if v.size == 1:
                                                    # Single value array - extract the first element
                                                    safe_card[k] = v.item() if hasattr(v, 'item') else v[0]
                                                else:
                                                    # Multi-value array - convert to list
                                                    safe_card[k] = v.tolist() if hasattr(v, 'tolist') else list(v)
                                            else:
                                                # Empty array, set appropriate default
                                                if k in ['purchase_price', 'current_value', 'high_value', 'low_value']:
                                                    safe_card[k] = 0.0
                                                elif k == 'tags':
                                                    safe_card[k] = []
                                                else:
                                                    safe_card[k] = ''
                                        elif pd.isna(v):
                                            # NaN values get defaults
                                            if k in ['purchase_price', 'current_value', 'high_value', 'low_value']:
                                                safe_card[k] = 0.0
                                            elif k == 'tags':
                                                safe_card[k] = []
                                            else:
                                                safe_card[k] = ''
                                        else:
                                            # Regular value, copy as-is
                                            safe_card[k] = v
                                    except Exception as field_error:
                                        print(f"Error processing field {k} in card 17: {str(field_error)}")
                                        # Set a safe default value
                                        if k in ['purchase_price', 'current_value', 'high_value', 'low_value']:
                                            safe_card[k] = 0.0
                                        elif k == 'tags':
                                            safe_card[k] = []
                                        else:
                                            safe_card[k] = ''
                                
                                # Only add the card if it has the minimum required fields
                                if 'player_name' in safe_card and safe_card['player_name']:
                                    new_collection.append(safe_card)
                                    print("Successfully processed and added card 17 with special handling")
                                else:
                                    print("Card 17 missing player_name after special handling, skipping")
                            else:
                                print(f"Card 17 is not a valid dict or missing player_name")
                        else:
                            # Regular processing for other cards
                            if isinstance(card, dict) and 'player_name' in card:
                                # Clean and add to new collection
                                cleaned_card = clean_nan_values(card)
                                new_collection.append(cleaned_card)
                    except Exception as card_error:
                        st.warning(f"Error processing card {i}: {str(card_error)}")
                        # Continue processing other cards
                        continue
                    
                st.success(f"Downloaded {len(new_collection)} cards from user document.")
            else:
                st.info("No 'collection' field found in user document or it's empty.")
                
            # Also check for savedCards
            if 'savedCards' in user_data and isinstance(user_data['savedCards'], list) and user_data['savedCards']:
                st.info(f"Found {len(user_data['savedCards'])} cards in 'savedCards' field.")
                saved_cards_count = 0
                
                for i, card in enumerate(user_data['savedCards']):
                    try:
                        if isinstance(card, dict) and 'player_name' in card:
                            # Only add if we don't already have a card with the same key attributes
                            is_duplicate = False
                            for existing_card in new_collection:
                                if (existing_card.get('player_name') == card.get('player_name') and
                                    existing_card.get('year') == card.get('year') and
                                    existing_card.get('card_set') == card.get('card_set') and
                                    existing_card.get('card_number') == card.get('card_number')):
                                    is_duplicate = True
                                    break
                                    
                            if not is_duplicate:
                                cleaned_card = clean_nan_values(card)
                                new_collection.append(cleaned_card)
                                saved_cards_count += 1
                    except Exception as card_error:
                        st.warning(f"Error processing saved card {i}: {str(card_error)}")
                        # Continue processing other cards
                        continue
                
                if saved_cards_count > 0:
                    st.success(f"Added {saved_cards_count} additional cards from 'savedCards' field.")
            
        except Exception as user_doc_error:
            st.error(f"Error getting user document: {str(user_doc_error)}")
            st.write(traceback.format_exc())
        
        # 2. Now check the cards subcollection
        st.info("Checking 'cards' subcollection...")
        cards_ref = user_ref.collection('cards')
        
        try:
            firebase_cards = list(cards_ref.stream())
            
            if firebase_cards:
                st.info(f"Found {len(firebase_cards)} cards in 'cards' subcollection.")
                subcollection_count = 0
                
                for doc in firebase_cards:
                    try:
                        card_data = doc.to_dict()
                        
                        # Skip invalid cards
                        if not isinstance(card_data, dict) or 'player_name' not in card_data:
                            continue
                            
                        # Add Firebase ID to help with future syncing
                        card_data['id'] = doc.id
                        
                        # Check for duplicates
                        is_duplicate = False
                        for existing_card in new_collection:
                            if (existing_card.get('player_name') == card_data.get('player_name') and
                                existing_card.get('year') == card_data.get('year') and
                                existing_card.get('card_set') == card_data.get('card_set') and
                                existing_card.get('card_number') == card_data.get('card_number')):
                                is_duplicate = True
                                break
                                
                        if not is_duplicate:
                            try:
                                cleaned_card = clean_nan_values(card_data)
                                new_collection.append(cleaned_card)
                                subcollection_count += 1
                            except Exception as clean_error:
                                st.warning(f"Error cleaning card {doc.id}: {str(clean_error)}")
                                # Skip this card but continue with others
                                continue
                            
                    except Exception as card_error:
                        st.warning(f"Error processing card {doc.id}: {str(card_error)}")
                        continue
                
                if subcollection_count > 0:
                    st.success(f"Added {subcollection_count} additional cards from 'cards' subcollection.")
            else:
                st.info("No cards found in 'cards' subcollection.")
                
        except Exception as subcol_error:
            st.error(f"Error accessing cards subcollection: {str(subcol_error)}")
            st.write(traceback.format_exc())
        
        # Final check and update session state
        if new_collection:
            # Sort the collection by player name for better browsing
            try:
                new_collection = sorted(new_collection, key=lambda x: str(x.get('player_name', '')).lower())
            except Exception as sort_error:
                st.warning(f"Unable to sort collection: {str(sort_error)}")
            
            # REPLACE the local collection with the merged collection
            st.session_state.collection = new_collection
            st.session_state.collection_loaded = True
            st.session_state.last_firebase_sync = datetime.now()
            
            st.success(f"Successfully downloaded a total of {len(new_collection)} cards!")
            st.balloons()
            
            # Force a refresh
            if 'last_refresh' in st.session_state:
                del st.session_state.last_refresh
            st.session_state.refresh_required = True
            return {
                'success': True,
                'message': f'Successfully downloaded {len(new_collection)} cards',
                'count': len(new_collection)
            }
        else:
            st.warning("No cards found in any Firebase location. Your collection is empty.")
            # Make sure we don't have an old local collection hanging around
            st.session_state.collection = []
            st.session_state.collection_loaded = True
            st.session_state.last_firebase_sync = datetime.now()
            return {
                'success': False,
                'message': 'No cards found in any Firebase location',
                'count': 0
            }
        
    except Exception as e:
        st.error(f"Download failed: {str(e)}")
        st.write(f"Error details: {traceback.format_exc()}")
        return {
            'success': False,
            'message': f'Download failed: {str(e)}',
            'count': 0
        }

def main():
    """Main function to run the collection manager."""
    
    try:
        # Check if user is authenticated
        if not st.session_state.get('user') or not st.session_state.get('uid'):
            st.warning("Please log in first.")
            return
        
        # Ensure the authenticated flag is set if we have user and uid
        st.session_state.authenticated = True
        
        logger.debug("User is authenticated. Loading collection from Firebase.")
        
        # Initialize session state variables
        init_session_state()
        
        # Debug: Show session state before loading
        if 'collection' in st.session_state:
            logger.debug(f"Collection before reload: {len(st.session_state.get('collection', []))} cards")
        else:
            logger.debug("No collection in session state before reload")
        
        # Check if we have cards already and if we need to refresh
        existing_collection_size = len(st.session_state.get('collection', []))
        force_refresh = st.session_state.get('force_refresh', False) or existing_collection_size == 0
        
        # Use the more reliable download_all_firebase_cards function to ensure we get all cards
        with st.spinner("Loading your collection..."):
            if force_refresh or existing_collection_size == 0:
                # If no cards or force refresh, use the more robust download_all_firebase_cards function
                logger.debug("Using download_all_firebase_cards to get complete collection")
                download_result = download_all_firebase_cards()
                
                if download_result.get('success', False):
                    logger.debug(f"Successfully loaded {len(st.session_state.get('collection', []))} cards")
                else:
                    # Fall back to standard loading if download failed
                    logger.debug("Full download failed, falling back to standard loading")
                    firebase_result = load_collection_from_firebase()
                    
                    # Debug the result
                    logger.debug(f"Firebase load result: {firebase_result.get('message', 'No message')}")
                    logger.debug(f"Firebase load success: {firebase_result.get('success', False)}")
                    logger.debug(f"Firebase cards count: {firebase_result.get('count', 0)}")
                    
                    if not firebase_result.get('success', False):
                        st.warning(f"Failed to load collection: {firebase_result.get('message', 'Unknown error')}")
                        # Set an empty collection if there isn't one already
                        if 'collection' not in st.session_state:
                            st.session_state.collection = []
                            st.session_state.collection_loaded = True
                    else:
                        logger.debug(f"Successfully loaded {len(st.session_state.get('collection', []))} cards from Firebase")
            else:
                # If we already have cards and don't need to refresh, skip loading
                logger.debug(f"Using existing collection with {existing_collection_size} cards")
        
        # Reset the force refresh flag
        st.session_state.force_refresh = False
        
        # Display debug info at the top of the page
        with st.expander("Debug Info (Click to expand)"):
            st.write(f"Collection size in session: {len(st.session_state.get('collection', []))}")
            st.write(f"User ID: {st.session_state.get('uid', 'None')}")
            st.write(f"Last Firebase sync: {st.session_state.get('last_firebase_sync', 'Never')}")
            st.write(f"Edit mode: {st.session_state.get('edit_mode', False)}")
            st.write(f"Edit card ID: {st.session_state.get('edit_card_id', 'None')}")
            
            if st.button("Dump Collection Data"):
                st.json(st.session_state.get('collection', []))
                
            # Add debug button to clear edit mode if needed
            if st.button("Clear Edit Mode"):
                if "edit_mode" in st.session_state:
                    del st.session_state.edit_mode
                if "edit_index" in st.session_state:
                    del st.session_state.edit_index
                if "edit_card_data" in st.session_state:
                    del st.session_state.edit_card_data
                if "edit_card_id" in st.session_state:
                    del st.session_state.edit_card_id
                if "redirect_to_edit" in st.session_state:
                    del st.session_state.redirect_to_edit
                st.query_params.clear()
                st.rerun()
        
        # System Information
        system_info = {
            "Python Version": platform.python_version(),
            "Streamlit Version": st.__version__,
            "Operating System": f"{platform.system()} {platform.release()}",
            "Current User": st.session_state.user.get('displayName', 'Unknown'),
            "User Email": st.session_state.user.get('email', 'Unknown'),
            "User ID": st.session_state.user.get('localId', 'Unknown'),
            "Collection Size": len(st.session_state.get('collection', [])),
            "Last Firebase Sync": st.session_state.get('last_firebase_sync', 'Never')
        }
        
        # Check for redirect to edit mode from button click
        if st.session_state.get('redirect_to_edit', False):
            # Clear the redirect flag to prevent infinite loops
            st.session_state.redirect_to_edit = False
            # Rerun once to process the edit mode
            st.rerun()
            
        # Check if we're in edit mode
        if st.session_state.get('edit_mode', False) and 'edit_card_data' in st.session_state:
            # Use the card data directly from session state
            card_data = st.session_state.edit_card_data
            card_index = st.session_state.get('edit_index', 0)
            
            # Create a form container to ensure stability
            edit_container = st.container()
            
            with edit_container:
                # Show the edit form in a container with a cancel button
                st.title("Edit Card")
                
                # Add a cancel button
                if st.button("← Back to Collection", key="cancel_edit"):
                    # Clear edit mode and redirect back to collection view
                    st.session_state.edit_mode = False
                    if "edit_index" in st.session_state:
                        del st.session_state.edit_index
                    if "edit_card_data" in st.session_state:
                        del st.session_state.edit_card_data
                    if "edit_card_id" in st.session_state:
                        del st.session_state.edit_card_id
                    # Clear the query parameter
                    st.query_params.clear()
                    st.rerun()
                
                # Display the edit form
                edit_card_form(card_index, card_data)
            
            # Return here to avoid showing the main interface
            return
        
        # Display the Collection Manager Interface
        st.title("Collection Manager")
        
        # Create tabs for different functionalities
        tabs = ["Add Cards", "View Collection", "Import/Export", "Diagnostics"]
        add_tab, view_tab, import_export_tab, diagnostics_tab = st.tabs(tabs)
        
        # Get all query parameters using the new method
        query_params = st.query_params
        
        # Check if edit parameter is in URL and we're not already in edit mode
        if 'edit' in query_params and not st.session_state.get('edit_mode', False):
            edit_param = query_params['edit']
            
            # Check if we have a collection
            if 'collection' in st.session_state and st.session_state.collection:
                collection = st.session_state.collection
                found_card = False
                
                # First try to interpret as an index (for backward compatibility)
                try:
                    card_index = int(edit_param)
                    if 0 <= card_index < len(collection):
                        # Found a valid index
                        card_data = collection[card_index]
                        st.session_state.edit_index = card_index
                        st.session_state.edit_card_data = card_data
                        st.session_state.edit_card_id = card_data.get('id', str(card_index))
                        st.session_state.edit_mode = True
                        found_card = True
                except ValueError:
                    # Not a valid index, try to find by ID
                    for i, card in enumerate(collection):
                        # Check if this card has the ID we're looking for
                        card_id = card.get('id', None)
                        if card_id and card_id == edit_param:
                            # Found the card by ID
                            st.session_state.edit_index = i
                            st.session_state.edit_card_data = card
                            st.session_state.edit_card_id = card_id
                            st.session_state.edit_mode = True
                            found_card = True
                            break
                
                # If we found the card, set the redirect flag to trigger a rerun
                if found_card:
                    st.session_state.redirect_to_edit = True
                    st.rerun()
                else:
                    # If we get here, we didn't find the card - clear the parameter
                    st.query_params.pop("edit")
        
        # Add tab content
        with add_tab:
            st.header("Add a Card")
            display_add_card_form()
        
        # View collection tab content
        with view_tab:
            st.header("Your Collection")
            
            # Add collection control buttons
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                # Add a reload button that forces a full reload from Firebase
                if st.button("🔄 Reload Collection", use_container_width=True):
                    st.session_state.force_refresh = True
                    with st.spinner("Reloading your collection..."):
                        reload_result = download_all_firebase_cards()
                        if reload_result.get('success', False):
                            st.success(f"Successfully reloaded {reload_result.get('count', 0)} cards!")
                            st.rerun()
                        else:
                            st.error(f"Failed to reload collection: {reload_result.get('message', 'Unknown error')}")
            
            with col2:
                # Add an update values button
                if st.button("💰 Update Values", use_container_width=True):
                    if 'collection' in st.session_state and st.session_state.collection:
                        with st.spinner("Updating card values..."):
                            update_result = update_card_values(st.session_state.collection)
                            if update_result:
                                st.success("Successfully updated card values!")
                                st.rerun()
                            else:
                                st.error("Failed to update card values.")
                    else:
                        st.error("No cards to update. Add some cards first.")
            
            # Add debug info about collection data
            st.write(f"Collection size: {len(st.session_state.get('collection', []))} cards")
            
            # Always use the collection from session state directly
            if 'collection' in st.session_state and st.session_state.collection:
                # Force using the collection from session state
                display_collection(st.session_state.collection)
            else:
                # Show a more helpful message and options when no cards
                st.warning("No cards in collection. You can add cards manually or import a collection.")
                
                # Add a quick way to add a sample card
                st.subheader("Add a sample card to get started")
                if st.button("Add Sample Card"):
                    # Create a sample card
                    sample_card = {
                        "player_name": "Sample Player",
                        "year": "2023",
                        "card_set": "Sample Set",
                        "card_number": "1",
                        "condition": "Mint",
                        "purchase_price": 10.00,
                        "current_value": 15.00,
                        "photo": "https://placehold.co/300x400?text=Sample+Card",
                        "notes": "This is a sample card to help you get started.",
                        "tags": ["sample", "demo"],
                        "purchase_date": datetime.now().strftime("%Y-%m-%d")
                    }
                    
                    # Add the sample card
                    add_result = add_card(sample_card)
                    if add_result.get('success', False):
                        st.success("Sample card added successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to add sample card: {add_result.get('message', 'Unknown error')}")
        
        # Import/Export tab content
        with import_export_tab:
            st.header("Import/Export Collection")
            
            # Import section
            st.subheader("Import Collection")
            import_file = st.file_uploader("Upload Excel File", type=["xlsx"], key="import_file")
            if import_file:
                if st.button("Import Cards", key="import_button"):
                    with st.spinner("Importing cards..."):
                        result = import_collection(import_file)
                        if result.get('success', False):
                            st.success(f"Successfully imported {result.get('count', 0)} cards!")
                            st.rerun()
                        else:
                            st.error(f"Import failed: {result.get('message', 'Unknown error')}")
            
            # Show sample template
            if st.button("Generate Sample Template"):
                template_data, filename = generate_sample_template()
                st.download_button(
                    label="Download Sample Template",
                    data=template_data,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
        
        # Diagnostics tab content
        with diagnostics_tab:
            st.header("Collection Diagnostics")
            
            diag_col1, diag_col2 = st.columns(2)
            
            with diag_col1:
                st.subheader("Firebase Connection")
                if st.button("Check Firebase Connection", key="check_firebase_button"):
                    with st.spinner("Checking Firebase connection..."):
                        result = check_firebase_connection()
                        if result.get('success', False):
                            st.success(f"Firebase connection successful! {result.get('message', '')}")
                        else:
                            st.error(f"Firebase connection failed: {result.get('message', 'Unknown error')}")
                            
                if st.button("Download All Firebase Cards", key="download_firebase_button"):
                    with st.spinner("Downloading cards from Firebase..."):
                        result = download_all_firebase_cards()
                        if result.get('success', False):
                            st.success(f"Successfully downloaded {result.get('count', 0)} cards!")
                            st.rerun()
                        else:
                            st.error(f"Download failed: {result.get('message', 'Unknown error')}")
            
            with diag_col2:
                st.subheader("Collection Repair")
                if st.button("Repair Collection", key="repair_collection_button"):
                    with st.spinner("Attempting to repair collection..."):
                        result = repair_firebase_collection()
                        if result.get('success', False):
                            st.success(f"Collection repair successful! {result.get('message', '')}")
                        else:
                            st.error(f"Collection repair failed: {result.get('message', 'Unknown error')}")
                            
            # Debug actions
            st.subheader("Debug Actions")
            debug_col1, debug_col2 = st.columns(2)
            with debug_col1:
                if st.button("Clear Session State", key="clear_session_state"):
                    for key in list(st.session_state.keys()):
                        if key != 'user' and key != 'uid' and key != 'authenticated':
                            del st.session_state[key]
                    st.success("Session state cleared (except auth data)")
                    st.rerun()
                    
            with debug_col2:
                if st.button("Show Current Session State", key="show_session_state"):
                    # Display all session state variables except sensitive user info
                    session_state_copy = {k: v for k, v in st.session_state.items() 
                                         if k not in ['user', 'password', 'password_confirm']}
                    st.json(session_state_copy)
                    
        # Check for completed edit that needs a rerun to display collection view
        if st.session_state.get('edit_completed', False):
            # Clear the flag to prevent multiple reruns
            del st.session_state.edit_completed
            # Rerun to show collection view
            st.rerun()
    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.write(f"Error details: {traceback.format_exc()}")
        print(f"Error in main: {str(e)}")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()

