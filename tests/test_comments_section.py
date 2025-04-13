import unittest
from unittest.mock import patch, MagicMock, call
from modules.ui.components import render_comments_section
import streamlit as st
from datetime import datetime, timedelta, timezone

class TestCommentsSection(unittest.TestCase):
    def setUp(self):
        # Mock comments data
        self.mock_comments = [
            {
                'id': '1',
                'uid': 'user1',
                'username': 'Test User 1',
                'comment': 'Test comment 1',
                'timestamp': (datetime.now() - timedelta(days=1)).isoformat()
            },
            {
                'id': '2',
                'uid': 'user2',
                'username': 'Test User 2',
                'comment': 'Test comment 2',
                'timestamp': datetime.now().isoformat()
            }
        ]
        
        # Mock callbacks
        self.mock_add_comment = MagicMock()
        self.mock_delete_comment = MagicMock()
        
        # Mock case and user data
        self.case_id = 'test_case_123'
        self.current_user_id = 'user1'

        # Common mock setup
        self.mock_col1 = MagicMock()
        self.mock_col2 = MagicMock()
        self.mock_cols = [self.mock_col1, self.mock_col2]

        # Mock Streamlit functions
        self.mock_subheader = MagicMock()
        self.mock_form = MagicMock()
        self.mock_text_area = MagicMock()
        self.mock_form_submit_button = MagicMock()
        self.mock_success = MagicMock()
        self.mock_error = MagicMock()
        self.mock_info = MagicMock()
        self.mock_container = MagicMock()
        self.mock_columns = MagicMock()
        self.mock_markdown = MagicMock()
        self.mock_button = MagicMock()
        self.mock_rerun = MagicMock()
        
        # Setup form context
        self.mock_form_context = MagicMock()
        self.mock_form_context.__enter__.return_value = None
        self.mock_form_context.__exit__.return_value = None
        self.mock_form.return_value = self.mock_form_context
        
        # Setup container context
        self.mock_container_context = MagicMock()
        self.mock_container_context.__enter__.return_value = None
        self.mock_container_context.__exit__.return_value = None
        self.mock_container.return_value = self.mock_container_context
        
        # Setup columns
        self.mock_col1.__enter__.return_value = self.mock_col1
        self.mock_col1.__exit__.return_value = None
        self.mock_col2.__enter__.return_value = self.mock_col2
        self.mock_col2.__exit__.return_value = None
        self.mock_columns.return_value = (self.mock_col1, self.mock_col2)
        
        # Patch all Streamlit functions
        self.patches = [
            patch('streamlit.subheader', self.mock_subheader),
            patch('streamlit.form', self.mock_form),
            patch('streamlit.text_area', self.mock_text_area),
            patch('streamlit.form_submit_button', self.mock_form_submit_button),
            patch('streamlit.success', self.mock_success),
            patch('streamlit.error', self.mock_error),
            patch('streamlit.info', self.mock_info),
            patch('streamlit.container', self.mock_container),
            patch('streamlit.columns', self.mock_columns),
            patch('streamlit.markdown', self.mock_markdown),
            patch('streamlit.button', self.mock_button),
            patch('streamlit.rerun', self.mock_rerun)
        ]
        
        for p in self.patches:
            p.start()
            
    def tearDown(self):
        for p in self.patches:
            p.stop()

    def setup_streamlit_mocks(self, mock_form, mock_container, mock_columns):
        """Helper method to set up common Streamlit mocks"""
        # Mock form context
        mock_form.return_value.__enter__.return_value = None
        mock_form.return_value.__exit__.return_value = None
        
        # Mock container context
        mock_container.return_value.__enter__.return_value = None
        mock_container.return_value.__exit__.return_value = None
        
        # Mock columns
        mock_columns.return_value = self.mock_cols
        self.mock_col1.__enter__.return_value = self.mock_col1
        self.mock_col1.__exit__.return_value = None
        self.mock_col2.__enter__.return_value = self.mock_col2
        self.mock_col2.__exit__.return_value = None

    @patch('streamlit.markdown')
    @patch('streamlit.text_area')
    @patch('streamlit.button')
    @patch('streamlit.subheader')
    @patch('streamlit.form')
    @patch('streamlit.form_submit_button')
    @patch('streamlit.success')
    @patch('streamlit.error')
    @patch('streamlit.info')
    @patch('streamlit.container')
    @patch('streamlit.columns')
    def test_empty_comments(self, mock_columns, mock_container, mock_info, mock_error, mock_success, 
                          mock_form_submit, mock_form, mock_subheader, mock_button, mock_text_area, mock_markdown):
        """Test rendering with no comments"""
        self.setup_streamlit_mocks(mock_form, mock_container, mock_columns)
        mock_form_submit.return_value = False
        
        render_comments_section(
            self.case_id,
            [],
            self.mock_add_comment,
            self.mock_delete_comment,
            self.current_user_id
        )
        
        mock_subheader.assert_called_with("Comments")
        mock_info.assert_called_with("No comments yet. Be the first to comment!")

    @patch('streamlit.markdown')
    @patch('streamlit.text_area')
    @patch('streamlit.button')
    @patch('streamlit.subheader')
    @patch('streamlit.form')
    @patch('streamlit.form_submit_button')
    @patch('streamlit.success')
    @patch('streamlit.error')
    @patch('streamlit.info')
    @patch('streamlit.container')
    @patch('streamlit.columns')
    def test_with_comments(self, mock_columns, mock_container, mock_info, mock_error, mock_success, 
                          mock_form_submit, mock_form, mock_subheader, mock_button, mock_text_area, mock_markdown):
        """Test rendering with existing comments"""
        self.setup_streamlit_mocks(mock_form, mock_container, mock_columns)
        mock_form_submit.return_value = False
        
        render_comments_section(
            self.case_id,
            self.mock_comments,
            self.mock_add_comment,
            self.mock_delete_comment,
            self.current_user_id
        )
        
        mock_subheader.assert_called_with("Comments")
        mock_markdown.assert_called()

    @patch('streamlit.markdown')
    @patch('streamlit.text_area')
    @patch('streamlit.button')
    @patch('streamlit.subheader')
    @patch('streamlit.form')
    @patch('streamlit.form_submit_button')
    @patch('streamlit.success')
    @patch('streamlit.error')
    @patch('streamlit.info')
    @patch('streamlit.container')
    @patch('streamlit.columns')
    def test_add_comment(self, mock_columns, mock_container, mock_info, mock_error, mock_success, 
                        mock_form_submit, mock_form, mock_subheader, mock_button, mock_text_area, mock_markdown):
        """Test adding a new comment"""
        self.setup_streamlit_mocks(mock_form, mock_container, mock_columns)
        
        # Mock form submission
        mock_text_area.return_value = "New test comment"
        mock_form_submit.return_value = True
        self.mock_add_comment.return_value = True
        
        # Test with empty comments to avoid delete button interference
        render_comments_section(
            self.case_id,
            [],  # Use empty comments list
            self.mock_add_comment,
            self.mock_delete_comment,
            self.current_user_id
        )
        
        # Verify add comment was called
        self.mock_add_comment.assert_called_once_with(
            self.case_id,
            "New test comment"
        )
        
        # Verify success message
        mock_success.assert_called_with("Comment added successfully!")

    @patch('streamlit.markdown')
    @patch('streamlit.text_area')
    @patch('streamlit.button')
    @patch('streamlit.subheader')
    @patch('streamlit.form')
    @patch('streamlit.form_submit_button')
    @patch('streamlit.success')
    @patch('streamlit.error')
    @patch('streamlit.info')
    @patch('streamlit.container')
    @patch('streamlit.columns')
    def test_delete_comment(self, mock_columns, mock_container, mock_info, mock_error, mock_success, 
                          mock_form_submit, mock_form, mock_subheader, mock_button, mock_text_area, mock_markdown):
        """Test deleting a comment"""
        self.setup_streamlit_mocks(mock_form, mock_container, mock_columns)
        mock_form_submit.return_value = False
        
        # Mock the delete button in the second column
        self.mock_col2.button.return_value = True
        self.mock_delete_comment.return_value = True
        
        render_comments_section(
            self.case_id,
            self.mock_comments,
            self.mock_add_comment,
            self.mock_delete_comment,
            self.current_user_id
        )
        
        # Verify delete was called with correct arguments
        self.mock_delete_comment.assert_called_once_with(
            self.case_id,
            '1'  # First comment's ID
        )
        mock_success.assert_called_with("Comment deleted successfully!")

    @patch('streamlit.markdown')
    @patch('streamlit.text_area')
    @patch('streamlit.button')
    @patch('streamlit.subheader')
    @patch('streamlit.form')
    @patch('streamlit.form_submit_button')
    @patch('streamlit.success')
    @patch('streamlit.error')
    @patch('streamlit.info')
    @patch('streamlit.container')
    @patch('streamlit.columns')
    def test_comment_ordering(self, mock_columns, mock_container, mock_info, mock_error, mock_success, 
                            mock_form_submit, mock_form, mock_subheader, mock_button, mock_text_area, mock_markdown):
        """Test that comments are displayed in chronological order"""
        self.setup_streamlit_mocks(mock_form, mock_container, mock_columns)
        mock_form_submit.return_value = False
        
        newer_comment = {
            'id': '3',
            'uid': 'user3',
            'username': 'Test User 3',
            'comment': 'Newest comment',
            'timestamp': (datetime.now() + timedelta(hours=1)).isoformat()
        }
        comments = self.mock_comments + [newer_comment]
        
        render_comments_section(
            self.case_id,
            comments,
            self.mock_add_comment,
            self.mock_delete_comment,
            self.current_user_id
        )
        
        mock_markdown.assert_called()

    @patch('streamlit.markdown')
    @patch('streamlit.text_area')
    @patch('streamlit.button')
    @patch('streamlit.subheader')
    @patch('streamlit.form')
    @patch('streamlit.form_submit_button')
    @patch('streamlit.success')
    @patch('streamlit.error')
    @patch('streamlit.info')
    @patch('streamlit.container')
    @patch('streamlit.columns')
    def test_missing_fields(self, mock_columns, mock_container, mock_info, mock_error, mock_success, 
                          mock_form_submit, mock_form, mock_subheader, mock_button, mock_text_area, mock_markdown):
        """Test handling of comments with missing fields"""
        self.setup_streamlit_mocks(mock_form, mock_container, mock_columns)
        mock_form_submit.return_value = False
        
        incomplete_comment = {
            'id': '3',
            'comment': 'Incomplete comment',
            'timestamp': datetime.now().isoformat()
            # Missing uid, username
        }
        
        render_comments_section(
            self.case_id,
            [incomplete_comment],
            self.mock_add_comment,
            self.mock_delete_comment,
            self.current_user_id
        )
        
        mock_markdown.assert_called()

    def test_add_comment_success(self):
        """Test adding a comment successfully"""
        self.mock_text_area.return_value = "Test comment"
        self.mock_form_submit_button.return_value = True
        
        on_add_comment = MagicMock(return_value=True)
        
        render_comments_section(
            self.case_id,
            [],
            on_add_comment,
            self.mock_delete_comment,
            self.current_user_id
        )
        
        on_add_comment.assert_called_once_with(
            self.case_id,
            "Test comment"
        )
        self.mock_success.assert_called_once_with("Comment added successfully!")
        self.mock_rerun.assert_called_once()
        
    def test_add_comment_failure(self):
        """Test adding a comment with failure"""
        self.mock_text_area.return_value = "Test comment"
        self.mock_form_submit_button.return_value = True
        
        on_add_comment = MagicMock(return_value=False)
        
        render_comments_section(
            self.case_id,
            [],
            on_add_comment,
            self.mock_delete_comment,
            self.current_user_id
        )
        
        on_add_comment.assert_called_once_with(
            self.case_id,
            "Test comment"
        )
        self.mock_error.assert_called_once_with("Failed to add comment")

    def test_display_comments(self):
        """Test displaying existing comments"""
        test_comment = {
            'id': 'comment1',
            'uid': 'user1',
            'username': 'Test User',
            'comment': 'Test comment content',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        render_comments_section(
            self.case_id,
            [test_comment],
            self.mock_add_comment,
            self.mock_delete_comment,
            self.current_user_id
        )
        
        self.mock_markdown.assert_called_with(unittest.mock.ANY, unsafe_allow_html=True)
        markdown_call = self.mock_markdown.call_args[0][0]
        self.assertIn(test_comment['username'], markdown_call)
        self.assertIn(test_comment['comment'], markdown_call)
        
    def test_delete_comment_owner(self):
        """Test deleting a comment as the owner"""
        test_comment = {
            'id': 'comment1',
            'uid': 'user1',
            'username': 'Test User',
            'comment': 'Test comment content',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.mock_button.return_value = True
        on_delete_comment = MagicMock(return_value=True)
        
        render_comments_section(
            self.case_id,
            [test_comment],
            self.mock_add_comment,
            on_delete_comment,
            self.current_user_id
        )
        
        on_delete_comment.assert_called_once_with(
            self.case_id,
            'comment1'
        )
if __name__ == '__main__':
    unittest.main() 