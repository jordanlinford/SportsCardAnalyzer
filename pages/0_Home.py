import streamlit as st
from modules.utils.analytics import track_page_view
from modules.core.firebase_manager import FirebaseManager
from modules.ui.branding import BrandingComponent
from modules.database.service import DatabaseService
from datetime import datetime, timedelta

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
    # Get the user's cards subcollection reference
    cards_ref = FirebaseManager.get_collection('users').document(st.session_state.uid).collection('cards')
    card_docs = cards_ref.get()
    
    # Convert documents to dictionaries
    collection = []
    for doc in card_docs:
        card_data = doc.to_dict()
        collection.append(card_data)
    
    # Calculate total cards and market value
    total_cards = len(collection)
    market_value = sum(float(card.get('current_value', 0)) for card in collection)
    
    # Get recently added cards (last 7 days)
    recent_cards = []
    for card in collection:
        if 'created_at' in card:
            try:
                created_date = datetime.strptime(card['created_at'], '%Y-%m-%d')
                if created_date > datetime.now() - timedelta(days=7):
                    recent_cards.append(card)
            except:
                continue
    
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
        st.metric("Recent Additions", str(len(recent_cards)), "0%")
        st.write("Cards added in the last 7 days")

    # Add recent activity section
    st.subheader("Recent Activity")
    
    if recent_cards:
        for card in recent_cards:
            with st.expander(f"{card.get('player_name', 'Unknown')} - {card.get('created_at', '')}"):
                st.write(f"Card: {card.get('card_name', 'Unknown')}")
                st.write(f"Year: {card.get('year', 'N/A')}")
                st.write(f"Set: {card.get('card_set', 'N/A')}")
                st.write(f"Grade: {card.get('grade', 'N/A')}")
                st.write(f"Value: ${card.get('current_value', 0):,.2f}")
    else:
        st.info("No recent activity to display. Start by adding cards to your collection or analyzing market trends.")

except Exception as e:
    st.error(f"Error loading dashboard data: {str(e)}")
    st.stop() 