"""Additional tests to reach 100% coverage for backend/api/admin.py"""

import pytest
from unittest.mock import Mock, patch
from conftest import UserNotFoundError


@pytest.fixture
def fake_auth():
    """Mock Firebase Auth."""
    with patch('backend.api.admin.auth') as mock_auth:
        mock_auth.UserNotFoundError = UserNotFoundError
        
        # Add EmailAlreadyExistsError
        class EmailAlreadyExistsError(Exception):
            pass
        mock_auth.EmailAlreadyExistsError = EmailAlreadyExistsError
        
        yield mock_auth


class TestAdminComplete100:
    """Tests for remaining uncovered lines to reach 100%"""

    # ==================== STATISTICS ENDPOINT ====================

    def test_statistics_with_counts(self, client, mock_db):
        """Cover lines 136, 141, 144-147 - statistics endpoint with actual counts"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        # Mock collections with items
        mock_user1 = Mock()
        mock_user2 = Mock()
        mock_task1 = Mock()
        mock_project1 = Mock()
        mock_membership1 = Mock()

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock()
                mock_coll.document = Mock(side_effect=document_side_effect)
                mock_coll.stream.return_value = [mock_user1, mock_user2]
            elif name == "tasks":
                mock_coll.stream.return_value = [mock_task1]
            elif name == "projects":
                mock_coll.stream.return_value = [mock_project1]
            elif name == "memberships":
                mock_coll.stream.return_value = [mock_membership1]
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)

        response = client.get("/api/admin/statistics?admin_id=admin123")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["system_statistics"]["users"] == 2
        assert data["system_statistics"]["tasks"] == 1
        assert data["system_statistics"]["projects"] == 1
        assert data["system_statistics"]["project_memberships"] == 1

    # ==================== ADD STAFF - EDGE CASES ====================

    def test_add_staff_email_already_exists(self, client, mock_db, fake_auth):
        """Cover line 278 - email already exists error"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock()
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)
        fake_auth.create_user.side_effect = fake_auth.EmailAlreadyExistsError("Email exists")

        response = client.post("/api/admin/staff?admin_id=admin123", json={
            "email": "existing@test.com",
            "password": "Password123!",
            "name": "Existing User"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Email already exists" in data["error"]

    def test_add_staff_generic_error(self, client, mock_db, fake_auth):
        """Cover line 280 - generic error during staff creation"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock()
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)
        fake_auth.create_user.side_effect = Exception("Database error")

        response = client.post("/api/admin/staff?admin_id=admin123", json={
            "email": "staff@test.com",
            "password": "Password123!",
            "name": "Staff User"
        })
        
        assert response.status_code == 500
        data = response.get_json()
        assert "Failed to add staff" in data["error"]

    # ==================== ADD MANAGER - EDGE CASES ====================

    def test_add_manager_missing_name(self, client, mock_db):
        """Cover line 303 - missing name field"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock()
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)

        response = client.post("/api/admin/managers?admin_id=admin123", json={
            "email": "manager@test.com",
            "password": "Password123!"
            # missing name
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "required" in data["error"].lower()

    def test_add_manager_email_already_exists(self, client, mock_db, fake_auth):
        """Cover line 350 - email already exists for manager"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock()
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)
        fake_auth.create_user.side_effect = fake_auth.EmailAlreadyExistsError("Email exists")

        response = client.post("/api/admin/managers?admin_id=admin123", json={
            "email": "existing@test.com",
            "password": "Password123!",
            "name": "Existing Manager",
            "manager_type": "manager"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Email already exists" in data["error"]

    def test_add_manager_generic_error(self, client, mock_db, fake_auth):
        """Cover line 352 - generic error during manager creation"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock()
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)
        fake_auth.create_user.side_effect = Exception("Firestore error")

        response = client.post("/api/admin/managers?admin_id=admin123", json={
            "email": "manager@test.com",
            "password": "Password123!",
            "name": "Manager User",
            "manager_type": "manager"
        })
        
        assert response.status_code == 500
        data = response.get_json()
        assert "Failed to add manager" in data["error"]

    # ==================== REMOVE STAFF - EDGE CASES ====================

    def test_remove_staff_user_not_found(self, client, mock_db):
        """Cover lines 367, 372 - staff user not found"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_target = Mock()
        mock_target.exists = False

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

        response = client.delete("/api/admin/staff/nonexistent?admin_id=admin123")
        
        assert response.status_code == 404
        data = response.get_json()
        assert "User not found" in data["error"]

    def test_remove_staff_not_staff_role(self, client, mock_db):
        """Cover lines 398-399 - trying to remove non-staff user"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"name": "Manager", "role": "manager"}

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

        response = client.delete("/api/admin/staff/user456?admin_id=admin123")
        
        assert response.status_code == 400
        data = response.get_json()
        assert "for removing staff only" in data["error"] or "not a staff member" in data["error"]

    # ==================== REMOVE MANAGER - EDGE CASES ====================

    def test_remove_manager_not_manager_role(self, client, mock_db):
        """Cover lines 418-419 - trying to remove non-manager user"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"name": "Staff", "role": "staff"}

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

        response = client.delete("/api/admin/managers/user456?admin_id=admin123")
        
        assert response.status_code == 400
        data = response.get_json()
        assert "for removing managers only" in data["error"] or "not a manager" in data["error"]

    def test_remove_manager_user_not_found(self, client, mock_db):
        """Cover lines 441, 446 - manager user not found"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_target = Mock()
        mock_target.exists = False

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

        response = client.delete("/api/admin/managers/nonexistent?admin_id=admin123")
        
        assert response.status_code == 404
        data = response.get_json()
        assert "User not found" in data["error"]

    # ==================== CHANGE ROLE - EDGE CASES ====================

    def test_change_role_user_not_found(self, client, mock_db):
        """Cover lines 473-474 - user not found for role change"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_target = Mock()
        mock_target.exists = False

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

        response = client.put("/api/admin/users/nonexistent/role?admin_id=admin123", json={
            "role": "manager"
        })
        
        assert response.status_code == 404
        data = response.get_json()
        assert "User not found" in data["error"]

    def test_change_role_cannot_change_own_role(self, client, mock_db):
        """Cover lines 516, 521 - cannot change own admin role"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    return Mock(get=Mock(return_value=mock_admin))
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)

        response = client.put("/api/admin/users/admin123/role?admin_id=admin123", json={
            "role": "staff"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Cannot change your own" in data["error"]

    # ==================== CHANGE STATUS - EDGE CASES ====================

    def test_change_status_user_not_found(self, client, mock_db):
        """Cover lines 543-544 - user not found for status change"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_target = Mock()
        mock_target.exists = False

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

        response = client.put("/api/admin/users/nonexistent/status?admin_id=admin123", json={
            "is_active": False
        })
        
        assert response.status_code == 404
        data = response.get_json()
        assert "User not found" in data["error"]

    def test_change_status_cannot_deactivate_own_admin(self, client, mock_db):
        """Cover lines 569, 574 - cannot deactivate own admin account"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin", "is_active": True}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    return Mock(get=Mock(return_value=mock_admin))
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)

        response = client.put("/api/admin/users/admin123/status?admin_id=admin123", json={
            "is_active": False
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Cannot deactivate your own" in data["error"]

    def test_change_status_activate_user(self, client, mock_db, fake_auth):
        """Cover lines 591, 603-604 - activate user"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"name": "User", "role": "staff", "is_active": False, "firebase_uid": "user456"}

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
            "is_active": True
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert "activated" in data["message"].lower()
        assert data["is_active"] is True

    # ==================== TASKS/PROJECTS FILTERS ====================

    def test_get_tasks_no_admin_id(self, client):
        """Cover lines 625, 630 - no admin_id in tasks endpoint"""
        response = client.get("/api/admin/tasks")
        
        assert response.status_code == 401
        data = response.get_json()
        assert "admin_id required" in data["error"]

    def test_get_projects_no_admin_id(self, client):
        """Cover lines 664, 669 - no admin_id in projects endpoint"""
        response = client.get("/api/admin/projects")
        
        assert response.status_code == 401
        data = response.get_json()
        assert "admin_id required" in data["error"]

    # ==================== CLEANUP ====================

    def test_cleanup_with_confirm_false_string(self, client):
        """Cover line 737-740 - cleanup with confirm=False (string)"""
        response = client.delete("/api/admin/cleanup/user123?confirm=False")
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Confirmation required" in data["error"]

    def test_cleanup_no_confirm_param(self, client):
        """Cover line 737-740 - cleanup without any confirm param"""
        response = client.delete("/api/admin/cleanup/user123")
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Confirmation required" in data["error"]
        assert "warning" in data
