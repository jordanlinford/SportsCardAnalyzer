from scrapers.ebay_scraper import EbayScraper
import json
import unittest

class TestEbayScraper(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.scraper = EbayScraper()
        
    def test_search_functionality(self):
        """Test the basic search functionality of the scraper."""
        # Test parameters
        test_params = {
            'player_name': 'Mike Trout',
            'year': '2011',
            'card_set': 'Topps Update',
            'variation': None,
            'card_number': '175',
            'negative_keywords': None,
            'scenario': 'Raw'
        }
        
        print("\nTest Parameters:")
        print(json.dumps(test_params, indent=2))
        
        print("\nStarting search...")
        results = self.scraper.search_cards(**test_params)
        
        # Assertions
        self.assertIsNotNone(results, "Search results should not be None")
        self.assertIsInstance(results, list, "Search results should be a list")
        
        print(f"\nSearch completed. Found {len(results)} results.")
        
        if results:
            print("\nFirst 3 results:")
            for i, result in enumerate(results[:3]):
                print(f"\nResult {i+1}:")
                print(json.dumps(result, indent=2))
                
                # Additional assertions for result structure
                self.assertIn('title', result, "Result should have a title")
                self.assertIn('price', result, "Result should have a price")
                self.assertIn('date', result, "Result should have a date")

    def test_psa_graded_search(self):
        """Test searching for PSA graded cards."""
        test_params = {
            'player_name': 'Mike Trout',
            'year': '2011',
            'card_set': 'Topps Update',
            'variation': None,
            'card_number': '175',
            'negative_keywords': None,
            'scenario': 'PSA 10'
        }
        
        results = self.scraper.search_cards(**test_params)
        self.assertIsNotNone(results)
        self.assertIsInstance(results, list)
        
        if results:
            for result in results:
                self.assertIn('PSA 10', result['title'].upper(), "Result should be a PSA 10 graded card")

    def test_negative_keywords(self):
        """Test the negative keywords functionality."""
        test_params = {
            'player_name': 'Mike Trout',
            'year': '2011',
            'card_set': 'Topps Update',
            'variation': None,
            'card_number': '175',
            'negative_keywords': 'reprint, fake',
            'scenario': 'Raw'
        }
        
        results = self.scraper.search_cards(**test_params)
        self.assertIsNotNone(results)
        
        if results:
            for result in results:
                title = result['title'].upper()
                self.assertNotIn('REPRINT', title, "Result should not contain 'reprint'")
                self.assertNotIn('FAKE', title, "Result should not contain 'fake'")

    def test_variation_search(self):
        """Test searching for specific card variations."""
        test_params = {
            'player_name': 'Mike Trout',
            'year': '2011',
            'card_set': 'Topps Update',
            'variation': 'Cognac Diamond',
            'card_number': '175',
            'negative_keywords': None,
            'scenario': 'Raw'
        }
        
        results = self.scraper.search_cards(**test_params)
        self.assertIsNotNone(results)
        
        if results:
            for result in results:
                title = result['title'].upper()
                self.assertIn('COGNAC', title, "Result should be a Cognac Diamond variation")

    def test_empty_results(self):
        """Test handling of searches with no results."""
        test_params = {
            'player_name': 'Nonexistent Player',
            'year': '9999',
            'card_set': 'Nonexistent Set',
            'variation': None,
            'card_number': '999',
            'negative_keywords': None,
            'scenario': 'Raw'
        }
        
        results = self.scraper.search_cards(**test_params)
        self.assertIsNotNone(results)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 0, "Search with no results should return empty list")

if __name__ == '__main__':
    unittest.main() 