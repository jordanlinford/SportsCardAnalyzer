import streamlit as st
import os
from typing import Optional

def inject_google_analytics():
    """Inject Google Analytics tracking code into the page."""
    try:
        tracking_id = st.secrets["google_analytics"]["tracking_id"]
        if not tracking_id:
            return
            
        ga_code = f"""
        <!-- Global site tag (gtag.js) - Google Analytics -->
        <script async src="https://www.googletagmanager.com/gtag/js?id={tracking_id}"></script>
        <script>
            window.dataLayer = window.dataLayer || [];
            function gtag(){{dataLayer.push(arguments);}}
            gtag('js', new Date());
            gtag('config', '{tracking_id}');
        </script>
        """
        
        st.components.v1.html(ga_code, height=0)
        
    except Exception as e:
        st.warning(f"Failed to inject Google Analytics: {str(e)}")

def initialize_analytics():
    """Initialize Google Analytics tracking."""
    try:
        # Get tracking ID from secrets
        tracking_id = st.secrets["google_analytics"]["tracking_id"]
        app_url = st.secrets["app"]["url"]
        app_name = st.secrets["app"]["name"]
        
        if not tracking_id:
            st.warning("Google Analytics tracking ID not found in secrets")
            return
            
        # Google Analytics tracking code
        ga_code = f"""
        <!-- Global site tag (gtag.js) - Google Analytics -->
        <script async src="https://www.googletagmanager.com/gtag/js?id={tracking_id}"></script>
        <script>
            window.dataLayer = window.dataLayer || [];
            function gtag(){{dataLayer.push(arguments);}}
            gtag('js', new Date());
            gtag('config', '{tracking_id}', {{
                'page_title': '{app_name}',
                'page_location': '{app_url}',
                'send_page_view': true
            }});
        </script>
        """
        
        # Inject the tracking code
        st.components.v1.html(ga_code, height=0)
        
    except Exception as e:
        st.warning(f"Failed to initialize Google Analytics: {str(e)}")

def track_event(category: str, action: str, label: Optional[str] = None, value: Optional[int] = None):
    """Track a custom event in Google Analytics."""
    try:
        tracking_id = st.secrets["google_analytics"]["tracking_id"]
        if not tracking_id:
            return
            
        event_data = {
            'event_category': category,
            'event_action': action
        }
        
        if label:
            event_data['event_label'] = label
        if value is not None:
            event_data['value'] = value
            
        # Create the event tracking code
        event_code = f"""
        <script>
            gtag('event', '{action}', {{
                'event_category': '{category}',
                'event_label': '{label if label else ""}',
                'value': {value if value is not None else 0}
            }});
        </script>
        """
        
        # Inject the event tracking code
        st.components.v1.html(event_code, height=0)
        
    except Exception as e:
        st.warning(f"Failed to track event: {str(e)}")

def track_page_view(page_name: str) -> None:
    """
    Tracks a page view in Google Analytics.
    
    Args:
        page_name (str): Name of the page being viewed
    """
    try:
        tracking_id = st.secrets["google_analytics"]["tracking_id"]
        if not tracking_id:
            return
            
        tracking_code = f"""
        <script>
            gtag('event', 'page_view', {{
                'page_title': '{page_name}',
                'page_location': window.location.href,
                'page_path': window.location.pathname
            }});
        </script>
        """
        
        st.components.v1.html(tracking_code, height=0)
    except Exception as e:
        st.warning(f"Failed to track page view: {str(e)}") 