"""
Interface for the eBay scraper.
This module provides a stable interface for interacting with the eBay scraper.
Other modules should use this interface rather than accessing the scraper directly.
"""

from typing import List, Dict, Any, Optional
from .ebay_scraper import EbayScraper

class EbayInterface:
    """Interface for the eBay scraper that provides stability and protection."""
    
    def __init__(self):
        """Initialize the interface with a new scraper instance."""
        self.scraper = EbayScraper()
        self._version = "1.0.0"
    
    def search_cards(self,
                    player_name: str,
                    year: Optional[str] = None,
                    card_set: Optional[str] = None,
                    card_number: Optional[str] = None,
                    variation: Optional[str] = None,
                    scenario: Optional[str] = None,
                    negative_keywords: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for cards using the eBay scraper.
        This method provides a stable interface that won't change even if the underlying scraper changes.
        
        Args:
            player_name: Name of the player to search for
            year: Year of the card (optional)
            card_set: Name of the card set (optional)
            card_number: Card number in the set (optional)
            variation: Specific variation of the card (optional)
            scenario: Card condition ("Raw", "PSA 9", or "PSA 10")
            negative_keywords: Keywords to exclude from search (optional)
            
        Returns:
            List of dictionaries containing card information
        """
        try:
            results = self.scraper.search_cards(
                player_name=player_name,
                year=year,
                card_set=card_set,
                card_number=card_number,
                variation=variation,
                scenario=scenario,
                negative_keywords=negative_keywords
            )
            return results
        except Exception as e:
            print(f"Error searching cards: {str(e)}")
            return []
    
    def get_graded_card_data(self, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get historical sales data for PSA 9 and PSA 10 versions of the card."""
        # Extract base card information
        title = card_data['title']
        # Remove any existing grade information from the title
        base_title = ' '.join([word for word in title.split() if 'psa' not in word.lower()])
        
        # Extract player name from the base title (assuming it's the first part)
        player_name = base_title.split()[0]

        # Search for PSA 9 and PSA 10 versions
        psa9_results = self.search_cards(
            player_name=player_name,
            scenario="PSA 9",
            negative_keywords="10"  # Exclude PSA 10 results
        )

        psa10_results = self.search_cards(
            player_name=player_name,
            scenario="PSA 10"
        )

        # Calculate average prices if data is available
        psa9_avg = sum(r['price'] for r in psa9_results) / len(psa9_results) if psa9_results else None
        psa10_avg = sum(r['price'] for r in psa10_results) / len(psa10_results) if psa10_results else None

        return {
            'psa9': {
                'avg_price': psa9_avg,
                'sales_count': len(psa9_results),
                'recent_sales': psa9_results[:5]  # Include 5 most recent sales for reference
            },
            'psa10': {
                'avg_price': psa10_avg,
                'sales_count': len(psa10_results),
                'recent_sales': psa10_results[:5]  # Include 5 most recent sales for reference
            }
        }
    
    def get_scraper_version(self) -> str:
        """Get the current version of the scraper."""
        return self._version
    
    def get_scraper_status(self) -> Dict[str, Any]:
        """Get the current status of the scraper."""
        return {
            "status": "active",
            "version": self.get_scraper_version(),
            "type": "ebay"
        } 