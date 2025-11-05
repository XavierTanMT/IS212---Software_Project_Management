"""
Super targeted tests for exact missing branch paths
Lines: 85, 188->185, 469->491, 477->491, 479->491, 483-485, 750->762
"""

import pytest
import sys
from unittest.mock import Mock, patch

fake_firestore = sys.modules.get("firebase_admin.firestore")


@pytest.fixture
def mock_db():
    return Mock()


class TestLine85NonExistentUser:
    """Line 85: User document doesn't exist in is_managed_by check"""
    
    def test_get_single_task_creator_not_exists_line_85(self, client, mock_db, monkeypatch):
        """Line 85: Manager tries to view task where creator user doesn't exist"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Manager viewing the task
        mock_manager_doc = Mock()
        mock_manager_doc.exists = True
        mock_manager_doc.to_dict.return_value = {
            "user_id": "manager1",
            "role": "manager"
        }
        
        # Task where creator doesn't exist as a user
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "nonexistent_creator"},  # This user doesn't exist
            "assigned_to": {"user_id": "nonexistent_assignee"},  # This user also doesn't exist
            "title": "Test task",
            "project_id": "proj1"  # Add project_id to avoid other checks
        }
        
        # Mock non-existent user documents
        mock_nonexistent_user = Mock()
        mock_nonexistent_user.exists = False  # Doesn't exist - triggers line 85
        
        # Mock that membership check fails
        mock_no_membership = Mock()
        mock_no_membership.exists = False
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                
                def document_side_effect(user_id):
                    mock_doc = Mock()
                    if user_id == "manager1":
                        mock_doc.get.return_value = mock_manager_doc
                    elif user_id in ["nonexistent_creator", "nonexistent_assignee"]:
                        # These users don't exist - will hit line 85 in is_managed_by
                        mock_doc.get.return_value = mock_nonexistent_user
                    else:
                        mock_other = Mock()
                        mock_other.exists = True
                        mock_other.to_dict.return_value = {"user_id": user_id}
                        mock_doc.get.return_value = mock_other
                    return mock_doc
                
                mock_users.document.side_effect = document_side_effect
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value.get.return_value = mock_task_doc
                return mock_tasks
            elif name == "memberships":
                # Manager is NOT a member of the project
                mock_memberships = Mock()
                mock_memberships.document.return_value.get.return_value = mock_no_membership
                return mock_memberships
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks/task1",
            headers={"X-User-Id": "manager1"}
        )
        
        # Manager can't view because creator/assignee don't exist (is_managed_by returns False at line 85)
        # Should return 404
        assert response.status_code == 404


class TestProjectOwnerBranches:
    """Lines 469-491: Project owner visibility branches"""
    
    def test_get_tasks_project_filter_no_owner_id_line_469(self, client, mock_db, monkeypatch):
        """Line 469->491: Project exists but has no owner_id field"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "staff1",
            "role": "staff"
        }
        
        # Project with no owner_id
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {}  # NO owner_id field
        
        # No membership for viewer
        mock_no_membership = Mock()
        mock_no_membership.exists = False
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            elif name == "projects":
                mock_projects = Mock()
                mock_projects.document.return_value.get.return_value = mock_project_doc
                return mock_projects
            elif name == "memberships":
                # No membership for viewer - this triggers the owner check path
                mock_memberships = Mock()
                mock_memberships.document.return_value.get.return_value = mock_no_membership
                return mock_memberships
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.where.return_value = mock_tasks
                mock_tasks.stream.return_value = []
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "staff1"}
        )
        
        assert response.status_code == 200
        # Should skip owner checks (line 469, if owner_id is falsy, skip to 491)
    
    def test_get_tasks_project_viewer_doc_not_exists_line_477(self, client, mock_db, monkeypatch):
        """Line 477->491: Viewer != owner and viewer's doc doesn't exist"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # First call to get viewer doc for role check - exists
        mock_viewer_doc_for_role = Mock()
        mock_viewer_doc_for_role.exists = True
        mock_viewer_doc_for_role.to_dict.return_value = {
            "user_id": "staff1",
            "role": "staff"
        }
        
        # Second call to get viewer doc for manager check - doesn't exist
        mock_viewer_doc_for_manager = Mock()
        mock_viewer_doc_for_manager.exists = False
        
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {
            "owner_id": "owner1"  # Different from viewer
        }
        
        # No membership
        mock_no_membership = Mock()
        mock_no_membership.exists = False
        
        call_count = [0]
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                
                def document_side_effect(user_id):
                    mock_doc = Mock()
                    if user_id == "staff1":
                        # First call returns exists, second call returns not exists
                        call_count[0] += 1
                        if call_count[0] <= 2:  # Role check calls
                            mock_doc.get.return_value = mock_viewer_doc_for_role
                        else:  # Manager check call - doesn't exist
                            mock_doc.get.return_value = mock_viewer_doc_for_manager
                    else:
                        mock_other = Mock()
                        mock_other.exists = True
                        mock_other.to_dict.return_value = {"user_id": user_id, "role": "staff"}
                        mock_doc.get.return_value = mock_other
                    return mock_doc
                
                mock_users.document.side_effect = document_side_effect
                return mock_users
            elif name == "projects":
                mock_projects = Mock()
                mock_projects.document.return_value.get.return_value = mock_project_doc
                return mock_projects
            elif name == "memberships":
                mock_memberships = Mock()
                mock_memberships.document.return_value.get.return_value = mock_no_membership
                return mock_memberships
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.where.return_value = mock_tasks
                mock_tasks.stream.return_value = []
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "staff1"}
        )
        
        assert response.status_code == 200
        # Skips manager check because vdoc.exists is False (line 477->491)
    
    def test_get_tasks_project_viewer_reports_to_different_manager_line_479(self, client, mock_db, monkeypatch):
        """Line 479->491: Viewer reports to manager who is NOT the project owner"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "staff1",
            "role": "staff",
            "manager_id": "manager2"  # Reports to manager2, not owner1
        }
        
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {
            "owner_id": "owner1"  # Different from viewer's manager
        }
        
        # No membership
        mock_no_membership = Mock()
        mock_no_membership.exists = False
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                
                def document_side_effect(user_id):
                    mock_doc = Mock()
                    if user_id == "staff1":
                        mock_doc.get.return_value = mock_viewer_doc
                    else:
                        mock_other = Mock()
                        mock_other.exists = True
                        mock_other.to_dict.return_value = {"user_id": user_id, "role": "staff"}
                        mock_doc.get.return_value = mock_other
                    return mock_doc
                
                mock_users.document.side_effect = document_side_effect
                return mock_users
            elif name == "projects":
                mock_projects = Mock()
                mock_projects.document.return_value.get.return_value = mock_project_doc
                return mock_projects
            elif name == "memberships":
                mock_memberships = Mock()
                mock_memberships.document.return_value.get.return_value = mock_no_membership
                return mock_memberships
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.where.return_value = mock_tasks
                mock_tasks.stream.return_value = []
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "staff1"}
        )
        
        assert response.status_code == 200
        # Skips adding project tasks because manager_id != owner_id (line 479->491)


