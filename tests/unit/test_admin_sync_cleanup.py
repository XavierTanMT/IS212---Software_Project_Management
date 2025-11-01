"""Tests for admin sync and cleanup endpoints to achieve 100% coverage."""

import pytest
from unittest.mock import Mock, patch
from conftest import UserNotFoundError
from datetime import datetime


@pytest.fixture
def fake_auth():
    """Mock Firebase Auth."""
    with patch('backend.api.admin.auth') as mock_auth:
        mock_auth.UserNotFoundError = UserNotFoundError
        yield mock_auth


@pytest.fixture
def fake_firestore():
    """Mock Firestore."""
    with patch('backend.api.admin.firestore') as mock_firestore:
        yield mock_firestore


class TestAdminSyncCleanup:
    """Test coverage for cleanup and sync endpoints (lines 775-808, 826-907, 917-922)"""

    # ==================== CLEANUP ENDPOINT TESTS ====================

    def test_cleanup_without_confirmation(self, client):
        """Cover lines 775-776, 737-740 - cleanup requires confirmation"""
        response = client.delete("/api/admin/cleanup/user123")
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Confirmation required" in data["error"]
        assert "warning" in data

    def test_cleanup_user_not_in_firestore(self, client, mock_db, fake_auth):
        """Cover lines 783-789 - user not found in Firestore"""
        # Mock Firestore user doesn't exist
        mock_doc = Mock()
        mock_doc.exists = False
        mock_user_ref = Mock()
        mock_user_ref.get.return_value = mock_doc
        mock_coll = Mock()
        mock_coll.document.return_value = mock_user_ref
        mock_db.collection.return_value = mock_coll

        # Mock Firebase Auth user doesn't exist
        fake_auth.delete_user.side_effect = UserNotFoundError("Not found")

        response = client.delete("/api/admin/cleanup/user123?confirm=true")
        
        assert response.status_code == 404
        data = response.get_json()
        assert data["status"] == "❌ Nothing to clean up"
        assert "User not found in Firestore" in data["errors"]
        assert "User not found in Firebase Auth" in data["errors"]

    def test_cleanup_user_firestore_only(self, client, mock_db, fake_auth):
        """Cover lines 783-788 - delete from Firestore successfully"""
        # Mock Firestore user exists
        mock_doc = Mock()
        mock_doc.exists = True
        mock_user_ref = Mock()
        mock_user_ref.get.return_value = mock_doc
        mock_coll = Mock()
        mock_coll.document.return_value = mock_user_ref
        mock_db.collection.return_value = mock_coll

        # Mock Firebase Auth user doesn't exist
        fake_auth.delete_user.side_effect = UserNotFoundError("Not found")

        response = client.delete("/api/admin/cleanup/user123?confirm=true")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["firestore_deleted"] is True
        assert data["firebase_auth_deleted"] is False
        assert "User not found in Firebase Auth" in data["errors"]
        mock_user_ref.delete.assert_called_once()

    def test_cleanup_firestore_error(self, client, mock_db, fake_auth):
        """Cover lines 790-791 - Firestore deletion fails"""
        # Mock Firestore deletion error
        mock_user_ref = Mock()
        mock_user_ref.get.side_effect = Exception("Firestore error")
        mock_coll = Mock()
        mock_coll.document.return_value = mock_user_ref
        mock_db.collection.return_value = mock_coll

        # Mock Firebase Auth succeeds
        fake_auth.delete_user.return_value = None

        response = client.delete("/api/admin/cleanup/user123?confirm=true")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["firebase_auth_deleted"] is True
        assert "Firestore deletion failed" in data["errors"][0]

    def test_cleanup_firebase_auth_only(self, client, mock_db, fake_auth):
        """Cover lines 794-796 - delete from Firebase Auth successfully"""
        # Mock Firestore user doesn't exist
        mock_doc = Mock()
        mock_doc.exists = False
        mock_user_ref = Mock()
        mock_user_ref.get.return_value = mock_doc
        mock_coll = Mock()
        mock_coll.document.return_value = mock_user_ref
        mock_db.collection.return_value = mock_coll

        # Mock Firebase Auth user exists
        fake_auth.delete_user.return_value = None

        response = client.delete("/api/admin/cleanup/user123?confirm=true")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["firestore_deleted"] is False
        assert data["firebase_auth_deleted"] is True
        assert data["status"] == "✅ Cleanup completed"

    def test_cleanup_firebase_auth_error(self, client, mock_db, fake_auth):
        """Cover lines 799-800 - Firebase Auth deletion fails"""
        # Mock Firestore succeeds
        mock_doc = Mock()
        mock_doc.exists = True
        mock_user_ref = Mock()
        mock_user_ref.get.return_value = mock_doc
        mock_coll = Mock()
        mock_coll.document.return_value = mock_user_ref
        mock_db.collection.return_value = mock_coll

        # Mock Firebase Auth deletion error
        fake_auth.delete_user.side_effect = Exception("Auth error")

        response = client.delete("/api/admin/cleanup/user123?confirm=true")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["firestore_deleted"] is True
        assert "Firebase Auth deletion failed" in data["errors"][0]

    def test_cleanup_both_successful(self, client, mock_db, fake_auth):
        """Cover lines 802-804 - cleanup both successfully"""
        # Mock Firestore user exists
        mock_doc = Mock()
        mock_doc.exists = True
        mock_user_ref = Mock()
        mock_user_ref.get.return_value = mock_doc
        mock_coll = Mock()
        mock_coll.document.return_value = mock_user_ref
        mock_db.collection.return_value = mock_coll

        # Mock Firebase Auth user exists
        fake_auth.delete_user.return_value = None

        response = client.delete("/api/admin/cleanup/user123?confirm=true")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["firestore_deleted"] is True
        assert data["firebase_auth_deleted"] is True
        assert data["status"] == "✅ Cleanup completed"
        assert len(data["errors"]) == 0

    # ==================== SYNC ENDPOINT TESTS ====================

    def test_sync_firestore_only_missing_password(self, client, mock_db, fake_auth):
        """Cover lines 826-847 - sync user in Firestore only, missing password"""
        # Mock user in Firestore only
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"email": "user@test.com", "name": "User"}
        mock_user_ref = Mock()
        mock_user_ref.get.return_value = mock_doc
        mock_coll = Mock()
        mock_coll.document.return_value = mock_user_ref
        mock_db.collection.return_value = mock_coll

        # Mock Firebase Auth user doesn't exist
        fake_auth.get_user.side_effect = UserNotFoundError("Not found")

        response = client.post("/api/admin/sync/user123", json={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Password required" in data["error"]
        assert "user_data" in data

    def test_sync_firestore_only_with_password(self, client, mock_db, fake_auth):
        """Cover lines 848-868 - sync user in Firestore only, create Firebase Auth user"""
        # Mock user in Firestore only
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"email": "user@test.com", "name": "User"}
        mock_user_ref = Mock()
        mock_user_ref.get.return_value = mock_doc
        mock_user_ref.update.return_value = None
        mock_coll = Mock()
        mock_coll.document.return_value = mock_user_ref
        mock_db.collection.return_value = mock_coll

        # Mock Firebase Auth user doesn't exist initially
        mock_firebase_user = Mock()
        mock_firebase_user.uid = "user123"
        
        def get_user_side_effect(uid):
            raise UserNotFoundError("Not found")
        
        fake_auth.get_user.side_effect = get_user_side_effect
        fake_auth.create_user.return_value = mock_firebase_user

        response = client.post("/api/admin/sync/user123", json={"password": "Password123!"})
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "✅ Synced"
        assert "Created Firebase Auth user" in data["message"]
        fake_auth.create_user.assert_called_once()
        mock_user_ref.update.assert_called_once()

    def test_sync_firestore_only_create_error(self, client, mock_db, fake_auth):
        """Cover lines 869-871 - Firebase Auth creation fails"""
        # Mock user in Firestore only
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"email": "user@test.com", "name": "User"}
        mock_user_ref = Mock()
        mock_user_ref.get.return_value = mock_doc
        mock_coll = Mock()
        mock_coll.document.return_value = mock_user_ref
        mock_db.collection.return_value = mock_coll

        # Mock Firebase Auth user doesn't exist
        fake_auth.get_user.side_effect = UserNotFoundError("Not found")
        fake_auth.create_user.side_effect = Exception("Creation failed")

        response = client.post("/api/admin/sync/user123", json={"password": "Password123!"})
        
        assert response.status_code == 500
        data = response.get_json()
        assert "Failed to create Firebase Auth user" in data["error"]

    def test_sync_firebase_auth_only(self, client, mock_db, fake_auth):
        """Cover lines 873-897 - sync user in Firebase Auth only, create Firestore doc"""
        # Mock user not in Firestore
        mock_doc = Mock()
        mock_doc.exists = False
        mock_user_ref = Mock()
        mock_user_ref.get.return_value = mock_doc
        mock_user_ref.set.return_value = None
        mock_coll = Mock()
        mock_coll.document.return_value = mock_user_ref
        mock_db.collection.return_value = mock_coll

        # Mock user in Firebase Auth
        mock_firebase_user = Mock()
        mock_firebase_user.uid = "user123"
        mock_firebase_user.email = "user@test.com"
        mock_firebase_user.display_name = "User"
        
        # Return user on both calls
        fake_auth.get_user.return_value = mock_firebase_user

        response = client.post("/api/admin/sync/user123", json={})
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "✅ Synced"
        assert "Created Firestore document" in data["message"]
        assert "user_data" in data
        mock_user_ref.set.assert_called_once()

    def test_sync_already_synced(self, client, mock_db, fake_auth):
        """Cover lines 899-904 - user already synced in both"""
        # Mock user in Firestore
        mock_doc = Mock()
        mock_doc.exists = True
        mock_user_ref = Mock()
        mock_user_ref.get.return_value = mock_doc
        mock_coll = Mock()
        mock_coll.document.return_value = mock_user_ref
        mock_db.collection.return_value = mock_coll

        # Mock user in Firebase Auth
        mock_firebase_user = Mock()
        mock_firebase_user.uid = "user123"
        fake_auth.get_user.return_value = mock_firebase_user

        response = client.post("/api/admin/sync/user123", json={})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "✅ Already synced"

    def test_sync_not_found_anywhere(self, client, mock_db, fake_auth):
        """Cover lines 906-911 - user doesn't exist anywhere"""
        # Mock user not in Firestore
        mock_doc = Mock()
        mock_doc.exists = False
        mock_user_ref = Mock()
        mock_user_ref.get.return_value = mock_doc
        mock_coll = Mock()
        mock_coll.document.return_value = mock_user_ref
        mock_db.collection.return_value = mock_coll

        # Mock user not in Firebase Auth
        fake_auth.get_user.side_effect = UserNotFoundError("Not found")

        response = client.post("/api/admin/sync/user123", json={})
        
        assert response.status_code == 404
        data = response.get_json()
        assert data["status"] == "❌ Not found"

    def test_get_recommendation_helper_synced(self):
        """Cover lines 917-918 - recommendation for synced users"""
        from backend.api.admin import _get_recommendation
        rec = _get_recommendation(True, True)
        assert "properly synced" in rec

    def test_get_recommendation_helper_firestore_only(self):
        """Cover lines 919-920 - recommendation for Firestore only"""
        from backend.api.admin import _get_recommendation
        rec = _get_recommendation(True, False)
        assert "Orphaned Firestore document" in rec

    def test_get_recommendation_helper_auth_only(self):
        """Cover line 921 - recommendation for Auth only"""
        from backend.api.admin import _get_recommendation
        rec = _get_recommendation(False, True)
        assert "Orphaned Firebase Auth user" in rec

    def test_get_recommendation_helper_not_exists(self):
        """Cover line 922 - recommendation for non-existent user"""
        from backend.api.admin import _get_recommendation
        rec = _get_recommendation(False, False)
        assert "doesn't exist" in rec
