"""
Test View for New Display Manager
This page provides a safe environment to test the new display manager implementation.
"""

import streamlit as st
from modules.core.display_manager import DisplayManager
from modules.core.collection_manager import CollectionManager
from config.feature_flags import is_feature_enabled

def main():
    st.title("Display Manager Test View")
    
    # Check if feature is enabled
    if not is_feature_enabled('new_display_manager'):
        st.warning("New display manager is not enabled. Enable it in feature flags to test.")
        return
    
    # Get current collection
    collection = CollectionManager.get_collection()
    
    # Display options
    display_mode = st.radio(
        "Select Display Mode",
        ["Grid", "Table", "Details"],
        horizontal=True
    )
    
    # Display collection based on selected mode
    if display_mode == "Grid":
        st.subheader("Grid View")
        DisplayManager.display_collection_grid(collection)
        
    elif display_mode == "Table":
        st.subheader("Table View")
        DisplayManager.display_collection_table(collection)
        
    elif display_mode == "Details":
        st.subheader("Details View")
        if collection:
            # Create a dropdown to select a card
            card_options = [
                f"{i+1}. {card.get('player_name', 'Unknown')} - {card.get('year', '')} {card.get('card_set', '')}"
                for i, card in enumerate(collection)
            ]
            selected_idx = st.selectbox(
                "Select a card to view details",
                range(len(card_options)),
                format_func=lambda i: card_options[i]
            )
            if selected_idx is not None:
                DisplayManager.display_card_details(collection[selected_idx])
        else:
            st.info("No cards available to display")
    
    # Display collection statistics
    stats = CollectionManager.get_collection_stats()
    DisplayManager.display_collection_stats(stats)

if __name__ == "__main__":
    main() 