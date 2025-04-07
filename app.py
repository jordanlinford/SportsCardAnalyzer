import streamlit as st
import sys
from pathlib import Path
import logging
from modules.core.firebase_manager import FirebaseManager
from modules.ui.theme.theme_manager import ThemeManager
from modules.ui.branding import BrandingComponent

# Add project root directory to Python path
project_root = str(Path(__file__).parent.absolute())
sys.path.append(project_root)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set page config with custom CSS
st.set_page_config(
    page_title="Sports Card Analyzer Pro",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS for persistent branding
st.markdown("""
    <style>
        /* Header container */
        .stApp > header {
            background-color: white;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* Sidebar container */
        .stSidebar {
            background-color: white;
            padding: 1rem;
        }
        
        /* Logo container in header */
        .stApp > header .logo-container {
            margin: 0;
            padding: 0;
        }
        
        /* Logo container in sidebar */
        .stSidebar .logo-container {
            margin-bottom: 1rem;
            padding: 0.5rem;
            border-bottom: 1px solid rgba(0,0,0,0.1);
        }
        
        /* Dark mode overrides */
        @media (prefers-color-scheme: dark) {
            .stApp > header {
                background-color: #111111;
            }
            
            .stSidebar {
                background-color: #111111;
            }
            
            .stSidebar .logo-container {
                border-bottom-color: rgba(255,255,255,0.1);
            }
        }
    </style>
""", unsafe_allow_html=True)

# Apply theme and branding styles
ThemeManager.apply_theme_styles()
BrandingComponent.add_branding_styles()

def initialize_firebase():
    """Initialize Firebase components."""
    try:
        FirebaseManager.initialize()
        return True
    except Exception as e:
        st.error(f"Error initializing Firebase: {str(e)}")
        return False

def main():
    # Initialize session state variables
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'uid' not in st.session_state:
        st.session_state.uid = None
    
    # Initialize Firebase
    if not initialize_firebase():
        return
    
    # Check if user is logged in
    if not st.session_state.user:
        st.switch_page("pages/0_login.py")
        return
    
    # Header with branding
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    BrandingComponent.display_horizontal_logo()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        # Sidebar header with branding
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        BrandingComponent.display_horizontal_logo()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Navigation
        st.page_link("app.py", label="Home", icon="🏠")
        st.page_link("pages/1_market_analysis.py", label="Market Analysis", icon="📊")
        st.page_link("pages/4_display_case.py", label="Display Case", icon="📸")
        st.page_link("pages/3_collection_manager.py", label="Collection Manager", icon="📋")
        st.page_link("pages/2_trade_analyzer.py", label="Trade Analyzer", icon="🔄")
        st.page_link("pages/6_profile_management.py", label="Profile", icon="👤")
        
        # Logout button
        if st.button("Logout", type="primary"):
            st.session_state.user = None
            st.session_state.uid = None
            st.rerun()
    
    # Main content
    st.title("Welcome to Sports Card Analyzer Pro")
    st.write(f"Hello, {st.session_state.user['displayName']}!")
    st.write("Use the sidebar to navigate to different sections of the application.")

if __name__ == "__main__":
    logger.debug("Starting application")
    main() 