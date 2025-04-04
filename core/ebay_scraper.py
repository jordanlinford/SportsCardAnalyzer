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

class EbayScraper:
    def __init__(self):
        self.base_url = "https://www.ebay.com/sch/i.html"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }
        
        # Set up retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,  # number of retries
            backoff_factor=1,  # wait 1, 2, 4 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504]  # HTTP status codes to retry on
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

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
        if variation:
            query_parts.append(variation)
            
        # Handle scenario-specific search terms
        if scenario == "Raw":
            query_parts.append("-PSA -SGC -BGS")
        elif scenario == "PSA 9":
            query_parts.append("PSA 9")
        elif scenario == "PSA 10":
            query_parts.append("PSA 10")
            
        # Filter out any None or empty strings
        query_parts = [part for part in query_parts if part]
        
        # Add negative keywords if provided
        if negative_keywords:
            if isinstance(negative_keywords, str):
                negative_keywords = [kw.strip() for kw in negative_keywords.split(',')]
            for term in negative_keywords:
                if term:
                    query_parts.append(f"-{term}")
        
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

    def _extract_price(self, price_element):
        """Extract and format the price from the price element"""
        if not price_element:
            return None
        
        try:
            price_text = price_element.get_text(strip=True)
            print(f"Raw price text: {price_text}")
            
            # Remove currency symbols and whitespace
            price_text = price_text.replace('$', '').replace(',', '').strip()
            
            # Handle "to" in price (e.g., "$1.00 to $2.00")
            if 'to' in price_text.lower():
                price_text = price_text.lower().split('to')[0].strip()
            
            # Convert to float
            try:
                return float(price_text)
            except ValueError:
                print(f"Could not convert price to float: {price_text}")
                return None
            
        except Exception as e:
            print(f"Error extracting price: {str(e)}")
            return None

    def search_cards(self, player_name, year=None, card_set=None, variation=None, card_number=None, negative_keywords=None, scenario=None, high_price=None):
        """Search for cards on eBay"""
        try:
            # Build the search query
            search_query = player_name
            if year:
                search_query += f" {year}"
            if card_set:
                search_query += f" {card_set}"
            if variation:
                search_query += f" {variation}"
            if card_number:
                search_query += f" #{card_number}"
            
            # Add negative keywords
            if negative_keywords:
                for keyword in negative_keywords.split(','):
                    search_query += f" -{keyword.strip()}"
            
            # Add scenario-specific terms
            if scenario == "Raw":
                search_query += " -PSA -SGC -BGS"
            elif scenario == "PSA 9":
                search_query += " PSA 9"
            elif scenario == "PSA 10":
                search_query += " PSA 10"
            
            # Encode the search query
            encoded_query = urllib.parse.quote(search_query)
            
            # Construct the eBay URL with high price parameter if provided
            url = f"https://www.ebay.com/sch/i.html?_nkw={encoded_query}&_sacat=0&_sop=12&_dmd=1&_ipg=200&LH_Sold=1&_udlo=&_udhi={high_price if high_price else ''}&_samilow=&_samihi=&_sadis=15&_stpos=&_sargn=-1%26saslc%3D1&_salic=1&_sop=12&_dmd=1&_ipg=200&_fosrp=1"
            
            print(f"Making request to eBay with URL: {url}")
            
            # Make the request
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            print(f"Received response with status code: {response.status_code}")
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all items
            items = soup.find_all('li', class_='s-item')
            print(f"Found {len(items)} items using s-item class")
            
            if not items:
                items = soup.find_all('div', class_='s-item__info')
                print(f"Found {len(items)} items using s-item__info class")
            
            if not items:
                items = soup.find_all('div', class_='s-item__wrapper')
                print(f"Found {len(items)} items using s-item__wrapper class")
            
            results = []
            
            # Process each item
            for idx, item in enumerate(items):
                print(f"\nProcessing item {idx + 1}")
                print(f"Item HTML: {str(item)[:500]}...")  # Print first 500 chars of HTML
                
                # Skip items with "Shop on eBay" title
                title_elem = item.find('div', class_='s-item__title')
                if title_elem and 'Shop on eBay' in title_elem.get_text():
                    print("Skipping 'Shop on eBay' listing")
                    continue
                
                # Extract title
                title = title_elem.get_text().strip() if title_elem else None
                print(f"Title: {title}")
                
                # Extract price
                price_elem = item.find('span', class_='s-item__price')
                price = self._extract_price(price_elem)
                print(f"Price: {price}")
                
                # Extract date - try multiple selectors and locations
                date_elem = None
                date_selectors = [
                    ('span', 's-item__sold-date'),
                    ('span', 's-item__ended-date'),
                    ('span', 's-item__time-left'),
                    ('span', 's-item__time-end'),
                    ('span', 's-item__time-left--completed'),
                    ('span', 's-item__sold-date--completed'),
                    ('span', 's-item__sold-date--completed--completed'),
                    ('span', 's-item__sold-date--completed--completed--completed'),
                    ('span', 's-item__sold-date--completed--completed--completed--completed'),
                    ('span', 's-item__sold-date--completed--completed--completed--completed--completed'),
                    ('div', 's-item__sold-date'),
                    ('div', 's-item__ended-date'),
                    ('div', 's-item__time-left'),
                    ('div', 's-item__time-end'),
                    ('div', 's-item__time-left--completed')
                ]
                
                # Try each selector
                for tag, class_name in date_selectors:
                    date_elem = item.find(tag, class_=class_name)
                    if date_elem:
                        print(f"Found date element with selector: {tag}.{class_name}")
                        break
                
                # If no date found, try finding any element containing "Sold" or "Ended"
                if not date_elem:
                    for elem in item.find_all(['span', 'div']):
                        text = elem.get_text().strip()
                        if 'Sold' in text or 'Ended' in text:
                            date_elem = elem
                            print(f"Found date element containing 'Sold' or 'Ended': {text}")
                            break
                
                print(f"Date element found: {'Yes' if date_elem else 'No'}")
                if date_elem:
                    print(f"Date element HTML: {str(date_elem)}")
                    print(f"Date element text: {date_elem.get_text().strip()}")
                date = self._extract_date(date_elem)
                print(f"Extracted date: {date}")
                
                # Extract image URL - try multiple methods
                image_url = None
                
                # Method 1: Look for img tag with data-defer-load attribute
                img_elem = item.find('img', attrs={'data-defer-load': True})
                if img_elem:
                    image_url = img_elem.get('data-defer-load')
                    print(f"Found image URL from data-defer-load: {image_url}")
                
                # Method 2: Look for img tag with src attribute
                if not image_url:
                    img_elem = item.find('img', attrs={'src': True})
                    if img_elem:
                        image_url = img_elem.get('src')
                        print(f"Found image URL from src: {image_url}")
                
                # Method 3: Look for img tag in s-item__image section
                if not image_url:
                    image_section = item.find('div', class_='s-item__image')
                    if image_section:
                        img_elem = image_section.find('img')
                        if img_elem:
                            image_url = img_elem.get('src') or img_elem.get('data-defer-load')
                            print(f"Found image URL from s-item__image section: {image_url}")
                
                # Clean up the image URL
                if image_url:
                    # Remove any query parameters
                    image_url = image_url.split('?')[0]
                    # Ensure we're using the highest quality version
                    if 's-l' in image_url:
                        image_url = image_url.replace('s-l64', 's-l500')
                        image_url = image_url.replace('s-l160', 's-l500')
                    print(f"Cleaned image URL: {image_url}")
                
                print(f"Final image URL: {image_url}")
                
                # Skip items with negative keywords
                if negative_keywords:
                    skip = False
                    for keyword in negative_keywords.split(','):
                        if keyword.strip().lower() in title.lower():
                            print(f"Skipping item due to negative keyword: {keyword.strip()}")
                            skip = True
                            break
                    if skip:
                        continue
                
                # Skip items that don't match the scenario
                if scenario == "Raw" and any(term in title.lower() for term in ['psa', 'sgc', 'bgs', 'graded']):
                    print("Skipping graded card in raw scenario")
                    continue
                elif scenario in ["PSA 9", "PSA 10"] and not any(term in title.lower() for term in [scenario.lower()]):
                    print(f"Skipping non-{scenario} card")
                    continue
                
                # Add the item to results
                results.append({
                    'title': title,
                    'price': price,
                    'date': date,
                    'image_url': image_url
                })
                print(f"Added item to results: {title}")
            
            print(f"\nTotal items processed: {len(results)}")
            return results
            
        except requests.exceptions.Timeout:
            print("Request timed out")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {str(e)}")
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
            print(f"Available attributes: {list(image_elem.attrs.keys())}")
            
            # Check each attribute individually
            for attr in ['src', 'data-src', 'data-img-src', 'data-srcset']:
                value = image_elem.get(attr)
                if value:
                    print(f"Found {attr}: {value}")
            
            image_url = (
                image_elem.get("src") or
                image_elem.get("data-src") or
                image_elem.get("data-img-src") or
                image_elem.get("data-srcset", "").split(",")[0].strip().split(" ")[0] or
                image_elem.get("data-srcset", "").split(",")[-1].strip().split(" ")[0]  # Try the last srcset URL
            )
            
            # Clean up the URL
            if image_url:
                print(f"\nCleaning up URL: {image_url}")
                # Remove any URL parameters that might affect the image
                image_url = image_url.split("?")[0]
                
                # If URL is relative, make it absolute
                if image_url.startswith("//"):
                    image_url = "https:" + image_url
                    print(f"Converted relative URL: {image_url}")
                elif image_url.startswith("/"):
                    image_url = "https://www.ebay.com" + image_url
                    print(f"Converted root-relative URL: {image_url}")
                
                # Ensure the URL is using HTTPS
                if image_url.startswith("http://"):
                    image_url = "https://" + image_url[7:]
                    print(f"Converted to HTTPS: {image_url}")
                
                # Skip placeholder images
                if "placeholder" in image_url.lower() or "no-image" in image_url.lower():
                    print("Skipping placeholder image")
                    return None
                else:
                    print(f"Final image URL: {image_url}")
                    return image_url
            else:
                print("No valid image URL found in any attribute")
                return None
            
        except Exception as e:
            print(f"Error extracting image URL: {str(e)}")
            return None 