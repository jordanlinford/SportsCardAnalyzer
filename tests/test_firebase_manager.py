import unittest
import time
from unittest.mock import patch, MagicMock
from modules.core.firebase_manager import FirebaseManager
import firebase_admin
from firebase_admin import credentials, firestore
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestFirebaseManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Mock environment variables
        cls.env_patcher = patch.dict('os.environ', {
            'FIREBASE_PROJECT_ID': 'test-project',
            'FIREBASE_PRIVATE_KEY_ID': 'test-key-id',
            'FIREBASE_PRIVATE_KEY': 'test-key',
            'FIREBASE_CLIENT_EMAIL': 'test@test.com',
            'FIREBASE_CLIENT_ID': 'test-client-id',
            'FIREBASE_CLIENT_X509_CERT_URL': 'https://test.com/cert',
            'FIREBASE_API_KEY': 'test-api-key',
            'FIREBASE_AUTH_DOMAIN': 'test.firebaseapp.com',
            'FIREBASE_STORAGE_BUCKET': 'test.appspot.com',
            'FIREBASE_MESSAGING_SENDER_ID': 'test-sender-id',
            'FIREBASE_APP_ID': 'test-app-id'
        })
        cls.env_patcher.start()
        
        # Reset FirebaseManager state
        FirebaseManager._initialized = False
        FirebaseManager._auth = None
        FirebaseManager._db = None
        FirebaseManager._firebase = None
        FirebaseManager._firebase_app = None
        FirebaseManager._current_user = None
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        cls.env_patcher.stop()
        # Reset FirebaseManager state
        FirebaseManager._initialized = False
        FirebaseManager._auth = None
        FirebaseManager._db = None
        FirebaseManager._firebase = None
        FirebaseManager._firebase_app = None
        FirebaseManager._current_user = None
    
    def setUp(self):
        """Set up before each test."""
        # Reset FirebaseManager state before each test
        FirebaseManager._initialized = False
        FirebaseManager._auth = None
        FirebaseManager._db = None
        FirebaseManager._firebase = None
        FirebaseManager._firebase_app = None
        FirebaseManager._current_user = None
    
    @patch('firebase_admin.get_app')
    @patch('firebase_admin.initialize_app')
    @patch('firebase_admin.credentials.Certificate')
    def test_firebase_admin_initialization(self, mock_cert, mock_init, mock_get):
        """Test Firebase Admin SDK initialization."""
        # Mock successful initialization
        mock_get.side_effect = ValueError("App doesn't exist")
        mock_cert.return_value = MagicMock()
        mock_init.return_value = MagicMock()
        
        # Test initialization
        result = FirebaseManager._initialize_firebase_admin()
        self.assertTrue(result)
        mock_cert.assert_called_once()
        mock_init.assert_called_once()
    
    @patch('firebase_admin.firestore.client')
    def test_firestore_initialization(self, mock_client):
        """Test Firestore initialization."""
        # Mock successful Firestore client
        mock_client.return_value = MagicMock()
        mock_client.return_value.collection.return_value.limit.return_value.get.return_value = []
        
        # Test initialization
        result = FirebaseManager._initialize_firestore()
        self.assertTrue(result)
        mock_client.assert_called_once()
    
    @patch('pyrebase.initialize_app')
    def test_firebase_client_initialization(self, mock_init):
        """Test Firebase Client SDK initialization."""
        # Mock successful initialization
        mock_firebase = MagicMock()
        mock_firebase.auth.return_value = MagicMock()
        mock_init.return_value = mock_firebase
        
        # Test initialization
        result = FirebaseManager._initialize_firebase_client()
        self.assertTrue(result)
        mock_init.assert_called_once()
    
    def test_connection_check(self):
        """Test connection checking mechanism."""
        # Set up initial state
        FirebaseManager._db = MagicMock()
        FirebaseManager._db.collection.return_value.limit.return_value.get.return_value = []
        FirebaseManager._last_connection_check = 0
        
        # Test connection check
        result = FirebaseManager._check_connection()
        self.assertTrue(result)
        self.assertGreater(FirebaseManager._last_connection_check, 0)
    
    @patch('modules.core.firebase_manager.FirebaseManager._initialize_firebase_admin')
    @patch('modules.core.firebase_manager.FirebaseManager._initialize_firestore')
    @patch('modules.core.firebase_manager.FirebaseManager._initialize_firebase_client')
    def test_full_initialization(self, mock_client, mock_firestore, mock_admin):
        """Test complete initialization process."""
        # Mock successful initialization of all components
        mock_admin.return_value = True
        mock_firestore.return_value = True
        mock_client.return_value = True
        
        # Test initialization
        result = FirebaseManager.initialize()
        self.assertTrue(result)
        self.assertTrue(FirebaseManager._initialized)
        
        # Test re-initialization (should use existing instance)
        result = FirebaseManager.initialize()
        self.assertTrue(result)
        mock_admin.assert_called_once()  # Should only be called once
    
    @patch('modules.core.firebase_manager.FirebaseManager._initialize_firebase_admin')
    @patch('modules.core.firebase_manager.FirebaseManager._initialize_firestore')
    @patch('modules.core.firebase_manager.FirebaseManager._initialize_firebase_client')
    def test_initialization_failure(self, mock_client, mock_firestore, mock_admin):
        """Test initialization failure handling."""
        # Mock failure in one component
        mock_admin.return_value = False
        mock_firestore.return_value = True
        mock_client.return_value = True
        
        # Test initialization
        result = FirebaseManager.initialize()
        self.assertFalse(result)
        self.assertFalse(FirebaseManager._initialized)
    
    def test_connection_loss_recovery(self):
        """Test connection loss and recovery."""
        # Set up initial state
        FirebaseManager._db = MagicMock()
        FirebaseManager._db.collection.return_value.limit.return_value.get.side_effect = [
            Exception("Connection lost"),  # First call fails
            []  # Second call succeeds
        ]
        FirebaseManager._last_connection_check = 0
        
        # Test connection check with failure
        result = FirebaseManager._check_connection()
        self.assertFalse(result)
        
        # Test connection recovery
        result = FirebaseManager._check_connection()
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main() 