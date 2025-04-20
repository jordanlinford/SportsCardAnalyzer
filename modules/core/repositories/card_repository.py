from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from modules.core.models import Card
from modules.core.firebase_manager import FirebaseManager
from ..service_container import ServiceContainer
import logging

class CardRepository:
    """Repository for managing Card documents"""
    
    def __init__(self):
        self.db = FirebaseManager.get_instance()
        self.logger = logging.getLogger(__name__)
        self.value_analyzer = ServiceContainer().value_analyzer
        self._cache: Dict[str, Card] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_duration = timedelta(minutes=5)
    
    def _get_from_cache(self, doc_id: str) -> Optional[Card]:
        """Get a card from cache if it exists and hasn't expired"""
        if doc_id in self._cache:
            expiry = self._cache_expiry.get(doc_id)
            if expiry and datetime.now() < expiry:
                return self._cache[doc_id]
            else:
                del self._cache[doc_id]
                del self._cache_expiry[doc_id]
        return None
    
    def _add_to_cache(self, card: Card):
        """Add a card to cache with expiry"""
        self._cache[card.id] = card
        self._cache_expiry[card.id] = datetime.now() + self._cache_duration
    
    async def create(self, card: Card) -> Card:
        """Create a new card"""
        try:
            doc_ref = self.db.collection('cards').document()
            card.id = doc_ref.id
            doc_ref.set(card.to_dict())
            self._add_to_cache(card)
            return card
        except Exception as e:
            self.logger.error(f"Error creating card: {str(e)}")
            raise

    async def get(self, card_id: str) -> Optional[Card]:
        """Get a card by ID"""
        try:
            # Check cache first
            cached_card = self._get_from_cache(card_id)
            if cached_card:
                return cached_card

            doc = self.db.collection('cards').document(card_id).get()
            if not doc.exists:
                return None
            
            card_data = doc.to_dict()
            card = Card(**card_data)
            self._add_to_cache(card)
            return card
        except Exception as e:
            self.logger.error(f"Error getting card: {str(e)}")
            return None

    async def update(self, card: Card) -> Card:
        """Update a card"""
        try:
            if not card.id:
                raise ValueError("Card must have an ID to update")
            
            self.db.collection('cards').document(card.id).update(card.to_dict())
            self._add_to_cache(card)
            return card
        except Exception as e:
            self.logger.error(f"Error updating card: {str(e)}")
            raise

    async def delete(self, card_id: str) -> bool:
        """Delete a card"""
        try:
            self.db.collection('cards').document(card_id).delete()
            if card_id in self._cache:
                del self._cache[card_id]
                del self._cache_expiry[card_id]
            return True
        except Exception as e:
            self.logger.error(f"Error deleting card: {str(e)}")
            return False

    async def list_all(self) -> List[Card]:
        """List all cards"""
        try:
            docs = self.db.collection('cards').get()
            cards = []
            for doc in docs:
                card_data = doc.to_dict()
                card = Card(**card_data)
                self._add_to_cache(card)
                cards.append(card)
            return cards
        except Exception as e:
            self.logger.error(f"Error listing cards: {str(e)}")
            return []

    async def search(self, query: str) -> List[Card]:
        """Search cards by query"""
        try:
            cards = await self.list_all()
            return [
                card for card in cards
                if query.lower() in card.player_name.lower() or
                query.lower() in card.set.lower() or
                str(card.year) == query
            ]
        except Exception as e:
            self.logger.error(f"Error searching cards: {str(e)}")
            return []

    async def filter_by_tags(self, tags: List[str]) -> List[Card]:
        """Filter cards by tags"""
        try:
            cards = await self.list_all()
            return [
                card for card in cards
                if all(tag.lower() in [t.lower() for t in card.tags] for tag in tags)
            ]
        except Exception as e:
            self.logger.error(f"Error filtering cards by tags: {str(e)}")
            return []
    
    async def get_by_player(self, player_name: str) -> List[Card]:
        """Get all cards for a specific player"""
        try:
            cards = await self.list_all()
            return [card for card in cards if card.player_name.lower() == player_name.lower()]
        except Exception as e:
            self.logger.error(f"Error getting cards for player {player_name}: {str(e)}")
            raise
    
    async def get_by_year(self, year: int) -> List[Card]:
        """Get all cards from a specific year"""
        try:
            cards = await self.list_all()
            return [card for card in cards if card.year == year]
        except Exception as e:
            self.logger.error(f"Error getting cards for year {year}: {str(e)}")
            raise
    
    async def get_by_set(self, card_set: str) -> List[Card]:
        """Get all cards from a specific set"""
        try:
            cards = await self.list_all()
            return [card for card in cards if card.set.lower() == card_set.lower()]
        except Exception as e:
            self.logger.error(f"Error getting cards for set {card_set}: {str(e)}")
            raise
    
    async def get_by_condition(self, condition: str) -> List[Card]:
        """Get all cards with a specific condition"""
        try:
            cards = await self.list_all()
            return [card for card in cards if card.condition.lower() == condition.lower()]
        except Exception as e:
            self.logger.error(f"Error getting cards with condition {condition}: {str(e)}")
            raise
    
    async def get_by_tag(self, tag: str) -> List[Card]:
        """Get all cards with a specific tag"""
        try:
            return await self.filter_by_tags([tag])
        except Exception as e:
            self.logger.error(f"Error getting cards with tag {tag}: {str(e)}")
            raise
    
    async def update_value(self, card: Card) -> Card:
        """Update a card's current value and ROI"""
        try:
            if not card.id:
                raise ValueError("Cannot update value for card without ID")
            
            current_value = await self.value_analyzer.analyze_card(card)
            card.current_value = current_value
            if card.purchase_price > 0:
                card.roi = ((current_value - card.purchase_price) / card.purchase_price) * 100
            card.last_updated = datetime.now()
            
            updated = await self.update(card)
            self._add_to_cache(updated)
            return updated
        except Exception as e:
            self.logger.error(f"Error updating value for card {card.id}: {str(e)}")
            raise
    
    async def batch_update_values(self, cards: List[Card]) -> List[Card]:
        """Update values for multiple cards"""
        try:
            if not cards:
                return []
            
            updated_cards = []
            for card in cards:
                try:
                    updated = await self.update_value(card)
                    updated_cards.append(updated)
                except Exception as e:
                    self.logger.error(f"Error updating value for card {card.id}: {str(e)}")
                    # Continue with other cards even if one fails
                    continue
            
            return updated_cards
        except Exception as e:
            self.logger.error(f"Error in batch update values: {str(e)}")
            raise 