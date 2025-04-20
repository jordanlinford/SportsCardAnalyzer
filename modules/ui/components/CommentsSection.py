import streamlit as st
from typing import List, Dict, Callable
from datetime import datetime

def render_comments_section(
    case_id: str,
    comments: List[Dict],
    on_add_comment: Callable,
    on_delete_comment: Callable,
    current_user_id: str
) -> None:
    """
    Renders a comments section with the ability to add and delete comments.
    
    Args:
        case_id: ID of the display case
        comments: List of comment dictionaries
        on_add_comment: Callback function when adding a comment
        on_delete_comment: Callback function when deleting a comment
        current_user_id: ID of the current user
    """
    st.subheader("Comments")
    
    # Add comment form
    with st.form(key="comment_form"):
        comment = st.text_area("Add a comment", key="new_comment")
        submit = st.form_submit_button("Post Comment")
        
        if submit and comment.strip():
            if on_add_comment(case_id, comment.strip()):
                st.success("Comment added successfully!")
                st.rerun()
            else:
                st.error("Failed to add comment")
    
    # Display comments
    if not comments:
        st.info("No comments yet. Be the first to comment!")
        return
    
    for comment in comments:
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <div style="font-weight: bold;">{comment.get('username', 'Anonymous')}</div>
                    <div style="color: #666; font-size: 0.8em;">{datetime.fromisoformat(comment['timestamp']).strftime('%B %d, %Y at %I:%M %p')}</div>
                    <div style="margin-top: 5px;">{comment['comment']}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                if comment.get('uid') == current_user_id:
                    if st.button("Delete", key=f"delete_{comment['id']}"):
                        if on_delete_comment(case_id, comment['id']):
                            st.success("Comment deleted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to delete comment") 