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

class BaseRepository(Generic[T]):
    """Base repository class for handling CRUD operations"""
    
    def __init__(self, collection_name: str, model_class: Type[T]):
        self.collection_name = collection_name
        self.model_class = model_class
        self.firebase = FirebaseService()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    async def create(self, model: T) -> T:
        """Create a new document"""
        try:
            data = model.to_dict()
            doc_id = await self.firebase.create_document(self.collection_name, data)
            model.id = doc_id
            self.logger.info(f"Created document {doc_id} in {self.collection_name}")
            return model
        except Exception as e:
            self.logger.error(f"Error creating document in {self.collection_name}: {str(e)}")
            raise RepositoryError(f"Failed to create document: {str(e)}")
    
    async def get(self, doc_id: str) -> Optional[T]:
        """Get a document by ID"""
        try:
            data = await self.firebase.get_document(self.collection_name, doc_id)
            if not data:
                self.logger.warning(f"Document {doc_id} not found in {self.collection_name}")
                return None
            return self.model_class.from_dict(data)
        except Exception as e:
            self.logger.error(f"Error getting document {doc_id} from {self.collection_name}: {str(e)}")
            raise RepositoryError(f"Failed to get document: {str(e)}")
    
    async def update(self, model: T) -> T:
        """Update a document"""
        try:
            if not model.id:
                raise RepositoryError("Cannot update document without ID")
            
            data = model.to_dict()
            await self.firebase.update_document(self.collection_name, model.id, data)
            self.logger.info(f"Updated document {model.id} in {self.collection_name}")
            return model
        except Exception as e:
            self.logger.error(f"Error updating document {model.id} in {self.collection_name}: {str(e)}")
            raise RepositoryError(f"Failed to update document: {str(e)}")
    
    async def delete(self, doc_id: str) -> bool:
        """Delete a document"""
        try:
            result = await self.firebase.delete_document(self.collection_name, doc_id)
            if result:
                self.logger.info(f"Deleted document {doc_id} from {self.collection_name}")
            else:
                self.logger.warning(f"Document {doc_id} not found in {self.collection_name}")
            return result
        except Exception as e:
            self.logger.error(f"Error deleting document {doc_id} from {self.collection_name}: {str(e)}")
            raise RepositoryError(f"Failed to delete document: {str(e)}")
    
    async def list(self, filters: Optional[Dict[str, Any]] = None) -> List[T]:
        """List documents with optional filters"""
        try:
            docs = await self.firebase.list_documents(self.collection_name, filters)
            return [self.model_class.from_dict(doc) for doc in docs]
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