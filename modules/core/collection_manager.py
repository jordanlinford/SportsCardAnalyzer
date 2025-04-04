"""
Collection Manager module for handling sports card collections.
Provides functionality for managing, analyzing, and tracking card collections.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Union, Tuple

class CollectionManager:
    """Manages a collection of sports cards with functionality for tracking values and performance."""
    
    def __init__(self):
        """Initialize the collection manager."""
        self.collection = pd.DataFrame(columns=[
            'player_name', 'year', 'card_set', 'card_number', 'variation',
            'condition', 'purchase_price', 'purchase_date', 'current_value',
            'last_updated', 'notes', 'photo', 'roi', 'tags'
        ])
    
    def add_card(self, card_data: Dict) -> bool:
        """
        Add a new card to the collection.
        
        Args:
            card_data (Dict): Dictionary containing card information
            
        Returns:
            bool: True if card was added successfully, False otherwise
        """
        try:
            # Ensure required fields are present
            required_fields = ['player_name', 'year', 'card_set']
            if not all(field in card_data for field in required_fields):
                return False
            
            # Add default values for optional fields
            card_data.setdefault('card_number', '')
            card_data.setdefault('variation', '')
            card_data.setdefault('condition', 'Raw')
            card_data.setdefault('purchase_price', 0.0)
            card_data.setdefault('purchase_date', datetime.now().strftime('%Y-%m-%d'))
            card_data.setdefault('current_value', card_data['purchase_price'])
            card_data.setdefault('last_updated', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            card_data.setdefault('notes', '')
            card_data.setdefault('photo', None)
            card_data.setdefault('roi', 0.0)
            card_data.setdefault('tags', '')
            
            # Add card to collection
            self.collection = pd.concat([
                self.collection,
                pd.DataFrame([card_data])
            ], ignore_index=True)
            
            return True
        except Exception:
            return False
    
    def remove_card(self, index: int) -> bool:
        """
        Remove a card from the collection.
        
        Args:
            index (int): Index of the card to remove
            
        Returns:
            bool: True if card was removed successfully, False otherwise
        """
        try:
            self.collection = self.collection.drop(index).reset_index(drop=True)
            return True
        except Exception:
            return False
    
    def update_card(self, index: int, updates: Dict) -> bool:
        """
        Update card information.
        
        Args:
            index (int): Index of the card to update
            updates (Dict): Dictionary containing fields to update
            
        Returns:
            bool: True if card was updated successfully, False otherwise
        """
        try:
            for field, value in updates.items():
                if field in self.collection.columns:
                    self.collection.at[index, field] = value
            return True
        except Exception:
            return False
    
    def get_collection_summary(self) -> Dict:
        """
        Get summary statistics for the collection.
        
        Returns:
            Dict: Collection summary including total value, cost, and ROI
        """
        if self.collection.empty:
            return {
                'total_cards': 0,
                'total_value': 0.0,
                'total_cost': 0.0,
                'total_roi': 0.0,
                'avg_card_value': 0.0
            }
        
        total_value = self.collection['current_value'].sum()
        total_cost = self.collection['purchase_price'].sum()
        
        return {
            'total_cards': len(self.collection),
            'total_value': total_value,
            'total_cost': total_cost,
            'total_roi': ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0,
            'avg_card_value': total_value / len(self.collection)
        }
    
    def get_collection_by_player(self) -> Dict[str, pd.DataFrame]:
        """
        Group collection by player.
        
        Returns:
            Dict[str, pd.DataFrame]: Dictionary with player names as keys and their cards as values
        """
        return dict(tuple(self.collection.groupby('player_name')))
    
    def get_collection_by_year(self) -> Dict[str, pd.DataFrame]:
        """
        Group collection by year.
        
        Returns:
            Dict[str, pd.DataFrame]: Dictionary with years as keys and cards as values
        """
        return dict(tuple(self.collection.groupby('year')))
    
    def get_top_performers(self, n: int = 5) -> pd.DataFrame:
        """
        Get the top performing cards by ROI.
        
        Args:
            n (int): Number of cards to return
            
        Returns:
            pd.DataFrame: Top performing cards
        """
        return self.collection.nlargest(n, 'roi')
    
    def get_underperformers(self, n: int = 5) -> pd.DataFrame:
        """
        Get the worst performing cards by ROI.
        
        Args:
            n (int): Number of cards to return
            
        Returns:
            pd.DataFrame: Worst performing cards
        """
        return self.collection.nsmallest(n, 'roi')
    
    def export_collection(self, format: str = 'csv') -> Union[str, bytes]:
        """
        Export the collection to a file format.
        
        Args:
            format (str): Export format ('csv' or 'excel')
            
        Returns:
            Union[str, bytes]: Exported data in specified format
        """
        if format == 'csv':
            return self.collection.to_csv(index=False)
        elif format == 'excel':
            output = pd.ExcelWriter('collection.xlsx', engine='openpyxl')
            self.collection.to_excel(output, index=False)
            return output.save()
        else:
            raise ValueError("Unsupported export format")
    
    def import_collection(self, data: Union[str, bytes], format: str = 'csv') -> bool:
        """
        Import collection data.
        
        Args:
            data (Union[str, bytes]): Data to import
            format (str): Import format ('csv' or 'excel')
            
        Returns:
            bool: True if import was successful, False otherwise
        """
        try:
            if format == 'csv':
                imported_df = pd.read_csv(data)
            elif format == 'excel':
                imported_df = pd.read_excel(data)
            else:
                return False
            
            # Validate required columns
            required_cols = [
                'player_name', 'year', 'card_set', 'card_number', 'variation',
                'condition', 'purchase_price', 'purchase_date'
            ]
            
            if not all(col in imported_df.columns for col in required_cols):
                return False
            
            # Add missing optional columns
            if 'current_value' not in imported_df.columns:
                imported_df['current_value'] = imported_df['purchase_price']
            if 'last_updated' not in imported_df.columns:
                imported_df['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if 'notes' not in imported_df.columns:
                imported_df['notes'] = ''
            if 'photo' not in imported_df.columns:
                imported_df['photo'] = None
            if 'roi' not in imported_df.columns:
                imported_df['roi'] = 0.0
            if 'tags' not in imported_df.columns:
                imported_df['tags'] = ''
            
            self.collection = imported_df
            return True
        except Exception:
            return False 