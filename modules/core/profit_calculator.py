"""
Profit Calculator module for Sports Card Analyzer Pro.
Handles all profit-related calculations and scenarios for sports cards.
"""

from typing import Dict, Any, List
import streamlit as st
from scrapers.ebay_interface import EbayInterface
import numpy as np
from datetime import datetime, timedelta
from modules.core.recommendation_engine import RecommendationEngine

class ProfitCalculator:
    def __init__(self):
        self.scraper = EbayInterface()
        self.recommendation_engine = RecommendationEngine()
        self.scenarios = {
            "Raw": self._calculate_raw_scenario,
            "PSA 9": self._calculate_psa9_scenario,
            "PSA 10": self._calculate_psa10_scenario
        }
        # Define grading service parameters
        self.grading_params = {
            'turnaround_time_days': {
                'n/a': 0,
                'economy': 30,
                'regular': 15,
                'express': 5,
                'other': 0
            },
            'grading_costs': {
                'n/a': 0,
                'economy': 50,
                'regular': 100,
                'express': 200,
                'other': 0
            },
            'psa9_probability': 0.50,    # 50% chance of PSA 9
            'psa10_probability': 0.20,   # 20% chance of PSA 10
            'lower_grade_probability': 0.30  # 30% chance of PSA 8 or lower
        }

    def calculate_profits(self, card_data: Dict[str, Any], scenario: str) -> Dict[str, Any]:
        """Calculate profits for a given card and scenario."""
        if scenario not in self.scenarios:
            raise ValueError(f"Invalid scenario: {scenario}")
        
        # Get graded card data if we don't already have it
        if 'graded_data' not in card_data:
            card_data['graded_data'] = self.scraper.get_graded_card_data(card_data)
        
        return self.scenarios[scenario](card_data)

    def _remove_outliers(self, prices: List[float]) -> List[float]:
        """Remove outliers using IQR method."""
        if not prices:
            return prices
            
        q1 = np.percentile(prices, 25)
        q3 = np.percentile(prices, 75)
        iqr = q3 - q1
        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 + (1.5 * iqr)
        
        return [x for x in prices if lower_bound <= x <= upper_bound]

    def _calculate_raw_scenario(self, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate immediate selling profit for raw card."""
        # Initialize values
        market_price = 0.0
        price_source = "estimated"
        recent_sales = []
        sales_count = 0

        # Get market data
        market_data = card_data.get('market_data', {})
        
        if market_data:
            # Try to get median price from market metrics
            market_price = float(market_data.get('median_price', 0.0))
            
            # Get recent sales if available
            if 'price_data' in market_data:
                raw_sales = [
                    {'price': sale['price'], 'date': sale['date'], 'title': sale.get('title', '')}
                    for sale in market_data['price_data']
                    if not any(grade.lower() in sale.get('title', '').lower() 
                             for grade in ['psa', 'bgs', 'sgc'])
                ]
                
                if raw_sales:
                    # Get prices from raw sales
                    prices = [sale['price'] for sale in raw_sales]
                    # Remove outliers
                    cleaned_prices = self._remove_outliers(prices)
                    if cleaned_prices:
                        market_price = np.median(cleaned_prices)
                        price_source = "historical"
                        recent_sales = [sale for sale in raw_sales 
                                      if sale['price'] in cleaned_prices]
                        sales_count = len(cleaned_prices)
        
        # Get user inputs (defaulting to 0)
        purchase_price = float(card_data.get('price', 0.0))
        shipping_cost = float(card_data.get('shipping_cost', 0.0))
        seller_fee_percentage = float(card_data.get('seller_fee_percentage', 12.9))  # Default to eBay fee
        
        # Calculate fees based on market price
        seller_fee_amount = market_price * (seller_fee_percentage / 100)
        
        # Calculate base costs (excluding seller fees)
        base_costs = purchase_price + shipping_cost
        
        # Calculate break-even price
        if seller_fee_percentage < 100:
            break_even_price = base_costs / (1 - seller_fee_percentage/100)
        else:
            break_even_price = float('inf')
        
        # Calculate total costs and profit
        total_costs = base_costs + seller_fee_amount
        net_profit = market_price - total_costs
        roi = (net_profit / purchase_price * 100) if purchase_price > 0 else 0
        
        return {
            'scenario_type': 'immediate_sale',
            'market_price': market_price,
            'purchase_price': purchase_price,
            'base_costs': base_costs,
            'total_costs': total_costs,
            'net_profit': net_profit,
            'roi': roi,
            'break_even_price': break_even_price,
            'price_source': price_source,
            'sales_count': sales_count,
            'shipping_cost': shipping_cost,
            'seller_fee': seller_fee_percentage,
            'seller_fee_amount': seller_fee_amount,
            'timeline': 'Immediate sale possible',
            'risk_level': 'Low - based on current market prices',
            'recent_sales': recent_sales
        }

    def _calculate_graded_scenario(self, card_data: Dict[str, Any], target_grade: str) -> Dict[str, Any]:
        """Calculate profit potential for grading scenario."""
        # Initialize values
        market_price = 0.0
        price_source = "estimated"
        recent_sales = []
        sales_count = 0
        
        # Get the original search parameters
        search_params = card_data.get('search_params', {})
        if search_params:
            # Create a search query for graded version
            player_name = search_params.get('player_name', '')
            year = search_params.get('year', '')
            card_set = search_params.get('card_set', '')
            card_number = search_params.get('card_number', '')
            variation = search_params.get('variation', '')
            
            # Build search query for graded version
            graded_query = f"{year} {player_name} {card_set}"
            if card_number:
                graded_query += f" #{card_number}"
            if variation:
                graded_query += f" {variation}"
            graded_query += f" {target_grade}"
            
            # Search for graded sales
            try:
                graded_results = self.scraper.search_cards(
                    query=graded_query,
                    scenario=target_grade
                )
                
                if graded_results:
                    # Filter results for exact variation if specified
                    if variation:
                        filtered_results = []
                        for result in graded_results:
                            if variation.lower() in result.get('title', '').lower():
                                filtered_results.append(result)
                        graded_results = filtered_results
                    
                    if graded_results:
                        # Extract prices from results
                        prices = [float(result['price']) for result in graded_results]
                        # Remove outliers
                        cleaned_prices = self._remove_outliers(prices)
                        if cleaned_prices:
                            market_price = np.median(cleaned_prices)
                            price_source = "historical"
                            recent_sales = [
                                {
                                    'price': result['price'],
                                    'date': result.get('date', 'N/A'),
                                    'title': result.get('title', '')
                                }
                                for result in graded_results
                                if float(result['price']) in cleaned_prices
                            ]
                            sales_count = len(cleaned_prices)
            except Exception as e:
                st.warning(f"Could not fetch {target_grade} sales data: {str(e)}")
        
        # If no graded sales data found, estimate from raw market price
        if market_price == 0:
            # Get raw market price from market_data
            market_data = card_data.get('market_data', {})
            raw_price = float(market_data.get('median_price', 0.0))
            
            # Apply grading multiplier
            multiplier = 2 if target_grade == "PSA 9" else 4
            market_price = raw_price * multiplier
            price_source = "estimated"
        
        # Get costs
        purchase_price = float(card_data.get('price', 0.0))
        grading_service = card_data.get('grading_service', 'economy')
        grading_cost = self.grading_params['grading_costs'][grading_service]
        shipping_cost = card_data.get('shipping_cost', 0.0)
        seller_fee_percentage = float(card_data.get('seller_fee_percentage', 0.0))
        
        # Calculate fees based on market price
        seller_fee_amount = market_price * (seller_fee_percentage / 100)
        
        # Calculate base costs (excluding seller fees)
        base_costs = purchase_price + grading_cost + shipping_cost
        
        # Calculate break-even price (excluding seller fees since they're percentage based)
        if seller_fee_percentage < 100:
            break_even_price = base_costs / (1 - seller_fee_percentage/100)
        else:
            break_even_price = float('inf')
        
        # Calculate total costs (including seller fees)
        total_costs = base_costs + seller_fee_amount
        
        # Calculate expected value based on grade probabilities
        if target_grade == "PSA 9":
            success_probability = self.grading_params['psa9_probability']
        else:  # PSA 10
            success_probability = self.grading_params['psa10_probability']
        
        # Calculate expected value and risk-adjusted returns
        expected_value = market_price * success_probability
        net_profit = expected_value - total_costs
        roi = (net_profit / purchase_price * 100) if purchase_price > 0 else 0
        
        # Calculate timeline
        grading_time = self.grading_params['turnaround_time_days'][grading_service]
        expected_completion = datetime.now() + timedelta(days=grading_time)
        
        return {
            'scenario_type': 'grading',
            'target_grade': target_grade,
            'market_price': market_price,
            'purchase_price': purchase_price,
            'base_costs': base_costs,
            'total_costs': total_costs,
            'net_profit': net_profit,
            'roi': roi,
            'break_even_price': break_even_price,
            'price_source': price_source,
            'recent_sales': recent_sales,
            'sales_count': sales_count,
            'grading_cost': grading_cost,
            'shipping_cost': shipping_cost,
            'seller_fee': seller_fee_percentage,
            'seller_fee_amount': seller_fee_amount,
            'success_probability': success_probability * 100,
            'grading_service': grading_service,
            'grading_time': grading_time,
            'expected_completion': expected_completion.strftime('%Y-%m-%d'),
            'timeline': f"{grading_time} days for grading + shipping time",
            'risk_level': 'High - depends on card condition and grading standards',
            'lower_grade_probability': self.grading_params['lower_grade_probability'] * 100
        }

    def _calculate_psa9_scenario(self, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate PSA 9 grading scenario."""
        return self._calculate_graded_scenario(card_data, "PSA 9")

    def _calculate_psa10_scenario(self, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate PSA 10 grading scenario."""
        return self._calculate_graded_scenario(card_data, "PSA 10")

    def display_profit_analysis(self, card_data: Dict[str, Any]) -> None:
        """Display profit analysis in Streamlit UI."""
        st.subheader("Profit Calculator")
        
        # Get market data from session state if available
        if 'market_data' in st.session_state:
            card_data['market_data'] = st.session_state.market_data
        
        # Common input fields for all scenarios at the top
        st.markdown("#### Cost Inputs")
        col1, col2 = st.columns(2)
        
        with col1:
            purchase_price = st.number_input(
                "Purchase Price ($)",
                min_value=0.0,
                value=0.0,
                step=1.0,
                key="purchase_price",
                help="The price you paid or plan to pay for the card"
            )
            shipping_cost = st.number_input(
                "Shipping Cost ($)",
                min_value=0.0,
                value=0.0,
                step=0.5,
                key="shipping_cost",
                help="Total shipping costs (both buying and selling)"
            )
        
        with col2:
            seller_fee_percentage = st.number_input(
                "Seller Fee (%)",
                min_value=0.0,
                max_value=100.0,
                value=0.0,  # Default to 0
                step=0.1,
                key="seller_fee",
                help="Platform selling fees (e.g., eBay typically charges 12.9% for cards)"
            )
            grading_service = st.selectbox(
                "Grading Service Level",
                options=['n/a', 'economy', 'regular', 'express', 'other'],
                index=0,  # Default to 'n/a'
                key="grading_service",
                help="Choose grading service level - affects both cost and turnaround time"
            )
            
            # Add custom grading cost input if 'other' is selected
            if grading_service == 'other':
                custom_grading_cost = st.number_input(
                    "Custom Grading Cost ($)",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    key="custom_grading_cost",
                    help="Enter your custom grading service cost"
                )
                # Update grading params with custom cost
                self.grading_params['grading_costs']['other'] = custom_grading_cost

        # Update card data with user inputs
        card_data.update({
            'price': purchase_price,
            'shipping_cost': shipping_cost,
            'seller_fee_percentage': seller_fee_percentage,
            'grading_service': grading_service
        })
        
        # Create tabs for different scenarios
        tab1, tab2, tab3 = st.tabs(["Raw Card", "PSA 9", "PSA 10"])
        
        with tab1:
            self._display_scenario_metrics("Raw", card_data)
        
        with tab2:
            self._display_scenario_metrics("PSA 9", card_data)
        
        with tab3:
            self._display_scenario_metrics("PSA 10", card_data)
            
        # Add recommendations section after all tabs
        st.markdown("---")  # Visual separator
        
        # Debug information
        st.write("Debug: Checking market data availability")
        if card_data is None:
            st.warning("Debug: card_data is None")
        else:
            st.write(f"Debug: card_data keys: {list(card_data.keys())}")
            
        if card_data and 'market_data' in card_data:
            st.write("Debug: Market data found, generating recommendations...")
            current_scenario = "Raw"  # Default to Raw scenario
            current_profit_data = self.calculate_profits(card_data, current_scenario)
            
            try:
                self.recommendation_engine.display_recommendations(
                    card_data=card_data,
                    market_data=card_data['market_data'],
                    profit_data=current_profit_data
                )
            except Exception as e:
                st.error(f"Debug: Error in recommendations: {str(e)}")
        else:
            st.info("Debug: Market data not available yet. Please complete a card search to see recommendations.")

    def _display_scenario_metrics(self, scenario: str, card_data: Dict[str, Any]) -> None:
        """Display metrics for a specific scenario."""
        results = self.calculate_profits(card_data, scenario)
        
        # Display market value and costs
        st.markdown("#### Market Value")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Market Price",
                f"${results['market_price']:.2f}",
                help=f"Based on {results['price_source']} data from {results['sales_count']} sales"
            )
            st.metric(
                "Break-Even Price",
                f"${results['break_even_price']:.2f}",
                help="Minimum selling price needed to recover all costs"
            )
        
        with col2:
            st.metric(
                "Base Costs",
                f"${results['base_costs']:.2f}",
                help="Sum of purchase price, shipping, and grading costs"
            )
            st.metric(
                "Seller Fees",
                f"${results['seller_fee_amount']:.2f}",
                help=f"Platform fees ({results['seller_fee']}% of sale price)"
            )
        
        # Display profit metrics
        st.markdown("#### Profit Analysis")
        col3, col4 = st.columns(2)
        
        with col3:
            st.metric(
                "Net Profit",
                f"${results['net_profit']:.2f}",
                help="Expected profit after all costs and fees"
            )
            if scenario != "Raw":
                st.metric(
                    "Success Probability",
                    f"{results['success_probability']:.1f}%",
                    help=f"Chance of achieving {scenario} grade"
                )
        
        with col4:
            st.metric(
                "ROI",
                f"{results['roi']:.1f}%",
                help="Return on Investment percentage"
            )
            if scenario != "Raw":
                st.metric(
                    "Lower Grade Risk",
                    f"{results['lower_grade_probability']:.1f}%",
                    help="Probability of receiving a lower grade"
                )
        
        # Display timeline and risk
        st.markdown("#### Timeline & Risk")
        st.info(
            f"⏱️ **Timeline:** {results['timeline']}\n\n"
            f"⚠️ **Risk Level:** {results['risk_level']}"
        )
        
        # Show recent sales if available
        if results.get('recent_sales'):
            with st.expander("Recent Sales History"):
                for sale in results['recent_sales'][:5]:  # Show last 5 sales
                    st.write(
                        f"${sale['price']:.2f} - "
                        f"Sold on {sale.get('date', 'N/A')}"
                    )

    def calculate_return(self, purchase_price: float, current_price: float, holding_period: int,
                        shipping_cost: float, seller_fee: float, market_trend: float = 0.5) -> float:
        """Calculate return on investment for a card.
        
        Args:
            purchase_price: Initial purchase price
            current_price: Current market price
            holding_period: Number of months holding the card
            shipping_cost: Cost of shipping
            seller_fee: Percentage fee for selling (e.g., 12.9 for eBay)
            market_trend: Market trend factor (0-1, where 0.5 is neutral)
            
        Returns:
            float: Return on investment percentage
        """
        # Calculate total costs
        seller_fee_amount = current_price * (seller_fee / 100)
        total_costs = purchase_price + shipping_cost + seller_fee_amount
        
        # Calculate base profit
        base_profit = current_price - total_costs
        
        # Adjust profit based on market trend
        trend_factor = (market_trend - 0.5) * 2  # Convert to -1 to 1 range
        adjusted_profit = base_profit * (1 + trend_factor * 0.1)  # 10% max adjustment
        
        # Calculate ROI
        roi = (adjusted_profit / purchase_price * 100) if purchase_price > 0 else 0
        
        return roi