import streamlit as st
import sys
from pathlib import Path
import logging

# Add project root directory to Python path
project_root = str(Path(__file__).parent.absolute())
sys.path.append(project_root)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import UI components
from modules.ui.theme.theme_manager import ThemeManager
from modules.ui.branding import BrandingComponent

# Set page config
st.set_page_config(
    page_title="Sports Card Analyzer",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply theme and branding styles
ThemeManager.apply_theme_styles()
BrandingComponent.add_branding_styles()

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None
if 'uid' not in st.session_state:
    st.session_state.uid = None

# Check if user is logged in
if not st.session_state.user:
    st.switch_page("pages/0_login.py")

# Sidebar header with branding
with st.sidebar:
    # Container for sidebar header with branding
    st.markdown('<div class="sidebar-header">', unsafe_allow_html=True)
    BrandingComponent.display_horizontal_logo()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Logout button
    if st.button("Logout"):
        st.session_state.user = None
        st.session_state.uid = None
        st.rerun()
    
    # Page navigation
    st.markdown("---")
    st.page_link("app.py", label="Home", icon="🏠")
    st.page_link("pages/1_display_case.py", label="Display Case", icon="📸")
    st.page_link("pages/2_market_analysis.py", label="Market Analysis", icon="📊")
    st.page_link("pages/3_collection_manager.py", label="Collection Manager", icon="📋")
    st.page_link("pages/4_settings.py", label="Settings", icon="⚙️")

# Main content header with branding
st.markdown('<div class="main-header">', unsafe_allow_html=True)
BrandingComponent.display_horizontal_logo()
st.markdown('</div>', unsafe_allow_html=True)

# Main content
st.title("Welcome to Sports Card Analyzer Pro")
st.write("Your all-in-one platform for managing and analyzing your sports card collection.")

# Display app features in a styled card
with ThemeManager.styled_card():
    st.subheader("Features")
    st.markdown("""
    1. **Market Analysis**
       - Search for cards
       - View price trends
       - Get market insights
    
    2. **Trade Analyzer**
       - Analyze potential trades
       - Compare card values
       - Make informed decisions
    
    3. **Collection Manager**
       - Track your cards
       - Monitor value changes
       - Organize your collection
    
    4. **Display Cases**
       - Create custom displays
       - Group cards by tags
       - Showcase your collection
    """)
logger.debug("Main function completed")

if __name__ == "__main__":
    logger.debug("Starting application")
    main() 