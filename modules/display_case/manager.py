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
    def __init__(self, uid: str, collection: pd.DataFrame):
        self.uid = uid
        self.collection = collection
        self.display_cases = {}
        self.last_refresh_time = None
        
    def load_display_cases(self, force_refresh: bool = False) -> Dict:
        """Load display cases from Firebase and refresh card data from current collection"""
        try:
            # Always get fresh collection data from Firebase
            new_collection = DatabaseService.get_user_collection(self.uid)
            
            # Check if we need to refresh
            collection_changed = force_refresh or self.last_refresh_time is None
            
            # Compare collections if not forcing refresh
            if not collection_changed and isinstance(self.collection, pd.DataFrame) and isinstance(new_collection, pd.DataFrame):
                # Compare tags between old and new collection
                old_tags = set()
                new_tags = set()
                
                # Get tags from old collection
                if 'tags' in self.collection.columns:
                    for tags in self.collection['tags'].dropna():
                        if isinstance(tags, str):
                            old_tags.update(tag.strip() for tag in tags.split(','))
                        elif isinstance(tags, list):
                            old_tags.update(str(tag).strip() for tag in tags)
                
                # Get tags from new collection
                if 'tags' in new_collection.columns:
                    for tags in new_collection['tags'].dropna():
                        if isinstance(tags, str):
                            new_tags.update(tag.strip() for tag in tags.split(','))
                        elif isinstance(tags, list):
                            new_tags.update(str(tag).strip() for tag in tags)
                
                # Check if tags have changed
                collection_changed = old_tags != new_tags
                
                if collection_changed:
                    print("Collection has changed, refreshing display cases")
                    print(f"Old tags: {old_tags}")
                    print(f"New tags: {new_tags}")
            elif not collection_changed and isinstance(self.collection, list) and isinstance(new_collection, list):
                # Compare tags between old and new collection for list format
                old_tags = set()
                new_tags = set()
                
                # Get tags from old collection
                for card in self.collection:
                    card_dict = card.to_dict() if hasattr(card, 'to_dict') else card
                    tags = card_dict.get('tags', [])
                    if isinstance(tags, str):
                        old_tags.update(tag.strip() for tag in tags.split(','))
                    elif isinstance(tags, list):
                        old_tags.update(str(tag).strip() for tag in tags)
                
                # Get tags from new collection
                for card in new_collection:
                    card_dict = card.to_dict() if hasattr(card, 'to_dict') else card
                    tags = card_dict.get('tags', [])
                    if isinstance(tags, str):
                        new_tags.update(tag.strip() for tag in tags.split(','))
                    elif isinstance(tags, list):
                        new_tags.update(str(tag).strip() for tag in tags)
                
                # Check if tags have changed
                collection_changed = old_tags != new_tags
                
                if collection_changed:
                    print("Collection has changed, refreshing display cases")
                    print(f"Old tags: {old_tags}")
                    print(f"New tags: {new_tags}")
            
            # Update collection and refresh time
            self.collection = new_collection
            self.last_refresh_time = datetime.now()
            
            # Load fresh display cases from Firebase
            loaded_cases = DatabaseService.get_user_display_cases(self.uid)
            
            # Ensure display_cases is always a dictionary
            self.display_cases = loaded_cases if isinstance(loaded_cases, dict) else {}
            
            # Refresh card data for each display case
            for case_name, display_case in self.display_cases.items():
                filtered_cards = self._filter_cards_by_tags(display_case['tags'])
                display_case['cards'] = filtered_cards
                display_case['total_value'] = sum(card.get('current_value', 0) for card in filtered_cards)
                print(f"Refreshed display case '{case_name}' with {len(filtered_cards)} cards")
            
            # Save the updated display cases
            self.save_display_cases()
            
            return self.display_cases
            
        except Exception as e:
            print(f"Error loading display cases: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            # Ensure we always return a dictionary
            self.display_cases = {}
            return self.display_cases
            
    def _normalize_tags(self, tags) -> List[str]:
        """Normalize tags to a consistent format with support for hierarchical tags"""
        normalized_tags = []
        try:
            print(f"\n=== Normalizing Tags ===")
            print(f"Input tags: {tags}")
            print(f"Input tags type: {type(tags)}")
            
            if pd.isna(tags) or tags is None:
                print("Tags are None or NaN")
                return []
                
            if isinstance(tags, str):
                print("Processing string tags")
                # First try to parse as JSON/list string
                try:
                    if tags.startswith('[') and tags.endswith(']'):
                        print("Attempting to parse as JSON/list string")
                        parsed_tags = ast.literal_eval(tags)
                        if isinstance(parsed_tags, list):
                            normalized_tags.extend([str(t).strip().lower() for t in parsed_tags if t and not pd.isna(t)])
                        else:
                            normalized_tags.append(str(parsed_tags).strip().lower())
                except:
                    print("Parsing as JSON failed, splitting by comma")
                    # If parsing fails, split by comma and clean
                    normalized_tags.extend([t.strip().lower() for t in tags.split(',') if t.strip()])
            elif isinstance(tags, list):
                print("Processing list tags")
                normalized_tags.extend([str(t).strip().lower() for t in tags if t and not pd.isna(t)])
            elif isinstance(tags, dict):
                print("Processing dict tags")
                normalized_tags.extend([str(t).strip().lower() for t in tags.values() if t and not pd.isna(t)])
            elif isinstance(tags, pd.Series):
                print("Processing Series tags")
                normalized_tags.extend([str(t).strip().lower() for t in tags if t and not pd.isna(t)])
            
            # Process hierarchical tags and special operators
            processed_tags = []
            for tag in normalized_tags:
                print(f"\nProcessing tag: {tag}")
                # Handle tag exclusions
                if tag.startswith('!'):
                    processed_tag = f"exclude:{tag[1:]}"
                    print(f"Exclusion tag: {processed_tag}")
                    processed_tags.append(processed_tag)
                # Handle tag ranges
                elif ':' in tag and '-' in tag:
                    category, range_str = tag.split(':', 1)
                    start, end = range_str.split('-', 1)
                    range_tags = [f"{category}:{i}" for i in range(int(start), int(end) + 1)]
                    print(f"Range tags: {range_tags}")
                    processed_tags.extend(range_tags)
                else:
                    processed_tags.append(tag)
            
            # Remove duplicates, empty strings, and None values
            processed_tags = list(set(tag for tag in processed_tags if tag and not pd.isna(tag)))
            print(f"\nFinal normalized tags: {processed_tags}")
            return sorted(processed_tags)  # Sort for consistency
        except Exception as e:
            print(f"Error in _normalize_tags: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return []

    def _has_matching_tags(self, card_tags, filter_tags) -> bool:
        """Check if the card tags match the filter tags with support for advanced filtering"""
        try:
            # Normalize both sets of tags
            card_tags_normalized = self._normalize_tags(card_tags)
            filter_tags_normalized = self._normalize_tags(filter_tags)
            
            print(f"\nChecking tags match:")
            print(f"Card tags: {card_tags_normalized}")
            print(f"Filter tags: {filter_tags_normalized}")
            
            # If either set is empty, return False
            if not card_tags_normalized or not filter_tags_normalized:
                print("One or both tag sets are empty")
                return False
            
            # Convert to sets for case-insensitive comparison
            card_tags_set = {tag.lower() for tag in card_tags_normalized}
            filter_tags_set = {tag.lower() for tag in filter_tags_normalized}
            
            print(f"Card tags set: {card_tags_set}")
            print(f"Filter tags set: {filter_tags_set}")
            
            # Handle exclusions
            exclude_tags = {tag[8:] for tag in filter_tags_set if tag.startswith('exclude:')}
            if exclude_tags:
                print(f"Exclude tags: {exclude_tags}")
                if any(tag in card_tags_set for tag in exclude_tags):
                    print(f"Card has excluded tag: {exclude_tags}")
                    return False
            
            # Handle hierarchical tags
            for filter_tag in filter_tags_set:
                if filter_tag.startswith('exclude:'):
                    continue
                    
                print(f"\nChecking filter tag: {filter_tag}")
                if ':' in filter_tag:
                    category, value = filter_tag.split(':', 1)
                    print(f"Category: {category}, Value: {value}")
                    # Check if card has any tag in this category
                    category_tags = [tag for tag in card_tags_set if tag.startswith(f"{category}:")]
                    print(f"Card's tags in category: {category_tags}")
                    if not category_tags:
                        print(f"Card missing category {category}")
                        return False
                    # Check if any tag in the category matches the value
                    if not any(tag.split(':', 1)[1] == value for tag in category_tags):
                        print(f"Card missing value {value} in category {category}")
                        return False
                else:
                    # Handle list tags
                    if isinstance(card_tags, list):
                        if not any(tag.lower() == filter_tag for tag in card_tags):
                            print(f"Card missing tag {filter_tag}")
                            return False
                    else:
                        if filter_tag not in card_tags_set:
                            print(f"Card missing tag {filter_tag}")
                            return False
            
            print("All tags match")
            return True
        except Exception as e:
            print(f"Error in _has_matching_tags: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False

    def _filter_cards_by_tags(self, tags: List[str]) -> List[Dict]:
        """Filter cards from current collection based on tags"""
        if not self.collection:
            print("No collection available for filtering")
            return []
        
        # Normalize the filter tags
        normalized_filter_tags = self._normalize_tags(tags)
        print(f"\nFiltering with tags: {normalized_filter_tags}")
        
        # Filter cards based on tags
        filtered_cards = []
        
        # Handle both DataFrame and list formats
        if isinstance(self.collection, pd.DataFrame):
            print("\nProcessing DataFrame collection")
            print(f"Collection shape: {self.collection.shape}")
            print(f"Collection columns: {self.collection.columns.tolist()}")
            
            if 'tags' not in self.collection.columns:
                print("ERROR: 'tags' column not found in collection")
                return []
                
            # Print sample of tags from collection
            print("\nSample of tags from collection:")
            for idx, row in self.collection.head().iterrows():
                print(f"Card {idx} tags: {row['tags']}")
            
            for idx, card in self.collection.iterrows():
                card_dict = card.to_dict()
                card_tags = card_dict.get('tags', [])
                print(f"\nChecking card {idx}:")
                print(f"Card tags: {card_tags}")
                print(f"Card tags type: {type(card_tags)}")
                
                if self._has_matching_tags(card_tags, normalized_filter_tags):
                    print("Card matches filter tags")
                    filtered_cards.append(card_dict)
                else:
                    print("Card does not match filter tags")
        else:
            # Handle list format (both Card objects and dictionaries)
            print("\nProcessing list collection")
            for idx, card in enumerate(self.collection):
                try:
                    print(f"\nChecking card {idx}:")
                    # Convert to dictionary if it's a Card object
                    card_dict = card.to_dict() if hasattr(card, 'to_dict') else card
                    
                    # Get tags from the card
                    card_tags = []
                    if 'tags' in card_dict:
                        tags_data = card_dict['tags']
                        print(f"Raw tags data: {tags_data}")
                        print(f"Raw tags type: {type(tags_data)}")
                        
                        if isinstance(tags_data, str):
                            card_tags = [tag.strip() for tag in tags_data.split(',') if tag.strip()]
                        elif isinstance(tags_data, list):
                            card_tags = [str(tag).strip() for tag in tags_data if tag]
                        else:
                            print(f"Unexpected tags data type: {type(tags_data)}")
                            continue
                    
                    print(f"Processed card tags: {card_tags}")
                    
                    # Check if any of the card's tags match the filter tags
                    if self._has_matching_tags(card_tags, normalized_filter_tags):
                        print("Card matches filter tags")
                        filtered_cards.append(card_dict)
                    else:
                        print("Card does not match filter tags")
                except Exception as e:
                    print(f"Error processing card {idx}: {str(e)}")
                    import traceback
                    print(f"Traceback: {traceback.format_exc()}")
                    continue
        
        print(f"\nTotal cards matching tags: {len(filtered_cards)}")
        return filtered_cards
            
    def save_display_cases(self) -> bool:
        """Save display cases to Firebase"""
        try:
            print(f"\n=== Saving Display Cases ===")
            print(f"UID: {self.uid}")
            print(f"Number of display cases: {len(self.display_cases)}")
            
            # Get the database service
            db = DatabaseService.get_instance()
            if not db:
                print("ERROR: Database service not initialized")
                return False
                
            # Save the display cases
            success = db.save_display_cases(self.uid, self.display_cases)
            print(f"Save result: {success}")
            return success
        except Exception as e:
            print(f"Error saving display cases: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False
            
    def create_display_case(self, name: str, description: str, tags: List[str]) -> Optional[Dict]:
        """Create a new display case with the given name, description, and tags"""
        try:
            # Debug print the input parameters
            print(f"Creating display case with name: {name}")
            print(f"Description: {description}")
            print(f"Tags: {tags}")
            
            # Normalize tags
            normalized_tags = self._normalize_tags(tags)
            print(f"Normalized tags: {normalized_tags}")
            
            # Filter cards based on tags
            filtered_cards = self._filter_cards_by_tags(normalized_tags)
            print(f"Found {len(filtered_cards)} cards with the selected tags")
            
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
            print(f"Total value of display case: ${total_value:.2f}")
            
            # Create the display case
            display_case = {
                'name': name,
                'description': description,
                'tags': normalized_tags,
                'cards': processed_cards,
                'created_date': datetime.now().isoformat(),
                'total_value': total_value
            }
            
            # Add the display case to the dictionary
            self.display_cases[name] = display_case
            
            # Save the display cases
            save_result = self.save_display_cases()
            print(f"Save result: {save_result}")
            
            if save_result:
                return display_case
            else:
                print("Failed to save display case")
                return None
        except Exception as e:
            print(f"Error creating display case: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return None
            
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
        
    def delete_display_case(self, name: str) -> bool:
        """Delete a display case from both local memory and Firebase"""
        try:
            if name in self.display_cases:
                del self.display_cases[name]
                if self.save_display_cases():
                    # Reload display cases to ensure sync
                    self.load_display_cases()
                    return True
            return False
        except Exception as e:
            print(f"Error deleting display case: {str(e)}")
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
        
    def refresh_display_case(self, name: str) -> bool:
        """Refresh a display case by filtering cards based on its tags"""
        if name not in self.display_cases:
            print(f"Display case '{name}' not found")
            return False
            
        # Get the display case
        display_case = self.display_cases[name]
        
        # Get the tags
        tags = display_case.get('tags', [])
        
        # Filter cards based on tags
        filtered_cards = self._filter_cards_by_tags(tags)
        
        # Update the display case
        display_case['cards'] = filtered_cards
        display_case['total_value'] = sum(card.get('current_value', 0) for card in filtered_cards)
        
        # Save the display cases
        return self.save_display_cases()
        
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