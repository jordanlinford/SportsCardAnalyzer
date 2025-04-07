import firebase_admin
from firebase_admin import credentials, firestore, auth

class FirebaseManager:
    """Manages Firebase operations for the application"""
    
    _instance = None
    _initialized = False
    
    @classmethod
    def initialize(cls, cred_path=None):
        """Initialize Firebase with credentials"""
        if not cls._initialized:
            try:
                if cred_path:
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                else:
                    firebase_admin.initialize_app()
                cls._initialized = True
            except Exception as e:
                print(f"Error initializing Firebase: {str(e)}")
                raise e
    
    @staticmethod
    def get_firestore_client():
        """Get Firestore client instance"""
        return firestore.client()
    
    @staticmethod
    def get_auth_client():
        """Get Firebase Auth client instance"""
        return auth
    
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
                auth = FirebaseManager.get_auth_client()
                auth.update_user(
                    uid,
                    display_name=profile_data['displayName']
                )
            
            return True
        except Exception as e:
            print(f"Error updating user profile: {str(e)}")
            raise e 