import streamlit as st
import pandas as pd
import io
from datetime import datetime, date
from PIL import Image
import base64
import requests
from modules.core.market_analysis import MarketAnalyzer
from modules.core.collection_manager import CollectionManager
from scrapers.ebay_interface import EbayInterface
from modules.firebase.config import db
from modules.firebase.user_management import UserManager
from modules.database import Card, UserPreferences, DatabaseService
from modules.database.models import CardCondition
from modules.ui.collection_display import display_collection_grid, display_collection_table
from modules.ui.styles import get_collection_styles
from io import BytesIO
import json
from modules.core.card_value_analyzer import CardValueAnalyzer # type: ignore

# Configure the page
st.set_page_config(
    page_title="Collection Manager - Sports Card Analyzer Pro",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"  # Collapse sidebar by default on mobile
)

# Apply global styles once at the start
st.markdown(get_collection_styles(), unsafe_allow_html=True)

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
        if save_collection_to_firebase(st.session_state.collection):
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
                    # Convert uploaded photo to base64
                    photo_bytes = photo.read()
                    photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
                    new_card['photo'] = f"data:image/{photo.type.split('/')[-1]};base64,{photo_base64}"
                
                # Add card to collection
                if 'collection' not in st.session_state:
                    st.session_state.collection = []
                
                st.session_state.collection.append(new_card)
                
                # Save to Firebase
                if DatabaseService.save_user_collection(st.session_state.uid, st.session_state.collection):
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
    
    # Calculate summary metrics
    total_value = sum(
        card.get('current_value', 0) if isinstance(card, dict) 
        else getattr(card, 'current_value', 0) if hasattr(card, 'current_value')
        else 0
        for card in filtered_collection
    )
    total_cost = sum(
        card.get('purchase_price', 0) if isinstance(card, dict)
        else getattr(card, 'purchase_price', 0) if hasattr(card, 'purchase_price')
        else 0
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
        
        # Add submit button
        submitted = st.form_submit_button("Save Changes")
        
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
                    # Resize to smaller dimensions
                    img.thumbnail((400, 500))
                    # Convert to RGB if necessary
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    # Save with higher compression
                    buffer = BytesIO()
                    img.save(buffer, format="JPEG", quality=50, optimize=True)
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
            if save_collection_to_firebase(st.session_state.collection):
                st.success("Card updated successfully!")
                st.session_state.editing_card = None
                st.session_state.editing_data = None
                st.rerun()
            else:
                st.error("Failed to save changes to database.")

def load_collection_from_firebase():
    """Load collection from Firebase"""
    try:
        if not st.session_state.uid:
            st.error("User not logged in")
            return []
        
        with st.spinner("Loading collection..."):
            collection_data = DatabaseService.get_user_collection(st.session_state.uid)
            if collection_data:
                return collection_data
            else:
                return []
    
    except Exception as e:
        st.error(f"Error loading collection: {str(e)}")
        return []

def save_collection_to_firebase(collection_df):
    """Save the collection to Firebase for the current user"""
    try:
        # Convert DataFrame to list of dictionaries if needed
        if isinstance(collection_df, pd.DataFrame):
            cards_data = collection_df.to_dict('records')
        else:
            cards_data = collection_df
            
        cards = []
        
        for idx, row in enumerate(cards_data):
            try:
                # Handle photo data first to ensure it's properly processed
                photo = safe_get(row, 'photo')
                photo_data = None
                
                if photo is not None and not pd.isna(photo):
                    if isinstance(photo, str):
                        if photo.startswith('data:image'):
                            # Validate base64 image
                            try:
                                # Check if it's a valid base64 string
                                base64_part = photo.split(',')[1]
                                # Decode and re-encode to ensure validity
                                image_data = base64.b64decode(base64_part)
                                # Re-encode with proper format
                                photo_data = f"data:image/jpeg;base64,{base64.b64encode(image_data).decode()}"
                            except Exception as e:
                                st.warning(f"Warning: Invalid base64 image for card {idx + 1}. Error: {str(e)}")
                                photo_data = None
                        elif photo.startswith('http'):
                            # Validate URL image
                            try:
                                response = requests.head(photo, timeout=5)
                                if response.status_code == 200:
                                    # Get the image content
                                    img_response = requests.get(photo, timeout=10)
                                    img_response.raise_for_status()
                                    # Convert to base64
                                    photo_data = f"data:image/jpeg;base64,{base64.b64encode(img_response.content).decode()}"
                                else:
                                    st.warning(f"Warning: Invalid image URL status code {response.status_code} for card {idx + 1}")
                            except Exception as e:
                                st.warning(f"Warning: Failed to process image URL for card {idx + 1}: {str(e)}")
                    elif hasattr(photo, 'getvalue'):
                        try:
                            # Handle file upload object
                            photo_bytes = photo.getvalue()
                            # Convert to base64
                            photo_data = f"data:image/jpeg;base64,{base64.b64encode(photo_bytes).decode()}"
                        except Exception as photo_error:
                            st.warning(f"Warning: Could not process photo for card {idx + 1}. Error: {str(photo_error)}")
                    elif isinstance(photo, (list, tuple)):
                        # Handle array of photos - take the first one
                        if photo:
                            photo = photo[0]
                            if isinstance(photo, str):
                                if photo.startswith('data:image'):
                                    try:
                                        base64_part = photo.split(',')[1]
                                        image_data = base64.b64decode(base64_part)
                                        photo_data = f"data:image/jpeg;base64,{base64.b64encode(image_data).decode()}"
                                    except Exception as e:
                                        st.warning(f"Warning: Invalid base64 image from array for card {idx + 1}. Error: {str(e)}")
                                elif photo.startswith('http'):
                                    try:
                                        response = requests.head(photo, timeout=5)
                                        if response.status_code == 200:
                                            img_response = requests.get(photo, timeout=10)
                                            img_response.raise_for_status()
                                            photo_data = f"data:image/jpeg;base64,{base64.b64encode(img_response.content).decode()}"
                                        else:
                                            st.warning(f"Warning: Invalid image URL status code {response.status_code} for card {idx + 1}")
                                    except Exception as e:
                                        st.warning(f"Warning: Failed to process image URL from array for card {idx + 1}: {str(e)}")
                
                # Create card object with proper type conversion
                try:
                    card = Card(
                        player_name=str(safe_get(row, 'player_name', '')),
                        year=str(safe_get(row, 'year', '')),
                        card_set=str(safe_get(row, 'card_set', '')),
                        card_number=str(safe_get(row, 'card_number', '')),
                        variation=str(safe_get(row, 'variation', '')),
                        condition=CardCondition.from_string(str(safe_get(row, 'condition', 'Raw'))),
                        purchase_price=float(safe_get(row, 'purchase_price', 0)),
                        purchase_date=datetime.fromisoformat(safe_get(row, 'purchase_date', datetime.now().isoformat())),
                        current_value=float(safe_get(row, 'current_value', 0)),
                        last_updated=datetime.fromisoformat(safe_get(row, 'last_updated', datetime.now().isoformat())),
                        notes=str(safe_get(row, 'notes', '')),
                        photo=photo_data,
                        roi=float(safe_get(row, 'roi', 0)),
                        tags=[str(tag) for tag in safe_get(row, 'tags', [])]
                    )
                    cards.append(card)
                except Exception as card_error:
                    st.error(f"Error creating card object for card {idx + 1}: {str(card_error)}")
                    continue
                    
            except Exception as card_error:
                st.error(f"Error processing card {idx + 1}: {str(card_error)}")
                continue
        
        if not cards:
            st.error("No valid cards to save")
            return False
        
        with st.spinner("Saving collection to database..."):
            try:
                success = DatabaseService.save_user_collection(st.session_state.uid, cards)
                if success:
                    st.success(f"Successfully saved {len(cards)} cards to your collection!")
                    return True
                else:
                    st.error("Failed to save collection to database. Please try again.")
                    return False
            except Exception as save_error:
                st.error(f"Error saving collection: {str(save_error)}")
                import traceback
                st.write("Debug: Error traceback:", traceback.format_exc())
                return False
                
    except Exception as e:
        st.error(f"Error in save_collection_to_firebase: {str(e)}")
        import traceback
        st.write("Debug: Error traceback:", traceback.format_exc())
        return False

def display_collection_grid(filtered_collection, is_shared=False):
    """Display collection in a responsive grid layout"""
    if not has_cards(filtered_collection):
        st.info("No cards to display")
        return
    
    # Create a grid of cards
    cols = st.columns(3)
    for idx, card in enumerate(filtered_collection):
        col = cols[idx % 3]
        with col:
            with st.container():
                # Safely get photo from card
                photo = None
                if isinstance(card, dict):
                    photo = card.get('photo', '')
                elif hasattr(card, 'photo'):
                    photo = card.photo
                
                if photo:
                    try:
                        # Handle base64 images
                        if isinstance(photo, str) and photo.startswith('data:image'):
                            try:
                                # Validate base64 string
                                base64_part = photo.split(',')[1]
                                base64.b64decode(base64_part)
                                st.image(photo, use_container_width=True)
                            except Exception as e:
                                st.warning(f"Invalid base64 image for card {idx + 1}")
                                st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Image", use_container_width=True)
                        # Handle URL images
                        elif isinstance(photo, str) and (photo.startswith('http://') or photo.startswith('https://')):
                            try:
                                response = requests.head(photo, timeout=5)
                                if response.status_code == 200:
                                    st.image(photo, use_container_width=True)
                                else:
                                    st.warning(f"Invalid image URL for card {idx + 1}")
                                    st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Image", use_container_width=True)
                            except Exception as e:
                                st.warning(f"Failed to load image URL for card {idx + 1}")
                                st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Image", use_container_width=True)
                        # Handle file upload objects
                        elif hasattr(photo, 'getvalue'):
                            try:
                                st.image(photo, use_container_width=True)
                            except Exception as e:
                                st.warning(f"Failed to load uploaded image for card {idx + 1}")
                                st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Image", use_container_width=True)
                        # Handle array/list of photos
                        elif isinstance(photo, (list, tuple)) and photo:
                            # Take the first photo from the array
                            first_photo = photo[0]
                            if isinstance(first_photo, str):
                                if first_photo.startswith('data:image'):
                                    try:
                                        base64_part = first_photo.split(',')[1]
                                        base64.b64decode(base64_part)
                                        st.image(first_photo, use_container_width=True)
                                    except Exception as e:
                                        st.warning(f"Invalid base64 image in array for card {idx + 1}")
                                        st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Image", use_container_width=True)
                                elif first_photo.startswith('http://') or first_photo.startswith('https://'):
                                    try:
                                        response = requests.head(first_photo, timeout=5)
                                        if response.status_code == 200:
                                            st.image(first_photo, use_container_width=True)
                                        else:
                                            st.warning(f"Invalid image URL in array for card {idx + 1}")
                                            st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Image", use_container_width=True)
                                    except Exception as e:
                                        st.warning(f"Failed to load image URL in array for card {idx + 1}")
                                        st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Image", use_container_width=True)
                            elif hasattr(first_photo, 'getvalue'):
                                try:
                                    st.image(first_photo, use_container_width=True)
                                except Exception as e:
                                    st.warning(f"Failed to load uploaded image in array for card {idx + 1}")
                                    st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Image", use_container_width=True)
                            else:
                                st.warning(f"Invalid image format in array for card {idx + 1}")
                                st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Image", use_container_width=True)
                        else:
                            st.warning(f"Invalid image format for card {idx + 1}")
                            st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Image", use_container_width=True)
                    except Exception as e:
                        st.warning(f"Failed to load image for card {idx + 1}")
                        st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Image", use_container_width=True)
                else:
                    st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=No+Image", use_container_width=True)
                
                # Safely get card details
                player_name = card.get('player_name', '') if isinstance(card, dict) else getattr(card, 'player_name', '')
                year = card.get('year', '') if isinstance(card, dict) else getattr(card, 'year', '')
                card_set = card.get('card_set', '') if isinstance(card, dict) else getattr(card, 'card_set', '')
                card_number = card.get('card_number', '') if isinstance(card, dict) else getattr(card, 'card_number', '')
                condition = card.get('condition', '') if isinstance(card, dict) else getattr(card, 'condition', '')
                current_value = card.get('current_value', 0) if isinstance(card, dict) else getattr(card, 'current_value', 0)
                roi = card.get('roi', 0) if isinstance(card, dict) else getattr(card, 'roi', 0)
                tags = card.get('tags', []) if isinstance(card, dict) else getattr(card, 'tags', [])
                
                # Display card details
                st.markdown(f"""
                <div style="background: rgba(0, 0, 0, 0.7); padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
                    <h4 style="color: white; margin-bottom: 0.5rem;">{player_name} {year}</h4>
                    <p style="margin: 0.25rem 0;">{card_set} #{card_number}</p>
                    <p style="margin: 0.25rem 0;">Condition: {condition}</p>
                    <p style="margin: 0.25rem 0; font-weight: bold;">Value: ${current_value:,.2f}</p>
                    <p style="margin: 0.25rem 0;">ROI: {roi:+.1f}%</p>
                    <p style="margin: 0.25rem 0;">Tags: {', '.join(tags) if tags else 'None'}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Add edit button if not shared collection
                if not is_shared:
                    if st.button("Edit", key=f"edit_{idx}"):
                        st.session_state.editing_card = idx
                        st.session_state.editing_data = card
                        st.session_state.current_tab = "View Collection"  # Set the current tab
                        st.rerun()  # Force a rerun to show the edit form

def display_collection_table(filtered_collection):
    """Display collection in a table format"""
    if not has_cards(filtered_collection):
        st.info("No cards to display")
        return
    
    # Convert collection to DataFrame for display
    df = pd.DataFrame([
        card.to_dict() if hasattr(card, 'to_dict') else card 
        for card in filtered_collection
    ])
    
    # Display table
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "photo": st.column_config.ImageColumn("Photo"),
            "current_value": st.column_config.NumberColumn("Current Value", format="$%.2f"),
            "purchase_price": st.column_config.NumberColumn("Purchase Price", format="$%.2f"),
            "roi": st.column_config.NumberColumn("ROI", format="%.1f%%"),
            "tags": st.column_config.ListColumn("Tags")
        }
    )

def has_cards(collection):
    """Helper function to check if collection has any cards."""
    if collection is None:
        return False
    if isinstance(collection, pd.DataFrame):
        return not collection.empty
    if isinstance(collection, list):
        return len(collection) > 0
    return False

def safe_get(card, key, default=None):
    """Safely get a value from a card, whether it's a Card object or dictionary."""
    if hasattr(card, 'to_dict'):
        card_dict = card.to_dict()
        return card_dict.get(key, default)
    elif isinstance(card, dict):
        return card.get(key, default)
    return default

def main():
    """Main function for the collection manager page"""
    init_session_state()
    
    # Check if user is logged in
    if not st.session_state.user:
        st.error("Please log in to access the collection manager")
        return
    
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
                # Get all tags from the card and check if any match the filter
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
                # Convert collection to DataFrame for export
                df = pd.DataFrame([
                    card.to_dict() if hasattr(card, 'to_dict') else card 
                    for card in st.session_state.collection
                ])
                excel_data = convert_df_to_excel(df)
                st.download_button(
                    label="Download Collection",
                    data=excel_data,
                    file_name=f"card_collection_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        
        with col2:
            st.subheader("Import Collection")
            uploaded_file = st.file_uploader(
                "Upload Collection (CSV or Excel)",
                type=['csv', 'xlsx']
            )
            
            if uploaded_file:
                try:
                    # Import collection
                    if uploaded_file.name.endswith('.csv'):
                        imported_df = pd.read_csv(uploaded_file)
                    else:
                        imported_df = pd.read_excel(uploaded_file)
                    
                    # Validate and process import
                    required_cols = [
                        'player_name', 'year', 'card_set', 'card_number',
                        'variation', 'condition', 'purchase_price', 'purchase_date'
                    ]
                    
                    missing_cols = [
                        col for col in required_cols
                        if col not in imported_df.columns
                    ]
                    
                    if missing_cols:
                        st.error(f"Missing required columns: {', '.join(missing_cols)}")
                    else:
                        # Add missing optional columns
                        if 'current_value' not in imported_df.columns:
                            imported_df['current_value'] = imported_df['purchase_price']
                        if 'last_updated' not in imported_df.columns:
                            imported_df['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        if 'notes' not in imported_df.columns:
                            imported_df['notes'] = ''
                        if 'photo' not in imported_df.columns:
                            imported_df['photo'] = None
                        if 'roi' not in imported_df.columns:
                            imported_df['roi'] = 0.0
                        if 'tags' not in imported_df.columns:
                            imported_df['tags'] = ''
                        
                        # Convert DataFrame to list of dictionaries
                        imported_collection = imported_df.to_dict('records')
                        
                        # Update collection
                        st.session_state.collection = imported_collection
                        st.success(f"Successfully imported {len(imported_collection)} cards!")
                        st.balloons()
                
                except Exception as e:
                    st.error(f"Error importing file: {str(e)}")

if __name__ == "__main__":
    main()
