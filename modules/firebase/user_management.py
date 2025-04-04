from typing import Dict, Optional, List
from firebase_admin import auth as admin_auth
from firebase_admin import firestore
from .firebase_init import get_firebase_app, get_firestore_client, get_pyrebase_auth
import requests.exceptions
import firebase_admin
import traceback

class UserManager:
    @staticmethod
    def create_user(email: str, password: str, display_name: str) -> Dict:
        """
        Create a new user with the given email, password, and display name.
        
        Args:
            email: User's email address
            password: User's password
            display_name: User's display name
            
        Returns:
            Dict with success status and user data or error message
        """
        try:
            print("Starting user creation process...")
            
            # Get Firebase Admin SDK app
            print("Getting Firebase Admin SDK app...")
            app = get_firebase_app()
            if app is None:
                print("ERROR: Firebase Admin SDK app is not initialized")
                return {'success': False, 'error': "Firebase Admin SDK not initialized"}
            
            print(f"Using Firebase Admin SDK app: {app.name}")
            
            # Get Firestore client
            print("Getting Firestore client...")
            firestore_client = get_firestore_client()
            if firestore_client is None:
                print("ERROR: Firestore client is not initialized")
                return {'success': False, 'error': "Firestore client not initialized"}
            
            print("Firestore client initialized")
            
            # Get Pyrebase auth
            print("Getting Pyrebase auth...")
            pb_auth = get_pyrebase_auth()
            if pb_auth is None:
                print("ERROR: Pyrebase auth is not initialized")
                return {'success': False, 'error': "Authentication service not initialized"}
            
            print("Pyrebase auth initialized")
            
            # Create user with Firebase Admin SDK
            print(f"Creating user with email: {email}")
            user = admin_auth.create_user(
                email=email,
                password=password,
                display_name=display_name
            )
            print(f"User created with UID: {user.uid}")
            
            # Initialize default preferences
            default_preferences = {
                'display_name': display_name,
                'theme': 'light',
                'currency': 'USD',
                'notifications': True,
                'default_sort': 'date_added',
                'default_view': 'grid',
                'price_alerts': False,
                'market_trends': True,
                'collection_stats': True,
                'defaultGradingCost': 0,
                'defaultMarketplaceFees': 12,
                'defaultShippingCost': 4.25
            }
            
            # Create user document in Firestore
            user_data = {
                'email': email,
                'displayName': display_name,
                'collection': [],  # Initialize empty collection
                'preferences': default_preferences
            }
            
            print(f"Creating user document in Firestore for UID: {user.uid}")
            firestore_client.collection('users').document(user.uid).set(user_data)
            print("User document created successfully")
            
            # Sign in the user to get the auth token
            print("Signing in user to get auth token...")
            try:
                # Use Pyrebase authentication
                auth_user = pb_auth.sign_in_with_email_and_password(email, password)
                print("User signed in successfully with Pyrebase")
            except Exception as auth_error:
                print(f"Error signing in with Pyrebase: {str(auth_error)}")
                print(f"Traceback: {traceback.format_exc()}")
                # Continue without the token if Pyrebase auth fails
                auth_user = {'idToken': None}
            
            return {
                'success': True,
                'user': user_data,
                'uid': user.uid,
                'token': auth_user.get('idToken')
            }
        except requests.exceptions.HTTPError as e:
            error_message = str(e)
            print(f"HTTP Error during user creation: {error_message}")
            if "EMAIL_EXISTS" in error_message:
                return {'success': False, 'error': "Email already exists"}
            elif "WEAK_PASSWORD" in error_message:
                return {'success': False, 'error': "Password should be at least 6 characters"}
            elif "INVALID_EMAIL" in error_message:
                return {'success': False, 'error': "Invalid email format"}
            else:
                return {'success': False, 'error': f"Authentication error: {str(e)}"}
        except Exception as e:
            print(f"Exception during user creation: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def sign_in(email: str, password: str) -> Dict:
        """
        Sign in a user with the given email and password.
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            Dict with success status and user data or error message
        """
        try:
            # Get Pyrebase auth
            print("Getting Pyrebase auth...")
            pb_auth = get_pyrebase_auth()
            if pb_auth is None:
                print("ERROR: Pyrebase auth is not initialized")
                return {'success': False, 'error': "Authentication service not initialized"}
            
            print("Pyrebase auth initialized")
            
            # Get Firestore client
            print("Getting Firestore client...")
            firestore_client = get_firestore_client()
            if firestore_client is None:
                print("ERROR: Firestore client is not initialized")
                return {'success': False, 'error': "Firestore client not initialized"}
            
            print("Firestore client initialized")
            
            # Sign in with Pyrebase
            print(f"Signing in user with email: {email}")
            try:
                auth_user = pb_auth.sign_in_with_email_and_password(email, password)
                print("User signed in successfully with Pyrebase")
                
                # Get user data from Firestore
                print(f"Getting user data from Firestore for UID: {auth_user['localId']}")
                user_doc = firestore_client.collection('users').document(auth_user['localId']).get()
                
                if not user_doc.exists:
                    print(f"User document not found for UID: {auth_user['localId']}")
                    return {'success': False, 'error': "User data not found"}
                
                user_data = user_doc.to_dict()
                print("User data retrieved successfully")
                
                return {
                    'success': True,
                    'user': user_data,
                    'uid': auth_user['localId'],
                    'token': auth_user['idToken']
                }
                
            except requests.exceptions.HTTPError as e:
                error_message = str(e)
                print(f"HTTP Error during sign in: {error_message}")
                if "EMAIL_NOT_FOUND" in error_message:
                    return {'success': False, 'error': "Email not found"}
                elif "INVALID_PASSWORD" in error_message:
                    return {'success': False, 'error': "Invalid password"}
                elif "INVALID_EMAIL" in error_message:
                    return {'success': False, 'error': "Invalid email format"}
                else:
                    return {'success': False, 'error': f"Authentication error: {str(e)}"}
            except Exception as e:
                print(f"Error during sign in: {str(e)}")
                print(f"Traceback: {traceback.format_exc()}")
                return {'success': False, 'error': f"Sign in failed: {str(e)}"}
                
        except Exception as e:
            print(f"Exception during sign in: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_user_data(uid: str) -> Optional[Dict]:
        """
        Get user data from Firestore.
        
        Args:
            uid: User's unique identifier
            
        Returns:
            Dict with user data or None if not found
        """
        try:
            firestore_client = get_firestore_client()
            if firestore_client is None:
                print("ERROR: Firestore client is not initialized")
                return None
                
            user_doc = firestore_client.collection('users').document(uid).get()
            if not user_doc.exists:
                print(f"User document not found for UID: {uid}")
                return None
                
            return user_doc.to_dict()
        except Exception as e:
            print(f"Error getting user data: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return None
    
    @staticmethod
    def update_user_preferences(uid: str, preferences: Dict) -> Dict:
        """
        Update user preferences in Firestore.
        
        Args:
            uid: User's unique identifier
            preferences: Dictionary of preferences to update
            
        Returns:
            Dict with success status and error message if any
        """
        try:
            firestore_client = get_firestore_client()
            if firestore_client is None:
                print("ERROR: Firestore client is not initialized")
                return {'success': False, 'error': "Firestore client not initialized"}
                
            # Ensure numeric values are properly formatted
            formatted_preferences = {
                'defaultGradingCost': float(preferences.get('defaultGradingCost', 0)),
                'defaultMarketplaceFees': float(preferences.get('defaultMarketplaceFees', 12)),
                'defaultShippingCost': float(preferences.get('defaultShippingCost', 4.25))
            }
            
            # Update the preferences in Firestore
            firestore_client.collection('users').document(uid).update({
                'preferences': formatted_preferences
            })
            
            print(f"Updated preferences for user {uid}: {formatted_preferences}")
            return {'success': True}
        except Exception as e:
            print(f"Error updating user preferences: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def save_collection(uid: str, collection_data: List[Dict]) -> Dict:
        """
        Save a collection of cards to Firebase.
        
        Args:
            uid: User ID
            collection_data: List of card dictionaries to save
            
        Returns:
            Dict with success status and error message if any
        """
        try:
            firestore_client = get_firestore_client()
            if firestore_client is None:
                print("ERROR: Firestore client is not initialized")
                return {'success': False, 'error': "Firestore client not initialized"}
                
            # Create a new list for processed items
            processed_data = []
            
            # Process each item individually
            for item in collection_data:
                processed_item = {}
                
                # Process each field
                for key, value in item.items():
                    if value is None:
                        processed_item[key] = ''  # Convert None to empty string
                    elif isinstance(value, (int, float)):
                        processed_item[key] = float(value)  # Convert numbers to float
                    elif isinstance(value, (dict, list)):
                        processed_item[key] = str(value)  # Convert complex objects to strings
                    elif hasattr(value, 'isoformat'):
                        processed_item[key] = value.isoformat()  # Convert dates to ISO format
                    else:
                        processed_item[key] = str(value)  # Convert everything else to string
                
                processed_data.append(processed_item)
            
            # Save to Firebase
            doc_ref = firestore_client.collection('users').document(uid)
            doc_ref.set({
                'collection': processed_data
            }, merge=True)
            
            return {'success': True}
        except Exception as e:
            print(f"Error saving collection: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def save_card(uid: str, card_data: Dict) -> Dict:
        """
        Save a card to the user's collection.
        
        Args:
            uid: User's unique identifier
            card_data: Card data to save
            
        Returns:
            Dict with success status and error message if any
        """
        try:
            firestore_client = get_firestore_client()
            if firestore_client is None:
                print("ERROR: Firestore client is not initialized")
                return {'success': False, 'error': "Firestore client not initialized"}
                
            # Ensure card_data contains only serializable values
            for key, value in card_data.items():
                if isinstance(value, (dict, list)):
                    card_data[key] = str(value)  # Convert complex objects to strings
                elif hasattr(value, 'isoformat'):  # Handle datetime objects
                    card_data[key] = value.isoformat()
            
            user_ref = firestore_client.collection('users').document(uid)
            user_ref.update({
                'savedCards': firestore.ArrayUnion([card_data])
            })
            return {'success': True}
        except Exception as e:
            print(f"Error saving card: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def save_trade(uid: str, trade_data: Dict) -> Dict:
        """
        Save a trade to the user's history.
        
        Args:
            uid: User's unique identifier
            trade_data: Trade data to save
            
        Returns:
            Dict with success status and error message if any
        """
        try:
            firestore_client = get_firestore_client()
            if firestore_client is None:
                print("ERROR: Firestore client is not initialized")
                return {'success': False, 'error': "Firestore client not initialized"}
                
            # Ensure trade_data contains only serializable values
            for key, value in trade_data.items():
                if isinstance(value, (dict, list)):
                    trade_data[key] = str(value)  # Convert complex objects to strings
                elif hasattr(value, 'isoformat'):  # Handle datetime objects
                    trade_data[key] = value.isoformat()
            
            user_ref = firestore_client.collection('users').document(uid)
            user_ref.update({
                'savedTrades': firestore.ArrayUnion([trade_data])
            })
            return {'success': True}
        except Exception as e:
            print(f"Error saving trade: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return {'success': False, 'error': str(e)} 