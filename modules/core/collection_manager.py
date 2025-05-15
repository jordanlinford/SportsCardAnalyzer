"""
Collection Manager Module
Handles all collection-related operations with robust error handling and state management.
"""

from modules.core.error_handler import handle_error, retry_on_error, DatabaseError, ValidationError
from config.environment import Environment
from config.feature_flags import is_feature_enabled
import streamlit as st
import logging

logger = logging.getLogger(__name__)

class CollectionManager:
    """Manages card collection operations with state persistence"""
    
    @staticmethod
    @handle_error
    def init_collection_state():
        """Initialize collection state in session"""
        if 'collection' not in st.session_state:
            st.session_state.collection = []
        if 'collection_loaded' not in st.session_state:
            st.session_state.collection_loaded = False
        if 'collection_version' not in st.session_state:
            st.session_state.collection_version = 0
    
    @staticmethod
    @handle_error
    @retry_on_error(max_retries=3)
    def add_card(card_data):
        """Add a card to the collection with validation"""
        if not is_feature_enabled('collection_management'):
            raise ValidationError("Collection management feature is disabled")
            
        # Validate required fields
        required_fields = ['player_name', 'year', 'card_set', 'card_number']
        for field in required_fields:
            if field not in card_data or not card_data[field]:
                raise ValidationError(f"Missing required field: {field}")
        
        # Generate unique ID if not provided
        if 'id' not in card_data:
            card_data['id'] = f"{card_data['player_name']}_{card_data['year']}_{card_data['card_set']}_{card_data['card_number']}".replace(" ", "_").lower()
        
        # Add to collection
        CollectionManager.init_collection_state()
        st.session_state.collection.append(card_data)
        st.session_state.collection_version += 1
        
        return {
            'success': True,
            'message': 'Card added successfully',
            'card_id': card_data['id']
        }
    
    @staticmethod
    @handle_error
    @retry_on_error(max_retries=3)
    def update_card(card_id, updated_data):
        """Update a card in the collection"""
        CollectionManager.init_collection_state()
        
        # Find card by ID
        card_index = None
        for i, card in enumerate(st.session_state.collection):
            if card.get('id') == card_id:
                card_index = i
                break
        
        if card_index is None:
            raise ValidationError(f"Card with ID {card_id} not found")
        
        # Update card data
        st.session_state.collection[card_index].update(updated_data)
        st.session_state.collection_version += 1
        
        return {
            'success': True,
            'message': 'Card updated successfully'
        }
    
    @staticmethod
    @handle_error
    @retry_on_error(max_retries=3)
    def delete_card(card_id):
        """Delete a card from the collection"""
        CollectionManager.init_collection_state()
        
        # Find card by ID
        card_index = None
        for i, card in enumerate(st.session_state.collection):
            if card.get('id') == card_id:
                card_index = i
                break
        
        if card_index is None:
            raise ValidationError(f"Card with ID {card_id} not found")
        
        # Remove card
        del st.session_state.collection[card_index]
        st.session_state.collection_version += 1
        
        return {
            'success': True,
            'message': 'Card deleted successfully'
        }
    
    @staticmethod
    @handle_error
    def get_collection():
        """Get the current collection"""
        CollectionManager.init_collection_state()
        return st.session_state.collection
    
    @staticmethod
    @handle_error
    def get_card(card_id):
        """Get a specific card by ID"""
        CollectionManager.init_collection_state()
        
        for card in st.session_state.collection:
            if card.get('id') == card_id:
                return card
        
        raise ValidationError(f"Card with ID {card_id} not found")
    
    @staticmethod
    @handle_error
    def clear_collection():
        """Clear the entire collection"""
        CollectionManager.init_collection_state()
        st.session_state.collection = []
        st.session_state.collection_version += 1
        return {
            'success': True,
            'message': 'Collection cleared successfully'
        }
    
    @staticmethod
    @handle_error
    def get_collection_stats():
        """Get collection statistics"""
        CollectionManager.init_collection_state()
        
        stats = {
            'total_cards': len(st.session_state.collection),
            'total_value': sum(float(card.get('current_value', 0)) for card in st.session_state.collection),
            'unique_players': len(set(card.get('player_name') for card in st.session_state.collection)),
            'unique_sets': len(set(card.get('card_set') for card in st.session_state.collection))
        }
        
        return stats 