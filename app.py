import streamlit as st
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).parent.absolute()
sys.path.append(str(project_root))

# Configure the page
st.set_page_config(
    page_title="Sports Card Analyzer Pro",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for mobile responsiveness
st.markdown("""
<style>
    /* Make content width responsive */
    .block-container {
        max-width: 100% !important;
        padding-top: 1rem !important;
        padding-right: 1rem !important;
        padding-left: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* Adjust header sizes for mobile */
    .main h1 {
        font-size: calc(1.5rem + 1vw) !important;
    }
    .main h2 {
        font-size: calc(1.2rem + 0.8vw) !important;
    }
    .main h3 {
        font-size: calc(1rem + 0.6vw) !important;
    }
    
    /* Make images responsive */
    img {
        max-width: 100% !important;
        height: auto !important;
    }
    
    /* Adjust button sizes for mobile */
    .stButton > button {
        width: 100% !important;
        padding: 0.5rem !important;
    }
    
    /* Adjust input fields for mobile */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input {
        min-height: 40px !important;
    }
    
    /* Adjust selectbox for mobile */
    .stSelectbox > div > div > select {
        min-height: 40px !important;
    }
    
    /* Make dataframes scrollable horizontally on mobile */
    .stDataFrame {
        overflow-x: auto !important;
    }
    
    /* Adjust metrics for mobile */
    .stMetric {
        padding: 0.5rem !important;
    }
    
    /* Adjust column gaps */
    .row-widget.stHorizontal > div {
        gap: 0.5rem !important;
    }
    
    /* Make tabs more touch-friendly */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem !important;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 0.5rem 1rem !important;
        white-space: normal !important;
    }
    
    /* Adjust plots for mobile */
    .js-plotly-plot {
        max-width: 100% !important;
    }
    
    /* Adjust multiselect for mobile */
    .stMultiSelect > div {
        min-height: 40px !important;
    }
    
    /* Make forms more mobile-friendly */
    .stForm > div {
        padding: 1rem !important;
    }
    
    @media (max-width: 640px) {
        /* Additional mobile-specific adjustments */
        .main .block-container {
            padding: 0.5rem !important;
        }
        
        /* Stack columns on mobile */
        [data-testid="column"] {
            width: 100% !important;
            margin-bottom: 1rem !important;
        }
        
        /* Adjust metric size on mobile */
        .stMetric {
            width: 100% !important;
        }
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.title("Welcome to Sports Card Analyzer Pro")
    st.write("Please select a page from the sidebar to get started.")
    
    # Initialize session state for user if not exists
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'uid' not in st.session_state:
        st.session_state.uid = None
    
    # If user is not logged in, redirect to login page
    if not st.session_state.user:
        st.switch_page("pages/login.py")
    
    # Add logout button to sidebar
    with st.sidebar:
        if st.button("Logout", type="primary"):
            # Clear session state
            st.session_state.user = None
            st.session_state.uid = None
            st.session_state.clear()
            # Redirect to login page
            st.switch_page("pages/login.py")
    
    # Display app features
    st.markdown("""
    ### Features:
    
    1. **Market Analysis**
       - Search for cards
       - View price trends
       - Get market insights
    
    2. **Collection Management**
       - Track your cards
       - Monitor value changes
       - Organize by display cases
    
    3. **Price Predictions**
       - Get price forecasts
       - Track market trends
       - Make informed decisions
    
    4. **Profit Calculator**
       - Calculate potential returns
       - Track ROI
       - Plan your investments
    """)

if __name__ == "__main__":
    main() 