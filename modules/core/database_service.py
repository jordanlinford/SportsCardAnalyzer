from typing import List, Dict, Optional
from firebase_admin import firestore
from modules.core.firebase_manager import FirebaseManager
from modules.core.models import Card
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for handling database operations."""
    
    def __init__(self):
        """Initialize the database service."""
        self._db = FirebaseManager().get_firestore_client()
        
    def get_user_data(self, uid: str) -> Dict:
        """
        Get user data from Firestore.
        
        Args:
            uid (str): User ID
            
        Returns:
            Dict: User data
        """
        try:
            doc = self._db.collection('users').document(uid).get()
            return doc.to_dict() if doc.exists else {}
        except Exception as e:
            logger.error(f"Error getting user data: {str(e)}")
            return {}
            
    def save_user_preferences(self, uid: str, preferences: Dict) -> bool:
        """
        Save user preferences to Firestore.
        
        Args:
            uid (str): User ID
            preferences (Dict): User preferences
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._db.collection('users').document(uid).set({
                'preferences': preferences
            }, merge=True)
            return True
        except Exception as e:
            logger.error(f"Error saving user preferences: {str(e)}")
            return False
            
    def get_user_collection(self, uid: str) -> List[Card]:
        """
        Get all cards from user's collection.
        
        Args:
            uid (str): User ID
            
        Returns:
            List[Card]: List of cards in user's collection
        """
        try:
            cards = []
            docs = self._db.collection('users').document(uid).collection('cards').stream()
            for doc in docs:
                card_data = doc.to_dict()
                cards.append(Card(**card_data))
            return cards
        except Exception as e:
            logger.error(f"Error getting user collection: {str(e)}")
            return []
            
    def save_user_collection(self, uid: str, cards: List[Card]) -> bool:
        """
        Save user's card collection to Firestore.
        
        Args:
            uid (str): User ID
            cards (List[Card]): List of cards to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            batch = self._db.batch()
            cards_ref = self._db.collection('users').document(uid).collection('cards')
            
            # Clear existing collection
            docs = cards_ref.stream()
            for doc in docs:
                batch.delete(doc.reference)
                
            # Add new cards
            for card in cards:
                card_dict = card.dict()
                card_id = f"{card.player_name}_{card.year}_{card.card_set}_{card.card_number}".lower().replace(" ", "_")
                doc_ref = cards_ref.document(card_id)
                batch.set(doc_ref, card_dict)
                
            batch.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving user collection: {str(e)}")
            return False
            
    def add_card_to_collection(self, uid: str, card: Card) -> bool:
        """
        Add a card to user's collection.
        
        Args:
            uid (str): User ID
            card (Card): Card to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            card_dict = card.dict()
            card_id = f"{card.player_name}_{card.year}_{card.card_set}_{card.card_number}".lower().replace(" ", "_")
            self._db.collection('users').document(uid).collection('cards').document(card_id).set(card_dict)
            return True
        except Exception as e:
            logger.error(f"Error adding card to collection: {str(e)}")
            return False
            
    def delete_card_from_collection(self, uid: str, card: Card) -> bool:
        """
        Delete a card from user's collection.
        
        Args:
            uid (str): User ID
            card (Card): Card to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            card_id = f"{card.player_name}_{card.year}_{card.card_set}_{card.card_number}".lower().replace(" ", "_")
            self._db.collection('users').document(uid).collection('cards').document(card_id).delete()
            return True
        except Exception as e:
            logger.error(f"Error deleting card from collection: {str(e)}")
            return False
            
    def update_card_in_collection(self, uid: str, card: Card) -> bool:
        """
        Update a card in user's collection.
        
        Args:
            uid (str): User ID
            card (Card): Card to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            card_dict = card.dict()
            card_id = f"{card.player_name}_{card.year}_{card.card_set}_{card.card_number}".lower().replace(" ", "_")
            self._db.collection('users').document(uid).collection('cards').document(card_id).update(card_dict)
            return True
        except Exception as e:
            logger.error(f"Error updating card in collection: {str(e)}")
            return False 