import firebase_admin
from firebase_admin import credentials, firestore
from typing import Dict, Any, Optional, List
import json
import os
from pathlib import Path
from dotenv import load_dotenv

class FirebaseService:
    """Service for handling Firebase database operations"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialize()
            self._initialized = True
    
    def _initialize(self):
        """Initialize Firebase connection"""
        try:
            # Load environment variables
            load_dotenv()
            
            # Get credentials from environment variables
            cred_json = os.getenv('FIREBASE_CREDENTIALS')
            if cred_json:
                cred_data = json.loads(cred_json)
            else:
                # Look for credentials file in common locations
                cred_paths = [
                    os.getenv('FIREBASE_CREDENTIALS_PATH'),
                    "firebase_credentials.json",
                    os.path.expanduser("~/.config/firebase/credentials.json"),
                    "/etc/firebase/credentials.json"
                ]
                
                cred_file = None
                for path in cred_paths:
                    if path and os.path.exists(path):
                        cred_file = path
                        break
                
                if not cred_file:
                    raise ValueError("Firebase credentials not found. Set FIREBASE_CREDENTIALS or FIREBASE_CREDENTIALS_PATH environment variable.")
                
                with open(cred_file, 'r') as f:
                    cred_data = json.load(f)
            
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_data)
                firebase_admin.initialize_app(cred)
            
            self.db = firestore.client()
            
        except Exception as e:
            print(f"Error initializing Firebase: {str(e)}")
            raise
    
    async def create_document(self, collection: str, data: Dict[str, Any]) -> str:
        """
        Create a new document in the specified collection
        
        Args:
            collection: Name of the collection
            data: Document data
            
        Returns:
            str: ID of the created document
        """
        try:
            doc_ref = self.db.collection(collection).document()
            doc_ref.set(data)
            return doc_ref.id
            
        except Exception as e:
            print(f"Error creating document: {str(e)}")
            raise
    
    async def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID from the specified collection
        
        Args:
            collection: Name of the collection
            doc_id: ID of the document
            
        Returns:
            Optional[Dict[str, Any]]: Document data if found, None otherwise
        """
        try:
            doc = self.db.collection(collection).document(doc_id).get()
            return doc.to_dict() if doc.exists else None
            
        except Exception as e:
            print(f"Error getting document: {str(e)}")
            raise
    
    async def update_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> None:
        """
        Update a document in the specified collection
        
        Args:
            collection: Name of the collection
            doc_id: ID of the document
            data: Updated document data
        """
        try:
            self.db.collection(collection).document(doc_id).update(data)
            
        except Exception as e:
            print(f"Error updating document: {str(e)}")
            raise
    
    async def delete_document(self, collection: str, doc_id: str) -> bool:
        """
        Delete a document from the specified collection
        
        Args:
            collection: Name of the collection
            doc_id: ID of the document
            
        Returns:
            bool: True if document was deleted, False if not found
        """
        try:
            doc = self.db.collection(collection).document(doc_id)
            if doc.get().exists:
                doc.delete()
                return True
            return False
            
        except Exception as e:
            print(f"Error deleting document: {str(e)}")
            raise
    
    async def list_documents(
        self,
        collection: str,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List documents from the specified collection with optional filters
        
        Args:
            collection: Name of the collection
            filters: Optional dictionary of field-value pairs to filter by
            order_by: Optional field to order results by
            limit: Optional maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of document data
        """
        try:
            query = self.db.collection(collection)
            
            if filters:
                for field, value in filters.items():
                    query = query.where(field, '==', value)
            
            if order_by:
                query = query.order_by(order_by)
            
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            return [doc.to_dict() for doc in docs]
            
        except Exception as e:
            print(f"Error listing documents: {str(e)}")
            raise
    
    async def batch_create(self, collection: str, items: List[Dict[str, Any]]) -> List[str]:
        """
        Create multiple documents in a batch
        
        Args:
            collection: Name of the collection
            items: List of document data
            
        Returns:
            List[str]: List of created document IDs
        """
        try:
            batch = self.db.batch()
            doc_refs = []
            
            for item in items:
                doc_ref = self.db.collection(collection).document()
                batch.set(doc_ref, item)
                doc_refs.append(doc_ref)
            
            batch.commit()
            return [ref.id for ref in doc_refs]
            
        except Exception as e:
            print(f"Error batch creating documents: {str(e)}")
            raise
    
    async def batch_update(self, collection: str, updates: Dict[str, Dict[str, Any]]) -> None:
        """
        Update multiple documents in a batch
        
        Args:
            collection: Name of the collection
            updates: Dictionary mapping document IDs to their updated data
        """
        try:
            batch = self.db.batch()
            
            for doc_id, data in updates.items():
                doc_ref = self.db.collection(collection).document(doc_id)
                batch.update(doc_ref, data)
            
            batch.commit()
            
        except Exception as e:
            print(f"Error batch updating documents: {str(e)}")
            raise
    
    async def batch_delete(self, collection: str, doc_ids: List[str]) -> None:
        """
        Delete multiple documents in a batch
        
        Args:
            collection: Name of the collection
            doc_ids: List of document IDs to delete
        """
        try:
            batch = self.db.batch()
            
            for doc_id in doc_ids:
                doc_ref = self.db.collection(collection).document(doc_id)
                batch.delete(doc_ref)
            
            batch.commit()
            
        except Exception as e:
            print(f"Error batch deleting documents: {str(e)}")
            raise 