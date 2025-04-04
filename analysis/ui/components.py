import streamlit as st
import plotly.express as px
import pandas as pd
from typing import Dict, List, Any, Optional

class CardDisplay:
    @staticmethod
    def display_image(image_url: Optional[str] = None):
        """Display card image with fallback."""
        if image_url:
            try:
                st.image(image_url, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not display card image: {str(e)}")
                st.image("https://via.placeholder.com/300x400?text=No+Image", use_container_width=True)
        else:
            st.image("https://via.placeholder.com/300x400?text=No+Image", use_container_width=True)

    @staticmethod
    def display_price_metrics(metrics: Dict[str, float]):
        """Display price analysis metrics in columns."""
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Low Price Range", f"${metrics['low_price']:.2f}",
                     help="25th percentile - 25% of sales were below this price (outliers removed)")
        with col2:
            st.metric("Median Price", f"${metrics['median_price']:.2f}",
                     help="50th percentile - Middle point of all sales (outliers removed)")
        with col3:
            st.metric("High Price Range", f"${metrics['high_price']:.2f}",
                     help="75th percentile - 75% of sales were below this price (outliers removed)")

    @staticmethod
    def display_market_scores(scores: Dict[str, float]):
        """Display market analysis scores in columns."""
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Price Volatility", f"{scores['volatility_score']:.1f}/10",
                     help="1 = Very Stable, 10 = Very Volatile. Based on price variation between sales")
        with col2:
            st.metric("Market Trend", f"{scores['trend_score']:.1f}/10",
                     help="1 = Declining, 5 = Stable, 10 = Strong Growth. Based on recent price changes")
        with col3:
            st.metric("Market Liquidity", f"{scores['liquidity_score']:.1f}/10",
                     help="1 = Hard to Trade, 10 = Easy to Trade. Based on number of recent sales")

    @staticmethod
    def display_market_grades(grades: Dict[str, str]):
        """Display market grades in columns."""
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Buying Grade", grades['buy_grade'],
                     help="A = Excellent time to buy, D = Poor time to buy. Based on price trend, volatility, and market liquidity")
        with col2:
            st.metric("Selling Grade", grades['sell_grade'],
                     help="A = Excellent time to sell, D = Poor time to sell. Based on price trend, volatility, and market liquidity")

    @staticmethod
    def create_price_trend_graph(df: pd.DataFrame, selected_card: Optional[Dict] = None):
        """Create and display price trend graph."""
        fig = px.line(df, x='date', y='price',
                     title='Card Price Trend Over Time',
                     labels={'price': 'Sale Price ($)', 'date': 'Date'})
        
        fig.update_layout(
            xaxis_title="Sale Date",
            yaxis_title="Price ($)",
            hovermode='x unified'
        )
        
        if selected_card and selected_card.get('date'):
            fig.add_scatter(
                x=[pd.to_datetime(selected_card['date'])],
                y=[selected_card['price']],
                mode='markers',
                name='Selected Card',
                marker=dict(size=12, color='red'),
                showlegend=True
            )
        
        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def display_recommendations(selected_card: Dict[str, Any], market_data: Dict[str, Any]):
        """Display recommendations for buyers and sellers based on market analysis."""
        st.markdown("### Market Recommendations")
        
        # Get market scores
        trend_score = market_data['scores']['trend_score']
        volatility_score = market_data['scores']['volatility_score']
        liquidity_score = market_data['scores']['liquidity_score']
        
        # Calculate overall market sentiment
        sentiment = (trend_score + liquidity_score - volatility_score) / 3
        
        # Generate recommendations based on market data
        if sentiment >= 7:
            market_sentiment = "very strong"
            recommendation = "This card shows excellent market fundamentals with strong demand and good liquidity."
        elif sentiment >= 5:
            market_sentiment = "positive"
            recommendation = "The card demonstrates solid market performance with balanced supply and demand."
        else:
            market_sentiment = "cautious"
            recommendation = "The card shows some market uncertainty with potential volatility risks."
        
        # Buyer's Perspective
        st.markdown("#### Buyer's Perspective")
        if trend_score >= 7 and liquidity_score >= 6:
            buyer_rec = f"""
            🟢 **Strong Buy Opportunity**
            - Current market conditions are favorable for buyers
            - High liquidity means you can easily find and purchase this card
            - Price stability suggests good value retention
            - Consider purchasing now before potential price increases
            """
        elif trend_score >= 5 and liquidity_score >= 5:
            buyer_rec = f"""
            🟡 **Moderate Buy Opportunity**
            - Market shows decent stability and liquidity
            - Consider purchasing if the price aligns with your budget
            - Monitor market trends for optimal entry point
            """
        else:
            buyer_rec = f"""
            🔴 **Cautious Buy**
            - Market shows some volatility
            - Consider waiting for better market conditions
            - Look for specific deals or auctions
            """
        st.markdown(buyer_rec)
        
        # Seller's Perspective
        st.markdown("#### Seller's Perspective")
        if trend_score >= 7 and liquidity_score >= 6:
            seller_rec = f"""
            🟢 **Strong Sell Opportunity**
            - High market demand presents good selling opportunity
            - Strong liquidity means quick sale potential
            - Consider listing now to capitalize on current market conditions
            """
        elif trend_score >= 5 and liquidity_score >= 5:
            seller_rec = f"""
            🟡 **Moderate Sell Opportunity**
            - Market conditions are decent for selling
            - Consider listing if you're looking to exit
            - Monitor market for optimal selling window
            """
        else:
            seller_rec = f"""
            🔴 **Hold Position**
            - Current market conditions may not be optimal for selling
            - Consider holding until market conditions improve
            - Look for specific high-value sales opportunities
            """
        st.markdown(seller_rec)
        
        # Market Commentary
        st.markdown("#### Market Commentary")
        commentary = f"""
        {recommendation} The card shows a trend score of {trend_score:.1f}/10, indicating {market_sentiment} market momentum. 
        With a liquidity score of {liquidity_score:.1f}/10, {('the market is highly liquid' if liquidity_score >= 7 else 'there is moderate liquidity' if liquidity_score >= 5 else 'liquidity is somewhat limited')}. 
        The volatility score of {volatility_score:.1f}/10 suggests {('low' if volatility_score <= 3 else 'moderate' if volatility_score <= 7 else 'high')} price volatility.
        """
        st.markdown(commentary)

    @staticmethod
    def display_profit_calculator(selected_card: Dict[str, Any], market_data: Dict[str, Any]):
        """Display profit calculator section with detailed cost breakdown."""
        st.subheader("Profit Calculator")
        
        # Create tabs for different scenarios
        tab1, tab2, tab3 = st.tabs(["Raw Card", "PSA 9", "PSA 10"])
        
        # Common input fields for all scenarios
        col1, col2 = st.columns(2)
        with col1:
            purchase_price = st.number_input(
                "Purchase Price ($)",
                min_value=0.0,
                value=float(selected_card['price']),
                step=1.0,
                key="purchase_price"
            )
        with col2:
            holding_period = st.number_input(
                "Holding Period (months)",
                min_value=1,
                value=12,
                step=1,
                key="holding_period"
            )
        
        # Raw Card Scenario
        with tab1:
            st.markdown("### Raw Card Scenario")
            
            # Input fields for raw card
            col1, col2 = st.columns(2)
            with col1:
                shipping_cost = st.number_input(
                    "Shipping Cost ($)",
                    min_value=0.0,
                    value=5.00,
                    step=1.0,
                    key="raw_shipping_cost"
                )
            with col2:
                seller_fee = st.number_input(
                    "Seller Fee (%)",
                    min_value=0.0,
                    max_value=15.0,
                    value=12.9,
                    step=0.1,
                    key="raw_seller_fee"
                )
            
            # Calculate raw card metrics
            current_price = selected_card['price']
            seller_fee_amount = current_price * (seller_fee / 100)
            total_costs = purchase_price + shipping_cost + seller_fee_amount
            profit = current_price - total_costs
            profit_percentage = (profit / total_costs) * 100
            break_even_price = total_costs
            
            # Display raw card metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Costs", f"${total_costs:.2f}",
                         help="Purchase price + shipping + seller fees")
            with col2:
                st.metric("Profit/Loss", f"${profit:.2f}",
                         help="Current value minus total costs")
            with col3:
                st.metric("Profit/Loss %", f"{profit_percentage:.1f}%",
                         help="Percentage return on investment")
            
            st.info(f"Break-even Price: ${break_even_price:.2f}")
        
        # PSA 9 Scenario
        with tab2:
            st.markdown("### PSA 9 Scenario")
            
            # Input fields for PSA 9
            col1, col2, col3 = st.columns(3)
            with col1:
                grading_cost = st.number_input(
                    "PSA Grading Cost ($)",
                    min_value=0.0,
                    value=25.00,
                    step=1.0,
                    key="psa9_grading_cost"
                )
            with col2:
                shipping_cost = st.number_input(
                    "Shipping Cost ($)",
                    min_value=0.0,
                    value=5.00,
                    step=1.0,
                    key="psa9_shipping_cost"
                )
            with col3:
                seller_fee = st.number_input(
                    "Seller Fee (%)",
                    min_value=0.0,
                    max_value=15.0,
                    value=12.9,
                    step=0.1,
                    key="psa9_seller_fee"
                )
            
            # Calculate PSA 9 metrics
            psa9_price = current_price * 2
            seller_fee_amount = psa9_price * (seller_fee / 100)
            total_costs = purchase_price + grading_cost + shipping_cost + seller_fee_amount
            profit = psa9_price - total_costs
            profit_percentage = (profit / total_costs) * 100
            break_even_price = total_costs
            
            # Display PSA 9 metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Costs", f"${total_costs:.2f}",
                         help="Purchase price + grading + shipping + seller fees")
            with col2:
                st.metric("Profit/Loss", f"${profit:.2f}",
                         help="PSA 9 value minus total costs")
            with col3:
                st.metric("Profit/Loss %", f"{profit_percentage:.1f}%",
                         help="Percentage return on investment")
            
            st.info(f"Break-even Price: ${break_even_price:.2f}")
        
        # PSA 10 Scenario
        with tab3:
            st.markdown("### PSA 10 Scenario")
            
            # Input fields for PSA 10
            col1, col2, col3 = st.columns(3)
            with col1:
                grading_cost = st.number_input(
                    "PSA Grading Cost ($)",
                    min_value=0.0,
                    value=25.00,
                    step=1.0,
                    key="psa10_grading_cost"
                )
            with col2:
                shipping_cost = st.number_input(
                    "Shipping Cost ($)",
                    min_value=0.0,
                    value=5.00,
                    step=1.0,
                    key="psa10_shipping_cost"
                )
            with col3:
                seller_fee = st.number_input(
                    "Seller Fee (%)",
                    min_value=0.0,
                    max_value=15.0,
                    value=12.9,
                    step=0.1,
                    key="psa10_seller_fee"
                )
            
            # Calculate PSA 10 metrics
            psa10_price = current_price * 4
            seller_fee_amount = psa10_price * (seller_fee / 100)
            total_costs = purchase_price + grading_cost + shipping_cost + seller_fee_amount
            profit = psa10_price - total_costs
            profit_percentage = (profit / total_costs) * 100
            break_even_price = total_costs
            
            # Display PSA 10 metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Costs", f"${total_costs:.2f}",
                         help="Purchase price + grading + shipping + seller fees")
            with col2:
                st.metric("Profit/Loss", f"${profit:.2f}",
                         help="PSA 10 value minus total costs")
            with col3:
                st.metric("Profit/Loss %", f"{profit_percentage:.1f}%",
                         help="Percentage return on investment")
            
            st.info(f"Break-even Price: ${break_even_price:.2f}")
        
        # Add disclaimer
        st.warning("""
        ⚠️ Note: The PSA 9 and PSA 10 price estimates are simplified assumptions based on typical market multipliers.
        Actual prices may vary significantly based on card condition, market conditions, and other factors.
        """)

    @staticmethod
    def display_price_prediction(selected_card: Dict[str, Any], market_data: Dict[str, Any]):
        """Display price prediction section."""
        st.subheader("Price Prediction")
        
        # Calculate trend-based prediction
        trend_score = market_data['scores']['trend_score']
        volatility_score = market_data['scores']['volatility_score']
        current_price = selected_card['price']
        
        # Simple prediction model based on trend and volatility
        months = [1, 3, 6, 12]
        predictions = []
        
        for month in months:
            # Base prediction on trend score (1-10) and volatility
            trend_factor = (trend_score - 5) / 5  # Convert to -1 to 1 range
            volatility_factor = volatility_score / 10  # 0 to 1 range
            
            # Calculate monthly growth rate
            monthly_growth = trend_factor * (1 - volatility_factor) * 0.05  # 5% max monthly growth
            
            # Calculate predicted price
            predicted_price = current_price * (1 + monthly_growth * month)
            predictions.append({
                'months': month,
                'price': predicted_price,
                'change': ((predicted_price - current_price) / current_price) * 100
            })
        
        # Display predictions
        st.markdown("### Price Forecast")
        cols = st.columns(4)
        for idx, pred in enumerate(predictions):
            with cols[idx]:
                st.metric(
                    f"{pred['months']} Month",
                    f"${pred['price']:.2f}",
                    f"{pred['change']:+.1f}%",
                    help=f"Predicted price after {pred['months']} months"
                )
        
        # Create and display price forecast graph
        st.markdown("### Price Forecast Graph")
        df_predictions = pd.DataFrame(predictions)
        
        # Add current price point
        df_predictions = pd.concat([
            pd.DataFrame([{'months': 0, 'price': current_price, 'change': 0}]),
            df_predictions
        ])
        
        fig = px.line(df_predictions, 
                     x='months', 
                     y='price',
                     title='Price Forecast Over Time',
                     labels={'price': 'Projected Price ($)', 
                            'months': 'Months',
                            'change': 'Price Change (%)'})
        
        # Add markers for each data point
        fig.update_traces(mode='lines+markers')
        
        fig.update_layout(
            xaxis_title="Months",
            yaxis_title="Projected Price ($)",
            hovermode='x unified',
            showlegend=False
        )
        
        # Update x-axis to show specific months
        fig.update_xaxes(tickvals=[0, 1, 3, 6, 12])
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add disclaimer
        st.info("""
        ⚠️ Price predictions are based on historical trends and market volatility.
        They should not be considered financial advice. Market conditions can change rapidly.
        """)

