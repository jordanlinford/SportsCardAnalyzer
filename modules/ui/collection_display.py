import streamlit as st
import pandas as pd
from modules.ui.styles import get_collection_styles
from modules.database.service import DatabaseService
from datetime import datetime
import traceback
import base64
from typing import Optional
import requests

def display_collection_grid(filtered_collection, is_shared=False):
    """Display collection in a responsive grid layout"""
    if not has_cards(filtered_collection):
        st.info("No cards to display")
        return
    
    # Create a grid of cards
    cols = st.columns(3)
    for idx, card in enumerate(filtered_collection):
        col = cols[idx % 3]
        with col:
            with st.container():
                # Safely get photo from card
                photo = None
                if isinstance(card, dict):
                    photo = card.get('photo', '')
                elif hasattr(card, 'photo'):
                    photo = card.photo
                
                # Display image with error handling
                try:
                    if photo:
                        if photo.startswith('data:image'):
                            # Handle base64 images
                            try:
                                st.image(photo, use_column_width=True)
                            except Exception as e:
                                st.error(f"Error displaying image: {str(e)}")
                                st.image("https://via.placeholder.com/300x400?text=Image+Error", use_column_width=True)
                        elif photo.startswith('http'):
                            # Handle URL images
                            try:
                                response = requests.head(photo, timeout=5)
                                if response.status_code == 200:
                                    st.image(photo, use_column_width=True)
                                else:
                                    st.image("https://via.placeholder.com/300x400?text=Image+Not+Available", use_column_width=True)
                            except:
                                st.image("https://via.placeholder.com/300x400?text=Image+Not+Available", use_column_width=True)
                        else:
                            st.image("https://via.placeholder.com/300x400?text=No+Image", use_column_width=True)
                    else:
                        st.image("https://via.placeholder.com/300x400?text=No+Image", use_column_width=True)
                except Exception as e:
                    st.error(f"Error displaying image: {str(e)}")
                    st.image("https://via.placeholder.com/300x400?text=Image+Error", use_column_width=True)
                
                # Safely get card details
                player_name = card.get('player_name', '') if isinstance(card, dict) else getattr(card, 'player_name', '')
                year = card.get('year', '') if isinstance(card, dict) else getattr(card, 'year', '')
                card_set = card.get('card_set', '') if isinstance(card, dict) else getattr(card, 'card_set', '')
                card_number = card.get('card_number', '') if isinstance(card, dict) else getattr(card, 'card_number', '')
                
                # Display card details
                st.markdown(f"""
                <div style="padding: 1rem;">
                    <h4>{player_name}</h4>
                    <p>{year} {card_set}</p>
                    <p>#{card_number}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Add edit button if not shared collection
                if not is_shared:
                    if st.button("Edit", key=f"edit_{idx}"):
                        st.session_state.editing_card = idx
                        st.session_state.editing_data = card
                        st.session_state.current_tab = "View Collection"  # Set the current tab
                        st.rerun()  # Force a rerun to show the edit form

def display_collection_table(filtered_df):
    """Display the collection in a simple table format"""
    if filtered_df.empty:
        st.info("No cards found matching the current filters.")
        return
        
    # Select and rename columns for display
    display_df = filtered_df[[
        'player_name', 'year', 'card_set', 'condition',
        'purchase_price', 'current_value', 'roi', 'tags'
    ]].copy()
    
    # Rename columns for better display
    display_df.columns = [
        'Player', 'Year', 'Set', 'Condition',
        'Purchase Price', 'Current Value', 'ROI (%)', 'Tags'
    ]
    
    # Format numeric columns
    display_df['Purchase Price'] = display_df['Purchase Price'].apply(lambda x: f"${float(x):.2f}")
    display_df['Current Value'] = display_df['Current Value'].apply(lambda x: f"${float(x):.2f}")
    display_df['ROI (%)'] = display_df['ROI (%)'].apply(lambda x: f"{float(x):.1f}%")
    
    # Display the table
    st.dataframe(
        display_df,
        use_column_width=True,
        hide_index=True
    ) 