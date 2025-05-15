"""
Display Manager Module
Handles all display-related operations with consistent patterns and error handling.
"""

from modules.core.error_handler import handle_error, ValidationError
from config.environment import Environment
from config.feature_flags import is_feature_enabled
import streamlit as st
import logging
import time
import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)

class DisplayManager:
    """Manages display operations with consistent patterns"""
    
    @staticmethod
    def validate_collection(collection):
        """Validate collection data structure"""
        if not isinstance(collection, (list, pd.DataFrame)):
            raise ValidationError("Collection must be a list or DataFrame")
        if len(collection) == 0:
            logger.warning("Empty collection provided")
            return False
        return True
    
    @staticmethod
    def validate_card(card):
        """Validate card data structure"""
        if not isinstance(card, dict):
            raise ValidationError("Card must be a dictionary")
        required_fields = ['player_name', 'year', 'card_set']
        missing_fields = [field for field in required_fields if field not in card]
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        return True
    
    @staticmethod
    @handle_error
    def display_collection_grid(collection, on_card_click=None):
        """Display collection in a grid layout"""
        logger.info("Starting grid display")
        start_time = time.time()
        
        if not is_feature_enabled('basic_display'):
            logger.error("Basic display feature is disabled")
            raise ValidationError("Basic display feature is disabled")
            
        if not DisplayManager.validate_collection(collection):
            logger.info("No cards to display in grid")
            st.info("No cards to display")
            return
            
        # Get UI settings
        ui_settings = Environment.get_ui_settings()
        cards_per_row = ui_settings['cards_per_row']
        logger.info(f"Displaying grid with {cards_per_row} cards per row")
        
        # Custom CSS for consistent styling
        st.markdown("""
        <style>
            .card-container {
                position: relative;
                width: 100%;
                height: 200px;
                border-radius: 6px;
                overflow: hidden;
                transition: transform 0.2s ease-in-out;
                box-shadow: 0 1px 3px rgba(0,0,0,0.15);
                margin-bottom: 0.5rem;
                background: #f9f9f9;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .card-container:hover {
                transform: scale(1.02);
            }
            
            .card-image {
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
                padding: 5px;
            }
            
            .card-overlay {
                position: absolute;
                bottom: 0;
                width: 100%;
                background: rgba(0,0,0,0.75);
                color: #fff;
                font-size: 0.7rem;
                padding: 0.25rem;
                text-align: center;
                opacity: 0;
                transition: opacity 0.3s ease-in-out;
            }
            
            .card-container:hover .card-overlay {
                opacity: 1;
            }
            
            .action-button {
                background-color: #0056d2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 0.3rem 0.6rem;
                font-size: 0.75rem;
                cursor: pointer;
                width: 100%;
                margin-top: 0.25rem;
            }
            
            .action-button:hover {
                background-color: #0041a8;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Display cards in grid
        for i in range(0, len(collection), cards_per_row):
            row_cards = collection[i:i + cards_per_row]
            cols = st.columns(cards_per_row)
            
            for j, card in enumerate(row_cards):
                with cols[j]:
                    try:
                        # Validate card data
                        DisplayManager.validate_card(card)
                        
                        # Card display
                        st.markdown(f"""
                        <div class="card-container">
                            <img src="{card.get('photo', 'https://placehold.co/160x220?text=No+Image')}" 
                                 class="card-image" 
                                 onerror="this.src='https://placehold.co/160x220?text=No+Image';"/>
                            <div class="card-overlay">
                                <strong>{card.get('player_name', '')}</strong><br/>
                                {card.get('year', '')} {card.get('card_set', '')}<br/>
                                ${float(card.get('current_value', 0)):,.2f}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Action buttons
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            if st.button("Edit", key=f"edit_{i+j}"):
                                if on_card_click:
                                    on_card_click(i+j)
                        with col2:
                            if st.button("Delete", key=f"delete_{i+j}"):
                                st.session_state['delete_card_id'] = card.get('id')
                                st.session_state['delete_card_index'] = i+j
                    except Exception as e:
                        logger.error(f"Error displaying card {i+j}: {str(e)}")
                        st.error(f"Error displaying card: {str(e)}")
        
        logger.info(f"Grid display completed in {time.time() - start_time:.2f} seconds")
    
    @staticmethod
    @handle_error
    def display_collection_table(collection):
        """Display collection in a table format"""
        logger.info("Starting table display")
        start_time = time.time()
        
        if not DisplayManager.validate_collection(collection):
            logger.info("No cards to display in table")
            st.info("No cards to display")
            return
            
        try:
            # Convert collection to DataFrame for table display
            if not isinstance(collection, pd.DataFrame):
                df = pd.DataFrame(collection)
            else:
                df = collection.copy()
            
            logger.info(f"Converted {len(collection)} cards to DataFrame")
            
            # Select columns to display
            display_columns = [
                'player_name', 'year', 'card_set', 'card_number',
                'condition', 'current_value'
            ]
            
            # Filter and format DataFrame
            display_df = df[display_columns].copy()
            display_df['current_value'] = display_df['current_value'].apply(
                lambda x: f"${float(x):,.2f}" if x else "$0.00"
            )
            
            # Display table
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
        except Exception as e:
            logger.error(f"Error in table display: {str(e)}")
            st.error(f"Error displaying table: {str(e)}")
            raise
        
        logger.info(f"Table display completed in {time.time() - start_time:.2f} seconds")
    
    @staticmethod
    @handle_error
    def display_card_details(card):
        """Display detailed view of a single card"""
        logger.info("Starting card details display")
        start_time = time.time()
        
        if not card:
            logger.warning("No card data available for details view")
            st.warning("No card data available")
            return
            
        try:
            # Validate card data
            DisplayManager.validate_card(card)
            
            # Create two columns for layout
            col1, col2 = st.columns([1, 2])
            
            with col1:
                # Display card image
                st.image(
                    card.get('photo', 'https://placehold.co/300x400?text=No+Image'),
                    use_container_width=True
                )
            
            with col2:
                # Display card details
                st.subheader(card.get('player_name', 'Unknown Player'))
                st.write(f"**Year:** {card.get('year', 'N/A')}")
                st.write(f"**Set:** {card.get('card_set', 'N/A')}")
                st.write(f"**Card Number:** {card.get('card_number', 'N/A')}")
                st.write(f"**Condition:** {card.get('condition', 'N/A')}")
                st.write(f"**Current Value:** ${float(card.get('current_value', 0)):,.2f}")
                
                if card.get('notes'):
                    st.write("**Notes:**")
                    st.write(card.get('notes'))
                
                if card.get('tags'):
                    st.write("**Tags:**")
                    tag_cols = st.columns(4)
                    for i, tag in enumerate(card.get('tags', [])):
                        with tag_cols[i % 4]:
                            st.markdown(f"`{tag}`")
        except Exception as e:
            logger.error(f"Error in card details display: {str(e)}")
            st.error(f"Error displaying card details: {str(e)}")
            raise
        
        logger.info(f"Card details display completed in {time.time() - start_time:.2f} seconds")
    
    @staticmethod
    @handle_error
    def display_collection_stats(stats):
        """Display collection statistics"""
        logger.info("Starting stats display")
        start_time = time.time()
        
        if not stats:
            logger.info("No stats to display")
            return
            
        try:
            # Create metrics display
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Cards", stats['total_cards'])
            with col2:
                st.metric("Total Value", f"${stats['total_value']:,.2f}")
            with col3:
                st.metric("Unique Players", stats['unique_players'])
            with col4:
                st.metric("Unique Sets", stats['unique_sets'])
        except Exception as e:
            logger.error(f"Error in stats display: {str(e)}")
            st.error(f"Error displaying stats: {str(e)}")
            raise
        
        logger.info(f"Stats display completed in {time.time() - start_time:.2f} seconds") 