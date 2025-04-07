import streamlit as st
import plotly.express as px
import pandas as pd
from typing import Dict, List, Any, Optional
import requests
import io
import plotly.graph_objects as go
from datetime import datetime, timedelta
from modules.core.profit_calculator import ProfitCalculator
from modules.core.grading_analyzer import GradingAnalyzer

class CardDisplay:
    @staticmethod
    def display_image(image_url: Optional[str] = None, show_placeholder: bool = False):
        """Display card image with fallback."""
        if not image_url or not image_url.strip():
            st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image", use_column_width=True)
            return

        try:
            # Handle base64 images
            if isinstance(image_url, str) and image_url.startswith('data:image'):
                try:
                    st.image(image_url, use_column_width=True)
                    return
                except Exception as e:
                    if show_placeholder:
                        st.warning(f"Failed to load base64 image: {str(e)}")
                    st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Base64", use_column_width=True)
                    return

            # Clean and format the URL
            image_url = image_url.strip()
            
            # Convert eBay thumbnail URLs to full-size images
            if '/s-l140' in image_url:
                image_url = image_url.replace('/s-l140', '/s-l1600')
            elif '/s-l300' in image_url:
                image_url = image_url.replace('/s-l300', '/s-l1600')
            
            if not image_url.startswith(('http://', 'https://')):
                image_url = f"https://{image_url}"

            # Enhanced headers for eBay image requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.ebay.com/",
                "Connection": "keep-alive",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }

            # Try to load the image with requests first
            response = requests.get(image_url, headers=headers, timeout=10, verify=True)
            response.raise_for_status()

            # Verify content type is an image
            content_type = response.headers.get('content-type', '').lower()
            if 'image' not in content_type:
                raise ValueError(f"Invalid content type: {content_type}")

            # Convert to image bytes and display
            image_bytes = io.BytesIO(response.content)
            st.image(image_bytes, use_column_width=True)

        except Exception as e:
            # If the first attempt fails, try direct loading
            try:
                st.image(image_url, use_column_width=True)
            except:
                # If both attempts fail, show placeholder
                st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Image+Load+Failed", use_column_width=True)
                if show_placeholder:
                    st.warning(f"Failed to load image: {str(e)}")

    @staticmethod
    def display_price_metrics(metrics: Dict[str, float]):
        """Display price analysis metrics in columns."""
        st.markdown("### Market Metrics")
        
        # First row - Core price metrics
        st.markdown("#### Price Analysis")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Average Price", f"${metrics['avg_price']:.2f}",
                     help="Mean price of all sales (outliers removed)")
        with col2:
            st.metric("Median Price", f"${metrics['median_price']:.2f}",
                     help="50th percentile - Middle point of all sales (outliers removed)")
        with col3:
            st.metric("Price Range", f"${metrics['low_price']:.2f} - ${metrics['high_price']:.2f}",
                     help="25th to 75th percentile range of sales (outliers removed)")
        
        # Second row - Market activity metrics
        st.markdown("#### Market Activity")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Market Liquidity", f"{metrics['liquidity_score']:.1f}/10",
                     help="1 = Hard to Trade, 10 = Easy to Trade. Based on number of recent sales")
        with col2:
            st.metric("Price Volatility", f"{metrics['volatility_score']:.1f}/10",
                     help="1 = Very Stable, 10 = Very Volatile. Based on price variation")
        with col3:
            st.metric("Trading Volume", f"{metrics['volume_score']:.1f}/10",
                     help="1 = Low Volume, 10 = High Volume. Based on number of transactions")

    @staticmethod
    def display_market_scores(scores: Dict[str, float]):
        """Display enhanced market analysis scores in columns."""
        st.markdown("### Market Analysis Scores")
        
        # Create two rows of metrics
        row1_cols = st.columns(3)
        row2_cols = st.columns(3)
        
        # First row - Core metrics
        with row1_cols[0]:
            st.metric("Price Volatility", f"{scores['volatility_score']:.1f}/10",
                     help="1 = Very Stable, 10 = Very Volatile. Based on price variation between sales")
        with row1_cols[1]:
            st.metric("Market Trend", f"{scores['trend_score']:.1f}/10",
                     help="1 = Declining, 5 = Stable, 10 = Strong Growth. Based on recent price changes")
        with row1_cols[2]:
            st.metric("Market Liquidity", f"{scores['liquidity_score']:.1f}/10",
                     help="1 = Hard to Trade, 10 = Easy to Trade. Based on number of recent sales")
        
        # Second row - Enhanced metrics
        with row2_cols[0]:
            st.metric("Price Momentum", f"{scores['momentum_score']:.1f}/10",
                     help="1 = Strong Decline, 5 = Stable, 10 = Strong Growth. Based on recent price acceleration")
        with row2_cols[1]:
            st.metric("Market Stability", f"{scores['stability_score']:.1f}/10",
                     help="1 = Very Unstable, 10 = Very Stable. Based on price consistency")
        with row2_cols[2]:
            st.metric("Trading Volume", f"{scores['volume_score']:.1f}/10",
                     help="1 = Low Volume, 10 = High Volume. Based on number of recent transactions")

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
    def display_market_segments(segments: Dict[str, Any]):
        """Display market segment analysis."""
        st.markdown("### Market Segments")
        
        # Price Brackets Analysis
        st.markdown("#### Price Distribution")
        price_data = []
        for bracket, info in segments['price_brackets'].items():
            price_data.append({
                'bracket': bracket,
                'volume': info['volume'],
                'avg_price': info['avg_price']
            })
        
        if price_data:
            df = pd.DataFrame(price_data)
            fig = px.bar(df, x='bracket', y='volume',
                        title='Sales Volume by Price Bracket',
                        labels={'bracket': 'Price Range', 'volume': 'Number of Sales'})
            st.plotly_chart(fig, use_container_width=True)
        
        # Condition Analysis if available
        if segments['condition_analysis']:
            st.markdown("#### Condition Analysis")
            condition_data = []
            for condition, info in segments['condition_analysis'].items():
                condition_data.append({
                    'condition': condition,
                    'avg_price': info['avg_price'],
                    'volume': info['volume'],
                    'trend': info['trend']
                })
            
            if condition_data:
                df = pd.DataFrame(condition_data)
                fig = px.scatter(df, x='volume', y='avg_price',
                               size='volume', color='trend',
                               hover_data=['condition'],
                               title='Price vs Volume by Condition',
                               labels={'volume': 'Number of Sales',
                                     'avg_price': 'Average Price ($)',
                                     'trend': 'Price Trend'})
        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def display_recommendations(selected_card: Dict[str, Any], market_data: Dict[str, Any]):
        """Display enhanced recommendations with detailed market insights."""
        st.markdown("### Market Recommendations")
        
        # Get market scores
        scores = market_data['scores']
        metrics = market_data['metrics']
        predictions = market_data.get('predictions', {})
        
        # Calculate overall market sentiment with enhanced factors
        sentiment = (
            scores['trend_score'] * 0.3 +
            scores['momentum_score'] * 0.2 +
            scores['liquidity_score'] * 0.2 +
            scores['stability_score'] * 0.2 +
            scores['volume_score'] * 0.1
        )
        
        # Generate market status
        if sentiment >= 7.5:
            market_status = "🟢 Very Strong"
            market_summary = "The market shows exceptional strength with positive trends across multiple indicators."
        elif sentiment >= 6:
            market_status = "🟡 Strong"
            market_summary = "The market demonstrates solid performance with good fundamentals."
        elif sentiment >= 4.5:
            market_status = "🟡 Stable"
            market_summary = "The market appears stable with balanced supply and demand."
        else:
            market_status = "🔴 Cautious"
            market_summary = "The market shows some uncertainty and may require careful consideration."
        
        # Display market overview
        st.markdown(f"#### Market Status: {market_status}")
        st.markdown(market_summary)
        
        # Display detailed analysis
        st.markdown("#### Key Insights")
        insights = []
        
        # Trend Analysis
        if scores['trend_score'] >= 7:
            insights.append("📈 Strong upward price trend")
        elif scores['trend_score'] <= 3:
            insights.append("📉 Significant price decline")
        
        # Momentum Analysis
        if scores['momentum_score'] >= 7:
            insights.append("🚀 High positive momentum")
        elif scores['momentum_score'] <= 3:
            insights.append("🔻 Negative price momentum")
        
        # Volume Analysis
        if scores['volume_score'] >= 7:
            insights.append("📊 High trading volume")
        elif scores['volume_score'] <= 3:
            insights.append("📊 Low trading volume")
        
        # Stability Analysis
        if scores['stability_score'] >= 7:
            insights.append("🎯 High price stability")
        elif scores['stability_score'] <= 3:
            insights.append("🎯 High price volatility")
        
        for insight in insights:
            st.markdown(f"- {insight}")
        
        # Trading Recommendations
        st.markdown("#### Trading Recommendations")
        
        # Buy recommendation
        st.markdown("**Buyer's Perspective**")
        if sentiment >= 6 and scores['stability_score'] >= 5:
            buy_rec = """
            🟢 **Strong Buy Opportunity**
            - Market shows strong fundamentals
            - Good price stability
            - High potential for value appreciation
            """
        elif sentiment >= 4.5:
            buy_rec = """
            🟡 **Consider Buying**
            - Market conditions are favorable
            - Monitor for optimal entry point
            - Consider dollar-cost averaging
            """
        else:
            buy_rec = """
            🔴 **Exercise Caution**
            - Market shows uncertainty
            - Higher risk environment
            - Wait for more favorable conditions
            """
        st.markdown(buy_rec)
        
        # Sell recommendation
        st.markdown("**Seller's Perspective**")
        if sentiment >= 6 and scores['liquidity_score'] >= 5:
            sell_rec = """
            🟢 **Favorable Selling Conditions**
            - Strong market demand
            - Good liquidity for quick sale
            - Potential for optimal pricing
            """
        elif sentiment >= 4.5:
            sell_rec = """
            🟡 **Moderate Selling Opportunity**
            - Decent market conditions
            - Consider timing and pricing strategy
            - Monitor market for best exit point
            """
        else:
            sell_rec = """
            🔴 **Consider Holding**
            - Challenging selling environment
            - May face pricing pressure
            - Consider waiting for market improvement
            """
        st.markdown(sell_rec)
        
        # Price Outlook
        if predictions and predictions.get('predicted_price'):
            st.markdown("#### Price Outlook")
            pred_price = predictions['predicted_price']
            current_price = metrics['avg_price']
            price_change = ((pred_price - current_price) / current_price) * 100
            
            st.markdown(f"""
            **30-Day Forecast:**
            - Current Average Price: ${current_price:.2f}
            - Predicted Price: ${pred_price:.2f}
            - Expected Change: {price_change:+.1f}%
            - Confidence: {predictions['confidence']*100:.1f}%
            """)

    @staticmethod
    def display_market_analysis(selected_card: Dict[str, Any], market_data: Dict[str, Any]):
        """Display market analysis for a selected card"""
        st.markdown("### Market Analysis")
        
        # Get metrics and scores
        metrics = market_data['metrics']
        scores = market_data['scores']
        sentiment = market_data['sentiment']
        predictions = market_data['predictions']
        
        # Display key metrics
        st.markdown("#### Key Metrics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Average Price",
                f"${metrics['avg_price']:.2f}",
                help="Average sale price over the period"
            )
        with col2:
            st.metric(
                "Median Price",
                f"${metrics['median_price']:.2f}",
                help="Middle price point of all sales"
            )
        with col3:
            st.metric(
                "Price Range",
                f"${metrics['low_price']:.2f} - ${metrics['high_price']:.2f}",
                help="Lowest to highest sale price"
            )
        
        # Display market scores
        st.markdown("#### Market Scores")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "Trend Score",
                f"{scores['trend_score']}/10",
                help="Price trend direction and strength"
            )
        with col2:
            st.metric(
                "Volatility Score",
                f"{scores['volatility_score']}/10",
                help="Price stability and risk"
            )
        with col3:
            st.metric(
                "Liquidity Score",
                f"{scores['liquidity_score']}/10",
                help="Ease of buying/selling"
            )
        with col4:
            st.metric(
                "Momentum Score",
                f"{scores['momentum_score']}/10",
                help="Recent price movement strength"
            )
        
        # Display key insights
        st.markdown("#### Key Insights")
        insights = []
        
        # Trend Analysis
        if scores['trend_score'] >= 7:
            insights.append("📈 Strong upward price trend")
        elif scores['trend_score'] <= 3:
            insights.append("📉 Significant price decline")
        
        # Momentum Analysis
        if scores['momentum_score'] >= 7:
            insights.append("🚀 High positive momentum")
        elif scores['momentum_score'] <= 3:
            insights.append("🔻 Negative price momentum")
        
        # Volume Analysis
        if scores['volume_score'] >= 7:
            insights.append("📊 High trading volume")
        elif scores['volume_score'] <= 3:
            insights.append("📊 Low trading volume")
        
        # Stability Analysis
        if scores['stability_score'] >= 7:
            insights.append("🎯 High price stability")
        elif scores['stability_score'] <= 3:
            insights.append("🎯 High price volatility")
        
        for insight in insights:
            st.markdown(f"- {insight}")
        
        # Trading Recommendations
        st.markdown("#### Trading Recommendations")
        
        # Buy recommendation
        st.markdown("**Buyer's Perspective**")
        if sentiment >= 6 and scores['stability_score'] >= 5:
            buy_rec = """
            🟢 **Strong Buy Opportunity**
            - Market shows strong fundamentals
            - Good price stability
            - High potential for value appreciation
            """
        elif sentiment >= 4.5:
            buy_rec = """
            🟡 **Consider Buying**
            - Market conditions are favorable
            - Monitor for optimal entry point
            - Consider dollar-cost averaging
            """
        else:
            buy_rec = """
            🔴 **Exercise Caution**
            - Market shows uncertainty
            - Higher risk environment
            - Wait for more favorable conditions
            """
        st.markdown(buy_rec)
        
        # Sell recommendation
        st.markdown("**Seller's Perspective**")
        if sentiment >= 6 and scores['liquidity_score'] >= 5:
            sell_rec = """
            🟢 **Favorable Selling Conditions**
            - Strong market demand
            - Good liquidity for quick sale
            - Potential for optimal pricing
            """
        elif sentiment >= 4.5:
            sell_rec = """
            🟡 **Moderate Selling Opportunity**
            - Decent market conditions
            - Consider timing and pricing strategy
            - Monitor market for best exit point
            """
        else:
            sell_rec = """
            🔴 **Consider Holding**
            - Challenging selling environment
            - May face pricing pressure
            - Consider waiting for market improvement
            """
        st.markdown(sell_rec)
        
        # Price Outlook
        if predictions and predictions.get('predicted_price'):
            st.markdown("#### Price Outlook")
            pred_price = predictions['predicted_price']
            current_price = metrics['avg_price']
            price_change = ((pred_price - current_price) / current_price) * 100
            
            st.markdown(f"""
            **30-Day Forecast:**
            - Current Average Price: ${current_price:.2f}
            - Predicted Price: ${pred_price:.2f}
            - Expected Change: {price_change:+.1f}%
            - Confidence: {predictions['confidence']*100:.1f}%
            """)

    @staticmethod
    def display_price_prediction(selected_card: Dict[str, Any], market_data: Dict[str, Any]):
        """Display price predictions with confidence intervals."""
        st.markdown("### Price Predictions")
        
        predictions = market_data['predictions']
        if predictions['predicted_price'] is not None:
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "30-Day Price Prediction",
                    f"${predictions['predicted_price']:.2f}",
                    help="Predicted price in 30 days based on historical trends"
                )
            with col2:
                st.metric(
                    "Prediction Confidence",
                    f"{predictions['confidence']*100:.1f}%",
                    help="Confidence level in the price prediction"
                )
            
            # Display prediction range
            if predictions['prediction_range'][0] is not None:
                st.markdown(f"""
                **Price Range Prediction (95% Confidence)**
                - Low: ${predictions['prediction_range'][0]:.2f}
                - High: ${predictions['prediction_range'][1]:.2f}
                """)

    @staticmethod
    def display_profit_calculator(selected_card: Dict[str, Any], market_data: Dict[str, Any]):
        """Display profit calculator for a card"""
        st.markdown("### Profit Calculator")
        
        # Initialize calculator
        calculator = ProfitCalculator()
        
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
        condition = selected_card.get('condition', '').lower()
        
        # If card is raw, show grading analysis
        if condition == 'raw':
            st.markdown("### Grading Analysis")
            
            # Calculate scenarios
            card_data = {
                'price': purchase_price,
                'market_data': market_data,
                'search_params': st.session_state.search_params
            }
            
            # Calculate PSA 9 scenario
            psa9_scenario = calculator._calculate_graded_scenario(card_data, 'PSA 9')
            psa9_price = psa9_scenario['market_price']
            psa9_source = "Recent PSA 9 Sale" if psa9_scenario['price_source'] == "historical" else "Estimated (1.5x raw value)"
            
            # Calculate PSA 10 scenario
            psa10_scenario = calculator._calculate_graded_scenario(card_data, 'PSA 10')
            psa10_price = psa10_scenario['market_price']
            psa10_source = "Recent PSA 10 Sale" if psa10_scenario['price_source'] == "historical" else "Estimated (3.0x raw value)"
            
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
                    help=f"Source: {psa9_source}"
                )
            with col2:
                st.metric(
                    "PSA 10 Value",
                    f"${psa10_price:.2f}",
                    f"{psa10_roi:+.1f}% vs Avg",
                    help=f"Source: {psa10_source}"
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