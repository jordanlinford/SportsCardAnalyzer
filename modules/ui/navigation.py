import streamlit as st

class Navigation:
    @staticmethod
    def render_navigation():
        """Render the navigation menu with icons"""
        st.markdown("""
        <style>
        .nav-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 8px 12px;
            border-radius: 4px;
            transition: all 0.2s ease;
            cursor: pointer;
            text-decoration: none;
            color: inherit;
        }
        
        .nav-item:hover {
            background-color: rgba(0,0,0,0.05);
        }
        
        .nav-item.active {
            background-color: rgba(0,0,0,0.1);
        }
        
        .nav-icon {
            width: 24px;
            height: 24px;
        }
        
        .nav-divider {
            height: 1px;
            background-color: rgba(0,0,0,0.1);
            margin: 8px 0;
        }
        
        @media (prefers-color-scheme: dark) {
            .nav-item:hover {
                background-color: rgba(255,255,255,0.1);
            }
            
            .nav-item.active {
                background-color: rgba(255,255,255,0.15);
            }
            
            .nav-divider {
                background-color: rgba(255,255,255,0.1);
            }
        }
        </style>
        """, unsafe_allow_html=True)

        pages = {
            "Market Analysis": {
                "icon": "market_analyzer",
                "path": "pages/1_market_analysis.py"
            },
            "Price Predictor": {
                "icon": "price_predictor",
                "path": "pages/2_price_predictor.py"
            },
            "Collection Manager": {
                "icon": "collection_manager",
                "path": "pages/3_collection_manager.py"
            },
            "Display Case": {
                "icon": "display_case",
                "path": "pages/4_display_case.py"
            },
            "Trade Analyzer": {
                "icon": "trade_analyzer",
                "path": "pages/5_trade_analyzer.py"
            }
        }

        current_page = st.session_state.get("current_page", "Market Analysis")

        # Render main navigation items
        for page_name, page_info in pages.items():
            with open(f"static/icons/{page_info['icon']}.svg", "r") as f:
                icon_svg = f.read()
            
            is_active = current_page == page_name
            st.markdown(
                f'''
                <a href="/{page_info['path']}" target="_self" class="nav-item{'active' if is_active else ''}">
                    <div class="nav-icon">{icon_svg}</div>
                    <div>{page_name}</div>
                </a>
                ''',
                unsafe_allow_html=True
            )
        
        # Add divider before profile
        st.markdown('<div class="nav-divider"></div>', unsafe_allow_html=True)
        
        # Add profile navigation item
        with open("static/icons/profile.svg", "r") as f:
            profile_icon = f.read()
        
        is_profile_active = current_page == "Profile"
        st.markdown(
            f'''
            <a href="/pages/6_profile_management.py" target="_self" class="nav-item{'active' if is_profile_active else ''}">
                <div class="nav-icon">{profile_icon}</div>
                <div>Profile</div>
            </a>
            ''',
            unsafe_allow_html=True
        ) 