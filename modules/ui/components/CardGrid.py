import streamlit as st
import pandas as pd
from typing import List, Dict, Callable, Optional
import math

def render_card_grid(
    cards: List[Dict],
    on_click: Optional[Callable] = None,
    cards_per_row: int = 5,
    show_details: bool = True
) -> None:
    """
    Renders a responsive grid of cards with hover effects.
    
    Args:
        cards: List of card dictionaries
        on_click: Optional callback function when a card is clicked
        cards_per_row: Number of cards to display per row (default: 5)
        show_details: Whether to show card details on hover (default: True)
    """
    if not cards:
        st.info("No cards to display")
        return
    
    # Calculate number of rows needed
    num_rows = math.ceil(len(cards) / cards_per_row)
    
    # Create CSS for hover effects
    st.markdown("""
    <style>
    .card-container {
        position: relative;
        width: 100%;
        padding-bottom: 140%;
        overflow: hidden;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
    }
    .card-container:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .card-image {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .card-details {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(0,0,0,0.7);
        color: white;
        padding: 8px;
        font-size: 0.8em;
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    .card-container:hover .card-details {
        opacity: 1;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create grid layout
    for row in range(num_rows):
        cols = st.columns(cards_per_row)
        for col in range(cards_per_row):
            idx = row * cards_per_row + col
            if idx < len(cards):
                card = cards[idx]
                with cols[col]:
                    # Create card container
                    st.markdown(f"""
                    <div class="card-container" onclick="document.getElementById('card-{idx}').click()">
                        <img class="card-image" src="{card.get('photo', '')}" alt="{card.get('player_name', '')}">
                        {f'''
                        <div class="card-details">
                            <div><strong>{card.get('player_name', '')}</strong></div>
                            <div>{card.get('year', '')} {card.get('card_set', '')}</div>
                            <div>${card.get('current_value', 0):,.2f}</div>
                        </div>
                        ''' if show_details else ''}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Add invisible button for click handling
                    if on_click:
                        st.button(
                            "View Card",
                            key=f"card-{idx}",
                            on_click=on_click,
                            args=(card,),
                            use_container_width=True
                        ) 