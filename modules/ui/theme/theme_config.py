"""Theme configuration for the Sports Card Analyzer app."""

# Primary colors
PRIMARY_COLOR = "#000000"  # Black to match logo
SECONDARY_COLOR = "#2563EB"  # Modern blue accent
ACCENT_COLOR = "#4B5563"  # Neutral gray accent

# Background colors
BACKGROUND_COLOR = "#FFFFFF"  # Clean white
SECONDARY_BACKGROUND_COLOR = "#F8FAFC"  # Light gray
TERTIARY_BACKGROUND_COLOR = "#F1F5F9"  # Slightly darker gray

# Text colors
TEXT_COLOR = "#111827"  # Near black for better readability
SECONDARY_TEXT_COLOR = "#4B5563"  # Medium gray

# Logo configuration
LOGO_PATH = "static/images/logo.png"
LOGO_WIDTH = 200  # Width in pixels for sidebar
LOGO_HEIGHT = 50  # Height in pixels for sidebar
FAVICON_PATH = "static/icons/icon.svg"  # Path to the icon for favicon

# Theme configuration for Streamlit
STREAMLIT_THEME = {
    'primaryColor': '#FF4B4B',
    'backgroundColor': '#FFFFFF',
    'secondaryBackgroundColor': '#F0F2F6',
    'textColor': '#262730',
    'font': 'Inter'
}

# Custom CSS
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Base styles */
.stApp {
    font-family: 'Inter', sans-serif;
}

/* Header styles */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    letter-spacing: -0.02em;
}

/* Sidebar styles */
[data-testid="stSidebar"] {
    background-color: #FFFFFF;
    border-right: 1px solid rgba(0,0,0,0.1);
}

[data-testid="stSidebar"] [data-testid="stMarkdown"] {
    font-family: 'Inter', sans-serif;
}

/* Sidebar header (logo area) */
[data-testid="stSidebar"] .sidebar-header {
    padding: 1rem;
    border-bottom: 1px solid rgba(0,0,0,0.1);
    margin-bottom: 1rem;
    background: linear-gradient(to bottom, rgba(0,0,0,0.02), transparent);
}

/* Logo styles */
.logo-container {
    padding: 1rem;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
}

.logo-container.vertical {
    flex-direction: column;
    text-align: center;
}

.logo-container.horizontal {
    flex-direction: row;
}

.logo-container svg {
    color: var(--text-color, #000000);
    width: 48px !important;
    height: 48px !important;
}

.logo-text {
    font-family: 'Inter', sans-serif;
    font-size: 20px;
    font-weight: 700;
    color: var(--text-color, #000000);
    line-height: 1.2;
    white-space: nowrap;
}

/* Button styles */
.stButton > button {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    border-radius: 4px;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Card styles */
.card {
    background: white;
    border-radius: 8px;
    border: 1px solid rgba(0,0,0,0.1);
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition: all 0.2s ease;
}

.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

/* Input field styles */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stDateInput > div > div > input {
    font-family: 'Inter', sans-serif;
    border-radius: 4px;
}

/* Alert/message styles */
.stAlert {
    border-radius: 4px;
}

/* Text styles */
.stMarkdown {
    font-family: 'Inter', sans-serif;
}

/* Navigation styles */
.nav-item {
    padding: 0.5rem 1rem;
    margin: 0.25rem 0;
    border-radius: 4px;
    transition: all 0.2s ease;
}

.nav-item:hover {
    background-color: rgba(0,0,0,0.05);
}

.nav-item.active {
    background-color: var(--primary-color);
    color: white;
}

/* Dark mode overrides */
@media (prefers-color-scheme: dark) {
    .stApp {
        background-color: #111111;
    }

    [data-testid="stSidebar"] {
        background-color: #111111;
        border-right: 1px solid rgba(255,255,255,0.1);
    }

    [data-testid="stSidebar"] .sidebar-header {
        border-bottom: 1px solid rgba(255,255,255,0.1);
        background: linear-gradient(to bottom, rgba(255,255,255,0.02), transparent);
    }

    .card {
        background: #111111;
        border: 1px solid rgba(255,255,255,0.1);
    }

    .logo-container svg {
        color: var(--text-color, #FFFFFF);
    }
    
    .logo-text {
        color: var(--text-color, #FFFFFF);
    }

    .nav-item:hover {
        background-color: rgba(255,255,255,0.05);
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