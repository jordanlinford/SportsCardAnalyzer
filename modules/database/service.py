from typing import Dict, List, Optional
from datetime import datetime
from firebase_admin import firestore
from .models import Card, UserPreferences
from modules.core.firebase_manager import FirebaseManager
import pandas as pd
import base64
import ast
import io
from PIL import Image
import logging
import streamlit as st

logger = logging.getLogger(__name__)

class DatabaseService:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of DatabaseService"""
        if cls._instance is None:
            cls._instance = DatabaseService()
        return cls._instance
        
    def __init__(self):
        """Initialize the database service"""
        self.db = None
        self._initialize_db()

    def _initialize_db(self):
        """Initialize the database connection"""
        try:
            firebase_manager = FirebaseManager.get_instance()
            if not firebase_manager._initialized:
                if not firebase_manager.initialize():
                    logger.error("Failed to initialize Firebase")
                    return
            self.db = firebase_manager.db
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            self.db = None

    def _ensure_db_connection(self) -> bool:
        """Ensure database connection is active"""
        if not self.db:
            self._initialize_db()
        return self.db is not None

    @staticmethod
    def get_user_data(uid: str) -> Optional[Dict]:
        """Get user data from Firestore."""
        try:
            service = DatabaseService.get_instance()
            if not service._ensure_db_connection():
                logger.error("Database connection not available")
                return None

            user_doc = service.db.collection('users').document(uid).get()
            if user_doc.exists:
                return user_doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Error getting user data: {str(e)}")
            return None

    @staticmethod
    def save_user_preferences(uid: str, preferences: Dict) -> bool:
        """Save user preferences to Firestore."""
        try:
            service = DatabaseService.get_instance()
            if not service._ensure_db_connection():
                logger.error("Database connection not available")
                return False

            # Ensure numeric values are properly formatted
            formatted_preferences = {
                'defaultGradingCost': float(preferences.get('defaultGradingCost', 0)),
                'defaultMarketplaceFees': float(preferences.get('defaultMarketplaceFees', 12)),
                'defaultShippingCost': float(preferences.get('defaultShippingCost', 4.25))
            }
            
            # Update the preferences in Firestore
            service.db.collection('users').document(uid).update({
                'preferences': formatted_preferences,
                'last_updated': datetime.now().isoformat()
            })
            
            logger.info(f"Updated preferences for user {uid}: {formatted_preferences}")
            return True
        except Exception as e:
            logger.error(f"Error saving user preferences: {str(e)}")
            return False

    @staticmethod
    def get_user_collection(uid: str) -> List[Card]:
        """Load user's card collection from Firestore."""
        try:
            # Get the Firebase database instance
            service = DatabaseService.get_instance()
            if not service._ensure_db_connection():
                st.error("Database connection not available")
                return []
                
            # Get the user's cards subcollection reference
            cards_ref = service.db.collection('users').document(uid).collection('cards')
            
            # Get all card documents
            card_docs = cards_ref.get()
            
            # Convert documents to Card objects
            cards = []
            for doc in card_docs:
                try:
                    card_data = doc.to_dict()
                    card = Card.from_dict(card_data)
                    cards.append(card)
                except Exception as e:
                    logger.error(f"Error converting card data: {str(e)}")
                    continue
            
            return cards
            
        except Exception as e:
            logger.error(f"Error loading collection: {str(e)}")
            return []

    @staticmethod
    def save_user_collection(uid: str, cards: List[Card]) -> bool:
        """Save user's card collection to Firestore."""
        try:
            service = DatabaseService.get_instance()
            if not service._ensure_db_connection():
                logger.error("Database connection not available")
                return False

            # Get the user's cards subcollection reference
            cards_ref = service.db.collection('users').document(uid).collection('cards')
            
            # Delete all existing cards
            existing_cards = cards_ref.get()
            for card in existing_cards:
                card.reference.delete()
            
            # Add all new cards
            for card in cards:
                # Generate a unique ID for the card based on its attributes
                card_id = f"{card.player_name}_{card.year}_{card.card_set}_{card.card_number}".replace(" ", "_").lower()
                
                # Add the card to the subcollection
                cards_ref.document(card_id).set(card.to_dict())
            
            # Update the user's last_updated timestamp
            user_ref = service.db.collection('users').document(uid)
            user_ref.update({'last_updated': datetime.now().isoformat()})
            
            logger.info(f"Successfully saved {len(cards)} cards to collection")
            return True
            
        except Exception as e:
            logger.error(f"Error in save_user_collection: {str(e)}")
            return False

    @staticmethod
    def add_card_to_collection(uid: str, card: Card) -> bool:
        """Add a card to the user's collection."""
        try:
            service = DatabaseService.get_instance()
            if not service._ensure_db_connection():
                logger.error("Database connection not available")
                return False

            # Get the user's cards subcollection reference
            cards_ref = service.db.collection('users').document(uid).collection('cards')
            
            # Generate a unique ID for the card based on its attributes
            card_id = f"{card.player_name}_{card.year}_{card.card_set}_{card.card_number}".replace(" ", "_").lower()
            
            # Convert card to dictionary and log the data
            card_data = card.to_dict()
            logger.info(f"Attempting to save card with ID: {card_id}")
            logger.debug(f"Card data: {card_data}")
            
            # Add the card to the subcollection
            cards_ref.document(card_id).set(card_data)
            
            # Update the user's last_updated timestamp
            user_ref = service.db.collection('users').document(uid)
            user_ref.update({'last_updated': datetime.now().isoformat()})
            
            logger.info(f"Successfully added card to collection: {card_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error in add_card_to_collection: {str(e)}")
            logger.error(f"Card data that failed to save: {card.to_dict() if card else 'No card data'}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    @staticmethod
    def update_card(uid: str, card: Card) -> bool:
        """Update a card in the user's collection."""
        try:
            service = DatabaseService.get_instance()
            if not service._ensure_db_connection():
                logger.error("Database connection not available")
                return False

            # Get the user's cards subcollection reference
            cards_ref = service.db.collection('users').document(uid).collection('cards')
            
            # Generate the card ID
            card_id = f"{card.player_name}_{card.year}_{card.card_set}_{card.card_number}".replace(" ", "_").lower()
            
            # Update the card document
            cards_ref.document(card_id).set(card.to_dict())
            
            # Update the user's last_updated timestamp
            user_ref = service.db.collection('users').document(uid)
            user_ref.update({'last_updated': datetime.now().isoformat()})
            
            logger.info(f"Successfully updated card: {card_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error in update_card: {str(e)}")
            return False

    @staticmethod
    def delete_card(uid: str, card: Card) -> bool:
        """Delete a card from the user's collection."""
        try:
            service = DatabaseService.get_instance()
            if not service._ensure_db_connection():
                logger.error("Database connection not available")
                return False

            # Get the user's cards subcollection reference
            cards_ref = service.db.collection('users').document(uid).collection('cards')
            
            # Generate the card ID
            card_id = f"{card.player_name}_{card.year}_{card.card_set}_{card.card_number}".replace(" ", "_").lower()
            
            # Delete the card document
            cards_ref.document(card_id).delete()
            
            # Update the user's last_updated timestamp
            user_ref = service.db.collection('users').document(uid)
            user_ref.update({'last_updated': datetime.now().isoformat()})
            
            logger.info(f"Successfully deleted card: {card_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error in delete_card: {str(e)}")
            return False

    @staticmethod
    def save_user_display_cases(uid: str, display_cases: Dict) -> bool:
        """Save user's display cases to Firestore."""
        try:
            print(f"\n=== Saving Display Cases to Firebase ===")
            print(f"User ID: {uid}")
            print(f"Number of display cases to save: {len(display_cases)}")
            
            if not uid:
                print("ERROR: No user ID provided")
                return False
                
            if not display_cases:
                print("ERROR: No display cases to save")
                return False
            
            # Create a serializable copy of the display cases
            serializable_cases = {}
            for name, case in display_cases.items():
                try:
                    print(f"\nProcessing display case: {name}")
                    print(f"Original case data: {case}")
                    
                    # Process cards to ensure they're serializable
                    processed_cards = []
                    for card in case.get('cards', []):
                        try:
                            # Create a new dict with only serializable data
                            processed_card = {}
                            for key, value in card.items():
                                if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                                    processed_card[key] = value
                                else:
                                    # Convert non-serializable types to string
                                    processed_card[key] = str(value)
                            processed_cards.append(processed_card)
                        except Exception as card_error:
                            print(f"Error processing card: {str(card_error)}")
                            print(f"Card data: {card}")
                            continue
                    
                    # Create a serializable display case
                    serializable_case = {
                        'name': str(case.get('name', '')),
                        'description': str(case.get('description', '')),
                        'tags': [str(tag) for tag in case.get('tags', [])],
                        'created_date': str(case.get('created_date', datetime.now().isoformat())),
                        'total_value': float(case.get('total_value', 0.0)),
                        'cards': processed_cards
                    }
                    serializable_cases[name] = serializable_case
                    print(f"Successfully processed display case: {name}")
                except Exception as case_error:
                    print(f"Error processing display case {name}: {str(case_error)}")
                    print(f"Case data: {case}")
                    continue
            
            if not serializable_cases:
                print("ERROR: No valid display cases to save after processing")
                return False
            
            # Get the current document
            user_ref = db.collection('users').document(uid)
            user_doc = user_ref.get()
            
            try:
                # If user document doesn't exist, create it with all required fields
                if not user_doc.exists:
                    print(f"User document for {uid} does not exist. Creating it now.")
                    user_ref.set({
                        'display_cases': serializable_cases,
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat(),
                        'last_updated': datetime.now().isoformat(),
                        'preferences': {
                            'display_name': 'User',
                            'theme': 'light',
                            'currency': 'USD',
                            'notifications': True,
                            'default_sort': 'date_added',
                            'default_view': 'grid',
                            'price_alerts': False,
                            'market_trends': True,
                            'collection_stats': True
                        }
                    })
                    print(f"Created new user document for {uid}")
                else:
                    # Get existing display cases
                    existing_cases = user_doc.to_dict().get('display_cases', {})
                    # Merge with new cases
                    existing_cases.update(serializable_cases)
                    # Update only the display_cases field
                    user_ref.update({
                        'display_cases': existing_cases,
                        'updated_at': datetime.now().isoformat(),
                        'last_updated': datetime.now().isoformat()
                    })
                    print(f"Updated display cases for user {uid}")
                
                print(f"Successfully saved {len(serializable_cases)} display cases")
                return True
            except Exception as save_error:
                print(f"Error during Firebase save operation: {str(save_error)}")
                print(f"Error type: {type(save_error).__name__}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                return False
                
        except Exception as e:
            print(f"Error in save_user_display_cases: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False

    @staticmethod
    def get_user_display_cases(uid: str) -> Dict:
        """Get user's display cases from Firestore."""
        try:
            user_doc = db.collection('users').document(uid).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                if 'display_cases' in user_data:
                    return user_data['display_cases']
            # If user document doesn't exist or doesn't have display_cases, return empty dict
            print(f"No display cases found for user {uid}. Returning empty dictionary.")
            return {}
        except Exception as e:
            print(f"Error getting user display cases: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return {}

    @staticmethod
    def save_display_cases(uid: str, display_cases: Dict) -> bool:
        """Save display cases to Firestore."""
        try:
            # Process display cases to ensure they're serializable
            processed_cases = {}
            for name, case in display_cases.items():
                processed_case = {
                    'name': str(case.get('name', '')),
                    'description': str(case.get('description', '')),
                    'tags': [str(tag) for tag in case.get('tags', [])],
                    'created_date': str(case.get('created_date', datetime.now().isoformat())),
                    'total_value': float(case.get('total_value', 0.0)),
                    'cards': []
                }
                
                # Process cards
                for card in case.get('cards', []):
                    processed_card = {}
                    for key, value in card.items():
                        if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                            processed_card[key] = value
                        else:
                            processed_card[key] = str(value)
                    processed_case['cards'].append(processed_card)
                
                processed_cases[name] = processed_case
            
            # Save to Firestore
            db.collection('users').document(uid).update({
                'display_cases': processed_cases,
                'updated_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            print(f"Error saving display cases: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False

    def process_card_photo(self, photo_data: str) -> str:
        """Process and compress card photo if needed."""
        try:
            if not photo_data:
                return "https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image"
            
            if not (photo_data.startswith('data:image') or photo_data.startswith('http')):
                return "https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image"
            
            # If it's a URL, return as is
            if photo_data.startswith('http'):
                return photo_data
            
            # Process base64 image
            if photo_data.startswith('data:image'):
                try:
                    # Extract base64 data
                    base64_part = photo_data.split(',')[1]
                    img_data = base64.b64decode(base64_part)
                    
                    # Process image with PIL
                    img = Image.open(io.BytesIO(img_data))
                    
                    # Convert to RGB if necessary
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Calculate new size maintaining aspect ratio
                    max_width = 800
                    max_height = 1000
                    ratio = min(max_width/img.size[0], max_height/img.size[1])
                    new_size = (int(img.size[0]*ratio), int(img.size[1]*ratio))
                    img = img.resize(new_size, Image.LANCZOS)
                    
                    # Save with compression
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=85, optimize=True)
                    compressed_data = buffer.getvalue()
                    
                    # Check final size
                    if len(compressed_data) > 1024 * 1024:  # If still over 1MB
                        # Try more aggressive compression
                        buffer = io.BytesIO()
                        img.save(buffer, format='JPEG', quality=60, optimize=True)
                        compressed_data = buffer.getvalue()
                        
                        if len(compressed_data) > 1024 * 1024:
                            print(f"Warning: Image still too large after compression ({len(compressed_data)/1024:.1f}KB)")
                            return "https://placehold.co/300x400/e6e6e6/666666.png?text=Image+Too+Large"
                    
                    # Convert back to base64
                    encoded_image = base64.b64encode(compressed_data).decode()
                    return f"data:image/jpeg;base64,{encoded_image}"
                    
                except Exception as e:
                    print(f"Error processing image: {str(e)}")
                    return "https://placehold.co/300x400/e6e6e6/666666.png?text=Image+Processing+Error"
            
            return "https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Image+Format"
            
        except Exception as e:
            print(f"Error in process_card_photo: {str(e)}")
            return "https://placehold.co/300x400/e6e6e6/666666.png?text=Error+Processing+Image"

    @staticmethod
    def load_user_collection(uid: str) -> List[Card]:
        """Load user's card collection from Firestore."""
        try:
            logger.info(f"Loading user collection for UID: {uid}")
            
            # Get the user's cards subcollection reference
            cards_ref = db.collection('users').document(uid).collection('cards')
            
            # Get all card documents
            card_docs = cards_ref.get()
            
            # Convert documents to Card objects
            cards = []
            successful_cards = 0
            failed_cards = 0
            
            for doc in card_docs:
                try:
                    card_data = doc.to_dict()
                    card = Card.from_dict(card_data)
                    cards.append(card)
                    successful_cards += 1
                except Exception as e:
                    logger.error(f"Error converting card data to Card object: {str(e)}")
                    logger.debug(f"Card data: {card_data}")
                    failed_cards += 1
                    continue
            
            logger.info(f"Successfully loaded {successful_cards} cards from collection")
            if failed_cards > 0:
                logger.warning(f"Failed to load {failed_cards} cards due to conversion errors")
            
            return cards
            
        except Exception as e:
            logger.error(f"Error in load_user_collection: {str(e)}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return []

    @staticmethod
    def remove_card_from_collection(uid: str, card: Card) -> bool:
        """Remove a card from the user's collection."""
        try:
            logger.info(f"Removing card from collection for UID: {uid}")
            
            # Get the user's cards subcollection reference
            cards_ref = db.collection('users').document(uid).collection('cards')
            
            # Generate the card ID
            card_id = f"{card.player_name}_{card.year}_{card.card_set}_{card.card_number}".replace(" ", "_").lower()
            logger.info(f"Generated card ID for removal: {card_id}")
            
            # Delete the card document
            cards_ref.document(card_id).delete()
            
            # Update the user's last_updated timestamp
            user_ref = db.collection('users').document(uid)
            user_ref.update({'last_updated': datetime.now().isoformat()})
            
            logger.info(f"Successfully removed card from collection: {card_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error in remove_card_from_collection: {str(e)}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return False 