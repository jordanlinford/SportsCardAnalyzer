from typing import TypeVar, Type, List, Optional, Dict, Any, Generic
import logging
from datetime import datetime
from .models import BaseModel
from modules.services.firebase import FirebaseService

T = TypeVar('T', bound=BaseModel)

class RepositoryError(Exception):
    """Base exception for repository errors"""
    pass

class DocumentNotFoundError(RepositoryError):
    """Raised when a document is not found"""
    pass

class Repository(Generic[T]):
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.firebase = FirebaseService()
        self.logger = logging.getLogger(__name__)
        self._cache = {}
    
    async def create(self, model: T) -> T:
        """Create a new document"""
        try:
            data = model.to_dict()
            doc_id = await self.firebase.create_document(self.collection_name, data)
            model.id = doc_id
            self._add_to_cache(model)
            self.logger.info(f"Created document {doc_id} in {self.collection_name}")
            return model
        except Exception as e:
            self.logger.error(f"Error creating document in {self.collection_name}: {str(e)}")
            raise RepositoryError(f"Failed to create document: {str(e)}")
    
    async def get(self, doc_id: str) -> Optional[T]:
        """Get a document by ID"""
        try:
            # Check cache first
            if doc_id in self._cache:
                return self._cache[doc_id]

            data = await self.firebase.get_document(self.collection_name, doc_id)
            if not data:
                return None

            model = self._create_model(data)
            self._add_to_cache(model)
            return model
        except Exception as e:
            self.logger.error(f"Error getting document {doc_id} from {self.collection_name}: {str(e)}")
            return None
    
    async def update(self, model: T) -> T:
        """Update a document"""
        try:
            if not model.id:
                raise RepositoryError("Cannot update document without ID")
            
            data = model.to_dict()
            await self.firebase.update_document(self.collection_name, model.id, data)
            self._add_to_cache(model)
            self.logger.info(f"Updated document {model.id} in {self.collection_name}")
            return model
        except Exception as e:
            self.logger.error(f"Error updating document {model.id} in {self.collection_name}: {str(e)}")
            raise RepositoryError(f"Failed to update document: {str(e)}")
    
    async def delete(self, doc_id: str) -> bool:
        """Delete a document"""
        try:
            await self.firebase.delete_document(self.collection_name, doc_id)
            self._remove_from_cache(doc_id)
            self.logger.info(f"Deleted document {doc_id} from {self.collection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting document {doc_id} from {self.collection_name}: {str(e)}")
            return False
    
    async def list_all(self) -> List[T]:
        """List all documents"""
        try:
            docs = await self.firebase.list_documents(self.collection_name)
            models = []
            for doc in docs:
                try:
                    model = self._create_model(doc)
                    models.append(model)
                    self._add_to_cache(model)
                except Exception as e:
                    self.logger.error(f"Error creating model from document: {str(e)}")
                    continue
            return models
        except Exception as e:
            self.logger.error(f"Error listing documents from {self.collection_name}: {str(e)}")
            return []

    def _create_model(self, data: Dict) -> T:
        """Create a model instance from data"""
        try:
            return T(**data)
        except Exception as e:
            self.logger.error(f"Error creating model from data: {str(e)}")
            raise RepositoryError(f"Failed to create model: {str(e)}")

    def _add_to_cache(self, model: T) -> None:
        """Add model to cache"""
        if model.id:
            self._cache[model.id] = model

    def _remove_from_cache(self, doc_id: str) -> None:
        """Remove model from cache"""
        self._cache.pop(doc_id, None)
    
    async def list(self, filters: Optional[Dict[str, Any]] = None) -> List[T]:
        """List documents with optional filters"""
        try:
            docs = await self.firebase.list_documents(self.collection_name, filters)
            return [self._create_model(doc) for doc in docs]
        except Exception as e:
            self.logger.error(f"Error listing documents in {self.collection_name}: {str(e)}")
            raise RepositoryError(f"Failed to list documents: {str(e)}")
    
    async def batch_create(self, models: List[T]) -> List[T]:
        """Create multiple documents in a batch"""
        try:
            if not models:
                return []
            
            data_list = [model.to_dict() for model in models]
            doc_ids = await self.firebase.batch_create(self.collection_name, data_list)
            for model, doc_id in zip(models, doc_ids):
                model.id = doc_id
            self.logger.info(f"Created {len(models)} documents in {self.collection_name}")
            return models
        except Exception as e:
            self.logger.error(f"Error batch creating documents in {self.collection_name}: {str(e)}")
            raise RepositoryError(f"Failed to batch create documents: {str(e)}")
    
    async def batch_update(self, models: List[T]) -> List[T]:
        """Update multiple documents in a batch"""
        try:
            if not models:
                return []
            
            updates = {model.id: model.to_dict() for model in models if model.id}
            await self.firebase.batch_update(self.collection_name, updates)
            self.logger.info(f"Updated {len(models)} documents in {self.collection_name}")
            return models
        except Exception as e:
            self.logger.error(f"Error batch updating documents in {self.collection_name}: {str(e)}")
            raise RepositoryError(f"Failed to batch update documents: {str(e)}")
    
    async def batch_delete(self, doc_ids: List[str]) -> bool:
        """Delete multiple documents in a batch"""
        try:
            if not doc_ids:
                return True
            
            await self.firebase.batch_delete(self.collection_name, doc_ids)
            self.logger.info(f"Deleted {len(doc_ids)} documents from {self.collection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error batch deleting documents from {self.collection_name}: {str(e)}")
            raise RepositoryError(f"Failed to batch delete documents: {str(e)}")
    
    async def exists(self, doc_id: str) -> bool:
        """Check if a document exists"""
        try:
            doc = await self.get(doc_id)
            return doc is not None
        except Exception as e:
            self.logger.error(f"Error checking existence of document {doc_id}: {str(e)}")
            raise RepositoryError(f"Failed to check document existence: {str(e)}") 