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
                    card.get('player_name', ''),
                    card.get('year', ''),
                    card.get('card_set', ''),
                    card.get('card_number', ''),
                    card.get('variation', ''),
                    card.get('condition', '')
                )
                
                # Update card value
                card['current_value'] = current_value
                
                # Calculate ROI
                purchase_price = float(card.get('purchase_price', 0))
                roi = ((current_value - purchase_price) / purchase_price * 100) if purchase_price > 0 else 0
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
    with st.form("add_card_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            player_name = st.text_input("Player Name", key="player_name")
            year = st.text_input("Year", key="year")
            card_set = st.text_input("Card Set", key="card_set")
            card_number = st.text_input("Card Number", key="card_number")
            variation = st.text_input("Variation", key="variation")
        
        with col2:
            condition = st.selectbox(
                "Condition",
                ["Raw", "PSA 1", "PSA 2", "PSA 3", "PSA 4", "PSA 5", "PSA 6", "PSA 7", "PSA 8", "PSA 9", "PSA 10", "Graded Other"],
                key="condition"
            )
            purchase_price = st.number_input("Purchase Price", min_value=0.0, step=0.01, key="purchase_price")
            purchase_date = st.date_input("Purchase Date", key="purchase_date")
            notes = st.text_area("Notes", key="notes")
            tags = st.text_input("Tags (comma-separated)", key="tags")
        
        photo = st.file_uploader("Upload Photo", type=["jpg", "jpeg", "png"], key="photo")
        
        submitted = st.form_submit_button("Add Card")
        
        if submitted:
            # Validate required fields
            if not player_name or not year or not card_set:
                st.error("Please fill in all required fields (Player Name, Year, Card Set)")
                return False, None
            
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
                return False, None
            
            # Create card dictionary
            card_data = {
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
                'photo': '',
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
                    card_data['photo'] = f"data:image/jpeg;base64,{encoded_image}"
                except Exception as e:
                    st.warning(f"Warning: Could not process uploaded image. Error: {str(e)}")
            
            return True, card_data
        
        return False, None

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
                
            player_name = st.text_input("Player Name", value=card_dict.get('player_name', ''), key="edit_player_name")
            year = st.text_input("Year", value=card_dict.get('year', ''), key="edit_year")
            card_set = st.text_input("Card Set", value=card_dict.get('card_set', ''), key="edit_card_set")
            card_number = st.text_input("Card Number", value=card_dict.get('card_number', ''), key="edit_card_number")
            variation = st.text_input("Variation", value=card_dict.get('variation', ''), key="edit_variation")
        
        with col2:
            # Get the current condition
            current_condition = card_dict.get('condition', 'Raw')
            
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
                value=float(card_dict.get('purchase_price', 0)),
                key="edit_purchase_price"
            )
            purchase_date = st.date_input(
                "Purchase Date",
                value=_parse_date(card_dict.get('purchase_date')),
                key="edit_purchase_date"
            )
            notes = st.text_area("Notes", value=card_dict.get('notes', ''), key="edit_notes")
            tags = st.text_input(
                "Tags (comma-separated)",
                value=', '.join(card_dict.get('tags', [])),
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
        # Debug: Print input type and data
        st.write("Debug: Input type:", type(collection_df))
        st.write("Debug: Input data:", collection_df.head())
        
        # Convert DataFrame to list of dictionaries if needed
        if isinstance(collection_df, pd.DataFrame):
            cards_data = collection_df.to_dict('records')
        else:
            cards_data = collection_df
            
        cards = []
        
        for idx, row in enumerate(cards_data):
            try:
                # Handle dates
                purchase_date = row.get('purchase_date', '')
                if not purchase_date or pd.isna(purchase_date):
                    purchase_date = datetime.now().isoformat()
                elif isinstance(purchase_date, datetime):
                    purchase_date = purchase_date.isoformat()
                elif isinstance(purchase_date, str):
                    try:
                        datetime.fromisoformat(purchase_date)
                    except ValueError:
                        purchase_date = datetime.now().isoformat()
                
                last_updated = row.get('last_updated', '')
                if not last_updated or pd.isna(last_updated):
                    last_updated = datetime.now().isoformat()
                elif isinstance(last_updated, datetime):
                    last_updated = last_updated.isoformat()
                elif isinstance(last_updated, str):
                    try:
                        datetime.fromisoformat(last_updated)
                    except ValueError:
                        last_updated = datetime.now().isoformat()
                
                # Handle numeric values with better error handling
                try:
                    purchase_price = float(row.get('purchase_price', 0.0))
                    if pd.isna(purchase_price):
                        purchase_price = 0.0
                except (ValueError, TypeError) as e:
                    st.warning(f"Warning: Invalid purchase price for card {idx + 1}. Setting to 0.0. Error: {str(e)}")
                    purchase_price = 0.0
                    
                try:
                    current_value = float(row.get('current_value', purchase_price))
                    if pd.isna(current_value):
                        current_value = purchase_price
                except (ValueError, TypeError) as e:
                    st.warning(f"Warning: Invalid current value for card {idx + 1}. Using purchase price. Error: {str(e)}")
                    current_value = purchase_price
                    
                try:
                    roi = float(row.get('roi', 0.0))
                    if pd.isna(roi):
                        roi = 0.0
                except (ValueError, TypeError) as e:
                    st.warning(f"Warning: Invalid ROI for card {idx + 1}. Setting to 0.0. Error: {str(e)}")
                    roi = 0.0
                
                # Handle photo data
                photo = row.get('photo')
                photo_data = "https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image"
                
                if photo is not None and not pd.isna(photo):
                    if isinstance(photo, str):
                        if photo.startswith('data:image'):
                            # Already in base64 format
                            photo_data = photo
                        elif photo.startswith('http'):
                            # Valid URL, keep as is
                            photo_data = photo
                        else:
                            try:
                                # Try to load the image URL
                                response = requests.get(photo, timeout=10)
                                response.raise_for_status()
                                content_type = response.headers.get('content-type', '').lower()
                                if 'image' in content_type:
                                    # Convert to base64
                                    photo_data = f"data:image/jpeg;base64,{base64.b64encode(response.content).decode()}"
                                    st.write(f"Debug: Successfully converted image URL to base64 for card {idx + 1}")
                            except Exception as e:
                                st.warning(f"Failed to process image URL: {str(e)}")
                    else:
                        try:
                            # Handle file upload object
                            photo_bytes = photo.getvalue()
                            photo_data = f"data:image/jpeg;base64,{base64.b64encode(photo_bytes).decode()}"
                            st.write(f"Debug: Successfully converted uploaded image to base64 for card {idx + 1}")
                        except Exception as photo_error:
                            st.warning(f"Warning: Could not process photo for card {idx + 1}. Error: {str(photo_error)}")
                
                # Handle tags
                tags = row.get('tags', '')
                if pd.isna(tags):
                    tags = []
                elif isinstance(tags, str):
                    tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
                elif not isinstance(tags, list):
                    tags = []
                
                # Create card object with proper type conversion
                try:
                    card = Card(
                        player_name=str(row.get('player_name', '')),
                        year=str(row.get('year', '')),
                        card_set=str(row.get('card_set', '')),
                        card_number=str(row.get('card_number', '')),
                        variation=str(row.get('variation', '')),
                        condition=CardCondition.from_string(str(row.get('condition', 'Raw'))),
                        purchase_price=purchase_price,
                        purchase_date=datetime.fromisoformat(purchase_date),
                        current_value=current_value,
                        last_updated=datetime.fromisoformat(last_updated),
                        notes=str(row.get('notes', '')),
                        photo=photo_data,
                        roi=roi,
                        tags=tags
                    )
                    cards.append(card)
                    st.write(f"Debug: Successfully processed card {idx + 1}")
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
                        st.image(photo, use_container_width=True)
                    except Exception as e:
                        st.error(f"Failed to load image: {str(e)}")
                
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
        submitted, card_data = display_add_card_form()
        
        if submitted and card_data:
            # Add new card to collection
            if isinstance(st.session_state.collection, list):
                st.session_state.collection.append(card_data)
            else:
                st.session_state.collection = [card_data]
            
            # Save to Firebase
            if save_collection_to_firebase(st.session_state.collection):
                st.success("Card added successfully!")
                st.balloons()
            else:
                st.error("Failed to save card to collection.")
    
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
                    if tag_filter.lower() in str(card.get('tags', '')).lower()
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
                    if player_filter.lower() in str(card.get('player_name', '')).lower()
                ]
            if year_filter:
                filtered_collection = [
                    card for card in filtered_collection
                    if year_filter.lower() in str(card.get('year', '')).lower()
                ]
            if set_filter:
                filtered_collection = [
                    card for card in filtered_collection
                    if set_filter.lower() in str(card.get('card_set', '')).lower()
                ]
            if tag_filter:
                filtered_collection = [
                    card for card in filtered_collection
                    if tag_filter.lower() in str(card.get('tags', '')).lower()
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
