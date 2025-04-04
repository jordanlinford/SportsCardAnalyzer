import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sklearn import metrics
from sklearn.linear_model import LinearRegression
from scipy import stats

class MarketAnalyzer:
    def __init__(self):
        self.price_history = []
        self.market_metrics = {}
        
    def analyze_market_data(self, card_data):
        """Analyze market data for a list of card sales"""
        try:
            # Convert card data to DataFrame
            df = pd.DataFrame(card_data)
            
            # Ensure price is numeric
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            df = df.dropna(subset=['price'])
            
            # Convert date to datetime
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df = df.dropna(subset=['date'])
            
            # Sort by date
            df = df.sort_values('date')
            
            # Calculate basic metrics
            median_price = df['price'].median()
            avg_price = df['price'].mean()
            price_range = {
                'min': df['price'].min(),
                'max': df['price'].max()
            }
            
            # Calculate volatility score
            if len(df) > 1:
                volatility_score = df['price'].std() / df['price'].mean() * 100
            else:
                volatility_score = 0
                
            # Calculate market health score (0-10)
            market_health_score = max(0, min(10, 10 - (volatility_score / 10)))
            
            # Calculate trend score using linear regression and R-squared value
            if len(df) > 1:
                # Convert dates to numeric values (days since first sale)
                first_date = df['date'].min()
                df['days_since_first'] = (df['date'] - first_date).dt.days
                
                # Perform linear regression
                x = df['days_since_first'].values
                y = df['price'].values
                slope, intercept = np.polyfit(x, y, 1)
                
                # Calculate R-squared value
                y_pred = slope * x + intercept
                r_squared = 1 - np.sum((y - y_pred) ** 2) / np.sum((y - np.mean(y)) ** 2)
                
                # Calculate trend strength (0-10)
                trend_direction = 1 if slope > 0 else -1
                trend_strength = abs(slope) / df['price'].mean() * 100
                trend_score = max(0, min(10, 5 + (trend_direction * trend_strength * r_squared)))
            else:
                trend_score = 5
                
            # Calculate liquidity score based on average days between sales
            date_diffs = df['date'].diff().dt.days
            avg_days_between_sales = date_diffs.mean() if not date_diffs.empty else 30
            liquidity_score = max(0, min(10, 10 - (avg_days_between_sales / 30)))
            
            # Return market data dictionary
            return {
                'median_price': median_price,
                'avg_price': avg_price,
                'price_range': price_range,
                'volatility_score': volatility_score,
                'market_health_score': market_health_score,
                'trend_score': trend_score,
                'liquidity_score': liquidity_score,
                'total_sales': len(df)
            }
            
        except Exception as e:
            print(f"Error in analyze_market_data: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _calculate_volatility_score(self, prices: np.ndarray) -> float:
        """Calculate price volatility score (1-10)"""
        if len(prices) < 2:
            return 5.0
        
        std_dev = np.std(prices)
        mean_price = np.mean(prices)
        
        # Normalize volatility score (1-10)
        volatility = min(10, max(1, (std_dev / mean_price) * 20))
        return round(volatility, 1)
    
    def _calculate_trend_score(self, df: pd.DataFrame) -> float:
        """Calculate trend score (1-10) based on price and volume trends"""
        if len(df) < 2:
            return 5.0
        
        # Calculate price trend
        price_slope = np.polyfit(range(len(df)), df['price'], 1)[0]
        price_trend = 1 if price_slope > 0 else -1
        
        # Calculate volume trend
        volume_slope = np.polyfit(range(len(df)), df['volume'], 1)[0]
        volume_trend = 1 if volume_slope > 0 else -1
        
        # Combine trends into score (1-10)
        trend_score = 5 + (price_trend + volume_trend) * 2.5
        return round(min(10, max(1, trend_score)), 1)
    
    def _calculate_liquidity_score(self, df: pd.DataFrame) -> float:
        """Calculate liquidity score (1-10) based on sales frequency"""
        if len(df) < 2:
            return 5.0
        
        # Calculate average days between sales if dates are available
        if 'date' in df.columns and df['date'].notna().any():
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df = df.sort_values('date')
            days_between_sales = df['date'].diff().dt.days.mean()
            
            if pd.isna(days_between_sales):
                return 5.0
            
            # Convert to liquidity score (1-10)
            liquidity = 10 - min(9, int(days_between_sales / 10))
            return max(1, liquidity)
        
        # If no dates, use number of sales as proxy
        return min(10, max(1, len(df) / 10))
    
    def _calculate_market_health_score(self, df: pd.DataFrame) -> float:
        """Calculate overall market health score (1-10)"""
        volatility = self._calculate_volatility_score(df['price'].values)
        trend = self._calculate_trend_score(df)
        liquidity = self._calculate_liquidity_score(df)
        
        # Weight the components
        weights = {
            'volatility': 0.3,
            'trend': 0.4,
            'liquidity': 0.3
        }
        
        # Invert volatility (lower is better)
        volatility_score = 11 - volatility
        
        # Calculate weighted average
        health_score = (
            weights['volatility'] * volatility_score +
            weights['trend'] * trend +
            weights['liquidity'] * liquidity
        )
        
        return round(min(10, max(1, health_score)), 1)
    
    def _analyze_price_segments(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze price segments and their characteristics"""
        if len(df) < 3:
            return {}
            
        # Create price segments
        df['price_segment'] = pd.qcut(df['price'], q=3, labels=['Low', 'Medium', 'High'])
        
        segments = {}
        for segment in ['Low', 'Medium', 'High']:
            segment_data = df[df['price_segment'] == segment]
            if len(segment_data) > 0:
                segments[segment] = {
                    'price_range': (
                        float(segment_data['price'].min()),
                        float(segment_data['price'].max())
                    ),
                    'average_price': float(segment_data['price'].mean()),
                    'sales_volume': len(segment_data),
                    'percentage_of_market': len(segment_data) / len(df) * 100
                }
        
        return segments

    @staticmethod
    def remove_outliers(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        """Remove outliers using IQR method with enhanced detection."""
        Q1 = df['price'].quantile(0.25)
        Q3 = df['price'].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # Enhanced outlier detection using z-score as well
        z_scores = stats.zscore(df['price'])
        z_score_mask = (abs(z_scores) < 3)
        
        # Combine both methods
        df_filtered = df[(df['price'] >= lower_bound) & 
                        (df['price'] <= upper_bound) &
                        z_score_mask]
        
        outliers_removed = len(df) - len(df_filtered)
        return df_filtered, outliers_removed

    @staticmethod
    def calculate_market_metrics(df_filtered: pd.DataFrame) -> Dict[str, float]:
        """Calculate enhanced market metrics from filtered data."""
        metrics = {
            'avg_price': df_filtered['price'].mean(),
            'std_price': df_filtered['price'].std(),
            'median_price': df_filtered['price'].median(),
            'low_price': df_filtered['price'].quantile(0.25),
            'high_price': df_filtered['price'].quantile(0.75),
            'volume_30d': len(df_filtered[df_filtered['date'] >= (pd.Timestamp.now() - pd.Timedelta(days=30))]),
            'volume_90d': len(df_filtered[df_filtered['date'] >= (pd.Timestamp.now() - pd.Timedelta(days=90))]),
            'price_momentum': 0.0,
            'volatility_index': 0.0
        }
        
        # Calculate enhanced price trend metrics
        recent_prices = df_filtered[
            df_filtered['date'] >= (pd.Timestamp.now() - pd.Timedelta(days=30))
        ]
        
        if not recent_prices.empty:
            # Calculate price momentum (rate of change)
            metrics['price_momentum'] = (
                recent_prices['price'].mean() - df_filtered['price'].mean()
            ) / df_filtered['price'].std()
            
            # Calculate volatility index (normalized standard deviation)
            metrics['volatility_index'] = recent_prices['price'].std() / recent_prices['price'].mean()
            
            # Calculate price trend
            metrics['price_trend'] = (
                recent_prices['price'].mean() - metrics['avg_price']
            ) / metrics['avg_price']
        
        return metrics

    def predict_future_price(self, df: pd.DataFrame, days_ahead: int = 30) -> Dict[str, float]:
        """Predict future price using multiple models."""
        if df.empty or len(df) < 10:
            return {
                'predicted_price': None,
                'confidence': 0.0,
                'prediction_range': (None, None)
            }

        # Prepare data for prediction
        df['days_from_start'] = (df['date'] - df['date'].min()).dt.days
        X = df['days_from_start'].values.reshape(-1, 1)
        y = df['price'].values

        # Fit linear regression
        model = LinearRegression()
        model.fit(X, y)

        # Calculate prediction interval
        y_pred = model.predict(X)
        std_err = np.sqrt(np.sum((y - y_pred) ** 2) / (len(y) - 2))
        
        # Predict future price
        future_x = np.array([[X[-1][0] + days_ahead]])
        predicted_price = model.predict(future_x)[0]
        
        # Calculate confidence interval
        confidence_interval = stats.t.interval(
            alpha=0.95,
            df=len(y)-2,
            loc=predicted_price,
            scale=std_err
        )

        # Calculate prediction confidence
        r2_score = model.score(X, y)
        confidence = min(max(r2_score * (1 - metrics['volatility_index']), 0), 1)

        return {
            'predicted_price': predicted_price,
            'confidence': confidence,
            'prediction_range': confidence_interval
        }

    @staticmethod
    def calculate_market_scores(metrics: Dict[str, float], df_filtered: pd.DataFrame) -> Dict[str, float]:
        """Calculate enhanced market analysis scores."""
        # Base scores
        trend_score = max(1, min(10, 5 + (metrics['price_trend'] * 50)))
        volatility_score = max(1, min(10, (metrics['std_price'] / metrics['avg_price']) * 10))
        liquidity_score = min(10, len(df_filtered) / 5)  # Adjusted for better scaling
        
        # Enhanced scores
        momentum_score = max(1, min(10, 5 + metrics['price_momentum'] * 2))
        stability_score = max(1, min(10, 10 - metrics['volatility_index'] * 5))
        volume_score = min(10, metrics['volume_30d'] / 10)
        
        return {
            'trend_score': trend_score,
            'volatility_score': volatility_score,
            'liquidity_score': liquidity_score,
            'momentum_score': momentum_score,
            'stability_score': stability_score,
            'volume_score': volume_score
        }

    def analyze_sales_data(self, sales_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Enhanced analysis function with comprehensive market insights."""
        if not sales_data:
            return None

        # Create DataFrame
        df = pd.DataFrame([{
            'date': item['date'],
            'price': item['price'],
            'condition': item.get('condition', 'unknown'),
            'title': item.get('title', '')
        } for item in sales_data if item.get('date')])

        if df.empty:
            return None

        # Convert dates and sort
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        # Remove outliers
        df_filtered, outliers_removed = self.remove_outliers(df)

        # Calculate all metrics
        metrics = self.calculate_market_metrics(df_filtered)
        scores = self.calculate_market_scores(metrics, df_filtered)
        grades = self.calculate_grades(scores)

        # Calculate price predictions
        predictions = self.predict_future_price(df_filtered)

        # Calculate market segments
        segments = self.analyze_market_segments(df_filtered)

        # Combine all results
        return {
            'metrics': metrics,
            'scores': scores,
            'grades': grades,
            'predictions': predictions,
            'segments': segments,
            'outliers_removed': outliers_removed,
            'total_sales': len(df),
            'filtered_sales': len(df_filtered),
            'filtered_data': df_filtered.to_dict('records')
        }

    def analyze_market_segments(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze different market segments (conditions, variations, etc.)"""
        segments = {
            'condition_analysis': {},
            'price_brackets': {},
            'temporal_analysis': {}
        }

        # Analyze by condition if available
        if 'condition' in df.columns:
            for condition in df['condition'].unique():
                condition_data = df[df['condition'] == condition]
                segments['condition_analysis'][condition] = {
                    'avg_price': condition_data['price'].mean(),
                    'volume': len(condition_data),
                    'trend': self.calculate_segment_trend(condition_data)
                }

        # Create price brackets
        price_ranges = pd.qcut(df['price'], q=4, labels=['Low', 'Medium-Low', 'Medium-High', 'High'])
        for label in price_ranges.unique():
            bracket_data = df[price_ranges == label]
            segments['price_brackets'][str(label)] = {
                'range': (bracket_data['price'].min(), bracket_data['price'].max()),
                'volume': len(bracket_data),
                'avg_price': bracket_data['price'].mean()
            }

        # Temporal analysis
        for period in [7, 30, 90]:
            recent_data = df[df['date'] >= (pd.Timestamp.now() - pd.Timedelta(days=period))]
            if not recent_data.empty:
                segments['temporal_analysis'][f'{period}d'] = {
                    'avg_price': recent_data['price'].mean(),
                    'volume': len(recent_data),
                    'price_change': (
                        recent_data['price'].mean() - df['price'].mean()
                    ) / df['price'].mean()
                }

        return segments

    @staticmethod
    def calculate_segment_trend(segment_df: pd.DataFrame) -> float:
        """Calculate trend for a market segment."""
        if len(segment_df) < 2:
            return 0.0

        segment_df = segment_df.sort_values('date')
        days_elapsed = (segment_df['date'].max() - segment_df['date'].min()).days
        if days_elapsed == 0:
            return 0.0

        price_change = (
            segment_df['price'].iloc[-1] - segment_df['price'].iloc[0]
        ) / segment_df['price'].iloc[0]

        return price_change / (days_elapsed / 30)  # Normalize to monthly rate

    @staticmethod
    def calculate_grades(scores: Dict[str, float]) -> Dict[str, str]:
        """Calculate buying and selling grades based on market scores."""
        buy_score = (
            (10 - scores['volatility_score']) * 0.3 +
            (10 - scores['trend_score']) * 0.4 +
            scores['liquidity_score'] * 0.3
        ) / 10

        sell_score = (
            scores['volatility_score'] * 0.3 +
            scores['trend_score'] * 0.4 +
            scores['liquidity_score'] * 0.3
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