"""
Display Manager Test Environment
A safe testing environment for the new display manager implementation.
"""

import streamlit as st
import logging
import time
import psutil
import os
from datetime import datetime
from modules.core.display_manager import DisplayManager
from modules.core.collection_manager import CollectionManager
from config.feature_flags import is_feature_enabled

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_memory_usage():
    """Get current memory usage"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # Convert to MB

def log_performance(start_time, operation, initial_memory):
    """Log performance metrics for display operations"""
    duration = time.time() - start_time
    current_memory = get_memory_usage()
    memory_diff = current_memory - initial_memory
    
    logger.info(f"{operation} completed in {duration:.2f} seconds, memory usage: {memory_diff:.2f}MB")
    return {
        'duration': duration,
        'memory_diff': memory_diff
    }

def main():
    st.title("Display Manager Test Environment")
    st.info("This is a testing environment for the new display manager. Changes here won't affect the main application.")
    
    # Performance tracking
    performance_data = {
        'grid_load': [],
        'table_load': [],
        'details_load': []
    }
    
    # Error tracking
    error_data = {
        'grid_errors': [],
        'table_errors': [],
        'details_errors': []
    }
    
    # Get current collection
    collection = CollectionManager.get_collection()
    
    # Display options
    display_mode = st.radio(
        "Select Display Mode",
        ["Grid", "Table", "Details"],
        horizontal=True
    )
    
    # Display collection based on selected mode
    if display_mode == "Grid":
        st.subheader("Grid View Test")
        start_time = time.time()
        initial_memory = get_memory_usage()
        
        try:
            DisplayManager.display_collection_grid(collection)
            metrics = log_performance(start_time, "Grid Display", initial_memory)
            performance_data['grid_load'].append(metrics)
        except Exception as e:
            error_msg = f"Error in grid display: {str(e)}"
            logger.error(error_msg)
            error_data['grid_errors'].append({
                'timestamp': datetime.now(),
                'error': error_msg
            })
            st.error(error_msg)
        
    elif display_mode == "Table":
        st.subheader("Table View Test")
        start_time = time.time()
        initial_memory = get_memory_usage()
        
        try:
            DisplayManager.display_collection_table(collection)
            metrics = log_performance(start_time, "Table Display", initial_memory)
            performance_data['table_load'].append(metrics)
        except Exception as e:
            error_msg = f"Error in table display: {str(e)}"
            logger.error(error_msg)
            error_data['table_errors'].append({
                'timestamp': datetime.now(),
                'error': error_msg
            })
            st.error(error_msg)
        
    elif display_mode == "Details":
        st.subheader("Details View Test")
        if collection:
            # Create a dropdown to select a card
            card_options = [
                f"{i+1}. {card.get('player_name', 'Unknown')} - {card.get('year', '')} {card.get('card_set', '')}"
                for i, card in enumerate(collection)
            ]
            selected_idx = st.selectbox(
                "Select a card to view details",
                range(len(card_options)),
                format_func=lambda i: card_options[i]
            )
            if selected_idx is not None:
                start_time = time.time()
                initial_memory = get_memory_usage()
                
                try:
                    DisplayManager.display_card_details(collection[selected_idx])
                    metrics = log_performance(start_time, "Details Display", initial_memory)
                    performance_data['details_load'].append(metrics)
                except Exception as e:
                    error_msg = f"Error in details display: {str(e)}"
                    logger.error(error_msg)
                    error_data['details_errors'].append({
                        'timestamp': datetime.now(),
                        'error': error_msg
                    })
                    st.error(error_msg)
        else:
            st.info("No cards available to display")
    
    # Display performance metrics
    st.subheader("Performance Metrics")
    col1, col2, col3 = st.columns(3)
    with col1:
        if performance_data['grid_load']:
            avg_duration = sum(m['duration'] for m in performance_data['grid_load']) / len(performance_data['grid_load'])
            avg_memory = sum(m['memory_diff'] for m in performance_data['grid_load']) / len(performance_data['grid_load'])
            st.metric("Grid Load Time", f"{avg_duration:.2f}s")
            st.metric("Memory Usage", f"{avg_memory:.2f}MB")
    with col2:
        if performance_data['table_load']:
            avg_duration = sum(m['duration'] for m in performance_data['table_load']) / len(performance_data['table_load'])
            avg_memory = sum(m['memory_diff'] for m in performance_data['table_load']) / len(performance_data['table_load'])
            st.metric("Table Load Time", f"{avg_duration:.2f}s")
            st.metric("Memory Usage", f"{avg_memory:.2f}MB")
    with col3:
        if performance_data['details_load']:
            avg_duration = sum(m['duration'] for m in performance_data['details_load']) / len(performance_data['details_load'])
            avg_memory = sum(m['memory_diff'] for m in performance_data['details_load']) / len(performance_data['details_load'])
            st.metric("Details Load Time", f"{avg_duration:.2f}s")
            st.metric("Memory Usage", f"{avg_memory:.2f}MB")
    
    # Display error statistics
    st.subheader("Error Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Grid Errors", len(error_data['grid_errors']))
    with col2:
        st.metric("Table Errors", len(error_data['table_errors']))
    with col3:
        st.metric("Details Errors", len(error_data['details_errors']))
    
    # Display collection statistics
    stats = CollectionManager.get_collection_stats()
    DisplayManager.display_collection_stats(stats)
    
    # Debug information
    with st.expander("Debug Information"):
        st.write("Collection Size:", len(collection))
        st.write("Performance Data:", performance_data)
        st.write("Error Data:", error_data)
        st.write("Current Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        st.write("Current Memory Usage:", f"{get_memory_usage():.2f}MB")
        
        # User feedback
        st.subheader("User Feedback")
        feedback = st.text_area("Please provide feedback on the display performance:")
        if st.button("Submit Feedback"):
            logger.info(f"User Feedback: {feedback}")
            st.success("Thank you for your feedback!")

if __name__ == "__main__":
    main() 