import streamlit as st
from typing import List, Dict, Callable

def render_card_grid(cards: List[Dict], on_click: Callable = None) -> None:
    """
    Renders a grid of cards with images only.
    
    Args:
        cards: List of card dictionaries
        on_click: Optional callback function when a card is clicked
    """
    if not cards:
        st.info("No cards to display")
        return
    
    # Create a grid of cards
    cols = st.columns(3)  # 3 cards per row
    for idx, card in enumerate(cards):
        col = cols[idx % 3]
        with col:
            # Create a container for each card
            with st.container():
                # Display card image
                if card.get('photo'):
                    st.image(card['photo'], use_container_width=True)
                
                # Add click handler if provided
                if on_click:
                    if st.button("View Details", key=f"view_{idx}"):
                        on_click(card) 