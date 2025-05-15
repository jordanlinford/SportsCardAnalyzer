"""
Unit tests for the DisplayManager module
"""

import pytest
import pandas as pd
from modules.core.display_manager import DisplayManager
from modules.core.error_handler import ValidationError

def test_validate_collection():
    """Test collection validation"""
    # Valid collections
    assert DisplayManager.validate_collection([]) is False
    assert DisplayManager.validate_collection([{'player_name': 'Test'}]) is True
    assert DisplayManager.validate_collection(pd.DataFrame([{'player_name': 'Test'}])) is True
    
    # Invalid collections
    with pytest.raises(ValidationError):
        DisplayManager.validate_collection("not a collection")
    with pytest.raises(ValidationError):
        DisplayManager.validate_collection(123)

def test_validate_card():
    """Test card validation"""
    # Valid cards
    valid_card = {
        'player_name': 'Test Player',
        'year': '2023',
        'card_set': 'Test Set'
    }
    assert DisplayManager.validate_card(valid_card) is True
    
    # Invalid cards
    with pytest.raises(ValidationError):
        DisplayManager.validate_card("not a card")
    with pytest.raises(ValidationError):
        DisplayManager.validate_card({})
    with pytest.raises(ValidationError):
        DisplayManager.validate_card({'player_name': 'Test'})

def test_display_collection_grid(mocker):
    """Test grid display functionality"""
    # Mock Streamlit functions
    mocker.patch('streamlit.markdown')
    mocker.patch('streamlit.columns')
    mocker.patch('streamlit.button')
    
    # Test with valid collection
    collection = [{
        'player_name': 'Test Player',
        'year': '2023',
        'card_set': 'Test Set',
        'photo': 'test.jpg',
        'current_value': 100.00
    }]
    DisplayManager.display_collection_grid(collection)
    
    # Test with empty collection
    DisplayManager.display_collection_grid([])
    
    # Test with invalid collection
    with pytest.raises(ValidationError):
        DisplayManager.display_collection_grid("invalid")

def test_display_collection_table(mocker):
    """Test table display functionality"""
    # Mock Streamlit functions
    mocker.patch('streamlit.dataframe')
    
    # Test with valid collection
    collection = [{
        'player_name': 'Test Player',
        'year': '2023',
        'card_set': 'Test Set',
        'card_number': '1',
        'condition': 'Mint',
        'current_value': 100.00
    }]
    DisplayManager.display_collection_table(collection)
    
    # Test with DataFrame
    df = pd.DataFrame(collection)
    DisplayManager.display_collection_table(df)
    
    # Test with empty collection
    DisplayManager.display_collection_table([])

def test_display_card_details(mocker):
    """Test card details display functionality"""
    # Mock Streamlit functions
    mocker.patch('streamlit.image')
    mocker.patch('streamlit.subheader')
    mocker.patch('streamlit.write')
    mocker.patch('streamlit.columns')
    
    # Test with valid card
    card = {
        'player_name': 'Test Player',
        'year': '2023',
        'card_set': 'Test Set',
        'photo': 'test.jpg',
        'current_value': 100.00,
        'notes': 'Test notes',
        'tags': ['tag1', 'tag2']
    }
    DisplayManager.display_card_details(card)
    
    # Test with minimal card
    minimal_card = {
        'player_name': 'Test Player',
        'year': '2023',
        'card_set': 'Test Set'
    }
    DisplayManager.display_card_details(minimal_card)
    
    # Test with invalid card
    with pytest.raises(ValidationError):
        DisplayManager.display_card_details({})

def test_display_collection_stats(mocker):
    """Test stats display functionality"""
    # Mock Streamlit functions
    mocker.patch('streamlit.columns')
    mocker.patch('streamlit.metric')
    
    # Test with valid stats
    stats = {
        'total_cards': 100,
        'total_value': 1000.00,
        'unique_players': 50,
        'unique_sets': 10
    }
    DisplayManager.display_collection_stats(stats)
    
    # Test with empty stats
    DisplayManager.display_collection_stats({}) 