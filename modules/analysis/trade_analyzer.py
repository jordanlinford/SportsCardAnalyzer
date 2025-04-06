"""
Trade analyzer module for evaluating card trades.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

class TradeAnalyzer:
    """Analyzes potential trades between sports cards."""
    
    def __init__(self):
        """Initialize the trade analyzer."""
        self.market_multipliers = {
            'hot': 1.2,      # Hot players/cards may command premium
            'stable': 1.0,   # Stable market value
            'cooling': 0.8   # Declining interest
        }
        
        self.condition_multipliers = {
            'PSA 10': 1.0,   # PSA 10 is baseline for graded
            'PSA 9': 0.5,    # PSA 9 typically half of PSA 10
            'Raw': 0.3       # Raw cards typically 30% of PSA 10
        }
    
    def analyze_trade(self, 
                     giving_cards: List[Dict[str, Any]], 
                     receiving_cards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a potential trade between two sets of cards.
        
        Args:
            giving_cards: List of cards being given in trade
            receiving_cards: List of cards being received in trade
            
        Returns:
            Dict containing trade analysis results
        """
        # Calculate values for each side
        giving_value = self._calculate_total_value(giving_cards)
        receiving_value = self._calculate_total_value(receiving_cards)
        
        # Calculate value difference
        value_difference = receiving_value - giving_value
        percentage_difference = (value_difference / giving_value * 100) if giving_value > 0 else 0
        
        # Calculate average metrics for each side
        giving_metrics = self._calculate_average_metrics(giving_cards)
        receiving_metrics = self._calculate_average_metrics(receiving_cards)
        
        # Calculate metric differences
        metric_differences = {
            'trend_difference': receiving_metrics['avg_trend'] - giving_metrics['avg_trend'],
            'volatility_difference': receiving_metrics['avg_volatility'] - giving_metrics['avg_volatility'],
            'liquidity_difference': receiving_metrics['avg_liquidity'] - giving_metrics['avg_liquidity']
        }
        
        # Determine trade fairness
        fairness_score = self._calculate_fairness_score(giving_value, receiving_value)
        
        # Calculate risk levels
        giving_risk = self._calculate_risk_score(giving_cards)
        receiving_risk = self._calculate_risk_score(receiving_cards)
        
        # Generate recommendations
        recommendation, details = self._generate_recommendation(
            giving_value, receiving_value,
            giving_risk, receiving_risk,
            metric_differences
        )
        
        return {
            'giving_value': giving_value,
            'receiving_value': receiving_value,
            'total_value': receiving_value,
            'value_difference': value_difference,
            'percentage_difference': percentage_difference,
            'fairness_score': fairness_score,
            'giving_risk': giving_risk,
            'receiving_risk': receiving_risk,
            'giving_metrics': giving_metrics,
            'receiving_metrics': receiving_metrics,
            'metric_differences': metric_differences,
            'recommendation': recommendation,
            'recommendation_details': details,
            'giving_health': giving_metrics['avg_liquidity'],
            'receiving_health': receiving_metrics['avg_liquidity'],
            'giving_trend': giving_metrics['avg_trend'],
            'receiving_trend': receiving_metrics['avg_trend']
        }
    
    def _calculate_total_value(self, cards: List[Dict[str, Any]]) -> float:
        """Calculate the total value of a set of cards."""
        total_value = 0.0
        
        for card in cards:
            # Get base market value
            market_value = float(card.get('market_value', 0.0))
            
            # Apply condition multiplier
            condition = card.get('condition', 'Raw')
            condition_multiplier = self.condition_multipliers.get(condition, 1.0)
            
            # Apply market trend multiplier
            trend = card.get('market_trend', 'stable')
            trend_multiplier = self.market_multipliers.get(trend, 1.0)
            
            # Calculate final value
            card_value = market_value * condition_multiplier * trend_multiplier
            total_value += card_value
        
        return total_value
    
    def _calculate_fairness_score(self, giving_value: float, receiving_value: float) -> float:
        """Calculate how fair the trade is on a scale of 0-10."""
        if giving_value == 0 or receiving_value == 0:
            return 0
            
        # Calculate ratio of values
        ratio = min(giving_value, receiving_value) / max(giving_value, receiving_value)
        
        # Convert to 0-10 scale
        score = ratio * 10
        
        return round(score, 1)
    
    def _calculate_risk_score(self, cards: List[Dict[str, Any]]) -> float:
        """Calculate the risk level of a set of cards on a scale of 0-10."""
        if not cards:
            return 0
            
        total_risk = 0
        
        for card in cards:
            # Factors that affect risk
            volatility = float(card.get('price_volatility', 5.0))
            liquidity = float(card.get('liquidity_score', 5.0))
            market_trend = card.get('market_trend', 'stable')
            
            # Calculate risk score for this card
            card_risk = (
                volatility * 0.4 +                    # Higher volatility = higher risk
                (10 - liquidity) * 0.4 +             # Lower liquidity = higher risk
                (10 if market_trend == 'hot' else    # Hot market might be unstable
                 5 if market_trend == 'stable' else  # Stable market is lower risk
                 8) * 0.2                           # Cooling market has moderate risk
            )
            
            total_risk += card_risk
        
        # Average risk across all cards
        avg_risk = total_risk / len(cards)
        
        return round(min(10, max(0, avg_risk)), 1)
    
    def _calculate_average_metrics(self, cards: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate average metrics for a set of cards."""
        if not cards:
            return {
                'avg_trend': 0.0,
                'avg_volatility': 0.0,
                'avg_liquidity': 0.0
            }
        
        # Calculate trend score based on market value changes
        total_trend = 0.0
        for card in cards:
            try:
                current_value = float(card.get('market_value', 0.0))
                forecast_30d = float(card.get('30_day_forecast', current_value))
                forecast_90d = float(card.get('90_day_forecast', current_value))
                
                # Calculate trend as percentage change
                if current_value > 0:
                    trend_30d = ((forecast_30d - current_value) / current_value) * 100
                    trend_90d = ((forecast_90d - current_value) / current_value) * 100
                    # Use weighted average of 30d and 90d trends
                    card_trend = (trend_30d * 0.7) + (trend_90d * 0.3)
                else:
                    card_trend = 0.0
                
                total_trend += card_trend
            except (ValueError, TypeError, ZeroDivisionError):
                continue
        
        total_volatility = sum(float(card.get('volatility_score', 5.0)) for card in cards)
        total_liquidity = sum(float(card.get('liquidity_score', 5.0)) for card in cards)
        
        return {
            'avg_trend': round(total_trend / len(cards), 1) if cards else 0.0,
            'avg_volatility': round(total_volatility / len(cards), 1) if cards else 0.0,
            'avg_liquidity': round(total_liquidity / len(cards), 1) if cards else 0.0
        }
    
    def _generate_recommendation(self,
                               giving_value: float,
                               receiving_value: float,
                               giving_risk: float,
                               receiving_risk: float,
                               metric_differences: Dict[str, float]) -> tuple[str, str]:
        """Generate a trade recommendation based on values, risks, and metrics."""
        value_ratio = receiving_value / giving_value if giving_value > 0 else 0
        risk_difference = receiving_risk - giving_risk
        
        # Calculate financial impact
        value_difference = receiving_value - giving_value
        value_difference_percent = (value_difference / giving_value * 100) if giving_value > 0 else 0
        
        # Initialize recommendation components
        value_component = ""
        risk_component = ""
        trend_component = ""
        metrics_component = ""
        financial_impact = ""
        
        # Analyze value ratio and financial impact
        if value_ratio >= 1.2:
            value_component = "Receiving significantly more value"
            financial_impact = f"Potential gain: ${value_difference:.2f} ({value_difference_percent:+.1f}%)"
        elif value_ratio >= 1.1:
            value_component = "Receiving more value"
            financial_impact = f"Potential gain: ${value_difference:.2f} ({value_difference_percent:+.1f}%)"
        elif value_ratio >= 0.9:
            value_component = "Fair value"
            financial_impact = f"Minimal financial impact: ${value_difference:.2f} ({value_difference_percent:+.1f}%)"
        elif value_ratio >= 0.8:
            value_component = "Receiving slightly less value"
            financial_impact = f"Potential loss: ${abs(value_difference):.2f} ({value_difference_percent:+.1f}%)"
        else:
            value_component = "Receiving significantly less value"
            financial_impact = f"Significant potential loss: ${abs(value_difference):.2f} ({value_difference_percent:+.1f}%)"
        
        # Analyze risk difference
        if risk_difference <= -2:
            risk_component = "with much lower risk"
        elif risk_difference <= -1:
            risk_component = "with lower risk"
        elif risk_difference <= 1:
            risk_component = "with similar risk"
        else:
            risk_component = "but with higher risk"
        
        # Analyze trend and metrics
        trend_diff = metric_differences['trend_difference']
        if abs(trend_diff) >= 5:
            trend_component = f"Cards you're {'receiving' if trend_diff > 0 else 'giving'} show stronger price trends"
        
        # Analyze other metrics
        metrics_insights = []
        if abs(metric_differences['volatility_difference']) >= 2:
            metrics_insights.append(
                f"{'Higher' if metric_differences['volatility_difference'] > 0 else 'Lower'} price volatility"
            )
        if abs(metric_differences['liquidity_difference']) >= 2:
            metrics_insights.append(
                f"{'Better' if metric_differences['liquidity_difference'] > 0 else 'Worse'} market liquidity"
            )
        
        if metrics_insights:
            metrics_component = f"Note: {', '.join(metrics_insights)} in cards you're receiving"
        
        # Generate final recommendation with financial impact
        if value_ratio >= 1.2 and risk_difference <= 2:
            recommendation = "Strong Accept"
            recommendation_details = (
                f"Strong Accept - {value_component} {risk_component}. "
                f"{financial_impact}. "
                f"{trend_component}. "
                f"{metrics_component}. "
                "This trade presents a significant opportunity for value appreciation with manageable risk."
            )
        elif value_ratio >= 1.1 and risk_difference <= 1:
            recommendation = "Accept"
            recommendation_details = (
                f"Accept - {value_component} {risk_component}. "
                f"{financial_impact}. "
                f"{trend_component}. "
                f"{metrics_component}. "
                "This trade offers good value with reasonable risk."
            )
        elif value_ratio >= 0.9 and risk_difference <= 0:
            recommendation = "Consider"
            recommendation_details = (
                f"Consider - {value_component} {risk_component}. "
                f"{financial_impact}. "
                f"{trend_component}. "
                f"{metrics_component}. "
                "This trade is fair but may not offer significant advantages."
            )
        elif value_ratio >= 0.8 and risk_difference <= -2:
            recommendation = "Consider"
            recommendation_details = (
                f"Consider - {value_component} {risk_component}. "
                f"{financial_impact}. "
                f"{trend_component}. "
                f"{metrics_component}. "
                "The lower risk profile may justify the slight value difference."
            )
        elif value_ratio < 0.8:
            recommendation = "Decline"
            recommendation_details = (
                f"Decline - {value_component} {risk_component}. "
                f"{financial_impact}. "
                f"{trend_component}. "
                f"{metrics_component}. "
                "The significant value loss makes this trade unfavorable."
            )
        elif risk_difference > 2:
            recommendation = "Decline"
            recommendation_details = (
                f"Decline - {value_component} {risk_component}. "
                f"{financial_impact}. "
                f"{trend_component}. "
                f"{metrics_component}. "
                "The high risk profile outweighs any potential value gains."
            )
        else:
            recommendation = "Consider"
            recommendation_details = (
                f"Consider - {value_component} {risk_component}. "
                f"{financial_impact}. "
                f"{trend_component}. "
                f"{metrics_component}. "
                "This trade presents a balanced opportunity that requires careful consideration."
            )
        
        return recommendation, recommendation_details.strip() 