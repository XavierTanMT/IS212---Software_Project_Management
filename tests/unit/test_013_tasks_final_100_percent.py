"""
Final coverage push to 100%
Covering: 85, 171->175, 188->185, 469->491, 477->491, 479->491, 483-485, 622-623, 750->762
"""
import pytest
import sys
from unittest.mock import Mock, patch

fake_firestore = sys.modules.get("firebase_admin.firestore")


@pytest.fixture
def mock_db():
    return Mock()


class TestLine85IsManagerException:
    """Line 85: Exception in is_managed_by user lookup"""
    
    def test_is_managed_by_user_not_exists_line_85(self, client, mock_db, monkeypatch):
        """Line 85: User document doesn't exist in is_managed_by check"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock task with project
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "creator1"},
            "project_id": "proj1",
            "title": "Task"
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        
        # Mock viewer (manager trying to check if user reports to them)
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "role": "manager",
            "name": "Manager"
        }
        
        # Mock creator user that doesn't exist (triggers line 85)
        mock_creator_doc = Mock()
        mock_creator_doc.exists = False  # This triggers line 85
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            elif name == "users":
                def user_doc_side_effect(user_id):
                    if user_id == "viewer1":
                        mock_user = Mock()
                        mock_user.get.return_value = mock_viewer_doc
                        return mock_user
                    elif user_id == "creator1":
                        mock_user = Mock()
                        mock_user.get.return_value = mock_creator_doc  # doesn't exist
                        return mock_user
                    return Mock()
                mock_users = Mock()
                mock_users.document.side_effect = user_doc_side_effect
                return mock_users
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        # Manager tries to view task - creator doesn't exist so is_managed_by returns False
        response = client.get(
            "/api/tasks/task1",
            headers={"X-User-Id": "viewer1"}
        )
        
        # Should return 200 (manager can view tasks even if creator check fails)
        assert response.status_code == 200


class TestLines171to175CreatorNotification:
    """Lines 171->175: Creator gets added to notification recipients"""
    
    def test_creator_notification_with_creator_id_lines_171_175(self, client, mock_db, monkeypatch):
        """Lines 171-175: creator_id exists and is added to recipients"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock task WITH creator_id
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "creator123"},  # Has creator
            "title": "Task with creator"
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        mock_editor_doc = Mock()
        mock_editor_doc.exists = True
        mock_editor_doc.to_dict.return_value = {
            "role": "staff",
            "name": "Editor"
        }
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            elif name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_editor_doc
                return mock_users
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.notifications") as mock_notifications, \
             patch("backend.api.tasks._can_edit_task", return_value=True):
            mock_notifications.create_notification = Mock()
            
            response = client.put(
                "/api/tasks/task1",
                json={"title": "Updated title"},
                headers={"X-User-Id": "editor1"}
            )
        
        assert response.status_code == 200
        # Verify notification was attempted (creator_id was in recipients)
        assert mock_notifications.create_notification.called


class TestLine188NoUserIdInMembership:
    """Line 188->185: Membership has no user_id"""
    
    def test_membership_without_user_id_line_188(self, client, mock_db, monkeypatch):
        """Line 188: Membership document missing user_id field"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock task with project_id
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "creator1"},
            "project_id": "proj1",  # Has project
            "title": "Task"
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        mock_editor_doc = Mock()
        mock_editor_doc.exists = True
        mock_editor_doc.to_dict.return_value = {
            "role": "staff",
            "name": "Editor"
        }
        
        # Mock membership WITHOUT user_id (triggers line 188)
        mock_membership = Mock()
        mock_membership.to_dict.return_value = {
            "project_id": "proj1"
            # NO user_id field - this triggers line 188->185
        }
        
        mock_memberships_query = Mock()
        mock_memberships_query.stream.return_value = [mock_membership]
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            elif name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_editor_doc
                return mock_users
            elif name == "memberships":
                mock_memberships = Mock()
                mock_memberships.where.return_value = mock_memberships_query
                return mock_memberships
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.notifications") as mock_notifications, \
             patch("backend.api.tasks._can_edit_task", return_value=True):
            mock_notifications.create_notification = Mock()
            
            response = client.put(
                "/api/tasks/task1",
                json={"status": "done"},
                headers={"X-User-Id": "editor1"}
            )
        
        assert response.status_code == 200


class TestLines469to491ProjectOwnerFiltering:
    """Lines 469->491, 477->491, 479->491, 483-485: Complex project owner filtering"""
    
    def test_viewer_is_project_owner_line_469_to_473(self, client, mock_db, monkeypatch):
        """Lines 469-473: Viewer is the project owner"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock viewer (staff)
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "staff"}
        
        # Mock project where viewer IS the owner
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {
            "owner_id": "viewer1",  # Viewer IS the owner
            "name": "My Project"
        }
        
        # Mock task in that project
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "id": "task1",
            "title": "Task",
            "project_id": "proj1"
        }
        
        mock_tasks_query = Mock()
        mock_tasks_query.limit.return_value.stream.return_value = [mock_task]
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            elif name == "projects":
                mock_projects = Mock()
                mock_projects.document.return_value.get.return_value = mock_project_doc
                return mock_projects
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.where.return_value = mock_tasks_query
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        # Filter by project where viewer is owner
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "viewer1"}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        # Response is a list, not a dict with "tasks" key
        assert isinstance(data, list)
    
    def test_viewer_reports_to_owner_lines_477_to_482(self, client, mock_db, monkeypatch):
        """Lines 477-482: Viewer reports to project owner"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock viewer (staff) who reports to owner
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "role": "staff",
            "manager_id": "owner1"  # Reports to owner
        }
        
        # Mock project with different owner
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {
            "owner_id": "owner1",  # Owner is viewer's manager
            "name": "Project"
        }
        
        # Mock task
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "id": "task1",
            "title": "Task",
            "project_id": "proj1"
        }
        
        mock_tasks_query = Mock()
        mock_tasks_query.limit.return_value.stream.return_value = [mock_task]
        
        # Track which user document is requested
        def user_doc_side_effect(user_id):
            mock_user = Mock()
            if user_id == "viewer1":
                mock_user.get.return_value = mock_viewer_doc
            else:
                mock_user.get.return_value = Mock(exists=False)
            return mock_user
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.side_effect = user_doc_side_effect
                return mock_users
            elif name == "projects":
                mock_projects = Mock()
                mock_projects.document.return_value.get.return_value = mock_project_doc
                return mock_projects
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.where.return_value = mock_tasks_query
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "viewer1"}
        )
        
        assert response.status_code == 200
    
    def test_owner_check_exception_lines_483_485(self, client, mock_db, monkeypatch):
        """Lines 483-485: Exception during owner check"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock viewer
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "staff"}
        
        # Mock project that throws exception
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.side_effect = Exception("Database error")
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            elif name == "projects":
                mock_projects = Mock()
                mock_projects.document.return_value.get.return_value = mock_project_doc
                return mock_projects
            elif name == "tasks":
                # Return empty result
                mock_tasks_query = Mock()
                mock_tasks_query.limit.return_value.stream.return_value = []
                mock_tasks = Mock()
                mock_tasks.where.return_value = mock_tasks_query
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        # Exception is caught and continues with default rules
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "viewer1"}
        )
        
        # Should succeed despite exception
        assert response.status_code == 200


