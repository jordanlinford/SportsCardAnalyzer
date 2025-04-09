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
        """Display the application logo."""
        if os.path.exists(LOGO_PATH):
            st.image(
                LOGO_PATH,
                width=LOGO_WIDTH,
                caption=None,
                use_container_width=False
            )
        else:
            st.markdown(
                f"""
                <div class="logo-container">
                    <h1 style="color: {STREAMLIT_THEME['primaryColor']}">Sports Card Analyzer</h1>
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