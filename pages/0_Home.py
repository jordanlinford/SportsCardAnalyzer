import streamlit as st
from modules.utils.analytics import track_page_view
from modules.core.firebase_manager import FirebaseManager
from modules.ui.branding import BrandingComponent
from modules.database.service import DatabaseService
from datetime import datetime, timedelta
import traceback

st.set_page_config(page_title="Home", layout="wide")
track_page_view("Home")

# Initialize session state if not exists
if 'user' not in st.session_state:
    st.session_state.user = None
if 'uid' not in st.session_state:
    st.session_state.uid = None

# Get user info
user = FirebaseManager().get_current_user()
if not user:
    st.error("Please log in to view your dashboard")
    st.stop()

display_name = user.get('displayName', 'User')
st.session_state.user = user
st.session_state.uid = user.get('localId')

# Get collection data
try:
    # Force a reload to ensure we have the most recent data
    with st.spinner("Loading your latest collection data..."):
        # Use DatabaseService to get the collection directly, bypassing the cache
        card_objects = DatabaseService.get_user_collection(st.session_state.uid)
        
        # Convert cards to dictionaries for easier processing
        collection = []
        for card in card_objects:
            if hasattr(card, 'to_dict') and callable(getattr(card, 'to_dict')):
                collection.append(card.to_dict())
            elif isinstance(card, dict):
                collection.append(card)
            else:
                # Try to convert object attributes to dict
                try:
                    card_dict = {k: getattr(card, k) for k in dir(card) 
                                if not k.startswith('_') and not callable(getattr(card, k))}
                    collection.append(card_dict)
                except Exception as e:
                    print(f"Could not convert card to dictionary: {str(e)}")
                    continue
    
    # Calculate total cards and market value
    total_cards = len(collection)
    market_value = sum(float(card.get('current_value', 0)) for card in collection)
    
    # Get recently added cards (last 7 days)
    recent_cards = []
    seven_days_ago = datetime.now() - timedelta(days=7)
    
    for card in collection:
        try:
            # First, verify card has created_at field
            if 'created_at' not in card or not card['created_at']:
                continue
                
            created_date = None
            created_at_str = str(card['created_at'])
            
            # Try multiple date formats
            date_formats = [
                '%Y-%m-%d',                # Standard date: 2023-04-18
                '%Y-%m-%dT%H:%M:%S',       # ISO format without timezone: 2023-04-18T14:30:45
                '%Y-%m-%d %H:%M:%S',       # Standard datetime: 2023-04-18 14:30:45
                '%m/%d/%Y'                 # US format: 04/18/2023
            ]
            
            # Try each format until one works
            for date_format in date_formats:
                try:
                    # For ISO format, we may need to truncate
                    parsing_str = created_at_str
                    if 'T' in created_at_str and date_format == '%Y-%m-%dT%H:%M:%S':
                        # Handle full ISO format with timezone
                        if '+' in created_at_str:
                            parsing_str = created_at_str.split('+')[0]
                        elif '.' in created_at_str:
                            parsing_str = created_at_str.split('.')[0]
                    
                    # Special case for just the date part
                    if len(parsing_str) == 10 and date_format != '%Y-%m-%d' and date_format != '%m/%d/%Y':
                        continue
                        
                    created_date = datetime.strptime(parsing_str, date_format)
                    break
                except ValueError:
                    continue
            
            # If we couldn't parse the date, try a more aggressive approach
            if created_date is None:
                try:
                    # Just extract the date part if it's in ISO format
                    if 'T' in created_at_str:
                        date_part = created_at_str.split('T')[0]
                        if len(date_part) == 10:  # YYYY-MM-DD
                            created_date = datetime.strptime(date_part, '%Y-%m-%d')
                except Exception:
                    continue
                    
            # If we still couldn't parse the date, skip this card
            if created_date is None:
                continue
                
            # Check if card was added in the last 7 days
            if created_date >= seven_days_ago:
                # Make a copy to avoid modifying the original
                card_copy = card.copy()
                # Add the parsed date for sorting
                card_copy['_parsed_created_date'] = created_date
                recent_cards.append(card_copy)
                
        except Exception as e:
            print(f"Error processing card: {e}")
            print(traceback.format_exc())
            continue
    
    # Sort recent cards by created_at (newest first)
    if recent_cards:
        recent_cards.sort(key=lambda x: x.get('_parsed_created_date', datetime.min), reverse=True)
        # Remove the temporary sorting field
        for card in recent_cards:
            if '_parsed_created_date' in card:
                del card['_parsed_created_date']
    
    st.title(f"Welcome back, {display_name}!")
    st.write("Your personal dashboard for tracking and evaluating sports card values.")
    st.info("Use the sidebar to explore tools like Market Analysis, Trade Analyzer, Collection Manager, and more.")

    # Add a dashboard overview section
    st.subheader("Dashboard Overview")

    # Create columns for quick stats
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Cards", str(total_cards), "0%")
        st.write("Track your entire collection")

    with col2:
        st.metric("Market Value", f"${market_value:,.2f}", "0%")
        st.write("Current estimated value")

    with col3:
        # Update to show the actual number instead of "0%"
        recent_count = len(recent_cards)
        st.metric("Recent Additions", str(recent_count), f"{recent_count} in the last 7 days")
        st.write("Cards added in the last 7 days")

    # Add recent activity section
    st.subheader("Recent Activity")
    
    if recent_cards:
        for card in recent_cards:
            # Format the card title for the expander
            player_name = card.get('player_name', 'Unknown')
            year = card.get('year', 'N/A')
            card_set = card.get('card_set', 'N/A')
            card_number = card.get('card_number', 'N/A')
            
            # Create a more descriptive title
            card_title = f"{player_name} ({year} {card_set} #{card_number})"
            
            with st.expander(card_title):
                # Create a two-column layout for card details
                col1, col2 = st.columns([1, 2])
                
                # Show card image if available
                with col1:
                    if 'photo' in card and card['photo']:
                        st.image(card['photo'], use_column_width=True)
                    else:
                        st.markdown("*No image available*")
                
                # Show card details
                with col2:
                    st.markdown(f"**Player:** {player_name}")
                    st.markdown(f"**Year:** {year}")
                    st.markdown(f"**Set:** {card_set}")
                    st.markdown(f"**Number:** {card_number}")
                    st.markdown(f"**Condition:** {card.get('condition', 'N/A')}")
                    st.markdown(f"**Current Value:** ${float(card.get('current_value', 0)):,.2f}")
                    
                    # Show purchase info if available
                    if 'purchase_price' in card and card['purchase_price']:
                        purchase_price = float(card.get('purchase_price', 0))
                        st.markdown(f"**Purchase Price:** ${purchase_price:,.2f}")
                        
                        # Calculate and show ROI if purchase price exists
                        if purchase_price > 0:
                            current_value = float(card.get('current_value', 0))
                            roi = ((current_value - purchase_price) / purchase_price) * 100
                            st.markdown(f"**ROI:** {roi:,.1f}%")
                    
                    # Show when the card was added with proper formatting
                    try:
                        created_at_str = card.get('created_at', 'Unknown date')
                        if created_at_str and created_at_str != 'Unknown date':
                            # Try to parse and format the date nicely
                            try:
                                # Handle different date formats
                                if 'T' in created_at_str:
                                    # ISO format
                                    created_date = datetime.fromisoformat(created_at_str.split('+')[0].split('.')[0])
                                elif ' ' in created_at_str and len(created_at_str) > 10:
                                    # Date with time
                                    created_date = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
                                else:
                                    # Just date
                                    created_date = datetime.strptime(created_at_str, '%Y-%m-%d')
                                
                                # Format date nicely
                                formatted_date = created_date.strftime('%B %d, %Y')
                                st.markdown(f"**Added on:** {formatted_date}")
                            except:
                                # If parsing fails, just show the raw string
                                st.markdown(f"**Added on:** {created_at_str}")
                        else:
                            st.markdown("**Added on:** Unknown")
                    except Exception as e:
                        st.markdown("**Added on:** Unable to determine")
    else:
        st.info("No cards have been added in the last 7 days. Use the Collection Manager to add cards to your collection.")
except Exception as e:
    st.error(f"Error loading dashboard: {str(e)}")
    st.write("Please try refreshing the page or contacting support if the issue persists.")
    print(f"Dashboard error: {str(e)}")
    print(traceback.format_exc()) 