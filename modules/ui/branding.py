from modules.ui.theme.theme_config import ThemeConfig

class BrandingComponent:
    """Handles all branding-related components and styling."""
    
    @staticmethod
    def display_horizontal_logo():
        """Display horizontal text only."""
        st.markdown("""
            <div class="logo-container horizontal">
                <h1 class="logo-text">Sports Card Analyzer</h1>
            </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def display_vertical_logo():
        """Display vertical text only."""
        st.markdown("""
            <div class="logo-container vertical">
                <h1 class="logo-text">Sports Card Analyzer</h1>
            </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def display_icon_only():
        """Display nothing."""
        pass
    
    @staticmethod
    def display_dark_mode_logo():
        """Display text optimized for dark mode."""
        st.markdown("""
            <div class="logo-container dark-mode">
                <h1 class="logo-text">Sports Card Analyzer</h1>
            </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def add_branding_styles():
        """Add necessary CSS styles for branding components."""
        theme_vars = ThemeConfig.get_css_variables()
        st.markdown(f"""
            <style>
                /* Theme variables */
                :root {{
                    --primary-color: {theme_vars['--primary-color']};
                    --background-color: {theme_vars['--background-color']};
                    --secondary-background-color: {theme_vars['--secondary-background-color']};
                    --text-color: {theme_vars['--text-color']};
                }}
                
                /* Logo container styles */
                .logo-container {{
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 100%;
                    margin: 0;
                    padding: 1rem;
                }}
                
                .logo-container.vertical {{
                    flex-direction: column;
                    text-align: center;
                }}
                
                .logo-container.horizontal {{
                    flex-direction: row;
                }}
                
                /* Logo text styles */
                .logo-text {{
                    font-size: 2.5rem;
                    font-weight: 700;
                    color: var(--text-color);
                    margin: 0;
                    line-height: 1.2;
                    text-align: center;
                }}
                
                /* Dark mode styles */
                .logo-container.dark-mode .logo-text {{
                    color: #ffffff;
                }}
                
                /* Mobile responsiveness */
                @media (max-width: 768px) {{
                    .logo-text {{
                        font-size: 2rem;
                    }}
                }}
            </style>
        """, unsafe_allow_html=True) 