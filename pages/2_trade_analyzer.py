import streamlit as st
from modules.analysis.trade_analyzer import TradeAnalyzer
from modules.core.market_analysis import MarketAnalyzer
from modules.core.price_predictor import PricePredictor
from scrapers.ebay_interface import EbayInterface
from modules.shared.collection_utils import add_to_collection
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root))

def init_session_state():
    """Initialize session state variables for trade analysis."""
    if 'giving_cards' not in st.session_state:
        st.session_state.giving_cards = []
    if 'receiving_cards' not in st.session_state:
        st.session_state.receiving_cards = []
    if 'trade_analysis' not in st.session_state:
        st.session_state.trade_analysis = None

def search_card(scraper, analyzer, predictor, search_params):
    """Search for a card and get its market data."""
    results = scraper.search_cards(**search_params)
    if not results:
        return None
    
    # Filter results for exact variation if specified
    variation = search_params.get('variation', '').lower()
    if variation:
        filtered_results = []
        for card in results:
            if variation in card['title'].lower():
                filtered_results.append(card)
        results = filtered_results
    
    if not results:
        return None
        
    # Get the first card as representative
    card = results[0]
    
    # Get market analysis
    market_data = analyzer.analyze_market_data(results)
    
    # Get price predictions
    predictions = predictor.predict_future_prices(results)
    
    # Combine all data
    card_data = {
        'title': card['title'],
        'market_value': market_data['median_price'],
        'price_volatility': predictions['price_volatility'],
        'liquidity_score': market_data['liquidity_score'],
        'market_trend': predictions['price_trend'],
        'condition': search_params.get('scenario', 'Raw'),
        'trend_direction': 'hot' if predictions['price_trend'] > 10 else 'cooling' if predictions['price_trend'] < -10 else 'stable',
        'trend_score': predictions['price_trend'],
        'volatility_score': predictions['price_volatility'],
        '30_day_forecast': predictions['metrics']['30_day_forecast'],
        '90_day_forecast': predictions['metrics']['90_day_forecast'],
        'image_url': card.get('image_url')  # Add image URL to card data
    }
    
    return card_data

