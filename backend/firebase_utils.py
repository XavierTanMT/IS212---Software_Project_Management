"""Firebase credential utilities for loading credentials from various sources."""
import os
import json
from typing import Dict, Any


def get_firebase_credentials() -> Dict[str, Any]:
    """
    Load Firebase credentials from environment variables or file.
    
    Supports three methods:
    1. FIREBASE_CREDENTIALS_JSON - JSON string or path to JSON file
    2. FIREBASE_CREDENTIALS_PATH - path to service account JSON file
    3. Individual environment variables (FIREBASE_PROJECT_ID, etc.)
    
    Returns:
        Dict containing Firebase service account credentials
        
    Raises:
        ValueError: If no valid credentials are found
    """
    # Option 1: FIREBASE_CREDENTIALS_JSON (JSON string or path to JSON file)
    creds_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
    if creds_json:
        try:
            # Try parsing as JSON string first
            return json.loads(creds_json)
        except json.JSONDecodeError:
            # If it's a file path, load from file
            if os.path.exists(creds_json):
                with open(creds_json, 'r') as f:
                    return json.load(f)
    
    # Option 2: FIREBASE_CREDENTIALS_PATH (file path)
    creds_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
    if creds_path and os.path.exists(creds_path):
        with open(creds_path, 'r') as f:
            return json.load(f)
    
    # Option 3: GOOGLE_APPLICATION_CREDENTIALS (legacy support)
    google_creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if google_creds_path and os.path.exists(google_creds_path):
        with open(google_creds_path, 'r') as f:
            return json.load(f)
    
    # Option 4: Individual environment variables
    if os.getenv('FIREBASE_PROJECT_ID'):
        return {
            "type": "service_account",
            "project_id": os.getenv('FIREBASE_PROJECT_ID'),
            "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
            "private_key": os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
            "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
            "client_id": os.getenv('FIREBASE_CLIENT_ID'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_CERT_URL'),
            "universe_domain": "googleapis.com"
        }
    
    raise ValueError(
        "Firebase credentials not found. Please set one of:\n"
        "1. FIREBASE_CREDENTIALS_JSON (JSON string or path to JSON file)\n"
        "2. FIREBASE_CREDENTIALS_PATH (path to service account JSON file)\n"
        "3. GOOGLE_APPLICATION_CREDENTIALS (path to service account JSON file)\n"
        "4. Individual env vars (FIREBASE_PROJECT_ID, FIREBASE_PRIVATE_KEY, etc.)"
    )
