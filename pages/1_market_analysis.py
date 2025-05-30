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
from modules.shared.collection_utils import save_card_to_collection
from scrapers.ebay_interface import EbayInterface
from modules.ui.components import CardDisplay
import base64
import requests
import re
import os
from modules.database.service import DatabaseService
from modules.database.models import Card, CardCondition
from typing import List, Dict, Any, Union
from modules.ui.theme.theme_manager import ThemeManager
from modules.ui.branding import BrandingComponent

def get_score_color(score):
    """Return color based on score value"""
    if score >= 8:
        return "#4CAF50"  # Green for strong scores
    elif score >= 6:
        return "#FFC107"  # Yellow for moderate scores
    else:
        return "#F44336"  # Red for weak scores

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
        # Use player name from the original search form input
        player_name = st.session_state.search_params.get('player_name', '')
        
        # Extract card details from title
    except Exception as e:
        st.error(f"Error adding card to collection: {str(e)}")
        return
    title = card_data['title']
    
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
    # Add to collection form
    with st.form("add_to_collection_form"):
        st.subheader("Add Card to Collection")
        
        # Create two rows of form fields
        # First row with three columns
        col1, col2, col3 = st.columns(3)
            
        with col1:
            player_name = st.text_input("Player Name", value=player_name)
            year = st.text_input("Year", value=year)
            with col2:
                card_set = st.text_input("Card Set", value=card_set)
                card_number = st.text_input("Card Number", value=card_number)
        
            with col3:
                variation = st.text_input("Variation", value=variation)
                condition = st.selectbox(
                    "Condition",
                    ["Raw", "PSA 10", "PSA 9", "PSA 8", "PSA 7", "PSA 6", 
                     "PSA 5", "PSA 4", "PSA 3", "PSA 2", "PSA 1",
                     "SGC 10", "SGC 9.5", "SGC 9"],
                    index=0
                )
            
            # Second row with two columns
            col4, col5 = st.columns(2)
            
            with col4:
                purchase_price = st.number_input(
                    "Purchase Price",
                    min_value=0.0,
                    step=0.01,
                    value=float(card_data.get('price', 0))
                )
            
            with col5:
                purchase_date = st.date_input("Purchase Date", value=datetime.now().date())
            
            # Tags field spanning full width
        tags = st.text_input("Tags (comma-separated)", help="Add tags to help organize your collection")
        # Notes field spanning full width
        notes = st.text_area("Notes", height=100)
        
        # Submit button spanning full width
        submitted = st.form_submit_button("Add to Collection", use_container_width=True)
        if submitted:
            # Validate required fields
            if not player_name or not year or not card_set:
                st.error("Please fill in all required fields (Player Name, Year, Card Set)")
                return False
            
            # Create card dictionary
            card_dict = {
                'player_name': player_name,
                'year': year,
                'card_set': card_set,
                'card_number': card_number,
                'variation': variation,
                'condition': condition,
                'purchase_price': purchase_price,
                'purchase_date': purchase_date.strftime('%Y-%m-%d'),
                'current_value': float(card_data.get('price', 0)),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'notes': notes,
                'photo': card_data.get('image_url', ''),
                'tags': [tag.strip() for tag in tags.split(',') if tag.strip()]
            }
            
            # Add to collection
            if save_card_to_collection(card_dict):
                st.success("Card added to collection successfully!")
                return True
            else:
                st.error("Failed to add card to collection")
                return False
            try:
                if save_card_to_collection(card_dict):
                    st.success("Card added to collection successfully!")
                    return True
                else:
                    st.error("Failed to add card to collection")
                    return False
            except Exception as e:
                st.error(f"Error adding card to collection: {str(e)}")
                st.write("Debug: Error traceback:", traceback.format_exc())
                return False