def main():
    st.title("Trade Analyzer")
    
    # Initialize session state
    init_session_state()
    
    # Initialize analyzers
    scraper = EbayInterface()
    analyzer = MarketAnalyzer()
    predictor = PricePredictor()
    trade_analyzer = TradeAnalyzer()
    
    # Create two columns for giving and receiving
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Cards You're Giving")
        
        # Add card form
        with st.form("add_giving_card"):
            st.write("Add a card you're giving:")
            player_name = st.text_input("Player Name", key="giving_player")
            year = st.text_input("Year", key="giving_year")
            card_set = st.text_input("Card Set", key="giving_set")
            card_number = st.text_input("Card Number", key="giving_number")
            variation = st.text_input("Variation", key="giving_variation")
            negative_keywords = st.text_input(
                "Exclude Keywords (comma-separated)",
                help="Enter keywords to exclude from search, separated by commas",
                key="giving_negative_keywords"
            )
            condition = st.selectbox(
                "Condition",
                ["Raw", "PSA 10", "PSA 9", "SGC 10", "SGC 9.5", "SGC 9"],
                key="giving_condition"
            )
            
            if st.form_submit_button("Add Card"):
                search_params = {
                    'player_name': player_name,
                    'year': year,
                    'card_set': card_set,
                    'card_number': card_number,
                    'variation': variation,
                    'negative_keywords': negative_keywords,
                    'scenario': condition
                }
                
                card_data = search_card(scraper, analyzer, predictor, search_params)
                if card_data:
                    st.session_state.giving_cards.append(card_data)
                    st.success(f"Added {card_data['title']}")
                else:
                    st.error("Card not found")
        
        # Display giving cards
        for i, card in enumerate(st.session_state.giving_cards):
            with st.container():
                # Display card image
                if card.get('image_url'):
                    st.image(card['image_url'], use_container_width=True)
                
                st.write(f"**{card['title']}**")
                st.write(f"Condition: {card['condition']}")
                
                # Market Value with forecast
                st.metric(
                    "Market Value",
                    f"${card['market_value']:.2f}",
                    f"30d Forecast: {((card['30_day_forecast'] - card['market_value']) / card['market_value'] * 100):+.1f}%"
                )
                
                # Price Trend with forecast
                trend_color = "🔥" if card['trend_direction'] == 'hot' else "❄️" if card['trend_direction'] == 'cooling' else "⚖️"
                st.metric(
                    "Price Trend",
                    f"{trend_color} {card['trend_score']:+.1f}%",
                    f"90d Forecast: {((card['90_day_forecast'] - card['market_value']) / card['market_value'] * 100):+.1f}%"
                )
                
                # Volatility and Liquidity
                st.metric(
                    "Market Health",
                    f"Volatility: {int(card['volatility_score'])}/10",
                    f"Liquidity: {int(card['liquidity_score'])}/10",
                    help="Volatility (0=Very Stable, 10=Highly Volatile) | Liquidity (0=Hard to Sell, 10=Easy to Sell)"
                )
                
                if st.button("Remove", key=f"remove_giving_{i}"):
                    st.session_state.giving_cards.pop(i)
                    st.rerun()
                st.markdown("---")
    
    with col2:
        st.subheader("Cards You're Receiving")
        
        # Add card form
        with st.form("add_receiving_card"):
            st.write("Add a card you're receiving:")
            player_name = st.text_input("Player Name", key="receiving_player")
            year = st.text_input("Year", key="receiving_year")
            card_set = st.text_input("Card Set", key="receiving_set")
            card_number = st.text_input("Card Number", key="receiving_number")
            variation = st.text_input("Variation", key="receiving_variation")
            negative_keywords = st.text_input(
                "Exclude Keywords (comma-separated)",
                help="Enter keywords to exclude from search, separated by commas",
                key="receiving_negative_keywords"
            )
            condition = st.selectbox(
                "Condition",
                ["Raw", "PSA 10", "PSA 9", "SGC 10", "SGC 9.5", "SGC 9"],
                key="receiving_condition"
            )
            
            if st.form_submit_button("Add Card"):
                search_params = {
                    'player_name': player_name,
                    'year': year,
                    'card_set': card_set,
                    'card_number': card_number,
                    'variation': variation,
                    'negative_keywords': negative_keywords,
                    'scenario': condition
                }
                
                card_data = search_card(scraper, analyzer, predictor, search_params)
                if card_data:
                    st.session_state.receiving_cards.append(card_data)
                    st.success(f"Added {card_data['title']}")
                else:
                    st.error("Card not found")
        
        # Display receiving cards
        for i, card in enumerate(st.session_state.receiving_cards):
            with st.container():
                # Display card image
                if card.get('image_url'):
                    st.image(card['image_url'], use_container_width=True)
                
                st.write(f"**{card['title']}**")
                st.write(f"Condition: {card['condition']}")
                
                # Market Value with forecast
                st.metric(
                    "Market Value",
                    f"${card['market_value']:.2f}",
                    f"30d Forecast: {((card['30_day_forecast'] - card['market_value']) / card['market_value'] * 100):+.1f}%"
                )
                
                # Price Trend with forecast
                trend_color = "🔥" if card['trend_direction'] == 'hot' else "❄️" if card['trend_direction'] == 'cooling' else "⚖️"
                st.metric(
                    "Price Trend",
                    f"{trend_color} {card['trend_score']:+.1f}%",
                    f"90d Forecast: {((card['90_day_forecast'] - card['market_value']) / card['market_value'] * 100):+.1f}%"
                )
                
                # Volatility and Liquidity
                st.metric(
                    "Market Health",
                    f"Volatility: {int(card['volatility_score'])}/10",
                    f"Liquidity: {int(card['liquidity_score'])}/10",
                    help="Volatility (0=Very Stable, 10=Highly Volatile) | Liquidity (0=Hard to Sell, 10=Easy to Sell)"
                )
                
                if st.button("Remove", key=f"remove_receiving_{i}"):
                    st.session_state.receiving_cards.pop(i)
                    st.rerun()
                st.markdown("---")
    
    # Analyze trade button
    if st.button("Analyze Trade", use_container_width=True):
        if not st.session_state.giving_cards and not st.session_state.receiving_cards:
            st.error("Please add cards to both sides of the trade")
        else:
            with st.spinner("Analyzing trade..."):
                analysis = trade_analyzer.analyze_trade(
                    st.session_state.giving_cards,
                    st.session_state.receiving_cards
                )
                st.session_state.trade_analysis = analysis
                st.success("Trade analysis complete!")
    
    # Display trade analysis if available
    if st.session_state.trade_analysis:
        st.subheader("Trade Analysis")
        
        # Overall trade value
        if 'total_value' in st.session_state.trade_analysis:
            st.metric(
                "Overall Trade Value",
                f"${st.session_state.trade_analysis['total_value']:.2f}",
                f"{st.session_state.trade_analysis['value_difference']:+.1f}%"
            )
        else:
            st.warning("Trade value information not available")
        
        # Market health comparison
        if 'giving_health' in st.session_state.trade_analysis and 'receiving_health' in st.session_state.trade_analysis:
            st.metric(
                "Market Health",
                f"Giving: {st.session_state.trade_analysis['giving_health']}/10",
                f"Receiving: {st.session_state.trade_analysis['receiving_health']}/10"
            )
        else:
            st.warning("Market health information not available")
        
        # Trend comparison
        if 'giving_trend' in st.session_state.trade_analysis and 'receiving_trend' in st.session_state.trade_analysis:
            st.metric(
                "Trend Comparison",
                f"Giving: {st.session_state.trade_analysis['giving_trend']:+.1f}%",
                f"Receiving: {st.session_state.trade_analysis['receiving_trend']:+.1f}%"
            )
        else:
            st.warning("Trend information not available")
        
        # Recommendations
        st.subheader("Recommendations")
        if 'recommendation' in st.session_state.trade_analysis:
            st.write(f"• {st.session_state.trade_analysis['recommendation']}")
            if 'recommendation_details' in st.session_state.trade_analysis:
                st.write(st.session_state.trade_analysis['recommendation_details'])
        else:
            st.warning("Recommendations not available")

if __name__ == "__main__":
    main() 