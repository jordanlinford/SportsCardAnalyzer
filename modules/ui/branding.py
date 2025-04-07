import streamlit as st

class BrandingComponent:
    @staticmethod
    def logo_svg(color="#000000"):
        """Generate the SVG logo with the specified color."""
        return f"""
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="48" height="48" rx="8" fill="{color}"/>
            <path d="M12 24L24 12L36 24L24 36L12 24Z" fill="white"/>
        </svg>
        """

    @staticmethod
    def display_horizontal_logo():
        """Display the horizontal logo with text."""
        st.markdown(f"""
        <div class="horizontal-logo" style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0;">
            {BrandingComponent.logo_svg()}
            <span style="font-family: 'Inter', sans-serif; font-size: 1.25rem; font-weight: 600; color: var(--text-color, #000000);">Sports Card Analyzer</span>
        </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def display_vertical_logo():
        """Display the vertical logo with text."""
        st.markdown(f"""
        <div class="vertical-logo" style="display: flex; flex-direction: column; align-items: center; gap: 0.5rem; padding: 1rem 0;">
            {BrandingComponent.logo_svg()}
            <span style="font-family: 'Inter', sans-serif; font-size: 1.5rem; font-weight: 600; color: var(--text-color, #000000);">Sports Card Analyzer</span>
        </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def display_icon_only():
        """Display just the icon without text."""
        st.markdown(f"""
        <div class="icon-only" style="display: flex; align-items: center; justify-content: center; padding: 0.5rem 0;">
            {BrandingComponent.logo_svg()}
        </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def display_dark_mode_logo():
        """Display the logo in dark mode colors."""
        st.markdown(f"""
        <div class="dark-mode-logo" style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0;">
            {BrandingComponent.logo_svg("#FFFFFF")}
            <span style="font-family: 'Inter', sans-serif; font-size: 1.25rem; font-weight: 600; color: #FFFFFF;">Sports Card Analyzer</span>
        </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def add_branding_styles():
        """Add the necessary CSS styles for branding."""
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        /* Base styles */
        .horizontal-logo, .vertical-logo, .icon-only, .dark-mode-logo {
            transition: all 0.3s ease;
        }
        
        /* Persistent logo styles */
        .stApp > header {
            background-color: white;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .stApp > header .horizontal-logo {
            margin: 0;
            padding: 0;
        }
        
        /* Sidebar logo styles */
        .stSidebar .horizontal-logo {
            margin-bottom: 1rem;
            padding: 0.5rem;
            border-bottom: 1px solid rgba(0,0,0,0.1);
        }
        
        /* Dark mode overrides */
        @media (prefers-color-scheme: dark) {
            .stApp > header {
                background-color: #111111;
            }
            
            .stSidebar .horizontal-logo {
                border-bottom-color: rgba(255,255,255,0.1);
            }
        }
        </style>
        """, unsafe_allow_html=True) 