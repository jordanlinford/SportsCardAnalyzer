import streamlit as st
from typing import Dict, Optional
import pyperclip

def render_display_case_header(
    display_case: Dict,
    on_share: Optional[callable] = None,
    show_metrics: bool = True
) -> None:
    """
    Renders a header for a display case with title, description, and sharing options.
    
    Args:
        display_case: Dictionary containing display case data
        on_share: Optional callback function for sharing
        show_metrics: Whether to show metrics (default: True)
    """
    # Title and Description
    st.title(display_case.get('name', 'Untitled Display Case'))
    st.markdown(display_case.get('description', ''))
    
    # Metrics
    if show_metrics:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Total Cards",
                len(display_case.get('cards', []))
            )
        with col2:
            st.metric(
                "Total Value",
                f"${display_case.get('total_value', 0):,.2f}"
            )
        with col3:
            avg_roi = sum(
                card.get('roi', 0) for card in display_case.get('cards', [])
            ) / max(1, len(display_case.get('cards', [])))
            st.metric(
                "Average ROI",
                f"{avg_roi:.1f}%"
            )
    
    # Share Section
    if on_share:
        share_col1, share_col2 = st.columns([3, 1])
        with share_col1:
            share_url = on_share(display_case)
            st.text_input(
                "Share Link",
                value=share_url,
                disabled=True,
                key="share_url"
            )
        with share_col2:
            if st.button("Copy Link", use_container_width=True):
                pyperclip.copy(share_url)
                st.success("Link copied to clipboard!")
    
    st.divider() 