def redirect_to_collection_manager(card_data):
    """Redirect to collection manager with pre-populated card data"""
    try:
        # Store the card data in session state
        st.session_state.prefilled_card = {
            'player_name': st.session_state.search_params.get('player_name', ''),
            'year': re.search(r'\b\d{4}\b', card_data['title']).group(0) if re.search(r'\b\d{4}\b', card_data['title']) else '',
            'card_set': re.search(rf'{st.session_state.search_params.get("year", "")}\s+(.*?)(?:\s+#|\s+Card|\s+RC|\s+Rookie|\s+PSA|\s+SGC|\s+BGS|$)', card_data['title']).group(1) if re.search(rf'{st.session_state.search_params.get("year", "")}\s+(.*?)(?:\s+#|\s+Card|\s+RC|\s+Rookie|\s+PSA|\s+SGC|\s+BGS|$)', card_data['title']) else '',
            'card_number': re.search(r'#(\d+)', card_data['title']).group(1) if re.search(r'#(\d+)', card_data['title']) else '',
            'variation': next((term for term in ['Parallel', 'Refractor', 'Prizm', 'Holo', 'Gold', 'Silver', 'Bronze', 'Red', 'Blue', 'Green', 'Yellow', 'Purple', 'Orange', 'Pink'] if term.lower() in card_data['title'].lower()), ''),
            'purchase_price': float(card_data.get('price', 0)),
            'photo': card_data.get('image_url', ''),
            'current_value': float(card_data.get('price', 0))
        }
        
        # Set the current tab to "Add Card"
        st.session_state.current_tab = "Add Card"
        
        # Redirect to collection manager
        st.switch_page("pages/3_collection_manager.py")
    
    except Exception as e:
        st.error(f"Error redirecting to collection manager: {str(e)}")
        import traceback
        st.write("Debug: Error traceback:", traceback.format_exc())
        return False

