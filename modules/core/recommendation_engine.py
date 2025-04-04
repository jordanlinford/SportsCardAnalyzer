"""
Recommendation Engine module for Sports Card Analyzer Pro.
Provides comprehensive analysis and recommendations for sports cards.
"""

from typing import Dict, Any
import streamlit as st
from datetime import datetime
import re

class RecommendationEngine:
    def __init__(self):
        pass

    def _extract_player_name(self, card_title: str) -> str:
        """Extract player name from card title."""
        # Remove year and card numbers
        name_part = re.sub(r'\d{4}|\#\d+', '', card_title)
        # Remove common card terms
        name_part = re.sub(r'PSA|BGS|SGC|\d+|\(.*?\)|RC|Rookie|Card|Prizm|Optic|Chrome|Refractor|Auto|Parallel|/\d+', '', name_part, flags=re.IGNORECASE)
        return name_part.strip()

    def _analyze_market_metrics(self, market_data: Dict[str, Any]) -> Dict[str, str]:
        """Analyze market metrics and generate insights."""
        metrics = market_data.get('metrics', {})
        
        # Market health analysis
        market_health = float(metrics.get('market_health_score', 0))
        health_analysis = (
            "very healthy and active" if market_health >= 8 else
            "healthy" if market_health >= 6 else
            "moderately healthy" if market_health >= 4 else
            "showing some weakness" if market_health >= 2 else
            "concerning"
        )

        # Price trend analysis
        trend_score = float(metrics.get('trend_score', 0))
        trend_analysis = (
            "strongly upward" if trend_score >= 8 else
            "moderately upward" if trend_score >= 6 else
            "stable" if trend_score >= 4 else
            "showing some decline" if trend_score >= 2 else
            "declining significantly"
        )

        # Liquidity analysis
        liquidity_score = float(metrics.get('liquidity_score', 0))
        liquidity_analysis = (
            "highly liquid" if liquidity_score >= 8 else
            "reasonably liquid" if liquidity_score >= 6 else
            "moderately liquid" if liquidity_score >= 4 else
            "somewhat illiquid" if liquidity_score >= 2 else
            "illiquid"
        )

        return {
            'health': health_analysis,
            'trend': trend_analysis,
            'liquidity': liquidity_analysis
        }

    def _generate_price_insights(self, market_data: Dict[str, Any], profit_data: Dict[str, Any]) -> str:
        """Generate insights about pricing and value."""
        metrics = market_data.get('metrics', {})
        avg_price = float(metrics.get('average_price', 0))
        median_price = float(metrics.get('median_price', 0))
        
        price_insights = []
        
        # Compare average to median
        price_diff_pct = ((avg_price - median_price) / median_price * 100) if median_price > 0 else 0
        if abs(price_diff_pct) > 10:
            if avg_price > median_price:
                price_insights.append("The market shows some high-value outlier listings, suggesting potential premium opportunities for rare variations.")
            else:
                price_insights.append("There are some bargain listings available below the typical market price.")

        # Add ROI insights if available
        if profit_data:
            roi = float(profit_data.get('roi', 0))
            if roi > 20:
                price_insights.append(f"The potential ROI of {roi:.1f}% is notably strong.")
            elif roi > 10:
                price_insights.append(f"The potential ROI of {roi:.1f}% is reasonable.")
            elif roi > 0:
                price_insights.append(f"The potential ROI of {roi:.1f}% is modest.")
            else:
                price_insights.append("The current price point may not offer favorable ROI.")

        return " ".join(price_insights)

    def _generate_buyer_recommendation(self, market_analysis: Dict[str, str], price_insights: str) -> str:
        """Generate specific recommendations for buyers."""
        health = market_analysis['health']
        trend = market_analysis['trend']
        liquidity = market_analysis['liquidity']
        
        if "healthy" in health and "upward" in trend:
            timing = "Consider buying soon, as prices show strength and could continue rising."
        elif "declining" in trend and "liquid" in liquidity:
            timing = "This could be a good buying opportunity if you believe in the long-term value."
        elif "stable" in trend:
            timing = "The market is stable, making it a reasonable time to buy if the price meets your criteria."
        else:
            timing = "Exercise caution and consider waiting for more favorable market conditions."

        return f"Buyer's Recommendation: {timing} The market is {health} and {liquidity}. {price_insights}"

    def _generate_seller_recommendation(self, market_analysis: Dict[str, str], price_insights: str) -> str:
        """Generate specific recommendations for sellers."""
        health = market_analysis['health']
        trend = market_analysis['trend']
        liquidity = market_analysis['liquidity']
        
        if "upward" in trend and "liquid" in liquidity:
            timing = "Consider selling now to capitalize on strong market conditions."
        elif "declining" in trend:
            timing = "If you're looking to sell, you might want to act soon or be prepared to hold longer term."
        elif "stable" in trend and "healthy" in health:
            timing = "Current market conditions are favorable for selling if your price expectations are met."
        else:
            timing = "Consider holding unless you need to sell, as market conditions could improve."

        return f"Seller's Recommendation: {timing} The market is {health} and {liquidity}. {price_insights}"

    def display_recommendations(self, card_data: Dict[str, Any], market_data: Dict[str, Any], profit_data: Dict[str, Any]) -> None:
        """Display comprehensive recommendations in the Streamlit UI."""
        st.markdown("---")  # Visual separator
        st.subheader("📊 Final Recommendation")
        
        # Market Analysis
        market_analysis = self._analyze_market_metrics(market_data)
        price_insights = self._generate_price_insights(market_data, profit_data)
        
        # Overall Market Summary
        st.markdown("#### Market Overview")
        st.write(f"""
        The market for this card is currently {market_analysis['health']}, with prices showing a {market_analysis['trend']} trend. 
        Trading activity indicates the market is {market_analysis['liquidity']}. {price_insights}
        """)
        
        # Player Name
        player_name = self._extract_player_name(card_data.get('title', ''))
        
        # Player News and Context
        st.markdown("#### Recent Context")
        st.info(f"""
        💡 **Player:** {player_name}
        
        To make a fully informed decision, consider:
        - Check recent player performance and news
        - Monitor upcoming games or events that could impact value
        - Research any recent sales of similar cards
        - Consider the overall market conditions for this sport/player
        """)
        
        # Recommendations
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### For Buyers")
            st.write(self._generate_buyer_recommendation(market_analysis, price_insights))
            
        with col2:
            st.markdown("#### For Sellers")
            st.write(self._generate_seller_recommendation(market_analysis, price_insights))
        
        # Risk Factors
        st.markdown("#### Risk Factors to Consider")
        st.warning("""
        ⚠️ **Key Risk Factors:**
        - Market volatility and trading volume
        - Player performance and team dynamics
        - Overall sports card market conditions
        - Grading population changes
        - Seasonal market fluctuations
        """) 