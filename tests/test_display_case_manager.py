import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch
from modules.display_case.manager import DisplayCaseManager
from modules.database.service import DatabaseService

@pytest.fixture
def sample_collection():
    """Create a sample collection for testing"""
    return pd.DataFrame({
        'player_name': ['Player 1', 'Player 2', 'Player 3'],
        'year': ['2020', '2021', '2022'],
        'card_set': ['Set A', 'Set B', 'Set C'],
        'card_number': ['123', '456', '789'],
        'variation': ['Base', 'Parallel', 'Auto'],
        'condition': ['MINT', 'NM', 'GOOD'],
        'purchase_price': [10.0, 20.0, 30.0],
        'current_value': [15.0, 25.0, 35.0],
        'tags': [['rookie', 'baseball'], ['auto', 'basketball'], ['parallel', 'football']],
        'photo': ['data:image/jpeg;base64,test1', 'data:image/jpeg;base64,test2', 'data:image/jpeg;base64,test3']
    })

@pytest.fixture
def display_case_manager(sample_collection):
    """Create a DisplayCaseManager instance for testing"""
    return DisplayCaseManager('test_uid', sample_collection)

def test_create_display_case(display_case_manager):
    """Test creating a new display case"""
    with patch('modules.database.service.DatabaseService.save_user_display_cases') as mock_save:
        mock_save.return_value = True
        
        result = display_case_manager.create_display_case(
            name='Test Case',
            description='Test Description',
            tags=['rookie', 'baseball']
        )
        
        assert result is not None
        assert result['name'] == 'Test Case'
        assert result['description'] == 'Test Description'
        assert len(result['cards']) == 1  # Should find one card with both rookie and baseball tags
        assert result['total_value'] == 15.0  # Value of the matching card
        mock_save.assert_called_once()

def test_create_simple_display_case(display_case_manager):
    """Test creating a simple display case with a single tag"""
    with patch('modules.database.service.DatabaseService.save_user_display_cases') as mock_save:
        mock_save.return_value = True
        
        result = display_case_manager.create_simple_display_case(
            name='Baseball Cards',
            tag='baseball'
        )
        
        assert result is not None
        assert result['name'] == 'Baseball Cards'
        assert len(result['cards']) == 1
        assert result['total_value'] == 15.0
        assert result['tags'] == ['baseball']
        mock_save.assert_called_once()

def test_load_display_cases(display_case_manager):
    """Test loading display cases from Firebase"""
    mock_cases = {
        'Case1': {
            'name': 'Case1',
            'description': 'Test Case',
            'tags': ['rookie'],
            'cards': [],
            'total_value': 0.0,
            'created_date': datetime.now().isoformat()
        }
    }
    
    with patch('modules.database.service.DatabaseService.get_user_display_cases') as mock_get:
        mock_get.return_value = mock_cases
        with patch('modules.database.service.DatabaseService.save_user_display_cases') as mock_save:
            mock_save.return_value = True
            
            result = display_case_manager.load_display_cases()
            
            assert result == mock_cases
            assert display_case_manager.display_cases == mock_cases
            mock_get.assert_called_once()

def test_delete_display_case(display_case_manager):
    """Test deleting a display case"""
    display_case_manager.display_cases = {
        'Test Case': {
            'name': 'Test Case',
            'description': 'Test Description',
            'tags': ['rookie'],
            'cards': [],
            'total_value': 0.0
        }
    }
    
    with patch('modules.database.service.DatabaseService.save_user_display_cases') as mock_save:
        mock_save.return_value = True
        with patch.object(display_case_manager, 'load_display_cases') as mock_load:
            
            result = display_case_manager.delete_display_case('Test Case')
            
            assert result is True
            assert 'Test Case' not in display_case_manager.display_cases
            mock_save.assert_called_once()
            mock_load.assert_called_once()

def test_update_display_case(display_case_manager):
    """Test updating a display case"""
    original_case = {
        'name': 'Test Case',
        'description': 'Original Description',
        'tags': ['rookie'],
        'cards': [],
        'total_value': 0.0
    }
    
    updated_case = {
        'name': 'Test Case',
        'description': 'Updated Description',
        'tags': ['rookie', 'baseball'],
        'cards': [],
        'total_value': 0.0
    }
    
    display_case_manager.display_cases = {'Test Case': original_case}
    
    with patch('modules.database.service.DatabaseService.save_user_display_cases') as mock_save:
        mock_save.return_value = True
        
        result = display_case_manager.update_display_case('Test Case', updated_case)
        
        assert result is True
        assert display_case_manager.display_cases['Test Case'] == updated_case
        mock_save.assert_called_once()

def test_filter_cards_by_tags(display_case_manager):
    """Test filtering cards by tags"""
    # Test with single tag
    result = display_case_manager._filter_cards_by_tags(['rookie'])
    assert len(result) == 1
    assert result[0]['player_name'] == 'Player 1'
    
    # Test with multiple tags
    result = display_case_manager._filter_cards_by_tags(['auto', 'basketball'])
    assert len(result) == 1
    assert result[0]['player_name'] == 'Player 2'
    
    # Test with non-matching tags
    result = display_case_manager._filter_cards_by_tags(['nonexistent'])
    assert len(result) == 0

def test_normalize_tags(display_case_manager):
    """Test tag normalization"""
    # Test string input
    result = display_case_manager._normalize_tags('rookie,auto')
    assert sorted(result) == ['auto', 'rookie']
    
    # Test list input
    result = display_case_manager._normalize_tags(['Rookie', 'AUTO'])
    assert sorted(result) == ['auto', 'rookie']
    
    # Test empty input
    result = display_case_manager._normalize_tags([])
    assert result == []
    
    # Test None input
    result = display_case_manager._normalize_tags(None)
    assert result == [] 