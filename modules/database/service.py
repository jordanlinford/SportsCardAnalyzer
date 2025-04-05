from typing import Dict, List, Optional
from datetime import datetime
from firebase_admin import firestore
from .models import Card, UserPreferences
from ..firebase.config import db
import pandas as pd
import base64
import ast

class DatabaseService:
    @staticmethod
    def get_user_data(uid: str) -> Optional[Dict]:
        """Get user data from Firestore."""
        try:
            user_doc = db.collection('users').document(uid).get()
            if user_doc.exists:
                return user_doc.to_dict()
            return None
        except Exception as e:
            print(f"Error getting user data: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return None

    @staticmethod
    def save_user_preferences(uid: str, preferences: Dict) -> bool:
        """Save user preferences to Firestore."""
        try:
            # Ensure numeric values are properly formatted
            formatted_preferences = {
                'defaultGradingCost': float(preferences.get('defaultGradingCost', 0)),
                'defaultMarketplaceFees': float(preferences.get('defaultMarketplaceFees', 12)),
                'defaultShippingCost': float(preferences.get('defaultShippingCost', 4.25))
            }
            
            # Update the preferences in Firestore
            db.collection('users').document(uid).update({
                'preferences': formatted_preferences
            })
            
            print(f"Updated preferences for user {uid}: {formatted_preferences}")
            return True
        except Exception as e:
            print(f"Error saving user preferences: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False

    @staticmethod
    def get_user_collection(uid: str) -> List[Card]:
        """Get user's card collection from Firestore."""
        try:
            user_doc = db.collection('users').document(uid).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                if 'collection' in user_data:
                    return [Card.from_dict(card_data) for card_data in user_data['collection']]
            return []
        except Exception as e:
            print(f"Error getting user collection: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return []

    @staticmethod
    def save_user_collection(uid: str, cards: List[Card]) -> bool:
        """Save user's card collection to Firestore."""
        try:
            # Convert all cards to a simple dict format that Firestore can handle
            collection_data = []
            for card in cards:
                try:
                    # Handle both Card objects and dictionary records
                    if isinstance(card, dict):
                        # Validate photo data
                        photo = card.get('photo', '')
                        if photo:
                            try:
                                # Validate base64 string format
                                if not photo.startswith('data:image'):
                                    print(f"Warning: Invalid photo data format for card {card.get('player_name', 'Unknown')}")
                                    photo = ''
                                else:
                                    # Validate base64 content
                                    try:
                                        base64_part = photo.split(',')[1]
                                        # Check size before decoding
                                        if len(base64_part) > 500 * 1024:  # 500KB limit
                                            print(f"Warning: Photo data too large for card {card.get('player_name', 'Unknown')}")
                                            photo = ''
                                        else:
                                            base64.b64decode(base64_part)
                                    except Exception as e:
                                        print(f"Warning: Invalid base64 image data for card {card.get('player_name', 'Unknown')}. Error: {str(e)}")
                                        photo = ''
                            except Exception as e:
                                print(f"Warning: Error validating photo data for card {card.get('player_name', 'Unknown')}. Error: {str(e)}")
                                photo = ''
                        
                        # Convert dictionary record to proper format
                        card_dict = {
                            'player_name': str(card.get('player_name', '')),
                            'year': str(card.get('year', '')),
                            'card_set': str(card.get('card_set', '')),
                            'card_number': str(card.get('card_number', '')),
                            'variation': str(card.get('variation', '')),
                            'condition': str(card.get('condition', '')),
                            'purchase_price': float(card.get('purchase_price', 0.0)),
                            'purchase_date': str(card.get('purchase_date', datetime.now().isoformat())),
                            'current_value': float(card.get('current_value', 0.0)),
                            'last_updated': str(card.get('last_updated', datetime.now().isoformat())),
                            'notes': str(card.get('notes', '')),
                            'photo': photo,
                            'roi': float(card.get('roi', 0.0)),
                            'tags': [str(tag) for tag in card.get('tags', [])]
                        }
                    else:
                        # Validate photo data for Card object
                        photo = card.photo
                        if photo:
                            try:
                                # Validate base64 string format
                                if not photo.startswith('data:image'):
                                    print(f"Warning: Invalid photo data format for card {card.player_name}")
                                    photo = ''
                                else:
                                    # Validate base64 content
                                    try:
                                        base64_part = photo.split(',')[1]
                                        # Check size before decoding
                                        if len(base64_part) > 500 * 1024:  # 500KB limit
                                            print(f"Warning: Photo data too large for card {card.player_name}")
                                            photo = ''
                                        else:
                                            base64.b64decode(base64_part)
                                    except Exception as e:
                                        print(f"Warning: Invalid base64 image data for card {card.player_name}. Error: {str(e)}")
                                        photo = ''
                            except Exception as e:
                                print(f"Warning: Error validating photo data for card {card.player_name}. Error: {str(e)}")
                                photo = ''
                        
                        # Convert Card object to dict
                        card_dict = {
                            'player_name': str(card.player_name),
                            'year': str(card.year),
                            'card_set': str(card.card_set),
                            'card_number': str(card.card_number),
                            'variation': str(card.variation),
                            'condition': str(card.condition.value),
                            'purchase_price': float(card.purchase_price),
                            'purchase_date': card.purchase_date.isoformat(),
                            'current_value': float(card.current_value),
                            'last_updated': card.last_updated.isoformat(),
                            'notes': str(card.notes),
                            'photo': photo,
                            'roi': float(card.roi),
                            'tags': [str(tag) for tag in card.tags]
                        }
                    
                    # Check total document size before adding
                    doc_size = len(str(card_dict).encode('utf-8')) / 1024  # Size in KB
                    if doc_size > 900:  # Warning if approaching 1MB limit
                        print(f"Warning: Card document for {card_dict['player_name']} is {doc_size:.1f}KB. Consider reducing size.")
                    
                    collection_data.append(card_dict)
                except Exception as card_error:
                    print(f"Error processing card: {str(card_error)}")
                    import traceback
                    print(f"Traceback: {traceback.format_exc()}")
                    continue

            if not collection_data:
                print("No valid cards to save")
                return False

            # Get current collection
            user_doc = db.collection('users').document(uid).get()
            
            try:
                if user_doc.exists:
                    # Update existing collection
                    db.collection('users').document(uid).update({
                        'collection': collection_data,
                        'updated_at': datetime.now().isoformat()
                    })
                    print(f"Successfully updated collection with {len(collection_data)} cards")
                else:
                    # Create new collection
                    db.collection('users').document(uid).set({
                        'collection': collection_data,
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    })
                    print(f"Successfully created new collection with {len(collection_data)} cards")
                return True
            except Exception as save_error:
                print(f"Error saving to Firestore: {str(save_error)}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                return False

        except Exception as e:
            print(f"Error in save_user_collection: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False

    @staticmethod
    def add_card_to_collection(uid: str, card: Card) -> bool:
        """Add a single card to user's collection."""
        try:
            user_ref = db.collection('users').document(uid)
            user_ref.update({
                'collection': firestore.ArrayUnion([card.to_dict()])
            })
            return True
        except Exception as e:
            print(f"Error adding card to collection: {str(e)}")
            return False

    @staticmethod
    def update_card_in_collection(uid: str, card: Card) -> bool:
        """Update a card in user's collection."""
        try:
            user_ref = db.collection('users').document(uid)
            user_doc = user_ref.get()
            if user_doc.exists:
                collection = user_doc.to_dict().get('collection', [])
                updated_collection = []
                for c in collection:
                    if (c.get('player_name') == card.player_name and 
                        c.get('year') == card.year and 
                        c.get('card_set') == card.card_set and 
                        c.get('card_number') == card.card_number):
                        updated_collection.append(card.to_dict())
                    else:
                        updated_collection.append(c)
                
                user_ref.update({
                    'collection': updated_collection
                })
                return True
            return False
        except Exception as e:
            print(f"Error updating card in collection: {str(e)}")
            return False

    @staticmethod
    def delete_card_from_collection(uid: str, card: Card) -> bool:
        """Delete a card from user's collection."""
        try:
            user_ref = db.collection('users').document(uid)
            user_doc = user_ref.get()
            if user_doc.exists:
                collection = user_doc.to_dict().get('collection', [])
                updated_collection = [
                    c for c in collection 
                    if not (c.get('player_name') == card.player_name and 
                           c.get('year') == card.year and 
                           c.get('card_set') == card.card_set and 
                           c.get('card_number') == card.card_number)
                ]
                
                user_ref.update({
                    'collection': updated_collection
                })
                return True
            return False
        except Exception as e:
            print(f"Error deleting card from collection: {str(e)}")
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
                        'collection': [],  # Initialize empty collection
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
                        'updated_at': datetime.now().isoformat()
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