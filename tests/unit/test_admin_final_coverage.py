"""Final tests to reach 100% coverage for backend/api/admin.py"""

import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def fake_auth():
    """Mock Firebase Auth."""
    with patch('backend.api.admin.auth') as mock_auth:
        from conftest import UserNotFoundError
        mock_auth.UserNotFoundError = UserNotFoundError
        yield mock_auth


class TestAdminFinalCoverage:
    """Tests for the remaining uncovered lines in admin.py"""

    def test_users_filter_by_role_no_match(self, client, mock_db, monkeypatch):
        """Cover line 196 - role filter excludes user"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_user1 = Mock()
        mock_user1.id = "user1"
        mock_user1.to_dict.return_value = {"name": "Manager", "role": "manager"}

        mock_user2 = Mock()
        mock_user2.id = "user2"
        mock_user2.to_dict.return_value = {"name": "Staff", "role": "staff"}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock()
                mock_coll.document = Mock(side_effect=document_side_effect)
                mock_coll.stream.return_value = [mock_user1, mock_user2]
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)

        response = client.get("/api/admin/users?admin_id=admin123&role=director")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 0  # No directors found

    def test_users_filter_by_status_inactive(self, client, mock_db, monkeypatch):
        """Cover line 203 - status filter for inactive users"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_user1 = Mock()
        mock_user1.id = "user1"
        mock_user1.to_dict.return_value = {"name": "Active", "is_active": True}

        mock_user2 = Mock()
        mock_user2.id = "user2"
        mock_user2.to_dict.return_value = {"name": "Inactive", "is_active": False}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock()
                mock_coll.document = Mock(side_effect=document_side_effect)
                mock_coll.stream.return_value = [mock_user1, mock_user2]
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)

        response = client.get("/api/admin/users?admin_id=admin123&status=inactive")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["users"][0]["name"] == "Inactive"

    def test_tasks_filter_by_status(self, client, mock_db, monkeypatch):
        """Cover lines 683-684 - tasks status filter"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_task1 = Mock()
        mock_task1.id = "task1"
        mock_task1.to_dict.return_value = {"name": "Task 1", "status": "todo", "priority": 1}

        mock_task2 = Mock()
        mock_task2.id = "task2"
        mock_task2.to_dict.return_value = {"name": "Task 2", "status": "done", "priority": 2}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock()
                mock_coll.document = Mock(side_effect=document_side_effect)
            elif name == "tasks":
                mock_coll.stream.return_value = [mock_task1, mock_task2]
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)

        response = client.get("/api/admin/tasks?admin_id=admin123&status=done")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["tasks"][0]["name"] == "Task 2"

    def test_tasks_filter_by_priority(self, client, mock_db, monkeypatch):
        """Cover lines 685-686 - tasks priority filter"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_task1 = Mock()
        mock_task1.id = "task1"
        mock_task1.to_dict.return_value = {"name": "Task 1", "status": "todo", "priority": 1}

        mock_task2 = Mock()
        mock_task2.id = "task2"
        mock_task2.to_dict.return_value = {"name": "Task 2", "status": "todo", "priority": 3}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock()
                mock_coll.document = Mock(side_effect=document_side_effect)
            elif name == "tasks":
                mock_coll.stream.return_value = [mock_task1, mock_task2]
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)

        response = client.get("/api/admin/tasks?admin_id=admin123&priority=3")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["tasks"][0]["name"] == "Task 2"

    def test_change_user_role_invalid_role(self, client, mock_db, monkeypatch):
        """Cover lines 493-494 - invalid role change"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"name": "User", "role": "staff"}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_target))
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)

        response = client.put("/api/admin/users/user456/role?admin_id=admin123", json={
            "role": "invalid_role"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Invalid role" in data["error"]

    def test_change_user_status_deactivate(self, client, mock_db, fake_auth, monkeypatch):
        """Cover lines 543-549 - deactivate user"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"name": "User", "role": "staff", "is_active": True, "firebase_uid": "user456"}

        mock_user_ref = Mock()
        mock_user_ref.get.return_value = mock_target
        mock_user_ref.update.return_value = None

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return mock_user_ref
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)
        fake_auth.update_user.return_value = None

        response = client.put("/api/admin/users/user456/status?admin_id=admin123", json={
            "is_active": False
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert "deactivated" in data["message"].lower()
        fake_auth.update_user.assert_called_once()

    def test_cleanup_missing_confirmation_param(self, client):
        """Cover lines 737-740 - cleanup without confirm param"""
        response = client.delete("/api/admin/cleanup/user123?confirm=false")
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Confirmation required" in data["error"]
