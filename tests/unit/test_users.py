import sys
import json

import pytest

# conftest sets up fake Firestore in sys.modules
fake_firestore = sys.modules.get("firebase_admin.firestore")

from backend.api import users_bp
from backend.api import users as users_module


def test_get_user_role_404(client, mock_db, monkeypatch):
    # Mock the firestore client to return our mock_db
    monkeypatch.setattr(fake_firestore, "client", lambda: mock_db)
    
    # Mock document that doesn't exist
    mock_doc = type('obj', (object,), {'exists': False, 'to_dict': lambda self: {}})()
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    
    res = client.get("/api/users/missing-user/role")
    assert res.status_code == 404
    data = res.get_json()
    assert data["error"] == "User not found"


def test_get_user_role_default_staff(client, mock_db, monkeypatch):
    # Mock the firestore client to return our mock_db
    monkeypatch.setattr(fake_firestore, "client", lambda: mock_db)
    
    # Mock document that exists
    mock_doc = type('obj', (object,), {
        'exists': True,
        'to_dict': lambda self: {
            "user_id": "u1",
            "name": "User One",
            "email": "u1@example.com",
        }
    })()
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

    res = client.get("/api/users/u1/role")
    assert res.status_code == 200
    data = res.get_json()
    assert data["user_id"] == "u1"
    assert data["role"] == "staff"


def test_get_user_role_manager(client, mock_db, monkeypatch):
    # Mock the firestore client to return our mock_db
    monkeypatch.setattr(fake_firestore, "client", lambda: mock_db)
    
    # Mock document that exists
    mock_doc = type('obj', (object,), {
        'exists': True,
        'to_dict': lambda self: {
            "user_id": "u2",
            "name": "Manager Two",
            "email": "u2@example.com",
            "role": "manager",
        }
    })()
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

    res = client.get("/api/users/u2/role")
    assert res.status_code == 200
    data = res.get_json()
    assert data["user_id"] == "u2"
    assert data["role"] == "manager"

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
import sys

# Get fake_firestore from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")

from flask import Flask
from backend.api import users_bp
from backend.api import users as users_module


# app and client fixtures provided by conftest.py


