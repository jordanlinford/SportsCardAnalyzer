from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from ..models import Card
from ..repository import BaseRepository, RepositoryError, DocumentNotFoundError
from ..service_container import ServiceContainer

class CardRepository(BaseRepository[Card]):
    """Repository for managing Card documents"""
    
    def __init__(self):
        super().__init__("cards", Card)
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
    
    async def get(self, doc_id: str) -> Optional[Card]:
        """Get a card by ID with caching"""
        cached = self._get_from_cache(doc_id)
        if cached:
            return cached
        
        card = await super().get(doc_id)
        if card:
            self._add_to_cache(card)
        return card
    
    async def update(self, card: Card) -> Card:
        """Update a card and invalidate cache"""
        updated = await super().update(card)
        if card.id in self._cache:
            self._add_to_cache(updated)
        return updated
    
    async def delete(self, doc_id: str) -> bool:
        """Delete a card and remove from cache"""
        result = await super().delete(doc_id)
        if result and doc_id in self._cache:
            del self._cache[doc_id]
            del self._cache_expiry[doc_id]
        return result
    
    async def get_by_player(self, player_name: str) -> List[Card]:
        """Get all cards for a specific player"""
        try:
            return await self.list({"player_name": player_name})
        except Exception as e:
            self.logger.error(f"Error getting cards for player {player_name}: {str(e)}")
            raise RepositoryError(f"Failed to get cards by player: {str(e)}")
    
    async def get_by_year(self, year: int) -> List[Card]:
        """Get all cards from a specific year"""
        try:
            return await self.list({"year": year})
        except Exception as e:
            self.logger.error(f"Error getting cards for year {year}: {str(e)}")
            raise RepositoryError(f"Failed to get cards by year: {str(e)}")
    
    async def get_by_set(self, card_set: str) -> List[Card]:
        """Get all cards from a specific set"""
        try:
            return await self.list({"card_set": card_set})
        except Exception as e:
            self.logger.error(f"Error getting cards for set {card_set}: {str(e)}")
            raise RepositoryError(f"Failed to get cards by set: {str(e)}")
    
    async def get_by_condition(self, condition: str) -> List[Card]:
        """Get all cards with a specific condition"""
        try:
            return await self.list({"condition": condition})
        except Exception as e:
            self.logger.error(f"Error getting cards with condition {condition}: {str(e)}")
            raise RepositoryError(f"Failed to get cards by condition: {str(e)}")
    
    async def get_by_tag(self, tag: str) -> List[Card]:
        """Get all cards with a specific tag"""
        try:
            return await self.list({"tags": tag})
        except Exception as e:
            self.logger.error(f"Error getting cards with tag {tag}: {str(e)}")
            raise RepositoryError(f"Failed to get cards by tag: {str(e)}")
    
    async def search(self, query: str) -> List[Card]:
        """Search cards by player name, set, or card number"""
        try:
            all_cards = await self.list()
            return [
                card for card in all_cards
                if query.lower() in card.player_name.lower() or
                   query.lower() in card.card_set.lower() or
                   query.lower() in card.card_number.lower()
            ]
        except Exception as e:
            self.logger.error(f"Error searching cards with query {query}: {str(e)}")
            raise RepositoryError(f"Failed to search cards: {str(e)}")
    
    async def update_value(self, card: Card) -> Card:
        """Update a card's current value and ROI"""
        try:
            if not card.id:
                raise RepositoryError("Cannot update value for card without ID")
            
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
            raise RepositoryError(f"Failed to update card value: {str(e)}")
    
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
            raise RepositoryError(f"Failed to batch update card values: {str(e)}") 