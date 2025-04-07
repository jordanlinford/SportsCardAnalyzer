import streamlit as st
from modules.ui.branding import BrandingComponent

class Navigation:
    """Handles navigation and sidebar components."""
    
    @staticmethod
    def display_sidebar():
        """Display the sidebar with navigation and branding."""
        with st.sidebar:
            # Display vertical logo
            BrandingComponent.display_vertical_logo()
            
            # Add spacing
            st.markdown("---")
            
            # Navigation links
            st.markdown("### Navigation")
            if st.button("🏠 Home"):
                st.switch_page("app.py")
            if st.button("📊 Market Analysis"):
                st.switch_page("pages/1_market_analysis.py")
            if st.button("📈 Price Trends"):
                st.switch_page("pages/2_price_trends.py")
            if st.button("📦 Collection Manager"):
                st.switch_page("pages/3_collection_manager.py")
            if st.button("🖼️ Display Case"):
                st.switch_page("pages/4_display_case.py")
            if st.button("📱 Mobile App"):
                st.switch_page("pages/5_mobile_app.py")
            if st.button("👤 Profile"):
                st.switch_page("pages/6_profile_management.py")
            
            # Add spacing
            st.markdown("---")
            
            # Logout button
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.rerun()
    
    @staticmethod
    def display_header():
        """Display the header with horizontal logo."""
        col1, col2 = st.columns([1, 4])
        with col1:
            BrandingComponent.display_horizontal_logo()
        with col2:
            st.markdown("""
                <div style="text-align: right; padding: 1rem;">
                    <h2>Sports Card Analyzer</h2>
                </div>
            """, unsafe_allow_html=True) 