class SearchForm:
    @staticmethod
    def create_search_form(form_key: str = "card_search_form"):
        """Create and display the search form."""
        with st.form(form_key):
            # First row: Player Name and Year
            col1, col2 = st.columns(2)
            with col1:
                player_name = st.text_input("Player Name *", placeholder="e.g., Tom Brady")
            with col2:
                year = st.text_input("Year", placeholder="e.g., 2020")
            
            # Second row: Card Set and Card Number
            col1, col2 = st.columns(2)
            with col1:
                card_set = st.text_input("Set", placeholder="e.g., Topps Chrome")
            with col2:
                card_number = st.text_input("Card Number", placeholder="e.g., 247")
            
            # Third row: Variation and Negative Keywords
            col1, col2 = st.columns(2)
            with col1:
                variation = st.text_input("Variation", placeholder="e.g., Refractor")
            with col2:
                negative_keywords = st.text_input("Negative Keywords", 
                                                placeholder="e.g., damaged, reprint (comma separated)")
            
            # Fourth row: Card Condition
            scenario = st.selectbox("Card Condition", ["Raw", "PSA 9", "PSA 10"])
            
            submitted = st.form_submit_button("Search Cards")
            
            return {
                'submitted': submitted,
                'player_name': player_name,
                'year': year,
                'card_set': card_set,
                'card_number': card_number,
                'variation': variation,
                'negative_keywords': negative_keywords,
                'scenario': scenario
            } 