def display_variations_grid(variation_groups):
    """Display cards in a responsive grid layout"""
    try:
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
                            use_container_width=True,
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

                # Add "Add to Collection" button
                if st.button("Add to Collection",
                            key=f"add_to_collection_{idx}",
                            use_container_width=True):
                    redirect_to_collection_manager(group['cards'][0])
    
    except Exception as e:
        st.error(f"Error displaying variations grid: {str(e)}")
        import traceback
        st.write("Debug: Error traceback:", traceback.format_exc())
        return False

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
    
    # Calculate price statistics with outlier removal
    def remove_outliers(series):
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        return series[(series >= lower_bound) & (series <= upper_bound)]
    
    # Remove outliers from price data
    clean_prices = remove_outliers(df['price'])
    
    # Calculate metrics with cleaned data
    median_price = clean_prices.median()
    last_7_sales = df.tail(7)  # Get last 7 sales since we're sorted ascending
    avg_sell_price = clean_prices.mean()
    price_std = clean_prices.std()
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
            'low_price': clean_prices.min(),
            'high_price': clean_prices.max(),
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
            # Create a container for the image with custom width
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(selected_card['image_url'], 
                        width=300,  # Set a fixed width that's 75% smaller than default
                        use_container_width=False,
                        output_format="JPEG",
                        caption=selected_card.get('title', 'Card Image'))
    
    # Display market metrics
    st.markdown("### Market Metrics")
    st.markdown("""
    Think of these metrics as your card's "report card" for market health. They help you understand:
    - How strong the market is for this card
    - Whether prices are trending up or down
    - How stable the prices are
    - What a fair price might be
    """)
    
    # First row - Price Statistics
    st.markdown("#### Price Statistics")
    price_col1, price_col2, price_col3 = st.columns(3)
    with price_col1:
        st.metric(
            "Average Sale Price",
            f"${avg_sell_price:.2f}",
            help="The typical selling price based on recent sales (outliers removed)"
        )
    with price_col2:
        st.metric(
            "Highest Sale Price",
            f"${clean_prices.max():.2f}",
            help="The highest price this card has sold for (outliers removed)"
        )
    with price_col3:
        st.metric(
            "Lowest Sale Price",
            f"${clean_prices.min():.2f}",
            help="The lowest price this card has sold for (outliers removed)"
        )
    
    # Second row - Market Scores
    st.markdown("#### Market Scores")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div style='text-align: center;'>
            <h3 style='color: {get_score_color(market_health_score)};'>{market_health_score:.1f}/10</h3>
            <p>Market Health Score</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size: 0.8em;'>
            <p style='color: #4CAF50;'>7-10: Strong market activity</p>
            <p style='color: #FFC107;'>5-7: Average market activity</p>
            <p style='color: #F44336;'>Below 5: Weak market interest</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style='text-align: center;'>
            <h3 style='color: {get_score_color(trend_score)};'>{trend_score:.1f}/10</h3>
            <p>Trend Score</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size: 0.8em;'>
            <p style='color: #4CAF50;'>7-10: Rapid price increases</p>
            <p style='color: #FFC107;'>5-7: Stable prices</p>
            <p style='color: #F44336;'>Below 5: Declining value</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style='text-align: center;'>
            <h3 style='color: {get_score_color(volatility_score)};'>{volatility_score:.1f}/10</h3>
            <p>Volatility Score</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size: 0.8em;'>
            <p style='color: #4CAF50;'>1-3: Very stable prices</p>
            <p style='color: #FFC107;'>4-7: Moderate volatility</p>
            <p style='color: #F44336;'>8-10: Risky price swings</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div style='text-align: center;'>
            <h3 style='color: {get_score_color(market_health_score)};'>{market_health_score:.1f}/10</h3>
            <p>Liquidity Score</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size: 0.8em;'>
            <p style='color: #4CAF50;'>7-10: High trading volume</p>
            <p style='color: #FFC107;'>5-7: Moderate trading volume</p>
            <p style='color: #F44336;'>Below 5: Low trading volume</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Display outlier information
    st.markdown("#### Data Quality")
    total_sales = len(df)
    outlier_count = len(df) - len(clean_prices)
    outlier_percentage = (outlier_count / total_sales * 100) if total_sales > 0 else 0
    
    st.info(f"""
    **Data Quality Note:**
    - Total sales analyzed: {total_sales}
    - Outliers removed: {outlier_count} ({outlier_percentage:.1f}%)
    - Price statistics shown above exclude outliers to provide more accurate market insights
    """)
    
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
        
        # Update layout
    fig.update_layout(
            title="Historical Price Trend",
            xaxis_title="Date",
        yaxis_title="Price ($)",
            yaxis_range=[y_min, y_max],
            hovermode='x unified',
            showlegend=True,
        legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Display the plot
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
                short_term_change = ((short_term_pred - avg_sell_price) / avg_sell_price) * 100
                st.metric(
                    "30-Day Forecast",
                    f"${short_term_pred:.2f}",
                    f"{short_term_change:+.1f}% vs Avg"
                )
            with col2:
                long_term_change = ((long_term_pred - avg_sell_price) / avg_sell_price) * 100
                st.metric(
                    "90-Day Forecast", 
                    f"${long_term_pred:.2f}",
                    f"{long_term_change:+.1f}% vs Avg"
                )
            with col3:
                confidence_score = max(1, min(10, (1 - volatility_factor) * 10))
                st.metric(
                    "Confidence Score",
                    f"{confidence_score:.1f}/10",
                    help="Based on price stability and trend strength"
                )
            
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
            
            # Get the selected card data for the profit calculator
            selected_card_data = None
            if 'selected_variation' in st.session_state and st.session_state.selected_variation:
                selected_card_data = st.session_state.selected_variation['cards'][0] if st.session_state.selected_variation['cards'] else None
            elif isinstance(card_data, list) and len(card_data) > 0:
                selected_card_data = card_data[0]
            elif isinstance(card_data, dict):
                selected_card_data = card_data
            
            # Display profit calculator with the selected card data
            if selected_card_data:
                # Determine if card is graded from title
                title = selected_card_data.get('title', '').lower()
                is_graded = any(grade in title for grade in ['psa', 'bgs', 'sgc'])
                
                # Add condition if missing
                if 'condition' not in selected_card_data:
                    if is_graded:
                        # Extract grade from title
                        grade_match = re.search(r'(psa|bgs|sgc)\s*(\d+)', title)
                        if grade_match:
                            selected_card_data['condition'] = f"{grade_match.group(1).upper()} {grade_match.group(2)}"
                        else:
                            selected_card_data['condition'] = 'graded'
                    else:
                        selected_card_data['condition'] = 'raw'
                
                CardDisplay.display_profit_calculator(selected_card_data, market_data)
            
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
    
    # Display overall score prominently
    st.markdown(f"""
    <div style='text-align: center; margin: 2rem 0;'>
        <h1 style='font-size: 3.5rem; color: {get_score_color(overall_score)};'>{overall_score:.1f}/10</h1>
        <p style='font-size: 1.2rem;'>Overall Market Score</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Display score interpretation
    st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <p style='font-size: 1.1rem;'>
            This score combines market trend, stability, and liquidity to provide a comprehensive market assessment.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Buyer's Recommendations
    st.markdown("#### Buyer's Perspective")
    if overall_score >= 8:
        st.success("Strong Buy Recommendation")
        st.markdown("""
        🟢 **Optimal Buying Conditions**
        - Market shows strong positive momentum
        - High liquidity means easy entry and exit
        - Price stability suggests good value retention
        - Consider purchasing now before potential price increases
        - Look for auctions ending soon for best deals
        - Consider buying in bulk for better pricing
        """)
    elif overall_score >= 6:
        st.info("Moderate Buy Recommendation")
        st.markdown("""
        🟡 **Favorable Buying Conditions**
        - Market shows decent stability and liquidity
        - Consider purchasing if the price aligns with your budget
        - Monitor market trends for optimal entry point
        - Look for cards with strong fundamentals
        - Consider setting price alerts for dips
        - Focus on well-graded examples
        """)
    elif overall_score >= 4:
        st.warning("Cautious Buy Recommendation")
        st.markdown("""
        🟡 **Selective Buying Opportunity**
        - Market shows mixed signals
        - Consider buying only if you find exceptional deals
        - Focus on high-grade examples
        - Set strict price limits
        - Consider dollar-cost averaging
        - Look for cards with strong long-term potential
        """)
    else:
        st.error("Hold Recommendation")
        st.markdown("""
        🔴 **Not Recommended for Buying**
        - Market shows negative trends
        - High volatility suggests price risk
        - Limited liquidity may make selling difficult
        - Consider waiting for market stabilization
        - Focus on other opportunities
        - Only buy if you find exceptional deals
        """)
    
    # Seller's Recommendations
    st.markdown("#### Seller's Perspective")
    if overall_score >= 8:
        st.success("Strong Sell Recommendation")
        st.markdown("""
        🟢 **Optimal Selling Conditions**
        - High market demand presents excellent selling opportunity
        - Strong liquidity means quick sale potential
        - Consider listing now to capitalize on current market conditions
        - List at competitive prices for quick sale
        - Consider auction format for maximum exposure
        - Highlight card condition and grading details
        """)
    elif overall_score >= 6:
        st.info("Moderate Sell Recommendation")
        st.markdown("""
        🟡 **Favorable Selling Conditions**
        - Market conditions are decent for selling
        - Consider listing if you're looking to exit
        - Monitor market for optimal selling window
        - Price competitively to attract buyers
        - Consider fixed-price listings
        - Highlight unique card features
        """)
    elif overall_score >= 4:
        st.warning("Cautious Sell Recommendation")
        st.markdown("""
        🟡 **Selective Selling Opportunity**
        - Market shows some uncertainty
        - Consider holding unless you need to sell
        - If selling, focus on high-grade examples
        - Price slightly below market to attract buyers
        - Consider longer listing durations
        - Highlight card's long-term potential
        """)
    else:
        st.error("Hold Recommendation")
        st.markdown("""
        🔴 **Not Recommended for Selling**
        - Current market conditions are unfavorable
        - High volatility may lead to suboptimal prices
        - Limited liquidity may make selling difficult
        - Consider waiting for market improvement
        - Focus on other cards in your collection
        - Only sell if absolutely necessary
        """)
    
    # Market Commentary
    st.markdown("#### Market Commentary")
    commentary = f"""
    The card shows a trend score of {trend_score:.1f}/10, indicating {'strong upward' if trend_score >= 7 else 'moderate upward' if trend_score >= 5 else 'stable' if trend_score >= 3 else 'downward'} momentum. 
    With a liquidity score of {liquidity_score:.1f}/10, {'the market is highly liquid' if liquidity_score >= 7 else 'there is moderate liquidity' if liquidity_score >= 5 else 'liquidity is somewhat limited'}. 
    The volatility score of {volatility_score:.1f}/10 suggests {'low' if volatility_score <= 3 else 'moderate' if volatility_score <= 7 else 'high'} price volatility.
    """
    st.markdown(commentary)
    
    # Risk Factors
    st.markdown("#### Risk Factors to Consider")
    st.warning("""
    ⚠️ **Key Risk Factors:**
    - Market volatility and trading volume
    - Player performance and team dynamics
    - Overall sports card market conditions
    - Grading population changes
    - Seasonal market fluctuations
    - Economic conditions and collector sentiment
    - Supply and demand dynamics
    - Competition from similar cards
    """)

def save_collection_to_firebase(collection_df):
    """Save the user's collection to Firebase"""
    cards = []
    for idx, row in collection_df.iterrows():
        # Handle dates
        purchase_date = row.get('purchase_date', '')
        if not purchase_date or pd.isna(purchase_date):
            purchase_date = datetime.now().isoformat()
        
        last_updated = row.get('last_updated', '')
        if not last_updated or pd.isna(last_updated):
            last_updated = datetime.now().isoformat()
        
        # Handle numeric values
        try:
            purchase_price = float(row.get('purchase_price', 0.0))
            if pd.isna(purchase_price):
                purchase_price = 0.0
        except (ValueError, TypeError) as e:
            st.warning(f"Warning: Invalid purchase price for card {idx + 1}. Setting to 0.0. Error: {str(e)}")
            purchase_price = 0.0
        
        try:
            current_value = float(row.get('current_value', 0.0))
            if pd.isna(current_value):
                current_value = 0.0
        except (ValueError, TypeError) as e:
            st.warning(f"Warning: Invalid current value for card {idx + 1}. Setting to 0.0. Error: {str(e)}")
            current_value = 0.0
        
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
    
    if not cards:
        st.error("No valid cards to save")
        return False
    
    try:
        with st.spinner("Saving collection to database..."):
            success = DatabaseService.save_user_collection(st.session_state.uid, cards)
            if success:
                st.success(f"Successfully saved {len(cards)} cards to your collection!")
                return True
            else:
                st.error("Failed to save collection")
                return False
    except Exception as e:
        st.error(f"Error saving collection: {str(e)}")
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
        # Get user data using DatabaseService
        user_data = DatabaseService.get_user_data(st.session_state.uid)
        if user_data and 'collection' in user_data:
            return pd.DataFrame(user_data['collection'])
    except Exception as e:
        st.error(f"Error loading collection: {str(e)}")
    
    return pd.DataFrame(columns=[
        'player_name', 'year', 'card_set', 'card_number', 'variation',
        'condition', 'purchase_price', 'purchase_date', 'current_value',
        'last_updated', 'notes', 'photo', 'roi', 'tags'
    ])

def export_collection_backup():
    """Export collection backup as a downloadable CSV file"""
    try:
        # Check if collection exists and has data
        if not hasattr(st.session_state, 'collection') or st.session_state.collection.empty:
            st.error("No collection data available to backup.")
            return False, "No collection data available"
        
        # Convert collection to CSV
        csv = st.session_state.collection.to_csv(index=False)
        
        # Create download button
        st.download_button(
            label="Download Collection Backup",
            data=csv,
            file_name="collection_backup.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        return True, "Download ready"
            
    except Exception as e:
        st.error(f"Error creating backup: {str(e)}")
        return False, str(e)

def display_search_form():
    """Display the search form for card search"""
    with st.form("search_form"):
        player_name = st.text_input("Player Name")
        year = st.text_input("Year")
        card_set = st.text_input("Card Set")
        card_number = st.text_input("Card Number")
        variation = st.text_input("Variation")
        condition = st.selectbox("Condition", [
            "Raw", "PSA 10", "PSA 9", "PSA 8", "PSA 7", "PSA 6", 
            "PSA 5", "PSA 4", "PSA 3", "PSA 2", "PSA 1",
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
    
    # Get card condition
    condition = None
    if isinstance(card_data, dict):
        condition = card_data.get('condition', '').lower()
    elif isinstance(card_data, list) and len(card_data) > 0:
        condition = card_data[0].get('condition', '').lower()
    
    # If card is raw, show grading analysis
    if condition == 'raw':
        st.markdown("### Grading Analysis")
        
        # Get PSA 9 and PSA 10 prices
        psa9_price = current_value * 1.5  # Default multiplier
        psa10_price = current_value * 3.0  # Default multiplier
        
        # Search for actual PSA 9 and PSA 10 sales in market data
        if isinstance(market_data.get('sales', []), list):
            psa9_sales = [sale for sale in market_data['sales'] if 'psa 9' in sale.get('title', '').lower()]
            psa10_sales = [sale for sale in market_data['sales'] if 'psa 10' in sale.get('title', '').lower()]
            
            if psa9_sales:
                psa9_price = psa9_sales[0]['price']
            if psa10_sales:
                psa10_price = psa10_sales[0]['price']
        
        # Calculate grading costs
        grading_fee = 25.0
        shipping_cost = 10.0
        total_grading_cost = grading_fee + shipping_cost
        
        # Calculate break-even prices and profits
        break_even = purchase_price + total_grading_cost
        psa9_profit = psa9_price - break_even
        psa10_profit = psa10_price - break_even
        
        # Calculate ROI for each grade
        psa9_roi = (psa9_profit / break_even * 100) if break_even > 0 else 0
        psa10_roi = (psa10_profit / break_even * 100) if break_even > 0 else 0
        
        # Display grading metrics
        st.markdown("#### Potential Graded Values")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "PSA 9 Value",
                f"${psa9_price:.2f}",
                f"{psa9_roi:+.1f}% vs Avg",
                help="Estimated value if graded PSA 9"
            )
        with col2:
            st.metric(
                "PSA 10 Value",
                f"${psa10_price:.2f}",
                f"{psa10_roi:+.1f}% vs Avg",
                help="Estimated value if graded PSA 10"
            )
        
        # Display break-even analysis
        st.markdown("#### Break-Even Analysis")
        st.markdown(f"""
        - **Total Grading Cost:** ${total_grading_cost:.2f} (Grading: ${grading_fee:.2f} + Shipping: ${shipping_cost:.2f})
        - **Break-Even Price:** ${break_even:.2f}
        """)
        
        # Quick verdict
        st.markdown("#### Grading Recommendation")
        if psa10_profit > total_grading_cost * 2:
            st.success("🟢 **GRADE IT!** - High profit potential at PSA 10")
        elif psa9_profit > total_grading_cost:
            st.info("🔵 **Consider Grading** - Profitable at PSA 9")
        else:
            st.warning("🟡 **DON'T GRADE** - Grading costs exceed potential profit")

def display_image(image_url):
    """Display card image with proper formatting"""
    if image_url:
        st.image(
            image_url,
            use_container_width=True,
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
        st.switch_page("pages/0_login.py")
    
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
    
    # Sidebar
    with st.sidebar:
        # Sidebar header with branding
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        BrandingComponent.display_horizontal_logo()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Logout button
        if st.button("Logout", type="primary"):
            st.session_state.user = None
            st.session_state.uid = None
            st.rerun()
    
    st.title("Market Analysis")
    
    # Initialize session state
    init_session_state()
    
    # Add billing section
    with ThemeManager.styled_card():
        st.subheader("Billing")
        st.info("💳 Billing management coming soon!")

        # Placeholder for future billing features
        st.markdown('''
        **Coming Soon:**
        - Subscription management
        - Payment history
        - Billing preferences
        ''')
    
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
                redirect_to_collection_manager(st.session_state.selected_card)

if __name__ == "__main__":
    main() 