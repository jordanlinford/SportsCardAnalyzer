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
            purchase_price = float(card.get('purchase_price', 0))
            current_value = float(card.get('current_value', 0))
            roi = ((current_value - purchase_price) / purchase_price * 100) if purchase_price > 0 else 0
        except (ValueError, TypeError):
            purchase_price = 0.0
            current_value = 0.0
            roi = 0.0
        
        # Create unique container for each card
        with st.container():
            # Handle image display
            photo_url = card.get('photo', '')
            if not photo_url or pd.isna(photo_url):
                photo_url = "https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image"
            elif photo_url.startswith('data:image'):
                # Handle base64 images
                try:
                    # Display base64 image
                    st.image(photo_url, use_container_width=True)
                except Exception as e:
                    st.error(f"Error displaying base64 image for card {idx + 1}: {str(e)}")
                    photo_url = "https://placehold.co/300x400/e6e6e6/666666.png?text=Base64+Error"
            else:
                # Handle URL images
                try:
                    # Test if URL is valid
                    response = requests.head(photo_url, timeout=5)
                    if response.status_code != 200:
                        st.warning(f"Invalid image URL status code {response.status_code} for card {idx + 1}")
                        photo_url = "https://placehold.co/300x400/e6e6e6/666666.png?text=Invalid+URL"
                except Exception as e:
                    st.warning(f"Error validating image URL for card {idx + 1}: {str(e)}")
                    photo_url = "https://placehold.co/300x400/e6e6e6/666666.png?text=URL+Error"
            
            # Card HTML with improved error handling
            try:
                card_html = f'''
                    <div class="collection-card">
                        <div class="card-image-container">
                            <img src="{photo_url}" alt="Card Image" onerror="this.src='https://placehold.co/300x400/e6e6e6/666666.png?text=Image+Error'">
                        </div>
                        <div class="card-details">
                            <h3>{card.get('player_name', 'Unknown Player')}</h3>
                            <p>{card.get('year', '')} {card.get('card_set', '')}</p>
                            <p>Condition: {card.get('condition', 'Unknown')}</p>
                            <p>Purchase: ${purchase_price:.2f}</p>
                        </div>
                    </div>
                '''
                st.markdown(card_html, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error creating card HTML for card {idx + 1}: {str(e)}")
                continue
            
            # Add editable current value field and action buttons if not in shared view
            if not is_shared:
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
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
                                st.write("Debug: Error traceback:", traceback.format_exc())
                                # Revert changes on error
                                st.session_state.collection.loc[idx, 'current_value'] = current_value
                                st.session_state.collection.loc[idx, 'roi'] = roi
                    except Exception as e:
                        st.error(f"Error handling value input: {str(e)}")
                        st.write("Debug: Error traceback:", traceback.format_exc())
                
                with col2:
                    if st.button("Edit", key=f"edit_{idx}", use_container_width=True):
                        st.session_state.editing_card = idx
                        st.session_state.editing_data = card.to_dict()
                        st.rerun()
                
                with col3:
                    if st.button("Delete", key=f"delete_{idx}", use_container_width=True):
                        if idx in filtered_df.index:
                            st.session_state.collection = st.session_state.collection.drop(idx)
                            st.session_state.collection = st.session_state.collection.reset_index(drop=True)
                            st.rerun()
            else:
                # For shared view, just display the current value
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