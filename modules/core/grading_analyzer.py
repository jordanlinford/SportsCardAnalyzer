from typing import Dict, List, Any
import streamlit as st
from modules.ui.indicators import RecommendationIndicator

class GradingAnalyzer:
    @staticmethod
    def analyze_grading_potential(card_data: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the potential value of grading a raw card.
        
        Args:
            card_data: Dictionary containing card information
            market_data: Dictionary containing market analysis data
            
        Returns:
            Dictionary containing grading analysis results
        """
        # Get current market value
        current_value = market_data['metrics']['avg_price']
        
        # Default multipliers if no graded sales found
        psa9_multiplier = 1.5
        psa10_multiplier = 3.0
        
        # Initialize price sources
        psa9_source = f"Estimated ({psa9_multiplier}x raw value)"
        psa10_source = f"Estimated ({psa10_multiplier}x raw value)"
        
        # Search for actual PSA 9 and PSA 10 sales
        psa9_price = None
        psa10_price = None
        
        if isinstance(market_data.get('sales', []), list):
            psa9_sales = [sale for sale in market_data['sales'] if 'psa 9' in sale.get('title', '').lower()]
            psa10_sales = [sale for sale in market_data['sales'] if 'psa 10' in sale.get('title', '').lower()]
            
            if psa9_sales:
                psa9_price = psa9_sales[0]['price']
                psa9_source = "Recent PSA 9 Sale"
            else:
                psa9_price = current_value * psa9_multiplier
                
            if psa10_sales:
                psa10_price = psa10_sales[0]['price']
                psa10_source = "Recent PSA 10 Sale"
            else:
                psa10_price = current_value * psa10_multiplier
        
        # Calculate grading costs
        grading_fee = 25.0  # PSA grading fee
        shipping_cost = 10.0  # Estimated shipping cost
        total_grading_cost = grading_fee + shipping_cost
        
        # Calculate break-even prices and profits
        break_even = current_value + total_grading_cost
        psa9_profit = psa9_price - break_even if psa9_price else None
        psa10_profit = psa10_price - break_even if psa10_price else None
        
        # Calculate ROI for each grade
        psa9_roi = (psa9_profit / break_even * 100) if psa9_profit and break_even > 0 else None
        psa10_roi = (psa10_profit / break_even * 100) if psa10_profit and break_even > 0 else None
        
        # Generate recommendation
        recommendation = RecommendationIndicator.get_grading_recommendation(
            psa10_profit,
            psa9_profit,
            total_grading_cost
        )
        
        return {
            'current_value': current_value,
            'psa9_price': psa9_price,
            'psa10_price': psa10_price,
            'psa9_source': psa9_source,
            'psa10_source': psa10_source,
            'grading_fee': grading_fee,
            'shipping_cost': shipping_cost,
            'total_grading_cost': total_grading_cost,
            'break_even': break_even,
            'psa9_profit': psa9_profit,
            'psa10_profit': psa10_profit,
            'psa9_roi': psa9_roi,
            'psa10_roi': psa10_roi,
            'recommendation': recommendation['recommendation'],
            'recommendation_color': recommendation['color'],
            'recommendation_icon': recommendation['icon']
        } 