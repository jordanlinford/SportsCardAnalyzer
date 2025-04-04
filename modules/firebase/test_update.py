import streamlit as st
from datetime import datetime
import traceback
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Now import the required modules
from modules.core.models import Card, CardCondition
from modules.firebase.config import db
from modules.firebase.user_management import UserManager

def test_card_update():
    st.title("Test Card Update Functionality")
    
    # Initialize session state
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'uid' not in st.session_state:
        st.session_state.uid = None
    
    # Authentication Section
    st.header("1. Authentication")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if st.button("Sign In"):
        try:
            result = UserManager.sign_in(email, password)
            if result.get('success'):
                st.session_state.user = result.get('user')
                st.session_state.uid = result.get('uid')
                st.success("Successfully signed in!")
            else:
                st.error(f"Failed to sign in: {result.get('error', 'Unknown error')}")
        except Exception as e:
            st.error(f"Error during sign in: {str(e)}")
            st.write("Debug: Error traceback:", traceback.format_exc())
    
    # Test Section
    if st.session_state.get('uid'):
        st.header("2. Test Card Update")
        
        # First, get current collection
        st.subheader("Current Collection")
        try:
            user_doc = db.collection('users').document(st.session_state.uid).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                current_cards = [Card.from_dict(card_data) for card_data in user_data.get('collection', [])]
                
                if current_cards:
                    st.write(f"Found {len(current_cards)} cards in collection")
                    # Display first card for testing
                    test_card = current_cards[0]
                    st.write("Test Card Details:", {
                        'player_name': test_card.player_name,
                        'year': test_card.year,
                        'card_set': test_card.card_set,
                        'card_number': test_card.card_number
                    })
                else:
                    st.warning("No cards found in collection. Please add a card first.")
                    return
            else:
                st.warning("No user document found. Please add a card first.")
                return
        except Exception as e:
            st.error(f"Error loading collection: {str(e)}")
            st.write("Debug: Error traceback:", traceback.format_exc())
            return
        
        # Update Test Section
        st.subheader("Update Test")
        
        # Create updated card with modified values
        updated_card = Card(
            player_name=test_card.player_name,
            year=test_card.year,
            card_set=test_card.card_set,
            card_number=test_card.card_number,
            variation=test_card.variation,
            condition=test_card.condition,
            purchase_price=test_card.purchase_price + 1.0,  # Modify price
            purchase_date=test_card.purchase_date,
            current_value=test_card.current_value + 2.0,  # Modify current value
            last_updated=datetime.now(),
            notes=test_card.notes + " (Updated)",
            photo=test_card.photo,
            roi=test_card.roi + 1.0,  # Modify ROI
            tags=test_card.tags + ["test_update"]  # Add new tag
        )
        
        if st.button("Test Update"):
            try:
                st.write("Attempting to update card...")
                st.write("Updated Card Details:", {
                    'player_name': updated_card.player_name,
                    'year': updated_card.year,
                    'card_set': updated_card.card_set,
                    'card_number': updated_card.card_number,
                    'purchase_price': updated_card.purchase_price,
                    'current_value': updated_card.current_value,
                    'notes': updated_card.notes,
                    'roi': updated_card.roi,
                    'tags': updated_card.tags
                })
                
                # Get current collection
                user_doc = db.collection('users').document(st.session_state.uid).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    collection = user_data.get('collection', [])
                    
                    # Find and update the card
                    updated = False
                    for i, card_data in enumerate(collection):
                        if (card_data.get('player_name') == updated_card.player_name and
                            card_data.get('year') == updated_card.year and
                            card_data.get('card_set') == updated_card.card_set and
                            card_data.get('card_number') == updated_card.card_number):
                            collection[i] = updated_card.to_dict()
                            updated = True
                            break
                    
                    if updated:
                        # Save the updated collection
                        db.collection('users').document(st.session_state.uid).update({
                            'collection': collection
                        })
                        st.success("Card update successful!")
                        
                        # Verify the update
                        st.subheader("Verification")
                        updated_doc = db.collection('users').document(st.session_state.uid).get()
                        if updated_doc.exists:
                            updated_data = updated_doc.to_dict()
                            updated_cards = [Card.from_dict(card_data) for card_data in updated_data.get('collection', [])]
                            
                            if updated_cards:
                                updated_card_data = next(
                                    (c for c in updated_cards 
                                     if c.player_name == updated_card.player_name and
                                     c.year == updated_card.year and
                                     c.card_set == updated_card.card_set and
                                     c.card_number == updated_card.card_number),
                                    None
                                )
                                
                                if updated_card_data:
                                    st.write("Verified Updated Card:", {
                                        'player_name': updated_card_data.player_name,
                                        'year': updated_card_data.year,
                                        'card_set': updated_card_data.card_set,
                                        'card_number': updated_card_data.card_number,
                                        'purchase_price': updated_card_data.purchase_price,
                                        'current_value': updated_card_data.current_value,
                                        'notes': updated_card_data.notes,
                                        'roi': updated_card_data.roi,
                                        'tags': updated_card_data.tags
                                    })
                                    
                                    # Compare values
                                    st.write("Update Verification:")
                                    st.write(f"Purchase Price: {test_card.purchase_price} -> {updated_card_data.purchase_price}")
                                    st.write(f"Current Value: {test_card.current_value} -> {updated_card_data.current_value}")
                                    st.write(f"Notes: {test_card.notes} -> {updated_card_data.notes}")
                                    st.write(f"ROI: {test_card.roi} -> {updated_card_data.roi}")
                                    st.write(f"Tags: {test_card.tags} -> {updated_card_data.tags}")
                                else:
                                    st.error("Card not found in collection after update!")
                            else:
                                st.error("Failed to retrieve updated collection!")
                        else:
                            st.error("Failed to retrieve updated document!")
                    else:
                        st.error("Failed to find card to update!")
                else:
                    st.error("User document not found!")
                    
            except Exception as e:
                st.error(f"Error during update: {str(e)}")
                st.write("Debug: Error traceback:", traceback.format_exc())
        
        # Edge Cases Section
        st.subheader("Edge Cases")
        
        # Test with missing fields
        if st.button("Test Missing Fields"):
            try:
                incomplete_card = Card(
                    player_name=test_card.player_name,
                    year=test_card.year,
                    card_set=test_card.card_set,
                    card_number=test_card.card_number,
                    variation="",  # Missing variation
                    condition=CardCondition.RAW,
                    purchase_price=0.0,  # Zero price
                    purchase_date=datetime.now(),
                    current_value=0.0,  # Zero value
                    last_updated=datetime.now(),
                    notes="",  # Empty notes
                    photo="",  # Empty photo
                    roi=0.0,  # Zero ROI
                    tags=[]  # Empty tags
                )
                
                # Get current collection
                user_doc = db.collection('users').document(st.session_state.uid).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    collection = user_data.get('collection', [])
                    
                    # Find and update the card
                    updated = False
                    for i, card_data in enumerate(collection):
                        if (card_data.get('player_name') == incomplete_card.player_name and
                            card_data.get('year') == incomplete_card.year and
                            card_data.get('card_set') == incomplete_card.card_set and
                            card_data.get('card_number') == incomplete_card.card_number):
                            collection[i] = incomplete_card.to_dict()
                            updated = True
                            break
                    
                    if updated:
                        # Save the updated collection
                        db.collection('users').document(st.session_state.uid).update({
                            'collection': collection
                        })
                        st.success("Successfully updated card with missing fields!")
                    else:
                        st.error("Failed to update card with missing fields!")
                else:
                    st.error("User document not found!")
                    
            except Exception as e:
                st.error(f"Error testing missing fields: {str(e)}")
                st.write("Debug: Error traceback:", traceback.format_exc())
        
        # Test with special characters
        if st.button("Test Special Characters"):
            try:
                special_card = Card(
                    player_name=test_card.player_name,
                    year=test_card.year,
                    card_set=test_card.card_set,
                    card_number=test_card.card_number,
                    variation="Special!@#$%^&*()",  # Special characters
                    condition=CardCondition.RAW,
                    purchase_price=test_card.purchase_price,
                    purchase_date=datetime.now(),
                    current_value=test_card.current_value,
                    last_updated=datetime.now(),
                    notes="Special chars: !@#$%^&*()",  # Special characters
                    photo=test_card.photo,
                    roi=test_card.roi,
                    tags=["special!@#$%^&*()"]  # Special characters
                )
                
                # Get current collection
                user_doc = db.collection('users').document(st.session_state.uid).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    collection = user_data.get('collection', [])
                    
                    # Find and update the card
                    updated = False
                    for i, card_data in enumerate(collection):
                        if (card_data.get('player_name') == special_card.player_name and
                            card_data.get('year') == special_card.year and
                            card_data.get('card_set') == special_card.card_set and
                            card_data.get('card_number') == special_card.card_number):
                            collection[i] = special_card.to_dict()
                            updated = True
                            break
                    
                    if updated:
                        # Save the updated collection
                        db.collection('users').document(st.session_state.uid).update({
                            'collection': collection
                        })
                        st.success("Successfully updated card with special characters!")
                    else:
                        st.error("Failed to update card with special characters!")
                else:
                    st.error("User document not found!")
                    
            except Exception as e:
                st.error(f"Error testing special characters: {str(e)}")
                st.write("Debug: Error traceback:", traceback.format_exc())
        
        # Test with long text
        if st.button("Test Long Text"):
            try:
                long_card = Card(
                    player_name=test_card.player_name,
                    year=test_card.year,
                    card_set=test_card.card_set,
                    card_number=test_card.card_number,
                    variation="Very long variation name that exceeds normal length and should test the system's ability to handle extended text input without breaking or causing any issues with the database storage and retrieval process",
                    condition=CardCondition.RAW,
                    purchase_price=test_card.purchase_price,
                    purchase_date=datetime.now(),
                    current_value=test_card.current_value,
                    last_updated=datetime.now(),
                    notes="Very long notes that exceed normal length and should test the system's ability to handle extended text input without breaking or causing any issues with the database storage and retrieval process. This is a test of the maximum length handling capabilities of the system.",
                    photo=test_card.photo,
                    roi=test_card.roi,
                    tags=["very_long_tag_that_exceeds_normal_length_and_should_test_the_system", "another_very_long_tag_for_testing_purposes"]
                )
                
                # Get current collection
                user_doc = db.collection('users').document(st.session_state.uid).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    collection = user_data.get('collection', [])
                    
                    # Find and update the card
                    updated = False
                    for i, card_data in enumerate(collection):
                        if (card_data.get('player_name') == long_card.player_name and
                            card_data.get('year') == long_card.year and
                            card_data.get('card_set') == long_card.card_set and
                            card_data.get('card_number') == long_card.card_number):
                            collection[i] = long_card.to_dict()
                            updated = True
                            break
                    
                    if updated:
                        # Save the updated collection
                        db.collection('users').document(st.session_state.uid).update({
                            'collection': collection
                        })
                        st.success("Successfully updated card with long text!")
                    else:
                        st.error("Failed to update card with long text!")
                else:
                    st.error("User document not found!")
                    
            except Exception as e:
                st.error(f"Error testing long text: {str(e)}")
                st.write("Debug: Error traceback:", traceback.format_exc())

if __name__ == "__main__":
    test_card_update() 