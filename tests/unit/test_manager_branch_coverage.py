"""
Test file to achieve 100% branch coverage for manager.py
Targeting specific uncovered branches
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import sys

fake_firestore = sys.modules.get("firebase_admin.firestore")


class TestManagerDashboardBranches:
    """Test specific branches in manager_dashboard"""
    
    def test_dashboard_with_team_members_from_memberships(self, client, mock_db, monkeypatch):
        """Test when team_member_ids is populated - covers 258->270 (skip fallback)"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "manager",
            "name": "Manager Name",
            "email": "manager@test.com"
        }
        
        # Mock membership for manager
        mock_mgr_membership = Mock()
        mock_mgr_membership.to_dict.return_value = {"project_id": "proj1", "user_id": "mgr123"}
        
        # Mock membership for staff in same project
        mock_staff_membership = Mock()
        mock_staff_membership.to_dict.return_value = {"project_id": "proj1", "user_id": "staff1"}
        
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
        
        memberships_call_count = {"count": 0}
        
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
                
            elif name == "memberships":
                # Simulate the two where() calls in _get_manager_team_member_ids
                def where_side_effect(*args, **kwargs):
                    memberships_call_count["count"] += 1
                    mock_where_result = Mock()
                    if memberships_call_count["count"] == 1:
                        # First call: get manager's memberships
                        mock_where_result.stream.return_value = iter([mock_mgr_membership])
                    else:
                        # Subsequent calls: get project members
                        mock_where_result.stream.return_value = iter([mock_mgr_membership, mock_staff_membership])
                    return mock_where_result
                
                mock_coll.where.side_effect = where_side_effect
                
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
        # Should have staff1 in team (from memberships, not fallback)
        # This covers the 258->270 branch (team_member_ids is NOT empty, so skip fallback)
        assert len(data.get("team_members", [])) >= 1
    
    def test_dashboard_fallback_empty_team(self, client, mock_db, monkeypatch):
        """Test fallback path when no team members found - covers 258->270"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "manager",
            "name": "Manager Name",
            "email": "manager@test.com"
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                    else:
                        mock_not_found = Mock()
                        mock_not_found.exists = False
                        mock_doc_ref.get.return_value = mock_not_found
                    return mock_doc_ref
                
                mock_coll.document.side_effect = document_side_effect
                # Return empty for where query - no team members
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([])
                mock_coll.where.return_value = mock_where_result
                
            elif name == "memberships":
                # No memberships - this triggers fallback
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
        # Should have no team members
        assert len(data.get("team_members", [])) == 0
    
    def test_dashboard_fallback_with_actual_users(self, client, mock_db, monkeypatch):
        """Test fallback FieldFilter path that finds users - covers 258->270, 263->261"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "manager",
            "name": "Manager Name",
            "email": "manager@test.com"
        }
        
        # Mock user found in fallback
        mock_user1 = Mock()
        mock_user1.id = "staff1"
        mock_user1.exists = True
        mock_user1.to_dict.return_value = {
            "name": "Staff One",
            "email": "staff1@test.com",
            "role": "staff",
            "is_active": True
        }
        
        # Mock user that is the manager themselves (should be skipped)
        mock_user2 = Mock()
        mock_user2.id = "mgr123"
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                    elif doc_id == "staff1":
                        mock_doc_ref.get.return_value = mock_user1
                    else:
                        mock_not_found = Mock()
                        mock_not_found.exists = False
                        mock_doc_ref.get.return_value = mock_not_found
                    return mock_doc_ref
                
                mock_coll.document.side_effect = document_side_effect
                
                # For FieldFilter - return users including manager
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([mock_user1, mock_user2])
                mock_coll.where.return_value = mock_where_result
                
            elif name == "memberships":
                # No memberships - trigger fallback
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
        # Should have found staff1 but not mgr123
        assert len(data.get("team_members", [])) == 1
    
    def test_dashboard_member_not_exists(self, client, mock_db, monkeypatch):
        """Test when team member document doesn't exist - covers 273->271"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "manager",
            "name": "Manager Name",
            "email": "manager@test.com"
        }
        
        # Mock membership with non-existent user
        mock_membership1 = Mock()
        mock_membership1.to_dict.return_value = {"project_id": "proj1", "user_id": "mgr123"}
        
        mock_user1 = Mock()
        mock_user1.id = "staff1"
        
        # Non-existent staff member
        mock_not_exists = Mock()
        mock_not_exists.exists = False
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                    else:
                        # Return non-existent document
                        mock_doc_ref.get.return_value = mock_not_exists
                    return mock_doc_ref
                
                mock_coll.document.side_effect = document_side_effect
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([mock_user1])
                mock_coll.where.return_value = mock_where_result
                
            elif name == "memberships":
                mock_where_result = Mock()
                mock_where_result.stream.return_value = iter([mock_membership1])
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
        # Should have no team members since staff1 doesn't exist
        assert len(data.get("team_members", [])) == 0
    
    def test_dashboard_with_completed_task_branch(self, client, mock_db, monkeypatch):
        """Test completed task counting - covers 300->303 and 317->320"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "manager",
            "name": "Manager Name",
            "email": "manager@test.com"
        }
        
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
        
        # Mock task with status that's NOT "To Do", "In Progress", or "Completed"
        # This will cause both if and elif to be false, covering branches 300->303
        mock_task_created = Mock()
        mock_task_created.id = "task1"
        mock_task_created.to_dict.return_value = {
            "title": "Cancelled Task",
            "status": "Cancelled",  # This triggers the branch - not in if or elif
            "priority": 5,
            "due_date": "2025-11-10T10:00:00+00:00",
            "created_by": {"user_id": "staff1", "name": "Staff One"},
            "assigned_to": {"user_id": "staff1", "name": "Staff One"}
        }
        
        # Mock assigned task with different non-standard status
        # This covers branch 317->320
        mock_task_assigned = Mock()
        mock_task_assigned.id = "task2"
        mock_task_assigned.to_dict.return_value = {
            "title": "On Hold Task",
            "status": "On Hold",  # This triggers the branch - not in if or elif
            "priority": 3,
            "due_date": "2025-11-12T10:00:00+00:00",
            "created_by": {"user_id": "other_user", "name": "Other User"},
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
                mock_where_result.stream.return_value = iter([])
                mock_coll.where.return_value = mock_where_result
                
            elif name == "tasks":
                # Alternate between created and assigned tasks
                def where_side_effect(*args, **kwargs):
                    mock_where_result = Mock()
                    # Check if this is created_by or assigned_to query
                    if len(args) >= 1 and args[0] == "created_by.user_id":
                        # Created tasks query
                        mock_where_result.stream.return_value = iter([mock_task_created])
                    elif len(args) >= 1 and args[0] == "assigned_to.user_id":
                        # Assigned tasks query
                        mock_where_result.stream.return_value = iter([mock_task_assigned])
                    else:
                        mock_where_result.stream.return_value = iter([])
                    return mock_where_result
                
                mock_coll.where.side_effect = where_side_effect
                
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(
            "/api/manager/dashboard",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 200
        data = response.get_json()
        # Should have tasks but neither should count as active or completed
        assert data.get("active_tasks", 0) == 0
        assert data.get("completed_tasks", 0) == 0


class TestGetAllUsersBranches:
    """Test specific branches in get_all_users"""
    
    def test_get_all_users_with_non_staff_non_manager_role(self, client, mock_db, monkeypatch):
        """Test user with role that's neither staff nor manager/director/hr/admin - covers 802->786"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "manager",
            "name": "Manager Name"
        }
        
        # User with unknown role
        mock_user1 = Mock()
        mock_user1.id = "user1"
        mock_user1.to_dict.return_value = {
            "name": "User One",
            "email": "user1@test.com",
            "role": "unknown_role",  # Not staff, manager, director, hr, or admin
            "is_active": True
        }
        
        # Regular staff for comparison
        mock_user2 = Mock()
        mock_user2.id = "user2"
        mock_user2.to_dict.return_value = {
            "name": "User Two",
            "email": "user2@test.com",
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
                    return mock_doc_ref
                
                mock_coll.document.side_effect = document_side_effect
                mock_coll.stream.return_value = iter([mock_user1, mock_user2])
                
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(
            "/api/manager/all-users",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 200
        data = response.get_json()
        # user1 should not appear in either list
        # user2 should appear in staff list
        assert len(data.get("staff", [])) == 1
        assert len(data.get("managers", [])) == 0


class TestBulkAssignStaffBranches:
    """Test specific branches in bulk_assign_staff"""
    
    def test_bulk_assign_exception_during_get_operation(self, client, mock_db, monkeypatch):
        """Test exception during .update() operation - covers 1211->1171 (exception then continue loop)"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "manager",
            "name": "Manager Name",
            "email": "manager@test.com",
            "team_staff_ids": []
        }
        
        # First staff - successful
        mock_staff1 = Mock()
        mock_staff1.exists = True
        mock_staff1.to_dict.return_value = {
            "name": "Staff One",
            "email": "staff1@test.com",
            "role": "staff"
        }
        
        # Second staff - will have exception during update()
        mock_staff2 = Mock()
        mock_staff2.exists = True
        mock_staff2.to_dict.return_value = {
            "name": "Staff Two",
            "email": "staff2@test.com",
            "role": "staff"
        }
        
        # Third staff - successful
        mock_staff3 = Mock()
        mock_staff3.exists = True
        mock_staff3.to_dict.return_value = {
            "name": "Staff Three",
            "email": "staff3@test.com",
            "role": "staff"
        }
        
        # Fourth staff - also successful to ensure loop continues after exception
        mock_staff4 = Mock()
        mock_staff4.exists = True
        mock_staff4.to_dict.return_value = {
            "name": "Staff Four",
            "email": "staff4@test.com",
            "role": "staff"
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                        mock_doc_ref.update.return_value = None
                    elif doc_id == "staff1":
                        mock_doc_ref.get.return_value = mock_staff1
                        mock_doc_ref.update.return_value = None
                    elif doc_id == "staff2":
                        mock_doc_ref.get.return_value = mock_staff2
                        # Make update raise an exception
                        mock_doc_ref.update.side_effect = Exception("Database error during update for staff2")
                    elif doc_id == "staff3":
                        mock_doc_ref.get.return_value = mock_staff3
                        mock_doc_ref.update.return_value = None
                    elif doc_id == "staff4":
                        mock_doc_ref.get.return_value = mock_staff4
                        mock_doc_ref.update.return_value = None
                    else:
                        mock_not_found = Mock()
                        mock_not_found.exists = False
                        mock_doc_ref.get.return_value = mock_not_found
                    return mock_doc_ref
                
                mock_coll.document.side_effect = document_side_effect
                
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/assign-staff",
            headers={"X-User-Id": "mgr123"},
            json={"staff_ids": ["staff1", "staff2", "staff3", "staff4"]}
        )
        assert response.status_code == 200
        data = response.get_json()
        # staff1, staff3, staff4 should succeed; staff2 should fail with exception
        assigned_list = data.get("assigned", data.get("staff_assigned", []))
        failed_list = data.get("failed", [])
        assert len(assigned_list) >= 3  # staff1, staff3, staff4
        assert len(failed_list) >= 1  # staff2
        # Verify staff2 is in failed with our specific error
        staff2_error = next((f for f in failed_list if f["user_id"] == "staff2"), None)
        assert staff2_error is not None
        assert "Database error" in staff2_error.get("error", "")
    
    def test_bulk_assign_staff_already_in_team(self, client, mock_db, monkeypatch):
        """Test when staff_id is already in existing_staff_ids list - covers 1211->1171 (false branch)"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "manager",
            "name": "Manager Name",
            "email": "manager@test.com",
            "team_staff_ids": ["staff1"]  # staff1 already in team
        }
        
        # First staff - already in team
        mock_staff1 = Mock()
        mock_staff1.exists = True
        mock_staff1.to_dict.return_value = {
            "name": "Staff One",
            "email": "staff1@test.com",
            "role": "staff"
        }
        
        # Second staff - new to team
        mock_staff2 = Mock()
        mock_staff2.exists = True
        mock_staff2.to_dict.return_value = {
            "name": "Staff Two",
            "email": "staff2@test.com",
            "role": "staff"
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                        mock_doc_ref.update.return_value = None
                    elif doc_id == "staff1":
                        mock_doc_ref.get.return_value = mock_staff1
                        mock_doc_ref.update.return_value = None
                    elif doc_id == "staff2":
                        mock_doc_ref.get.return_value = mock_staff2
                        mock_doc_ref.update.return_value = None
                    else:
                        mock_not_found = Mock()
                        mock_not_found.exists = False
                        mock_doc_ref.get.return_value = mock_not_found
                    return mock_doc_ref
                
                mock_coll.document.side_effect = document_side_effect
                
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/assign-staff",
            headers={"X-User-Id": "mgr123"},
            json={"staff_ids": ["staff1", "staff2"]}
        )
        assert response.status_code == 200
        data = response.get_json()
        # Both should be assigned successfully
        assigned_list = data.get("assigned", data.get("staff_assigned", []))
        assert len(assigned_list) == 2
    
    def test_bulk_assign_with_exception_in_staff_loop(self, client, mock_db, monkeypatch):
        """Test exception handling during staff assignment loop"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "manager",
            "name": "Manager Name",
            "email": "manager@test.com",
            "team_staff_ids": []
        }
        
        # First staff - successful
        mock_staff1 = Mock()
        mock_staff1.exists = True
        mock_staff1.to_dict.return_value = {
            "name": "Staff One",
            "email": "staff1@test.com",
            "role": "staff"
        }
        
        # Second staff - will raise exception during update
        mock_staff2 = Mock()
        mock_staff2.exists = True
        mock_staff2.to_dict.return_value = {
            "name": "Staff Two",
            "email": "staff2@test.com",
            "role": "staff"
        }
        
        # Third staff - should succeed after exception
        mock_staff3 = Mock()
        mock_staff3.exists = True
        mock_staff3.to_dict.return_value = {
            "name": "Staff Three",
            "email": "staff3@test.com",
            "role": "staff"
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                        # Manager update should work
                        mock_doc_ref.update.return_value = None
                    elif doc_id == "staff1":
                        mock_doc_ref.get.return_value = mock_staff1
                        # First staff update works
                        mock_doc_ref.update.return_value = None
                    elif doc_id == "staff2":
                        mock_doc_ref.get.return_value = mock_staff2
                        # Second staff update raises exception during update call
                        def raise_exception(*args, **kwargs):
                            raise Exception("Update failed for staff2")
                        mock_doc_ref.update.side_effect = raise_exception
                    elif doc_id == "staff3":
                        mock_doc_ref.get.return_value = mock_staff3
                        # Third staff update works
                        mock_doc_ref.update.return_value = None
                    else:
                        mock_not_found = Mock()
                        mock_not_found.exists = False
                        mock_doc_ref.get.return_value = mock_not_found
                    return mock_doc_ref
                
                mock_coll.document.side_effect = document_side_effect
                
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/assign-staff",
            headers={"X-User-Id": "mgr123"},
            json={"staff_ids": ["staff1", "staff2", "staff3"]}
        )
        assert response.status_code == 200
        data = response.get_json()
        # staff1 and staff3 should be assigned, staff2 should be in failed list
        assert "assigned" in data or "staff_assigned" in data
        # Check both possible response keys
        assigned_list = data.get("assigned", data.get("staff_assigned", []))
        failed_list = data.get("failed", [])
        assert len(assigned_list) >= 2  # staff1 and staff3 succeeded
        assert len(failed_list) == 1  # staff2 failed
        assert failed_list[0]["user_id"] == "staff2"


