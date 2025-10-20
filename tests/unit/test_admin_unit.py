"""Unit tests for admin.py module"""
import pytest
from unittest.mock import Mock, patch
import sys

# Get fake modules from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")
fake_auth = sys.modules.get("firebase_admin.auth")

# Get the UserNotFoundError from fake_auth
UserNotFoundError = fake_auth.UserNotFoundError

from flask import Flask
from backend.api import users_bp


# app, client, and mock_db fixtures provided by conftest.py


class TestAdminEndpoints:
    """Test admin diagnostic endpoints"""
    
    def test_check_user_sync_synced(self, client, mock_db, monkeypatch):
        """Test checking a user that exists in both Firestore and Firebase Auth"""
        user_id = "test_user_123"
        
        # Mock Firestore document
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "user_id": user_id,
            "name": "Test User",
            "email": "test@example.com"
        }
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth user
        mock_firebase_user = Mock()
        mock_firebase_user.uid = user_id
        mock_firebase_user.email = "test@example.com"
        mock_firebase_user.display_name = "Test User"
        mock_firebase_user.disabled = False
        mock_firebase_user.email_verified = True
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "get_user", Mock(return_value=mock_firebase_user))
        
        response = client.get(f"/api/users/admin/check/{user_id}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["user_id"] == user_id
        assert data["in_firestore"] == True
        assert data["in_firebase_auth"] == True
        assert data["synced"] == True
    
    def test_check_user_sync_firestore_only(self, client, mock_db, monkeypatch):
        """Test checking a user that exists only in Firestore"""
        user_id = "orphan_firestore_user"
        
        # Mock Firestore document exists
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "user_id": user_id,
            "name": "Orphaned User",
            "email": "orphan@example.com"
        }
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth user not found
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "get_user", Mock(side_effect=UserNotFoundError("User not found")))
        
        response = client.get(f"/api/users/admin/check/{user_id}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["user_id"] == user_id
        assert data["in_firestore"] == True
        assert data["in_firebase_auth"] == False
        assert data["synced"] == False
    
    def test_check_user_sync_auth_only(self, client, mock_db, monkeypatch):
        """Test checking a user that exists only in Firebase Auth"""
        user_id = "orphan_auth_user"
        
        # Mock Firestore document does not exist
        mock_doc = Mock()
        mock_doc.exists = False
        mock_doc.to_dict.return_value = None
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth user exists
        mock_firebase_user = Mock()
        mock_firebase_user.uid = user_id
        mock_firebase_user.email = "auth@example.com"
        mock_firebase_user.display_name = "Auth User"
        mock_firebase_user.disabled = False
        mock_firebase_user.email_verified = True
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "get_user", Mock(return_value=mock_firebase_user))
        
        response = client.get(f"/api/users/admin/check/{user_id}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["user_id"] == user_id
        assert data["in_firestore"] == False
        assert data["in_firebase_auth"] == True
        assert data["synced"] == False
    
    def test_check_user_sync_not_found(self, client, mock_db, monkeypatch):
        """Test checking a user that doesn't exist anywhere"""
        user_id = "nonexistent_user"
        
        # Mock Firestore document does not exist
        mock_doc = Mock()
        mock_doc.exists = False
        mock_doc.to_dict.return_value = None
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth user not found
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "get_user", Mock(side_effect=UserNotFoundError("User not found")))
        
        response = client.get(f"/api/users/admin/check/{user_id}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["user_id"] == user_id
        assert data["in_firestore"] == False
        assert data["in_firebase_auth"] == False
        assert data["synced"] == True  # Both False == synced
    
    def test_cleanup_user_without_confirmation(self, client, mock_db, monkeypatch):
        """Test cleanup endpoint without confirmation parameter"""
        user_id = "test_user"
        
        response = client.delete(f"/api/users/admin/cleanup/{user_id}")
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "Confirmation required" in data["error"]
    
    def test_cleanup_user_with_confirmation(self, client, mock_db, monkeypatch):
        """Test cleanup endpoint with confirmation"""
        user_id = "test_user"
        
        # Mock Firestore document
        mock_doc = Mock()
        mock_doc.exists = True
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_doc_ref.delete = Mock()
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth delete
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "delete_user", Mock())
        
        response = client.delete(f"/api/users/admin/cleanup/{user_id}?confirm=true")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["firestore_deleted"] == True
        assert data["firebase_auth_deleted"] == True
    
    def test_cleanup_user_not_found(self, client, mock_db, monkeypatch):
        """Test cleanup endpoint when user doesn't exist"""
        user_id = "nonexistent_user"
        
        # Mock Firestore document does not exist
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth user not found
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "delete_user", Mock(side_effect=UserNotFoundError("User not found")))
        
        response = client.delete(f"/api/users/admin/cleanup/{user_id}?confirm=true")
        
        assert response.status_code == 404
        data = response.get_json()
        assert data["firestore_deleted"] == False
        assert data["firebase_auth_deleted"] == False
    
    def test_sync_user_already_synced(self, client, mock_db, monkeypatch):
        """Test sync endpoint when user is already synced"""
        user_id = "synced_user"
        
        # Mock Firestore document exists
        mock_doc = Mock()
        mock_doc.exists = True
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth user exists
        mock_firebase_user = Mock()
        mock_firebase_user.uid = user_id
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "get_user", Mock(return_value=mock_firebase_user))
        
        response = client.post(f"/api/users/admin/sync/{user_id}", json={})
        
        # Debug print
        if response.status_code != 200:
            print(f"Response: {response.get_json()}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "Already synced" in data["status"]
    
    def test_sync_user_firestore_only_no_password(self, client, mock_db, monkeypatch):
        """Test sync endpoint for Firestore-only user without password"""
        user_id = "firestore_only_user"
        
        # Mock Firestore document exists
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "user_id": user_id,
            "email": "test@example.com",
            "name": "Test User"
        }
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth user not found
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "get_user", Mock(side_effect=UserNotFoundError("User not found")))
        
        response = client.post(f"/api/users/admin/sync/{user_id}", json={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Password required" in data["error"]
    
    def test_sync_user_firestore_only_with_password(self, client, mock_db, monkeypatch):
        """Test sync endpoint for Firestore-only user with password"""
        user_id = "firestore_only_user"
        
        # Mock Firestore document exists
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "user_id": user_id,
            "email": "test@example.com",
            "name": "Test User"
        }
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_doc_ref.update = Mock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth create user
        mock_new_user = Mock()
        mock_new_user.uid = user_id
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "get_user", Mock(side_effect=UserNotFoundError("User not found")))
        monkeypatch.setattr(fake_auth, "create_user", Mock(return_value=mock_new_user))
        
        response = client.post(f"/api/users/admin/sync/{user_id}", json={"password": "TestPass123"})
        
        assert response.status_code == 201
        data = response.get_json()
        assert "Synced" in data["status"]
    
    def test_sync_user_auth_only(self, client, mock_db, monkeypatch):
        """Test sync endpoint for Firebase Auth-only user"""
        user_id = "auth_only_user"
        
        # Mock Firestore document does not exist
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_doc_ref.set = Mock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth user exists
        mock_firebase_user = Mock()
        mock_firebase_user.uid = user_id
        mock_firebase_user.email = "auth@example.com"
        mock_firebase_user.display_name = "Auth User"
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "get_user", Mock(return_value=mock_firebase_user))
        
        response = client.post(f"/api/users/admin/sync/{user_id}", json={})
        
        assert response.status_code == 201
        data = response.get_json()
        assert "Synced" in data["status"]
        assert "Firestore document" in data["message"]
    
    def test_sync_user_not_found(self, client, mock_db, monkeypatch):
        """Test sync endpoint when user doesn't exist anywhere"""
        user_id = "nonexistent_user"
        
        # Mock Firestore document does not exist
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth user not found
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "get_user", Mock(side_effect=UserNotFoundError("User not found")))
        
        response = client.post(f"/api/users/admin/sync/{user_id}", json={})
        
        assert response.status_code == 404
        data = response.get_json()
        assert "Not found" in data["status"]
    
    def test_check_user_sync_auth_exception(self, client, mock_db, monkeypatch):
        """Test check endpoint when Firebase Auth raises generic exception"""
        user_id = "error_user"
        
        # Mock Firestore document exists
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"email": "test@example.com"}
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth raises generic exception
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "get_user", Mock(side_effect=Exception("Firebase error")))
        
        response = client.get(f"/api/users/admin/check/{user_id}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "firebase_data" in data
        assert "error" in data["firebase_data"]
    
    def test_cleanup_user_firestore_exception(self, client, mock_db, monkeypatch):
        """Test cleanup endpoint when Firestore raises exception"""
        user_id = "error_user"
        
        # Mock Firestore to raise exception
        mock_doc_ref = Mock()
        mock_doc_ref.get.side_effect = Exception("Firestore error")
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth delete
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "delete_user", Mock())
        
        response = client.delete(f"/api/users/admin/cleanup/{user_id}?confirm=true")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["firestore_deleted"] == False
        assert any("Firestore deletion failed" in error for error in data["errors"])
        assert data["firebase_auth_deleted"] == True
    
    def test_cleanup_user_auth_exception(self, client, mock_db, monkeypatch):
        """Test cleanup endpoint when Firebase Auth raises generic exception"""
        user_id = "error_user"
        
        # Mock Firestore document exists
        mock_doc = Mock()
        mock_doc.exists = True
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_doc_ref.delete = Mock()
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth raises exception
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "delete_user", Mock(side_effect=Exception("Auth error")))
        
        response = client.delete(f"/api/users/admin/cleanup/{user_id}?confirm=true")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["firestore_deleted"] == True
        assert data["firebase_auth_deleted"] == False
        assert any("Firebase Auth deletion failed" in error for error in data["errors"])
    
    def test_sync_user_create_auth_exception(self, client, mock_db, monkeypatch):
        """Test sync endpoint when Firebase Auth create_user raises exception"""
        user_id = "error_user"
        
        # Mock Firestore document exists
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "user_id": user_id,
            "email": "test@example.com",
            "name": "Test User"
        }
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth get_user not found, create_user raises exception
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "get_user", Mock(side_effect=UserNotFoundError("User not found")))
        monkeypatch.setattr(fake_auth, "create_user", Mock(side_effect=Exception("Create failed")))
        
        response = client.post(f"/api/users/admin/sync/{user_id}", json={"password": "TestPass123"})
        
        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data
        assert "Failed to create Firebase Auth user" in data["error"]