class TestLines622to623NotifyException:
    """Lines 622-623: Exception in _notify_task_changes"""
    
    def test_notify_task_changes_exception_lines_622_623(self, client, mock_db, monkeypatch):
        """Lines 622-623: Exception when calling _notify_task_changes"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "creator1"},
            "title": "Task"
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        mock_editor_doc = Mock()
        mock_editor_doc.exists = True
        mock_editor_doc.to_dict.return_value = {
            "role": "staff",
            "name": "Editor"
        }
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            elif name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_editor_doc
                return mock_users
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        # Make notifications module raise exception
        with patch("backend.api.notifications") as mock_notifications, \
             patch("backend.api.tasks._can_edit_task", return_value=True), \
             patch("builtins.print") as mock_print:
            mock_notifications.create_notification.side_effect = Exception("Notification error")
            
            response = client.put(
                "/api/tasks/task1",
                json={"title": "Updated"},
                headers={"X-User-Id": "editor1"}
            )
        
        # Should succeed despite notification failure
        assert response.status_code == 200
        # Verify exception was caught and printed
        mock_print.assert_called()


class TestLines750to762ReassignmentNotification:
    """Lines 750->762: Previous assignee notification exception"""
    
    def test_reassignment_notification_exception_lines_750_762(self, client, mock_db, monkeypatch):
        """Lines 750-762: Exception when notifying previous assignee"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock task with current assignee
        mock_current_task = Mock()
        mock_current_task.exists = True
        mock_current_task.id = "task1"
        mock_current_task.to_dict.return_value = {
            "created_by": {"user_id": "creator1"},
            "assigned_to": {"user_id": "old_assignee"},  # Currently assigned
            "title": "Task"
        }
        
        # Mock updated task (after reassignment)
        mock_updated_task = Mock()
        mock_updated_task.id = "task1"
        mock_updated_task.to_dict.return_value = {
            "created_by": {"user_id": "creator1"},
            "assigned_to": {"user_id": "new_assignee"},  # Reassigned
            "title": "Task"
        }
        
        mock_task_ref = Mock()
        # First call returns current, second returns updated
        mock_task_ref.get.side_effect = [mock_current_task, mock_updated_task]
        mock_task_ref.update.return_value = None
        
        mock_editor_doc = Mock()
        mock_editor_doc.exists = True
        mock_editor_doc.to_dict.return_value = {
            "role": "manager",
            "name": "Manager"
        }
        
        # Mock new assignee
        mock_new_assignee_doc = Mock()
        mock_new_assignee_doc.exists = True
        mock_new_assignee_doc.to_dict.return_value = {
            "user_id": "new_assignee",
            "name": "New Assignee",
            "email": "new@example.com"
        }
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            elif name == "users":
                def user_doc_side_effect(user_id):
                    mock_user = Mock()
                    if user_id == "editor1":
                        mock_user.get.return_value = mock_editor_doc
                    elif user_id == "new_assignee":
                        mock_user.get.return_value = mock_new_assignee_doc
                    else:
                        mock_user.get.return_value = Mock(exists=False)
                    return mock_user
                mock_users = Mock()
                mock_users.document.side_effect = user_doc_side_effect
                return mock_users
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        # Make notification raise exception for reassignment notification
        with patch("backend.api.notifications") as mock_notifications, \
             patch("backend.api.tasks._can_edit_task", return_value=True), \
             patch("builtins.print") as mock_print:
            mock_notifications.create_notification.side_effect = Exception("Notification failed")
            
            response = client.patch(
                "/api/tasks/task1/reassign",
                json={"new_assigned_to_id": "new_assignee"},
                headers={"X-User-Id": "editor1"}
            )
        
        # Should succeed despite notification failure
        assert response.status_code == 200
        # Verify exception was caught and printed (line 762)
        assert any("Failed to create reassignment notifications" in str(call) for call in mock_print.call_args_list)
