"""Collection utilities shared across multiple pages."""
import streamlit as st
import re
from datetime import datetime
from typing import Dict, Any, Optional
from modules.database.service import DatabaseService

def save_card_to_collection(card_dict: Dict[str, Any]) -> bool:
    """Save a card to the user's collection in Firebase"""
    try:
        if not st.session_state.uid:
            st.error("Please log in to add cards to your collection")
            return False
            
        # Get current collection
        collection = DatabaseService.get_user_collection(st.session_state.uid) or []
        
        # Add new card
        collection.append(card_dict)
        
        # Save updated collection
        success = DatabaseService.save_user_collection(st.session_state.uid, collection)
        
        if not success:
            st.error("Failed to save card to collection. Please try again.")
            return False
            
        # Force refresh the collection in session state
        st.session_state.collection = DatabaseService.get_user_collection(st.session_state.uid)
        
        return True
        
    except Exception as e:
        st.error(f"Error saving card to collection: {str(e)}")
        import traceback
        st.write("Debug: Error traceback:", traceback.format_exc())
        return False

def add_to_collection(card_data: Dict[str, Any], market_data: Optional[Dict[str, Any]] = None) -> bool:
    """Add a card from market analysis to collection"""
    try:
        # Use player name from the original search form input
        player_name = st.session_state.search_params.get('player_name', '')
        
        # Extract card details from title
        title = card_data['title']
        
        # Extract year (looking for 4-digit number)
        year_match = re.search(r'\b\d{4}\b', title)
        year = year_match.group(0) if year_match else ""
        
        # Extract card set (text between year and card number, if present)
        set_match = re.search(rf'{year}\s+(.*?)(?:\s+#|\s+Card|\s+RC|\s+Rookie|\s+PSA|\s+SGC|\s+BGS|$)', title)
        card_set = set_match.group(1) if set_match else ""
        
        # Extract card number
        number_match = re.search(r'#(\d+)', title)
        card_number = number_match.group(1) if number_match else ""
        
        # Extract variation (look for common parallel terms)
        variation_terms = ['Parallel', 'Refractor', 'Prizm', 'Holo', 'Gold', 'Silver', 'Bronze', 
                          'Red', 'Blue', 'Green', 'Yellow', 'Purple', 'Orange', 'Pink']
        variation = next((term for term in variation_terms if term.lower() in title.lower()), "")
        
        # Add to collection form
        with st.form("add_to_collection_form"):
            st.subheader("Add Card to Collection")
            
            # Create two rows of form fields
            # First row with three columns
            col1, col2, col3 = st.columns(3)
            
            with col1:
                player_name = st.text_input("Player Name", value=player_name)
                year = st.text_input("Year", value=year)
            
            with col2:
                card_set = st.text_input("Card Set", value=card_set)
                card_number = st.text_input("Card Number", value=card_number)
            
            with col3:
                variation = st.text_input("Variation", value=variation)
                condition = st.selectbox(
                    "Condition",
                    ["Raw", "PSA 10", "PSA 9", "SGC 10", "SGC 9.5", "SGC 9"],
                    index=0
                )
            
            # Second row with two columns
            col4, col5 = st.columns(2)
            
            with col4:
                purchase_price = st.number_input(
                    "Purchase Price",
                    min_value=0.0,
                    step=0.01,
                    value=float(card_data.get('price', 0))
                )
            
            with col5:
                purchase_date = st.date_input("Purchase Date", value=datetime.now().date())
            
            # Tags field spanning full width
            tags = st.text_input("Tags (comma-separated)", help="Add tags to help organize your collection")
            
            # Notes field spanning full width
            notes = st.text_area("Notes", height=100)
            
            # Submit button spanning full width
            submitted = st.form_submit_button("Add to Collection", use_container_width=True)
            
            if submitted:
                # Validate required fields
                if not player_name or not year or not card_set:
                    st.error("Please fill in all required fields (Player Name, Year, Card Set)")
                    return False
                
                # Create card dictionary
                card_dict = {
                    'player_name': player_name,
                    'year': year,
                    'card_set': card_set,
                    'card_number': card_number,
                    'variation': variation,
                    'condition': condition,
                    'purchase_price': purchase_price,
                    'purchase_date': purchase_date.strftime('%Y-%m-%d'),
                    'current_value': float(card_data.get('price', 0)),
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'notes': notes,
                    'photo': card_data.get('image_url', ''),
                    'tags': [tag.strip() for tag in tags.split(',') if tag.strip()]
                }
                
                # Add to collection
                if save_card_to_collection(card_dict):
                    st.success("Card added to collection successfully!")
                    return True
                else:
                    st.error("Failed to add card to collection")
                    return False
        
        return False
    
    except Exception as e:
        st.error(f"Error adding card to collection: {str(e)}")
        import traceback
        st.write("Debug: Error traceback:", traceback.format_exc())
        return False 