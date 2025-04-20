from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from modules.core.repository import Repository, RepositoryError, DocumentNotFoundError
from modules.core.models import User
from .collection_repository import CollectionRepository
import logging

class UserRepository:
    """Repository for managing User documents"""
    
    def __init__(self):
        self._repository = Repository('users')
        self.logger = logging.getLogger(__name__)
        self.collection_repository = CollectionRepository()
        self._cache: Dict[str, User] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_duration = timedelta(minutes=5)
    
    def _get_from_cache(self, doc_id: str) -> Optional[User]:
        """Get a user from cache if it exists and hasn't expired"""
        if doc_id in self._cache:
            expiry = self._cache_expiry.get(doc_id)
            if expiry and datetime.now() < expiry:
                return self._cache[doc_id]
            else:
                del self._cache[doc_id]
                del self._cache_expiry[doc_id]
        return None
    
    def _add_to_cache(self, user: User):
        """Add a user to cache with expiry"""
        self._cache[user.id] = user
        self._cache_expiry[user.id] = datetime.now() + self._cache_duration
    
    async def create(self, user: User) -> User:
        """Create a new user"""
        try:
            return await self._repository.create(user)
        except Exception as e:
            self.logger.error(f"Error creating user: {str(e)}")
            raise RepositoryError(f"Failed to create user: {str(e)}")

    async def get(self, user_id: str) -> Optional[User]:
        """Get a user by ID"""
        try:
            return await self._repository.get(user_id)
        except Exception as e:
            self.logger.error(f"Error getting user: {str(e)}")
            return None

    async def update(self, user: User) -> User:
        """Update a user"""
        try:
            return await self._repository.update(user)
        except Exception as e:
            self.logger.error(f"Error updating user: {str(e)}")
            raise RepositoryError(f"Failed to update user: {str(e)}")

    async def delete(self, user_id: str) -> bool:
        """Delete a user"""
        try:
            return await self._repository.delete(user_id)
        except Exception as e:
            self.logger.error(f"Error deleting user: {str(e)}")
            return False

    async def list_all(self) -> List[User]:
        """List all users"""
        try:
            return await self._repository.list_all()
        except Exception as e:
            self.logger.error(f"Error listing users: {str(e)}")
            return []

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        try:
            users = await self.list_all()
            for user in users:
                if user.email.lower() == email.lower():
                    return user
            return None
        except Exception as e:
            self.logger.error(f"Error getting user by email: {str(e)}")
            return None

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by username"""
        try:
            users = await self.list_all()
            for user in users:
                if user.username.lower() == username.lower():
                    return user
            return None
        except Exception as e:
            self.logger.error(f"Error getting user by username: {str(e)}")
            return None

    async def get_collections(self, user_id: str) -> List[User]:
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
    
    async def add_collection(self, user_id: str, collection_id: str) -> User:
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
    
    async def remove_collection(self, user_id: str, collection_id: str) -> User:
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
    
    async def update_preferences(self, user_id: str, preferences: Dict[str, Any]) -> User:
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
    
    async def search(self, query: str) -> List[User]:
        """Search users by display name or email"""
        try:
            all_users = await self.list_all()
            return [
                user for user in all_users
                if query.lower() in user.display_name.lower() or
                   query.lower() in user.email.lower()
            ]
        except Exception as e:
            self.logger.error(f"Error searching users with query {query}: {str(e)}")
            raise RepositoryError(f"Failed to search users: {str(e)}") 