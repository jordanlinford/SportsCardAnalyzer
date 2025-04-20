"""Theme configuration for the Sports Card Analyzer app."""

# Primary colors
PRIMARY_COLOR = "#1A365D"  # Deep navy blue
SECONDARY_COLOR = "#2B6CB0"  # Rich blue
ACCENT_COLOR = "#E2E8F0"  # Light blue-gray

# Background colors
BACKGROUND_COLOR = "#FFFFFF"  # Clean white
SECONDARY_BACKGROUND_COLOR = "#F7FAFC"  # Very light blue-gray
TERTIARY_BACKGROUND_COLOR = "#EDF2F7"  # Light blue-gray

# Text colors
TEXT_COLOR = "#1A202C"  # Dark blue-gray
SECONDARY_TEXT_COLOR = "#4A5568"  # Medium blue-gray

# Logo configuration
LOGO_PATH = "static/images/logo.png"
LOGO_WIDTH = 200  # Width in pixels for sidebar
LOGO_HEIGHT = 50  # Height in pixels for sidebar
FAVICON_PATH = "static/icons/icon.svg"  # Path to the icon for favicon

# Theme configuration for Streamlit
STREAMLIT_THEME = {
    'primaryColor': PRIMARY_COLOR,
    'backgroundColor': BACKGROUND_COLOR,
    'secondaryBackgroundColor': SECONDARY_BACKGROUND_COLOR,
    'textColor': TEXT_COLOR,
    'font': 'Inter'
}

# Custom CSS
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Theme variables */
:root {
    --primary-color: #1A365D;
    --secondary-color: #2B6CB0;
    --accent-color: #E2E8F0;
    --background-color: #FFFFFF;
    --secondary-background-color: #F7FAFC;
    --text-color: #1A202C;
    --secondary-text-color: #4A5568;
    --border-color: #E2E8F0;
    --success-color: #38A169;
    --warning-color: #D69E2E;
    --error-color: #E53E3E;
    --info-color: #3182CE;
}

/* Base styles */
.stApp {
    font-family: 'Inter', sans-serif;
    background-color: var(--background-color);
}

/* Card styles */
.card {
    background-color: var(--background-color);
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
    border: 1px solid var(--border-color);
}

/* Button styles */
.stButton > button {
    background-color: var(--primary-color);
    color: white;
    border-radius: 6px;
    padding: 0.5rem 1rem;
    font-weight: 500;
    transition: all 0.2s;
}

.stButton > button:hover {
    background-color: var(--secondary-color);
    transform: translateY(-1px);
}

/* Metric styles */
[data-testid="stMetricValue"] {
    font-size: 2rem;
    font-weight: 700;
    color: var(--primary-color);
}

[data-testid="stMetricLabel"] {
    font-size: 1rem;
    color: var(--secondary-text-color);
}

/* Header styles */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--text-color);
}

/* Sidebar styles */
[data-testid="stSidebar"] {
    background-color: var(--background-color);
    border-right: 1px solid var(--border-color);
    padding: 1.5rem;
}

[data-testid="stSidebar"] [data-testid="stMarkdown"] {
    font-family: 'Inter', sans-serif;
}

/* Sidebar navigation */
[data-testid="stSidebar"] .sidebar-content {
    margin-top: 2rem;
}

[data-testid="stSidebar"] .sidebar-nav-item {
    padding: 0.75rem 1rem;
    margin: 0.25rem 0;
    border-radius: 6px;
    transition: all 0.2s;
}

[data-testid="stSidebar"] .sidebar-nav-item:hover {
    background-color: var(--accent-color);
}

/* Form styles */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {
    border-radius: 6px;
    border: 1px solid var(--border-color);
    padding: 0.5rem;
}

/* Alert styles */
.stAlert {
    border-radius: 6px;
    padding: 1rem;
}

/* Mobile-friendly adjustments */
@media (max-width: 640px) {
    .stForm {
        width: 100% !important;
    }
    
    .js-plotly-plot {
        height: 300px !important;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
    }
    
    .card-image {
        max-width: 200px !important;
        margin: 0 auto !important;
        display: block !important;
    }
}
"""

class ThemeConfig:
    """Configuration for application themes."""
    
    # Light theme colors
    LIGHT_THEME = {
        "primaryColor": "#FF4B4B",
        "backgroundColor": "#FFFFFF",
        "secondaryBackgroundColor": "#F0F2F6",
        "textColor": "#262730",
        "font": "sans serif"
    }
    
    # Dark theme colors
    DARK_THEME = {
        "primaryColor": "#FF4B4B",
        "backgroundColor": "#0E1117",
        "secondaryBackgroundColor": "#262730",
        "textColor": "#FAFAFA",
        "font": "sans serif"
    }
    
    @staticmethod
    def get_theme(is_dark_mode=False):
        """Get theme configuration based on mode."""
        return ThemeConfig.DARK_THEME if is_dark_mode else ThemeConfig.LIGHT_THEME
    
    @staticmethod
    def get_css_variables(is_dark_mode=False):
        """Get CSS variables for the theme."""
        theme = ThemeConfig.get_theme(is_dark_mode)
        return {
            "--primary-color": theme["primaryColor"],
            "--background-color": theme["backgroundColor"],
            "--secondary-background-color": theme["secondaryBackgroundColor"],
            "--text-color": theme["textColor"]
        } 