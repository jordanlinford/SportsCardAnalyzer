import firebase_admin
from firebase_admin import credentials, firestore, auth
import pyrebase
import os
import traceback
import sys

# Define a unique app name
APP_NAME = 'sports-card-analyzer-app'

# Pyrebase Configuration
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyAfb2YtBxD5YEWrNpG0J3GN_g0ZfPzsoOE",
    "authDomain": "sports-card-analyzer.firebaseapp.com",
    "databaseURL": "https://sports-card-analyzer.firebaseio.com",
    "projectId": "sports-card-analyzer",
    "storageBucket": "sports-card-analyzer.firebasestorage.app",
    "messagingSenderId": "27312906394",
    "appId": "1:27312906394:web:11296b8bb530daad5a7f23"
}

# Global variables to store initialized instances
_firebase_app = None
_firestore_client = None
_pyrebase_instance = None
_pyrebase_auth = None

def initialize_firebase_admin():
    """
    Initialize Firebase Admin SDK with proper error handling.
    Returns the initialized app or None if initialization fails.
    """
    global _firebase_app
    
    try:
        # Check if app already exists
        try:
            _firebase_app = firebase_admin.get_app(name=APP_NAME)
            print(f"Using existing Firebase Admin SDK app: {APP_NAME}")
            return _firebase_app
        except ValueError:
            # App doesn't exist, initialize it
            print("Initializing new Firebase Admin SDK app...")
            
            # Check if service account file exists
            service_account_path = 'firebase_key.json'
            if not os.path.exists(service_account_path):
                # Try alternate locations
                alternate_paths = [
                    'modules/firebase/serviceAccountKey.json',
                    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'firebase_key.json')
                ]
                
                for path in alternate_paths:
                    if os.path.exists(path):
                        service_account_path = path
                        break
                else:
                    error_msg = f"Service account file not found at {service_account_path} or any alternate locations"
                    print(f"Error: {error_msg}")
                    raise FileNotFoundError(error_msg)
            
            print(f"Using service account at: {service_account_path}")
            
            # Initialize the app
            cred = credentials.Certificate(service_account_path)
            _firebase_app = firebase_admin.initialize_app(cred, {
                'projectId': 'sports-card-analyzer',
                'storageBucket': 'sports-card-analyzer.firebasestorage.app'
            }, name=APP_NAME)
            
            print(f"Successfully initialized Firebase Admin SDK app: {APP_NAME}")
            return _firebase_app
    except Exception as e:
        print(f"Error initializing Firebase Admin SDK: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        _firebase_app = None
        return None

def initialize_firestore():
    """
    Initialize Firestore client with proper error handling.
    Returns the initialized client or None if initialization fails.
    """
    global _firestore_client, _firebase_app
    
    try:
        # Ensure Firebase Admin SDK is initialized
        if _firebase_app is None:
            _firebase_app = initialize_firebase_admin()
            if _firebase_app is None:
                raise Exception("Failed to initialize Firebase Admin SDK")
        
        # Initialize Firestore client
        _firestore_client = firestore.client(_firebase_app)
        print("Firestore client initialized successfully")
        return _firestore_client
    except Exception as e:
        print(f"Error initializing Firestore client: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        _firestore_client = None
        return None

def initialize_pyrebase():
    """
    Initialize Pyrebase with proper error handling.
    Returns the initialized Pyrebase instance or None if initialization fails.
    """
    global _pyrebase_instance, _pyrebase_auth
    
    try:
        # Initialize Pyrebase
        print("Initializing Pyrebase...")
        
        # Get the named app
        app = get_firebase_app()
        if app is None:
            print("ERROR: Firebase Admin SDK app is not initialized")
            return None
            
        print(f"Using Firebase Admin SDK app: {app.name}")
        
        # Now initialize Pyrebase
        print("Initializing Pyrebase with config...")
        _pyrebase_instance = pyrebase.initialize_app(FIREBASE_CONFIG)
        _pyrebase_auth = _pyrebase_instance.auth()
        print("Pyrebase initialized successfully")
        return _pyrebase_instance
    except Exception as e:
        print(f"Error initializing Pyrebase: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        _pyrebase_instance = None
        _pyrebase_auth = None
        return None

def get_firebase_app():
    """
    Get the initialized Firebase Admin SDK app.
    If not initialized, attempts to initialize it.
    """
    global _firebase_app
    if _firebase_app is None:
        _firebase_app = initialize_firebase_admin()
    return _firebase_app

def get_firestore_client():
    """
    Get the initialized Firestore client.
    If not initialized, attempts to initialize it.
    """
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = initialize_firestore()
    return _firestore_client

def get_pyrebase():
    """
    Get the initialized Pyrebase instance.
    If not initialized, attempts to initialize it.
    """
    global _pyrebase_instance
    if _pyrebase_instance is None:
        _pyrebase_instance = initialize_pyrebase()
    return _pyrebase_instance

def get_pyrebase_auth():
    """
    Get the initialized Pyrebase auth instance.
    If not initialized, attempts to initialize it.
    """
    global _pyrebase_auth
    if _pyrebase_auth is None:
        firebase = get_pyrebase()
        if firebase:
            _pyrebase_auth = firebase.auth()
    return _pyrebase_auth

def initialize_all():
    """
    Initialize all Firebase components in the correct order.
    Returns True if all components are initialized successfully, False otherwise.
    """
    try:
        print("Initializing all Firebase components...")
        
        # Initialize Firebase Admin SDK first
        app = initialize_firebase_admin()
        if app is None:
            raise Exception("Failed to initialize Firebase Admin SDK")
        
        # Initialize Firestore
        db = initialize_firestore()
        if db is None:
            raise Exception("Failed to initialize Firestore")
        
        # Initialize Pyrebase
        firebase = initialize_pyrebase()
        if firebase is None:
            raise Exception("Failed to initialize Pyrebase")
        
        print("All Firebase components initialized successfully")
        return True
    except Exception as e:
        print(f"Error initializing Firebase components: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

# Initialize all components when this module is imported
initialize_all() 