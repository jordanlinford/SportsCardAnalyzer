import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import re
import urllib.parse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import quote

class EbayScraper:
    """A class to scrape eBay for sports card listings."""
    
    def __init__(self):
        """Initialize the scraper with proper headers and session setup."""
        # Set up a session with retries
        self.session = requests.Session()
        
        # Configure retries
        retries = Retry(
            total=5,
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504]
        )
        
        # Add retry adapter to session
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        
        # Set up headers to mimic a browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })

    def build_search_query(self, player_name, year=None, card_set=None, variation=None, card_number=None, negative_keywords=None, scenario="Raw"):
        """Build the search query for eBay based on scenario"""
        print("\n=== Building Search Query ===")
        print(f"Input parameters:")
        print(f"Player: {player_name}")
        print(f"Year: {year}")
        print(f"Set: {card_set}")
        print(f"Card Number: {card_number}")
        print(f"Variation: {variation}")
        print(f"Scenario: {scenario}")
        print(f"Negative Keywords: {negative_keywords}")
        
        # Build the main query parts
        query_parts = []
        
        # Add required fields first
        if year:
            query_parts.append(year)
        if player_name:
            query_parts.append(player_name)
        if card_set:
            query_parts.append(card_set)
        if card_number:
            # Handle different card number formats
            card_number = card_number.strip()
            if not card_number.startswith('#'):
                card_number = f"#{card_number}"
            query_parts.append(card_number)
            
        # Handle scenario-specific search terms
        if scenario == "Raw":
            query_parts.append("-PSA -SGC -BGS")
        elif scenario == "PSA 9":
            query_parts.append('"PSA 9"')
        elif scenario == "PSA 10":
            query_parts.append('"PSA 10"')
            
        # Filter out any None or empty strings
        query_parts = [part for part in query_parts if part]
        
        # Add negative keywords if provided
        if negative_keywords:
            if isinstance(negative_keywords, str):
                negative_keywords = [kw.strip() for kw in negative_keywords.split(',')]
            for term in negative_keywords:
                if term:
                    query_parts.append(f"-{term}")
        
        # Only add default exclusions if no specific variation is requested
        if not variation:
            query_parts.extend([
                "-reprint -fake -replica -custom",
                "-purple -blue -red -green -orange -pink -yellow -gold -silver -bronze",  # Exclude color variations
                "-shock -velocity -hyper -prizm -mosaic -select -chrome -contenders",  # Exclude other variations
                "-autograph -auto -patch -relic -memorabilia",  # Exclude special editions
                "-wave -holo -refractor"  # Exclude common variations
            ])
        else:
            # If variation is specified, add it with quotes to ensure exact match
            query_parts.append(f'"{variation}"')
        
        query = " ".join(query_parts)
        print(f"\nFinal search query: {query}")
        return query

    def _extract_date(self, date_element):
        """Extract and format the sale date from the date element"""
        try:
            if not date_element:
                print("No date element provided")
                return None
                
            # Find the actual date text within the element
            date_span = date_element.find('span', class_='s-item__caption--signal')
            if date_span:
                date_text = date_span.get_text().strip()
            else:
                date_text = date_element.get_text().strip()
                
            print(f"Raw date text: {date_text}")
            
            # Clean up the date text
            date_text = date_text.replace('Sold', '').strip()
            print(f"Cleaned date text: {date_text}")
            
            # Handle relative dates
            if 'd ago' in date_text:
                days = int(date_text.split()[0])
                date = datetime.now() - timedelta(days=days)
                print(f"Converted relative date: {date.strftime('%Y-%m-%d')}")
                return date.strftime('%Y-%m-%d')
            elif 'h ago' in date_text:
                hours = int(date_text.split()[0])
                date = datetime.now() - timedelta(hours=hours)
                print(f"Converted relative date: {date.strftime('%Y-%m-%d')}")
                return date.strftime('%Y-%m-%d')
            elif 'm ago' in date_text:
                minutes = int(date_text.split()[0])
                date = datetime.now() - timedelta(minutes=minutes)
                print(f"Converted relative date: {date.strftime('%Y-%m-%d')}")
                return date.strftime('%Y-%m-%d')
            
            # Try to parse regular date format
            try:
                # Extract just the date part (e.g., "Jan 15, 2025")
                date_match = re.search(r'([A-Za-z]+ \d{1,2}, \d{4})', date_text)
                if date_match:
                    date_text = date_match.group(1)
                    date = datetime.strptime(date_text, '%b %d, %Y')
                    
                    # Validate the date is not in the future
                    current_date = datetime.now()
                    if date > current_date:
                        print(f"Found future date {date.strftime('%Y-%m-%d')}, using current date instead")
                        date = current_date
                    
                    print(f"Parsed regular date: {date.strftime('%Y-%m-%d')}")
                    return date.strftime('%Y-%m-%d')
                else:
                    print(f"No date pattern found in text: {date_text}")
                    return None
            except ValueError as e:
                print(f"Failed to parse regular date format: {date_text}")
                return None
                
        except Exception as e:
            print(f"Error extracting date: {str(e)}")
            return None

    def _extract_price(self, elem):
        """Extract price from an element"""
        if not elem:
            return None
        try:
            price_text = elem.get_text().strip()
            # Remove currency symbol and commas, then convert to float
            price = float(price_text.replace('$', '').replace(',', ''))
            return price
        except (ValueError, AttributeError):
            return None

    def search_cards(self, player_name, year=None, card_set=None, card_number=None, variation=None, scenario="Raw", negative_keywords=None):
        """Search for cards on eBay."""
        try:
            print("\n=== Starting Card Search ===")
            
            # Build the search query
            search_query = self.build_search_query(
                player_name=player_name,
                year=year,
                card_set=card_set,
                card_number=card_number,
                variation=variation,
                scenario=scenario,
                negative_keywords=negative_keywords
            )
            
            # Encode the search query for URL
            encoded_query = quote(search_query)
            
            # Construct the eBay URL with more inclusive parameters
            url = f"https://www.ebay.com/sch/i.html?_nkw={encoded_query}&_sacat=0&LH_Sold=1&_ipg=240&_sop=12&_dmd=1&_udlo=&_udhi=&_samilow=&_samihi=&_sadis=200&_stpos=&_sargn=-1%26saslc%3D1&_salic=1&_fosrp=1"
            print(f"\nMaking request to eBay with URL: {url}")
            
            # Make the request
            response = self.session.get(url)
            print(f"Received response with status code: {response.status_code}")
            
            if response.status_code != 200:
                print("Failed to get response from eBay")
                return []
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            print("\nParsing HTML response...")
            
            # Try different methods to find items
            items = []
            
            # Method 1: Search for srp-results container
            container = soup.find('ul', class_='srp-results')
            if container:
                items = container.find_all(['li', 'div'], class_=['s-item', 's-item__pl-on-bottom'])
                print(f"Found {len(items)} items using srp-results container")
            
            # Method 2: Search for item wrappers if Method 1 failed
            if not items:
                items = soup.find_all(['div', 'li'], class_=['s-item__wrapper', 's-item'])
                print(f"Found {len(items)} items using wrapper classes")
            
            # Method 3: Search for item info containers if Method 2 failed
            if not items:
                items = soup.find_all('div', class_=['s-item__info', 'srp-river-result'])
                print(f"Found {len(items)} items using info classes")
            
            if not items:
                print("No items found in search results")
                return []
            
            print(f"\nProcessing {len(items)} items...")
            
            # Process each item
            results = []
            for idx, item_html in enumerate(items, 1):
                print(f"\nProcessing item {idx}/{len(items)}")
                item_data = self.process_item(item_html)
                if item_data:
                    results.append(item_data)
                    print(f"Successfully added item {idx} to results")
            
            print(f"\nSearch complete. Found {len(results)} valid items.")
            return results
            
        except Exception as e:
            print(f"Error in search_cards: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def calculate_volatility_score(self, prices):
        """Calculate price volatility score (1-10)"""
        if len(prices) < 2:
            return 5  # Default middle score if insufficient data
            
        # Calculate standard deviation of prices
        std_dev = np.std(prices)
        mean_price = np.mean(prices)
        
        # Normalize volatility score (1-10)
        volatility = min(10, max(1, (std_dev / mean_price) * 20))
        return round(volatility, 1)

    def calculate_trend_score(self, df):
        """Calculate trend score (1-10) based on price and volume trends"""
        if len(df) < 2:
            return 5  # Default middle score if insufficient data
            
        # Calculate price trend
        price_slope = np.polyfit(range(len(df)), df['price'], 1)[0]
        price_trend = 1 if price_slope > 0 else -1
        
        # Calculate volume trend (assuming equal time intervals)
        volume_slope = np.polyfit(range(len(df)), df['volume'], 1)[0]
        volume_trend = 1 if volume_slope > 0 else -1
        
        # Combine trends into score (1-10)
        trend_score = 5 + (price_trend + volume_trend) * 2.5
        return round(min(10, max(1, trend_score)), 1)

    def calculate_liquidity_score(self, df):
        """Calculate liquidity score (1-10) based on sales frequency"""
        if len(df) < 2:
            return 5  # Default middle score if insufficient data
            
        # Calculate average days between sales
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.sort_values('date')
        days_between_sales = df['date'].diff().dt.days.mean()
        
        # Handle NaN values
        if pd.isna(days_between_sales):
            return 5  # Default middle score if we can't calculate days between sales
        
        # Convert to liquidity score (1-10)
        # Lower days between sales = higher liquidity score
        liquidity = 10 - min(9, int(days_between_sales / 10))
        return max(1, liquidity)

    def analyze_market_data(self, results):
        """Analyze the market data from search results"""
        if not results:
            return None
            
        df = pd.DataFrame(results)
        
        # Convert date strings to datetime objects
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')
        
        # Sort by date
        df = df.sort_values('date')
        
        if df.empty:
            return None
            
        # Add volume column (1 sale per row)
        df['volume'] = 1
        
        # Remove outliers using IQR method
        Q1 = df['price'].quantile(0.25)
        Q3 = df['price'].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # Filter out outliers
        df_filtered = df[(df['price'] >= lower_bound) & (df['price'] <= upper_bound)]
        
        # Calculate scores using filtered data
        volatility_score = self.calculate_volatility_score(df_filtered['price'].values)
        trend_score = self.calculate_trend_score(df_filtered)
        liquidity_score = self.calculate_liquidity_score(df_filtered)
        
        # Prepare price data for chart (using filtered data)
        price_data = []
        for _, row in df_filtered.iterrows():
            price_data.append({
                'date': row['date'].strftime('%Y-%m-%d'),
                'price': float(row['price'])
            })
        
        return {
            'average_price': float(df_filtered['price'].mean()),
            'lowest_price': float(df_filtered['price'].min()),
            'highest_price': float(df_filtered['price'].max()),
            'price_data': price_data,
            'volatility_score': volatility_score,
            'trend_score': trend_score,
            'liquidity_score': liquidity_score,
            'total_sales': len(df_filtered),
            'original_sales': len(df),  # Keep track of original number of sales
            'outliers_removed': len(df) - len(df_filtered)  # Number of outliers removed
        }

    def get_item_image(self, item_html):
        """Get the main image URL for an item."""
        try:
            print("\n=== Image Retrieval Debug ===")
            
            # Method 1: Look for the image container first
            print("\nLooking for image container...")
            image_container = (
                item_html.find("div", class_="s-item__image") or
                item_html.find("div", class_="s-item__image-wrapper") or
                item_html.find("div", class_="s-item__image-section") or
                item_html.find("div", class_="s-item__image-container") or
                item_html.find("div", class_="s-item__image-section--completed") or
                item_html.find("div", class_="s-item__image-section--completed--completed") or
                item_html.find("div", class_="s-item__image-section--completed--completed--completed") or
                item_html.find("div", class_="s-item__image-section--completed--completed--completed--completed") or
                item_html.find("div", class_="s-item__image-section--completed--completed--completed--completed--completed")
            )
            
            if image_container:
                print("Found image container!")
                print(f"Container classes: {image_container.get('class', [])}")
                
                # Look for image within the container
                image_elem = (
                    image_container.find("img") or
                    image_container.find("img", class_="s-item__image-img") or
                    image_container.find("img", class_="s-item__image--img") or
                    image_container.find("img", class_="s-item__image-img--img") or
                    image_container.find("img", class_="s-item__image--img--completed") or
                    image_container.find("img", class_="s-item__image--img--completed--completed") or
                    image_container.find("img", class_="s-item__image--img--completed--completed--completed") or
                    image_container.find("img", class_="s-item__image--img--completed--completed--completed--completed") or
                    image_container.find("img", class_="s-item__image--img--completed--completed--completed--completed--completed")
                )
                
                if image_elem:
                    print("Found image element in container!")
                    print(f"Image classes: {image_elem.get('class', [])}")
                    return self._extract_image_url(image_elem)
                else:
                    print("No image found in container")
            else:
                print("No image container found")
            
            # Method 2: Try direct search for image
            print("\nTrying direct search for image...")
            image_elem = (
                item_html.find("img", class_="s-item__image-img") or
                item_html.find("img", class_="s-item__image") or
                item_html.find("img", class_="s-item__image--img") or
                item_html.find("img", class_="s-item__image-img--img") or
                item_html.find("img", class_="s-item__image--img--img") or
                item_html.find("img", class_="s-item__image--img--completed") or
                item_html.find("img", class_="s-item__image--img--completed--completed") or
                item_html.find("img", class_="s-item__image--img--completed--completed--completed") or
                item_html.find("img", class_="s-item__image--img--completed--completed--completed--completed") or
                item_html.find("img", class_="s-item__image--img--completed--completed--completed--completed--completed")
            )
            
            if image_elem:
                print("Found image element in direct search!")
                print(f"Image classes: {image_elem.get('class', [])}")
                return self._extract_image_url(image_elem)
            else:
                print("No image found in direct search")
            
            # Method 3: Try finding any img tag in the item
            print("\nTrying to find any img tag in item...")
            image_elem = item_html.find("img")
            if image_elem:
                print("Found generic img tag!")
                print(f"Image classes: {image_elem.get('class', [])}")
                return self._extract_image_url(image_elem)
            else:
                print("No generic img tag found")
            
            print("No image element found to extract URL from")
            return None

        except Exception as e:
            print(f"Error getting image: {str(e)}")
            return None

    def _extract_image_url(self, image_elem):
        """Extract and clean the image URL from an image element."""
        try:
            print("\nExtracting image URL...")
            
            # Try different image URL sources in order of preference
            for attr in ['data-src', 'src', 'data-img-src', 'data-srcset']:
                image_url = image_elem.get(attr)
                if image_url:
                    print(f"Found URL in {attr}: {image_url}")
                    
                    # Remove query parameters
                    image_url = image_url.split("?")[0]
                    
                    # Convert protocol-relative URLs to HTTPS
                    if image_url.startswith("//"):
                        image_url = "https:" + image_url
                        print(f"Converted to absolute URL: {image_url}")
                    elif image_url.startswith("/"):
                        image_url = "https://www.ebay.com" + image_url
                        print(f"Converted to absolute URL: {image_url}")
                    
                    # Convert HTTP to HTTPS
                    if image_url.startswith("http://"):
                        image_url = "https://" + image_url[7:]
                        print(f"Converted to HTTPS: {image_url}")
                    
                    # Skip placeholder images
                    if "placeholder" in image_url.lower() or "no-image" in image_url.lower():
                        print("Skipping placeholder image")
                        continue
                    
                    # Get highest resolution version
                    if 's-l' in image_url:
                        # Replace common eBay image size indicators with larger versions
                        for size in ['s-l64', 's-l96', 's-l140', 's-l160', 's-l225', 's-l300']:
                            if size in image_url:
                                image_url = image_url.replace(size, 's-l1000')
                                print(f"Upgraded to high resolution: {image_url}")
                                break
                    
                    print(f"Final image URL: {image_url}")
                    return image_url
            
            print("No valid image URL found")
            return None
            
        except Exception as e:
            print(f"Error extracting image URL: {str(e)}")
            return None

    def process_item(self, item_html):
        """Process a single item from the search results."""
        try:
            print("\n=== Processing Item ===")
            
            # Get the title
            title_elem = (
                item_html.find("div", class_="s-item__title") or
                item_html.find("span", class_="s-item__title") or
                item_html.find("h3", class_="s-item__title")
            )
            
            if not title_elem:
                print("No title element found")
                return None
            
            title = title_elem.get_text().strip()
            if not title or title.lower() == "shop on ebay":
                print("Invalid title or 'Shop on eBay' placeholder")
                return None
            
            print(f"Title: {title}")
            
            # Get the price
            price_elem = (
                item_html.find("span", class_="s-item__price") or
                item_html.find("span", class_="POSITIVE") or
                item_html.find("span", class_="NEGATIVE")
            )
            
            if not price_elem:
                print("No price element found")
                return None
            
            price_text = price_elem.get_text().strip()
            if not price_text:
                print("Empty price text")
                return None
            
            try:
                # Clean up price text and convert to float
                price = float(price_text.replace('$', '').replace(',', '').strip())
                if price <= 0:
                    print("Invalid price (<=0)")
                    return None
                print(f"Price: ${price:.2f}")
            except ValueError:
                print(f"Could not convert price text to float: {price_text}")
                return None
            
            # Get the sale date
            date_elem = (
                item_html.find("span", class_="s-item__ended-date") or
                item_html.find("span", class_="s-item__time-end") or
                item_html.find("span", class_="s-item__time-left") or
                item_html.find("div", class_="s-item__title--tagblock") or
                item_html.find("span", class_="POSITIVE") or
                item_html.find("span", class_="NEGATIVE")
            )
            
            sale_date = None
            if date_elem:
                sale_date = self._extract_date(date_elem)
                print(f"Sale date: {sale_date}")
            
            # Get the image URL
            image_url = None
            
            # First try the image wrapper
            image_wrapper = (
                item_html.find("div", class_="s-item__image-wrapper") or
                item_html.find("div", class_="s-item__image-section") or
                item_html.find("div", class_="s-item__image")
            )
            
            if image_wrapper:
                print("Found image wrapper")
                img_elem = image_wrapper.find("img")
                if img_elem:
                    image_url = self._extract_image_url(img_elem)
            
            # If no image found in wrapper, try direct image search
            if not image_url:
                print("Trying direct image search")
                img_elem = (
                    item_html.find("img", class_="s-item__image-img") or
                    item_html.find("img", class_="s-item__image") or
                    item_html.find("img")
                )
                if img_elem:
                    image_url = self._extract_image_url(img_elem)
            
            # Create item dictionary
            item = {
                'title': title,
                'price': price,
                'image_url': image_url,
                'date': sale_date
            }
            
            print("Successfully processed item:")
            print(f"Title: {title}")
            print(f"Price: ${price:.2f}")
            if image_url:
                print(f"Image URL: {image_url}")
            if sale_date:
                print(f"Sale Date: {sale_date}")
            
            return item
            
        except Exception as e:
            print(f"Error processing item: {str(e)}")
            import traceback
            traceback.print_exc()
            return None 