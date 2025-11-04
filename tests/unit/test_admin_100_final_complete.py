"""
Targeted tests to achieve 100% coverage for admin.py
Focuses on remaining uncovered lines (sync utilities, edge cases)
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from firebase_admin import auth


class TestAdminSyncUtilities:
    """Tests for sync and cleanup utilities in admin.py"""
    
    def test_check_user_sync_both_exist(self, client, mock_db):
        """Test check endpoint when user exists in both systems"""
        # Mock Firestore
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "name": "Test User",
            "email": "test@example.com",
            "role": "staff"
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Mock Firebase Auth
        mock_firebase_user = Mock()
        mock_firebase_user.uid = "user123"
        mock_firebase_user.email = "test@example.com"
        mock_firebase_user.display_name = "Test User"
        mock_firebase_user.disabled = False
        mock_firebase_user.email_verified = True
        
        with patch('firebase_admin.auth.get_user', return_value=mock_firebase_user):
            response = client.get("/api/admin/check/user123")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["synced"] is True
        assert data["in_firestore"] is True
        assert data["in_firebase_auth"] is True
        assert "✅ Synced" in data["status"]
    
    def test_check_user_sync_firestore_only(self, client, mock_db):
        """Test check endpoint when user exists only in Firestore"""
        # Mock Firestore
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"name": "Test", "email": "test@example.com"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Mock Firebase Auth - user not found
        with patch('firebase_admin.auth.get_user', side_effect=auth.UserNotFoundError("Not found")):
            response = client.get("/api/admin/check/user123")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["synced"] is False
        assert data["in_firestore"] is True
        assert data["in_firebase_auth"] is False
        assert "⚠️" in data["status"]
    
    def test_check_user_sync_firebase_only(self, client, mock_db):
        """Test check endpoint when user exists only in Firebase Auth"""
        # Mock Firestore - not found
        mock_doc = Mock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Mock Firebase Auth
        mock_firebase_user = Mock()
        mock_firebase_user.uid = "user123"
        mock_firebase_user.email = "test@example.com"
        mock_firebase_user.display_name = "Test User"
        mock_firebase_user.disabled = False
        mock_firebase_user.email_verified = True
        
        with patch('firebase_admin.auth.get_user', return_value=mock_firebase_user):
            response = client.get("/api/admin/check/user123")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["synced"] is False
        assert data["in_firestore"] is False
        assert data["in_firebase_auth"] is True
    
    def test_check_user_sync_neither_exist(self, client, mock_db):
        """Test check endpoint when user doesn't exist anywhere"""
        # Mock Firestore - not found
        mock_doc = Mock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Mock Firebase Auth - not found
        with patch('firebase_admin.auth.get_user', side_effect=auth.UserNotFoundError("Not found")):
            response = client.get("/api/admin/check/user123")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["synced"] is True  # Both don't exist, so they're "synced"
        assert data["in_firestore"] is False
        assert data["in_firebase_auth"] is False
    
    def test_check_user_firebase_error(self, client, mock_db):
        """Test check endpoint when Firebase Auth throws an error"""
        # Mock Firestore
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"name": "Test"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Mock Firebase Auth - generic error
        with patch('firebase_admin.auth.get_user', side_effect=Exception("Firebase error")):
            response = client.get("/api/admin/check/user123")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "error" in data["firebase_data"]
    
    def test_cleanup_user_without_confirmation(self, client):
        """Test cleanup endpoint without confirmation parameter"""
        response = client.delete("/api/admin/cleanup/user123")
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Confirmation required" in data["error"]
        assert "confirm=true" in data["message"]
    
    def test_cleanup_user_with_confirmation_both_exist(self, client, mock_db):
        """Test cleanup endpoint with confirmation - removes from both systems"""
        # Mock Firestore
        mock_doc = Mock()
        mock_doc.exists = True
        mock_ref = Mock()
        mock_ref.get.return_value = mock_doc
        mock_ref.delete = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        
        # Mock Firebase Auth deletion
        with patch('firebase_admin.auth.delete_user') as mock_delete:
            response = client.delete("/api/admin/cleanup/user123?confirm=true")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["firestore_deleted"] is True
        assert data["firebase_auth_deleted"] is True
        assert "✅ Cleanup completed" in data["status"]
        mock_ref.delete.assert_called_once()
        mock_delete.assert_called_once_with("user123")
    
    def test_cleanup_user_firestore_not_found(self, client, mock_db):
        """Test cleanup when user not in Firestore"""
        # Mock Firestore - not found
        mock_doc = Mock()
        mock_doc.exists = False
        mock_ref = Mock()
        mock_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_ref
        
        # Mock Firebase Auth deletion
        with patch('firebase_admin.auth.delete_user'):
            response = client.delete("/api/admin/cleanup/user123?confirm=true")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["firestore_deleted"] is False
        assert "User not found in Firestore" in data["errors"]
    
    def test_cleanup_user_firebase_not_found(self, client, mock_db):
        """Test cleanup when user not in Firebase Auth"""
        # Mock Firestore
        mock_doc = Mock()
        mock_doc.exists = True
        mock_ref = Mock()
        mock_ref.get.return_value = mock_doc
        mock_ref.delete = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        
        # Mock Firebase Auth - not found
        with patch('firebase_admin.auth.delete_user', side_effect=auth.UserNotFoundError("Not found")):
            response = client.delete("/api/admin/cleanup/user123?confirm=true")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["firestore_deleted"] is True
        assert "User not found in Firebase Auth" in data["errors"]
    
    def test_cleanup_user_nothing_to_cleanup(self, client, mock_db):
        """Test cleanup when user doesn't exist anywhere"""
        # Mock Firestore - not found
        mock_doc = Mock()
        mock_doc.exists = False
        mock_ref = Mock()
        mock_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_ref
        
        # Mock Firebase Auth - not found
        with patch('firebase_admin.auth.delete_user', side_effect=auth.UserNotFoundError("Not found")):
            response = client.delete("/api/admin/cleanup/user123?confirm=true")
        
        assert response.status_code == 404
        data = response.get_json()
        assert data["firestore_deleted"] is False
        assert data["firebase_auth_deleted"] is False
        assert "❌ Nothing to clean up" in data["status"]
    
    def test_sync_user_firestore_only_no_password(self, client, mock_db):
        """Test sync when user in Firestore only but no password provided"""
        # Mock Firestore
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "email": "test@example.com",
            "name": "Test User"
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Mock Firebase Auth - not found
        with patch('firebase_admin.auth.get_user', side_effect=auth.UserNotFoundError("Not found")):
            response = client.post("/api/admin/sync/user123", json={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Password required" in data["error"]
    
    def test_sync_user_firestore_only_with_password(self, client, mock_db):
        """Test sync when user in Firestore only with password provided"""
        # Mock Firestore
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "email": "test@example.com",
            "name": "Test User"
        }
        mock_ref = Mock()
        mock_ref.get.return_value = mock_doc
        mock_ref.update = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        
        # Mock Firebase Auth
        mock_firebase_user = Mock()
        mock_firebase_user.uid = "user123"
        
        with patch('firebase_admin.auth.get_user', side_effect=auth.UserNotFoundError("Not found")):
            with patch('firebase_admin.auth.create_user', return_value=mock_firebase_user):
                response = client.post("/api/admin/sync/user123", json={"password": "newpass123"})
        
        assert response.status_code == 201
        data = response.get_json()
        assert "✅ Synced" in data["status"]
        assert "Created Firebase Auth user" in data["message"]
        mock_ref.update.assert_called_once()
    
    def test_sync_user_firebase_only(self, client, mock_db):
        """Test sync when user in Firebase Auth only"""
        # Mock Firestore - not found
        mock_doc = Mock()
        mock_doc.exists = False
        mock_ref = Mock()
        mock_ref.get.return_value = mock_doc
        mock_ref.set = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        
        # Mock Firebase Auth
        mock_firebase_user = Mock()
        mock_firebase_user.uid = "user123"
        mock_firebase_user.email = "test@example.com"
        mock_firebase_user.display_name = "Test User"
        
        def get_user_side_effect(uid):
            if uid == "user123":
                return mock_firebase_user
            raise auth.UserNotFoundError("Not found")
        
        with patch('firebase_admin.auth.get_user', side_effect=get_user_side_effect):
            response = client.post("/api/admin/sync/user123", json={})
        
        assert response.status_code == 201
        data = response.get_json()
        assert "✅ Synced" in data["status"]
        assert "Created Firestore document" in data["message"]
        mock_ref.set.assert_called_once()
    
    def test_sync_user_already_synced(self, client, mock_db):
        """Test sync when user already exists in both systems"""
        # Mock Firestore
        mock_doc = Mock()
        mock_doc.exists = True
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Mock Firebase Auth
        mock_firebase_user = Mock()
        with patch('firebase_admin.auth.get_user', return_value=mock_firebase_user):
            response = client.post("/api/admin/sync/user123", json={})
        
        assert response.status_code == 200
        data = response.get_json()
        assert "Already synced" in data["status"]
    
    def test_sync_user_not_found_anywhere(self, client, mock_db):
        """Test sync when user doesn't exist anywhere"""
        # Mock Firestore - not found
        mock_doc = Mock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Mock Firebase Auth - not found
        with patch('firebase_admin.auth.get_user', side_effect=auth.UserNotFoundError("Not found")):
            response = client.post("/api/admin/sync/user123", json={})
        
        assert response.status_code == 404
        data = response.get_json()
        assert "❌ Not found" in data["status"]
    
    def test_sync_user_create_firebase_error(self, client, mock_db):
        """Test sync when Firebase Auth creation fails"""
        # Mock Firestore
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "email": "test@example.com",
            "name": "Test User"
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Mock Firebase Auth
        with patch('firebase_admin.auth.get_user', side_effect=auth.UserNotFoundError("Not found")):
            with patch('firebase_admin.auth.create_user', side_effect=Exception("Creation failed")):
                response = client.post("/api/admin/sync/user123", json={"password": "pass123"})
        
        assert response.status_code == 500
        data = response.get_json()
        assert "Failed to create Firebase Auth user" in data["error"]


class TestAdminEdgeCases:
    """Tests for edge cases in admin endpoints"""
    
    def test_get_all_tasks_with_status_filter(self, client, mock_db, monkeypatch):
        """Test getting tasks with status filter"""
        monkeypatch.setattr("backend.api.admin._get_admin_id", lambda: "admin123")
        
        # Mock admin verification
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        # Mock tasks
        task1 = Mock()
        task1.to_dict.return_value = {"status": "Completed", "priority": 1}
        task1.id = "task1"
        
        task2 = Mock()
        task2.to_dict.return_value = {"status": "In Progress", "priority": 2}
        task2.id = "task2"
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
            elif name == "tasks":
                mock_coll.stream = Mock(return_value=[task1, task2])
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/admin/tasks?status=Completed")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["filters"]["status"] == "Completed"
    
    def test_get_all_tasks_with_priority_filter(self, client, mock_db, monkeypatch):
        """Test getting tasks with priority filter"""
        monkeypatch.setattr("backend.api.admin._get_admin_id", lambda: "admin123")
        
        # Mock admin verification
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        # Mock tasks
        task1 = Mock()
        task1.to_dict.return_value = {"status": "Completed", "priority": 1}
        task1.id = "task1"
        
        task2 = Mock()
        task2.to_dict.return_value = {"status": "In Progress", "priority": 2}
        task2.id = "task2"
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
            elif name == "tasks":
                mock_coll.stream = Mock(return_value=[task1, task2])
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/admin/tasks?priority=1")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["filters"]["priority"] == "1"
    
    def test_check_user_via_users_endpoint(self, client, mock_db):
        """Test check endpoint via /api/users/admin/check route"""
        # Mock Firestore
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"name": "Test", "email": "test@example.com"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Mock Firebase Auth
        mock_firebase_user = Mock()
        mock_firebase_user.uid = "user123"
        mock_firebase_user.email = "test@example.com"
        mock_firebase_user.display_name = "Test"
        mock_firebase_user.disabled = False
        mock_firebase_user.email_verified = True
        
        with patch('firebase_admin.auth.get_user', return_value=mock_firebase_user):
            response = client.get("/api/users/admin/check/user123")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["synced"] is True
    
    def test_cleanup_user_via_users_endpoint(self, client, mock_db):
        """Test cleanup endpoint via /api/users/admin/cleanup route"""
        # Mock Firestore
        mock_doc = Mock()
        mock_doc.exists = True
        mock_ref = Mock()
        mock_ref.get.return_value = mock_doc
        mock_ref.delete = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        
        # Mock Firebase Auth
        with patch('firebase_admin.auth.delete_user'):
            response = client.delete("/api/users/admin/cleanup/user123?confirm=true")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["firestore_deleted"] is True
    
    def test_sync_user_via_users_endpoint(self, client, mock_db):
        """Test sync endpoint via /api/users/admin/sync route"""
        # Mock Firestore
        mock_doc = Mock()
        mock_doc.exists = True
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Mock Firebase Auth
        mock_firebase_user = Mock()
        with patch('firebase_admin.auth.get_user', return_value=mock_firebase_user):
            response = client.post("/api/users/admin/sync/user123", json={})
        
        assert response.status_code == 200
        data = response.get_json()
        assert "Already synced" in data["status"]
