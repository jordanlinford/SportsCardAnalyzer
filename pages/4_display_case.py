import streamlit as st
import pandas as pd
from PIL import Image
import io
import base64
import json
from datetime import datetime
import os
import zipfile
from pathlib import Path
from modules.display_case.manager import DisplayCaseManager
import ast
from modules.database.service import DatabaseService

st.set_page_config(
    page_title="Display Case - Sports Card Analyzer Pro",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

backgrounds = {
    "Minimal Dark": {
        "gradient": "linear-gradient(135deg, #1c1c1c, #2a2a2a)",
        "text": "#ffffff",
        "text_shadow": "2px 2px 4px rgba(0,0,0,0.5)"
    },
    "Steel Gray": {
        "gradient": "linear-gradient(135deg, #3e3e3e, #1f1f1f)",
        "text": "#ffffff",
        "text_shadow": "2px 2px 4px rgba(0,0,0,0.5)"
    },
    "Soft Light": {
        "gradient": "linear-gradient(135deg, #f0f0f0, #e0e0e0)",
        "text": "#000000",
        "text_shadow": "none"
    },
    "Blue Night": {
        "gradient": "linear-gradient(135deg, #1a2a6c, #b21f1f, #fdbb2d)",
        "text": "#ffffff",
        "text_shadow": "2px 2px 4px rgba(0,0,0,0.5)"
    }
}

def init_session_state():
    if 'display_case_manager' not in st.session_state:
        st.session_state.display_case_manager = None
    if 'collection' not in st.session_state:
        st.session_state.collection = pd.DataFrame(columns=[
            'player_name', 'year', 'card_set', 'card_number', 'variation',
            'condition', 'purchase_price', 'purchase_date', 'current_value',
            'last_updated', 'notes', 'photo', 'roi', 'tags'
        ])
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'uid' not in st.session_state:
        st.session_state.uid = None
    if 'bg_choice' not in st.session_state:
        st.session_state.bg_choice = "Minimal Dark"
    if 'last_uid' not in st.session_state:
        st.session_state.last_uid = None

def display_case_grid(display_case):
    """Display cards in a grid format, dynamically filtered from current collection"""
    if not display_case:
        st.info("No display case selected")
        return

    if not display_case.get('tags'):
        st.info("No tags defined for this display case")
        return

    # Get the current theme settings
    theme = backgrounds[st.session_state.bg_choice]
    text_color = theme["text"]
    text_shadow = theme["text_shadow"]
    card_bg = "rgba(0, 0, 0, 0.7)" if text_color == "#ffffff" else "rgba(255, 255, 255, 0.9)"

    try:
        # Check if we have cards directly in the display case
        if display_case.get('cards') and len(display_case['cards']) > 0:
            # Use the cards directly from the display case
            valid_cards = display_case['cards']
            print(f"Using {len(valid_cards)} cards directly from display case")
        else:
            # Dynamically filter cards from current collection based on tags
            current_tags = display_case['tags']
            print(f"Filtering cards with tags: {current_tags}")
            
            # Use the DisplayCaseManager's tag matching logic
            if st.session_state.display_case_manager and not st.session_state.collection.empty:
                try:
                    valid_cards = st.session_state.display_case_manager._filter_cards_by_tags(current_tags)
                    print(f"Found {len(valid_cards)} cards matching tags")
                except Exception as e:
                    st.error(f"Error filtering cards: {str(e)}")
                    print(f"Error in display_case_grid: {str(e)}")
                    import traceback
                    print(f"Traceback: {traceback.format_exc()}")
                    valid_cards = []
            else:
                valid_cards = []

        if not valid_cards:
            st.info("No cards found matching the selected tags")
            return

        # Create a container for the grid
        with st.container():
            # Create a grid of columns
            cols = st.columns(3)
            
            for idx, card in enumerate(valid_cards):
                col = cols[idx % 3]  # Cycle through columns
                with col:
                    with st.container():
                        # Display the card image
                        if card.get('photo'):
                            try:
                                # Handle different image formats
                                if isinstance(card['photo'], str):
                                    if card['photo'].startswith('data:image'):
                                        # Handle base64 encoded images
                                        st.image(card['photo'], use_column_width=True)
                                    else:
                                        # Handle URL or file path
                                        st.image(card['photo'], use_column_width=True)
                                else:
                                    st.error("Invalid image format")
                            except Exception as e:
                                st.error(f"Failed to load image: {str(e)}")
                        
                        # Ensure all card data is properly formatted
                        try:
                            # Format numeric values
                            current_value = float(card.get('current_value', 0))
                            roi = float(card.get('roi', 0))
                            
                            # Get and normalize tags
                            card_tags = card.get('tags', [])
                            if isinstance(card_tags, str):
                                if card_tags.startswith('[') and card_tags.endswith(']'):
                                    try:
                                        card_tags = ast.literal_eval(card_tags)
                                    except:
                                        card_tags = [t.strip() for t in card_tags.strip('[]').split(',') if t.strip()]
                                else:
                                    card_tags = [t.strip() for t in card_tags.split(',') if t.strip()]
                            elif not isinstance(card_tags, list):
                                card_tags = []
                            
                            # Display card details with proper styling
                            st.markdown(f"""
                            <div style="background: {card_bg}; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
                                <h4 style="color: {text_color}; margin-bottom: 0.5rem; text-shadow: {text_shadow}; font-weight: bold;">{card.get('player_name', 'Unknown Player')} {card.get('year', '')}</h4>
                                <p style="margin: 0.25rem 0; text-shadow: {text_shadow};">{card.get('card_set', 'Unknown Set')} #{card.get('card_number', '')}</p>
                                <p style="margin: 0.25rem 0; text-shadow: {text_shadow};">Condition: {card.get('condition', 'Unknown')}</p>
                                <p style="margin: 0.25rem 0; text-shadow: {text_shadow}; font-weight: bold;">Value: ${current_value:,.2f}</p>
                                <p style="margin: 0.25rem 0; text-shadow: {text_shadow};">ROI: {roi:+.1f}%</p>
                                <p style="margin: 0.25rem 0; text-shadow: {text_shadow};">Tags: {', '.join(card_tags)}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Error formatting card data: {str(e)}")
                            print(f"Error formatting card {idx}: {str(e)}")
                            import traceback
                            print(f"Traceback: {traceback.format_exc()}")

    except Exception as e:
        st.error(f"Error displaying cards: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")

def export_display_case(display_case):
    """Export display case data as a JSON file with enhanced card details."""
    try:
        export_data = {
            'display_case': {
                'name': display_case['name'],
                'description': display_case['description'],
                'tags': display_case['tags'],
                'created_date': display_case['created_date'],
                'total_value': display_case['total_value'],
                'total_cards': len(display_case['cards'])
            },
            'cards': []
        }
        
        for card in display_case['cards']:
            # Create a new dictionary with only serializable data
            card_data = {
                'player_name': str(card.get('player_name', '')),
                'year': str(card.get('year', '')),
                'card_set': str(card.get('card_set', '')),
                'card_number': str(card.get('card_number', '')),
                'variation': str(card.get('variation', '')),
                'condition': str(card.get('condition', '')),  # Convert CardCondition to string
                'current_value': float(card.get('current_value', 0)),
                'purchase_price': float(card.get('purchase_price', 0)),
                'purchase_date': str(card.get('purchase_date', '')),
                'roi': float(card.get('roi', 0)),
                'notes': str(card.get('notes', '')),
                'photo': str(card.get('photo', '')),
                'tags': [str(tag) for tag in card.get('tags', [])]
            }
            export_data['cards'].append(card_data)
        
        # Format the JSON with indentation for better readability
        return json.dumps(export_data, indent=2)
    except Exception as e:
        print(f"Error in export_display_case: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return json.dumps({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, indent=2)

def create_backup():
    """Create a backup of all display cases and save as a zip file on desktop."""
    try:
        # Get the desktop path
        desktop = str(Path.home() / "Desktop")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(desktop, f"Sports_Card_Analyzer_Pro_Backup_{timestamp}")
        
        # Create backup directory
        os.makedirs(backup_dir, exist_ok=True)
        
        # Export each display case
        for case_name, display_case in st.session_state.display_case_manager.display_cases.items():
            # Create a safe filename
            safe_name = case_name.lower().replace(' ', '_')
            file_path = os.path.join(backup_dir, f"{safe_name}.json")
            
            # Export the display case data
            export_data = export_display_case(display_case)
            
            # Save to file
            with open(file_path, 'w') as f:
                f.write(export_data)
        
        # Create zip file
        zip_path = f"{backup_dir}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, backup_dir)
                    zipf.write(file_path, arcname)
        
        # Clean up the backup directory
        for root, dirs, files in os.walk(backup_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(backup_dir)
        
        return zip_path
    except Exception as e:
        st.error(f"Failed to create backup: {str(e)}")
        return None

def main():
    st.title("Display Case")
    init_session_state()

    # Check if user has changed
    if st.session_state.uid != st.session_state.last_uid:
        print(f"User changed from {st.session_state.last_uid} to {st.session_state.uid}")
        st.session_state.last_uid = st.session_state.uid
        st.session_state.display_case_manager = None
        # Load collection from Firebase first
        if st.session_state.uid:
            st.session_state.collection = DatabaseService.get_user_collection(st.session_state.uid)
            if st.session_state.collection is None or len(st.session_state.collection) == 0:
                st.session_state.collection = pd.DataFrame(columns=[
                    'player_name', 'year', 'card_set', 'card_number', 'variation',
                    'condition', 'purchase_price', 'purchase_date', 'current_value',
                    'last_updated', 'notes', 'photo', 'roi', 'tags'
                ])
        else:
            st.session_state.collection = pd.DataFrame(columns=[
                'player_name', 'year', 'card_set', 'card_number', 'variation',
                'condition', 'purchase_price', 'purchase_date', 'current_value',
                'last_updated', 'notes', 'photo', 'roi', 'tags'
            ])

    with st.sidebar:
        st.subheader("Display Case Settings")
        bg_choice = st.selectbox("Background Theme", list(backgrounds.keys()))
        st.session_state.bg_choice = bg_choice
        enable_comments = st.checkbox("Enable Comments", value=True)
        
        # Add a refresh button
        if st.button("Refresh All Display Cases"):
            if st.session_state.display_case_manager:
                st.info("Refreshing all display cases...")
                st.session_state.display_case_manager.load_display_cases(force_refresh=True)
                st.success("Display cases refreshed successfully!")
                st.rerun()
            else:
                st.error("Display case manager not initialized")

    # Set theme variables based on selected background
    theme = backgrounds[bg_choice]
    bg_gradient = theme["gradient"]
    text_color = theme["text"]
    text_shadow = theme["text_shadow"]
    card_bg = "rgba(0, 0, 0, 0.7)" if text_color == "#ffffff" else "rgba(255, 255, 255, 0.9)"

    # Apply CSS with proper theme handling
    st.markdown(f"""
    <style>
    /* Main app background */
    .stApp {{
        background: {bg_gradient};
        background-attachment: fixed;
        background-size: cover;
        background-position: center;
        color: {text_color};
        text-shadow: {text_shadow};
    }}
    
    /* Streamlit text elements */
    .stTitle, .stSubheader, .stMarkdown, .stText, .stSelectbox label, 
    .stCheckbox label, .stTextInput label, .stTextArea label, 
    .stMultiSelect label, .stTabs [data-baseweb="tab-list"] button {{
        color: {text_color} !important;
        text-shadow: {text_shadow} !important;
    }}
    
    /* Streamlit headings */
    h1, h2, h3, h4, h5, h6 {{
        color: {text_color} !important;
        text-shadow: {text_shadow} !important;
    }}
    
    /* Streamlit form elements */
    .stForm {{
        background: {card_bg};
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }}
    
    /* Display case grid */
    .display-case-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1.5rem;
        padding: 1rem;
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: thin;
        scrollbar-color: rgba(255, 255, 255, 0.3) transparent;
    }}
    
    /* Custom scrollbar for webkit browsers */
    .display-case-grid::-webkit-scrollbar {{
        height: 8px;
    }}
    
    .display-case-grid::-webkit-scrollbar-track {{
        background: transparent;
    }}
    
    .display-case-grid::-webkit-scrollbar-thumb {{
        background-color: rgba(255, 255, 255, 0.3);
        border-radius: 4px;
    }}
    
    /* Display case cards */
    .display-case-card {{
        background: {card_bg};
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        transition: transform 0.2s;
        color: {text_color};
        min-width: 300px;
        max-width: 400px;
        margin: 0 auto;
    }}
    
    .display-case-card:hover {{
        transform: scale(1.03);
        box-shadow: 0 6px 20px rgba(255, 215, 0, 0.3);
    }}
    
    /* Card images */
    .display-case-image {{
        width: 100%;
        height: 400px;
        object-fit: contain;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        background: rgba(0, 0, 0, 0.1);
    }}
    
    /* Container for the grid */
    .stContainer {{
        width: 100%;
        overflow-x: auto;
        padding: 0;
        margin: 0;
    }}
    
    /* Ensure columns maintain equal width */
    .row-widget.stHorizontal {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1.5rem;
        width: 100%;
        min-width: 900px;
    }}
    
    /* Responsive adjustments */
    @media (max-width: 768px) {{
        .display-case-grid {{
            padding: 0.5rem;
        }}
        
        .display-case-card {{
            min-width: 250px;
        }}
        
        .display-case-image {{
            height: 350px;
        }}
    }}
    
    /* Streamlit sidebar */
    .css-1d391kg {{
        background: {card_bg} !important;
    }}
    
    /* Sidebar text styling */
    .css-1d391kg .stSubheader,
    .css-1d391kg .stSelectbox label,
    .css-1d391kg .stCheckbox label,
    .css-1d391kg .stMarkdown,
    .css-1d391kg .stText,
    .css-1d391kg .stTextInput label,
    .css-1d391kg .stTextArea label,
    .css-1d391kg .stMultiSelect label {{
        color: {text_color} !important;
        text-shadow: {text_shadow} !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        font-size: 14px !important;
        line-height: 1.5 !important;
    }}
    
    /* Sidebar selectbox and checkbox styling */
    .css-1d391kg .stSelectbox select,
    .css-1d391kg .stCheckbox input {{
        background: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {text_color} !important;
        border-radius: 4px !important;
        padding: 4px 8px !important;
    }}
    
    /* Sidebar hover effects */
    .css-1d391kg .stSelectbox select:hover,
    .css-1d391kg .stCheckbox input:hover {{
        border-color: #4CAF50 !important;
    }}
    
    /* Streamlit tabs */
    .stTabs [data-baseweb="tab-list"] {{
        background: {card_bg} !important;
    }}
    
    /* Streamlit buttons */
    .stButton button {{
        background: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {text_color} !important;
    }}
    
    /* Streamlit inputs */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {{
        background: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {text_color} !important;
    }}

    /* Metric container */
    .stMetric {{
        background: {card_bg} !important;
        padding: 1rem !important;
        border-radius: 10px !important;
    }}
    
    /* Metric value and label */
    .stMetric [data-testid="stMetricValue"],
    .stMetric [data-testid="stMetricLabel"],
    .stMetric div,
    .stMetric span,
    .stMetric p {{
        color: {text_color} !important;
        text-shadow: {text_shadow} !important;
    }}
    
    /* Info text and share link */
    .stInfo, .stInfo a, .stInfo p, .stInfo span, .stInfo div {{
        background: {card_bg} !important;
        color: {text_color} !important;
        text-shadow: {text_shadow} !important;
    }}
    
    /* Download button text */
    .stDownloadButton button {{
        background: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {text_color} !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    if not st.session_state.user:
        st.switch_page("pages/login.py")

    if st.session_state.display_case_manager is None and st.session_state.uid:
        print(f"Initializing DisplayCaseManager for user {st.session_state.uid}")
        st.session_state.display_case_manager = DisplayCaseManager(
            st.session_state.uid,
            st.session_state.collection
        )
        st.session_state.display_case_manager.load_display_cases(force_refresh=True)

    tab1, tab2 = st.tabs(["Create Display Case", "View Display Cases"])

    with tab1:
        st.subheader("Create New Display Case")
        if st.session_state.display_case_manager is None:
            st.error("Display case manager not initialized. Please refresh the page.")
        else:
            # Get all available tags
            all_tags = st.session_state.display_case_manager.get_all_tags()
            
            if not all_tags:
                st.warning("No tags found in your collection. Please add tags to your cards first.")
            else:
                with st.form("create_display_case"):
                    col1, col2 = st.columns(2)
                    with col1:
                        name = st.text_input("Display Case Name", help="Enter a unique name for your display case")
                    with col2:
                        description = st.text_area("Description", help="Describe what this display case represents")
                    
                    # Tag selection with better organization
                    st.subheader("Select Tags")
                    st.markdown("Select one or more tags to filter cards for this display case")
                    
                    # Group tags by first letter for better organization
                    tag_groups = {}
                    for tag in all_tags:
                        first_letter = tag[0].upper() if tag else '#'
                        if first_letter not in tag_groups:
                            tag_groups[first_letter] = []
                        tag_groups[first_letter].append(tag)
                    
                    # Create columns for tag groups
                    cols = st.columns(min(3, len(tag_groups)))
                    selected_tags = []
                    
                    for i, (letter, tags) in enumerate(sorted(tag_groups.items())):
                        with cols[i % len(cols)]:
                            st.markdown(f"**{letter}**")
                            for tag in sorted(tags):
                                if st.checkbox(tag, key=f"tag_{tag}"):
                                    selected_tags.append(tag)
                    
                    submitted = st.form_submit_button("Create Display Case")
                    if submitted:
                        if name and selected_tags:
                            new_case = st.session_state.display_case_manager.create_display_case(
                                name, description, selected_tags
                            )
                            if new_case:
                                st.success(f"Display case '{name}' created successfully with {len(new_case['cards'])} cards!")
                                st.balloons()
                            else:
                                st.error("Failed to create display case. Please try again.")
                        else:
                            st.error("Please provide a name and select at least one tag.")

    with tab2:
        display_cases = st.session_state.display_case_manager.display_cases
        if display_cases:
            selected_case = st.selectbox("Select Display Case", options=list(display_cases.keys()))
            if selected_case:
                display_case = display_cases[selected_case]
                st.subheader(display_case['name'])
                st.markdown(f"*{display_case['description']}*")
                col1, col2 = st.columns(2)
                with col1:
                    # Create metrics with custom HTML for better control
                    st.markdown(f"""
                    <div style="background: {card_bg}; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
                        <div style="color: {text_color}; text-shadow: {text_shadow}; font-size: 0.9rem;">Total Cards</div>
                        <div style="color: {text_color}; text-shadow: {text_shadow}; font-size: 1.2rem; font-weight: bold;">{len(display_case['cards'])}</div>
                    </div>
                    <div style="background: {card_bg}; padding: 1rem; border-radius: 10px;">
                        <div style="color: {text_color}; text-shadow: {text_shadow}; font-size: 0.9rem;">Tags</div>
                        <div style="color: {text_color}; text-shadow: {text_shadow}; font-size: 1.2rem; font-weight: bold;">{", ".join(display_case['tags'])}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Add refresh button for this display case
                    if st.button("Refresh Display Case", key=f"refresh_{selected_case}"):
                        if st.session_state.display_case_manager.refresh_display_case(selected_case):
                            st.success(f"Display case '{selected_case}' refreshed successfully!")
                            st.rerun()
                        else:
                            st.error(f"Failed to refresh display case '{selected_case}'.")
                    
                    # Add backup button
                    if st.button("Create Backup", key="create_backup"):
                        zip_path = create_backup()
                        if zip_path:
                            with open(zip_path, 'rb') as f:
                                zip_data = f.read()
                            st.download_button(
                                label="Download Backup",
                                data=zip_data,
                                file_name=os.path.basename(zip_path),
                                mime="application/zip"
                            )
                            st.success(f"Backup created successfully! Saved as {os.path.basename(zip_path)}")
                    
                    if st.button("Edit Tags", key=f"edit_tags_{selected_case}"):
                        st.session_state.editing_tags = True
                        st.session_state.current_case = selected_case
                        st.session_state.current_tags = display_case['tags'].copy()
                        st.rerun()
                    
                    if st.session_state.get('editing_tags', False) and st.session_state.get('current_case') == selected_case:
                        with st.form(f"edit_tags_form_{selected_case}"):
                            # Combine current tags with all_tags to ensure all options are available
                            current_tags = display_case['tags']
                            all_available_tags = list(set(all_tags + current_tags))
                            new_tags = st.multiselect(
                                "Select Tags",
                                options=all_available_tags,
                                default=current_tags,
                                key=f"new_tags_{selected_case}"
                            )
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("Save Tags", use_container_width=True):
                                    if new_tags != current_tags:
                                        # Create a copy of the display case to avoid modifying the original
                                        updated_case = display_case.copy()
                                        updated_case['tags'] = new_tags
                                        if st.session_state.display_case_manager.update_display_case(selected_case, updated_case):
                                            st.success("Tags updated successfully!")
                                            st.session_state.editing_tags = False
                                            st.session_state.current_case = None
                                            st.rerun()
                                        else:
                                            st.error("Failed to update tags.")
                                    else:
                                        st.info("No changes made to tags.")
                                        st.session_state.editing_tags = False
                                        st.session_state.current_case = None
                                        st.rerun()
                            with col2:
                                if st.form_submit_button("Cancel", use_container_width=True):
                                    st.session_state.editing_tags = False
                                    st.session_state.current_case = None
                                    st.rerun()
                with col2:
                    st.markdown(f"""
                    <div style="background: {card_bg}; padding: 1rem; border-radius: 10px;">
                        <div style="color: {text_color}; text-shadow: {text_shadow}; font-size: 0.9rem;">Total Value</div>
                        <div style="color: {text_color}; text-shadow: {text_shadow}; font-size: 1.2rem; font-weight: bold;">${display_case['total_value']:,.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                st.subheader("Cards")
                display_case_grid(display_case)
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    export_data = export_display_case(display_case)
                    st.download_button(
                        label="Export Display Case",
                        data=export_data,
                        file_name=f"display_case_{selected_case.lower().replace(' ', '_')}.json",
                        mime="application/json"
                    )
                with col2:
                    if st.button("Delete Display Case"):
                        if st.session_state.display_case_manager.delete_display_case(selected_case):
                            st.success(f"Display case '{selected_case}' deleted.")
                            st.rerun()
                        else:
                            st.error("Failed to delete display case from database.")
                display_url = f"https://your-app-link.com/?case_id={selected_case.lower().replace(' ', '_')}"
                st.markdown(f"""
                <div style="background: {card_bg}; padding: 1rem; border-radius: 10px; color: {text_color}; text-shadow: {text_shadow};">
                    Share this case: {display_url}
                </div>
                """, unsafe_allow_html=True)
                if enable_comments:
                    st.subheader("Comments")
                    name = st.text_input("Name")
                    comment = st.text_area("Leave a comment")
                    if st.button("Post Comment"):
                        st.success(f"Comment posted by {name} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {comment}")
        else:
            st.info("No display cases created yet. Create one in the 'Create Display Case' tab!")

if __name__ == "__main__":
    main()
