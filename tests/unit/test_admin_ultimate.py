"""Ultimate coverage tests - targeting the last remaining lines"""

import pytest
from unittest.mock import Mock, patch
from conftest import UserNotFoundError


@pytest.fixture
def fake_auth():
    """Mock Firebase Auth."""
    with patch('backend.api.admin.auth') as mock_auth:
        mock_auth.UserNotFoundError = UserNotFoundError
        
        class EmailAlreadyExistsError(Exception):
            pass
        mock_auth.EmailAlreadyExistsError = EmailAlreadyExistsError
        
        yield mock_auth


class TestAdminUltimateCoverage:
    """Tests targeting the last 34 missing lines"""

    # ==================== LINE 26 - Non-admin role ====================
    
    def test_verify_admin_non_admin_user(self, client, mock_db):
        """Cover line 26 - user with non-admin role trying to access admin endpoint"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "manager", "name": "Manager User"}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    return Mock(get=Mock(return_value=mock_user))
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)

        response = client.get("/api/admin/dashboard?admin_id=manager123")
        assert response.status_code == 403

    # ==================== LINES 71-74 - Dashboard role breakdown ====================
    
    def test_dashboard_role_in_breakdown(self, client, mock_db):
        """Cover lines 71-74 - role exists in role_breakdown dict"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin", "name": "Admin", "email": "admin@test.com"}

        # Create multiple users with same role to test increment
        mock_user1 = Mock()
        mock_user1.id = "user1"
        mock_user1.to_dict.return_value = {"name": "Staff1", "role": "staff", "is_active": True}

        mock_user2 = Mock()
        mock_user2.id = "user2"
        mock_user2.to_dict.return_value = {"name": "Staff2", "role": "staff", "is_active": True}

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
                mock_coll.stream.return_value = []
            elif name == "projects":
                mock_coll.stream.return_value = []
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)

        response = client.get("/api/admin/dashboard?admin_id=admin123")
        assert response.status_code == 200

    # ==================== LINE 136 - Statistics calculations ====================
    
    def test_statistics_zero_division_handling(self, client, mock_db):
        """Cover line 136 - statistics with zero users/projects"""
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
                mock_coll.stream.return_value = []
            else:
                mock_coll.stream.return_value = []
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)

        response = client.get("/api/admin/statistics?admin_id=admin123")
        assert response.status_code == 200

    # ==================== LINES 177, 182 - User filtering ====================
    
    def test_users_role_filter_not_matching(self, client, mock_db):
        """Cover line 177 - role filter doesn't match (continue statement)"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_user1 = Mock()
        mock_user1.id = "user1"
        mock_user1.to_dict.return_value = {"name": "Staff", "role": "staff"}

        mock_user2 = Mock()
        mock_user2.id = "user2"
        mock_user2.to_dict.return_value = {"name": "Manager", "role": "manager"}

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

        # Request only managers, staff should be filtered out (line 177)
        response = client.get("/api/admin/users?admin_id=admin123&role=manager")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1

    def test_users_status_filter_active_not_matching(self, client, mock_db):
        """Cover line 182 - active status filter, user is inactive (continue)"""
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

        # Request only active users, inactive should be filtered out (line 182)
        response = client.get("/api/admin/users?admin_id=admin123&status=active")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["users"][0]["name"] == "Active"

    # ==================== LINES 232, 237 - Add staff validation ====================
    
    def test_add_staff_all_fields_empty(self, client, mock_db):
        """Cover lines 232, 237 - all required fields missing"""
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

        response = client.post("/api/admin/staff?admin_id=admin123", json={})
        assert response.status_code == 400

    # ==================== LINES 298, 303 - Add manager validation ====================
    
    def test_add_manager_all_fields_empty(self, client, mock_db):
        """Cover lines 298, 303 - all required fields missing for manager"""
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

        response = client.post("/api/admin/managers?admin_id=admin123", json={})
        assert response.status_code == 400

    # ==================== LINES 367, 372, 398-399 - Remove staff validation ====================
    
    def test_remove_staff_user_does_not_exist(self, client, mock_db):
        """Cover lines 367, 372 - staff user doesn't exist"""
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

    def test_remove_staff_wrong_role(self, client, mock_db):
        """Cover lines 398-399 - trying to remove non-staff via staff endpoint"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"name": "Director", "role": "director"}

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

    # ==================== LINES 418-419, 441, 446 - Remove manager validation ====================
    
    def test_remove_manager_wrong_role(self, client, mock_db):
        """Cover lines 418-419 - trying to remove non-manager via manager endpoint"""
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

    def test_remove_manager_does_not_exist(self, client, mock_db):
        """Cover lines 441, 446 - manager user doesn't exist"""
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

    # ==================== LINES 473-474, 493-494, 516, 521 - Change role validation ====================
    
    def test_change_role_user_not_found(self, client, mock_db):
        """Cover lines 473-474 - user doesn't exist for role change"""
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

        response = client.put("/api/admin/users/nonexistent/role?admin_id=admin123", json={"role": "manager"})
        assert response.status_code == 404

    def test_change_role_invalid_role_value(self, client, mock_db):
        """Cover lines 493-494 - invalid role specified"""
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

        response = client.put("/api/admin/users/user456/role?admin_id=admin123", json={"role": "superuser"})
        assert response.status_code == 400

    def test_change_own_admin_role(self, client, mock_db):
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

        response = client.put("/api/admin/users/admin123/role?admin_id=admin123", json={"role": "staff"})
        assert response.status_code == 400

    # ==================== LINES 543-549, 569, 574 - Change status validation ====================
    
    def test_change_status_user_not_found(self, client, mock_db):
        """Cover lines 543-549 - user doesn't exist for status change"""
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

        response = client.put("/api/admin/users/nonexistent/status?admin_id=admin123", json={"is_active": False})
        assert response.status_code == 404

    def test_change_status_deactivate_own_admin(self, client, mock_db):
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

        response = client.put("/api/admin/users/admin123/status?admin_id=admin123", json={"is_active": False})
        assert response.status_code == 400

    # ==================== LINES 603-604 - Update Firebase Auth ====================
    
    def test_change_status_with_firebase_update_success(self, client, mock_db, fake_auth):
        """Cover lines 603-604 - Firebase Auth update succeeds"""
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

        response = client.put("/api/admin/users/user456/status?admin_id=admin123", json={"is_active": True})
        assert response.status_code == 200
        fake_auth.update_user.assert_called_once()

    # ==================== LINES 630, 669 - No admin_id ====================
    
    def test_tasks_endpoint_no_admin_id(self, client):
        """Cover line 630 - tasks endpoint without admin_id"""
        response = client.get("/api/admin/tasks")
        assert response.status_code == 401

    def test_projects_endpoint_no_admin_id(self, client):
        """Cover line 669 - projects endpoint without admin_id"""
        response = client.get("/api/admin/projects")
        assert response.status_code == 401

    # ==================== LINES 737-740 - Cleanup confirmation ====================
    
    def test_cleanup_no_confirm(self, client):
        """Cover lines 737-740 - cleanup without confirm parameter"""
        response = client.delete("/api/admin/cleanup/user123")
        assert response.status_code == 400

    def test_cleanup_confirm_false(self, client):
        """Cover lines 737-740 - cleanup with confirm=false"""
        response = client.delete("/api/admin/cleanup/user123?confirm=false")
        assert response.status_code == 400

    def test_cleanup_confirm_empty(self, client):
        """Cover lines 737-740 - cleanup with empty confirm"""
        response = client.delete("/api/admin/cleanup/user123?confirm=")
        assert response.status_code == 400
