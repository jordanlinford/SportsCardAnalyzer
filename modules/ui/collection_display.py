"""Collection display component for the Sports Card Analyzer app."""
import streamlit as st
import pandas as pd
from modules.ui.styles import get_collection_styles
from modules.database.service import DatabaseService
from datetime import datetime
import traceback
import base64
from typing import List, Optional, Union, Dict, Any
import requests
import io
from PIL import Image
from ..database.models import Card

def display_collection_grid(filtered_collection, is_shared=False):
    """Display collection in a responsive grid layout"""
    # Debug information
    st.write("### Grid Display Debug")
    st.write(f"Collection type: {type(filtered_collection)}")
    if isinstance(filtered_collection, pd.DataFrame):
        st.write(f"DataFrame shape: {filtered_collection.shape}")
        st.write(f"DataFrame columns: {filtered_collection.columns.tolist()}")
    elif isinstance(filtered_collection, list):
        st.write(f"List length: {len(filtered_collection)}")
        if filtered_collection:
            st.write("First item type:", type(filtered_collection[0]))
    
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
                                st.image(photo, use_container_width=True)
                            except Exception as e:
                                st.error(f"Error displaying image: {str(e)}")
                                st.image("https://via.placeholder.com/300x400?text=Image+Error", use_container_width=True)
                        elif photo.startswith('http'):
                            # Handle URL images
                            try:
                                response = requests.head(photo, timeout=5)
                                if response.status_code == 200:
                                    st.image(photo, use_container_width=True)
                                else:
                                    st.image("https://via.placeholder.com/300x400?text=Image+Not+Available", use_container_width=True)
                            except:
                                st.image("https://via.placeholder.com/300x400?text=Image+Not+Available", use_container_width=True)
                        else:
                            st.image("https://via.placeholder.com/300x400?text=No+Image", use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/300x400?text=No+Image", use_container_width=True)
                except Exception as e:
                    st.error(f"Error displaying image: {str(e)}")
                    st.image("https://via.placeholder.com/300x400?text=Image+Error", use_container_width=True)
                
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
        use_container_width=True,
        hide_index=True
    ) 

