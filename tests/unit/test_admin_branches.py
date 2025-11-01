"""Branch-specific tests to reach 100% branch coverage"""

import pytest
from unittest.mock import Mock, patch
from conftest import UserNotFoundError


@pytest.fixture
def fake_auth():
    """Mock Firebase Auth."""
    with patch('backend.api.admin.auth') as mock_auth:
        mock_auth.UserNotFoundError = UserNotFoundError
        yield mock_auth


class TestAdminBranchSpecific:
    """Tests targeting specific branch conditions for 100% coverage"""

    # ==================== BRANCH 71->74 (role NOT in breakdown) ====================
    
    def test_dashboard_role_not_in_breakdown(self, client, mock_db):
        """Cover branch 71->74 - role NOT already in role_breakdown dict"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin", "name": "Admin", "email": "admin@test.com"}

        # Create user with unique role that won't be in breakdown yet
        mock_user1 = Mock()
        mock_user1.id = "user1"
        mock_user1.to_dict.return_value = {"name": "HR1", "role": "hr", "is_active": True, "created_at": "2024-01-01"}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock()
                mock_coll.document = Mock(side_effect=document_side_effect)
                mock_coll.stream.return_value = [mock_user1]
            elif name == "tasks":
                mock_coll.stream.return_value = []
            elif name == "projects":
                mock_coll.stream.return_value = []
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)

        response = client.get("/api/admin/dashboard?admin_id=admin123")
        assert response.status_code == 200
        data = response.get_json()
        # HR role should be added to breakdown
        assert data["statistics"]["total_users"] == 1

    def test_dashboard_role_already_in_breakdown(self, client, mock_db):
        """Cover branch 71->72 - role IS already in role_breakdown dict (increment)"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin", "name": "Admin", "email": "admin@test.com"}

        # Two users with same role - first adds to dict, second increments
        mock_user1 = Mock()
        mock_user1.id = "user1"
        mock_user1.to_dict.return_value = {"name": "Manager1", "role": "manager", "is_active": True, "created_at": "2024-01-01"}

        mock_user2 = Mock()
        mock_user2.id = "user2"
        mock_user2.to_dict.return_value = {"name": "Manager2", "role": "manager", "is_active": False, "created_at": "2024-01-02"}

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

    def test_dashboard_inactive_user(self, client, mock_db):
        """Cover branch 74->65 - user is_active is False"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin", "name": "Admin", "email": "admin@test.com"}

        mock_user1 = Mock()
        mock_user1.id = "user1"
        mock_user1.to_dict.return_value = {"name": "Inactive", "role": "staff", "is_active": False, "created_at": "2024-01-01"}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock()
                mock_coll.document = Mock(side_effect=document_side_effect)
                mock_coll.stream.return_value = [mock_user1]
            elif name == "tasks":
                mock_coll.stream.return_value = []
            elif name == "projects":
                mock_coll.stream.return_value = []
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)

        response = client.get("/api/admin/dashboard?admin_id=admin123")
        assert response.status_code == 200
        data = response.get_json()
        assert data["statistics"]["active_users"] == 0
        assert data["statistics"]["inactive_users"] == 1

    # ==================== LINES 136, 141 - Statistics with data ====================
    
    def test_statistics_with_actual_data(self, client, mock_db):
        """Cover lines 136, 141 - statistics calculations with real data"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

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

    # ==================== COMPREHENSIVE FILTER TESTS ====================
    
    def test_users_with_role_and_status_filters_combined(self, client, mock_db):
        """Cover lines 177, 182, 232, 237 - both filters applied"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_user1 = Mock()
        mock_user1.id = "user1"
        mock_user1.to_dict.return_value = {"name": "Active Staff", "role": "staff", "is_active": True}

        mock_user2 = Mock()
        mock_user2.id = "user2"
        mock_user2.to_dict.return_value = {"name": "Inactive Staff", "role": "staff", "is_active": False}

        mock_user3 = Mock()
        mock_user3.id = "user3"
        mock_user3.to_dict.return_value = {"name": "Active Manager", "role": "manager", "is_active": True}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock()
                mock_coll.document = Mock(side_effect=document_side_effect)
                mock_coll.stream.return_value = [mock_user1, mock_user2, mock_user3]
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)

        # Get only active staff (filters both role and status)
        response = client.get("/api/admin/users?admin_id=admin123&role=staff&status=active")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["users"][0]["name"] == "Active Staff"

    def test_users_status_inactive_filter(self, client, mock_db):
        """Cover line 237 - status filter for inactive (line 204 continue)"""
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

    # ==================== VALIDATION TESTS - MISSING FIELDS ====================
    
    def test_add_staff_missing_only_email(self, client, mock_db):
        """Cover line 298 - specifically missing email"""
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

        response = client.post("/api/admin/staff?admin_id=admin123", json={
            "password": "Pass123!",
            "name": "Test User"
        })
        assert response.status_code == 400

    def test_add_manager_missing_only_email(self, client, mock_db):
        """Cover line 303 - specifically missing email for manager"""
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
            "password": "Pass123!",
            "name": "Test Manager",
            "manager_type": "manager"
        })
        assert response.status_code == 400

    # ==================== UPDATE FIREBASE AUTH SUCCESS ====================
    
    def test_change_status_firebase_auth_exception_caught(self, client, mock_db, fake_auth):
        """Cover line 603-604 - Firebase auth update exception is caught"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {
            "name": "User",
            "role": "staff",
            "is_active": True,
            "firebase_uid": "user456"
        }

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
        
        # Make Firebase update raise exception (should be caught)
        fake_auth.update_user.side_effect = Exception("Firebase error")

        response = client.put("/api/admin/users/user456/status?admin_id=admin123", json={
            "is_active": False
        })
        
        # Should still return 200 even if Firebase update fails
        assert response.status_code == 200

    # ==================== COMPREHENSIVE COVERAGE FOR ALL BRANCHES ====================
    
    def test_remove_staff_is_staff_hard_delete(self, client, mock_db, fake_auth):
        """Ensure staff removal with hard delete covers all paths"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"name": "Staff", "role": "staff", "firebase_uid": "staff123"}

        mock_user_ref = Mock()
        mock_user_ref.get.return_value = mock_target
        mock_user_ref.delete.return_value = None

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
        fake_auth.delete_user.return_value = None

        response = client.delete("/api/admin/staff/staff123?admin_id=admin123&hard_delete=true")
        assert response.status_code == 200
        data = response.get_json()
        assert "permanently deleted" in data["message"].lower()
