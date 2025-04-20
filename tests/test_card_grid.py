import unittest
from unittest.mock import patch, MagicMock
from modules.ui.components.CardGrid import render_card_grid

class TestCardGrid(unittest.TestCase):
    def setUp(self):
        # Mock Streamlit functions
        self.mock_markdown = MagicMock()
        self.mock_container = MagicMock()
        self.mock_info = MagicMock()
        
        # Patch Streamlit functions
        self.patcher_markdown = patch('streamlit.markdown', self.mock_markdown)
        self.patcher_container = patch('streamlit.container', self.mock_container)
        self.patcher_info = patch('streamlit.info', self.mock_info)
        
        # Start patches
        self.patcher_markdown.start()
        self.patcher_container.start()
        self.patcher_info.start()

    def tearDown(self):
        # Stop all patches
        self.patcher_markdown.stop()
        self.patcher_container.stop()
        self.patcher_info.stop()

    def test_empty_cards(self):
        """Test rendering with no cards"""
        render_card_grid([])
        self.mock_info.assert_called_once_with("No cards to display.")

    def test_single_card(self):
        """Test rendering with a single card"""
        cards = [{
            'photo': 'https://example.com/card1.jpg',
            'player_name': 'Test Player',
            'year': '2020',
            'card_set': 'Test Set',
            'current_value': 100.00
        }]

        render_card_grid(cards)

        # Verify the grid container was created
        self.mock_container.assert_called_once()

        # Verify the CSS styles were added
        self.mock_markdown.assert_any_call(
            """
    <style>
    .card-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        padding: 0.5rem;
    }
    
    .card-container {
        position: relative;
        width: 80px;
        height: 120px;
        border-radius: 4px;
        overflow: hidden;
        transition: transform 0.2s ease-in-out;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        background: #f5f5f5;
        flex: 0 0 auto;
    }

    .card-container:hover {
        transform: scale(1.05);
    }

    .card-img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        border-radius: 4px;
    }

    .card-overlay {
        position: absolute;
        bottom: 0;
        width: 100%;
        background: rgba(0,0,0,0.75);
        color: #fff;
        font-size: 0.6rem;
        padding: 0.2rem;
        text-align: center;
        opacity: 0;
        transition: opacity 0.3s ease-in-out;
    }

    .card-container:hover .card-overlay {
        opacity: 1;
    }
    </style>
    """,
            unsafe_allow_html=True
        )

        # Verify the grid start HTML
        self.mock_markdown.assert_any_call(
            '<div class="card-grid">',
            unsafe_allow_html=True
        )

        # Verify the card HTML was rendered
        self.mock_markdown.assert_any_call(
            """
            <div class="card-container">
                <img src="https://example.com/card1.jpg" class="card-img" onerror="this.src='https://placehold.co/80x120?text=No+Image';"/>
                <div class="card-overlay">
                    <strong>Test Player</strong><br/>
                    2020 Test Set<br/>
                    $100.00
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Verify the grid end HTML
        self.mock_markdown.assert_any_call(
            '</div>',
            unsafe_allow_html=True
        )

    def test_multiple_cards(self):
        """Test rendering with multiple cards"""
        cards = [
            {
                'photo': 'https://example.com/card1.jpg',
                'player_name': 'Player 1',
                'year': '2020',
                'card_set': 'Set 1',
                'current_value': 100.00
            },
            {
                'photo': 'https://example.com/card2.jpg',
                'player_name': 'Player 2',
                'year': '2021',
                'card_set': 'Set 2',
                'current_value': 200.00
            }
        ]

        render_card_grid(cards)

        # Verify the grid container was created
        self.mock_container.assert_called_once()

        # Verify the number of markdown calls
        # 1 for CSS, 1 for grid start, 2 for cards, 1 for grid end
        self.assertEqual(self.mock_markdown.call_count, 5)

    def test_missing_fields(self):
        """Test rendering with cards missing some fields"""
        cards = [{
            'photo': 'https://example.com/card1.jpg',
            'player_name': 'Test Player',
            # Missing year and card_set
            'current_value': 100.00
        }]

        render_card_grid(cards)

        # Verify the card HTML was rendered with empty values for missing fields
        self.mock_markdown.assert_any_call(
            """
            <div class="card-container">
                <img src="https://example.com/card1.jpg" class="card-img" onerror="this.src='https://placehold.co/80x120?text=No+Image';"/>
                <div class="card-overlay">
                    <strong>Test Player</strong><br/>
                     <br/>
                    $100.00
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    def test_invalid_image_url(self):
        """Test handling of invalid image URLs"""
        cards = [{
            'photo': 'invalid-url',
            'player_name': 'Test Player',
            'year': '2020',
            'card_set': 'Test Set',
            'current_value': 100.00
        }]

        render_card_grid(cards)

        # Verify the card HTML includes the fallback image
        self.mock_markdown.assert_any_call(
            """
            <div class="card-container">
                <img src="invalid-url" class="card-img" onerror="this.src='https://placehold.co/80x120?text=No+Image';"/>
                <div class="card-overlay">
                    <strong>Test Player</strong><br/>
                    2020 Test Set<br/>
                    $100.00
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

if __name__ == '__main__':
    unittest.main() 