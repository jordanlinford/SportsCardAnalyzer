import streamlit as st
import pandas as pd
import io
from datetime import datetime, date
from PIL import Image
import base64
import requests
import traceback
from modules.core.market_analysis import MarketAnalyzer
from modules.core.collection_manager import CollectionManager
from scrapers.ebay_interface import EbayInterface
from modules.firebase.config import db
from modules.firebase.user_management import UserManager
from modules.database import Card, UserPreferences, DatabaseService
from modules.database.models import CardCondition
from modules.ui.collection_display import CardDisplay
from modules.ui.theme.theme_manager import ThemeManager
from io import BytesIO
import json
from modules.core.card_value_analyzer import CardValueAnalyzer # type: ignore
from modules.core.firebase_manager import FirebaseManager  # Updated import path
from modules.ui.components import CardDisplay
from modules.ui.theme.theme_manager import ThemeManager
import os

# Configure the page
st.set_page_config(
    page_title="Collection Manager - Sports Card Analyzer Pro",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="collapsed"  # Collapse sidebar by default on mobile
)

# Apply theme styles
ThemeManager.apply_theme_styles()

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
                    # Convert uploaded photo to base64
                    photo_bytes = photo.read()
                    photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
                    new_card['photo'] = f"data:image/{photo.type.split('/')[-1]};base64,{photo_base64}"
                
                # Initialize collection if not exists
                if 'collection' not in st.session_state:
                    st.session_state.collection = []
                
                # Convert DataFrame to list if needed
                if isinstance(st.session_state.collection, pd.DataFrame):
                    st.session_state.collection = st.session_state.collection.to_dict('records')
                
                # Add new card
                st.session_state.collection = st.session_state.collection + [new_card]
                
                # Save to Firebase
                if save_collection_to_firebase(st.session_state.collection):
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
                if delete_card(card_index):
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
    """Load the user's collection from Firebase"""
    try:
        if not st.session_state.user or not st.session_state.uid:
            st.warning("User not logged in")
            return []
        
        # Ensure Firebase is initialized
        if not FirebaseManager.initialize():
            st.error("Failed to initialize Firebase")
            return []
        
        # Get user document using FirebaseManager
        try:
            users_collection = FirebaseManager.get_collection('users')
            if not users_collection:
                st.error("Failed to access Firestore collection")
                return []
                
            user_doc = users_collection.document(st.session_state.uid).get()
            if not user_doc.exists:
                st.warning("No user data found")
                return []
            
            user_data = user_doc.to_dict()
            if 'collection' not in user_data:
                st.info("No collection found for user")
                return []
            
            # Convert collection to list
            collection = user_data['collection']
            
            # Ensure all required fields exist and process image data
            for card in collection:
                if 'photo' not in card:
                    card['photo'] = "https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image"
                if 'last_updated' not in card:
                    card['last_updated'] = datetime.now().isoformat()
            
            return collection
            
        except Exception as e:
            st.error(f"Error accessing Firestore: {str(e)}")
            return []
            
    except Exception as e:
        st.error(f"Error loading collection: {str(e)}")
        return []

def save_collection_to_firebase(collection):
    """Save the collection to Firebase"""
    try:
        if not st.session_state.user or not st.session_state.uid:
            st.error("User not logged in")
            return False
        
        # Convert DataFrame to list if needed
        if isinstance(collection, pd.DataFrame):
            collection = collection.to_dict('records')
        
        # Process each card's photo data
        processed_collection = []
        for card in collection:
            processed_card = card.copy()
            
            # Handle photo data
            if 'photo' in processed_card:
                photo = processed_card['photo']
                if photo and isinstance(photo, str):
                    if photo.startswith('http'):
                        try:
                            # Validate URL image
                            response = requests.head(photo, timeout=5)
                            if response.status_code != 200:
                                st.warning(f"Invalid image URL for card {processed_card.get('player_name', 'Unknown')}. Using placeholder.")
                                processed_card['photo'] = "https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image"
                        except:
                            st.warning(f"Failed to validate image URL for card {processed_card.get('player_name', 'Unknown')}. Using placeholder.")
                            processed_card['photo'] = "https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image"
                    elif photo.startswith('data:image'):
                        try:
                            # Validate base64 image
                            base64_part = photo.split(',')[1]
                            base64.b64decode(base64_part)
                            # Check if the base64 string is too large (Firestore has a 1MB limit)
                            if len(base64_part) > 900000:  # Approx 900KB
                                st.warning(f"Image too large for card {processed_card.get('player_name', 'Unknown')}. Using placeholder.")
                                processed_card['photo'] = "https://placehold.co/300x400/e6e6e6/666666.png?text=Image+Too+Large"
                        except:
                            st.warning(f"Invalid base64 image for card {processed_card.get('player_name', 'Unknown')}. Using placeholder.")
                            processed_card['photo'] = "https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Image"
                    else:
                        # Invalid image format
                        st.warning(f"Invalid image format for card {processed_card.get('player_name', 'Unknown')}. Using placeholder.")
                        processed_card['photo'] = "https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image"
                else:
                    # No valid photo data
                    processed_card['photo'] = "https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image"
            
            processed_collection.append(processed_card)
        
        # Save to Firebase
        db.collection('users').document(st.session_state.uid).update({
            'collection': processed_collection,
            'last_updated': datetime.now().isoformat()
        })
        
        return True
        
    except Exception as e:
        st.error(f"Error saving collection: {str(e)}")
        st.write("Debug: Error traceback:", traceback.format_exc())
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
    # Create sample data
    sample_data = {
        'Player Name': ['Michael Jordan', 'LeBron James'],
        'Year': ['1986', '2003'],
        'Card Set': ['Fleer', 'Topps Chrome'],
        'Variation': ['Base', 'Refractor'],
        'Condition': ['PSA 9', 'PSA 10'],
        'Date Purchased': ['2023-01-15', ''],  # Optional
        'Purchase Amount': [150.00, ''],  # Optional
        'Notes': ['Rookie Card', '']  # Optional
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
            "- Player Name: Full name of the player",
            "- Year: Year the card was produced (e.g., 1986)",
            "- Card Set: Name of the set (e.g., Topps, Panini Prizm)",
            "- Variation: Type of card (e.g., Base, Refractor, Prizm)",
            "- Condition: Card condition (e.g., PSA 9, Raw)",
            "",
            "Optional Fields:",
            "- Date Purchased: When you bought the card (YYYY-MM-DD)",
            "- Purchase Amount: How much you paid for the card",
            "- Notes: Any additional information about the card",
            "",
            "Notes:",
            "- Leave optional fields blank if not applicable",
            "- Dates will default to today's date if left blank",
            "- Purchase amounts will default to 0 if left blank"
        ]
        
        for row_num, instruction in enumerate(instructions, start=len(df) + 3):
            worksheet.write(row_num, 0, instruction)
    
    return output.getvalue()

def delete_card(card_index):
    """Delete a card from the collection"""
    try:
        if not st.session_state.collection:
            st.error("No cards in collection")
            return False
        
        # Remove the card from the collection
        st.session_state.collection.pop(card_index)
        
        # Save the updated collection to Firebase
        if save_collection_to_firebase(st.session_state.collection):
            st.success("Card deleted successfully!")
            return True
        else:
            st.error("Failed to save changes to database")
            return False
            
    except Exception as e:
        st.error(f"Error deleting card: {str(e)}")
        return False

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
                        
                        # Save to Firebase
                        if save_collection_to_firebase(imported_collection):
                            st.success(f"Successfully imported {len(imported_collection)} cards!")
                            st.balloons()
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
