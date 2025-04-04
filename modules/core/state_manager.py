import streamlit as st

class StateManager:
    def __init__(self):
        self.state = {
            'search_results': None,
            'selected_card': None,
            'show_all_results': True,
            'form_submitted': False
        }

    def initialize_session_state(self):
        """Initialize session state variables if they don't exist."""
        if 'search_results' not in st.session_state:
            st.session_state.search_results = None
        if 'selected_card' not in st.session_state:
            st.session_state.selected_card = None
        if 'show_all_results' not in st.session_state:
            st.session_state.show_all_results = True
        if 'form_submitted' not in st.session_state:
            st.session_state.form_submitted = False

    def get_state(self):
        """Get the current state from session state."""
        self.state['search_results'] = st.session_state.search_results
        self.state['selected_card'] = st.session_state.selected_card
        self.state['show_all_results'] = st.session_state.show_all_results
        self.state['form_submitted'] = st.session_state.form_submitted
        return self.state

    def update_search_results(self, results):
        """Update search results in session state."""
        st.session_state.search_results = results

    def on_card_select(self, card):
        """Handle card selection."""
        st.session_state.selected_card = card
        st.session_state.show_all_results = False

    def clear_selection(self):
        """Clear the selected card."""
        st.session_state.selected_card = None
        st.session_state.show_all_results = True 