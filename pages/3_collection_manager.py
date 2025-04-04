import streamlit as st
import pandas as pd
import io
from datetime import datetime
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
                ["Mint", "Near Mint", "Excellent", "Very Good", "Good", "Poor"],
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
    # Convert collection data to dictionaries if they are Card objects
    if isinstance(collection_data, list):
        collection_data = [card.to_dict() if hasattr(card, 'to_dict') else card for card in collection_data]
    
    # Convert collection data to base64 for URL-safe sharing
    collection_json = json.dumps(collection_data)
    encoded_data = base64.urlsafe_b64encode(collection_json.encode()).decode()
    return f"?share={encoded_data}"

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
    
    if not filtered_collection:
        st.info("No cards in collection")
        return
    
    # Calculate summary metrics
    total_value = sum(card.current_value for card in filtered_collection)
    total_cost = sum(card.purchase_price for card in filtered_collection)
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

def edit_card_form(card_index, card_data):
    """Display form for editing a card"""
    with st.form("edit_card_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            player_name = st.text_input("Player Name", value=card_data.get('player_name', ''), key="edit_player_name")
            year = st.text_input("Year", value=card_data.get('year', ''), key="edit_year")
            card_set = st.text_input("Card Set", value=card_data.get('card_set', ''), key="edit_card_set")
            card_number = st.text_input("Card Number", value=card_data.get('card_number', ''), key="edit_card_number")
            variation = st.text_input("Variation", value=card_data.get('variation', ''), key="edit_variation")
        
        with col2:
            condition = st.selectbox(
                "Condition",
                ["Mint", "Near Mint", "Excellent", "Very Good", "Good", "Poor"],
                index=["Mint", "Near Mint", "Excellent", "Very Good", "Good", "Poor"].index(card_data.get('condition', 'Mint')),
                key="edit_condition"
            )
            purchase_price = st.number_input(
                "Purchase Price",
                min_value=0.0,
                step=0.01,
                value=float(card_data.get('purchase_price', 0)),
                key="edit_purchase_price"
            )
            purchase_date = st.date_input(
                "Purchase Date",
                value=datetime.strptime(card_data.get('purchase_date', ''), '%Y-%m-%d').date() if card_data.get('purchase_date') else datetime.now().date(),
                key="edit_purchase_date"
            )
            notes = st.text_area("Notes", value=card_data.get('notes', ''), key="edit_notes")
            tags = st.text_input(
                "Tags (comma-separated)",
                value=', '.join(card_data.get('tags', [])),
                key="edit_tags"
            )
        
        photo = st.file_uploader("Upload New Photo", type=["jpg", "jpeg", "png"], key="edit_photo")
        
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
            st.session_state.collection[card_index].update({
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
            })
            
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
                    st.session_state.collection[card_index]['photo'] = f"data:image/jpeg;base64,{encoded_image}"
                except Exception as e:
                    st.warning(f"Warning: Could not process uploaded image. Error: {str(e)}")
            
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

def save_collection_to_firebase(collection):
    """Save collection to Firebase"""
    try:
        if not st.session_state.uid:
            st.error("User not logged in")
            return False
        
        # Process collection data
        processed_cards = []
        for idx, card in enumerate(collection):
            try:
                # Convert numeric fields
                purchase_price = float(card.get('purchase_price', 0))
                current_value = float(card.get('current_value', purchase_price))
                roi = ((current_value - purchase_price) / purchase_price * 100) if purchase_price > 0 else 0
                
                # Convert date fields
                purchase_date = card.get('purchase_date', '')
                if purchase_date:
                    try:
                        purchase_date = pd.to_datetime(purchase_date).strftime('%Y-%m-%d')
                    except:
                        purchase_date = ''
                
                last_updated = card.get('last_updated', '')
                if not last_updated:
                    last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Handle photo data
                photo_data = card.get('photo', '')
                if photo_data and isinstance(photo_data, str) and photo_data.startswith('data:image'):
                    # Photo is already in base64 format
                    pass
                elif photo_data and isinstance(photo_data, bytes):
                    # Convert bytes to base64
                    photo_data = f"data:image/jpeg;base64,{base64.b64encode(photo_data).decode()}"
                else:
                    photo_data = ''
                
                # Handle tags
                tags = card.get('tags', '')
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except:
                        tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
                elif not isinstance(tags, list):
                    tags = []
                
                # Create processed card dictionary
                processed_card = {
                    'player_name': str(card.get('player_name', '')),
                    'year': str(card.get('year', '')),
                    'card_set': str(card.get('card_set', '')),
                    'card_number': str(card.get('card_number', '')),
                    'variation': str(card.get('variation', '')),
                    'condition': str(card.get('condition', '')),
                    'purchase_price': purchase_price,
                    'purchase_date': purchase_date,
                    'current_value': current_value,
                    'last_updated': last_updated,
                    'notes': str(card.get('notes', '')),
                    'photo': photo_data,
                    'roi': roi,
                    'tags': tags
                }
                
                # Debug: Print photo data size
                if photo_data:
                    photo_size = len(photo_data) / 1024  # Convert to KB
                    if photo_size > 500:  # Warning if approaching 1MB limit
                        st.warning(f"Warning: Photo for card {idx + 1} is {photo_size:.1f}KB. Consider reducing size further.")
                
                processed_cards.append(processed_card)
            except Exception as card_error:
                st.warning(f"Warning: Could not process card {idx + 1}. Error: {str(card_error)}")
                continue
        
        if not processed_cards:
            st.error("No valid cards to save")
            return False
        
        with st.spinner("Saving collection to database..."):
            success = DatabaseService.save_user_collection(st.session_state.uid, processed_cards)
            if success:
                st.success(f"Successfully saved {len(processed_cards)} cards to your collection!")
                return True
            else:
                st.error("Failed to save collection to database. Please try again.")
        
    except Exception as e:
        st.error(f"Error saving collection: {str(e)}")
        import traceback
        st.write("Debug: Error traceback:", traceback.format_exc())
        return False

def display_collection_grid(filtered_collection, is_shared=False):
    """Display collection in a responsive grid layout"""
    if not filtered_collection:
        st.info("No cards to display")
        return
    
    # Create a grid of cards
    cols = st.columns(3)
    for idx, card in enumerate(filtered_collection):
        col = cols[idx % 3]
        with col:
            with st.container():
                # Display card image if available
                if card.photo:
                    try:
                        st.image(card.photo, use_column_width=True)
                    except Exception as e:
                        st.error(f"Failed to load image: {str(e)}")
                
                # Display card details
                st.markdown(f"""
                <div style="background: rgba(0, 0, 0, 0.7); padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
                    <h4 style="color: white; margin-bottom: 0.5rem;">{card.player_name} {card.year}</h4>
                    <p style="margin: 0.25rem 0;">{card.card_set} #{card.card_number}</p>
                    <p style="margin: 0.25rem 0;">Condition: {card.condition.value}</p>
                    <p style="margin: 0.25rem 0; font-weight: bold;">Value: ${card.current_value:,.2f}</p>
                    <p style="margin: 0.25rem 0;">ROI: {card.roi:+.1f}%</p>
                    <p style="margin: 0.25rem 0;">Tags: {', '.join(card.tags)}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Add edit button if not shared collection
                if not is_shared:
                    if st.button("Edit", key=f"edit_{idx}"):
                        st.session_state.editing_card = idx
                        st.session_state.editing_data = card
                        st.rerun()

def display_collection_table(filtered_collection):
    """Display collection in a table format"""
    if not filtered_collection:
        st.info("No cards to display")
        return
    
    # Convert collection to DataFrame for display
    df = pd.DataFrame([card.to_dict() for card in filtered_collection])
    
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

def main():
    """Main function for the collection manager page"""
    # Initialize session state
    init_session_state()
    
    # Check if user is logged in
    if not st.session_state.user:
        st.error("Please log in to access the collection manager")
        return
    
    # Load collection from Firebase if needed
    if not st.session_state.collection and st.session_state.uid:
        st.session_state.collection = load_collection_from_firebase()
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Add Cards", "View Collection", "Share Collection", "Import/Export"])
    
    # Tab 1: Add Cards
    with tab1:
        st.subheader("Add New Card")
        submitted, card_data = display_add_card_form()
        
        if submitted and card_data:
            # Add new card to collection
            st.session_state.collection.append(card_data)
            
            # Save to Firebase
            if save_collection_to_firebase(st.session_state.collection):
                st.success("Card added successfully!")
                st.balloons()
            else:
                st.error("Failed to save card to collection.")
    
    # Tab 2: View Collection
    with tab2:
        if st.session_state.collection:
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
            
            # Show edit form if a card is being edited
            if st.session_state.editing_card is not None and st.session_state.editing_data is not None:
                edit_card_form(st.session_state.editing_card, st.session_state.editing_data)
                if st.button("Cancel Edit", use_container_width=True):
                    st.session_state.editing_card = None
                    st.session_state.editing_data = None
                    st.rerun()
            else:
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
        if st.session_state.collection:
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
            
            if filtered_collection:
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
                st.warning("No cards match the selected filters.")
        else:
            st.info("Add some cards to your collection to generate a share link.")
    
    # Tab 4: Import/Export
    with tab4:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Export Collection")
            if st.session_state.collection:
                # Convert collection to DataFrame for export
                df = pd.DataFrame(st.session_state.collection)
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
