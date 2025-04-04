import traceback
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from modules.core.market_analysis import MarketAnalyzer
from modules.core.price_predictor import PricePredictor
from modules.firebase.user_management import UserManager
from scrapers.ebay_interface import EbayInterface
from modules.ui.components import CardDisplay, display_profit_calculator
import base64
import requests
import re
from modules.firebase.config import db
import os
from modules.database.service import DatabaseService
from modules.database.models import Card, CardCondition
from typing import List, Dict, Any, Union

# Configure the page
st.set_page_config(
    page_title="Market Analysis - Sports Card Analyzer Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"  # Collapse sidebar by default on mobile
)

# Add mobile-specific CSS
st.markdown("""
<style>
    /* Mobile-friendly adjustments for market analysis */
    @media (max-width: 640px) {
        /* Make search form full width */
        .stForm {
            width: 100% !important;
        }
        
        /* Adjust chart size */
        .js-plotly-plot {
            height: 300px !important;
        }
        
        /* Stack metrics vertically */
        [data-testid="stMetricValue"] {
            font-size: 1.2rem !important;
        }
        
        /* Adjust card display */
        .card-image {
            max-width: 200px !important;
            margin: 0 auto !important;
            display: block !important;
        }
        
        /* Make price segments stack */
        .price-segment {
            width: 100% !important;
            margin-bottom: 1rem !important;
        }
    }
    
    /* General improvements */
    .search-results {
        overflow-x: auto !important;
    }
    
    .variation-card {
        border: 1px solid #ddd;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    .grade-card {
        border: 1px solid #ddd;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        background-color: #f8f9fa;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .grade-card h4 {
        margin: 0 0 0.5rem 0;
        color: #2c3e50;
    }
    
    .grade-card p {
        margin: 0.25rem 0;
        color: #34495e;
    }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    """Initialize session state variables."""
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'uid' not in st.session_state:
        st.session_state.uid = None
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'selected_card' not in st.session_state:
        st.session_state.selected_card = None
    if 'market_data' not in st.session_state:
        st.session_state.market_data = None
    if 'search_params' not in st.session_state:
        st.session_state.search_params = {}
    if 'collection' not in st.session_state:
        st.session_state.collection = load_collection_from_firebase()

def reset_session_state():
    """Reset all session state variables"""
    st.session_state.search_results = None
    st.session_state.selected_card = None
    st.session_state.market_data = None
    st.session_state.search_params = {}

def get_variation_groups(results):
    """Group cards by their variations based on common keywords"""
    variation_keywords = [
        'press proof', 'optic', 'canvas', 'pink', 'red', 'blue', 'yellow', 'green',
        'bronze', 'negative', 'variation', 'prizm', 'wave', 'holo', 'refractor'
    ]
    
    groups = {}
    ungrouped = []
    
    for card in results:
        title_lower = card['title'].lower()
        found_variations = [kw for kw in variation_keywords if kw in title_lower]
        
        # Only group if we found specific variations
        if found_variations:
            variations_key = ' '.join(sorted(found_variations))
            if variations_key not in groups:
                groups[variations_key] = {
                    'cards': [],
                    'representative_image': None,
                    'variation_name': variations_key.title(),
                    'price_range': [float('inf'), 0],
                    'count': 0
                }
            
            group = groups[variations_key]
            group['cards'].append(card)
            group['count'] += 1
            
            price = card['price']
            group['price_range'][0] = min(group['price_range'][0], price)
            group['price_range'][1] = max(group['price_range'][1], price)
            
            if not group['representative_image'] and card.get('image_url'):
                group['representative_image'] = card['image_url']
        else:
            # If no variations found, put in base group
            if 'base' not in groups:
                groups['base'] = {
                    'cards': [],
                    'representative_image': None,
                    'variation_name': 'Base Card',
                    'price_range': [float('inf'), 0],
                    'count': 0
                }
            groups['base']['cards'].append(card)
            groups['base']['count'] += 1
            
            price = card['price']
            groups['base']['price_range'][0] = min(groups['base']['price_range'][0], price)
            groups['base']['price_range'][1] = max(groups['base']['price_range'][1], price)
            
            if not groups['base']['representative_image'] and card.get('image_url'):
                groups['base']['representative_image'] = card['image_url']
    
    return groups

def add_to_collection(card_data, market_data):
    """Add a card from market analysis to collection"""
    try:
        # First, show the card details and market data for confirmation
        st.subheader("Confirm Card Details")
        
        cols = st.columns([1, 2])
        with cols[0]:
            if card_data.get('image_url'):
                st.image(card_data['image_url'], 
                        use_column_width=True,
                        output_format="JPEG",
                        caption=card_data['title'])
        
        with cols[1]:
            st.write("Card Information:")
            st.write(f"Title: {card_data['title']}")
            st.write(f"Price: ${card_data['price']:.2f}")
            st.write(f"Sale Date: {card_data['date']}")
            
            if market_data:
                st.write("\nMarket Analysis:")
                st.write(f"Average Price: ${market_data['metrics']['avg_price']:.2f}")
                st.write(f"Price Range: ${market_data['metrics']['low_price']:.2f} - ${market_data['metrics']['high_price']:.2f}")
                st.write(f"Volatility Score: {market_data['scores']['volatility_score']:.1f}/10")
                st.write(f"Trend Score: {market_data['scores']['trend_score']:.1f}/10")
                st.write(f"Liquidity Score: {market_data['scores']['liquidity_score']:.1f}/10")
        
        # Add option to search for a different card
        st.write("---")
        search_new = st.checkbox("Search for a different card?")
        
        if search_new:
            with st.form("search_different_card"):
                cols = st.columns(3)
                with cols[0]:
                    player_name = st.text_input("Player Name")
                    year = st.text_input("Year")
                with cols[1]:
                    card_set = st.text_input("Card Set")
                    card_number = st.text_input("Card Number")
                with cols[2]:
                    variation = st.text_input("Variation")
                    condition = st.selectbox("Condition", ["Raw", "PSA 10", "PSA 9", "SGC 10", "SGC 9.5", "SGC 9"])
                
                negative_keywords = st.text_input(
                    "Exclude Keywords (comma-separated)",
                    help="Enter keywords to exclude from search, separated by commas"
                )
                
                if st.form_submit_button("Search"):
                    scraper = EbayInterface()
                    analyzer = MarketAnalyzer()
                    
                    search_params = {
                        'player_name': player_name,
                        'year': year,
                        'card_set': card_set,
                        'card_number': card_number,
                        'variation': variation,
                        'negative_keywords': negative_keywords,
                        'scenario': condition
                    }
                    
                    with st.spinner("Searching for card..."):
                        results = scraper.search_cards(**search_params)
                        if results:
                            new_market_data = analyzer.analyze_market_data(results)
                            card_data = results[0]  # Use the first result
                            market_data = new_market_data
                            st.success("Card found! Please proceed with adding to collection.")
                            st.rerun()
                        else:
                            st.error("No results found. Please try adjusting your search parameters.")
                            return False
        
        st.write("---")
        st.subheader("Add to Collection")
        
        # Extract card details from title
        title = card_data['title']
        # Extract player name (assuming it's the first part before the year)
        player_name = title.split()[0:2]  # Take first two words as player name
        player_name = " ".join(player_name)
        
        # Extract year (looking for 4-digit number)
        year_match = re.search(r'\b\d{4}\b', title)
        year = year_match.group(0) if year_match else ""
        
        # Extract card set (text between year and card number, if present)
        set_match = re.search(rf'{year}\s+(.*?)(?:\s+#|\s+Card|\s+RC|\s+Rookie|\s+PSA|\s+SGC|\s+BGS|$)', title)
        card_set = set_match.group(1) if set_match else ""
        
        # Extract card number
        number_match = re.search(r'#(\d+)', title)
        card_number = number_match.group(1) if number_match else ""
        
        # Extract variation (look for common parallel terms)
        variation_terms = ['Parallel', 'Refractor', 'Prizm', 'Holo', 'Gold', 'Silver', 'Bronze', 
                          'Red', 'Blue', 'Green', 'Yellow', 'Purple', 'Orange', 'Pink']
        variation = next((term for term in variation_terms if term.lower() in title.lower()), "")
        
        # Get purchase details
        with st.form("add_card_form"):
            col1, col2 = st.columns(2)
            with col1:
                player_name = st.text_input("Player Name", value=player_name)
                year = st.text_input("Year", value=year)
                card_set = st.text_input("Card Set", value=card_set)
                card_number = st.text_input("Card Number", value=card_number)
            
            with col2:
                variation = st.text_input("Variation", value=variation)
                condition = st.selectbox("Condition", ["Raw", "PSA 9", "PSA 10"])
                purchase_price = st.number_input("Purchase Price ($)", min_value=0.0, format="%.2f")
                purchase_date = st.date_input("Purchase Date")
            
            notes = st.text_area("Notes")
            tags = st.text_input("Tags (comma-separated)", help="Add tags to help organize your collection")
            
            submitted = st.form_submit_button("Add to Collection")
            
            if submitted:
                try:
                    # Handle image data
                    photo_data = None
                    if card_data.get('image_url'):
                        try:
                            st.write("Attempting to fetch image from:", card_data['image_url'])
                            response = requests.get(card_data['image_url'], timeout=10)
                            response.raise_for_status()
                            
                            # Check content type
                            content_type = response.headers.get('content-type', '').lower()
                            if 'image' not in content_type:
                                st.warning(f"Invalid content type for image: {content_type}")
                            else:
                                # Convert to base64
                                photo_data = f"data:image/jpeg;base64,{base64.b64encode(response.content).decode()}"
                                st.write("Successfully converted image to base64")
                        except requests.exceptions.RequestException as e:
                            st.warning(f"Failed to fetch image: {str(e)}")
                        except Exception as e:
                            st.warning(f"Error processing image: {str(e)}")
                    else:
                        st.warning("No image URL provided")
                    
                    # Create new card entry
                    new_card = pd.DataFrame([{
                        'player_name': player_name,
                        'year': year,
                        'card_set': card_set,
                        'card_number': card_number,
                        'variation': variation,
                        'condition': condition,
                        'purchase_price': purchase_price,
                        'purchase_date': purchase_date.strftime('%Y-%m-%d'),
                        'current_value': market_data['metrics']['avg_price'],
                        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'notes': notes,
                        'photo': photo_data,
                        'roi': ((market_data['metrics']['avg_price'] - purchase_price) / purchase_price * 100) if purchase_price > 0 else 0,
                        'tags': tags
                    }])
                    
                    # Debug: Print new card data
                    st.write("New card data:", new_card.to_dict('records'))
                    
                    # Add to collection
                    if st.session_state.collection is None:
                        st.session_state.collection = new_card
                    else:
                        st.session_state.collection = pd.concat([st.session_state.collection, new_card], ignore_index=True)
                    
                    # Save to Firebase immediately
                    if save_collection_to_firebase(st.session_state.collection):
                        st.success(f"""
                            Card successfully added to your collection!
                            - {card_data.get('title', '')}
                            - Condition: {condition}
                            - Purchase Price: ${purchase_price:.2f}
                            - Current Market Value: ${market_data['metrics']['avg_price']:.2f}
                        """)
                        st.balloons()
                        return True
                    else:
                        st.error("Failed to save card to Firebase. Please try again.")
                        # Remove the card from session state since Firebase save failed
                        if st.session_state.collection is not None:
                            st.session_state.collection = st.session_state.collection.iloc[:-1]
                        return False
                except Exception as e:
                    st.error(f"Error creating new card entry: {str(e)}")
                    st.write("Debug: Error traceback:", traceback.format_exc())
                    return False
    except Exception as e:
        st.error(f"Error in add_to_collection: {str(e)}")
        st.write("Debug: Error traceback:", traceback.format_exc())
        return False

def display_variations_grid(variation_groups):
    """Display cards in a responsive grid layout"""
    # Use a 2-column layout that stacks on mobile
    cols = st.columns(2)
    for idx, (variation_key, group) in enumerate(variation_groups.items()):
        col = cols[idx % 2]
        with col:
            with st.container():
                # Calculate price statistics for this variation
                prices = [card['price'] for card in group['cards']]
                min_price = min(prices)
                max_price = max(prices)
                median_price = sum(prices) / len(prices)
                
                st.markdown(f"""
                <div class="variation-card">
                    <h4>{group['variation_name']}</h4>
                    <p>Found: {group['count']} listings</p>
                    <p>Price Range: ${min_price:.2f} - ${max_price:.2f}</p>
                    <p>Median Price: ${median_price:.2f}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if group['representative_image']:
                    st.image(group['representative_image'], 
                            use_column_width=True,
                            output_format="JPEG",
                            caption=group['variation_name'])
                
                if st.button("View Details", 
                         key=f"select_variation_{idx}",
                         use_container_width=True):
                    # When button is clicked, update session state with the entire group
                    st.session_state.selected_variation = group
                    st.session_state.selected_card = group['cards'][0]  # Keep the first card for display purposes
                    # Calculate market data for the selected variation
                    analyzer = MarketAnalyzer()
                    st.session_state.market_data = analyzer.analyze_market_data(group['cards'])
                    st.rerun()

def display_sales_log(df):
    """Display a log of recent sales."""
    st.markdown("### Recent Sales Log")
    st.markdown("Below are the 7 most recent sales matching your search criteria:")
    
    # Create a clean table of recent sales
    recent_sales = df.head(7)[['date', 'price', 'title']].copy()
    recent_sales['date'] = recent_sales['date'].dt.strftime('%Y-%m-%d')
    recent_sales['price'] = recent_sales['price'].apply(lambda x: f"${x:.2f}")
    recent_sales.columns = ['Sale Date', 'Price', 'Card Details']
    
    # Display the table with custom styling
    st.markdown("""
    <style>
    .recent-sales {
        font-size: 0.9em;
        margin-bottom: 2em;
    }
    .recent-sales th {
        background-color: #f0f2f6;
        font-weight: bold;
    }
    .recent-sales td {
        white-space: normal !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.table(recent_sales)
    st.info(f"Total number of sales found: {len(df)}")
    st.markdown("---")

def display_market_analysis(card_data, market_data):
    """Display market analysis section with price trends and predictions."""
    st.subheader("Market Analysis")
    
    if not card_data or len(card_data) == 0:
        st.warning("No valid market data available for analysis.")
        return
        
    # Initialize DataFrame
    if 'selected_variation' in st.session_state and st.session_state.selected_variation:
        df = pd.DataFrame(st.session_state.selected_variation['cards'])
    else:
        df = pd.DataFrame(card_data)
    
    # Ensure price is numeric
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    # Ensure date column is properly formatted
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # Remove any rows with missing price or date
    df = df.dropna(subset=['price', 'date'])
    
    # Check if DataFrame has rows after cleaning
    if df.empty:
        st.warning("No valid data to plot. Please check if sale dates and prices exist.")
        return
    
    # Sort by date in ascending order for proper trend display
    df = df.sort_values('date', ascending=True)
    
    # Display the sales log
    display_sales_log(df)
    
    # Calculate metrics
    median_price = df['price'].median()
    last_7_sales = df.tail(7)  # Get last 7 sales since we're sorted ascending
    avg_sell_price = last_7_sales['price'].mean()
    price_std = df['price'].std()
    volatility_score = min((price_std / avg_sell_price) * 10, 10)
    
    # Calculate market health score
    sales_volume = len(df)
    price_trend = (df['price'].iloc[-1] - df['price'].iloc[0]) / df['price'].iloc[0] if len(df) > 1 else 0
    market_health_score = min((sales_volume / 30) * 5 + (1 + price_trend) * 5, 10)
    trend_score = min((1 + price_trend) * 5, 10)
    
    # Store calculated metrics
    if isinstance(card_data, list) and len(card_data) > 0:
        card_data[0]['market_health_score'] = market_health_score
        card_data[0]['trend_score'] = trend_score
        card_data[0]['volatility_score'] = volatility_score
    
    # Initialize market data with scores
    market_data = {
        'scores': {
            'trend_score': trend_score,
            'volatility_score': volatility_score,
            'liquidity_score': market_health_score,
            'momentum_score': trend_score,  # Using trend score as momentum
            'stability_score': 10 - volatility_score,  # Inverse of volatility
            'volume_score': min(sales_volume / 30 * 10, 10)  # Based on sales volume
        },
        'metrics': {
            'avg_price': avg_sell_price,
            'median_price': median_price,
            'low_price': df['price'].min(),
            'high_price': df['price'].max(),
            'liquidity_score': market_health_score,
            'volatility_score': volatility_score,
            'volume_score': min(sales_volume / 30 * 10, 10)
        }
    }
    
    # Store market data in session state
    st.session_state.market_data = market_data
    
    # Display selected card image at the top if available
    if 'selected_variation' in st.session_state and st.session_state.selected_variation:
        selected_card = st.session_state.selected_variation['cards'][0] if st.session_state.selected_variation['cards'] else None
        if selected_card and selected_card.get('image_url'):
            display_image(selected_card['image_url'])
    
    # Display market metrics
    st.markdown("### Market Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Market Health Score",
            f"{market_health_score:.1f}/10",
            help="Based on sales volume and price trend"
        )
    with col2:
        st.metric(
            "Trend Score",
            f"{trend_score:.1f}/10",
            help="Based on price movement direction and strength"
        )
    with col3:
        st.metric(
            "Volatility Score",
            f"{volatility_score:.1f}/10",
            help="Based on price standard deviation"
        )
    with col4:
        st.metric(
            "Average Sell Price",
            f"${avg_sell_price:.2f}",
            help="Mean price of last 7 sales"
        )
    
    if df is not None and not df.empty:
        # Display historical price trend
        st.markdown("### Historical Price Trend")
        
        # Create figure with secondary y-axis
        fig = go.Figure()
        
        # Add price line with markers
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['price'],
            mode='markers+lines',
            name='Sale Price',
            line=dict(color='blue', width=2),
            marker=dict(size=8, color='blue', line=dict(color='white', width=1))
        ))
        
        # Add moving average line
        window_size = min(7, len(df))
        if window_size > 1:
            df['moving_avg'] = df['price'].rolling(window=window_size, min_periods=1).mean()
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['moving_avg'],
                mode='lines',
                name=f'{window_size}-Day Moving Average',
                line=dict(color='red', width=2, dash='dash')
            ))
        
        # Calculate y-axis range
        min_price = df['price'].min()
        max_price = df['price'].max()
        price_range = max_price - min_price
        y_min = max(0, min_price - (price_range * 0.1))
        y_max = max_price + (price_range * 0.1)
        
        # Update layout with improved styling
        fig.update_layout(
            title='Historical Price Trend',
            xaxis_title='Sale Date',
            yaxis_title='Price ($)',
            hovermode='x unified',
            showlegend=True,
            yaxis=dict(range=[y_min, y_max]),
            height=500,
            template='plotly_white',
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=50, r=50, t=50, b=50),
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        # Add hover template
        fig.update_traces(
            hovertemplate="<br>".join([
                "Date: %{x}",
                "Price: $%{y:.2f}",
                "<extra></extra>"
            ])
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display price prediction
        st.markdown("### Price Prediction")
        predictor = PricePredictor()
        predictions = predictor.predict_future_prices(card_data)
        
        if predictions and predictions['predicted_prices']:
            # Calculate prediction ranges
            current_price = df['price'].iloc[-1]  # Use last price since we're sorted ascending
            avg_price = last_7_sales['price'].mean()
            volatility_factor = price_std / avg_price
            
            # Calculate prediction ranges
            short_term_range = volatility_factor * 0.5
            long_term_range = volatility_factor * 1.0
            
            # Calculate trend direction and strength
            price_trend = (current_price - avg_price) / avg_price
            trend_strength = abs(price_trend)
            
            # Adjust predictions based on trend
            if price_trend > 0:
                short_term_multiplier = 1 + (trend_strength * 0.5)
                long_term_multiplier = 1 + (trend_strength * 0.8)
            else:
                short_term_multiplier = 1 - (trend_strength * 0.5)
                long_term_multiplier = 1 - (trend_strength * 0.8)
            
            # Calculate predictions
            short_term_pred = avg_price * short_term_multiplier
            long_term_pred = avg_price * long_term_multiplier
            
            # Display prediction metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "30-Day Forecast",
                    f"${short_term_pred:.2f}",
                    f"±{short_term_range*100:.1f}%"
                )
            with col2:
                st.metric(
                    "90-Day Forecast",
                    f"${long_term_pred:.2f}",
                    f"±{long_term_range*100:.1f}%"
                )
            with col3:
                confidence_score = max(1, min(10, (1 - volatility_factor) * 10))
                st.metric(
                    "Confidence Score",
                    f"{confidence_score:.1f}/10",
                    help="Based on price stability and trend strength"
                )
            
            # Create prediction chart
            future_dates, _ = zip(*predictions['predicted_prices'])
            fig = go.Figure()
            
            # Add historical prices
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['price'],
                mode='markers+lines',
                name='Historical Prices',
                line=dict(color='blue', width=2),
                marker=dict(size=6)
            ))
            
            # Add average price line
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=[avg_price] * len(df['date']),
                mode='lines',
                name='Average Price',
                line=dict(color='green', dash='dot', width=1)
            ))
            
            # Add prediction line
            fig.add_trace(go.Scatter(
                x=future_dates,
                y=[short_term_pred] * len(future_dates),
                mode='lines',
                name='Short-term Forecast',
                line=dict(color='red', dash='dash', width=2)
            ))
            
            # Add confidence intervals
            fig.add_trace(go.Scatter(
                x=future_dates,
                y=[short_term_pred * (1 + short_term_range)] * len(future_dates),
                mode='lines',
                name='Upper Bound',
                line=dict(color='red', dash='dot', width=1)
            ))
            
            fig.add_trace(go.Scatter(
                x=future_dates,
                y=[short_term_pred * (1 - short_term_range)] * len(future_dates),
                mode='lines',
                name='Lower Bound',
                line=dict(color='red', dash='dot', width=1),
                fill='tonexty'
            ))
            
            # Update layout
            fig.update_layout(
                title='Price History and Predictions',
                xaxis_title='Date',
                yaxis_title='Price ($)',
                showlegend=True,
                yaxis=dict(range=[y_min, y_max]),
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Generate recommendations
            if price_trend > 0:
                if trend_strength > 0.1:
                    short_term_rec = "Strong upward trend - Consider buying"
                    long_term_rec = "Positive momentum - Good long-term hold"
                else:
                    short_term_rec = "Moderate upward trend - Watch for entry point"
                    long_term_rec = "Stable growth - Consider holding"
            else:
                if trend_strength > 0.1:
                    short_term_rec = "Downward trend - Consider waiting"
                    long_term_rec = "Negative momentum - Monitor for bottom"
                else:
                    short_term_rec = "Moderate decline - Look for stabilization"
                    long_term_rec = "Market weakness - Consider selling"
            
            # Display recommendations
            st.markdown("### Market Recommendations")
            
            # Create a single container for recommendations
            with st.container():
                st.info(f"""
                **Short-term (30 days):** {short_term_rec}
                
                **Long-term (90 days):** {long_term_rec}
                """)
            
            # Display profit calculator
            display_profit_calculator(card_data, market_data)
            
            # Add detailed recommendations section
            st.markdown("---")  # Visual separator
            try:
                display_recommendations(st.session_state.selected_card, market_data)
            except Exception as e:
                st.error(f"An error occurred in market analysis: {str(e)}")
                print(f"Error in display_market_analysis: {str(e)}")
                traceback.print_exc()

def display_recommendations(card, market_data):
    """Display detailed recommendations for a card"""
    st.markdown("### Detailed Recommendations")
    
    # Get market scores
    trend_score = market_data['scores']['trend_score']
    volatility_score = market_data['scores']['volatility_score']
    liquidity_score = market_data['scores']['liquidity_score']
    
    # Calculate overall score
    overall_score = (trend_score + (10 - volatility_score) + liquidity_score) / 3
    
    # Display scores
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Overall Score",
            f"{overall_score:.1f}/10",
            help="Combined score based on trend, volatility, and liquidity"
        )
    with col2:
        st.metric(
            "Trend Score",
            f"{trend_score:.1f}/10",
            help="Based on price movement direction and strength"
        )
    with col3:
        st.metric(
            "Volatility Score",
            f"{volatility_score:.1f}/10",
            help="Based on price standard deviation"
        )
    with col4:
        st.metric(
            "Liquidity Score",
            f"{liquidity_score:.1f}/10",
            help="Based on sales volume and market depth"
        )
    
    # Generate recommendations based on scores
    if overall_score >= 8:
        st.success("Strong Buy Recommendation")
        st.markdown("""
        - This card shows strong positive momentum
        - Market is stable with good liquidity
        - Consider buying for both short and long-term holds
        """)
    elif overall_score >= 6:
        st.info("Moderate Buy Recommendation")
        st.markdown("""
        - Card shows positive trends but with some volatility
        - Market has decent liquidity
        - Consider buying for long-term holds
        """)
    elif overall_score >= 4:
        st.warning("Hold Recommendation")
        st.markdown("""
        - Card shows mixed signals
        - Market has moderate volatility
        - Consider holding if already owned
        """)
    else:
        st.error("Sell Recommendation")
        st.markdown("""
        - Card shows negative trends
        - Market is volatile with low liquidity
        - Consider selling if owned
        """)

def save_collection_to_firebase(collection_df):
    """Save the collection to Firebase for the current user"""
    try:
        # Debug: Print input type and data
        st.write("Debug: Input type:", type(collection_df))
        st.write("Debug: Input data:", collection_df.head())
        
        # Convert DataFrame to list of dictionaries if needed
        if isinstance(collection_df, pd.DataFrame):
            cards_data = collection_df.to_dict('records')
        else:
            cards_data = collection_df
            
        cards = []
        
        for idx, row in enumerate(cards_data):
            try:
                # Handle dates
                purchase_date = row.get('purchase_date', '')
                if not purchase_date or pd.isna(purchase_date):
                    purchase_date = datetime.now().isoformat()
                elif isinstance(purchase_date, datetime):
                    purchase_date = purchase_date.isoformat()
                elif isinstance(purchase_date, str):
                    try:
                        datetime.fromisoformat(purchase_date)
                    except ValueError:
                        purchase_date = datetime.now().isoformat()
                
                last_updated = row.get('last_updated', '')
                if not last_updated or pd.isna(last_updated):
                    last_updated = datetime.now().isoformat()
                elif isinstance(last_updated, datetime):
                    last_updated = last_updated.isoformat()
                elif isinstance(last_updated, str):
                    try:
                        datetime.fromisoformat(last_updated)
                    except ValueError:
                        last_updated = datetime.now().isoformat()
                
                # Handle numeric values with better error handling
                try:
                    purchase_price = float(row.get('purchase_price', 0.0))
                    if pd.isna(purchase_price):
                        purchase_price = 0.0
                except (ValueError, TypeError) as e:
                    st.warning(f"Warning: Invalid purchase price for card {idx + 1}. Setting to 0.0. Error: {str(e)}")
                    purchase_price = 0.0
                    
                try:
                    current_value = float(row.get('current_value', purchase_price))
                    if pd.isna(current_value):
                        current_value = purchase_price
                except (ValueError, TypeError) as e:
                    st.warning(f"Warning: Invalid current value for card {idx + 1}. Using purchase price. Error: {str(e)}")
                    current_value = purchase_price
                    
                try:
                    roi = float(row.get('roi', 0.0))
                    if pd.isna(roi):
                        roi = 0.0
                except (ValueError, TypeError) as e:
                    st.warning(f"Warning: Invalid ROI for card {idx + 1}. Setting to 0.0. Error: {str(e)}")
                    roi = 0.0
                
                # Handle photo data
                photo = row.get('photo')
                photo_data = "https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image"
                
                if photo is not None and not pd.isna(photo):
                    if isinstance(photo, str):
                        if photo.startswith('data:image'):
                            # Already in base64 format
                            photo_data = photo
                        elif photo.startswith('http'):
                            # Valid URL, keep as is
                            photo_data = photo
                        else:
                            try:
                                # Try to load the image URL
                                response = requests.get(photo, timeout=10)
                                response.raise_for_status()
                                content_type = response.headers.get('content-type', '').lower()
                                if 'image' in content_type:
                                    # Convert to base64
                                    photo_data = f"data:image/jpeg;base64,{base64.b64encode(response.content).decode()}"
                                    st.write(f"Debug: Successfully converted image URL to base64 for card {idx + 1}")
                            except Exception as e:
                                st.warning(f"Failed to process image URL: {str(e)}")
                    else:
                        try:
                            # Handle file upload object
                            photo_bytes = photo.getvalue()
                            photo_data = f"data:image/jpeg;base64,{base64.b64encode(photo_bytes).decode()}"
                            st.write(f"Debug: Successfully converted uploaded image to base64 for card {idx + 1}")
                        except Exception as photo_error:
                            st.warning(f"Warning: Could not process photo for card {idx + 1}. Error: {str(photo_error)}")
                
                # Handle tags
                tags = row.get('tags', '')
                if pd.isna(tags):
                    tags = []
                elif isinstance(tags, str):
                    tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
                elif not isinstance(tags, list):
                    tags = []
                
                # Create card object with proper type conversion
                try:
                    card = Card(
                        player_name=str(row.get('player_name', '')),
                        year=str(row.get('year', '')),
                        card_set=str(row.get('card_set', '')),
                        card_number=str(row.get('card_number', '')),
                        variation=str(row.get('variation', '')),
                        condition=CardCondition.from_string(str(row.get('condition', 'Raw'))),
                        purchase_price=purchase_price,
                        purchase_date=datetime.fromisoformat(purchase_date),
                        current_value=current_value,
                        last_updated=datetime.fromisoformat(last_updated),
                        notes=str(row.get('notes', '')),
                        photo=photo_data,
                        roi=roi,
                        tags=tags
                    )
                    cards.append(card)
                    st.write(f"Debug: Successfully processed card {idx + 1}")
                except Exception as card_error:
                    st.error(f"Error creating card object for card {idx + 1}: {str(card_error)}")
                    continue
                    
            except Exception as card_error:
                st.error(f"Error processing card {idx + 1}: {str(card_error)}")
                continue
        
        if not cards:
            st.error("No valid cards to save")
            return False
        
        with st.spinner("Saving collection to database..."):
            try:
                success = DatabaseService.save_user_collection(st.session_state.uid, cards)
                if success:
                    st.success(f"Successfully saved {len(cards)} cards to your collection!")
                    return True
                else:
                    st.error("Failed to save collection to database. Please try again.")
                    return False
            except Exception as save_error:
                st.error(f"Error saving collection: {str(save_error)}")
                import traceback
                st.write("Debug: Error traceback:", traceback.format_exc())
                return False
        
    except Exception as e:
        st.error(f"Error in save_collection_to_firebase: {str(e)}")
        import traceback
        st.write("Debug: Error traceback:", traceback.format_exc())
        return False

def load_collection_from_firebase():
    """Load the user's collection from Firebase"""
    if not st.session_state.user or not st.session_state.uid:
        return pd.DataFrame(columns=[
            'player_name', 'year', 'card_set', 'card_number', 'variation',
            'condition', 'purchase_price', 'purchase_date', 'current_value',
            'last_updated', 'notes', 'photo', 'roi', 'tags'
        ])
    
    try:
        user_doc = db.collection('users').document(st.session_state.uid).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            if 'collection' in user_data:
                return pd.DataFrame(user_data['collection'])
    except Exception as e:
        st.error(f"Error loading collection: {str(e)}")
    
    return pd.DataFrame(columns=[
        'player_name', 'year', 'card_set', 'card_number', 'variation',
        'condition', 'purchase_price', 'purchase_date', 'current_value',
        'last_updated', 'notes', 'photo', 'roi', 'tags'
    ])

def export_collection_backup():
    """Export collection backup to desktop"""
    try:
        # Check if collection exists and has data
        if not hasattr(st.session_state, 'collection') or st.session_state.collection.empty:
            st.error("No collection data available to backup.")
            return False, "No collection data available"
            
        # Use specific backup name
        backup_filename = "APRIL 2 BACKUP.csv"
        
        # Get desktop path
        desktop_path = os.path.expanduser("~/Desktop")
        backup_path = os.path.join(desktop_path, backup_filename)
        
        # Export collection to CSV
        st.session_state.collection.to_csv(backup_path, index=False)
        
        # Verify the file was created
        if os.path.exists(backup_path):
            st.success(f"Backup file created successfully at: {backup_path}")
            return True, backup_path
        else:
            st.error("Backup file was not created successfully.")
            return False, "File creation failed"
            
    except Exception as e:
        st.error(f"Error creating backup: {str(e)}")
        return False, str(e)

def display_search_form():
    """Display the search form for card search"""
    with st.form("search_form"):
        cols = st.columns(3)
        with cols[0]:
            player_name = st.text_input("Player Name")
            year = st.text_input("Year")
            card_set = st.text_input("Card Set")
        
        with cols[1]:
            card_number = st.text_input("Card Number")
            variation = st.text_input("Variation")
            condition = st.selectbox("Condition", [
                "Raw", "PSA 10", "PSA 9", 
                "SGC 10", "SGC 9.5", "SGC 9"
            ])
        
        negative_keywords = st.text_input(
            "Exclude Keywords (comma-separated)",
            help="Enter keywords to exclude from search, separated by commas"
        )
        
        submitted = st.form_submit_button("Search", use_container_width=True)
        return submitted, {
            'player_name': player_name,
            'year': year,
            'card_set': card_set,
            'card_number': card_number,
            'variation': variation,
            'scenario': condition,
            'negative_keywords': negative_keywords
        }

def display_profit_calculator(card_data, market_data):
    """Display profit calculator for a card"""
    st.markdown("### Profit Calculator")
    
    # Get current market value
    current_value = market_data['metrics']['avg_price']
    
    # Get purchase price from user
    purchase_price = st.number_input(
        "Enter your purchase price ($)",
        min_value=0.0,
        value=0.0,
        step=0.01,
        format="%.2f"
    )
    
    # Calculate profit/loss
    profit_loss = current_value - purchase_price
    roi = (profit_loss / purchase_price * 100) if purchase_price > 0 else 0
    
    # Display results
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Current Market Value",
            f"${current_value:.2f}",
            help="Based on recent sales data"
        )
    with col2:
        st.metric(
            "Profit/Loss",
            f"${profit_loss:.2f}",
            f"{roi:.1f}% ROI",
            delta_color="inverse" if profit_loss < 0 else "normal"
        )
    with col3:
        st.metric(
            "Return on Investment",
            f"{roi:.1f}%",
            help="Percentage return on your investment"
        )

def display_image(image_url):
    """Display card image with proper formatting"""
    if image_url:
        st.image(
            image_url,
            use_column_width=True,
            output_format="JPEG",
            caption="Card Image"
        )
    else:
        st.warning("No image available for this card")

def main():
    # Initialize session state for user if not exists
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'uid' not in st.session_state:
        st.session_state.uid = None
    if 'preferences' not in st.session_state:
        st.session_state.preferences = None
    
    # If user is not logged in, redirect to login page
    if not st.session_state.user:
        st.switch_page("pages/login.py")
    
    # Get user preferences with defaults
    user_preferences = st.session_state.preferences or {
        'display_name': st.session_state.user.get('displayName', 'User'),
        'theme': 'light',
        'currency': 'USD',
        'notifications': True,
        'default_sort': 'date_added',
        'default_view': 'grid',
        'price_alerts': False,
        'market_trends': True,
        'collection_stats': True
    }
    
    st.title("Market Analysis")
    
    # Initialize session state
    init_session_state()
    
    # Add backup button in the top right
    col1, col2, col3 = st.columns([2, 1, 1])
    with col3:
        if st.button("Backup Collection", use_container_width=True):
            success, result = export_collection_backup()
            if success:
                st.success(f"Collection backup created successfully!\nSaved to: {result}")
            else:
                st.error(f"Failed to create backup: {result}")
    
    # Initialize analyzers
    scraper = EbayInterface()
    analyzer = MarketAnalyzer()
    predictor = PricePredictor()
    
    # Display search form
    submitted, search_params = display_search_form()
    
    if submitted:
        with st.spinner("Searching for cards..."):
            # Reset state for new search
            reset_session_state()
            
            # Store search parameters
            st.session_state.search_params = search_params
            
            try:
                # Perform search and wait for results
                results = scraper.search_cards(**st.session_state.search_params)
                
                if results:
                    # Store results in session state
                    st.session_state.search_results = results
                    # Group the results by variation
                    st.session_state.variation_groups = get_variation_groups(results)
                    st.success(f"Found {len(results)} cards in {len(st.session_state.variation_groups)} variations!")
                    st.rerun()
                else:
                    st.error("No results found. Try adjusting your search parameters.")
            except Exception as e:
                st.error(f"An error occurred during search: {str(e)}")
    
    # Display results
    if st.session_state.search_results and not st.session_state.selected_card:
        st.subheader("Search Results")
        display_variations_grid(st.session_state.variation_groups)
    
    # Display analysis
    if st.session_state.selected_card and st.session_state.market_data:
        display_market_analysis(st.session_state.search_results, st.session_state.market_data)
        
        # Mobile-friendly buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("New Search", use_container_width=True):
                reset_session_state()
                st.rerun()
        
        with col2:
            if st.button("Add to Collection", use_container_width=True):
                st.subheader("Add Card to Collection")
                if add_to_collection(st.session_state.selected_card, st.session_state.market_data):
                    reset_session_state()
                    st.rerun()

if __name__ == "__main__":
    main() 