class CardDisplay:
    @staticmethod
    def display_image(image_data: str, use_container_width=True):
        """Display a card image with proper error handling."""
        try:
            if not image_data:
                st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image", use_container_width=use_container_width)
                return
            
            # Handle URL images
            if image_data.startswith('http'):
                try:
                    response = requests.get(image_data, timeout=5)
                    if response.status_code == 200:
                        image = Image.open(io.BytesIO(response.content))
                        st.image(image, use_container_width=use_container_width)
                    else:
                        st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Base64", use_container_width=use_container_width)
                except:
                    st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Image+Load+Failed", use_container_width=use_container_width)
                return
            
            # Handle base64 images
            if image_data.startswith('data:image'):
                try:
                    # Extract the base64 part
                    base64_part = image_data.split(',')[1]
                    # Decode the base64 string
                    image_bytes = base64.b64decode(base64_part)
                    # Convert to image
                    image = Image.open(io.BytesIO(image_bytes))
                    st.image(image, use_container_width=use_container_width)
                except:
                    st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Base64", use_container_width=use_container_width)
                return
            
            # Handle file path images
            try:
                image = Image.open(image_data)
                st.image(image, use_container_width=use_container_width)
            except:
                st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Image+Load+Failed", use_container_width=use_container_width)
            
        except Exception as e:
            st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Image+Error", use_container_width=use_container_width)

    @staticmethod
    def display_grid(cards: Union[List[Union[Card, Dict[str, Any]]], pd.DataFrame], on_click=None):
        """Display cards in a grid layout."""
        if cards is None or (hasattr(cards, 'empty') and cards.empty):
            st.warning("No cards to display.")
            return

        # Add grid styles with mobile responsiveness
        st.markdown("""
        <style>
        .card-grid-item {
            border: 1px solid rgba(0,0,0,0.1);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            background: white;
            transition: all 0.2s ease;
        }
        
        .card-grid-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        .card-grid-content {
            margin-top: 1rem;
            text-align: center;
        }
        
        .card-grid-content h3 {
            margin: 0;
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-color, #000000);
        }
        
        .card-grid-content p {
            margin: 0.25rem 0;
            font-size: 0.9rem;
            color: var(--text-color, #000000);
            opacity: 0.8;
        }
        
        .card-grid-content .value {
            font-weight: 600;
            color: var(--primary-color, #000000);
        }
        
        /* Mobile responsiveness */
        @media (max-width: 768px) {
            .card-grid-item {
                padding: 0.75rem;
            }
            
            .card-grid-content h3 {
                font-size: 1rem;
            }
            
            .card-grid-content p {
                font-size: 0.8rem;
            }
        }
        
        /* Dark mode */
        @media (prefers-color-scheme: dark) {
            .card-grid-item {
                background: #111111;
                border-color: rgba(255,255,255,0.1);
            }
        }
        </style>
        """, unsafe_allow_html=True)

        # Create responsive columns based on screen size
        screen_width = st.session_state.get('screen_width', 1200)  # Default to desktop
        num_columns = 3 if screen_width > 768 else (2 if screen_width > 480 else 1)
        cols = st.columns(num_columns)
        
        # Convert DataFrame to list of dictionaries if needed
        if isinstance(cards, pd.DataFrame):
            cards = cards.to_dict('records')
        
        # Display cards in grid
        for idx, card in enumerate(cards):
            col = cols[idx % num_columns]
            with col:
                with st.container():
                    # Get card data
                    if isinstance(card, dict):
                        card_data = card
                    else:
                        card_data = card.to_dict() if hasattr(card, 'to_dict') else card.__dict__
                    
                    # Display image
                    photo = card_data.get('photo', '')
                    CardDisplay.display_image(photo)
                    
                    # Display card details
                    st.markdown(f"""
                    <div class="card-grid-content">
                        <h3>{card_data.get('player_name', 'Unknown')}</h3>
                        <p>{card_data.get('year', '')} {card_data.get('card_set', '')}</p>
                        <p>#{card_data.get('card_number', '')}</p>
                        <p class="value">${float(card_data.get('current_value', 0)):.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Add click handler if provided
                    if on_click:
                        if st.button("Edit", key=f"edit_{idx}"):
                            on_click(idx)

    @staticmethod
    def display_table(cards: Union[List[Union[Card, Dict[str, Any]]], pd.DataFrame], on_click=None):
        """Display cards in a table format."""
        if cards is None or (hasattr(cards, 'empty') and cards.empty):
            st.warning("No cards to display.")
            return
            
        # Convert to DataFrame if needed
        if isinstance(cards, list):
            df = pd.DataFrame([card.to_dict() if hasattr(card, 'to_dict') else card for card in cards])
        else:
            df = cards.copy()
            
        # Select and rename columns for display
        display_df = df[[
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
            use_container_width=True,
            hide_index=True
        )

def display_image(image_data: str, use_container_width=True):
    """Display an image from various sources (URL, base64, or file path)"""
    try:
        if not image_data:
            st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=No+Image", use_container_width=use_container_width)
            return
            
        # Handle URL images
        if image_data.startswith('http'):
            try:
                response = requests.get(image_data, timeout=5)
                if response.status_code == 200:
                    image = Image.open(io.BytesIO(response.content))
                    st.image(image, use_container_width=use_container_width)
                else:
                    st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Image+Not+Available", use_container_width=use_container_width)
            except:
                st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Image+Not+Available", use_container_width=use_container_width)
            return
            
        # Handle base64 images
        if image_data.startswith('data:image'):
            try:
                base64_part = image_data.split(',')[1]
                image_bytes = base64.b64decode(base64_part)
                image = Image.open(io.BytesIO(image_bytes))
                st.image(image, use_container_width=use_container_width)
            except:
                st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Base64", use_container_width=use_container_width)
            return
            
        # Handle file path images
        try:
            image = Image.open(image_data)
            st.image(image, use_container_width=use_container_width)
        except:
            st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Image+Load+Failed", use_container_width=use_container_width)
            
    except Exception as e:
        st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Image+Error", use_container_width=use_container_width)

def display_dataframe(df, use_container_width=True):
    """Display a dataframe with proper formatting"""
    st.dataframe(df, use_container_width=use_container_width, hide_index=True) 

def has_cards(collection):
    """Check if collection has any cards"""
    if collection is None:
        return False
    if isinstance(collection, pd.DataFrame):
        return not collection.empty
    if isinstance(collection, list):
        return len(collection) > 0
    return False 