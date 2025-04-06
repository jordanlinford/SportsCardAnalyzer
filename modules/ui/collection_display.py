import streamlit as st
import pandas as pd
from modules.ui.styles import get_collection_styles
from modules.database.service import DatabaseService
from datetime import datetime
import traceback
import base64
from typing import Optional
import requests

def display_collection_grid(filtered_df, is_shared=False):
    """Display the collection in a grid layout with cards"""
    if filtered_df.empty:
        st.info("No cards found matching the current filters.")
        return

    # Create the grid container
    grid_html = '<div class="card-grid">'
    
    # Iterate through the DataFrame and create cards
    for idx, card in filtered_df.iterrows():
        # Calculate ROI
        try:
            purchase_price = float(safe_get(card, 'purchase_price', 0))
            current_value = float(safe_get(card, 'current_value', 0))
            roi = ((current_value - purchase_price) / purchase_price * 100) if purchase_price > 0 else 0
        except (ValueError, TypeError):
            purchase_price = 0.0
            current_value = 0.0
            roi = 0.0
        
        # Create unique container for each card
        with st.container():
            # Handle image display
            photo_url = safe_get(card, 'photo', '')
            
            # Create a column for the image and details
            col1, col2 = st.columns([1, 1])
            
            with col1:
                try:
                    if not photo_url or pd.isna(photo_url):
                        st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image", use_container_width=True)
                    elif photo_url.startswith('data:image'):
                        # Handle base64 images
                        try:
                            # Validate base64 string
                            base64_part = photo_url.split(',')[1]
                            base64.b64decode(base64_part)
                            st.image(photo_url, use_container_width=True)
                        except Exception as e:
                            st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+Image", use_container_width=True)
                            st.warning(f"Error displaying image for card {idx + 1}")
                    else:
                        # Handle URL images
                        try:
                            st.image(photo_url, use_container_width=True)
                        except Exception as e:
                            st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+URL", use_container_width=True)
                            st.warning(f"Error loading image URL for card {idx + 1}")
                except Exception as e:
                    st.image("https://placehold.co/300x400/e6e6e6/666666.png?text=Error", use_container_width=True)
                    st.warning(f"Error displaying image for card {idx + 1}")
            
            with col2:
                # Display card details
                st.markdown(f"""
                <div style="padding: 1rem;">
                    <h4 style="margin-bottom: 0.5rem;">{safe_get(card, 'player_name', 'Unknown Player')}</h4>
                    <p style="margin: 0.25rem 0;">{safe_get(card, 'year', '')} {safe_get(card, 'card_set', '')}</p>
                    <p style="margin: 0.25rem 0;">Condition: {safe_get(card, 'condition', 'Unknown')}</p>
                    <p style="margin: 0.25rem 0;">Purchase: ${purchase_price:.2f}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Add editable current value field and action buttons if not in shared view
                if not is_shared:
                    try:
                        new_value = st.number_input(
                            "Current Value ($)",
                            min_value=0.0,
                            value=float(current_value),
                            format="%.2f",
                            key=f"value_{idx}"
                        )
                        
                        if new_value != current_value:
                            try:
                                # Update the value in the collection
                                st.session_state.collection.loc[idx, 'current_value'] = float(new_value)
                                
                                # Recalculate ROI
                                new_roi = ((new_value - purchase_price) / purchase_price * 100) if purchase_price > 0 else 0
                                st.session_state.collection.loc[idx, 'roi'] = float(new_roi)
                                
                                # Update last_updated timestamp
                                st.session_state.collection.loc[idx, 'last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                
                                # Save to Firebase
                                if DatabaseService.save_user_collection(st.session_state.uid, st.session_state.collection):
                                    st.success("Value updated successfully!")
                                    st.rerun()
                                else:
                                    st.error("Failed to update value. Please try again.")
                                    # Revert changes if save failed
                                    st.session_state.collection.loc[idx, 'current_value'] = current_value
                                    st.session_state.collection.loc[idx, 'roi'] = roi
                            except Exception as e:
                                st.error(f"Error updating value: {str(e)}")
                                # Revert changes on error
                                st.session_state.collection.loc[idx, 'current_value'] = current_value
                                st.session_state.collection.loc[idx, 'roi'] = roi
                    except Exception as e:
                        st.error(f"Error handling value input: {str(e)}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Edit", key=f"edit_{idx}", use_container_width=True):
                            st.session_state.editing_card = idx
                            st.session_state.editing_data = card.to_dict()
                            st.rerun()
                    
                    with col2:
                        if st.button("Delete", key=f"delete_{idx}", use_container_width=True):
                            if idx in filtered_df.index:
                                st.session_state.collection = st.session_state.collection.drop(idx)
                                st.session_state.collection = st.session_state.collection.reset_index(drop=True)
                                st.rerun()
                else:
                    # For shared view, just display the current value and ROI
                    st.markdown(f"<p>Current Value: ${current_value:.2f}</p>", unsafe_allow_html=True)
                    st.markdown(f"<p>ROI: {roi:.1f}%</p>", unsafe_allow_html=True)

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