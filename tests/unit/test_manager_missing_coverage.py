"""
Complete test coverage for manager.py missing lines
Targeting: 237-356 (dashboard), 610, 767-814 (all-users), 
1050-1096 (assign-manager), 1134-1227 (assign-staff bulk),
1254-1305 (remove-manager), 1336-1365 (my-team)
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import sys

fake_firestore = sys.modules.get("firebase_admin.firestore")


class TestManagerDashboardEndpoint:
    """Test manager_dashboard endpoint - lines 237-356"""
    
    def test_dashboard_missing_manager_id(self, client, mock_db, monkeypatch):
        """Test GET /api/manager/dashboard without manager ID"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        response = client.get("/api/manager/dashboard")
        assert response.status_code == 401
        assert "Manager ID required" in response.get_json().get("error", "")
    
    def test_dashboard_manager_not_found(self, client, mock_db, monkeypatch):
        """Test dashboard when manager doesn't exist"""
        mock_mgr = Mock()
        mock_mgr.exists = False
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_mgr
                mock_coll.document.return_value = mock_doc_ref
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(
            "/api/manager/dashboard",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 404
        assert "Manager not found" in response.get_json().get("error", "")
    
    def test_dashboard_insufficient_permissions(self, client, mock_db, monkeypatch):
        """Test dashboard with non-manager role (staff)"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "staff", "name": "Staff User"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_mgr
                mock_coll.document.return_value = mock_doc_ref
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(
            "/api/manager/dashboard",
            headers={"X-User-Id": "staff123"}
        )
        assert response.status_code == 403
    
    def test_dashboard_field_filter_exception_handling(self, client, mock_db, monkeypatch):
        """Test dashboard FieldFilter fallback exception handling (lines 265-267)"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager", "name": "Manager"}
        
        call_count = {"users_where": 0}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_mgr
                mock_coll.document.return_value = mock_doc_ref
                
                # First where() call for FieldFilter - raise exception
                # Second where() call in team retrieval should work
                def where_side_effect(filter=None, **kwargs):
                    if filter:  # FieldFilter case
                        if call_count["users_where"] == 0:
                            call_count["users_where"] += 1
                            raise Exception("FieldFilter not available")
                    mock_where_result = Mock()
                    mock_where_result.stream.return_value = iter([])
                    return mock_where_result
                
                mock_coll.where.side_effect = where_side_effect
                
            elif name == "memberships":
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([])
                mock_coll.where.return_value = mock_where_result
                
            elif name == "tasks":
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([])
                mock_coll.where.return_value = mock_where_result
                
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(
            "/api/manager/dashboard",
            headers={"X-User-Id": "mgr123"}
        )
        # Should still succeed despite FieldFilter exception (fallback to empty team)
        assert response.status_code == 200
    
    def test_dashboard_success_with_memberships_and_team(self, client, mock_db, monkeypatch):
        """Test successful dashboard with project memberships and team members"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "manager",
            "name": "Manager Name",
            "email": "manager@test.com"
        }
        
        # Mock membership
        mock_membership1 = Mock()
        mock_membership1.to_dict.return_value = {"project_id": "proj1", "user_id": "mgr123"}
        
        # Mock team member
        mock_staff1 = Mock()
        mock_staff1.id = "staff1"
        mock_staff1.exists = True
        mock_staff1.to_dict.return_value = {
            "name": "Staff One",
            "email": "staff1@test.com",
            "role": "staff",
            "is_active": True
        }
        
        # Mock task
        mock_task1 = Mock()
        mock_task1.id = "task1"
        mock_task1.to_dict.return_value = {
            "title": "Test Task",
            "status": "In Progress",
            "priority": 5,
            "due_date": "2025-11-10T10:00:00+00:00",
            "created_by": {"user_id": "staff1", "name": "Staff One"},
            "assigned_to": {"user_id": "staff1", "name": "Staff One"}
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                    elif doc_id == "staff1":
                        mock_doc_ref.get.return_value = mock_staff1
                    else:
                        mock_not_found = Mock()
                        mock_not_found.exists = False
                        mock_doc_ref.get.return_value = mock_not_found
                    return mock_doc_ref
                
                mock_coll.document.side_effect = document_side_effect
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([mock_staff1])
                mock_coll.where.return_value = mock_where_result
                
            elif name == "memberships":
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([mock_membership1])
                mock_coll.where.return_value = mock_where_result
                
            elif name == "tasks":
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([mock_task1])
                mock_coll.where.return_value = mock_where_result
                
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(
            "/api/manager/dashboard",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "team_members" in data
        assert "team_tasks" in data
        assert "statistics" in data
        assert data["team_size"] >= 0
        assert "active_tasks" in data
        assert "completed_tasks" in data
    
    def test_dashboard_fallback_to_field_filter(self, client, mock_db, monkeypatch):
        """Test dashboard fallback when no memberships - uses FieldFilter"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "director",
            "name": "Director Name"
        }
        
        mock_staff = Mock()
        mock_staff.id = "staff1"
        mock_staff.exists = True
        mock_staff.to_dict.return_value = {
            "name": "Staff Member",
            "email": "staff@test.com",
            "role": "staff",
            "is_active": True
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                    elif doc_id == "staff1":
                        mock_doc_ref.get.return_value = mock_staff
                    return mock_doc_ref
                
                mock_coll.document.side_effect = document_side_effect
                
                # For where with FieldFilter (fallback)
                def where_side_effect(filter=None, **kwargs):
                    mock_where_result = Mock()
                    if filter:
                        # FieldFilter case - return staff
                        mock_where_result.stream.return_value = iter([mock_staff])
                    else:
                        # Regular where - return empty
                        mock_where_result.stream.return_value = iter([])
                    return mock_where_result
                
                mock_coll.where.side_effect = where_side_effect
                
            elif name == "memberships":
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([])
                mock_coll.where.return_value = mock_where_result
                
            elif name == "tasks":
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([])
                mock_coll.where.return_value = mock_where_result
                
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(
            "/api/manager/dashboard",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "team_members" in data
    
    def test_dashboard_with_completed_tasks(self, client, mock_db, monkeypatch):
        """Test dashboard statistics with completed tasks"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager", "name": "Manager"}
        
        mock_staff = Mock()
        mock_staff.id = "staff1"
        mock_staff.exists = True
        mock_staff.to_dict.return_value = {
            "name": "Staff",
            "email": "staff@test.com",
            "role": "staff",
            "is_active": True
        }
        
        # Completed task
        mock_completed = Mock()
        mock_completed.id = "task_completed"
        mock_completed.to_dict.return_value = {
            "title": "Completed Task",
            "status": "Completed",
            "priority": 3,
            "due_date": "2025-11-15T10:00:00+00:00",
            "created_by": {"user_id": "staff1", "name": "Staff"},
            "assigned_to": {"user_id": "staff1", "name": "Staff"}
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                    elif doc_id == "staff1":
                        mock_doc_ref.get.return_value = mock_staff
                    return mock_doc_ref
                
                mock_coll.document.side_effect = document_side_effect
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([mock_staff])
                mock_coll.where.return_value = mock_where_result
                
            elif name == "memberships":
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([])
                mock_coll.where.return_value = mock_where_result
                
            elif name == "tasks":
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([mock_completed])
                mock_coll.where.return_value = mock_where_result
                
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(
            "/api/manager/dashboard",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["statistics"]["completed_tasks"] >= 1
    
    def test_dashboard_with_overdue_tasks(self, client, mock_db, monkeypatch):
        """Test dashboard with overdue tasks"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager", "name": "Manager"}
        
        mock_staff = Mock()
        mock_staff.id = "staff1"
        mock_staff.exists = True
        mock_staff.to_dict.return_value = {
            "name": "Staff",
            "email": "staff@test.com",
            "role": "staff",
            "is_active": True
        }
        
        # Overdue task
        mock_overdue = Mock()
        mock_overdue.id = "task_overdue"
        mock_overdue.to_dict.return_value = {
            "title": "Overdue Task",
            "status": "In Progress",
            "priority": 5,
            "due_date": "2020-01-01T10:00:00+00:00",
            "created_by": {"user_id": "staff1", "name": "Staff"},
            "assigned_to": {"user_id": "staff1", "name": "Staff"}
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                    elif doc_id == "staff1":
                        mock_doc_ref.get.return_value = mock_staff
                    return mock_doc_ref
                
                mock_coll.document.side_effect = document_side_effect
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([mock_staff])
                mock_coll.where.return_value = mock_where_result
                
            elif name == "memberships":
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([])
                mock_coll.where.return_value = mock_where_result
                
            elif name == "tasks":
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([mock_overdue])
                mock_coll.where.return_value = mock_where_result
                
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(
            "/api/manager/dashboard",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["statistics"]["overdue_count"] >= 1


class TestGetAllUsersEndpoint:
    """Test get_all_users endpoint - lines 767-814"""
    
    def test_get_all_users_missing_manager_id(self, client, mock_db, monkeypatch):
        """Test GET /api/manager/all-users without manager ID"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        response = client.get("/api/manager/all-users")
        assert response.status_code == 401
        assert "Manager ID required" in response.get_json().get("error", "")
    
    def test_get_all_users_manager_not_found(self, client, mock_db, monkeypatch):
        """Test all-users when manager doesn't exist"""
        mock_mgr = Mock()
        mock_mgr.exists = False
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_mgr
                mock_coll.document.return_value = mock_doc_ref
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(
            "/api/manager/all-users",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 404
    
    def test_get_all_users_insufficient_permissions(self, client, mock_db, monkeypatch):
        """Test all-users with non-manager role"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "staff"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_user
                mock_coll.document.return_value = mock_doc_ref
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(
            "/api/manager/all-users",
            headers={"X-User-Id": "staff123"}
        )
        assert response.status_code == 403
    
    def test_get_all_users_success_separates_staff_and_managers(self, client, mock_db, monkeypatch):
        """Test successful retrieval separating staff and managers"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        # Staff user
        mock_staff = Mock()
        mock_staff.id = "staff1"
        mock_staff.to_dict.return_value = {
            "name": "Staff User",
            "email": "staff@test.com",
            "role": "staff",
            "is_active": True,
            "manager_id": "mgr123",
            "created_at": "2025-01-01T00:00:00+00:00"
        }
        
        # Manager user
        mock_other_mgr = Mock()
        mock_other_mgr.id = "mgr2"
        mock_other_mgr.to_dict.return_value = {
            "name": "Other Manager",
            "email": "mgr2@test.com",
            "role": "director",
            "is_active": True,
            "created_at": "2025-01-01T00:00:00+00:00"
        }
        
        # HR user (should go to managers list)
        mock_hr = Mock()
        mock_hr.id = "hr1"
        mock_hr.to_dict.return_value = {
            "name": "HR User",
            "email": "hr@test.com",
            "role": "hr",
            "is_active": True,
            "created_at": "2025-01-01T00:00:00+00:00"
        }
        
        # Admin user (should go to managers list)
        mock_admin = Mock()
        mock_admin.id = "admin1"
        mock_admin.to_dict.return_value = {
            "name": "Admin User",
            "email": "admin@test.com",
            "role": "admin",
            "is_active": True,
            "created_at": "2025-01-01T00:00:00+00:00"
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_mgr
                mock_coll.document.return_value = mock_doc_ref
                # For stream() call
                mock_coll.stream.return_value = iter([mock_staff, mock_other_mgr, mock_hr, mock_admin])
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(
            "/api/manager/all-users",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "staff" in data
        assert "managers" in data
        assert "total_staff" in data
        assert "total_managers" in data
        assert data["total_staff"] >= 1
        assert data["total_managers"] >= 3  # director, hr, admin
    
    def test_get_all_users_exception_handling(self, client, mock_db, monkeypatch):
        """Test exception handling in get_all_users"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_mgr
                mock_coll.document.return_value = mock_doc_ref
                # Raise exception on stream
                mock_coll.stream.side_effect = Exception("Database error")
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(
            "/api/manager/all-users",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 500
        assert "error" in response.get_json()


class TestAssignManagerToStaffEndpoint:
    """Test assign_manager_to_staff endpoint - lines 1050-1096"""
    
    def test_assign_manager_missing_manager_id(self, client, mock_db, monkeypatch):
        """Test POST /api/manager/staff/<id>/assign-manager without manager ID"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        response = client.post(
            "/api/manager/staff/staff123/assign-manager",
            json={"manager_id": "mgr2"}
        )
        assert response.status_code == 401
    
    def test_assign_manager_target_manager_not_found(self, client, mock_db, monkeypatch):
        """Test when target manager doesn't exist"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        mock_target = Mock()
        mock_target.exists = False
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                    elif doc_id == "mgr2":
                        mock_doc_ref.get.return_value = mock_target
                    return mock_doc_ref
                mock_coll.document.side_effect = document_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/staff/staff123/assign-manager",
            headers={"X-User-Id": "mgr123"},
            json={"manager_id": "mgr2"}
        )
        assert response.status_code == 404
        assert "Target manager not found" in response.get_json().get("error", "")
    
    def test_assign_manager_target_not_manager_role(self, client, mock_db, monkeypatch):
        """Test when target is not a manager"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"role": "staff", "name": "Not Manager"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                    elif doc_id == "staff2":
                        mock_doc_ref.get.return_value = mock_target
                    return mock_doc_ref
                mock_coll.document.side_effect = document_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/staff/staff123/assign-manager",
            headers={"X-User-Id": "mgr123"},
            json={"manager_id": "staff2"}
        )
        assert response.status_code == 400
        assert "not a manager" in response.get_json().get("error", "")
    
    def test_assign_manager_staff_not_found(self, client, mock_db, monkeypatch):
        """Test when staff member doesn't exist"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        mock_target_mgr = Mock()
        mock_target_mgr.exists = True
        mock_target_mgr.to_dict.return_value = {
            "role": "manager",
            "name": "Target Manager",
            "email": "target@test.com"
        }
        
        mock_staff = Mock()
        mock_staff.exists = False
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                    elif doc_id == "mgr2":
                        mock_doc_ref.get.return_value = mock_target_mgr
                    elif doc_id == "staff999":
                        mock_doc_ref.get.return_value = mock_staff
                    return mock_doc_ref
                mock_coll.document.side_effect = document_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/staff/staff999/assign-manager",
            headers={"X-User-Id": "mgr123"},
            json={"manager_id": "mgr2"}
        )
        assert response.status_code == 404
        assert "Staff member not found" in response.get_json().get("error", "")
    
    def test_assign_manager_user_not_staff_role(self, client, mock_db, monkeypatch):
        """Test when user is not a staff member"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        mock_target_mgr = Mock()
        mock_target_mgr.exists = True
        mock_target_mgr.to_dict.return_value = {
            "role": "director",
            "name": "Target Manager"
        }
        
        mock_staff = Mock()
        mock_staff.exists = True
        mock_staff.to_dict.return_value = {"role": "manager"}  # Not staff!
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                    elif doc_id == "mgr2":
                        mock_doc_ref.get.return_value = mock_target_mgr
                    elif doc_id == "not_staff":
                        mock_doc_ref.get.return_value = mock_staff
                    return mock_doc_ref
                mock_coll.document.side_effect = document_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/staff/not_staff/assign-manager",
            headers={"X-User-Id": "mgr123"},
            json={"manager_id": "mgr2"}
        )
        assert response.status_code == 400
        assert "not a staff member" in response.get_json().get("error", "")
    
    def test_assign_manager_success(self, client, mock_db, monkeypatch):
        """Test successful manager assignment"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        mock_target_mgr = Mock()
        mock_target_mgr.exists = True
        mock_target_mgr.to_dict.return_value = {
            "role": "manager",
            "name": "Target Manager",
            "email": "target@test.com"
        }
        
        mock_staff_doc = Mock()
        mock_staff_doc.exists = True
        mock_staff_doc.to_dict.return_value = {
            "role": "staff",
            "name": "Staff Member",
            "email": "staff@test.com"
        }
        
        mock_staff_ref = Mock()
        mock_staff_ref.get.return_value = mock_staff_doc
        mock_staff_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                    elif doc_id == "mgr2":
                        mock_doc_ref.get.return_value = mock_target_mgr
                    elif doc_id == "staff1":
                        return mock_staff_ref
                    return mock_doc_ref
                mock_coll.document.side_effect = document_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/staff/staff1/assign-manager",
            headers={"X-User-Id": "mgr123"},
            json={"manager_id": "mgr2"}
        )
        assert response.status_code == 200
        assert mock_staff_ref.update.called
        data = response.get_json()
        assert data["staff_id"] == "staff1"
        assert data["manager_id"] == "mgr2"
    
    def test_assign_manager_defaults_to_self(self, client, mock_db, monkeypatch):
        """Test assigning manager defaults to current manager when no manager_id provided (line 1059)"""
        call_count = {"mgr123_calls": 0}
        
        mock_mgr_verify = Mock()
        mock_mgr_verify.exists = True
        mock_mgr_verify.to_dict.return_value = {
            "role": "manager",
            "name": "Manager",
            "email": "mgr@test.com"
        }
        
        mock_staff_doc = Mock()
        mock_staff_doc.exists = True
        mock_staff_doc.to_dict.return_value = {
            "role": "staff",
            "name": "Staff Member",
            "email": "staff@test.com"
        }
        
        mock_staff_ref = Mock()
        mock_staff_ref.get.return_value = mock_staff_doc
        mock_staff_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "mgr123":
                        mock_doc_ref = Mock()
                        # First call: verification, Second call: target manager check
                        if call_count["mgr123_calls"] == 0:
                            mock_doc_ref.get.return_value = mock_mgr_verify
                            call_count["mgr123_calls"] += 1
                        else:
                            mock_doc_ref.get.return_value = mock_mgr_verify
                        return mock_doc_ref
                    elif doc_id == "staff1":
                        return mock_staff_ref
                    return Mock()
                mock_coll.document.side_effect = document_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/staff/staff1/assign-manager",
            headers={"X-User-Id": "mgr123"},
            json={}  # No manager_id - should default to mgr123
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["manager_id"] == "mgr123"
        # Verify mgr123 was checked as target manager (defaulted to self)
        assert call_count["mgr123_calls"] >= 1


class TestBulkAssignStaffEndpoint:
    """Test bulk assign-staff endpoint - lines 1134-1227"""
    
    def test_bulk_assign_missing_manager_id(self, client, mock_db, monkeypatch):
        """Test POST /api/manager/assign-staff without manager ID"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        response = client.post(
            "/api/manager/assign-staff",
            json={"staff_ids": ["staff1", "staff2"]}
        )
        assert response.status_code == 401
    
    def test_bulk_assign_invalid_staff_ids_not_array(self, client, mock_db, monkeypatch):
        """Test bulk assign with non-array staff_ids"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_mgr
                mock_coll.document.return_value = mock_doc_ref
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/assign-staff",
            headers={"X-User-Id": "mgr123"},
            json={"staff_ids": "not_an_array"}
        )
        assert response.status_code == 400
        assert "non-empty array" in response.get_json().get("error", "")
    
    def test_bulk_assign_empty_staff_ids(self, client, mock_db, monkeypatch):
        """Test bulk assign with empty array"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_mgr
                mock_coll.document.return_value = mock_doc_ref
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/assign-staff",
            headers={"X-User-Id": "mgr123"},
            json={"staff_ids": []}
        )
        assert response.status_code == 400
    
    def test_bulk_assign_target_manager_not_found(self, client, mock_db, monkeypatch):
        """Test bulk assign when target manager doesn't exist"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        mock_target = Mock()
        mock_target.exists = False
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                    elif doc_id == "mgr_invalid":
                        mock_doc_ref.get.return_value = mock_target
                    return mock_doc_ref
                mock_coll.document.side_effect = document_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/assign-staff",
            headers={"X-User-Id": "mgr123"},
            json={"staff_ids": ["staff1"], "manager_id": "mgr_invalid"}
        )
        assert response.status_code == 404
    
    def test_bulk_assign_target_not_manager_role(self, client, mock_db, monkeypatch):
        """Test bulk assign when target is not a manager"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"role": "staff"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                    elif doc_id == "not_mgr":
                        mock_doc_ref.get.return_value = mock_target
                    return mock_doc_ref
                mock_coll.document.side_effect = document_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/assign-staff",
            headers={"X-User-Id": "mgr123"},
            json={"staff_ids": ["staff1"], "manager_id": "not_mgr"}
        )
        assert response.status_code == 400
    
    def test_bulk_assign_with_mixed_results(self, client, mock_db, monkeypatch):
        """Test bulk assign with some success, some failures"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "manager",
            "name": "Manager",
            "email": "mgr@test.com",
            "team_staff_ids": []
        }
        
        # Staff that exists
        mock_staff1_doc = Mock()
        mock_staff1_doc.exists = True
        mock_staff1_doc.to_dict.return_value = {
            "role": "staff",
            "name": "Staff 1",
            "email": "staff1@test.com"
        }
        mock_staff1_ref = Mock()
        mock_staff1_ref.get.return_value = mock_staff1_doc
        mock_staff1_ref.update = Mock()
        
        # Staff that doesn't exist
        mock_staff2_doc = Mock()
        mock_staff2_doc.exists = False
        mock_staff2_ref = Mock()
        mock_staff2_ref.get.return_value = mock_staff2_doc
        
        # User with wrong role
        mock_staff3_doc = Mock()
        mock_staff3_doc.exists = True
        mock_staff3_doc.to_dict.return_value = {"role": "manager"}
        mock_staff3_ref = Mock()
        mock_staff3_ref.get.return_value = mock_staff3_doc
        
        mock_mgr_ref = Mock()
        mock_mgr_ref.get.return_value = mock_mgr
        mock_mgr_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "mgr123":
                        return mock_mgr_ref
                    elif doc_id == "staff1":
                        return mock_staff1_ref
                    elif doc_id == "staff_not_found":
                        return mock_staff2_ref
                    elif doc_id == "wrong_role":
                        return mock_staff3_ref
                    return Mock()
                mock_coll.document.side_effect = document_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/assign-staff",
            headers={"X-User-Id": "mgr123"},
            json={"staff_ids": ["staff1", "staff_not_found", "wrong_role"]}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["staff_assigned"]) >= 1
        assert len(data["failed"]) >= 2
        assert mock_mgr_ref.update.called
    
    def test_bulk_assign_defaults_to_self(self, client, mock_db, monkeypatch):
        """Test bulk assign defaults to current manager when no manager_id (line 1143)"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "manager",
            "name": "Manager",
            "email": "mgr@test.com",
            "team_staff_ids": []
        }
        
        mock_staff_doc = Mock()
        mock_staff_doc.exists = True
        mock_staff_doc.to_dict.return_value = {
            "role": "staff",
            "name": "Staff 1",
            "email": "staff1@test.com"
        }
        mock_staff_ref = Mock()
        mock_staff_ref.get.return_value = mock_staff_doc
        mock_staff_ref.update = Mock()
        
        mock_mgr_ref = Mock()
        mock_mgr_ref.get.return_value = mock_mgr
        mock_mgr_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "mgr123":
                        return mock_mgr_ref
                    elif doc_id == "staff1":
                        return mock_staff_ref
                    return Mock()
                mock_coll.document.side_effect = document_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/assign-staff",
            headers={"X-User-Id": "mgr123"},
            json={"staff_ids": ["staff1"]}  # No manager_id - should default to mgr123
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["staff_assigned"]) == 1
    
    def test_bulk_assign_exception_handling(self, client, mock_db, monkeypatch):
        """Test exception handling during bulk assignment"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "manager",
            "team_staff_ids": []
        }
        
        mock_staff_doc = Mock()
        mock_staff_doc.exists = True
        mock_staff_doc.to_dict.side_effect = Exception("Database error")
        
        mock_staff_ref = Mock()
        mock_staff_ref.get.return_value = mock_staff_doc
        
        mock_mgr_ref = Mock()
        mock_mgr_ref.get.return_value = mock_mgr
        mock_mgr_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "mgr123":
                        return mock_mgr_ref
                    elif doc_id == "staff_error":
                        return mock_staff_ref
                    return Mock()
                mock_coll.document.side_effect = document_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/assign-staff",
            headers={"X-User-Id": "mgr123"},
            json={"staff_ids": ["staff_error"]}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["failed"]) >= 1


class TestRemoveStaffFromManagerEndpoint:
    """Test remove_staff_from_manager endpoint - lines 1254-1305"""
    
    def test_remove_staff_missing_manager_id(self, client, mock_db, monkeypatch):
        """Test DELETE /api/manager/staff/<id>/remove-manager without manager ID"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        response = client.delete("/api/manager/staff/staff123/remove-manager")
        assert response.status_code == 401
    
    def test_remove_staff_staff_not_found(self, client, mock_db, monkeypatch):
        """Test remove when staff doesn't exist"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        mock_staff_doc = Mock()
        mock_staff_doc.exists = False
        mock_staff_ref = Mock()
        mock_staff_ref.get.return_value = mock_staff_doc
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "mgr123":
                        mock_doc_ref = Mock()
                        mock_doc_ref.get.return_value = mock_mgr
                        return mock_doc_ref
                    elif doc_id == "staff_not_found":
                        return mock_staff_ref
                    return Mock()
                mock_coll.document.side_effect = document_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete(
            "/api/manager/staff/staff_not_found/remove-manager",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 404
    
    def test_remove_staff_not_assigned_to_manager(self, client, mock_db, monkeypatch):
        """Test remove when staff is not assigned to this manager"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        mock_staff_doc = Mock()
        mock_staff_doc.exists = True
        mock_staff_doc.to_dict.return_value = {
            "manager_id": "other_mgr",
            "role": "staff"
        }
        mock_staff_ref = Mock()
        mock_staff_ref.get.return_value = mock_staff_doc
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "mgr123":
                        mock_doc_ref = Mock()
                        mock_doc_ref.get.return_value = mock_mgr
                        return mock_doc_ref
                    elif doc_id == "staff1":
                        return mock_staff_ref
                    return Mock()
                mock_coll.document.side_effect = document_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete(
            "/api/manager/staff/staff1/remove-manager",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 403
    
    def test_remove_staff_success(self, client, mock_db, monkeypatch):
        """Test successful staff removal"""
        # Need separate references for verification and for staff update
        mock_current_mgr_doc_verify = Mock()
        mock_current_mgr_doc_verify.exists = True
        mock_current_mgr_doc_verify.to_dict.return_value = {"role": "manager"}
        
        mock_current_mgr_doc_update = Mock()
        mock_current_mgr_doc_update.exists = True
        mock_current_mgr_doc_update.to_dict.return_value = {
            "team_staff_ids": ["staff1", "staff2"]
        }
        
        mock_staff_doc = Mock()
        mock_staff_doc.exists = True
        mock_staff_doc.to_dict.return_value = {
            "manager_id": "mgr123",
            "role": "staff"
        }
        mock_staff_ref = Mock()
        mock_staff_ref.get.return_value = mock_staff_doc
        mock_staff_ref.update = Mock()
        
        call_count = {"mgr123": 0}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "mgr123":
                        mock_ref = Mock()
                        # First call: verification - return role info
                        # Second call: update team - return team info
                        if call_count["mgr123"] == 0:
                            mock_ref.get.return_value = mock_current_mgr_doc_verify
                            call_count["mgr123"] += 1
                        else:
                            mock_ref.get.return_value = mock_current_mgr_doc_update
                        mock_ref.update = Mock()
                        return mock_ref
                    elif doc_id == "staff1":
                        return mock_staff_ref
                    return Mock()
                mock_coll.document.side_effect = document_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete(
            "/api/manager/staff/staff1/remove-manager",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 200
        assert mock_staff_ref.update.called
    
    def test_remove_staff_director_can_remove_anyone(self, client, mock_db, monkeypatch):
        """Test that director can remove any staff (director is in manager roles)"""
        # Separate docs for verification and update phases
        mock_director_verify = Mock()
        mock_director_verify.exists = True
        mock_director_verify.to_dict.return_value = {"role": "director"}
        
        mock_staff_doc = Mock()
        mock_staff_doc.exists = True
        mock_staff_doc.to_dict.return_value = {
            "manager_id": "other_mgr",
            "role": "staff"
        }
        mock_staff_ref = Mock()
        mock_staff_ref.get.return_value = mock_staff_doc
        mock_staff_ref.update = Mock()
        
        mock_other_mgr_doc = Mock()
        mock_other_mgr_doc.exists = True
        mock_other_mgr_doc.to_dict.return_value = {
            "team_staff_ids": ["staff1"]
        }
        mock_other_mgr_ref = Mock()
        mock_other_mgr_ref.get.return_value = mock_other_mgr_doc
        mock_other_mgr_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "director123":
                        mock_ref = Mock()
                        mock_ref.get.return_value = mock_director_verify
                        return mock_ref
                    elif doc_id == "staff1":
                        return mock_staff_ref
                    elif doc_id == "other_mgr":
                        return mock_other_mgr_ref
                    return Mock()
                mock_coll.document.side_effect = document_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete(
            "/api/manager/staff/staff1/remove-manager",
            headers={"X-User-Id": "director123"}
        )
        assert response.status_code == 200
        assert mock_staff_ref.update.called


class TestGetMyTeamEndpoint:
    """Test get_my_team endpoint - lines 1336-1365"""
    
    def test_get_my_team_missing_manager_id(self, client, mock_db, monkeypatch):
        """Test GET /api/manager/my-team without manager ID"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        response = client.get("/api/manager/my-team")
        assert response.status_code == 401
    
    def test_get_my_team_manager_not_found(self, client, mock_db, monkeypatch):
        """Test my-team when manager doesn't exist"""
        mock_mgr = Mock()
        mock_mgr.exists = False
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_mgr
                mock_coll.document.return_value = mock_doc_ref
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(
            "/api/manager/my-team",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 404
    
    def test_get_my_team_success(self, client, mock_db, monkeypatch):
        """Test successful retrieval of team staff"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        # Mock staff member
        mock_staff1 = Mock()
        mock_staff1.id = "staff1"
        mock_staff1.to_dict.return_value = {
            "name": "Staff Member",
            "email": "staff@test.com",
            "role": "staff",
            "is_active": True,
            "manager_assigned_at": "2025-01-01T00:00:00+00:00",
            "created_at": "2024-01-01T00:00:00+00:00"
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_mgr
                mock_coll.document.return_value = mock_doc_ref
                
                # For where query
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([mock_staff1])
                mock_coll.where.return_value = mock_where_result
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(
            "/api/manager/my-team",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "team_staff" in data
        assert "team_size" in data
        assert data["team_size"] >= 1
        assert len(data["team_staff"]) >= 1
    
    def test_get_my_team_empty_team(self, client, mock_db, monkeypatch):
        """Test when manager has no team staff"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_mgr
                mock_coll.document.return_value = mock_doc_ref
                
                # Empty results
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([])
                mock_coll.where.return_value = mock_where_result
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(
            "/api/manager/my-team",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["team_size"] == 0
        assert len(data["team_staff"]) == 0


class TestAssignTaskToTeamMember:
    """Test assign_task_to_team_member - line 610"""
    
    def test_assign_task_assignee_not_in_team(self, client, mock_db, monkeypatch):
        """Test assigning task to non-team member (line 610)"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {"title": "Test Task"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "mgr123":
                        mock_doc_ref = Mock()
                        mock_doc_ref.get.return_value = mock_mgr
                        return mock_doc_ref
                    return Mock()
                
                mock_coll.document.side_effect = document_side_effect
                # For where query - return empty team
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([])
                mock_coll.where.return_value = mock_where_result
                
            elif name == "tasks":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_task
                mock_coll.document.return_value = mock_doc_ref
                
            elif name == "memberships":
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([])
                mock_coll.where.return_value = mock_where_result
                
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/tasks/task123/assign",
            headers={"X-User-Id": "mgr123"},
            json={"assignee_ids": ["not_in_team"]}
        )
        assert response.status_code == 403
        assert "not in your team" in response.get_json().get("error", "")
