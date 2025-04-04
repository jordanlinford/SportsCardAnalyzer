from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
from ..database.service import DatabaseService
import ast

class DisplayCaseManager:
    def __init__(self, uid: str, collection: pd.DataFrame):
        self.uid = uid
        self.collection = collection
        self.display_cases = {}
        self.last_refresh_time = None
        
    def load_display_cases(self, force_refresh: bool = False) -> Dict:
        """Load display cases from Firebase and refresh card data from current collection"""
        try:
            # Always refresh collection data from Firebase
            new_collection = DatabaseService.get_user_collection(self.uid)
            
            # Check if collection has changed
            collection_changed = (
                force_refresh or 
                self.last_refresh_time is None or
                len(new_collection) != len(self.collection) or
                not new_collection.equals(self.collection)
            )
            
            if collection_changed:
                print("Collection has changed, refreshing display cases")
                self.collection = new_collection
                self.last_refresh_time = datetime.now()
                
                # Load fresh display cases from Firebase
                self.display_cases = DatabaseService.get_user_display_cases(self.uid)
                
                # If no display cases exist, initialize with empty dict
                if not self.display_cases:
                    self.display_cases = {}
                    return self.display_cases
                
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
            return {}
            
    def _normalize_tags(self, tags) -> List[str]:
        """Normalize tags to a consistent format"""
        normalized_tags = []
        try:
            if pd.isna(tags) or tags is None:
                return []
                
            if isinstance(tags, str):
                # First try to parse as JSON/list string
                try:
                    if tags.startswith('[') and tags.endswith(']'):
                        parsed_tags = ast.literal_eval(tags)
                        if isinstance(parsed_tags, list):
                            normalized_tags.extend([str(t).strip().lower() for t in parsed_tags if t and not pd.isna(t)])
                        else:
                            normalized_tags.append(str(parsed_tags).strip().lower())
                except:
                    # If parsing fails, split by comma and clean
                    normalized_tags.extend([t.strip().lower() for t in tags.split(',') if t.strip()])
            elif isinstance(tags, list):
                normalized_tags.extend([str(t).strip().lower() for t in tags if t and not pd.isna(t)])
            elif isinstance(tags, dict):
                normalized_tags.extend([str(t).strip().lower() for t in tags.values() if t and not pd.isna(t)])
            elif isinstance(tags, pd.Series):
                normalized_tags.extend([str(t).strip().lower() for t in tags if t and not pd.isna(t)])
            
            # Remove duplicates, empty strings, and None values
            normalized_tags = list(set(tag for tag in normalized_tags if tag and not pd.isna(tag)))
            print(f"Normalized tags result: {normalized_tags}")
            return sorted(normalized_tags)  # Sort for consistency
        except Exception as e:
            print(f"Error in _normalize_tags: {str(e)}")
            return []

    def _has_matching_tags(self, card_tags, filter_tags) -> bool:
        """Check if any of the filter tags match the card tags"""
        # Normalize both sets of tags
        card_tags_normalized = self._normalize_tags(card_tags)
        filter_tags_normalized = self._normalize_tags(filter_tags)
        
        # Debug print
        print(f"Card tags: {card_tags_normalized}")
        print(f"Filter tags: {filter_tags_normalized}")
        
        # Check for any matching tags (case insensitive)
        card_tags_set = {tag.lower() for tag in card_tags_normalized}
        filter_tags_set = {tag.lower() for tag in filter_tags_normalized}
        return bool(card_tags_set & filter_tags_set)

    def _filter_cards_by_tags(self, tags: List[str]) -> List[Dict]:
        """Filter cards from current collection based on tags"""
        if not self.collection and 'tags' in self.collection[0]:
            # Normalize the filter tags
            normalized_filter_tags = self._normalize_tags(tags)
            print(f"Filtering cards with tags: {normalized_filter_tags}")
            
            # Filter cards based on tags
            filtered_cards = []
            for card in self.collection:
                card_tags = self._normalize_tags(card['tags'])
                if any(tag in card_tags for tag in normalized_filter_tags):
                    # Ensure all fields are properly handled
                    card_dict = card.copy()
                    
                    # Ensure image field is properly handled
                    if 'photo' in card_dict and pd.isna(card_dict['photo']):
                        card_dict['photo'] = None
                    
                    # Ensure tags are properly formatted
                    if 'tags' in card_dict:
                        card_dict['tags'] = self._normalize_tags(card_dict['tags'])
                    
                    # Ensure numeric fields are properly handled
                    for field in ['current_value', 'purchase_price', 'roi']:
                        if field in card_dict and pd.isna(card_dict[field]):
                            card_dict[field] = 0.0
                        elif field in card_dict:
                            try:
                                card_dict[field] = float(card_dict[field])
                            except (ValueError, TypeError):
                                card_dict[field] = 0.0
                    
                    filtered_cards.append(card_dict)
            
            print(f"Found {len(filtered_cards)} cards matching the tags")
            return filtered_cards
        return []
            
    def save_display_cases(self) -> bool:
        """Save display cases to Firebase"""
        try:
            # Debug print the display cases
            print(f"Saving {len(self.display_cases)} display cases")
            
            # Create a copy of the display cases for serialization
            serializable_cases = {}
            for name, case in self.display_cases.items():
                # Create a new dict with only serializable data
                serializable_case = {
                    'name': case.get('name', ''),
                    'description': case.get('description', ''),
                    'tags': case.get('tags', []),
                    'created_date': case.get('created_date', ''),
                    'total_value': case.get('total_value', 0.0)
                }
                
                # Handle cards separately to ensure they're serializable
                if 'cards' in case:
                    serializable_cards = []
                    for card in case['cards']:
                        # Create a new dict with only serializable data
                        serializable_card = {}
                        for key, value in card.items():
                            # Skip non-serializable types
                            if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                                serializable_card[key] = value
                            else:
                                # Convert to string representation
                                serializable_card[key] = str(value)
                        serializable_cards.append(serializable_card)
                    serializable_case['cards'] = serializable_cards
                
                serializable_cases[name] = serializable_case
            
            # Save to Firebase
            result = DatabaseService.save_user_display_cases(self.uid, serializable_cases)
            
            # Debug print the result
            print(f"Save result: {result}")
            
            return result
        except Exception as e:
            print(f"Error saving display cases: {str(e)}")
            import traceback
            traceback.print_exc()
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
            
            # Ensure the collection has a 'tags' column
            if 'tags' not in self.collection.columns:
                self.collection['tags'] = self.collection['tags'].apply(lambda x: [] if pd.isna(x) else x)
            
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
            save_result = DatabaseService.save_user_display_cases(self.uid, self.display_cases)
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
            if not self.collection.empty and 'tags' in self.collection.columns:
                print(f"Collection shape: {self.collection.shape}")
                print(f"Tags column type: {self.collection['tags'].dtype}")
                print(f"Sample of tags column: {self.collection['tags'].head()}")
                
                # Get all non-null tags from the collection
                tags_series = self.collection['tags'].dropna()
                print(f"Number of non-null tags: {len(tags_series)}")
                
                # Normalize and collect all unique tags
                for tags in tags_series:
                    normalized_tags = self._normalize_tags(tags)
                    print(f"Raw tags: {tags}")
                    print(f"Normalized tags: {normalized_tags}")
                    all_tags.update(normalized_tags)
            
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