"""Final push to 100% coverage - targeting specific branch conditions"""

import pytest
from unittest.mock import Mock, patch


class TestAdminBranchCoverage:
    """Tests for specific branch conditions and edge cases"""

    def test_verify_admin_access_non_admin_role(self, client, mock_db):
        """Cover line 26 - user exists but is not admin"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "staff", "name": "Regular User"}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    return Mock(get=Mock(return_value=mock_user))
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)

        # Try to access any admin endpoint
        response = client.get("/api/admin/statistics?admin_id=staff123")
        
        assert response.status_code == 403
        data = response.get_json()
        assert "Admin access required" in data["error"]

    def test_dashboard_with_role_breakdown(self, client, mock_db):
        """Cover lines 71-74 branch conditions for role counting"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}

        # Create users with different roles
        mock_user1 = Mock()
        mock_user1.id = "user1"
        mock_user1.to_dict.return_value = {"name": "Staff1", "role": "staff", "is_active": True}

        mock_user2 = Mock()
        mock_user2.id = "user2"
        mock_user2.to_dict.return_value = {"name": "Manager1", "role": "manager", "is_active": True}

        mock_user3 = Mock()
        mock_user3.id = "user3"
        mock_user3.to_dict.return_value = {"name": "Inactive", "role": "staff", "is_active": False}

        # Create tasks with different statuses
        mock_task1 = Mock()
        mock_task1.id = "task1"
        mock_task1.to_dict.return_value = {"name": "Task1", "status": "todo", "priority": 1}

        mock_task2 = Mock()
        mock_task2.id = "task2"
        mock_task2.to_dict.return_value = {"name": "Task2", "status": "in_progress", "priority": 2}

        # Create projects
        mock_project1 = Mock()
        mock_project1.id = "proj1"
        mock_project1.to_dict.return_value = {"name": "Project1"}

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock()
                mock_coll.document = Mock(side_effect=document_side_effect)
                mock_coll.stream.return_value = [mock_user1, mock_user2, mock_user3]
            elif name == "tasks":
                mock_coll.stream.return_value = [mock_task1, mock_task2]
            elif name == "projects":
                mock_coll.stream.return_value = [mock_project1]
            return mock_coll

        mock_db.collection = Mock(side_effect=collection_side_effect)

        response = client.get("/api/admin/dashboard?admin_id=admin123")
        
        assert response.status_code == 200
        data = response.get_json()
        # Verify role breakdown was calculated
        assert data["statistics"]["total_users"] == 3
        assert data["statistics"]["active_users"] == 2
        # Dashboard should have statistics
        assert "statistics" in data

    def test_users_endpoint_role_filter_match(self, client, mock_db):
        """Cover lines 177, 182 - role filter matches"""
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

        response = client.get("/api/admin/users?admin_id=admin123&role=staff")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["users"][0]["name"] == "Staff"

    def test_users_endpoint_status_filter_active(self, client, mock_db):
        """Cover lines 232, 237 - status filter for active users"""
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

        response = client.get("/api/admin/users?admin_id=admin123&status=active")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["users"][0]["name"] == "Active"

    def test_add_staff_missing_email(self, client, mock_db):
        """Cover line 298 - missing email field"""
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
            "password": "Password123!",
            "name": "Staff User"
            # missing email
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "required" in data["error"].lower()

    def test_add_staff_missing_password(self, client, mock_db):
        """Cover line 298 - missing password field"""
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
            "email": "staff@test.com",
            "name": "Staff User"
            # missing password
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "required" in data["error"].lower()

    def test_add_manager_missing_email(self, client, mock_db):
        """Cover line 303 - missing email for manager"""
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
            "password": "Password123!",
            "name": "Manager User",
            "manager_type": "manager"
            # missing email
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "required" in data["error"].lower()

    def test_remove_staff_user_not_exists(self, client, mock_db):
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

    def test_remove_manager_user_not_exists(self, client, mock_db):
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

    def test_change_role_user_not_exists(self, client, mock_db):
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

        response = client.put("/api/admin/users/nonexistent/role?admin_id=admin123", json={
            "role": "manager"
        })
        
        assert response.status_code == 404

    def test_change_status_user_not_exists(self, client, mock_db):
        """Cover lines 543-544 - user doesn't exist for status change"""
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

    def test_tasks_endpoint_no_admin_id_header(self, client):
        """Cover lines 630 - tasks endpoint without admin_id"""
        response = client.get("/api/admin/tasks")
        
        assert response.status_code == 401
        data = response.get_json()
        assert "admin_id required" in data["error"]

    def test_projects_endpoint_no_admin_id_header(self, client):
        """Cover lines 669 - projects endpoint without admin_id"""
        response = client.get("/api/admin/projects")
        
        assert response.status_code == 401
        data = response.get_json()
        assert "admin_id required" in data["error"]

    def test_cleanup_various_confirm_values(self, client):
        """Cover lines 737-740 - cleanup with different confirm values"""
        # Test with no confirm parameter
        response = client.delete("/api/admin/cleanup/user123")
        assert response.status_code == 400
        
        # Test with confirm=false
        response = client.delete("/api/admin/cleanup/user123?confirm=false")
        assert response.status_code == 400
        
        # Test with confirm=FALSE
        response = client.delete("/api/admin/cleanup/user123?confirm=FALSE")
        assert response.status_code == 400
        
        # Test with empty confirm
        response = client.delete("/api/admin/cleanup/user123?confirm=")
        assert response.status_code == 400
