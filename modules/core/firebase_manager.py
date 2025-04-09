import firebase_admin
from firebase_admin import credentials, auth, firestore
import pyrebase
import os
import logging
from dotenv import load_dotenv
import time

logger = logging.getLogger(__name__)

class FirebaseManager:
    """Manages Firebase initialization and operations."""
    
    _initialized = False
    _auth = None
    _db = None
    _firebase = None
    _firebase_app = None
    _current_user = None
    _max_retries = 3
    _retry_delay = 1  # seconds
    
    @staticmethod
    def initialize():
        """Initialize Firebase components if not already initialized."""
        try:
            if not FirebaseManager._initialized:
                logger.info("Starting Firebase initialization...")
                
                # Load environment variables
                load_dotenv()
                
                # Initialize Firebase Admin SDK
                try:
                    # Check if app already exists
                    try:
                        FirebaseManager._firebase_app = firebase_admin.get_app()
                        logger.info("Using existing Firebase Admin SDK app")
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
                except Exception as e:
                    logger.error(f"Error initializing Firebase Admin SDK: {str(e)}")
                    raise
                
                # Initialize Firestore with retry mechanism
                for attempt in range(FirebaseManager._max_retries):
                    try:
                        FirebaseManager._db = firestore.client()
                        if FirebaseManager._db:
                            logger.info("Firestore client initialized successfully")
                            break
                        else:
                            logger.warning(f"Firestore client initialization attempt {attempt + 1} failed")
                            if attempt < FirebaseManager._max_retries - 1:
                                time.sleep(FirebaseManager._retry_delay)
                    except Exception as e:
                        logger.warning(f"Firestore client initialization attempt {attempt + 1} failed: {str(e)}")
                        if attempt < FirebaseManager._max_retries - 1:
                            time.sleep(FirebaseManager._retry_delay)
                        else:
                            raise RuntimeError(f"Failed to initialize Firestore client after {FirebaseManager._max_retries} attempts")
                
                if not FirebaseManager._db:
                    raise RuntimeError("Failed to initialize Firestore client")
                
                # Initialize Firebase Client SDK
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
                
                FirebaseManager._initialized = True
                logger.info("Firebase initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing Firebase: {str(e)}")
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
        """Get the current authenticated user."""
        return FirebaseManager._current_user
    
    @staticmethod
    def get_user_id():
        """Get the current user's ID."""
        if FirebaseManager._current_user:
            return FirebaseManager._current_user.get('localId')
        return None
    
    @staticmethod
    def get_firestore_client():
        """Get Firestore client instance."""
        try:
            # Ensure Firebase is initialized
            if not FirebaseManager.initialize():
                logger.error("Failed to initialize Firebase")
                return None
            
            # Ensure Firestore client is available
            if not FirebaseManager._db:
                logger.error("Firestore client not initialized")
                return None
            
            return FirebaseManager._db
            
        except Exception as e:
            logger.error(f"Error getting Firestore client: {str(e)}")
            return None
    
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
    
    @staticmethod
    def sign_in(email, password):
        """Sign in user with email and password."""
        try:
            auth = FirebaseManager.get_auth()
            if not auth:
                raise RuntimeError("Firebase Auth is not initialized")
            user = auth.sign_in_with_email_and_password(email, password)
            FirebaseManager._current_user = user
            return user
        except Exception as e:
            logger.error(f"Sign in error: {str(e)}")
            raise
    
    @staticmethod
    def sign_up(email, password, display_name):
        """Sign up new user with email and password."""
        try:
            auth = FirebaseManager.get_auth()
            if not auth:
                raise RuntimeError("Firebase Auth is not initialized")
            user = auth.create_user_with_email_and_password(email, password)
            FirebaseManager._current_user = user
            # Update user profile with display name
            auth.update_profile(user['idToken'], {'displayName': display_name})
            return user
        except Exception as e:
            logger.error(f"Sign up error: {str(e)}")
            raise
    
    @staticmethod
    def sign_in_with_google():
        """Sign in user with Google."""
        try:
            # This is a placeholder - actual implementation would use Firebase UI
            # or a custom OAuth flow
            raise NotImplementedError("Google sign-in not implemented yet")
        except Exception as e:
            logger.error(f"Google sign-in error: {str(e)}")
            raise
    
    @staticmethod
    def sign_out():
        """Sign out current user."""
        try:
            auth = FirebaseManager.get_auth()
            if not auth:
                raise RuntimeError("Firebase Auth is not initialized")
            FirebaseManager._current_user = None
            return True
        except Exception as e:
            logger.error(f"Sign out error: {str(e)}")
            return False
    
    @staticmethod
    def update_user_profile(uid, profile_data):
        """Update user profile in Firebase"""
        try:
            # Update user profile in Firestore
            db = FirebaseManager.get_firestore_client()
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