class TestNowIso:
    """Test the now_iso helper function"""
    
    def test_now_iso_returns_iso_format(self):
        """Test that now_iso returns ISO formatted datetime string"""
        # Mock datetime to control the timestamp
        mock_dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        with patch('backend.api.users.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_dt
            
            result = users_module.now_iso()
            
            assert result == "2024-01-15T10:30:45+00:00"
            mock_datetime.now.assert_called_once_with(timezone.utc)


class TestGetUserByEmail:
    """Test the get_user_by_email helper function"""
    
    def test_get_user_by_email_found(self):
        """Test finding a user by email"""
        mock_db = Mock()
        mock_doc = Mock()
        mock_doc.id = "user123"
        mock_doc.to_dict.return_value = {
            "user_id": "user123",
            "name": "John Doe",
            "email": "john@example.com",
            "created_at": "2024-01-01T00:00:00+00:00"
        }
        
        # Mock the query chain
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [mock_doc]
        
        result = users_module.get_user_by_email(mock_db, "john@example.com")
        
        assert result is not None
        assert result["id"] == "user123"
        assert result["user_id"] == "user123"
        assert result["name"] == "John Doe"
        assert result["email"] == "john@example.com"
        
        # Verify the query was constructed correctly
        mock_db.collection.assert_called_with("users")
        # New FieldFilter syntax uses filter parameter
        assert mock_db.collection.return_value.where.called
        call_kwargs = mock_db.collection.return_value.where.call_args[1]
        assert 'filter' in call_kwargs
        mock_db.collection.return_value.where.return_value.limit.assert_called_with(1)
        
    def test_get_user_by_email_not_found(self):
        """Test when user with email doesn't exist"""
        mock_db = Mock()
        
        # Mock empty result
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        result = users_module.get_user_by_email(mock_db, "nonexistent@example.com")
        
        assert result is None


class TestCreateUser:
    """Test the create_user POST endpoint"""
    
    def test_create_user_success(self, client, mock_db, monkeypatch):
        """Test successfully creating a new user"""
        # Setup mocks
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = False
        mock_ref.get.return_value = mock_get_result
        
        mock_db.collection.return_value.document.return_value = mock_ref
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Make request
        payload = {
            "user_id": "user123",
            "name": "John Doe",
            "email": "john@example.com"
        }
        response = client.post("/api/users", json=payload)
        
        # Assertions
        assert response.status_code == 201
        data = response.get_json()
        assert "user" in data
        assert data["user"]["user_id"] == "user123"
        assert data["user"]["name"] == "John Doe"
        assert data["user"]["email"] == "john@example.com"
        assert "created_at" in data["user"]
        
        # Verify database calls
        mock_db.collection.assert_called_with("users")
        mock_ref.set.assert_called_once()
        
    def test_create_user_email_lowercase(self, client, mock_db, monkeypatch):
        """Test that email is converted to lowercase"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = False
        mock_ref.get.return_value = mock_get_result
        
        mock_db.collection.return_value.document.return_value = mock_ref
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "user_id": "user123",
            "name": "John Doe",
            "email": "JOHN@EXAMPLE.COM"
        }
        response = client.post("/api/users", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["user"]["email"] == "john@example.com"
        
    def test_create_user_trims_whitespace(self, client, mock_db, monkeypatch):
        """Test that user_id, name, and email are trimmed"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = False
        mock_ref.get.return_value = mock_get_result
        
        mock_db.collection.return_value.document.return_value = mock_ref
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "user_id": "  user123  ",
            "name": "  John Doe  ",
            "email": "  john@example.com  "
        }
        response = client.post("/api/users", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["user"]["user_id"] == "user123"
        assert data["user"]["name"] == "John Doe"
        assert data["user"]["email"] == "john@example.com"
        
    def test_create_user_missing_user_id(self, client, mock_db, monkeypatch):
        """Test error when user_id is missing"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "John Doe",
            "email": "john@example.com"
        }
        response = client.post("/api/users", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "user_id, name and email are required" in data["error"]
        
    def test_create_user_missing_name(self, client, mock_db, monkeypatch):
        """Test error when name is missing"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "user_id": "user123",
            "email": "john@example.com"
        }
        response = client.post("/api/users", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "user_id, name and email are required" in data["error"]
        
    def test_create_user_missing_email(self, client, mock_db, monkeypatch):
        """Test error when email is missing"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "user_id": "user123",
            "name": "John Doe"
        }
        response = client.post("/api/users", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "user_id, name and email are required" in data["error"]
        
    def test_create_user_empty_user_id(self, client, mock_db, monkeypatch):
        """Test error when user_id is empty string"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "user_id": "",
            "name": "John Doe",
            "email": "john@example.com"
        }
        response = client.post("/api/users", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        
    def test_create_user_empty_name(self, client, mock_db, monkeypatch):
        """Test error when name is empty string"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "user_id": "user123",
            "name": "",
            "email": "john@example.com"
        }
        response = client.post("/api/users", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        
    def test_create_user_empty_email(self, client, mock_db, monkeypatch):
        """Test error when email is empty string"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "user_id": "user123",
            "name": "John Doe",
            "email": ""
        }
        response = client.post("/api/users", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        
    def test_create_user_whitespace_only_fields(self, client, mock_db, monkeypatch):
        """Test error when fields are only whitespace"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "user_id": "   ",
            "name": "   ",
            "email": "   "
        }
        response = client.post("/api/users", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        
    def test_create_user_already_exists(self, client, mock_db, monkeypatch):
        """Test error when user_id already exists"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = True  # User already exists
        mock_ref.get.return_value = mock_get_result
        
        mock_db.collection.return_value.document.return_value = mock_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "user_id": "user123",
            "name": "John Doe",
            "email": "john@example.com"
        }
        response = client.post("/api/users", json=payload)
        
        assert response.status_code == 409
        data = response.get_json()
        assert "error" in data
        assert "User already exists" in data["error"]
        
    def test_create_user_email_already_exists(self, client, mock_db, monkeypatch):
        """Test error when email already exists"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = False
        mock_ref.get.return_value = mock_get_result
        
        # Mock existing user with same email
        mock_existing_user = Mock()
        mock_existing_user.id = "other_user"
        mock_existing_user.to_dict.return_value = {
            "user_id": "other_user",
            "name": "Other User",
            "email": "john@example.com"
        }
        
        mock_db.collection.return_value.document.return_value = mock_ref
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [mock_existing_user]
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "user_id": "user123",
            "name": "John Doe",
            "email": "john@example.com"
        }
        response = client.post("/api/users", json=payload)
        
        assert response.status_code == 409
        data = response.get_json()
        assert "error" in data
        assert "Email already exists" in data["error"]
        
    def test_create_user_empty_payload(self, client, mock_db, monkeypatch):
        """Test error when payload is empty"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post("/api/users", json={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data


