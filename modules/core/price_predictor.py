import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import requests
from bs4 import BeautifulSoup
import xgboost as xgb
from textblob import TextBlob
import re

from scrapers.ebay_interface import EbayInterface

class PricePredictor:
    def __init__(self):
        # Initialize multiple models for ensemble prediction
        self.rf_model = RandomForestRegressor(n_estimators=200, random_state=42)
        self.gb_model = GradientBoostingRegressor(n_estimators=200, random_state=42)
        self.xgb_model = xgb.XGBRegressor(n_estimators=200, random_state=42)
        self.scaler = StandardScaler()
        
        # Enhanced seasonal factors with more granular data
        self.seasonal_factors = {
            # Monthly seasonal factors based on historical card market data
            1: 1.02,  # January (post-holiday boost)
            2: 0.98,  # February
            3: 1.05,  # March (start of season)
            4: 1.08,  # April (early season)
            5: 1.02,  # May
            6: 0.98,  # June
            7: 0.95,  # July
            8: 0.92,  # August
            9: 1.10,  # September (NFL season start)
            10: 1.08, # October
            11: 1.05, # November
            12: 1.12  # December (holiday season)
        }
        
        # Weekly seasonal factors
        self.weekly_factors = {
            0: 1.05,  # Monday
            1: 1.02,  # Tuesday
            2: 1.00,  # Wednesday
            3: 0.98,  # Thursday
            4: 0.95,  # Friday
            5: 1.10,  # Saturday
            6: 1.15   # Sunday
        }
        
        # Grade multipliers based on market data
        self.grade_multipliers = {
            'PSA 10': 2.5,  # Updated based on market data
            'PSA 9': 1.8,   # Updated based on market data
            'PSA 8': 1.4,
            'Raw': 1.0
        }
        
    def get_player_stats(self, player_name):
        """Fetch current player statistics and performance metrics"""
        try:
            # This would typically connect to a sports stats API
            # For now, using example data for Jordan Love
            stats = {
                'jordan love': {
                    'games_played': 17,
                    'passing_yards': 4159,
                    'touchdowns': 32,
                    'qb_rating': 92.4,
                    'team_success': 0.85,  # Team's win rate
                    'market_sentiment': 0.8,  # Based on media coverage and fan interest
                    'recent_performance': 0.9,  # Last 3 games performance
                    'injury_status': 1.0,  # 1.0 = healthy, 0.0 = injured
                    'contract_status': 1.0,  # 1.0 = stable, 0.0 = uncertain
                    'team_playoffs': 1.0  # 1.0 = in playoffs, 0.0 = eliminated
                }
            }
            return stats.get(player_name.lower(), {})
        except Exception as e:
            print(f"Error fetching player stats: {e}")
            return {}

    def get_historical_sales(self, card_info):
        """Fetch historical sales data for similar cards"""
        try:
            # This would typically connect to a card sales database
            # For now, using example historical data
            base_price = np.mean([card['price'] for card in card_info])
            historical_trend = [
                base_price * factor for factor in [
                    0.8, 0.85, 0.9, 1.0, 1.1, 1.2, 1.15, 1.1,
                    1.05, 1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7,
                    0.75, 0.8, 0.85, 0.9, 1.0, 1.1, 1.2, 1.3
                ]
            ]
            return historical_trend
        except Exception as e:
            print(f"Error fetching historical sales: {e}")
            return []

    def analyze_card_condition(self, card_data):
        """Analyze card condition and its impact on price"""
        condition_multipliers = {
            'PSA 10': 1.8,  # More realistic multiplier
            'PSA 9': 1.3,   # More realistic multiplier
            'PSA 8': 1.1,
            'Raw': 1.0
        }
        
        # Extract condition from title or use default
        condition = 'Raw'
        for grade in condition_multipliers.keys():
            if any(grade.lower() in card['title'].lower() for card in card_data):
                condition = grade
                break
                
        return condition, condition_multipliers[condition]

    def calculate_market_factors(self, player_stats):
        """Calculate market influence factors with more conservative scaling"""
        if not player_stats:
            return 1.0
            
        performance_score = min(max((
            (player_stats.get('passing_yards', 0) / 5000) * 0.25 +  # More conservative scaling
            (player_stats.get('touchdowns', 0) / 35) * 0.25 +      # More conservative scaling
            (player_stats.get('qb_rating', 0) / 110) * 0.2 +       # More conservative scaling
            player_stats.get('team_success', 0.5) * 0.15 +         # Slightly increased weight
            player_stats.get('market_sentiment', 0.5) * 0.15       # Slightly increased weight
        ), 0.8), 1.5)  # More conservative limits
        
        return performance_score

    def analyze_market_sentiment(self, card_data):
        """Analyze market sentiment from card titles and descriptions"""
        try:
            # Extract text from card titles
            titles = [card.get('title', '') for card in card_data]
            
            # Calculate sentiment scores
            sentiment_scores = []
            for title in titles:
                # Clean the title
                clean_title = re.sub(r'[^\w\s]', ' ', title.lower())
                # Calculate sentiment
                sentiment = TextBlob(clean_title).sentiment.polarity
                sentiment_scores.append(sentiment)
            
            # Calculate average sentiment
            avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0
            
            # Normalize sentiment to 0-1 range
            normalized_sentiment = (avg_sentiment + 1) / 2
            
            return normalized_sentiment
        except Exception as e:
            print(f"Error analyzing market sentiment: {e}")
            return 0.5  # Neutral sentiment as fallback

    def prepare_data(self, card_data):
        """Prepare the data for prediction by creating comprehensive features"""
        try:
            print(f"Preparing data for {len(card_data)} cards")
            
            # Create DataFrame from card data
            df = pd.DataFrame(card_data)
            print(f"DataFrame columns: {df.columns.tolist()}")
            
            # Ensure required columns exist
            required_columns = ['title', 'price', 'date']
            for col in required_columns:
                if col not in df.columns:
                    print(f"Warning: Missing required column '{col}' in card data")
                    return None
            
            # Convert price to numeric, handling any errors
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            if df['price'].isna().any():
                print(f"Warning: {df['price'].isna().sum()} prices could not be converted to numeric values")
                df = df.dropna(subset=['price'])
            
            # Convert date to datetime, handling various formats
            try:
                df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
            except:
                try:
                    df['date'] = pd.to_datetime(df['date'])
                except:
                    print("Warning: Could not parse dates, using sequential dates")
                    df['date'] = pd.date_range(end=datetime.now(), periods=len(df))
            
            print(f"Number of valid data points after cleaning: {len(df)}")
            
            # Sort by date
            df = df.sort_values('date')
            
            # Add volume column if not present (default to 1)
            if 'volume' not in df.columns:
                df['volume'] = 1
            
            # Time-based features
            df['year'] = df['date'].dt.year
            df['month'] = df['date'].dt.month
            df['day_of_week'] = df['date'].dt.dayofweek
            df['day_of_month'] = df['date'].dt.day
            df['quarter'] = df['date'].dt.quarter
            
            # Seasonal features
            df['seasonal_factor'] = df['month'].map(self.seasonal_factors)
            df['weekly_factor'] = df['day_of_week'].map(self.weekly_factors)
            
            # Rolling statistics
            df['price_ma7'] = df['price'].rolling(window=7, min_periods=1).mean()
            df['price_ma30'] = df['price'].rolling(window=30, min_periods=1).mean()
            df['price_std7'] = df['price'].rolling(window=7, min_periods=1).std()
            df['price_std30'] = df['price'].rolling(window=30, min_periods=1).std()
            
            # Price momentum
            df['price_momentum'] = (df['price'] - df['price_ma7']) / df['price_ma7']
            df['price_volatility'] = df['price_std7'] / df['price_ma7']
            
            # Volume features
            df['volume_ma7'] = df['volume'].rolling(window=7, min_periods=1).mean()
            df['volume_ma30'] = df['volume'].rolling(window=30, min_periods=1).mean()
            
            # Lag features
            df['price_lag1'] = df['price'].shift(1)
            df['price_lag7'] = df['price'].shift(7)
            df['price_lag30'] = df['price'].shift(30)
            
            # Forward features (for training)
            df['price_forward7'] = df['price'].shift(-7)
            df['price_forward30'] = df['price'].shift(-30)
            
            # Fill NaN values
            df = df.fillna(method='ffill').fillna(method='bfill')
            
            # Verify we have enough data
            if len(df) < 7:
                print(f"Warning: Not enough data points for reliable prediction. Got {len(df)}, need at least 7.")
                return None
                
            print("Data preparation successful")
            return df
            
        except Exception as e:
            print(f"Error preparing data: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_graded_sales_data(self, card_data):
        """Fetch and analyze sales data for different grades (Raw, PSA 9, PSA 10)"""
        try:
            # Get the base search parameters from the first card
            base_card = card_data[0]
            title_parts = base_card['title'].split()
            
            # Extract player name and card details
            player_name = ' '.join(title_parts[0:2])  # First two words are usually player name
            year = next((part for part in title_parts if part.isdigit() and len(part) == 4), None)
            card_set = next((part for part in title_parts if part in ['Donruss', 'Prizm', 'Select', 'Mosaic']), None)
            card_number = next((part.replace('#', '') for part in title_parts if '#' in part), None)
            
            if not all([player_name, year, card_set, card_number]):
                return None
            
            # Create search queries for each grade
            grades = ['Raw', 'PSA 9', 'PSA 10']
            grade_data = {}
            
            for grade in grades:
                # Build search query
                if grade == 'Raw':
                    query = f"{year} {player_name} {card_set} #{card_number} -PSA -SGC -BGS"
                else:
                    query = f"{year} {player_name} {card_set} #{card_number} {grade}"
                
                # Search for sales
                scraper = EbayInterface()
                results = scraper.search_cards(
                    player_name=player_name,
                    year=year,
                    card_set=card_set,
                    card_number=card_number,
                    variation='',
                    scenario=grade,
                    negative_keywords=''
                )
                
                if results:
                    # Calculate median price for this grade
                    prices = [float(card['price']) for card in results]
                    median_price = np.median(prices)
                    grade_data[grade] = {
                        'median_price': median_price,
                        'sales_count': len(results),
                        'recent_sales': results[:5]  # Keep the 5 most recent sales
                    }
            
            return grade_data
        except Exception as e:
            print(f"Error fetching graded sales data: {e}")
            return None

    def prepare_features(self, df):
        """Prepare features for prediction"""
        # Ensure all required columns exist
        required_columns = [
            'price_ma7', 'price_ma30', 'price_std7', 'price_std30',
            'price_momentum', 'price_volatility', 'volume_ma7', 'volume_ma30',
            'price_lag1', 'price_lag7', 'price_lag30',
            'seasonal_factor', 'weekly_factor'
        ]
        
        # If any required columns are missing, create them
        for col in required_columns:
            if col not in df.columns:
                if col == 'price_ma7':
                    df['price_ma7'] = df['price'].rolling(window=7, min_periods=1).mean()
                elif col == 'price_ma30':
                    df['price_ma30'] = df['price'].rolling(window=30, min_periods=1).mean()
                elif col == 'price_std7':
                    df['price_std7'] = df['price'].rolling(window=7, min_periods=1).std()
                elif col == 'price_std30':
                    df['price_std30'] = df['price'].rolling(window=30, min_periods=1).std()
                elif col == 'price_momentum':
                    df['price_momentum'] = (df['price'] - df['price_ma7']) / df['price_ma7']
                elif col == 'price_volatility':
                    df['price_volatility'] = df['price_std7'] / df['price_ma7']
                elif col == 'volume_ma7':
                    df['volume_ma7'] = df['volume'].rolling(window=7, min_periods=1).mean()
                elif col == 'volume_ma30':
                    df['volume_ma30'] = df['volume'].rolling(window=30, min_periods=1).mean()
                elif col == 'price_lag1':
                    df['price_lag1'] = df['price'].shift(1)
                elif col == 'price_lag7':
                    df['price_lag7'] = df['price'].shift(7)
                elif col == 'price_lag30':
                    df['price_lag30'] = df['price'].shift(30)
                elif col == 'seasonal_factor':
                    df['seasonal_factor'] = df['month'].map(self.seasonal_factors)
                elif col == 'weekly_factor':
                    df['weekly_factor'] = df['day_of_week'].map(self.weekly_factors)
        
        # Fill any remaining NaN values
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        return df

    def train_models(self, df):
        """Train multiple models for ensemble prediction"""
        try:
            # Prepare features
            feature_cols = [
                'price_ma7', 'price_ma30', 'price_std7', 'price_std30',
                'price_momentum', 'price_volatility', 'volume_ma7', 'volume_ma30',
                'price_lag1', 'price_lag7', 'price_lag30',
                'seasonal_factor', 'weekly_factor'
            ]
            
            X = df[feature_cols]
            y = df['price']
            
            # Split data with more recent data in test set
            split_idx = int(len(df) * 0.8)
            X_train = X.iloc[:split_idx]
            X_test = X.iloc[split_idx:]
            y_train = y.iloc[:split_idx]
            y_test = y.iloc[split_idx:]
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train models with more trees and better parameters
            self.rf_model = RandomForestRegressor(
                n_estimators=500,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            )
            
            self.gb_model = GradientBoostingRegressor(
                n_estimators=500,
                learning_rate=0.01,
                max_depth=5,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            )
            
            self.xgb_model = xgb.XGBRegressor(
                n_estimators=500,
                learning_rate=0.01,
                max_depth=5,
                min_child_weight=2,
                random_state=42
            )
            
            # Train models
            self.rf_model.fit(X_train_scaled, y_train)
            self.gb_model.fit(X_train_scaled, y_train)
            self.xgb_model.fit(X_train_scaled, y_train)
            
            # Calculate model performance
            rf_pred = self.rf_model.predict(X_test_scaled)
            gb_pred = self.gb_model.predict(X_test_scaled)
            xgb_pred = self.xgb_model.predict(X_test_scaled)
            
            # Calculate model weights based on performance
            rf_score = r2_score(y_test, rf_pred)
            gb_score = r2_score(y_test, gb_pred)
            xgb_score = r2_score(y_test, xgb_pred)
            
            # Add small epsilon to avoid division by zero
            epsilon = 1e-10
            total_score = rf_score + gb_score + xgb_score + epsilon
            
            self.model_weights = {
                'rf': rf_score / total_score,
                'gb': gb_score / total_score,
                'xgb': xgb_score / total_score
            }
            
            return self.model_weights
            
        except Exception as e:
            print(f"Error in train_models: {e}")
            import traceback
            traceback.print_exc()
            return {'rf': 0.33, 'gb': 0.33, 'xgb': 0.34}  # Default weights

    def predict_future_prices(self, card_data, days_ahead=90):
        """Predict future prices using ensemble of models"""
        try:
            # Limit days_ahead to 365 (12 months)
            days_ahead = min(days_ahead, 365)
            
            # Prepare data
            df = self.prepare_data(card_data)
            
            # Get current price and basic metrics
            current_price = float(card_data[-1]['price']) if card_data else 0
            if df is None:
                # If we can't prepare data, use simple trend-based prediction
                df = pd.DataFrame(card_data)
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                df = df.sort_values('date')
                
                # Calculate basic trend
                if len(df) > 1:
                    price_trend = (df['price'].iloc[-1] - df['price'].iloc[0]) / df['price'].iloc[0]
                else:
                    price_trend = 0
                
                # Generate simple predictions
                future_dates = [df['date'].max() + timedelta(days=i+1) for i in range(days_ahead)]
                predicted_prices = []
                
                for i in range(days_ahead):
                    # Simple linear projection with reduced confidence
                    price = current_price * (1 + price_trend * (i + 1) / 365)
                    # Apply conservative bounds
                    price = max(min(price, current_price * 1.3), current_price * 0.7)
                    predicted_prices.append(price)
                
                # Calculate confidence based on data quality
                data_confidence = min((len(card_data) / 30), 1) * 4  # Up to 4 points for data quantity
                trend_confidence = min(abs(price_trend) * 2, 1) * 3  # Up to 3 points for trend strength
                market_confidence = 3  # Base market confidence
                
                # Combine confidence scores
                prediction_confidence = min(
                    data_confidence + trend_confidence + market_confidence,
                    10
                )
                
                return {
                    'current_price': current_price,
                    'predicted_prices': list(zip(future_dates, predicted_prices)),
                    'confidence_score': prediction_confidence,
                    'price_volatility': 0,
                    'price_trend': price_trend * 100,
                    'market_factor': 1.0,
                    'sentiment_factor': 0.5,
                    'recommendations': {
                        'short_term': self._generate_recommendation(current_price, predicted_prices[29], 1.0),
                        'long_term': self._generate_recommendation(current_price, predicted_prices[-1], 1.0)
                    },
                    'metrics': {
                        '30_day_forecast': predicted_prices[29],
                        '90_day_forecast': predicted_prices[-1],
                        'potential_30_day_return': ((predicted_prices[29] - current_price) / current_price) * 100,
                        'potential_90_day_return': ((predicted_prices[-1] - current_price) / current_price) * 100
                    }
                }
            
            # Get player name and stats
            player_name = card_data[0]['title'].split()[0:2]
            player_name = ' '.join(player_name)
            player_stats = self.get_player_stats(player_name)
            
            # Analyze market sentiment
            market_sentiment = self.analyze_market_sentiment(card_data)
            
            # Train models
            model_weights = self.train_models(df)
            
            # Generate future dates
            future_dates = [df['date'].max() + timedelta(days=i+1) for i in range(days_ahead)]
            
            # Prepare future features
            future_df = pd.DataFrame({'date': future_dates})
            future_df = self.prepare_features(future_df)
            
            # Get feature columns
            feature_cols = [
                'price_ma7', 'price_ma30', 'price_std7', 'price_std30',
                'price_momentum', 'price_volatility', 'volume_ma7', 'volume_ma30',
                'price_lag1', 'price_lag7', 'price_lag30',
                'seasonal_factor', 'weekly_factor'
            ]
            
            # Scale features
            future_features = self.scaler.transform(future_df[feature_cols])
            
            # Get predictions from each model
            rf_pred = self.rf_model.predict(future_features)
            gb_pred = self.gb_model.predict(future_features)
            xgb_pred = self.xgb_model.predict(future_features)
            
            # Combine predictions using model weights
            ensemble_pred = (
                rf_pred * model_weights['rf'] +
                gb_pred * model_weights['gb'] +
                xgb_pred * model_weights['xgb']
            )
            
            # Apply market factors
            market_factor = self.calculate_market_factors(player_stats)
            sentiment_factor = 1 + (market_sentiment - 0.5) * 0.2  # ±10% impact from sentiment
            
            # Calculate final predictions with all factors
            predicted_prices = []
            for i, pred in enumerate(ensemble_pred):
                # Base prediction
                price = pred
                
                # Apply market and sentiment factors
                price *= market_factor * sentiment_factor
                
                # Apply seasonal factors
                seasonal_factor = self.seasonal_factors[future_dates[i].month]
                weekly_factor = self.weekly_factors[future_dates[i].weekday()]
                price *= seasonal_factor * weekly_factor
                
                # Add reduced volatility
                volatility = np.random.normal(0, df['price_std30'].iloc[-1] * 0.05)
                price += volatility
                
                # Apply conservative bounds
                current_price = df['price'].iloc[-1]
                price = max(min(price, current_price * 1.5), current_price * 0.7)
                
                predicted_prices.append(price)
            
            # Calculate confidence metrics
            data_confidence = min((len(card_data) / 30), 1) * 4  # Up to 4 points for data quantity
            market_confidence = min(market_factor, 1) * 3  # Up to 3 points for market strength
            sentiment_confidence = min(market_sentiment * 2, 1) * 3  # Up to 3 points for sentiment
            
            # Model confidence based on R² scores
            model_confidence = sum(model_weights.values()) * 3  # Up to 3 points for model performance
            
            # Combine confidence scores
            prediction_confidence = min(
                data_confidence + market_confidence + sentiment_confidence + model_confidence,
                10
            )
            
            # Calculate market indicators
            price_volatility = (df['price_std30'].iloc[-1] / df['price_ma30'].iloc[-1]) * 100
            price_trend = ((df['price'].iloc[-1] - df['price'].iloc[0]) / df['price'].iloc[0]) * 100
            
            # Generate recommendations
            future_price_30d = predicted_prices[29]
            future_price_90d = predicted_prices[-1]
            current_price = df['price'].iloc[-1]
            
            recommendations = {
                'short_term': self._generate_recommendation(current_price, future_price_30d, market_factor),
                'long_term': self._generate_recommendation(current_price, future_price_90d, market_factor)
            }
            
            return {
                'current_price': current_price,
                'predicted_prices': list(zip(future_dates, predicted_prices)),
                'confidence_score': prediction_confidence,
                'price_volatility': price_volatility,
                'price_trend': price_trend,
                'market_factor': market_factor,
                'sentiment_factor': sentiment_factor,
                'recommendations': recommendations,
                'metrics': {
                    '30_day_forecast': future_price_30d,
                    '90_day_forecast': future_price_90d,
                    'potential_30_day_return': ((future_price_30d - current_price) / current_price) * 100,
                    'potential_90_day_return': ((future_price_90d - current_price) / current_price) * 100
                }
            }
            
        except Exception as e:
            print(f"Error in predict_future_prices: {e}")
            # Return a basic prediction even in case of error
            current_price = float(card_data[-1]['price']) if card_data else 0
            future_dates = [datetime.now() + timedelta(days=i+1) for i in range(days_ahead)]
            predicted_prices = [current_price * 1.1 for _ in range(days_ahead)]  # Simple 10% increase
            
            return {
                'current_price': current_price,
                'predicted_prices': list(zip(future_dates, predicted_prices)),
                'confidence_score': 3.0,  # Low confidence for error case
                'price_volatility': 0,
                'price_trend': 0,
                'market_factor': 1.0,
                'sentiment_factor': 0.5,
                'recommendations': {
                    'short_term': 'Hold',
                    'long_term': 'Hold'
                },
                'metrics': {
                    '30_day_forecast': predicted_prices[29],
                    '90_day_forecast': predicted_prices[-1],
                    'potential_30_day_return': 10,
                    'potential_90_day_return': 10
                }
            }
    
    def _generate_recommendation(self, current_price, future_price, market_factor):
        """Generate buy/sell recommendations based on comprehensive analysis"""
        price_change_pct = ((future_price - current_price) / current_price) * 100
        
        # Adjust thresholds based on market factor
        buy_threshold = 15 / market_factor  # Higher market factor = lower threshold needed
        strong_buy_threshold = 25 / market_factor
        
        if price_change_pct > strong_buy_threshold and market_factor > 1.1:
            return "Strong Buy"
        elif price_change_pct > buy_threshold:
            return "Buy"
        elif price_change_pct < -strong_buy_threshold and market_factor < 0.9:
            return "Strong Sell"
        elif price_change_pct < -buy_threshold:
            return "Sell"
        else:
            return "Hold" 