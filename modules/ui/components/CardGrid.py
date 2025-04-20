import streamlit as st
import base64
import io
from PIL import Image
import requests

def render_card_grid(cards, on_click=None):
    if not cards:
        st.info("No cards to display.")
        return

    st.markdown("""
    <style>
    .card-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        padding: 0.5rem;
    }
    
    .card-container {
        position: relative;
        width: 80px;
        height: 120px;
        border-radius: 4px;
        overflow: hidden;
        transition: transform 0.2s ease-in-out;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        background: #f5f5f5;
        flex: 0 0 auto;
    }

    .card-container:hover {
        transform: scale(1.05);
    }

    .card-img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        border-radius: 4px;
    }

    .card-overlay {
        position: absolute;
        bottom: 0;
        width: 100%;
        background: rgba(0,0,0,0.75);
        color: #fff;
        font-size: 0.6rem;
        padding: 0.2rem;
        text-align: center;
        opacity: 0;
        transition: opacity 0.3s ease-in-out;
    }

    .card-container:hover .card-overlay {
        opacity: 1;
    }
    </style>
    """, unsafe_allow_html=True)

    # Create a container for the grid
    grid_container = st.container()
    
    with grid_container:
        st.markdown('<div class="card-grid">', unsafe_allow_html=True)
        
        for card in cards:
            photo = card.get('photo', '')
            player_name = card.get('player_name', '')
            year = card.get('year', '')
            card_set = card.get('card_set', '')
            value = card.get('current_value', 0)

            st.markdown(f"""
            <div class="card-container">
                <img src="{photo}" class="card-img" onerror="this.src='https://placehold.co/80x120?text=No+Image';"/>
                <div class="card-overlay">
                    <strong>{player_name}</strong><br/>
                    {year} {card_set}<br/>
                    ${value:,.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True) 