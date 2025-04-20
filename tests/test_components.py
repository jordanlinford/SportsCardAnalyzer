import unittest
from unittest.mock import patch, MagicMock
from modules.ui.components import CardDisplay
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px

class TestUIComponents(unittest.TestCase):
    def setUp(self):
        # Mock card data
        self.mock_card = {
            'name': 'Test Card',
            'player_name': 'Test Player',
            'year': 2020,
            'card_set': 'Test Set',
            'condition': 'PSA 9',
            'current_value': 100.0,
            'photo': 'https://example.com/image.jpg',
            'last_updated': datetime.now(),
            'price_history': [
                {'date': datetime.now() - timedelta(days=30), 'price': 80.0},
                {'date': datetime.now() - timedelta(days=15), 'price': 90.0},
                {'date': datetime.now(), 'price': 100.0}
            ]
        }
        
        # Mock market data
        self.mock_market_data = {
            'metrics': {
                'avg_price': 100.0,
                'price_change': 10.0,
                'volume': 50
            },
            'sales': [
                {'title': 'PSA 9 Test Card', 'price': 150.0},
                {'title': 'PSA 10 Test Card', 'price': 300.0}
            ]
        }

    @patch('streamlit.markdown')
    @patch('streamlit.columns')
    @patch('streamlit.button')
    def test_display_grid(self, mock_button, mock_columns, mock_markdown):
        """Test the CardDisplay.display_grid method"""
        # Mock columns return value
        mock_cols = [MagicMock() for _ in range(5)]
        mock_columns.return_value = mock_cols
        
        # Test with single card
        CardDisplay.display_grid([self.mock_card])
        
        # Verify markdown was called for styling and card display
        mock_markdown.assert_called()
        mock_columns.assert_called_with(5)

    @patch('streamlit.markdown')
    @patch('streamlit.columns')
    @patch('streamlit.number_input')
    @patch('streamlit.metric')
    def test_display_profit_calculator(self, mock_metric, mock_number_input, mock_columns, mock_markdown):
        """Test the CardDisplay.display_profit_calculator method"""
        # Mock input values
        mock_number_input.return_value = 50.0  # Purchase price
        
        # Mock columns return value
        mock_cols = [MagicMock() for _ in range(3)]
        mock_columns.return_value = mock_cols
        
        # Test calculator
        CardDisplay.display_profit_calculator(self.mock_card, self.mock_market_data)
        
        # Verify metrics were displayed
        self.assertEqual(mock_metric.call_count, 3)  # Current value, Profit/Loss, ROI
        mock_columns.assert_called_with(3)

if __name__ == '__main__':
    unittest.main() 