class TestGetUser:
    """Test the get_user GET endpoint"""
    
    def test_get_user_success(self, client, mock_db, monkeypatch):
        """Test successfully retrieving a user"""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "user_id": "user123",
            "name": "John Doe",
            "email": "john@example.com",
            "created_at": "2024-01-01T00:00:00+00:00"
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/users/user123")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["user_id"] == "user123"
        assert data["name"] == "John Doe"
        assert data["email"] == "john@example.com"
        
        # Verify database calls
        mock_db.collection.assert_called_with("users")
        mock_db.collection.return_value.document.assert_called_with("user123")
        
    def test_get_user_not_found(self, client, mock_db, monkeypatch):
        """Test error when user doesn't exist"""
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/users/nonexistent")
        
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "User not found" in data["error"]


class TestBlueprintRegistration:
    """Test blueprint is properly registered"""
    
    def test_blueprint_registered(self, client, mock_db, monkeypatch):
        """Test that users blueprint is registered with correct prefix"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Test the POST endpoint is accessible
        response = client.post("/api/users", json={})
        # Should return 400 (validation error) not 404 (not found)
        assert response.status_code == 400
        
        # Test the GET endpoint is accessible
        mock_doc = Mock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        response = client.get("/api/users/test")
        # Should return 404 (user not found), not 404 (endpoint not found)
        assert response.status_code == 404


class TestEdgeCases:
    """Test edge cases and integration scenarios"""
    
    def test_create_user_with_special_characters_in_name(self, client, mock_db, monkeypatch):
        """Test creating user with special characters in name"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = False
        mock_ref.get.return_value = mock_get_result
        
        mock_db.collection.return_value.document.return_value = mock_ref
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "user_id": "user123",
            "name": "O'Brien-Smith, Jr.",
            "email": "john@example.com"
        }
        response = client.post("/api/users", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["user"]["name"] == "O'Brien-Smith, Jr."
        
    def test_create_user_with_mixed_case_email(self, client, mock_db, monkeypatch):
        """Test that mixed case email is normalized to lowercase"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = False
        mock_ref.get.return_value = mock_get_result
        
        mock_db.collection.return_value.document.return_value = mock_ref
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "user_id": "user123",
            "name": "John Doe",
            "email": "John.Doe@Example.COM"
        }
        response = client.post("/api/users", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["user"]["email"] == "john.doe@example.com"
        
    def test_get_user_with_special_characters_in_id(self, client, mock_db, monkeypatch):
        """Test retrieving user with special characters in user_id"""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "user_id": "user-123_test",
            "name": "Test User",
            "email": "test@example.com",
            "created_at": "2024-01-01T00:00:00+00:00"
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/users/user-123_test")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["user_id"] == "user-123_test"
