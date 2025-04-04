"""
This module provides access to Firebase services.
It imports and re-exports the initialized Firebase components from firebase_init.py.
"""

from .firebase_init import (
    get_firebase_app,
    get_firestore_client,
    get_pyrebase,
    get_pyrebase_auth,
    initialize_all
)

# Re-export the initialized components
app = get_firebase_app()
db = get_firestore_client()
firebase = get_pyrebase()
pb_auth = get_pyrebase_auth()

# Initialize all components if not already initialized
if app is None or db is None or firebase is None or pb_auth is None:
    initialize_all()
    app = get_firebase_app()
    db = get_firestore_client()
    firebase = get_pyrebase()
    pb_auth = get_pyrebase_auth()

# Define a unique app name
APP_NAME = 'sports-card-analyzer-app'

# Pyrebase Configuration
firebase_config = {
    "apiKey": "AIzaSyAfb2YtBxD5YEWrNpG0J3GN_g0ZfPzsoOE",
    "authDomain": "sports-card-analyzer.firebaseapp.com",
    "databaseURL": "https://sports-card-analyzer.firebaseio.com",
    "projectId": "sports-card-analyzer",
    "storageBucket": "sports-card-analyzer.firebasestorage.app",
    "messagingSenderId": "27312906394",
    "appId": "1:27312906394:web:11296b8bb530daad5a7f23"
}

# DO NOT reassign pb_auth to auth from firebase_admin
# This line was causing the issue:
# pb_auth = auth 