"""Theme manager for the Sports Card Analyzer app."""
import os
import streamlit as st
from .theme_config import STREAMLIT_THEME, CUSTOM_CSS, LOGO_PATH, LOGO_WIDTH, LOGO_HEIGHT

class ThemeManager:
    @staticmethod
    def apply_theme_styles():
        """Apply the custom theme styles to the Streamlit app."""
        # Apply custom CSS
        st.markdown(f'<style>{CUSTOM_CSS}</style>', unsafe_allow_html=True)
        
        # Set theme configuration
        st.markdown(
            f"""
            <style>
                .stApp {{
                    background-color: {STREAMLIT_THEME['backgroundColor']};
                }}
            </style>
            """,
            unsafe_allow_html=True
        )
    
    @staticmethod
    def display_logo():
        """Display the application logo with enhanced styling."""
        st.markdown(
            """
            <style>
                .logo-container {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    padding: 1rem 0;
                    margin-bottom: 1rem;
                }
                .logo-container img {
                    max-width: 100%;
                    height: auto;
                    transition: transform 0.2s ease;
                }
                .logo-container img:hover {
                    transform: scale(1.02);
                }
                @media (max-width: 640px) {
                    .logo-container {
                        padding: 0.5rem 0;
                    }
                }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        if os.path.exists(LOGO_PATH):
            st.markdown(
                f"""
                <div class="logo-container">
                    <img src="{LOGO_PATH}" alt="Sports Card Analyzer Logo" width="{LOGO_WIDTH}" height="{LOGO_HEIGHT}">
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div class="logo-container">
                    <h1 style="color: {STREAMLIT_THEME['primaryColor']}; font-size: 2rem; margin: 0;">Sports Card Analyzer</h1>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    @staticmethod
    def styled_card():
        """Create a styled card container that works as a context manager."""
        container = st.container()
        container.markdown("<div class='card'>", unsafe_allow_html=True)
        
        class CardContext:
            def __init__(self, container):
                self.container = container
            
            def __enter__(self):
                return self.container
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                self.container.markdown("</div>", unsafe_allow_html=True)
        
        return CardContext(container)
    
    @staticmethod
    def styled_header(text, level=1):
        """Create a styled header."""
        st.markdown(f"<h{level}>{text}</h{level}>", unsafe_allow_html=True)
    
    @staticmethod
    def styled_button(label, key=None, help=None):
        """Create a styled button."""
        return st.button(
            label,
            key=key,
            help=help,
            use_container_width=True
        ) 