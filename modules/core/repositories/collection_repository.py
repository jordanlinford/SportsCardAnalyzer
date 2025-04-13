from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from modules.core.repository import Repository, RepositoryError, DocumentNotFoundError
from modules.core.models import Collection, Card
from .card_repository import CardRepository
import logging

class CollectionRepository:
    """Repository for managing Collection documents"""
    
    def __init__(self):
        self._repository = Repository('collections')
        self._card_repository = Repository('cards')
        self.logger = logging.getLogger(__name__)
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
    
    async def create(self, collection: Collection) -> Collection:
        """Create a new collection"""
        try:
            return await self._repository.create(collection)
        except Exception as e:
            self.logger.error(f"Error creating collection: {str(e)}")
            raise RepositoryError(f"Failed to create collection: {str(e)}")

    async def get(self, collection_id: str) -> Optional[Collection]:
        """Get a collection by ID"""
        try:
            return await self._repository.get(collection_id)
        except Exception as e:
            self.logger.error(f"Error getting collection: {str(e)}")
            return None

    async def update(self, collection: Collection) -> Collection:
        """Update a collection"""
        try:
            return await self._repository.update(collection)
        except Exception as e:
            self.logger.error(f"Error updating collection: {str(e)}")
            raise RepositoryError(f"Failed to update collection: {str(e)}")

    async def delete(self, collection_id: str) -> bool:
        """Delete a collection"""
        try:
            return await self._repository.delete(collection_id)
        except Exception as e:
            self.logger.error(f"Error deleting collection: {str(e)}")
            return False

    async def list_all(self) -> List[Collection]:
        """List all collections"""
        try:
            return await self._repository.list_all()
        except Exception as e:
            self.logger.error(f"Error listing collections: {str(e)}")
            return []

    async def add_card(self, collection_id: str, card_id: str) -> bool:
        """Add a card to a collection"""
        try:
            collection = await self.get(collection_id)
            if not collection:
                raise DocumentNotFoundError(f"Collection {collection_id} not found")

            card = await self._card_repository.get(card_id)
            if not card:
                raise DocumentNotFoundError(f"Card {card_id} not found")

            if card_id not in collection.cards:
                collection.cards.append(card_id)
                await self.update(collection)
            return True
        except Exception as e:
            self.logger.error(f"Error adding card to collection: {str(e)}")
            raise RepositoryError(f"Failed to add card to collection: {str(e)}")

    async def remove_card(self, collection_id: str, card_id: str) -> bool:
        """Remove a card from a collection"""
        try:
            collection = await self.get(collection_id)
            if not collection:
                raise DocumentNotFoundError(f"Collection {collection_id} not found")

            if card_id in collection.cards:
                collection.cards.remove(card_id)
                await self.update(collection)
            return True
        except Exception as e:
            self.logger.error(f"Error removing card from collection: {str(e)}")
            raise RepositoryError(f"Failed to remove card from collection: {str(e)}")

    async def get_cards(self, collection_id: str) -> List[Card]:
        """Get all cards in a collection"""
        try:
            collection = await self.get(collection_id)
            if not collection:
                raise DocumentNotFoundError(f"Collection {collection_id} not found")

            cards = []
            for card_id in collection.cards:
                card = await self._card_repository.get(card_id)
                if card:
                    cards.append(card)
            return cards
        except Exception as e:
            self.logger.error(f"Error getting cards from collection: {str(e)}")
            raise RepositoryError(f"Failed to get cards from collection: {str(e)}")
    
    async def get_by_user(self, user_id: str) -> List[Collection]:
        """Get all collections for a specific user"""
        try:
            return await self.list_all()
        except Exception as e:
            self.logger.error(f"Error getting collections for user {user_id}: {str(e)}")
            raise RepositoryError(f"Failed to get user collections: {str(e)}")
    
    async def get_public_collections(self) -> List[Collection]:
        """Get all public collections"""
        try:
            return await self.list_all()
        except Exception as e:
            self.logger.error(f"Error getting public collections: {str(e)}")
            raise RepositoryError(f"Failed to get public collections: {str(e)}")
    
    async def search(self, query: str) -> List[Collection]:
        """Search collections by name or description"""
        try:
            all_collections = await self.list_all()
            return [
                collection for collection in all_collections
                if query.lower() in collection.name.lower() or
                   (collection.description and query.lower() in collection.description.lower())
            ]
        except Exception as e:
            self.logger.error(f"Error searching collections with query {query}: {str(e)}")
            raise RepositoryError(f"Failed to search collections: {str(e)}") 