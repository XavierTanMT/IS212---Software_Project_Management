import os
from dotenv import load_dotenv
from firebase_admin import credentials, initialize_app, firestore, auth

# Load environment variables
load_dotenv()

class FirebaseConfig:
    def __init__(self):
        self.project_id = os.getenv('FIREBASE_PROJECT_ID')
        self.credentials_path = os.getenv('FIREBASE_CREDENTIALS_PATH', './serviceAccountKey.json')
        
        if not self.project_id:
            raise ValueError("FIREBASE_PROJECT_ID environment variable is required")
        
        # Initialize Firebase Admin SDK
        if os.path.exists(self.credentials_path):
            cred = credentials.Certificate(self.credentials_path)
            initialize_app(cred, {'projectId': self.project_id})
        else:
            # For production deployment (e.g., Google Cloud Run)
            initialize_app()
        
        # Initialize Firestore
        self.db = firestore.client()
        
        print(f"✅ Firebase initialized for project: {self.project_id}")

# Global Firebase instance
firebase_config = FirebaseConfig()
db = firebase_config.db
