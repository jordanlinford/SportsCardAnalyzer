import os
from typing import Optional, BinaryIO
from datetime import datetime, timedelta
import mimetypes
import hashlib
from pathlib import Path

class StorageService:
    """Service for handling file storage operations"""
    
    def __init__(self, storage_path: str = "storage"):
        self.storage_path = storage_path
        self._ensure_storage_path()
    
    def _ensure_storage_path(self):
        """Ensure the storage directory exists"""
        os.makedirs(self.storage_path, exist_ok=True)
    
    def _generate_file_path(self, file_name: str) -> str:
        """Generate a unique file path based on the original file name"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(file_name)
        hash_value = hashlib.md5(f"{name}_{timestamp}".encode()).hexdigest()[:8]
        safe_name = "".join(c for c in name if c.isalnum() or c in "-_")
        return os.path.join(self.storage_path, f"{safe_name}_{hash_value}{ext}")
    
    async def save_file(self, file: BinaryIO, original_filename: str) -> str:
        """
        Save a file to storage
        
        Args:
            file: File-like object containing the file data
            original_filename: Original name of the file
            
        Returns:
            str: Path to the saved file
        """
        try:
            file_path = self._generate_file_path(original_filename)
            
            with open(file_path, 'wb') as f:
                f.write(file.read())
            
            return file_path
            
        except Exception as e:
            print(f"Error saving file: {str(e)}")
            raise
    
    async def get_file(self, file_path: str) -> Optional[BinaryIO]:
        """
        Get a file from storage
        
        Args:
            file_path: Path to the file
            
        Returns:
            Optional[BinaryIO]: File data if found, None otherwise
        """
        try:
            if not os.path.exists(file_path):
                return None
            
            return open(file_path, 'rb')
            
        except Exception as e:
            print(f"Error getting file: {str(e)}")
            return None
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if file was deleted, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            os.remove(file_path)
            return True
            
        except Exception as e:
            print(f"Error deleting file: {str(e)}")
            return False
    
    def get_file_url(self, file_path: str) -> str:
        """
        Get the URL for accessing a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: URL for accessing the file
        """
        return f"file://{os.path.abspath(file_path)}"
    
    def get_mime_type(self, file_path: str) -> str:
        """
        Get the MIME type of a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: MIME type of the file
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream' 