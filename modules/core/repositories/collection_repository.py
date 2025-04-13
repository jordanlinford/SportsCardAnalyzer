from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from ..models import Collection, Card
from ..repository import BaseRepository, RepositoryError, DocumentNotFoundError
from .card_repository import CardRepository

class CollectionRepository(BaseRepository[Collection]):
    """Repository for managing Collection documents"""
    
    def __init__(self):
        super().__init__("collections", Collection)
        self.card_repository = CardRepository()
        self._cache: Dict[str, Collection] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_duration = timedelta(minutes=5)
    
    def _get_from_cache(self, doc_id: str) -> Optional[Collection]:
        """Get a collection from cache if it exists and hasn't expired"""
        if doc_id in self._cache:
            expiry = self._cache_expiry.get(doc_id)
            if expiry and datetime.now() < expiry:
                return self._cache[doc_id]
            else:
                del self._cache[doc_id]
                del self._cache_expiry[doc_id]
        return None
    
    def _add_to_cache(self, collection: Collection):
        """Add a collection to cache with expiry"""
        self._cache[collection.id] = collection
        self._cache_expiry[collection.id] = datetime.now() + self._cache_duration
    
    async def get(self, doc_id: str) -> Optional[Collection]:
        """Get a collection by ID with caching"""
        cached = self._get_from_cache(doc_id)
        if cached:
            return cached
        
        collection = await super().get(doc_id)
        if collection:
            self._add_to_cache(collection)
        return collection
    
    async def update(self, collection: Collection) -> Collection:
        """Update a collection and invalidate cache"""
        updated = await super().update(collection)
        if collection.id in self._cache:
            self._add_to_cache(updated)
        return updated
    
    async def delete(self, doc_id: str) -> bool:
        """Delete a collection and remove from cache"""
        result = await super().delete(doc_id)
        if result and doc_id in self._cache:
            del self._cache[doc_id]
            del self._cache_expiry[doc_id]
        return result
    
    async def get_cards(self, collection_id: str) -> List[Card]:
        """Get all cards in a collection"""
        try:
            collection = await self.get(collection_id)
            if not collection:
                raise DocumentNotFoundError(f"Collection {collection_id} not found")
            
            cards = []
            for card_id in collection.cards:
                try:
                    card = await self.card_repository.get(card_id)
                    if card:
                        cards.append(card)
                except Exception as e:
                    self.logger.error(f"Error getting card {card_id} for collection {collection_id}: {str(e)}")
                    # Continue with other cards even if one fails
                    continue
            
            return cards
        except Exception as e:
            self.logger.error(f"Error getting cards for collection {collection_id}: {str(e)}")
            raise RepositoryError(f"Failed to get collection cards: {str(e)}")
    
    async def add_card(self, collection_id: str, card_id: str) -> Collection:
        """Add a card to a collection"""
        try:
            collection = await self.get(collection_id)
            if not collection:
                raise DocumentNotFoundError(f"Collection {collection_id} not found")
            
            if card_id not in collection.cards:
                collection.cards.append(card_id)
                updated = await self.update(collection)
                self._add_to_cache(updated)
                return updated
            return collection
        except Exception as e:
            self.logger.error(f"Error adding card {card_id} to collection {collection_id}: {str(e)}")
            raise RepositoryError(f"Failed to add card to collection: {str(e)}")
    
    async def remove_card(self, collection_id: str, card_id: str) -> Collection:
        """Remove a card from a collection"""
        try:
            collection = await self.get(collection_id)
            if not collection:
                raise DocumentNotFoundError(f"Collection {collection_id} not found")
            
            if card_id in collection.cards:
                collection.cards.remove(card_id)
                updated = await self.update(collection)
                self._add_to_cache(updated)
                return updated
            return collection
        except Exception as e:
            self.logger.error(f"Error removing card {card_id} from collection {collection_id}: {str(e)}")
            raise RepositoryError(f"Failed to remove card from collection: {str(e)}")
    
    async def get_by_user(self, user_id: str) -> List[Collection]:
        """Get all collections for a specific user"""
        try:
            return await self.list({"user_id": user_id})
        except Exception as e:
            self.logger.error(f"Error getting collections for user {user_id}: {str(e)}")
            raise RepositoryError(f"Failed to get user collections: {str(e)}")
    
    async def get_public_collections(self) -> List[Collection]:
        """Get all public collections"""
        try:
            return await self.list({"is_public": True})
        except Exception as e:
            self.logger.error(f"Error getting public collections: {str(e)}")
            raise RepositoryError(f"Failed to get public collections: {str(e)}")
    
    async def search(self, query: str) -> List[Collection]:
        """Search collections by name or description"""
        try:
            all_collections = await self.list()
            return [
                collection for collection in all_collections
                if query.lower() in collection.name.lower() or
                   (collection.description and query.lower() in collection.description.lower())
            ]
        except Exception as e:
            self.logger.error(f"Error searching collections with query {query}: {str(e)}")
            raise RepositoryError(f"Failed to search collections: {str(e)}") 