import firebase_admin
from firebase_admin import credentials, auth, firestore
import logging

logger = logging.getLogger(__name__)

class FirebaseManager:
    """Manages Firebase initialization and operations."""
    
    _initialized = False
    _auth = None
    _db = None
    
    @staticmethod
    def initialize():
        """Initialize Firebase components if not already initialized."""
        try:
            if not FirebaseManager._initialized:
                # Initialize Firebase Admin SDK
                cred = credentials.Certificate("firebase-credentials.json")
                firebase_admin.initialize_app(cred)
                FirebaseManager._initialized = True
                logger.info("Firebase initialized successfully")
            return True
        except Exception as e:
            if "already exists" in str(e):
                logger.info("Firebase already initialized")
                return True
            logger.error(f"Error initializing Firebase: {str(e)}")
            return False
    
    @staticmethod
    def get_auth():
        """Get Firebase Auth instance."""
        if not FirebaseManager._initialized:
            FirebaseManager.initialize()
        return auth
    
    @staticmethod
    def get_firestore_client():
        """Get Firestore client instance."""
        if not FirebaseManager._initialized:
            FirebaseManager.initialize()
        return firestore.client()
    
    @staticmethod
    def sign_in(email, password):
        """Sign in user with email and password."""
        try:
            user = FirebaseManager.get_auth().sign_in_with_email_and_password(email, password)
            return user
        except Exception as e:
            logger.error(f"Sign in error: {str(e)}")
            raise
    
    @staticmethod
    def sign_up(email, password, display_name):
        """Sign up new user with email and password."""
        try:
            user = FirebaseManager.get_auth().create_user_with_email_and_password(email, password)
            # Update user profile with display name
            FirebaseManager.get_auth().update_profile(user['idToken'], {'displayName': display_name})
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
            FirebaseManager.get_auth().current_user = None
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
            user_ref = db.collection('users').document(uid)
            
            # Update the document
            user_ref.update(profile_data)
            
            # If display name is being updated, also update it in Firebase Auth
            if 'displayName' in profile_data:
                auth = FirebaseManager.get_auth()
                auth.update_user(
                    uid,
                    display_name=profile_data['displayName']
                )
            
            return True
        except Exception as e:
            print(f"Error updating user profile: {str(e)}")
            raise e 