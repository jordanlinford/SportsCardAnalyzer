from typing import Dict, Any, Optional, List
from uuid import uuid4

class MockFirebaseService:
    """Mock Firebase service for testing"""
    
    def __init__(self):
        self.data: Dict[str, Dict[str, Dict[str, Any]]] = {}
    
    async def create_document(self, collection: str, data: Dict[str, Any]) -> str:
        """Create a new document in the specified collection"""
        if collection not in self.data:
            self.data[collection] = {}
        
        doc_id = str(uuid4())
        self.data[collection][doc_id] = data.copy()
        return doc_id
    
    async def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID from the specified collection"""
        if collection not in self.data or doc_id not in self.data[collection]:
            return None
        return self.data[collection][doc_id].copy()
    
    async def update_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> None:
        """Update a document in the specified collection"""
        if collection not in self.data:
            self.data[collection] = {}
        
        if doc_id not in self.data[collection]:
            raise ValueError(f"Document {doc_id} not found in collection {collection}")
        
        self.data[collection][doc_id].update(data)
    
    async def delete_document(self, collection: str, doc_id: str) -> bool:
        """Delete a document from the specified collection"""
        if collection not in self.data or doc_id not in self.data[collection]:
            return False
        
        del self.data[collection][doc_id]
        return True
    
    async def list_documents(
        self,
        collection: str,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List documents from the specified collection with optional filters"""
        if collection not in self.data:
            return []
        
        docs = list(self.data[collection].values())
        
        if filters:
            for field, value in filters.items():
                docs = [doc for doc in docs if field in doc and doc[field] == value]
        
        if order_by:
            docs.sort(key=lambda x: x.get(order_by))
        
        if limit:
            docs = docs[:limit]
        
        return [doc.copy() for doc in docs]
    
    async def batch_create(self, collection: str, items: List[Dict[str, Any]]) -> List[str]:
        """Create multiple documents in a batch"""
        doc_ids = []
        for item in items:
            doc_id = await self.create_document(collection, item)
            doc_ids.append(doc_id)
        return doc_ids
    
    async def batch_update(self, collection: str, updates: Dict[str, Dict[str, Any]]) -> None:
        """Update multiple documents in a batch"""
        for doc_id, data in updates.items():
            await self.update_document(collection, doc_id, data)
    
    async def batch_delete(self, collection: str, doc_ids: List[str]) -> None:
        """Delete multiple documents in a batch"""
        for doc_id in doc_ids:
            await self.delete_document(collection, doc_id) 