import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch
from modules.display_case.manager import DisplayCaseManager

@pytest.fixture
def edge_case_collection():
    """Create a collection with edge cases for testing"""
    return pd.DataFrame({
        'player_name': ['Player 1', 'Player 2', 'Player 3', 'Player 4', 'Player 5'],
        'year': ['2020', '2021', '2022', '2023', '2024'],
        'card_set': ['Set A', 'Set B', 'Set C', 'Set D', 'Set E'],
        'card_number': ['123', '456', '789', '012', '345'],
        'variation': ['Base', 'Parallel', 'Auto', 'Relic', 'Printing Plate'],
        'condition': ['MINT', 'NM', 'GOOD', 'POOR', 'GEM-MT'],
        'purchase_price': [10.0, None, 30.0, 'invalid', 50.0],
        'current_value': [15.0, 'N/A', 35.0, 'pending', ''],
        'tags': [
            ['rookie', 'baseball'],  # Normal case
            None,  # Missing tags
            '',  # Empty string
            'single,tag,with,commas',  # Comma-separated string
            ['', None, 'valid_tag']  # Mixed valid/invalid tags
        ],
        'photo': [
            'data:image/jpeg;base64,test1',  # Valid photo
            None,  # Missing photo
            '',  # Empty photo
            123,  # Non-string photo
            ['invalid', 'photo']  # Invalid photo type
        ]
    })

@pytest.fixture
def edge_case_manager(edge_case_collection):
    """Create a DisplayCaseManager instance with edge cases"""
    return DisplayCaseManager('test_uid', edge_case_collection)

def test_validate_collection_empty():
    """Test collection validation with empty/invalid collections"""
    # Test with empty DataFrame
    empty_df_manager = DisplayCaseManager('test_uid', pd.DataFrame())
    assert empty_df_manager._validate_collection() is False
    
    # Test with empty list
    empty_list_manager = DisplayCaseManager('test_uid', [])
    assert empty_list_manager._validate_collection() is False
    
    # Test with None
    none_manager = DisplayCaseManager('test_uid', None)
    assert none_manager._validate_collection() is False
    
    # Test with invalid type
    invalid_manager = DisplayCaseManager('test_uid', "not a collection")
    assert invalid_manager._validate_collection() is False

def test_validate_card_photo_edge_cases(edge_case_manager):
    """Test photo validation with various edge cases"""
    cards = edge_case_manager.collection.to_dict('records')
    
    # Valid photo
    assert edge_case_manager._validate_card_photo(cards[0]) is True
    
    # Missing photo
    assert edge_case_manager._validate_card_photo(cards[1]) is False
    
    # Empty photo
    assert edge_case_manager._validate_card_photo(cards[2]) is False
    
    # Non-string photo
    assert edge_case_manager._validate_card_photo(cards[3]) is True  # Should convert to string
    
    # Invalid photo type
    assert edge_case_manager._validate_card_photo(cards[4]) is False

def test_safe_get_card_value_edge_cases(edge_case_manager):
    """Test value extraction with various edge cases"""
    cards = edge_case_manager.collection.to_dict('records')
    
    # Valid numeric value
    assert edge_case_manager._safe_get_card_value(cards[0]) == 15.0
    
    # Non-numeric string value
    assert edge_case_manager._safe_get_card_value(cards[1]) == 0.0
    
    # Valid numeric value
    assert edge_case_manager._safe_get_card_value(cards[2]) == 35.0
    
    # Invalid string value
    assert edge_case_manager._safe_get_card_value(cards[3]) == 0.0
    
    # Empty value
    assert edge_case_manager._safe_get_card_value(cards[4]) == 0.0

def test_normalize_tags_edge_cases(edge_case_manager):
    """Test tag normalization with various edge cases"""
    # Test with mixed case and spaces
    assert edge_case_manager._normalize_tags(['  ROOKIE  ', ' Baseball ']) == ['baseball', 'rookie']
    
    # Test with duplicates
    assert edge_case_manager._normalize_tags(['rookie', 'ROOKIE', 'Rookie']) == ['rookie']
    
    # Test with invalid values in list
    assert edge_case_manager._normalize_tags(['valid', None, '', 123]) == ['valid']
    
    # Test with complex string
    assert edge_case_manager._normalize_tags('rookie,  BASEBALL, rookie') == ['baseball', 'rookie']
    
    # Test with invalid string
    assert edge_case_manager._normalize_tags('{"invalid": "json"}') == ['{"invalid": "json"}']

def test_filter_cards_by_tags_edge_cases(edge_case_manager):
    """Test card filtering with various edge cases"""
    # Test with single valid tag
    result = edge_case_manager._filter_cards_by_tags(['rookie'])
    assert len(result) == 1
    assert result[0]['player_name'] == 'Player 1'
    
    # Test with non-existent tag
    result = edge_case_manager._filter_cards_by_tags(['nonexistent'])
    assert len(result) == 0
    
    # Test with empty tag list
    result = edge_case_manager._filter_cards_by_tags([])
    assert len(result) == 0
    
    # Test with mixed valid/invalid tags
    result = edge_case_manager._filter_cards_by_tags(['rookie', '', None])
    assert len(result) == 1
    assert result[0]['player_name'] == 'Player 1'

def test_create_display_case_edge_cases(edge_case_manager):
    """Test display case creation with edge cases"""
    with patch('modules.database.service.DatabaseService.save_user_display_cases') as mock_save:
        mock_save.return_value = True
        
        # Test with valid case
        result = edge_case_manager.create_display_case(
            name='Test Case',
            description='Test Description',
            tags=['rookie']
        )
        assert result is not None
        assert result['name'] == 'Test Case'
        assert len(result['cards']) == 1
        
        # Test with no matching cards
        result = edge_case_manager.create_display_case(
            name='Empty Case',
            description='No Cards',
            tags=['nonexistent']
        )
        assert result is None
        
        # Test with empty tags
        result = edge_case_manager.create_display_case(
            name='Empty Tags',
            description='No Tags',
            tags=[]
        )
        assert result is None
        
        # Test with invalid tags
        result = edge_case_manager.create_display_case(
            name='Invalid Tags',
            description='Bad Tags',
            tags=['', None, 123]
        )
        assert result is None

def test_display_case_total_value_calculation(edge_case_manager):
    """Test total value calculation with various value formats"""
    with patch('modules.database.service.DatabaseService.save_user_display_cases') as mock_save:
        mock_save.return_value = True
        
        # Create a case with mixed value formats
        result = edge_case_manager.create_display_case(
            name='Mixed Values',
            description='Cards with various value formats',
            tags=['rookie', 'baseball']
        )
        
        assert result is not None
        assert isinstance(result['total_value'], float)
        assert result['total_value'] == 15.0  # Only valid value should be counted

def test_display_case_serialization(edge_case_manager):
    """Test display case serialization for storage"""
    with patch('modules.database.service.DatabaseService.save_user_display_cases') as mock_save:
        mock_save.return_value = True
        
        # Create a case with various data types
        result = edge_case_manager.create_display_case(
            name='Serialization Test',
            description='Testing serialization',
            tags=['rookie']
        )
        
        assert result is not None
        # Verify all values are serializable types
        assert all(isinstance(v, (str, int, float, list, dict, bool, type(None))) 
                  for v in result.values())
        # Verify all card values are serializable
        assert all(isinstance(v, (str, int, float, list, dict, bool, type(None))) 
                  for card in result['cards'] 
                  for v in card.values()) 