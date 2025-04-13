import traceback
from typing import Dict, List, Optional, Union
from datetime import datetime
import pandas as pd
from ..database.service import DatabaseService
import ast
import json
import base64
from ..core.firebase_manager import FirebaseManager
import streamlit as st

class DisplayCaseManager:
    def __init__(self, uid: str, collection: Union[pd.DataFrame, List[Dict]]):
        self.uid = uid
        self.collection = collection
        self.display_cases = {}
        self.last_refresh_time = None
        self.db = DatabaseService.get_instance()  # Initialize the database service
        
    def load_display_cases(self) -> List[Dict]:
        """
        Load all display cases from Firebase.
        
        Returns:
            List[Dict]: List of display cases
        """
        print("\n=== Loading Display Cases ===")
        if not self.db:
            print("[ERROR] Database service not initialized")
            return []
        
        try:
            # Get the Firebase client
            db = FirebaseManager.get_firestore_client()
            if not db:
                print("[ERROR] Failed to get Firebase client")
                return []
            
            # Get the user document reference
            user_doc = db.collection('users').document(self.uid)
            if not user_doc.get().exists:
                print("[ERROR] User document not found")
                return []
            
            # Get the display cases subcollection
            display_cases = user_doc.collection('display_cases').get()
            cases = []
            
            for case in display_cases:
                case_data = case.to_dict()
                case_data['id'] = case.id
                
                # Ensure cards key exists
                if 'cards' not in case_data:
                    case_data['cards'] = []
                
                # Validate and ensure photo data is present for each card
                for card in case_data['cards']:
                    if not card.get('photo'):
                        # Try to find the original card in the collection
                        card_id = card.get('id')
                        if card_id:
                            # Find the card in the collection
                            matching_card = next((c for c in self.collection if c.get('id') == card_id), None)
                            if matching_card:
                                card['photo'] = matching_card.get('photo')
                
                # Calculate total value if not present
                if 'total_value' not in case_data:
                    case_data['total_value'] = sum(card.get('value', 0) for card in case_data['cards'])
                
                cases.append(case_data)
            
            print(f"Loaded {len(cases)} display cases")
            return cases
            
        except Exception as e:
            print(f"[ERROR] Failed to load display cases: {str(e)}")
            print(traceback.format_exc())
            return []

    def _normalize_tags(self, tags: Union[str, List[str]]) -> List[str]:
        """Normalize tags to a consistent format"""
        try:
            if not tags:
                return []
            
            # Handle string input
            if isinstance(tags, str):
                # Try to parse as JSON if it looks like a JSON string
                if tags.strip().startswith('[') and tags.strip().endswith(']'):
                    try:
                        tags = json.loads(tags)
                    except json.JSONDecodeError:
                        # If not valid JSON, split by comma
                        tags = [tag.strip() for tag in tags.split(',')]
                else:
                    # Split by comma if not JSON
                    tags = [tag.strip() for tag in tags.split(',')]
            
            # Ensure we have a list
            if not isinstance(tags, list):
                tags = [tags]
            
            # Process each tag
            normalized_tags = []
            for tag in tags:
                if not tag:  # Skip empty tags
                    continue
                
                # Handle nested lists
                if isinstance(tag, list):
                    normalized_tags.extend(self._normalize_tags(tag))
                    continue
                
                # Convert to string and clean
                tag = str(tag).strip().lower()
                if tag:  # Only add non-empty tags
                    normalized_tags.append(tag)
            
            # Remove duplicates while preserving order
            seen = set()
            return [x for x in normalized_tags if not (x in seen or seen.add(x))]
            
        except Exception as e:
            print(f"Error normalizing tags: {str(e)}")
            print(f"Tags input: {tags}")
            print(f"Traceback: {traceback.format_exc()}")
            return []

    def _validate_collection(self) -> bool:
        """
        Validate that the collection exists and has data.
        
        Returns:
            bool: True if collection is valid and contains data
        """
        print("\n=== Validating Collection ===")
        if self.collection is None:
            print("[DEBUG] Collection is None")
            return False
        
        if isinstance(self.collection, pd.DataFrame):
            print(f"[DEBUG] Collection is DataFrame with shape: {self.collection.shape}")
            print(f"[DEBUG] Collection columns: {self.collection.columns.tolist()}")
            if self.collection.empty:
                print("[DEBUG] Collection DataFrame is empty")
                return False
            if 'tags' not in self.collection.columns:
                print("[DEBUG] Collection DataFrame missing 'tags' column")
                return False
            return True
        elif isinstance(self.collection, list):
            print(f"[DEBUG] Collection is list with length: {len(self.collection)}")
            if len(self.collection) == 0:
                print("[DEBUG] Collection list is empty")
                return False
            
            # Convert any non-dict items to dicts
            for i, item in enumerate(self.collection):
                if not isinstance(item, dict):
                    try:
                        if hasattr(item, 'to_dict'):
                            self.collection[i] = item.to_dict()
                        else:
                            print(f"[DEBUG] Converting item {i} to dict")
                            self.collection[i] = dict(item)
                    except Exception as e:
                        print(f"[DEBUG] Failed to convert item {i} to dict: {str(e)}")
                        return False
            
            return True
        
        print(f"[DEBUG] Collection is neither DataFrame nor list, type: {type(self.collection)}")
        return False

    def _validate_card_photo(self, card: Dict) -> bool:
        """
        Validate and normalize card photo data.
        
        Args:
            card (Dict): Card dictionary containing photo data
            
        Returns:
            bool: True if photo is valid and properly formatted
        """
        if 'photo' not in card or not card['photo']:
            print(f"[DEBUG] Card {card.get('player_name', 'Unknown')} has no photo")
            return False
        
        if not isinstance(card['photo'], str):
            try:
                if isinstance(card['photo'], (list, dict)):
                    print(f"[DEBUG] Invalid photo type for {card.get('player_name', 'Unknown')}")
                    return False
                card['photo'] = str(card['photo'])
            except:
                print(f"[DEBUG] Failed to convert photo to string for {card.get('player_name', 'Unknown')}")
                return False
        
        return True

    def _safe_get_card_value(self, card: Dict) -> float:
        """
        Safely extract and convert card value.
        
        Args:
            card (Dict): Card dictionary containing value data
            
        Returns:
            float: Card value, defaults to 0.0 if invalid
        """
        try:
            return float(card.get('current_value', 0))
        except (ValueError, TypeError):
            print(f"[DEBUG] Invalid value for card {card.get('player_name', 'Unknown')}")
            return 0.0

    def _filter_cards_by_tags(self, tags: List[str]) -> List[Dict]:
        """
        Filter collection cards by specified tags.
        
        Args:
            tags (List[str]): List of tags to filter by
            
        Returns:
            List[Dict]: List of matching cards
        """
        print("\n=== Filtering Cards by Tags ===")
        print(f"Input tags: {tags}")
        
        if not self._validate_collection():
            print("[ERROR] Collection validation failed")
            return []
        
        normalized_filter_tags = set(t.lower().strip() for t in tags if t and not pd.isna(t))
        print(f"Normalized filter tags: {normalized_filter_tags}")
        
        if not normalized_filter_tags:
            print("[ERROR] No valid tags after normalization")
            return []
        
        matching_cards = []
        
        if isinstance(self.collection, pd.DataFrame):
            print("[DEBUG] Processing DataFrame collection")
            for idx, row in self.collection.iterrows():
                card = row.to_dict()
                # Generate a consistent ID for the card
                card_id = f"{card.get('player_name', '')}_{card.get('year', '')}_{card.get('card_set', '')}_{card.get('card_number', '')}".replace(" ", "_").lower()
                card['id'] = card_id
                card_tags = self._normalize_tags(card.get('tags', []))
                print(f"Card {idx} tags: {card_tags}")
                if any(tag in card_tags for tag in normalized_filter_tags):
                    if self._validate_card_photo(card):
                        matching_cards.append(card)
                        print(f"Added card {idx} to matches")
        else:
            print("[DEBUG] Processing list collection")
            for idx, card in enumerate(self.collection):
                if hasattr(card, 'to_dict'):
                    card = card.to_dict()
                # Generate a consistent ID for the card
                card_id = f"{card.get('player_name', '')}_{card.get('year', '')}_{card.get('card_set', '')}_{card.get('card_number', '')}".replace(" ", "_").lower()
                card['id'] = card_id
                card_tags = self._normalize_tags(card.get('tags', []))
                print(f"Card {idx} tags: {card_tags}")
                if any(tag in card_tags for tag in normalized_filter_tags):
                    if self._validate_card_photo(card):
                        matching_cards.append(card)
                        print(f"Added card {idx} to matches")
        
        print(f"Found {len(matching_cards)} matching cards")
        return matching_cards

    def create_display_case(self, name: str, description: str, tags: List[str]) -> bool:
        """Create a new display case with optimized data storage"""
        try:
            print(f"\n=== Creating Display Case ===")
            print(f"Name: {name}")
            print(f"Tags: {tags}")
            
            if not self._validate_collection():
                print("[ERROR] Invalid collection")
                return False
            
            # Normalize tags
            normalized_tags = self._normalize_tags(tags)
            if not normalized_tags:
                print("[ERROR] No valid tags provided")
                return False
            
            # Filter cards by tags
            filtered_cards = self._filter_cards_by_tags(normalized_tags)
            if not filtered_cards:
                print("[ERROR] No cards found matching the tags")
                return False
            
            # Optimize card data for storage
            optimized_cards = []
            for card in filtered_cards:
                try:
                    optimized_card = {
                        'id': card.get('id', ''),
                        'player_name': card.get('player_name', ''),
                        'year': card.get('year', ''),
                        'set_name': card.get('set_name', ''),
                        'card_number': card.get('card_number', ''),
                        'current_value': card.get('current_value', 0),
                        'grade': card.get('grade', ''),
                        'tags': card.get('tags', []),
                        'photo': card.get('photo', '')  # Include the photo field
                    }
                    optimized_cards.append(optimized_card)
                except Exception as e:
                    print(f"Error optimizing card data: {str(e)}")
                    continue
            
            # Create display case with optimized data
            display_case = {
                'name': name,
                'description': description,
                'tags': normalized_tags,
                'cards': optimized_cards,
                'total_value': sum(card.get('current_value', 0) for card in filtered_cards),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Get the Firebase client
            db = FirebaseManager.get_firestore_client()
            if not db:
                print("ERROR: Firebase client not initialized")
                return False
                
            # Get the user document reference
            user_ref = db.collection('users').document(self.uid)
            
            # Get the display cases subcollection
            display_cases_ref = user_ref.collection('display_cases')
            
            # Generate a safe document ID
            safe_doc_id = name.lower().replace(' ', '_').replace('/', '_').replace('\\', '_')
            
            # Save the display case document
            try:
                display_cases_ref.document(safe_doc_id).set(display_case)
                print(f"Successfully created display case: {name}")
                
                # Update local state
                self.display_cases[safe_doc_id] = display_case
                return True
            except Exception as e:
                print(f"Error saving display case to Firebase: {str(e)}")
                print(f"Traceback: {traceback.format_exc()}")
                return False
            
        except Exception as e:
            print(f"Error creating display case: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return False

    def save_display_cases(self) -> bool:
        """Save display cases to Firebase as separate documents in a subcollection"""
        try:
            print(f"\n=== Saving Display Cases ===")
            print(f"UID: {self.uid}")
            print(f"Number of display cases: {len(self.display_cases)}")
            
            # Get the database service
            db = DatabaseService.get_instance()
            if not db:
                print("ERROR: Database service not initialized")
                return False
                
            # Get the user document reference
            user_ref = db.collection('users').document(self.uid)
            
            # Get the display cases subcollection
            display_cases_ref = user_ref.collection('display_cases')
            
            # Save each display case as a separate document
            for case_name, display_case in self.display_cases.items():
                try:
                    # Convert the display case to a dictionary if it's not already
                    case_data = dict(display_case) if not isinstance(display_case, dict) else display_case
                    
                    # Save the display case document
                    display_cases_ref.document(case_name).set(case_data)
                    print(f"Successfully saved display case: {case_name}")
                    
                except Exception as e:
                    print(f"Error saving display case {case_name}: {str(e)}")
                    print(f"Traceback: {traceback.format_exc()}")
                    return False
                    
            print("All display cases saved successfully")
            return True
            
        except Exception as e:
            print(f"Error saving display cases: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return False
            
    def get_all_tags(self) -> List[str]:
        """Get all unique tags from the current collection"""
        all_tags = set()
        try:
            if isinstance(self.collection, pd.DataFrame):
                if not self.collection.empty and 'tags' in self.collection.columns:
                    # Get all non-null tags from the collection
                    tags_series = self.collection['tags'].dropna()
                    
                    # Normalize and collect all unique tags
                    for tags in tags_series:
                        if isinstance(tags, str):
                            # Handle comma-separated string
                            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
                        elif isinstance(tags, list):
                            # Handle list format
                            tag_list = [str(tag).strip() for tag in tags if tag]
                        else:
                            continue
                        all_tags.update(tag_list)
            else:
                # Handle list format
                for card in self.collection:
                    try:
                        card_dict = card.to_dict() if hasattr(card, 'to_dict') else card
                        if 'tags' in card_dict:
                            tags = card_dict['tags']
                            if isinstance(tags, str):
                                # Handle comma-separated string
                                tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
                            elif isinstance(tags, list):
                                # Handle list format
                                tag_list = [str(tag).strip() for tag in tags if tag]
                            else:
                                continue
                            all_tags.update(tag_list)
                    except Exception as e:
                        print(f"Error processing card tags: {str(e)}")
                        continue
            
            # Debug print to help diagnose issues
            print(f"All available tags: {sorted(list(all_tags))}")
            
            # Sort tags alphabetically for better display
            return sorted(list(all_tags))
        except Exception as e:
            print(f"Error in get_all_tags: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return []
        
    def delete_display_case(self, case_name: str) -> bool:
        """Delete a display case"""
        try:
            print(f"\n=== Deleting Display Case ===")
            print(f"Case name: {case_name}")
            
            # Get the Firebase client
            db = FirebaseManager.get_firestore_client()
            if not db:
                print("ERROR: Firebase client not initialized")
                return False
                
            # Get the user document reference
            user_ref = db.collection('users').document(self.uid)
            
            # Get the display cases subcollection
            display_cases_ref = user_ref.collection('display_cases')
            
            # Generate a safe document ID
            safe_doc_id = case_name.lower().replace(' ', '_').replace('/', '_').replace('\\', '_')
            
            # Delete the display case document
            try:
                display_cases_ref.document(safe_doc_id).delete()
                print(f"Successfully deleted display case: {case_name}")
                
                # Update local state
                if safe_doc_id in self.display_cases:
                    del self.display_cases[safe_doc_id]
                return True
            except Exception as e:
                print(f"Error deleting display case from Firebase: {str(e)}")
                print(f"Traceback: {traceback.format_exc()}")
                return False
            
        except Exception as e:
            print(f"Error deleting display case: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return False

    def get_display_case(self, name: str) -> Optional[Dict]:
        """Get a specific display case by name, with refreshed card data"""
        if name in self.display_cases:
            display_case = self.display_cases[name]
            # Refresh card data from current collection
            filtered_cards = self._filter_cards_by_tags(display_case['tags'])
            display_case['cards'] = filtered_cards
            display_case['total_value'] = sum(card.get('current_value', 0) for card in filtered_cards)
            return display_case
        return None
        
    def update_display_case(self, name: str, updated_case: Dict) -> bool:
        """Update an existing display case"""
        if name not in self.display_cases:
            print(f"Display case '{name}' not found")
            return False
            
        # Update the display case
        self.display_cases[name] = updated_case
        
        # Save the display cases
        return self.save_display_cases()
        
    def refresh_display_case(self, case_name: str) -> bool:
        """Refresh a display case with current collection data"""
        try:
            print(f"\n=== Refreshing Display Case ===")
            print(f"Case name: {case_name}")
            
            if not self._validate_collection():
                print("[ERROR] Invalid collection")
                return False
            
            # Get the Firebase client
            db = FirebaseManager.get_firestore_client()
            if not db:
                print("ERROR: Firebase client not initialized")
                return False
                
            # Get the user document reference
            user_ref = db.collection('users').document(self.uid)
            
            # Get the display cases subcollection
            display_cases_ref = user_ref.collection('display_cases')
            
            # Generate a safe document ID
            safe_doc_id = case_name.lower().replace(' ', '_').replace('/', '_').replace('\\', '_')
            
            # Get the current display case
            case_doc = display_cases_ref.document(safe_doc_id).get()
            if not case_doc.exists:
                print(f"[ERROR] Display case {case_name} not found")
                return False
                
            case_data = case_doc.to_dict()
            tags = case_data.get('tags', [])
            
            # Filter cards by tags using current collection
            filtered_cards = self._filter_cards_by_tags(tags)
            if not filtered_cards:
                print("[ERROR] No cards found matching the tags")
                return False
            
            # Update the display case with current cards
            case_data['cards'] = filtered_cards
            case_data['total_value'] = sum(card.get('value', 0) for card in filtered_cards)
            case_data['updated_at'] = datetime.now().isoformat()
            
            # Save the updated display case
            try:
                display_cases_ref.document(safe_doc_id).set(case_data)
                print(f"Successfully refreshed display case: {case_name}")
                return True
            except Exception as e:
                print(f"Error saving refreshed display case to Firebase: {str(e)}")
                print(f"Traceback: {traceback.format_exc()}")
                return False
            
        except Exception as e:
            print(f"Error refreshing display case: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return False
        
    def create_smart_display_case(self, name: str, description: str, tag_patterns: List[str]) -> Dict:
        """Create a display case based on smart tag patterns"""
        try:
            print(f"\n=== Creating Smart Display Case ===")
            print(f"Name: {name}")
            print(f"Description: {description}")
            print(f"Input tag patterns: {tag_patterns}")
            
            # Check collection status
            if not self.collection:
                print("ERROR: No collection available")
                return None
            print(f"Collection type: {type(self.collection)}")
            if isinstance(self.collection, pd.DataFrame):
                print(f"Collection shape: {self.collection.shape}")
                print(f"Collection columns: {self.collection.columns.tolist()}")
                print(f"Sample tags from collection: {self.collection['tags'].head()}")
            
            # Normalize tag patterns
            normalized_patterns = self._normalize_tags(tag_patterns)
            print(f"\nNormalized tag patterns: {normalized_patterns}")
            
            # Filter cards based on patterns
            filtered_cards = self._filter_cards_by_tags(normalized_patterns)
            print(f"\nFound {len(filtered_cards)} cards matching the tags")
            
            # Process cards to ensure they're serializable
            processed_cards = []
            for card in filtered_cards:
                processed_card = {}
                for key, value in card.items():
                    if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        processed_card[key] = value
                    else:
                        processed_card[key] = str(value)
                processed_cards.append(processed_card)
            
            # Calculate total value
            total_value = sum(float(card.get('current_value', 0)) for card in processed_cards)
            
            # Create display case
            display_case = {
                'name': name,
                'description': description,
                'tags': normalized_patterns,
                'cards': processed_cards,
                'total_value': total_value,
                'created_date': datetime.now().isoformat(),
                'is_smart': True  # Mark as smart display case
            }
            
            # Save to display cases
            self.display_cases[name] = display_case
            if self.save_display_cases():
                print(f"\nSuccessfully created display case '{name}' with {len(processed_cards)} cards")
                return display_case
            else:
                print("\nFailed to save display case")
                return None
        except Exception as e:
            print(f"\nError creating smart display case: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return None

    def get_share_url(self, case_name: str) -> Optional[str]:
        """Generate a shareable URL for a display case"""
        try:
            if case_name not in self.display_cases:
                print(f"Display case '{case_name}' not found")
                return None
                
            # Get the display case
            display_case = self.display_cases[case_name]
            
            # Create a serializable version of the display case
            serializable_case = {
                'name': display_case.get('name', ''),
                'description': display_case.get('description', ''),
                'tags': display_case.get('tags', []),
                'created_date': display_case.get('created_date', ''),
                'total_value': display_case.get('total_value', 0.0),
                'cards': []
            }
            
            # Process cards to ensure they're serializable
            for card in display_case.get('cards', []):
                processed_card = {}
                for key, value in card.items():
                    if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        processed_card[key] = value
                    else:
                        processed_card[key] = str(value)
                serializable_case['cards'].append(processed_card)
            
            # Convert to JSON and encode
            case_json = json.dumps(serializable_case)
            encoded_data = base64.urlsafe_b64encode(case_json.encode()).decode()
            
            # Generate the share URL
            return f"?share_case={encoded_data}"
            
        except Exception as e:
            print(f"Error generating share URL: {str(e)}")
            return None

    def debug_collection(self):
        """Debug method to check collection state"""
        try:
            print("\n=== Debug Collection State ===")
            if not self.collection:
                print("No collection available")
                return
            
            print(f"Collection type: {type(self.collection)}")
            if isinstance(self.collection, pd.DataFrame):
                print(f"Collection shape: {self.collection.shape}")
                print(f"Columns: {self.collection.columns.tolist()}")
                
                if 'tags' in self.collection.columns:
                    print("\nSample of tags from first 5 cards:")
                    for idx, row in self.collection.head().iterrows():
                        print(f"Card {idx} tags: {row['tags']}")
                else:
                    print("No 'tags' column found in collection")
        except Exception as e:
            print(f"Error in debug_collection: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")

    def create_simple_display_case(self, name: str, tag: str) -> Union[Dict, None]:
        try:
            print(f"\n[DEBUG] === Creating Simple Display Case ===")
            print(f"[DEBUG] Name: {name}")
            print(f"[DEBUG] Tag: {tag}")
            print(f"[DEBUG] Collection type: {type(self.collection)}")
            
            # Check if collection is empty
            if isinstance(self.collection, pd.DataFrame):
                if self.collection.empty:
                    print("[DEBUG] Collection DataFrame is empty")
                    return None
            elif isinstance(self.collection, list):
                if len(self.collection) == 0:
                    print("[DEBUG] Collection list is empty")
                    return None
            else:
                print("[DEBUG] Collection is neither list nor DataFrame")
                return None

            # Normalize tag
            tag = tag.strip().lower()
            matching_cards = []

            # Handle both collection types
            if isinstance(self.collection, pd.DataFrame):
                for idx, row in self.collection.iterrows():
                    card = row.to_dict()
                    raw_tags = card.get('tags', [])
                    if isinstance(raw_tags, str):
                        try:
                            parsed = ast.literal_eval(raw_tags)
                            raw_tags = parsed if isinstance(parsed, list) else [t.strip() for t in raw_tags.split(',')]
                        except:
                            raw_tags = [t.strip() for t in raw_tags.split(',')]
                    elif not isinstance(raw_tags, list):
                        raw_tags = []
                    normalized_tags = [str(t).strip().lower() for t in raw_tags if t]
                    if tag in normalized_tags:
                        # Ensure photo is properly included and valid
                        if 'photo' in card and card['photo']:
                            # Convert photo to string if it's not already
                            if not isinstance(card['photo'], str):
                                card['photo'] = str(card['photo'])
                            matching_cards.append(card)
                        else:
                            print(f"[DEBUG] Card {card.get('player_name', 'Unknown')} has no photo")

            elif isinstance(self.collection, list):
                for idx, card in enumerate(self.collection):
                    if hasattr(card, 'to_dict'):
                        card = card.to_dict()
                    raw_tags = card.get('tags', [])
                    if isinstance(raw_tags, str):
                        try:
                            parsed = ast.literal_eval(raw_tags)
                            raw_tags = parsed if isinstance(parsed, list) else [t.strip() for t in raw_tags.split(',')]
                        except:
                            raw_tags = [t.strip() for t in raw_tags.split(',')]
                    elif not isinstance(raw_tags, list):
                        raw_tags = []
                    normalized_tags = [str(t).strip().lower() for t in raw_tags if t]
                    if tag in normalized_tags:
                        # Ensure photo is properly included and valid
                        if 'photo' in card and card['photo']:
                            # Convert photo to string if it's not already
                            if not isinstance(card['photo'], str):
                                card['photo'] = str(card['photo'])
                            matching_cards.append(card)
                        else:
                            print(f"[DEBUG] Card {card.get('player_name', 'Unknown')} has no photo")

            print(f"[DEBUG] Found {len(matching_cards)} cards matching tag '{tag}'")

            if not matching_cards:
                return None

            # Create display case with enhanced card data
            display_case = {
                'name': name,
                'description': f"Cards tagged with '{tag}'",
                'tags': [tag],
                'cards': matching_cards,
                'total_value': sum(float(card.get('current_value', 0)) for card in matching_cards),
                'created_date': datetime.now().isoformat()
            }

            # Save the display case
            self.display_cases[name] = display_case
            if self.save_display_cases():
                print("[DEBUG] Display case saved successfully.")
                return display_case
            else:
                print("[ERROR] Failed to save display case.")
                return None

        except Exception as e:
            print(f"[ERROR] Exception in create_simple_display_case: {str(e)}")
            print(traceback.format_exc())
            return None

    def preview_cards_by_tag(self, tag: str) -> List[Dict]:
        """Preview cards that have a specific tag"""
        try:
            if not self.collection or not isinstance(self.collection, pd.DataFrame):
                print("No valid collection available")
                return []
            
            if 'tags' not in self.collection.columns:
                print("Collection does not have a 'tags' column")
                return []
            
            print(f"\n=== Previewing cards with tag: {tag} ===")
            matching_cards = []
            
            for idx, card in self.collection.iterrows():
                card_dict = card.to_dict()
                card_tags = card_dict.get('tags', [])
                
                # Convert tags to list if it's a string
                if isinstance(card_tags, str):
                    card_tags = [t.strip() for t in card_tags.split(',')]
                elif not isinstance(card_tags, list):
                    card_tags = []
                
                # Check if the tag exists in the card's tags
                if tag.lower() in [t.lower() for t in card_tags]:
                    print(f"Found matching card: {card_dict.get('player_name', 'Unknown')}")
                    matching_cards.append(card_dict)
            
            print(f"Found {len(matching_cards)} cards with tag '{tag}'")
            return matching_cards
            
        except Exception as e:
            print(f"Error previewing cards: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return []

    def like_display_case(self, case_id: str, like: bool) -> bool:
        """Like or unlike a display case"""
        try:
            # Get Firestore client
            db = FirebaseManager.get_firestore_client()
            if not db:
                print("Error: Firestore client not initialized")
                return False
            
            # Get current user's UID
            uid = self.uid
            
            # Update likes in Firestore
            likes_ref = db.collection('display_cases').document(case_id).collection('likes')
            
            if like:
                # Add like
                likes_ref.document(uid).set({
                    'timestamp': datetime.now(),
                    'uid': uid
                })
            else:
                # Remove like
                likes_ref.document(uid).delete()
            
            # Update local display case
            if case_id in self.display_cases:
                case = self.display_cases[case_id]
                likes = case.get('likes', 0)
                case['likes'] = likes + (1 if like else -1)
                case['is_liked'] = like
            
            return True
        except Exception as e:
            print(f"Error liking display case: {str(e)}")
            return False

    def get_case_likes(self, case_id: str) -> tuple[int, bool]:
        """Get number of likes and whether current user has liked the case"""
        try:
            # Get Firestore client
            db = FirebaseManager.get_firestore_client()
            if not db:
                print("Error: Firestore client not initialized")
                return 0, False
            
            # Get current user's UID
            uid = self.uid
            
            # Get likes from Firestore
            likes_ref = db.collection('display_cases').document(case_id).collection('likes')
            likes = len(list(likes_ref.get()))
            is_liked = likes_ref.document(uid).get().exists
            
            return likes, is_liked
        except Exception as e:
            print(f"Error getting case likes: {str(e)}")
            return 0, False

    def add_comment(self, case_id: str, comment: str) -> bool:
        """Add a comment to a display case"""
        try:
            # Get Firestore client
            db = FirebaseManager.get_firestore_client()
            if not db:
                print("Error: Firestore client not initialized")
                return False
            
            # Get current user's UID
            uid = self.uid
            
            # Add comment to Firestore
            comments_ref = db.collection('display_cases').document(case_id).collection('comments')
            comments_ref.add({
                'uid': uid,
                'comment': comment,
                'timestamp': datetime.now(),
                'username': st.session_state.get('user', {}).get('displayName', 'Anonymous')
            })
            
            return True
        except Exception as e:
            print(f"Error adding comment: {str(e)}")
            return False

    def get_comments(self, case_id: str) -> List[Dict]:
        """Get all comments for a display case"""
        try:
            # Get Firestore client
            db = FirebaseManager.get_firestore_client()
            if not db:
                print("Error: Firestore client not initialized")
                return []
            
            # Get comments from Firestore
            comments_ref = db.collection('display_cases').document(case_id).collection('comments')
            comments = []
            for doc in comments_ref.order_by('timestamp', direction='DESCENDING').get():
                comment_data = doc.to_dict()
                comment_data['id'] = doc.id
                comments.append(comment_data)
            
            return comments
        except Exception as e:
            print(f"Error getting comments: {str(e)}")
            return []

    def delete_comment(self, case_id: str, comment_id: str) -> bool:
        """Delete a comment from a display case"""
        try:
            # Get Firestore client
            db = FirebaseManager.get_firestore_client()
            if not db:
                print("Error: Firestore client not initialized")
                return False
            
            # Get current user's UID
            uid = self.uid
            
            # Get the comment document
            comment_ref = db.collection('display_cases').document(case_id).collection('comments').document(comment_id)
            comment = comment_ref.get()
            
            # Check if comment exists and user is the owner
            if comment.exists and comment.get('uid') == uid:
                comment_ref.delete()
                return True
            
            return False
        except Exception as e:
            print(f"Error deleting comment: {str(e)}")
            return False 