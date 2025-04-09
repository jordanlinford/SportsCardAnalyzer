"""
This module provides access to Firebase services.
It imports and re-exports the initialized Firebase components from FirebaseManager.
"""

from modules.core.firebase_manager import FirebaseManager
import logging

logger = logging.getLogger(__name__)

# Initialize Firebase components
if not FirebaseManager.initialize():
    logger.error("Failed to initialize Firebase")
    raise RuntimeError("Failed to initialize Firebase")

# Get initialized components
app = FirebaseManager.get_firebase_app()
db = FirebaseManager.get_firestore_client()
auth = FirebaseManager.get_auth()

# Define a unique app name
APP_NAME = 'sports-card-analyzer-app'