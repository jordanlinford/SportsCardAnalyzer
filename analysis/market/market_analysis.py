import pandas as pd
import numpy as np
from typing import Dict, List, Any

class MarketAnalyzer:
    @staticmethod
    def remove_outliers(df: pd.DataFrame) -> pd.DataFrame:
        """Remove outliers using IQR method."""
        Q1 = df['price'].quantile(0.25)
        Q3 = df['price'].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        df_filtered = df[(df['price'] >= lower_bound) & (df['price'] <= upper_bound)]
        
        return df_filtered

    @staticmethod
    def calculate_market_metrics(df_filtered: pd.DataFrame) -> Dict[str, float]:
        """Calculate key market metrics from filtered data."""
        if df_filtered.empty:
            return {
                'avg_price': 0.0,
                'std_price': 0.0,
                'median_price': 0.0,
                'low_price': 0.0,
                'high_price': 0.0,
                'price_trend': 0.0
            }
            
        # Convert date to datetime if it's not already
        df_filtered['date'] = pd.to_datetime(df_filtered['date'])
        df_filtered = df_filtered.sort_values('date')
        
        # Calculate basic metrics
        metrics = {
            'avg_price': df_filtered['price'].mean(),
            'std_price': df_filtered['price'].std(),
            'median_price': df_filtered['price'].median(),
            'low_price': df_filtered['price'].min(),
            'high_price': df_filtered['price'].max()
        }
        
        # Calculate price trend over last 30 days
        recent_prices = df_filtered[
            df_filtered['date'] >= (pd.Timestamp.now() - pd.Timedelta(days=30))
        ]
        
        if not recent_prices.empty:
            old_prices = df_filtered[
                df_filtered['date'] < (pd.Timestamp.now() - pd.Timedelta(days=30))
            ]
            if not old_prices.empty:
                old_avg = old_prices['price'].mean()
                metrics['price_trend'] = (metrics['avg_price'] - old_avg) / old_avg
            else:
                metrics['price_trend'] = 0.0
        else:
            metrics['price_trend'] = 0.0
        
        return metrics

    @staticmethod
    def calculate_market_scores(metrics: Dict[str, float], df_filtered: pd.DataFrame) -> Dict[str, float]:
        """Calculate market analysis scores."""
        if df_filtered.empty:
            return {
                'trend': 5.0,
                'volatility': 5.0,
                'liquidity': 0.0
            }
            
        # Calculate trend score (0-10)
        trend_score = 5.0 + (metrics.get('price_trend', 0.0) * 5.0)  # Scale trend to reasonable range
        trend_score = max(0, min(10, trend_score))
        
        # Calculate volatility score (0-10)
        if metrics['avg_price'] > 0:
            volatility = metrics['std_price'] / metrics['avg_price']
            volatility_score = min(10, volatility * 10)
        else:
            volatility_score = 5.0
            
        # Calculate liquidity score (0-10)
        liquidity_score = min(10, len(df_filtered) / 10)  # Scale based on number of sales
        
        return {
            'trend': trend_score,
            'volatility': volatility_score,
            'liquidity': liquidity_score
        }

    @staticmethod
    def calculate_grades(scores: Dict[str, float]) -> Dict[str, str]:
        """Calculate buying and selling grades based on market scores."""
        # Calculate buy score (0-1)
        buy_score = (
            (10 - scores['volatility']) * 0.3 +  # Lower volatility is better for buying
            (10 - scores['trend']) * 0.4 +       # Lower trend is better for buying
            scores['liquidity'] * 0.3            # Higher liquidity is better
        ) / 10

        # Calculate sell score (0-1)
        sell_score = (
            scores['volatility'] * 0.3 +         # Higher volatility is better for selling
            scores['trend'] * 0.4 +              # Higher trend is better for selling
            scores['liquidity'] * 0.3            # Higher liquidity is better
        ) / 10

        def get_grade(score: float) -> str:
            if score >= 0.8: return 'A'
            if score >= 0.6: return 'B'
            if score >= 0.4: return 'C'
            return 'D'

        return {
            'buy_grade': get_grade(buy_score),
            'sell_grade': get_grade(sell_score)
        }

    def analyze_sales_data(self, sales_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sales data to generate market insights."""
        if not sales_data:
            return {}
            
        # Convert to DataFrame
        df = pd.DataFrame(sales_data)
        
        # Convert date to datetime and sort
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Extract card details
        df['player'] = df['title'].str.extract(r'([A-Za-z\s]+)(?:\s+\d{4}|\s+RC|\s+Rookie)')
        df['year'] = df['title'].str.extract(r'(\d{4})')
        df['set'] = df['title'].str.extract(r'(\d{4}\s+[A-Za-z\s]+)')
        df['card_number'] = df['title'].str.extract(r'#(\d+)')
        df['variation'] = df['title'].str.extract(r'(Pink|Blue|Green|Purple|Gold|Red|Orange|Yellow|White|Black|Silver|Bronze|Holo|Refractor|Wave|Prizm|Optic|Chrome|Select|Mosaic|Donruss|Topps|Bowman|Upper Deck|Fleer|Score|Stadium Club|Pro Set|Skybox|Hoops|Metal|Flair|SP|UD|Leaf|Pacific|Playoff|Press Pass|Sage|Hit|Inception|Contenders|Prestige|Absolute|Certified|Elite|Finest|Gridiron|Limited|Luminaries|Mosaic|Obsidian|Phoenix|Plates & Patches|Playbook|Prizm|Revolution|Select|Spectra|Status|Threads|Titanium|Unparalleled|Vanguard|Xr|Zenith)')
        
        # Identify graded cards and extract grades
        df['is_graded'] = df['title'].str.contains('PSA|BGS|SGC', case=False)
        grade_extract = df['title'].str.extract(r'(?i)(PSA|BGS|SGC)\s*(\d+)')
        df['grade'] = grade_extract[0] + ' ' + grade_extract[1]
        df['grade'] = df['grade'].fillna('Raw')
        df['grade'] = df['grade'].str.strip()
        
        # Convert price to float
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        
        # Group by card variation to analyze each variation separately
        variation_groups = df.groupby('variation')
        
        # Initialize results dictionary
        results = {
            'metrics': {},
            'scores': {},
            'grades': {},
            'variations': {}
        }
        
        # Analyze each variation
        for variation, group in variation_groups:
            if pd.isna(variation):
                continue
                
            variation_data = {
                'metrics': {},
                'scores': {},
                'grades': {}
            }
            
            # Calculate basic metrics for this variation
            variation_data['metrics'] = {
                'median_price': group['price'].median(),
                'avg_price': group['price'].mean(),
                'std_price': group['price'].std(),
                'low_price': group['price'].min(),
                'high_price': group['price'].max(),
                'total_sales': len(group),
                'has_graded_data': group['is_graded'].any()
            }
            
            # Calculate price trend over last 30 days
            recent_prices = group[
                group['date'] >= (pd.Timestamp.now() - pd.Timedelta(days=30))
            ]
            
            if not recent_prices.empty:
                old_prices = group[
                    group['date'] < (pd.Timestamp.now() - pd.Timedelta(days=30))
                ]
                if not old_prices.empty:
                    old_avg = old_prices['price'].mean()
                    variation_data['metrics']['price_trend'] = (variation_data['metrics']['avg_price'] - old_avg) / old_avg
                else:
                    variation_data['metrics']['price_trend'] = 0.0
            else:
                variation_data['metrics']['price_trend'] = 0.0
            
            # Calculate grade multipliers for this variation
            raw_cards = group[group['grade'] == 'Raw']
            psa9_cards = group[group['grade'] == 'PSA 9']
            psa10_cards = group[group['grade'] == 'PSA 10']
            
            if not raw_cards.empty:
                raw_median = raw_cards['price'].median()
                
                if not psa9_cards.empty:
                    variation_data['metrics']['psa9_multiplier'] = psa9_cards['price'].median() / raw_median
                if not psa10_cards.empty:
                    variation_data['metrics']['psa10_multiplier'] = psa10_cards['price'].median() / raw_median
            
            # Calculate market scores for this variation
            variation_data['scores'] = self.calculate_market_scores(variation_data['metrics'], group)
            
            # Calculate market grades for this variation
            variation_data['grades'] = self.calculate_grades(variation_data['scores'])
            
            # Store variation data
            results['variations'][variation] = variation_data
        
        # Calculate overall metrics using the most common variation
        most_common_variation = df['variation'].mode().iloc[0]
        results['metrics'] = results['variations'][most_common_variation]['metrics']
        results['scores'] = results['variations'][most_common_variation]['scores']
        results['grades'] = results['variations'][most_common_variation]['grades']
        
        return results

    def calculate_market_grades(self, scores: Dict[str, float]) -> Dict[str, str]:
        """Calculate market grades based on scores."""
        trend_score = scores['trend']
        volatility_score = scores['volatility']
        liquidity_score = scores['liquidity']
        
        # Calculate buy grade
        buy_score = (trend_score * 0.4 + (10 - volatility_score) * 0.3 + liquidity_score * 0.3) / 10
        if buy_score >= 0.8:
            buy_grade = 'A'
        elif buy_score >= 0.6:
            buy_grade = 'B'
        elif buy_score >= 0.4:
            buy_grade = 'C'
        else:
            buy_grade = 'D'
        
        # Calculate sell grade
        sell_score = (trend_score * 0.4 + volatility_score * 0.3 + liquidity_score * 0.3) / 10
        if sell_score >= 0.8:
            sell_grade = 'A'
        elif sell_score >= 0.6:
            sell_grade = 'B'
        elif sell_score >= 0.4:
            sell_grade = 'C'
        else:
            sell_grade = 'D'
        
        return {
            'buy_grade': buy_grade,
            'sell_grade': sell_grade
        } 