import sys
import os
import traceback
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Firebase modules
from modules.firebase.config import get_firebase_app, db
from firebase_admin import firestore

def test_firebase_connection():
    """Test Firebase connection and basic operations"""
    print("Starting Firebase connection test...")
    
    try:
        # Get Firebase app
        print("Getting Firebase app...")
        app = get_firebase_app()
        print(f"Firebase app initialized: {app.name}")
        
        # Get Firestore client
        print("Getting Firestore client...")
        firestore_client = firestore.client(app)
        print("Firestore client initialized")
        
        # Try to create a test document
        print("Creating test document...")
        test_collection = firestore_client.collection('test')
        test_doc = test_collection.document('connection_test')
        test_doc.set({
            'timestamp': datetime.now().isoformat(),
            'message': 'Firebase connection test successful'
        })
        print("Test document created successfully")
        
        # Try to read the test document
        print("Reading test document...")
        doc = test_doc.get()
        if doc.exists:
            print(f"Test document read successfully: {doc.to_dict()}")
        else:
            print("Test document does not exist")
        
        # Clean up test document
        print("Cleaning up test document...")
        test_doc.delete()
        print("Test document deleted successfully")
        
        print("Firebase connection test completed successfully!")
        return True
    except Exception as e:
        print(f"Error during Firebase connection test: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_firebase_connection()
    if success:
        print("Firebase is working correctly!")
    else:
        print("Firebase connection test failed. Check the error messages above.") 