from ebay_scraper import EbayScraper
import json

def test_scraper():
    print("Initializing eBay Scraper...")
    scraper = EbayScraper()
    
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
    results = scraper.search_cards(**test_params)
    
    print(f"\nSearch completed. Found {len(results)} results.")
    
    if results:
        print("\nFirst 3 results:")
        for i, result in enumerate(results[:3]):
            print(f"\nResult {i+1}:")
            print(json.dumps(result, indent=2))
    else:
        print("\nNo results found.")

if __name__ == "__main__":
    test_scraper() 