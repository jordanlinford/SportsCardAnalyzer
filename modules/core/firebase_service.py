import firebase_admin
from firebase_admin import credentials, firestore
from typing import Dict, Any, Optional, List
import json
import os

class FirebaseService:
    def __init__(self, credentials_path: str):
        if not firebase_admin._apps:
            cred = credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()

    async def create_document(self, collection: str, data: Dict[str, Any]) -> Any:
        """Create a new document in the specified collection"""
        doc_ref = self.db.collection(collection).document()
        doc_ref.set(data)
        return doc_ref

    async def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID from the specified collection"""
        doc = self.db.collection(collection).document(doc_id).get()
        return doc.to_dict() if doc.exists else None

    async def update_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> None:
        """Update a document in the specified collection"""
        self.db.collection(collection).document(doc_id).update(data)

    async def delete_document(self, collection: str, doc_id: str) -> bool:
        """Delete a document from the specified collection"""
        doc = self.db.collection(collection).document(doc_id)
        if doc.get().exists:
            doc.delete()
            return True
        return False

    async def list_documents(self, collection: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        """List documents from the specified collection with optional filters"""
        query = self.db.collection(collection)
        
        if filters:
            for field, value in filters.items():
                query = query.where(field, '==', value)
        
        docs = query.stream()
        return {doc.id: doc.to_dict() for doc in docs}

    async def batch_create(self, collection: str, items: List[Dict[str, Any]]) -> List[Any]:
        """Create multiple documents in a batch"""
        batch = self.db.batch()
        doc_refs = []
        
        for item in items:
            doc_ref = self.db.collection(collection).document()
            batch.set(doc_ref, item)
            doc_refs.append(doc_ref)
        
        batch.commit()
        return doc_refs

    async def batch_update(self, collection: str, updates: Dict[str, Dict[str, Any]]) -> None:
        """Update multiple documents in a batch"""
        batch = self.db.batch()
        
        for doc_id, data in updates.items():
            doc_ref = self.db.collection(collection).document(doc_id)
            batch.update(doc_ref, data)
        
        batch.commit()

    async def batch_delete(self, collection: str, doc_ids: List[str]) -> None:
        """Delete multiple documents in a batch"""
        batch = self.db.batch()
        
        for doc_id in doc_ids:
            doc_ref = self.db.collection(collection).document(doc_id)
            batch.delete(doc_ref)
        
        batch.commit() 