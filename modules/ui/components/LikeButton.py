import streamlit as st
from typing import Callable, Optional
from modules.core.firebase_manager import FirebaseManager

def render_like_button(
    case_id: str,
    initial_likes: int = 0,
    is_liked: bool = False,
    on_like: Optional[Callable] = None
) -> None:
    """
    Renders a like button with count and animation.
    
    Args:
        case_id: ID of the display case
        initial_likes: Initial number of likes
        is_liked: Whether the current user has liked the case
        on_like: Callback function when like button is clicked
    """
    # Add CSS for animation
    st.markdown("""
    <style>
    .like-button {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        border-radius: 20px;
        background: #f0f2f6;
        border: none;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .like-button:hover {
        background: #e6e8eb;
    }
    .like-button.liked {
        background: #ff4b4b;
        color: white;
    }
    .like-count {
        font-weight: bold;
    }
    @keyframes like-animation {
        0% { transform: scale(1); }
        50% { transform: scale(1.2); }
        100% { transform: scale(1); }
    }
    .like-animation {
        animation: like-animation 0.3s ease;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create like button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button(
            "❤️",
            key=f"like-{case_id}",
            use_container_width=True,
            on_click=on_like,
            args=(case_id, not is_liked)
        ):
            st.markdown(
                f'<div class="like-animation">❤️</div>',
                unsafe_allow_html=True
            )
    with col2:
        st.markdown(
            f'<div class="like-count">{initial_likes}</div>',
            unsafe_allow_html=True
        ) 