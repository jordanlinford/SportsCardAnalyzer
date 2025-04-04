import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from modules.firebase.test_save import save_collection, test_firebase_connection
from modules.firebase.user_management import UserManager
from modules.database.service import DatabaseService
from modules.database.models import Card, CardCondition
import streamlit as st
import json

st.title("Test Save Collection")

# Initialize session state for authentication
if 'user' not in st.session_state:
    st.session_state.user = None
if 'uid' not in st.session_state:
    st.session_state.uid = None

# Authentication section
st.header("Authentication")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Sign In")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Sign In"):
        result = UserManager.sign_in(email, password)
        if result['success']:
            st.session_state.user = result['user']
            st.session_state.uid = result['uid']
            st.success("Signed in successfully!")
        else:
            st.error(result['error'])

with col2:
    st.subheader("Create Account")
    new_email = st.text_input("New Email")
    new_password = st.text_input("New Password", type="password")
    display_name = st.text_input("Display Name")
    if st.button("Create Account"):
        result = UserManager.create_user(new_email, new_password, display_name)
        if result['success']:
            st.session_state.user = result['user']
            st.session_state.uid = result['uid']
            st.success("Account created successfully!")
        else:
            st.error(result['error'])

# Test section
if st.session_state.user and st.session_state.uid:
    st.header("Test Save Collection")
    st.write(f"Logged in as: {st.session_state.user.get('email', 'Unknown')}")
    st.write(f"User ID: {st.session_state.uid}")

    # Test Firebase Connection
    if st.button("Test Firebase Connection"):
        result = test_firebase_connection(st.session_state.uid)
        if result['success']:
            st.success("Firebase connection test passed!")
        else:
            st.error(f"Firebase connection test failed: {result['error']}")

    # Test Card Saving
    if st.button("Test Card Save"):
        try:
            # Create a test card
            test_card = Card(
                player_name="Test Player",
                year="2024",
                card_set="Test Set",
                card_number="123",
                variation="Test Variation",
                condition=CardCondition.RAW,
                purchase_price=100.0,
                purchase_date=datetime.now(),
                current_value=150.0,
                last_updated=datetime.now(),
                notes="Test card for testing",
                photo="test_photo_url",
                roi=50.0,
                tags=["test", "card"]
            )

            # Try to save the card
            success = DatabaseService.save_user_collection(st.session_state.uid, [test_card])
            
            if success:
                st.success("Card saved successfully!")
                
                # Verify the card was saved
                saved_cards = DatabaseService.get_user_collection(st.session_state.uid)
                if saved_cards:
                    st.success(f"Retrieved {len(saved_cards)} cards from database")
                    st.write("Last saved card:", saved_cards[-1].to_dict())
                else:
                    st.error("No cards found in database after save")
            else:
                st.error("Failed to save card to database")
                
        except Exception as e:
            st.error(f"Error during test: {str(e)}")
            import traceback
            st.write("Error traceback:", traceback.format_exc())

    # Test Edge Cases
    if st.button("Test Edge Cases"):
        try:
            # Test cards with various edge cases
            edge_cases = [
                # Card with missing fields
                Card(
                    player_name="Edge Case 1",
                    year="2024",
                    card_set="Test Set",
                    card_number="456",
                    variation="",
                    condition=CardCondition.RAW,
                    purchase_price=0.0,
                    purchase_date=datetime.now(),
                    current_value=0.0,
                    last_updated=datetime.now(),
                    notes="",
                    photo="",
                    roi=0.0,
                    tags=[]
                ),
                # Card with special characters
                Card(
                    player_name="José Ramírez",
                    year="2024",
                    card_set="Test Set",
                    card_number="789",
                    variation="Special #/100",
                    condition=CardCondition.PSA_10,
                    purchase_price=1000.0,
                    purchase_date=datetime.now(),
                    current_value=1500.0,
                    last_updated=datetime.now(),
                    notes="Special characters test!",
                    photo="test_photo_url",
                    roi=50.0,
                    tags=["special", "characters", "test"]
                ),
                # Card with very long text
                Card(
                    player_name="Long Text Test",
                    year="2024",
                    card_set="Test Set",
                    card_number="101",
                    variation="Long Text Variation",
                    condition=CardCondition.PSA_9,
                    purchase_price=200.0,
                    purchase_date=datetime.now(),
                    current_value=300.0,
                    last_updated=datetime.now(),
                    notes="This is a very long note that tests how the system handles long text fields. It should be properly stored and retrieved without any issues. The note contains multiple sentences and various types of characters to ensure proper handling.",
                    photo="test_photo_url",
                    roi=50.0,
                    tags=["long", "text", "test", "multiple", "tags", "for", "testing"]
                )
            ]

            # Try to save the edge cases
            success = DatabaseService.save_user_collection(st.session_state.uid, edge_cases)
            
            if success:
                st.success("Edge case cards saved successfully!")
                
                # Verify the cards were saved
                saved_cards = DatabaseService.get_user_collection(st.session_state.uid)
                if saved_cards:
                    st.success(f"Retrieved {len(saved_cards)} cards from database")
                    st.write("Last saved edge case card:", saved_cards[-1].to_dict())
                else:
                    st.error("No cards found in database after save")
            else:
                st.error("Failed to save edge case cards to database")
                
        except Exception as e:
            st.error(f"Error during edge case test: {str(e)}")
            import traceback
            st.write("Error traceback:", traceback.format_exc())

    # Clear Collection
    if st.button("Clear Collection"):
        try:
            # Create an empty collection
            success = DatabaseService.save_user_collection(st.session_state.uid, [])
            
            if success:
                st.success("Collection cleared successfully!")
                
                # Verify the collection is empty
                saved_cards = DatabaseService.get_user_collection(st.session_state.uid)
                if not saved_cards:
                    st.success("Collection is empty")
                else:
                    st.error(f"Collection still contains {len(saved_cards)} cards")
            else:
                st.error("Failed to clear collection")
                
        except Exception as e:
            st.error(f"Error clearing collection: {str(e)}")
            import traceback
            st.write("Error traceback:", traceback.format_exc()) 