import firebase_admin
from firebase_admin import credentials, auth, firestore
import pyrebase
import os
import logging
from dotenv import load_dotenv
import time
from typing import Optional, Dict, Any
from datetime import datetime
import atexit

logger = logging.getLogger(__name__)

class FirebaseManager:
    """Manages Firebase initialization and operations."""
    
    _instance = None
    _initialized = False
    _auth = None
    _db = None
    _firebase = None
    _firebase_app = None
    _current_user = None
    _max_retries = 3
    _retry_delay = 1  # seconds
    _last_connection_check = 0
    _connection_check_interval = 300  # 5 minutes
    
    @classmethod
    def get_instance(cls) -> 'FirebaseManager':
        """Get singleton instance of FirebaseManager"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize Firebase connection if not already initialized"""
        self._logger = logging.getLogger(__name__)
        if not FirebaseManager._initialized:
            self.initialize()
        
        # Register cleanup handler
        atexit.register(self.cleanup)

    def cleanup(self):
        """Clean up Firebase resources"""
        try:
            if self._firebase_app:
                firebase_admin.delete_app(self._firebase_app)
                self._firebase_app = None
                self._initialized = False
                self._auth = None
                self._db = None
                self._logger.info("Successfully cleaned up Firebase resources")
        except Exception as e:
            self._logger.error(f"Error during Firebase cleanup: {str(e)}")

    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()

    @classmethod
    def initialize(cls) -> bool:
        """Initialize Firebase connection"""
        try:
            if cls._initialized:
                return True

            # Load environment variables
            load_dotenv()

            # Initialize Firebase Admin SDK
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": os.getenv('FIREBASE_PROJECT_ID'),
                "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
                "private_key": os.getenv('FIREBASE_PRIVATE_KEY').replace("\\n", "\n"),
                "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
                "client_id": os.getenv('FIREBASE_CLIENT_ID'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_X509_CERT_URL')
            })

            try:
                cls._firebase_app = firebase_admin.get_app()
                logger.info("Using existing Firebase Admin SDK app")
            except ValueError:
                cls._firebase_app = firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")

            cls._db = firestore.client()
            cls._auth = auth.Client(cls._firebase_app)

            # Initialize Pyrebase client
            firebase_config = {
                "apiKey": os.getenv("FIREBASE_API_KEY"),
                "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
                "projectId": os.getenv("FIREBASE_PROJECT_ID"),
                "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
                "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
                "appId": os.getenv("FIREBASE_APP_ID"),
                "databaseURL": f"https://{os.getenv('FIREBASE_PROJECT_ID')}.firebaseio.com"
            }

            # Verify all required config values are present
            required_keys = ["apiKey", "authDomain", "projectId", "storageBucket", "messagingSenderId", "appId", "databaseURL"]
            missing_keys = [key for key in required_keys if not firebase_config[key]]
            if missing_keys:
                raise ValueError(f"Missing required Firebase config values: {', '.join(missing_keys)}")

            # Initialize Pyrebase
            cls._firebase = pyrebase.initialize_app(firebase_config)
            cls._initialized = True
            logger.info("Firebase initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing Firebase: {str(e)}")
            return False

    @property
    def db(self):
        """Get Firestore database instance"""
        if not self._initialized:
            raise RuntimeError("Firebase not initialized")
        return self._db

    def get_firestore_client(self):
        """Get Firestore client"""
        return self.db

    def collection(self, name: str):
        """Get a collection reference"""
        return self.db.collection(name)

    def document(self, collection: str, doc_id: str):
        """Get a document reference"""
        return self.db.collection(collection).document(doc_id)

    def batch(self):
        """Get a new write batch"""
        return self.db.batch()

    def transaction(self):
        """Get a new transaction"""
        return self.db.transaction()

    def close(self):
        """Close Firebase connection"""
        if self._firebase_app:
            firebase_admin.delete_app(self._firebase_app)
            self._initialized = False
            self._db = None
            self._firebase_app = None
            self._auth = None

    @classmethod
    def check_connection(cls) -> bool:
        """Check if Firebase connection is active and reconnect if needed"""
        current_time = time.time()
        
        # Only check connection every 5 minutes
        if current_time - cls._last_connection_check < cls._connection_check_interval:
            return cls._initialized

        cls._last_connection_check = current_time

        try:
            if not cls._initialized or not cls._db:
                return cls.initialize()

            # Try a simple operation to verify connection
            cls._db.collection('_connection_test').limit(1).get()
            return True

        except Exception as e:
            logger.error(f"Firebase connection check failed: {str(e)}")
            cls._initialized = False
            return cls.initialize()

    @classmethod
    def set_current_user(cls, user_data: dict):
        """Set current user data"""
        cls._current_user = user_data

    @classmethod
    def get_current_user_id(cls) -> Optional[str]:
        """Get current user ID"""
        if cls._current_user:
            return cls._current_user.get('localId')
        return None

    @staticmethod
    def _check_connection() -> bool:
        """Check if Firebase connection is still valid."""
        current_time = time.time()
        if current_time - FirebaseManager._last_connection_check < FirebaseManager._connection_check_interval:
            return True
            
        try:
            # Simple Firestore operation to check connection
            if FirebaseManager._db:
                FirebaseManager._db.collection('users').limit(1).get()
                FirebaseManager._last_connection_check = current_time
                return True
        except Exception as e:
            logger.warning(f"Connection check failed: {str(e)}")
            return False
        return False
    
    @staticmethod
    def _initialize_firebase_admin() -> bool:
        """Initialize Firebase Admin SDK with proper error handling."""
        try:
            # Check if app already exists
            try:
                FirebaseManager._firebase_app = firebase_admin.get_app()
                logger.info("Using existing Firebase Admin SDK app")
                return True
            except ValueError:
                # Initialize new app
                cred = credentials.Certificate({
                    "type": "service_account",
                    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
                    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL")
                })
                FirebaseManager._firebase_app = firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
                return True
        except Exception as e:
            logger.error(f"Error initializing Firebase Admin SDK: {str(e)}")
            return False
    
    @staticmethod
    def _initialize_firestore() -> bool:
        """Initialize Firestore with retry mechanism and connection monitoring."""
        for attempt in range(FirebaseManager._max_retries):
            try:
                FirebaseManager._db = firestore.client()
                if FirebaseManager._db:
                    # Verify connection
                    FirebaseManager._db.collection('users').limit(1).get()
                    logger.info("Firestore client initialized successfully")
                    FirebaseManager._last_connection_check = time.time()
                    return True
                else:
                    logger.warning(f"Firestore client initialization attempt {attempt + 1} failed")
                    if attempt < FirebaseManager._max_retries - 1:
                        time.sleep(FirebaseManager._retry_delay)
            except Exception as e:
                logger.warning(f"Firestore client initialization attempt {attempt + 1} failed: {str(e)}")
                if attempt < FirebaseManager._max_retries - 1:
                    time.sleep(FirebaseManager._retry_delay)
                else:
                    logger.error(f"Failed to initialize Firestore client after {FirebaseManager._max_retries} attempts")
                    return False
        return False
    
    @staticmethod
    def _initialize_firebase_client() -> bool:
        """Initialize Firebase Client SDK with proper configuration validation."""
        try:
            firebase_config = {
                "apiKey": os.getenv("FIREBASE_API_KEY"),
                "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
                "projectId": os.getenv("FIREBASE_PROJECT_ID"),
                "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
                "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
                "appId": os.getenv("FIREBASE_APP_ID"),
                "databaseURL": f"https://{os.getenv('FIREBASE_PROJECT_ID')}.firebaseio.com"
            }
            
            # Verify all required config values are present
            required_keys = ["apiKey", "authDomain", "projectId", "storageBucket", "messagingSenderId", "appId", "databaseURL"]
            missing_keys = [key for key in required_keys if not firebase_config[key]]
            if missing_keys:
                raise ValueError(f"Missing required Firebase config values: {', '.join(missing_keys)}")
            
            # Initialize Pyrebase
            FirebaseManager._firebase = pyrebase.initialize_app(firebase_config)
            FirebaseManager._auth = FirebaseManager._firebase.auth()
            return True
        except Exception as e:
            logger.error(f"Error initializing Firebase Client SDK: {str(e)}")
            return False
    
    @staticmethod
    def get_firebase_app():
        """Get Firebase Admin SDK app instance."""
        if not FirebaseManager._initialized:
            if not FirebaseManager.initialize():
                raise RuntimeError("Failed to initialize Firebase")
        if not FirebaseManager._firebase_app:
            raise RuntimeError("Firebase Admin SDK app is not initialized")
        return FirebaseManager._firebase_app
    
    @staticmethod
    def get_auth():
        """Get Firebase Auth instance."""
        if not FirebaseManager._initialized:
            if not FirebaseManager.initialize():
                raise RuntimeError("Failed to initialize Firebase")
        if not FirebaseManager._auth:
            raise RuntimeError("Firebase Auth is not initialized")
        return FirebaseManager._auth
    
    @staticmethod
    def get_current_user():
        """Get current user data"""
        return FirebaseManager._current_user
    
    @staticmethod
    def get_collection(collection_name):
        """Get a Firestore collection with proper error handling."""
        try:
            # Ensure Firebase is initialized
            if not FirebaseManager.initialize():
                logger.error("Failed to initialize Firebase")
                return None
            
            # Ensure Firestore client is available
            if not FirebaseManager._db:
                logger.error("Firestore client not initialized")
                return None
            
            # Get the collection
            collection = FirebaseManager._db.collection(collection_name)
            if not collection:
                logger.error(f"Failed to access collection: {collection_name}")
                return None
            
            return collection
            
        except Exception as e:
            logger.error(f"Error accessing collection {collection_name}: {str(e)}")
            return None
    
    def sign_in(self, email: str, password: str) -> dict:
        """Sign in a user with email and password"""
        try:
            if not self._initialized:
                raise RuntimeError("Firebase not initialized")

            # Sign in user with Pyrebase
            user = self._firebase.auth().sign_in_with_email_and_password(email, password)
            
            # Get user data from Firestore
            user_doc = self.db.collection('users').document(user['localId']).get()
            
            # Create user document if it doesn't exist
            if not user_doc.exists:
                user_data = {
                    'email': email,
                    'display_name': email.split('@')[0],
                    'created_at': datetime.now(),
                    'last_login': datetime.now()
                }
                self.db.collection('users').document(user['localId']).set(user_data)
            else:
                # Get the Firestore user profile data
                user_profile = user_doc.to_dict()
                
                # Merge the Firestore profile data with the auth data
                # This is the key change - preserve custom profile fields
                for key, value in user_profile.items():
                    if key not in user:
                        user[key] = value
                
                # Update last login
                self.db.collection('users').document(user['localId']).update({
                    'last_login': datetime.now()
                })

            # Set current user
            self.set_current_user(user)

            return user

        except Exception as e:
            logger.error(f"Error signing in user: {str(e)}")
            raise

    def sign_up(self, email: str, password: str, display_name: str = None) -> dict:
        """Create a new user with email and password"""
        try:
            if not self._initialized:
                raise RuntimeError("Firebase not initialized")

            # Create user with Pyrebase
            user = self._firebase.auth().create_user_with_email_and_password(email, password)
            
            # Create user document in Firestore
            user_data = {
                'email': email,
                'display_name': display_name or email.split('@')[0],
                'created_at': datetime.now(),
                'last_login': datetime.now(),
                'preferences': {
                    'theme': 'light',
                    'notifications': True
                }
            }
            self.db.collection('users').document(user['localId']).set(user_data)

            # Set current user
            self.set_current_user(user)

            return user

        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise

    def sign_out(self) -> bool:
        """Sign out the current user"""
        try:
            self._current_user = None
            return True
        except Exception as e:
            logger.error(f"Error signing out user: {str(e)}")
            return False

    def delete_user(self, uid: str) -> bool:
        """Delete a user and their data"""
        try:
            if not self._initialized:
                raise RuntimeError("Firebase not initialized")

            # Delete user from Firebase Auth
            auth.delete_user(uid)

            # Delete user document from Firestore
            self.db.collection('users').document(uid).delete()

            return True

        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            return False

    def update_user(self, uid: str, data: dict) -> bool:
        """Update user data in Firestore"""
        try:
            if not self._initialized:
                raise RuntimeError("Firebase not initialized")

            # Update user document
            self.db.collection('users').document(uid).update(data)
            return True

        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            return False

    def update_card(self, uid: str, card_id: str, updated_data: dict) -> bool:
        """Update a card in the user's collection
        
        Args:
            uid: User ID
            card_id: Card ID (in format player_name_year_set_number)
            updated_data: Updated card data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self._initialized:
                if not self.initialize():
                    logger.error("Firebase not initialized")
                    return False

            # Get the user's cards collection reference
            cards_ref = self.db.collection('users').document(uid).collection('cards')
            
            # Update the card
            cards_ref.document(card_id).set(updated_data)
            
            # Update the user's last_modified timestamp
            self.db.collection('users').document(uid).update({
                'last_modified': datetime.now().isoformat(),
                'collection_version': firestore.Increment(1)  # Increment version number
            })
            
            logger.info(f"Card updated successfully: {card_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating card: {str(e)}")
            return False

    def sign_in_with_google(self):
        """Sign in user with Google."""
        try:
            if not self._initialized:
                raise RuntimeError("Firebase not initialized")
                
            # This is a placeholder - actual implementation would use Firebase UI
            # or a custom OAuth flow
            raise NotImplementedError("Google sign-in not implemented yet")
        except Exception as e:
            logger.error(f"Google sign-in error: {str(e)}")
            raise
    
    @staticmethod
    def update_user_profile(uid, profile_data):
        """Update user profile in Firebase"""
        try:
            # Update user profile in Firestore
            db = FirebaseManager.get_instance().db
            if not db:
                raise RuntimeError("Firestore client is not initialized")
            user_ref = db.collection('users').document(uid)
            
            # Update the document
            user_ref.update(profile_data)
            
            # If display name is being updated, also update it in Firebase Auth
            if 'displayName' in profile_data:
                auth.update_user(uid, display_name=profile_data['displayName'])
            
            return True
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            return False

    def is_initialized(self):
        """Check if Firebase is initialized"""
        return FirebaseManager._initialized
        
    @staticmethod
    def is_initialized_static():
        """Static method to check if Firebase is initialized"""
        return FirebaseManager._initialized 