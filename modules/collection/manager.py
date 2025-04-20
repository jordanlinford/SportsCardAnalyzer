from typing import List, Dict, Optional
from modules.core.database_service import DatabaseService
from modules.core.models import Card
import streamlit as st
import logging

logger = logging.getLogger(__name__)

class CollectionManager:
    """Manager for handling card collection operations."""
    
    def __init__(self):
        """Initialize the collection manager."""
        self._db = DatabaseService()
        
    def get_user_collection(self, uid: str) -> List[Card]:
        """
        Get all cards from user's collection.
        
        Args:
            uid (str): User ID
            
        Returns:
            List[Card]: List of cards in user's collection
        """
        try:
            return self._db.get_user_collection(uid)
        except Exception as e:
            logger.error(f"Error getting user collection: {str(e)}")
            return []
            
    def add_card(self, uid: str, card: Card) -> bool:
        """
        Add a card to user's collection.
        
        Args:
            uid (str): User ID
            card (Card): Card to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check for duplicate card
            existing_cards = self.get_user_collection(uid)
            for existing_card in existing_cards:
                if (existing_card.player_name == card.player_name and
                    existing_card.year == card.year and
                    existing_card.card_set == card.card_set and
                    existing_card.card_number == card.card_number):
                    st.error("This card already exists in your collection!")
                    return False
                    
            # Add the card
            success = self._db.add_card_to_collection(uid, card)
            if success:
                st.success("Card added successfully!")
                return True
            else:
                st.error("Failed to add card to collection.")
                return False
        except Exception as e:
            logger.error(f"Error adding card: {str(e)}")
            st.error("An error occurred while adding the card.")
            return False
            
    def update_card(self, uid: str, card: Card) -> bool:
        """
        Update a card in user's collection.
        
        Args:
            uid (str): User ID
            card (Card): Card to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            success = self._db.update_card_in_collection(uid, card)
            if success:
                st.success("Card updated successfully!")
                return True
            else:
                st.error("Failed to update card.")
                return False
        except Exception as e:
            logger.error(f"Error updating card: {str(e)}")
            st.error("An error occurred while updating the card.")
            return False
            
    def delete_card(self, uid: str, card: Card) -> bool:
        """
        Delete a card from user's collection.
        
        Args:
            uid (str): User ID
            card (Card): Card to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            success = self._db.delete_card_from_collection(uid, card)
            if success:
                st.success("Card deleted successfully!")
                return True
            else:
                st.error("Failed to delete card.")
                return False
        except Exception as e:
            logger.error(f"Error deleting card: {str(e)}")
            st.error("An error occurred while deleting the card.")
            return False
            
    def search_cards(self, uid: str, query: str) -> List[Card]:
        """
        Search cards in user's collection.
        
        Args:
            uid (str): User ID
            query (str): Search query
            
        Returns:
            List[Card]: List of matching cards
        """
        try:
            cards = self.get_user_collection(uid)
            query = query.lower()
            
            return [
                card for card in cards
                if query in card.player_name.lower() or
                   query in card.card_set.lower() or
                   query in str(card.year) or
                   query in str(card.card_number)
            ]
        except Exception as e:
            logger.error(f"Error searching cards: {str(e)}")
            return []
            
    def filter_cards_by_tags(self, uid: str, tags: List[str]) -> List[Card]:
        """
        Filter cards by tags.
        
        Args:
            uid (str): User ID
            tags (List[str]): Tags to filter by
            
        Returns:
            List[Card]: List of cards matching the tags
        """
        try:
            cards = self.get_user_collection(uid)
            if not tags:
                return cards
                
            # Normalize tags
            normalized_tags = {tag.lower().strip() for tag in tags}
            
            return [
                card for card in cards
                if card.tags and any(tag.lower().strip() in normalized_tags for tag in card.tags)
            ]
        except Exception as e:
            logger.error(f"Error filtering cards by tags: {str(e)}")
            return []
            
    def get_collection_stats(self, uid: str) -> Dict:
        """
        Get statistics about user's collection.
        
        Args:
            uid (str): User ID
            
        Returns:
            Dict: Collection statistics
        """
        try:
            cards = self.get_user_collection(uid)
            total_cards = len(cards)
            total_value = sum(card.value or 0 for card in cards)
            
            # Count cards by year
            cards_by_year = {}
            for card in cards:
                year = card.year
                if year in cards_by_year:
                    cards_by_year[year] += 1
                else:
                    cards_by_year[year] = 1
                    
            # Count cards by player
            cards_by_player = {}
            for card in cards:
                player = card.player_name
                if player in cards_by_player:
                    cards_by_player[player] += 1
                else:
                    cards_by_player[player] = 1
                    
            return {
                'total_cards': total_cards,
                'total_value': total_value,
                'cards_by_year': cards_by_year,
                'cards_by_player': cards_by_player
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {
                'total_cards': 0,
                'total_value': 0,
                'cards_by_year': {},
                'cards_by_player': {}
            } 