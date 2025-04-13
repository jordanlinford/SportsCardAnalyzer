from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from ..models import UserProfile, Collection
from ..repository import BaseRepository, RepositoryError, DocumentNotFoundError
from .collection_repository import CollectionRepository

class UserRepository(BaseRepository[UserProfile]):
    """Repository for managing UserProfile documents"""
    
    def __init__(self):
        super().__init__("users", UserProfile)
        self.collection_repository = CollectionRepository()
        self._cache: Dict[str, UserProfile] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_duration = timedelta(minutes=5)
    
    def _get_from_cache(self, doc_id: str) -> Optional[UserProfile]:
        """Get a user from cache if it exists and hasn't expired"""
        if doc_id in self._cache:
            expiry = self._cache_expiry.get(doc_id)
            if expiry and datetime.now() < expiry:
                return self._cache[doc_id]
            else:
                del self._cache[doc_id]
                del self._cache_expiry[doc_id]
        return None
    
    def _add_to_cache(self, user: UserProfile):
        """Add a user to cache with expiry"""
        self._cache[user.id] = user
        self._cache_expiry[user.id] = datetime.now() + self._cache_duration
    
    async def get(self, doc_id: str) -> Optional[UserProfile]:
        """Get a user by ID with caching"""
        cached = self._get_from_cache(doc_id)
        if cached:
            return cached
        
        user = await super().get(doc_id)
        if user:
            self._add_to_cache(user)
        return user
    
    async def update(self, user: UserProfile) -> UserProfile:
        """Update a user and invalidate cache"""
        updated = await super().update(user)
        if user.id in self._cache:
            self._add_to_cache(updated)
        return updated
    
    async def delete(self, doc_id: str) -> bool:
        """Delete a user and remove from cache"""
        result = await super().delete(doc_id)
        if result and doc_id in self._cache:
            del self._cache[doc_id]
            del self._cache_expiry[doc_id]
        return result
    
    async def get_collections(self, user_id: str) -> List[Collection]:
        """Get all collections for a user"""
        try:
            user = await self.get(user_id)
            if not user:
                raise DocumentNotFoundError(f"User {user_id} not found")
            
            collections = []
            for collection_id in user.collections:
                try:
                    collection = await self.collection_repository.get(collection_id)
                    if collection:
                        collections.append(collection)
                except Exception as e:
                    self.logger.error(f"Error getting collection {collection_id} for user {user_id}: {str(e)}")
                    # Continue with other collections even if one fails
                    continue
            
            return collections
        except Exception as e:
            self.logger.error(f"Error getting collections for user {user_id}: {str(e)}")
            raise RepositoryError(f"Failed to get user collections: {str(e)}")
    
    async def add_collection(self, user_id: str, collection_id: str) -> UserProfile:
        """Add a collection to a user's profile"""
        try:
            user = await self.get(user_id)
            if not user:
                raise DocumentNotFoundError(f"User {user_id} not found")
            
            if collection_id not in user.collections:
                user.collections.append(collection_id)
                updated = await self.update(user)
                self._add_to_cache(updated)
                return updated
            return user
        except Exception as e:
            self.logger.error(f"Error adding collection {collection_id} to user {user_id}: {str(e)}")
            raise RepositoryError(f"Failed to add collection to user: {str(e)}")
    
    async def remove_collection(self, user_id: str, collection_id: str) -> UserProfile:
        """Remove a collection from a user's profile"""
        try:
            user = await self.get(user_id)
            if not user:
                raise DocumentNotFoundError(f"User {user_id} not found")
            
            if collection_id in user.collections:
                user.collections.remove(collection_id)
                updated = await self.update(user)
                self._add_to_cache(updated)
                return updated
            return user
        except Exception as e:
            self.logger.error(f"Error removing collection {collection_id} from user {user_id}: {str(e)}")
            raise RepositoryError(f"Failed to remove collection from user: {str(e)}")
    
    async def update_preferences(self, user_id: str, preferences: Dict[str, Any]) -> UserProfile:
        """Update user preferences"""
        try:
            user = await self.get(user_id)
            if not user:
                raise DocumentNotFoundError(f"User {user_id} not found")
            
            user.preferences.update(preferences)
            updated = await self.update(user)
            self._add_to_cache(updated)
            return updated
        except Exception as e:
            self.logger.error(f"Error updating preferences for user {user_id}: {str(e)}")
            raise RepositoryError(f"Failed to update user preferences: {str(e)}")
    
    async def get_by_email(self, email: str) -> Optional[UserProfile]:
        """Get a user by email"""
        try:
            users = await self.list({"email": email})
            return users[0] if users else None
        except Exception as e:
            self.logger.error(f"Error getting user by email {email}: {str(e)}")
            raise RepositoryError(f"Failed to get user by email: {str(e)}")
    
    async def search(self, query: str) -> List[UserProfile]:
        """Search users by display name or email"""
        try:
            all_users = await self.list()
            return [
                user for user in all_users
                if query.lower() in user.display_name.lower() or
                   query.lower() in user.email.lower()
            ]
        except Exception as e:
            self.logger.error(f"Error searching users with query {query}: {str(e)}")
            raise RepositoryError(f"Failed to search users: {str(e)}") 