class TestNotificationBranches:
    """Lines 188->185, 750->762: Notification edge cases"""
    
    def test_update_task_member_has_no_user_id_line_188(self, client, mock_db, monkeypatch):
        """Line 188->185: Membership document has no user_id field"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "user1",
            "role": "staff"
        }
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"},
            "assigned_to": {"user_id": "user1"},
            "project_id": "proj1",
            "title": "Old title"
        }
        
        # Membership with NO user_id
        mock_member_no_uid = Mock()
        mock_member_no_uid.to_dict.return_value = {"project_id": "proj1"}  # No user_id field
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_task_ref = Mock()
                mock_task_ref.get.return_value = mock_task_doc
                mock_task_ref.update.return_value = None
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            elif name == "memberships":
                mock_memberships = Mock()
                mock_memberships.where.return_value = mock_memberships
                mock_memberships.stream.return_value = [mock_member_no_uid]
                return mock_memberships
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_edit_task", return_value=True):
            response = client.put(
                "/api/tasks/task1",
                json={"title": "New title"},
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 200
        # Skips adding member to recipients because uid is falsy (line 188->185)
    
    def test_reassign_notification_fails_for_previous_assignee_line_750(self, client, mock_db, monkeypatch):
        """Line 750->762: No previous assignee OR same assignee (skip notification to old assignee)"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "manager1",
            "role": "manager"
        }
        
        # Task with NO assigned_to (no previous assignee)
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "creator1"},
            # NO assigned_to field - current_assigned_to_id will be None
            "project_id": "proj1"
        }
        
        mock_new_assignee_doc = Mock()
        mock_new_assignee_doc.exists = True
        mock_new_assignee_doc.to_dict.return_value = {
            "user_id": "new_user",
            "name": "New User"
        }
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                
                def document_side_effect(user_id):
                    mock_doc = Mock()
                    if user_id == "manager1":
                        mock_doc.get.return_value = mock_viewer_doc
                    elif user_id == "new_user":
                        mock_doc.get.return_value = mock_new_assignee_doc
                    else:
                        mock_other = Mock()
                        mock_other.exists = True
                        mock_other.to_dict.return_value = {"user_id": user_id}
                        mock_doc.get.return_value = mock_other
                    return mock_doc
                
                mock_users.document.side_effect = document_side_effect
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_task_ref = Mock()
                mock_task_ref.get.return_value = mock_task_doc
                mock_task_ref.update.return_value = None
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_edit_task", return_value=True):
            with patch("backend.api.notifications.create_notification") as mock_notif:
                response = client.patch(
                    "/api/tasks/task1/reassign",
                    json={"new_assigned_to_id": "new_user"},
                    headers={"X-User-Id": "manager1"}
                )
        
        assert response.status_code == 200
        # Should skip notifying previous assignee (line 750->762, current_assigned_to_id is None)


class TestExceptionInOwnerCheck:
    """Lines 483-485: Exception handling in owner check"""
    
    def test_get_tasks_exception_in_project_owner_check_line_483(self, client, mock_db, monkeypatch):
        """Lines 483-485: Exception during project owner visibility check"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "staff1",
            "role": "staff"
        }
        
        # Make to_dict() raise exception
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.side_effect = Exception("Firestore error")
        
        # No membership
        mock_no_membership = Mock()
        mock_no_membership.exists = False
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            elif name == "projects":
                mock_projects = Mock()
                mock_projects.document.return_value.get.return_value = mock_project_doc
                return mock_projects
            elif name == "memberships":
                mock_memberships = Mock()
                mock_memberships.document.return_value.get.return_value = mock_no_membership
                return mock_memberships
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.where.return_value = mock_tasks
                mock_tasks.stream.return_value = []
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "staff1"}
        )
        
        assert response.status_code == 200
        # Should catch exception (lines 483-485) and continue with default visibility rules
