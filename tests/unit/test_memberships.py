import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
import sys

# Get fake_firestore from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")

from flask import Flask
from backend.api import memberships_bp
from backend.api import memberships as memberships_module


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = Flask('test_memberships_app')
    app.config['TESTING'] = True
    # Use try-except to handle blueprint already registered
    try:
        app.register_blueprint(memberships_bp)
    except AssertionError:
        # Blueprint already registered, that's okay
        pass
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


class TestNowIso:
    """Test the now_iso helper function"""
    
    def test_now_iso_returns_iso_format(self):
        """Test that now_iso returns ISO formatted datetime string"""
        # Mock datetime to control the timestamp
        mock_dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        with patch('backend.api.memberships.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_dt
            
            result = memberships_module.now_iso()
            
            assert result == "2024-01-15T10:30:45+00:00"
            mock_datetime.now.assert_called_once_with(timezone.utc)


class TestAddMember:
    """Test the add_member POST endpoint"""
    
    def test_add_member_success(self, client, mock_db, monkeypatch):
        """Test successfully adding a member to a project"""
        # Setup mock
        mock_ref = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Make request
        payload = {
            "project_id": "proj123",
            "user_id": "user456",
            "role": "admin"
        }
        response = client.post("/api/memberships", json=payload)
        
        # Assertions
        assert response.status_code == 201
        data = response.get_json()
        assert data["project_id"] == "proj123"
        assert data["user_id"] == "user456"
        assert data["role"] == "admin"
        assert "added_at" in data
        
        # Verify database calls
        mock_db.collection.assert_called_with("memberships")
        mock_db.collection.return_value.document.assert_called_with("proj123_user456")
        mock_ref.set.assert_called_once()
        
    def test_add_member_default_role(self, client, mock_db, monkeypatch):
        """Test that role defaults to 'contributor' when not provided"""
        mock_ref = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "project_id": "proj123",
            "user_id": "user456"
        }
        response = client.post("/api/memberships", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["role"] == "contributor"
        
    def test_add_member_trims_whitespace(self, client, mock_db, monkeypatch):
        """Test that project_id, user_id, and role are trimmed"""
        mock_ref = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "project_id": "  proj123  ",
            "user_id": "  user456  ",
            "role": "  admin  "
        }
        response = client.post("/api/memberships", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["project_id"] == "proj123"
        assert data["user_id"] == "user456"
        assert data["role"] == "admin"
        
        # Verify document name is trimmed
        mock_db.collection.return_value.document.assert_called_with("proj123_user456")
        
    def test_add_member_missing_project_id(self, client, mock_db, monkeypatch):
        """Test error when project_id is missing"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "user_id": "user456",
            "role": "admin"
        }
        response = client.post("/api/memberships", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "project_id and user_id are required" in data["error"]
        
    def test_add_member_missing_user_id(self, client, mock_db, monkeypatch):
        """Test error when user_id is missing"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "project_id": "proj123",
            "role": "admin"
        }
        response = client.post("/api/memberships", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "project_id and user_id are required" in data["error"]
        
    def test_add_member_empty_project_id(self, client, mock_db, monkeypatch):
        """Test error when project_id is empty string"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "project_id": "",
            "user_id": "user456"
        }
        response = client.post("/api/memberships", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        
    def test_add_member_empty_user_id(self, client, mock_db, monkeypatch):
        """Test error when user_id is empty string"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "project_id": "proj123",
            "user_id": ""
        }
        response = client.post("/api/memberships", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        
    def test_add_member_whitespace_only_project_id(self, client, mock_db, monkeypatch):
        """Test error when project_id is only whitespace"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "project_id": "   ",
            "user_id": "user456"
        }
        response = client.post("/api/memberships", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        
    def test_add_member_whitespace_only_user_id(self, client, mock_db, monkeypatch):
        """Test error when user_id is only whitespace"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "project_id": "proj123",
            "user_id": "   "
        }
        response = client.post("/api/memberships", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        
    def test_add_member_empty_payload(self, client, mock_db, monkeypatch):
        """Test error when payload is empty"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post("/api/memberships", json={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        
    def test_add_member_document_naming_convention(self, client, mock_db, monkeypatch):
        """Test that membership document is named correctly"""
        mock_ref = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "project_id": "myproject",
            "user_id": "myuser",
            "role": "viewer"
        }
        response = client.post("/api/memberships", json=payload)
        
        assert response.status_code == 201
        # Verify document is named {project_id}_{user_id}
        mock_db.collection.return_value.document.assert_called_with("myproject_myuser")


class TestListProjectMembers:
    """Test the list_project_members GET endpoint"""
    
    def test_list_project_members_success(self, client, mock_db, monkeypatch):
        """Test successfully listing members of a project"""
        # Setup mock documents
        mock_doc1 = Mock()
        mock_doc1.to_dict.return_value = {
            "project_id": "proj123",
            "user_id": "user1",
            "role": "admin",
            "added_at": "2024-01-01T00:00:00+00:00"
        }
        mock_doc2 = Mock()
        mock_doc2.to_dict.return_value = {
            "project_id": "proj123",
            "user_id": "user2",
            "role": "contributor",
            "added_at": "2024-01-02T00:00:00+00:00"
        }
        
        mock_db.collection.return_value.where.return_value.stream.return_value = [mock_doc1, mock_doc2]
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Make request
        response = client.get("/api/memberships/by-project/proj123")
        
        # Assertions
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        assert data[0]["user_id"] == "user1"
        assert data[0]["role"] == "admin"
        assert data[1]["user_id"] == "user2"
        assert data[1]["role"] == "contributor"
        
        # Verify database calls
        mock_db.collection.assert_called_with("memberships")
        mock_db.collection.return_value.where.assert_called_with("project_id", "==", "proj123")
        
    def test_list_project_members_empty_result(self, client, mock_db, monkeypatch):
        """Test listing members when project has no members"""
        mock_db.collection.return_value.where.return_value.stream.return_value = []
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/memberships/by-project/nonexistent")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data == []
        
    def test_list_project_members_single_member(self, client, mock_db, monkeypatch):
        """Test listing members when project has only one member"""
        mock_doc = Mock()
        mock_doc.to_dict.return_value = {
            "project_id": "proj456",
            "user_id": "owner1",
            "role": "owner",
            "added_at": "2024-01-01T00:00:00+00:00"
        }
        
        mock_db.collection.return_value.where.return_value.stream.return_value = [mock_doc]
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/memberships/by-project/proj456")
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["user_id"] == "owner1"
        assert data[0]["role"] == "owner"


class TestBlueprintRegistration:
    """Test blueprint is properly registered"""
    
    def test_blueprint_registered(self, client, mock_db, monkeypatch):
        """Test that memberships blueprint is registered with correct prefix"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        mock_db.collection.return_value.where.return_value.stream.return_value = []
        
        # Test the POST endpoint is accessible
        response = client.post("/api/memberships", json={})
        # Should return 400 (validation error) not 404 (not found)
        assert response.status_code == 400
        
        # Test the GET endpoint is accessible
        response = client.get("/api/memberships/by-project/test")
        # Should return 200, not 404
        assert response.status_code == 200


class TestEdgeCases:
    """Test edge cases and integration scenarios"""
    
    def test_add_member_with_special_characters_in_ids(self, client, mock_db, monkeypatch):
        """Test adding member with special characters in project_id and user_id"""
        mock_ref = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "project_id": "proj-123_test",
            "user_id": "user.456@test",
            "role": "contributor"
        }
        response = client.post("/api/memberships", json=payload)
        
        assert response.status_code == 201
        # Document name should include special characters
        mock_db.collection.return_value.document.assert_called_with("proj-123_test_user.456@test")
        
    def test_add_member_role_case_sensitivity(self, client, mock_db, monkeypatch):
        """Test that role value is case-sensitive and not modified"""
        mock_ref = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "project_id": "proj123",
            "user_id": "user456",
            "role": "Admin"  # Mixed case
        }
        response = client.post("/api/memberships", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["role"] == "Admin"  # Should preserve case
        
    def test_list_project_members_query_filter(self, client, mock_db, monkeypatch):
        """Test that the correct Firestore query is constructed"""
        mock_db.collection.return_value.where.return_value.stream.return_value = []
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/memberships/by-project/test_project_id")
        
        assert response.status_code == 200
        # Verify the where clause is correctly applied
        mock_db.collection.return_value.where.assert_called_with("project_id", "==", "test_project_id")
