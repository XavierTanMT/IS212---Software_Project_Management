"""Unit tests for backend/firebase_utils.py"""

import os
import json
import pytest
from unittest.mock import patch, mock_open
import sys

# Ensure backend is in path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backend.firebase_utils import get_firebase_credentials


class TestGetFirebaseCredentials:
    """Test suite for get_firebase_credentials function."""
    
    def test_option1_json_string(self, monkeypatch, tmp_path):
        """Test Option 1: FIREBASE_CREDENTIALS_JSON as JSON string."""
        creds_data = {
            "type": "service_account",
            "project_id": "test-project-1",
            "private_key": "fake-key"
        }
        
        monkeypatch.setenv("FIREBASE_CREDENTIALS_JSON", json.dumps(creds_data))
        
        result = get_firebase_credentials()
        
        assert result == creds_data
        assert result["project_id"] == "test-project-1"
    
    def test_option1_file_path(self, monkeypatch, tmp_path):
        """Test Option 1: FIREBASE_CREDENTIALS_JSON as file path."""
        creds_file = tmp_path / "creds.json"
        creds_data = {
            "type": "service_account",
            "project_id": "test-project-2",
            "private_key": "fake-key-2"
        }
        creds_file.write_text(json.dumps(creds_data))
        
        monkeypatch.setenv("FIREBASE_CREDENTIALS_JSON", str(creds_file))
        
        result = get_firebase_credentials()
        
        assert result == creds_data
        assert result["project_id"] == "test-project-2"
    
    def test_option2_credentials_path(self, monkeypatch, tmp_path):
        """Test Option 2: FIREBASE_CREDENTIALS_PATH (covers lines 37-38)."""
        creds_file = tmp_path / "firebase_creds.json"
        creds_data = {
            "type": "service_account",
            "project_id": "test-project-path",
            "private_key": "fake-key-path"
        }
        creds_file.write_text(json.dumps(creds_data))
        
        # Unset FIREBASE_CREDENTIALS_JSON so it falls through to option 2
        monkeypatch.delenv("FIREBASE_CREDENTIALS_JSON", raising=False)
        monkeypatch.setenv("FIREBASE_CREDENTIALS_PATH", str(creds_file))
        
        result = get_firebase_credentials()
        
        assert result == creds_data
        assert result["project_id"] == "test-project-path"
    
    def test_option3_google_application_credentials(self, monkeypatch, tmp_path):
        """Test Option 3: GOOGLE_APPLICATION_CREDENTIALS (covers line 48)."""
        creds_file = tmp_path / "google_creds.json"
        creds_data = {
            "type": "service_account",
            "project_id": "test-google-project",
            "private_key": "fake-google-key"
        }
        creds_file.write_text(json.dumps(creds_data))
        
        # Unset previous options so it falls through to option 3
        monkeypatch.delenv("FIREBASE_CREDENTIALS_JSON", raising=False)
        monkeypatch.delenv("FIREBASE_CREDENTIALS_PATH", raising=False)
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds_file))
        
        result = get_firebase_credentials()
        
        assert result == creds_data
        assert result["project_id"] == "test-google-project"
    
    def test_option4_individual_env_vars(self, monkeypatch):
        """Test Option 4: Individual environment variables."""
        # Unset all other options
        monkeypatch.delenv("FIREBASE_CREDENTIALS_JSON", raising=False)
        monkeypatch.delenv("FIREBASE_CREDENTIALS_PATH", raising=False)
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        
        # Set individual env vars
        monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-env-project")
        monkeypatch.setenv("FIREBASE_PRIVATE_KEY_ID", "test-key-id")
        monkeypatch.setenv("FIREBASE_PRIVATE_KEY", "-----BEGIN PRIVATE KEY-----\\ntest\\n-----END PRIVATE KEY-----")
        monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", "test@example.com")
        monkeypatch.setenv("FIREBASE_CLIENT_ID", "12345")
        monkeypatch.setenv("FIREBASE_CLIENT_CERT_URL", "https://example.com/cert")
        
        result = get_firebase_credentials()
        
        assert result["type"] == "service_account"
        assert result["project_id"] == "test-env-project"
        assert result["private_key_id"] == "test-key-id"
        assert result["private_key"] == "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----"
        assert result["client_email"] == "test@example.com"
        assert result["client_id"] == "12345"
        assert result["auth_uri"] == "https://accounts.google.com/o/oauth2/auth"
        assert result["token_uri"] == "https://oauth2.googleapis.com/token"
    
    def test_no_credentials_raises_error(self, monkeypatch):
        """Test that ValueError is raised when no credentials are found."""
        # Unset all credential options
        monkeypatch.delenv("FIREBASE_CREDENTIALS_JSON", raising=False)
        monkeypatch.delenv("FIREBASE_CREDENTIALS_PATH", raising=False)
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
        
        with pytest.raises(ValueError) as exc_info:
            get_firebase_credentials()
        
        assert "Firebase credentials not found" in str(exc_info.value)
    
    def test_option1_nonexistent_file(self, monkeypatch):
        """Test Option 1: When file path doesn't exist, falls through."""
        # Set to a non-existent file path
        monkeypatch.setenv("FIREBASE_CREDENTIALS_JSON", "/nonexistent/path/creds.json")
        monkeypatch.delenv("FIREBASE_CREDENTIALS_PATH", raising=False)
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
        
        with pytest.raises(ValueError) as exc_info:
            get_firebase_credentials()
        
        assert "Firebase credentials not found" in str(exc_info.value)
    
    def test_option2_nonexistent_file(self, monkeypatch):
        """Test Option 2: When FIREBASE_CREDENTIALS_PATH doesn't exist, falls through."""
        monkeypatch.delenv("FIREBASE_CREDENTIALS_JSON", raising=False)
        monkeypatch.setenv("FIREBASE_CREDENTIALS_PATH", "/nonexistent/firebase.json")
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
        
        with pytest.raises(ValueError) as exc_info:
            get_firebase_credentials()
        
        assert "Firebase credentials not found" in str(exc_info.value)
    
    def test_option3_nonexistent_file(self, monkeypatch):
        """Test Option 3: When GOOGLE_APPLICATION_CREDENTIALS doesn't exist, falls through."""
        monkeypatch.delenv("FIREBASE_CREDENTIALS_JSON", raising=False)
        monkeypatch.delenv("FIREBASE_CREDENTIALS_PATH", raising=False)
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/nonexistent/google.json")
        monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
        
        with pytest.raises(ValueError) as exc_info:
            get_firebase_credentials()
        
        assert "Firebase credentials not found" in str(exc_info.value)
    
    def test_priority_option1_over_option2(self, monkeypatch, tmp_path):
        """Test that Option 1 takes priority over Option 2."""
        # Create two different credential files
        creds1 = tmp_path / "creds1.json"
        creds1_data = {"type": "service_account", "project_id": "priority-1"}
        creds1.write_text(json.dumps(creds1_data))
        
        creds2 = tmp_path / "creds2.json"
        creds2_data = {"type": "service_account", "project_id": "priority-2"}
        creds2.write_text(json.dumps(creds2_data))
        
        # Set both options
        monkeypatch.setenv("FIREBASE_CREDENTIALS_JSON", str(creds1))
        monkeypatch.setenv("FIREBASE_CREDENTIALS_PATH", str(creds2))
        
        result = get_firebase_credentials()
        
        # Should use Option 1
        assert result["project_id"] == "priority-1"
    
    def test_priority_option2_over_option3(self, monkeypatch, tmp_path):
        """Test that Option 2 takes priority over Option 3."""
        # Create two different credential files
        creds2 = tmp_path / "creds2.json"
        creds2_data = {"type": "service_account", "project_id": "priority-2"}
        creds2.write_text(json.dumps(creds2_data))
        
        creds3 = tmp_path / "creds3.json"
        creds3_data = {"type": "service_account", "project_id": "priority-3"}
        creds3.write_text(json.dumps(creds3_data))
        
        # Unset Option 1, set Options 2 and 3
        monkeypatch.delenv("FIREBASE_CREDENTIALS_JSON", raising=False)
        monkeypatch.setenv("FIREBASE_CREDENTIALS_PATH", str(creds2))
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds3))
        
        result = get_firebase_credentials()
        
        # Should use Option 2
        assert result["project_id"] == "priority-2"
