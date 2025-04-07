"""Collection display component for the Sports Card Analyzer app."""
import streamlit as st
import pandas as pd
from modules.ui.styles import get_collection_styles
from modules.database.service import DatabaseService
from datetime import datetime
import traceback
import base64
from typing import List, Optional
import requests
import io
from PIL import Image
from ..database.models import Card

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

class CardDisplay:
    @staticmethod
    def display_image(image_data: str, use_column_width=True):
        """Display a card image with proper error handling."""
        try:
            if not image_data:
                st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image", use_column_width=use_column_width)
                return
            
            # Handle base64 images
            if isinstance(image_data, str) and image_data.startswith('data:image'):
                try:
                    # Extract the base64 part
                    base64_data = image_data.split(',')[1]
                    # Decode the base64 string
                    image_bytes = base64.b64decode(base64_data)
                    # Create an image from the bytes
                    image = Image.open(io.BytesIO(image_bytes))
                    # Display the image
                    st.image(image, use_column_width=use_column_width)
                    return
                except Exception as e:
                    st.error(f"Failed to load base64 image: {str(e)}")
                    st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Base64", use_column_width=use_column_width)
                    return

            # Handle URL images
            if isinstance(image_data, str) and image_data.startswith(('http://', 'https://')):
                try:
                    # Enhanced headers for image requests
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Connection": "keep-alive",
                        "Cache-Control": "no-cache",
                        "Pragma": "no-cache"
                    }

                    # Try to load the image with requests
                    response = requests.get(image_data, headers=headers, timeout=10, verify=True)
                    response.raise_for_status()

                    # Verify content type is an image
                    content_type = response.headers.get('content-type', '').lower()
                    if 'image' not in content_type:
                        raise ValueError(f"Invalid content type: {content_type}")

                    # Convert to image bytes and display
                    image_bytes = io.BytesIO(response.content)
                    st.image(image_bytes, use_column_width=use_column_width)
                    return
                except Exception as e:
                    # If the first attempt fails, try direct loading
                    try:
                        st.image(image_data, use_column_width=use_column_width)
                        return
                    except:
                        st.error(f"Failed to load URL image: {str(e)}")
                        st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Image+Load+Failed", use_column_width=use_column_width)
                        return

            # Invalid image format
            st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Image", use_column_width=use_column_width)
            
        except Exception as e:
            st.error(f"Error displaying image: {str(e)}")
            st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Image+Error", use_column_width=use_column_width)

    @staticmethod
    def display_grid(cards: List[Card], on_click=None):
        """Display cards in a grid layout."""
        if cards is None or (hasattr(cards, 'empty') and cards.empty):
            st.warning("No cards to display.")
            return

        # Add grid styles
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
        
        /* Dark mode */
        @media (prefers-color-scheme: dark) {
            .card-grid-item {
                background: #111111;
                border-color: rgba(255,255,255,0.1);
            }
        }
        </style>
        """, unsafe_allow_html=True)

        # Create columns for the grid
        cols = st.columns(3)
        
        # Convert DataFrame to list of dictionaries if needed
        if hasattr(cards, 'to_dict'):
            cards = cards.to_dict('records')
        
        # Display each card in the grid
        for i, card in enumerate(cards):
            col = cols[i % 3]
            with col:
                st.markdown('<div class="card-grid-item">', unsafe_allow_html=True)
                
                # Display card image using the proper display_image method
                if isinstance(card, dict):
                    image_url = card.get('photo', '')
                else:
                    image_url = getattr(card, 'photo', '')
                
                # Use the CardDisplay.display_image method for consistent image handling
                CardDisplay.display_image(image_url, use_column_width=True)
                
                # Display card details
                st.markdown('<div class="card-grid-content">', unsafe_allow_html=True)
                
                # Get card details
                if isinstance(card, dict):
                    player_name = card.get('player_name', '')
                    year = card.get('year', '')
                    card_set = card.get('card_set', '')
                    card_number = card.get('card_number', '')
                    condition = card.get('condition', '')
                    current_value = card.get('current_value', 0)
                else:
                    player_name = getattr(card, 'player_name', '')
                    year = getattr(card, 'year', '')
                    card_set = getattr(card, 'card_set', '')
                    card_number = getattr(card, 'card_number', '')
                    condition = getattr(card, 'condition', '')
                    current_value = getattr(card, 'current_value', 0)
                
                # Display player name
                st.markdown(f'<h3>{player_name}</h3>', unsafe_allow_html=True)
                
                # Display card details
                st.markdown(f'<p>{year} {card_set} #{card_number}</p>', unsafe_allow_html=True)
                
                # Display condition and value
                st.markdown(f'<p>Condition: {condition}</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="value">Value: ${current_value:,.2f}</p>', unsafe_allow_html=True)
                
                # Add edit button if on_click is provided
                if on_click is not None:
                    if st.button("Edit", key=f"edit_{i}"):
                        on_click(i)
                
                st.markdown('</div>', unsafe_allow_html=True)  # Close card-grid-content
                st.markdown('</div>', unsafe_allow_html=True)  # Close card-grid-item

    @staticmethod
    def display_table(cards: List[Card], on_click=None):
        """Display cards in a table layout."""
        if not cards:
            st.warning("No cards to display.")
            return
        
        # Convert cards to DataFrame
        df = pd.DataFrame([
            {
                'Player': card.player_name if hasattr(card, 'player_name') else card.get('player_name', ''),
                'Year': card.year if hasattr(card, 'year') else card.get('year', ''),
                'Set': card.card_set if hasattr(card, 'card_set') else card.get('card_set', ''),
                'Number': card.card_number if hasattr(card, 'card_number') else card.get('card_number', ''),
                'Condition': card.condition if hasattr(card, 'condition') else card.get('condition', ''),
                'Purchase Price': card.purchase_price if hasattr(card, 'purchase_price') else card.get('purchase_price', 0),
                'Current Value': card.current_value if hasattr(card, 'current_value') else card.get('current_value', 0),
                'ROI': card.roi if hasattr(card, 'roi') else card.get('roi', 0)
            }
            for card in cards
        ])
        
        # Format currency columns
        df['Purchase Price'] = df['Purchase Price'].apply(lambda x: f"${x:.2f}")
        df['Current Value'] = df['Current Value'].apply(lambda x: f"${x:.2f}")
        df['ROI'] = df['ROI'].apply(lambda x: f"{x:.1f}%")
        
        # Display table
        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True
        ) 