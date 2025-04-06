import streamlit as st
from modules.analysis.trade_analyzer import TradeAnalyzer
from modules.core.market_analysis import MarketAnalyzer
from modules.core.price_predictor import PricePredictor
from scrapers.ebay_interface import EbayInterface
from modules.shared.collection_utils import add_to_collection
from modules.ui.components import CardDisplay
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
                # Add card number header
                if i == 0:
                    st.markdown("### First Card", unsafe_allow_html=True)
                else:
                    st.markdown(f"### Card {i + 1}", unsafe_allow_html=True)
                
                # Create a container with minimal spacing
                st.markdown('<div style="min-height: 100px; margin-top: -4rem; padding-top: 0.005rem;">', unsafe_allow_html=True)
                
                # Display card image with minimal spacing
                if card.get('image_url'):
                    st.image(card['image_url'], use_container_width=True)
                
                # Display card details with minimal spacing
                st.markdown(f"**{card['title']}**", unsafe_allow_html=True)
                st.markdown(f"*{card['condition']}*", unsafe_allow_html=True)
                
                # Market Value with forecast
                st.metric(
                    "Market Value",
                    f"${card['market_value']:.2f}",
                    f"30d Forecast: {((card['30_day_forecast'] - card['market_value']) / card['market_value'] * 100):+.1f}%",
                    help="This shows what the card is worth right now and how much it might change in the next month. A positive number means it's likely to go up in value."
                )
                
                # Price Trend with forecast
                trend_color = "🔥" if card['trend_direction'] == 'hot' else "❄️" if card['trend_direction'] == 'cooling' else "⚖️"
                st.metric(
                    "Price Trend",
                    f"{trend_color} {card['trend_score']:+.1f}%",
                    f"90d Forecast: {((card['90_day_forecast'] - card['market_value']) / card['market_value'] * 100):+.1f}%",
                    help="This shows if the card's price is going up (🔥), down (❄️), or staying steady (⚖️). The forecast tells you what to expect over the next few months."
                )
                
                # Volatility and Liquidity
                st.metric(
                    "Market Health",
                    f"Volatility: {int(card['volatility_score'])}/10",
                    f"Liquidity: {int(card['liquidity_score'])}/10",
                    help="Volatility (0=Very Stable, 10=Highly Volatile) shows how much the card's price jumps around. Liquidity (0=Hard to Sell, 10=Easy to Sell) tells you how quickly you can sell the card. Lower volatility and higher liquidity are better for trading."
                )
                
                if st.button("Remove", key=f"remove_giving_{i}"):
                    st.session_state.giving_cards.pop(i)
                    st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
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
                # Add card number header
                if i == 0:
                    st.markdown("### First Card", unsafe_allow_html=True)
                else:
                    st.markdown(f"### Card {i + 1}", unsafe_allow_html=True)
                
                # Create a container with minimal spacing
                st.markdown('<div style="min-height: 100px; margin-top: -4rem; padding-top: 0.005rem;">', unsafe_allow_html=True)
                
                # Display card image with minimal spacing
                if card.get('image_url'):
                    st.image(card['image_url'], use_container_width=True)
                
                # Display card details with minimal spacing
                st.markdown(f"**{card['title']}**", unsafe_allow_html=True)
                st.markdown(f"*{card['condition']}*", unsafe_allow_html=True)
                
                # Market Value with forecast
                st.metric(
                    "Market Value",
                    f"${card['market_value']:.2f}",
                    f"30d Forecast: {((card['30_day_forecast'] - card['market_value']) / card['market_value'] * 100):+.1f}%",
                    help="This shows what the card is worth right now and how much it might change in the next month. A positive number means it's likely to go up in value."
                )
                
                # Price Trend with forecast
                trend_color = "🔥" if card['trend_direction'] == 'hot' else "❄️" if card['trend_direction'] == 'cooling' else "⚖️"
                st.metric(
                    "Price Trend",
                    f"{trend_color} {card['trend_score']:+.1f}%",
                    f"90d Forecast: {((card['90_day_forecast'] - card['market_value']) / card['market_value'] * 100):+.1f}%",
                    help="This shows if the card's price is going up (🔥), down (❄️), or staying steady (⚖️). The forecast tells you what to expect over the next few months."
                )
                
                # Volatility and Liquidity
                st.metric(
                    "Market Health",
                    f"Volatility: {int(card['volatility_score'])}/10",
                    f"Liquidity: {int(card['liquidity_score'])}/10",
                    help="Volatility (0=Very Stable, 10=Highly Volatile) shows how much the card's price jumps around. Liquidity (0=Hard to Sell, 10=Easy to Sell) tells you how quickly you can sell the card. Lower volatility and higher liquidity are better for trading."
                )
                
                if st.button("Remove", key=f"remove_receiving_{i}"):
                    st.session_state.receiving_cards.pop(i)
                    st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
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
        st.subheader("Trade Analysis Results")
        
        # Overall Trade Value with clearer explanation
        col1, col2 = st.columns(2)
        with col1:
            value_diff = st.session_state.trade_analysis.get('value_difference', 0)
            value_diff_percent = st.session_state.trade_analysis.get('value_difference_percent', 0)
            st.metric(
                "Total Value Difference",
                f"${abs(value_diff):.2f}",
                f"{value_diff_percent:+.1f}%",
                help="This shows how much more or less value you're getting in the trade. A positive number means you're getting more value, while a negative number means you're giving up more value."
            )
        
        # Market Health Comparison with clearer labels
        with col2:
            giving_health = st.session_state.trade_analysis.get('giving_health', 0)
            receiving_health = st.session_state.trade_analysis.get('receiving_health', 0)
            st.metric(
                "Market Health Comparison",
                f"Giving: {giving_health:.1f}/10",
                f"Receiving: {receiving_health:.1f}/10",
                help="This compares how stable and easy to sell the cards are. Higher numbers mean the cards are more stable and easier to sell. A higher number is better for both sides."
            )
        
        # Trend Comparison with clearer explanation
        st.markdown("### Price Trend Analysis")
        col1, col2, col3 = st.columns(3)
        with col1:
            giving_trend = st.session_state.trade_analysis.get('giving_trend', 0)
            st.metric(
                "Cards You're Giving",
                f"{giving_trend:.1f}%",
                help="This shows how much the cards you're giving away have been increasing in value. A higher positive number means the cards are gaining value quickly."
            )
        with col2:
            receiving_trend = st.session_state.trade_analysis.get('receiving_trend', 0)
            st.metric(
                "Cards You're Receiving",
                f"{receiving_trend:.1f}%",
                help="This shows how much the cards you're getting have been increasing in value. A higher positive number means the cards are gaining value quickly."
            )
        with col3:
            trend_advantage = receiving_trend - giving_trend
            st.metric(
                "Trend Advantage",
                f"{trend_advantage:.1f}%",
                help="This shows if the cards you're getting are increasing in value faster than the ones you're giving away. A positive number is good - it means you're getting cards that are growing in value faster."
            )
        
        # Display recommendation
        st.markdown("### Trade Recommendation")
        recommendation = st.session_state.trade_analysis.get('recommendation', '')
        if recommendation:
            # Calculate financial metrics
            total_giving_value = sum(card.get('market_value', 0) for card in st.session_state.giving_cards)
            total_receiving_value = sum(card.get('market_value', 0) for card in st.session_state.receiving_cards)
            value_difference = total_receiving_value - total_giving_value
            value_difference_percent = (value_difference / total_giving_value * 100) if total_giving_value > 0 else 0
            
            # Calculate trend metrics
            giving_trend = st.session_state.trade_analysis.get('giving_trend', 0)
            receiving_trend = st.session_state.trade_analysis.get('receiving_trend', 0)
            trend_advantage = receiving_trend - giving_trend
            
            # Calculate health metrics
            giving_health = st.session_state.trade_analysis.get('giving_health', 0)
            receiving_health = st.session_state.trade_analysis.get('receiving_health', 0)
            health_advantage = receiving_health - giving_health
            
            # Create detailed recommendation
            st.markdown("#### Financial Analysis")
            st.markdown(f"""
            - **Total Value:** You're {'gaining' if value_difference > 0 else 'losing'} ${abs(value_difference):.2f} ({value_difference_percent:+.1f}%) in current market value
            - **Giving Value:** ${total_giving_value:.2f}
            - **Receiving Value:** ${total_receiving_value:.2f}
            """)
            
            st.markdown("#### Market Health Analysis")
            st.markdown(f"""
            - **Market Stability:** The cards you're receiving have a {'higher' if health_advantage > 0 else 'lower'} market health score ({health_advantage:+.1f} points difference)
            - **Giving Health Score:** {giving_health:.1f}/10
            - **Receiving Health Score:** {receiving_health:.1f}/10
            """)
            
            st.markdown("#### Price Trend Analysis")
            st.markdown(f"""
            - **Trend Advantage:** The cards you're receiving are {'gaining' if trend_advantage > 0 else 'losing'} value {abs(trend_advantage):.1f}% faster than the cards you're giving
            - **Giving Trend:** {giving_trend:+.1f}%
            - **Receiving Trend:** {receiving_trend:+.1f}%
            """)
            
            # Display final recommendation
            st.markdown("#### Final Recommendation")
            if isinstance(recommendation, dict):
                st.markdown(f"**{recommendation.get('verdict', '')}**")
                st.markdown(recommendation.get('details', ''))
            else:
                st.markdown(f"**{recommendation}**")
                
            # Add risk assessment
            st.markdown("#### Risk Assessment")
            if value_difference > 0 and trend_advantage > 0 and health_advantage > 0:
                st.success("Low Risk: This trade shows positive indicators across all major metrics")
            elif value_difference > 0 and (trend_advantage > 0 or health_advantage > 0):
                st.info("Moderate Risk: This trade has some positive aspects but also areas of concern")
            else:
                st.warning("High Risk: This trade shows multiple areas of concern that should be carefully considered")
        else:
            st.warning("No recommendation available")

if __name__ == "__main__":
    main() 