from typing import List, Dict, Optional
from modules.core.database_service import DatabaseService
from modules.core.models import Card
import streamlit as st
import logging
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MarketManager:
    """Manager for handling market analysis operations."""
    
    def __init__(self):
        """Initialize the market manager."""
        self._db = DatabaseService()
        
    def analyze_market_trends(self, cards: List[Card], time_period: str = '30d') -> Dict:
        """
        Analyze market trends for a list of cards.
        
        Args:
            cards (List[Card]): List of cards to analyze
            time_period (str): Time period for analysis (e.g., '30d', '90d', '1y')
            
        Returns:
            Dict: Market analysis results
        """
        try:
            # Convert time period to days
            days = int(time_period[:-1])
            
            # Get historical data for each card
            historical_data = []
            for card in cards:
                # In a real implementation, this would fetch from an external API
                # For now, we'll simulate some data
                historical_data.append({
                    'player_name': card.player_name,
                    'year': card.year,
                    'card_set': card.card_set,
                    'card_number': card.card_number,
                    'current_value': card.value or 0,
                    'price_history': self._generate_simulated_price_history(card.value or 0, days)
                })
                
            # Calculate trends
            trends = []
            for data in historical_data:
                price_history = data['price_history']
                if len(price_history) > 1:
                    start_price = price_history[0]['value']
                    end_price = price_history[-1]['value']
                    price_change = end_price - start_price
                    percent_change = (price_change / start_price) * 100 if start_price > 0 else 0
                    
                    trends.append({
                        'player_name': data['player_name'],
                        'year': data['year'],
                        'card_set': data['card_set'],
                        'card_number': data['card_number'],
                        'current_value': data['current_value'],
                        'price_change': price_change,
                        'percent_change': percent_change,
                        'trend': 'up' if percent_change > 0 else 'down' if percent_change < 0 else 'stable'
                    })
                    
            return {
                'trends': trends,
                'time_period': time_period,
                'total_cards_analyzed': len(cards)
            }
        except Exception as e:
            logger.error(f"Error analyzing market trends: {str(e)}")
            return {
                'trends': [],
                'time_period': time_period,
                'total_cards_analyzed': 0
            }
            
    def get_market_insights(self, cards: List[Card]) -> Dict:
        """
        Get market insights for a list of cards.
        
        Args:
            cards (List[Card]): List of cards to analyze
            
        Returns:
            Dict: Market insights
        """
        try:
            # Group cards by player
            cards_by_player = {}
            for card in cards:
                if card.player_name in cards_by_player:
                    cards_by_player[card.player_name].append(card)
                else:
                    cards_by_player[card.player_name] = [card]
                    
            # Calculate insights
            insights = {
                'total_value': sum(card.value or 0 for card in cards),
                'average_value': sum(card.value or 0 for card in cards) / len(cards) if cards else 0,
                'highest_value_card': max(cards, key=lambda x: x.value or 0) if cards else None,
                'player_distribution': {
                    player: len(player_cards) for player, player_cards in cards_by_player.items()
                },
                'year_distribution': self._get_year_distribution(cards),
                'set_distribution': self._get_set_distribution(cards)
            }
            
            return insights
        except Exception as e:
            logger.error(f"Error getting market insights: {str(e)}")
            return {
                'total_value': 0,
                'average_value': 0,
                'highest_value_card': None,
                'player_distribution': {},
                'year_distribution': {},
                'set_distribution': {}
            }
            
    def _generate_simulated_price_history(self, current_value: float, days: int) -> List[Dict]:
        """
        Generate simulated price history for a card.
        
        Args:
            current_value (float): Current value of the card
            days (int): Number of days of history to generate
            
        Returns:
            List[Dict]: List of price history entries
        """
        try:
            # Generate random price movements
            import random
            history = []
            value = current_value
            
            for i in range(days):
                # Simulate daily price change (-5% to +5%)
                change = random.uniform(-0.05, 0.05)
                value = value * (1 + change)
                
                history.append({
                    'date': (datetime.now() - timedelta(days=days-i)).strftime('%Y-%m-%d'),
                    'value': round(value, 2)
                })
                
            return history
        except Exception as e:
            logger.error(f"Error generating price history: {str(e)}")
            return []
            
    def _get_year_distribution(self, cards: List[Card]) -> Dict[int, int]:
        """
        Get distribution of cards by year.
        
        Args:
            cards (List[Card]): List of cards
            
        Returns:
            Dict[int, int]: Distribution of cards by year
        """
        try:
            distribution = {}
            for card in cards:
                if card.year in distribution:
                    distribution[card.year] += 1
                else:
                    distribution[card.year] = 1
            return distribution
        except Exception as e:
            logger.error(f"Error getting year distribution: {str(e)}")
            return {}
            
    def _get_set_distribution(self, cards: List[Card]) -> Dict[str, int]:
        """
        Get distribution of cards by set.
        
        Args:
            cards (List[Card]): List of cards
            
        Returns:
            Dict[str, int]: Distribution of cards by set
        """
        try:
            distribution = {}
            for card in cards:
                if card.card_set in distribution:
                    distribution[card.card_set] += 1
                else:
                    distribution[card.card_set] = 1
            return distribution
        except Exception as e:
            logger.error(f"Error getting set distribution: {str(e)}")
            return {} 