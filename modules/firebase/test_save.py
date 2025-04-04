from typing import Dict, List
from firebase_admin import firestore
from .config import db
import streamlit as st
from datetime import datetime

def save_collection(uid: str, collection_data: List[Dict]) -> Dict:
    """
    Save a collection of cards to Firebase.
    
    Args:
        uid: User ID
        collection_data: List of card dictionaries to save
        
    Returns:
        Dict with success status and error message if any
    """
    try:
        st.write("Processing collection data...")
        
        # Create a new list for processed items
        processed_data = []
        
        # Process each item individually
        for i, item in enumerate(collection_data):
            st.write(f"Processing item {i+1}/{len(collection_data)}")
            processed_item = {}
            
            # Process each field
            for key, value in item.items():
                if value is None:
                    processed_item[key] = ''  # Convert None to empty string
                elif isinstance(value, (int, float)):
                    processed_item[key] = float(value)  # Convert numbers to float
                elif isinstance(value, (dict, list)):
                    processed_item[key] = str(value)  # Convert complex objects to strings
                elif hasattr(value, 'isoformat'):
                    processed_item[key] = value.isoformat()  # Convert dates to ISO format
                else:
                    processed_item[key] = str(value)  # Convert everything else to string
            
            # Show processed item
            st.write(f"Processed item {i+1}:")
            st.json(processed_item)
            
            processed_data.append(processed_item)
        
        st.write("Saving to Firebase...")
        
        # Save to Firebase
        doc_ref = db.collection('users').document(uid)
        doc_ref.set({
            'collection': processed_data
        }, merge=True)
        
        st.write("Save completed successfully")
        return {'success': True}
    except Exception as e:
        st.error(f"Error in save_collection: {str(e)}")
        return {'success': False, 'error': str(e)}

def test_firebase_connection(uid: str) -> Dict:
    """
    Test Firebase connection and permissions.
    
    Args:
        uid: User ID to test with
        
    Returns:
        Dict with test results and error message if any
    """
    try:
        # Test 1: Check if user document exists
        user_doc = db.collection('users').document(uid).get()
        if not user_doc.exists:
            return {'success': False, 'error': "User document does not exist"}
        
        # Test 2: Try to read user data
        user_data = user_doc.to_dict()
        if not user_data:
            return {'success': False, 'error': "User data is empty"}
        
        # Test 3: Try to write test data
        test_data = {
            'test_field': 'test_value',
            'test_timestamp': datetime.now().isoformat()
        }
        
        # Try to update with test data
        db.collection('users').document(uid).update(test_data)
        
        # Verify the update
        updated_doc = db.collection('users').document(uid).get()
        updated_data = updated_doc.to_dict()
        if 'test_field' not in updated_data or updated_data['test_field'] != 'test_value':
            return {'success': False, 'error': "Failed to verify test data write"}
        
        # Clean up test data
        db.collection('users').document(uid).update({
            'test_field': firestore.DELETE_FIELD,
            'test_timestamp': firestore.DELETE_FIELD
        })
        
        return {'success': True}
        
    except Exception as e:
        return {'success': False, 'error': str(e)} 