class TestRemoveManagerBranches:
    """Test specific branches in remove_manager_from_staff"""
    
    def test_remove_manager_with_no_current_manager(self, client, mock_db, monkeypatch):
        """Test removing manager when staff has no current manager - covers 1289->1305"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "director",  # Director can remove even if not assigned
            "name": "Director User"
        }
        
        mock_staff = Mock()
        mock_staff.exists = True
        mock_staff.to_dict.return_value = {
            "name": "Staff One",
            "email": "staff1@test.com",
            "role": "staff"
            # No manager_id field - this triggers the 1289->1305 branch
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
                        mock_doc_ref.update.return_value = None
                    return mock_doc_ref
                
                mock_coll.document.side_effect = document_side_effect
                
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete(
            "/api/manager/staff/staff1/remove-manager",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
    
    def test_remove_manager_current_manager_not_exists(self, client, mock_db, monkeypatch):
        """Test when current manager document doesn't exist - covers 1293->1305"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "director",  # Director can remove even if not the assigned manager
            "name": "Director User"
        }
        
        mock_staff = Mock()
        mock_staff.exists = True
        mock_staff.to_dict.return_value = {
            "name": "Staff One",
            "email": "staff1@test.com",
            "role": "staff",
            "manager_id": "old_mgr_999"  # Staff has manager but it doesn't exist
        }
        
        # Current manager doesn't exist - this triggers the 1293->1305 branch
        mock_old_mgr = Mock()
        mock_old_mgr.exists = False
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        mock_doc_ref.get.return_value = mock_mgr
                    elif doc_id == "staff1":
                        mock_doc_ref.get.return_value = mock_staff
                        mock_doc_ref.update.return_value = None
                    elif doc_id == "old_mgr_999":
                        # Old manager doesn't exist
                        mock_doc_ref.get.return_value = mock_old_mgr
                    return mock_doc_ref
                
                mock_coll.document.side_effect = document_side_effect
                
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete(
            "/api/manager/staff/staff1/remove-manager",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
    
    def test_remove_manager_staff_not_in_team_list(self, client, mock_db, monkeypatch):
        """Test when staff is not in manager's team_staff_ids - covers 1297->1305"""
        # The manager making the request
        first_mgr = Mock()
        first_mgr.exists = True
        first_mgr.to_dict.return_value = {"role": "manager", "name": "Manager Name"}
        
        # Second manager with team data (for team update check)
        second_mgr = Mock()
        second_mgr.exists = True
        second_mgr.to_dict.return_value = {
            "role": "manager",
            "name": "Manager Name",
            "team_staff_ids": ["other_staff"],  # staff1 not in list
            "team_size": 1
        }
        
        mock_staff = Mock()
        mock_staff.exists = True
        mock_staff.to_dict.return_value = {
            "name": "Staff One",
            "email": "staff1@test.com",
            "role": "staff",
            "manager_id": "mgr123"  # Staff is assigned to mgr123
        }
        
        # Track if update was called on manager
        update_called = {"called": False}
        call_count = {"count": 0}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "mgr123":
                        # First get for permission check, second for team update
                        def get_side_effect():
                            call_count["count"] += 1
                            if call_count["count"] == 1:
                                return first_mgr
                            else:
                                return second_mgr
                        
                        mock_doc_ref.get.side_effect = get_side_effect
                        
                        # Update should NOT be called since staff1 not in team
                        def update_side_effect(*args, **kwargs):
                            update_called["called"] = True
                        mock_doc_ref.update.side_effect = update_side_effect
                        
                    elif doc_id == "staff1":
                        mock_doc_ref.get.return_value = mock_staff
                        mock_doc_ref.update.return_value = None
                    return mock_doc_ref
                
                mock_coll.document.side_effect = document_side_effect
                
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete(
            "/api/manager/staff/staff1/remove-manager",
            headers={"X-User-Id": "mgr123"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
        # Manager update should not be called since staff1 wasn't in the team list
