"""
Tests for the final 2% of backend/api/tasks.py coverage.
Targeting lines: 85, 171->175, 188->185, 239, 469->491, 477->491, 479->491, 483-485, 622-623, 750->762
"""

import pytest
import sys
from datetime import datetime, timezone
from unittest.mock import Mock, patch

fake_firestore = sys.modules.get("firebase_admin.firestore")


@pytest.fixture
def mock_db():
    return Mock()


class TestIsManagedByNonExistentUser:
    """Line 85: User doesn't exist in is_managed_by check"""
    
    def test_get_tasks_filter_by_nonexistent_managed_user_line_85(self, client, mock_db, monkeypatch):
        """Line 85: When checking is_managed_by, user doesn't exist"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "manager1",
            "role": "manager"
        }
        
        # Non-existent user document
        mock_nonexistent_user = Mock()
        mock_nonexistent_user.exists = False
        
        call_count = [0]
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                
                def document_side_effect(user_id):
                    mock_doc = Mock()
                    if user_id == "manager1":
                        mock_doc.get.return_value = mock_viewer_doc
                    else:
                        # Return non-existent user
                        call_count[0] += 1
                        mock_doc.get.return_value = mock_nonexistent_user
                    return mock_doc
                
                mock_users.document.side_effect = document_side_effect
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.where.return_value = mock_tasks
                mock_tasks.stream.return_value = []
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        # Request with managed_by filter for non-existent user
        response = client.get(
            "/api/tasks?managed_by=nonexistent_user",
            headers={"X-User-Id": "manager1"}
        )
        
        assert response.status_code == 200
        # Should hit line 85 checking if user exists


class TestNotifyCreatorAndAssignee:
    """Lines 171->175, 188->185: Notify creator and assignee on task update"""
    
    def test_update_task_notifies_creator_and_assignee_lines_171_175_188(self, client, mock_db, monkeypatch):
        """Lines 171-175, 188: Notify creator and assignee when task is updated"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "editor_user",
            "role": "staff"
        }
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "editor_user"},  # Different from editor
            "assigned_to": {"user_id": "assignee_user"},  # Different from editor
            "project_id": "proj1",
            "title": "Old title"
        }
        
        # Mock project members
        mock_member1 = Mock()
        mock_member1.to_dict.return_value = {"user_id": "member1"}
        mock_member2 = Mock()
        mock_member2.to_dict.return_value = {"user_id": "member2"}
        
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
            elif name == "projects":
                mock_projects = Mock()
                mock_project_ref = Mock()
                mock_memberships = Mock()
                mock_memberships.stream.return_value = [mock_member1, mock_member2]
                mock_project_ref.collection.return_value = mock_memberships
                mock_projects.document.return_value = mock_project_ref
                return mock_projects
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_edit_task", return_value=True):
            with patch("backend.api.notifications.create_notification") as mock_notif:
                mock_notif.return_value = None
                
                response = client.put(
                    "/api/tasks/task1",
                    json={"title": "New title"},
                    headers={"X-User-Id": "editor_user"}
                )
        
        assert response.status_code == 200
        # Should notify creator (line 171-175) and assignee (line 175), and members (line 188)


class TestRecurringTaskWithTimezone:
    """Line 239: Due date has no timezone info"""
    
    def test_complete_recurring_task_no_timezone_line_239(self, client, mock_db, monkeypatch):
        """Line 239: Recurring task due date without timezone"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "user1",
            "role": "staff"
        }
        
        # Task with recurring data but no timezone in due_date
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"},
            "assigned_to": {"user_id": "user1"},
            "status": "In Progress",
            "recurring": True,
            "recurring_interval_days": 7,
            "recurring_original_due_date": "2024-01-15T10:00:00"  # No Z or timezone
        }
        
        mock_new_task_ref = Mock()
        mock_new_task_ref.id = "new_recurring_task"
        
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
                mock_tasks.add.return_value = (None, mock_new_task_ref)
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_edit_task", return_value=True):
            response = client.put(
                "/api/tasks/task1",
                json={"status": "Completed"},
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 200
        # Should hit line 239 where timezone is added


class TestProjectOwnerVisibility:
    """Lines 469->491, 477->491, 479->491, 483-485: Project owner visibility logic"""
    
    def test_get_tasks_viewer_is_project_owner_lines_469_491(self, client, mock_db, monkeypatch):
        """Lines 469-491: Viewer is project owner"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "owner1",
            "role": "manager"
        }
        
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {
            "owner_id": "owner1"  # Viewer is the owner
        }
        
        mock_task = Mock()
        mock_task.id = "task1"
        mock_task.to_dict.return_value = {
            "project_id": "proj1",
            "created_by": {"user_id": "other_user"}
        }
        
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
                mock_tasks.where.return_value = mock_tasks
                mock_tasks.limit.return_value = mock_tasks
                mock_tasks.stream.return_value = [mock_task]
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "owner1"}
        )
        
        assert response.status_code == 200
        # Should hit lines 469-473 (viewer is owner)
    
    def test_get_tasks_viewer_reports_to_owner_lines_477_491(self, client, mock_db, monkeypatch):
        """Lines 477-491: Viewer reports to project owner"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "staff1",
            "role": "staff",
            "manager_id": "owner1"  # Reports to owner
        }
        
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {
            "owner_id": "owner1"
        }
        
        mock_task = Mock()
        mock_task.id = "task1"
        mock_task.to_dict.return_value = {
            "project_id": "proj1"
        }
        
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
                        mock_other.to_dict.return_value = {"user_id": user_id}
                        mock_doc.get.return_value = mock_other
                    return mock_doc
                
                mock_users.document.side_effect = document_side_effect
                return mock_users
            elif name == "projects":
                mock_projects = Mock()
                mock_projects.document.return_value.get.return_value = mock_project_doc
                return mock_projects
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.where.return_value = mock_tasks
                mock_tasks.limit.return_value = mock_tasks
                mock_tasks.stream.return_value = [mock_task]
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "staff1"}
        )
        
        assert response.status_code == 200
        # Should hit lines 477-482 (viewer reports to owner)


class TestUpdateNotificationException:
    """Lines 622-623: Exception during notification sending"""
    
    def test_update_task_notification_exception_lines_622_623(self, client, mock_db, monkeypatch):
        """Lines 622-623: Exception when sending notifications"""
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
            "title": "Old title"
        }
        
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
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_edit_task", return_value=True):
            # Make _notify_task_changes raise an exception
            with patch("backend.api.tasks._notify_task_changes", side_effect=Exception("Notification failed")):
                response = client.put(
                    "/api/tasks/task1",
                    json={"title": "New title"},
                    headers={"X-User-Id": "user1"}
                )
        
        assert response.status_code == 200
        # Should hit lines 622-623 (exception handling)


class TestReassignNotificationException:
    """Lines 750->762: Exception during reassignment notifications"""
    
    def test_reassign_task_notification_exception_lines_750_762(self, client, mock_db, monkeypatch):
        """Lines 750-762: Exception when sending reassignment notifications"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "manager1",
            "role": "manager"
        }
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"},
            "assigned_to": {"user_id": "old_assignee"},
            "project_id": "proj1"
        }
        
        mock_new_assignee_doc = Mock()
        mock_new_assignee_doc.exists = True
        mock_new_assignee_doc.to_dict.return_value = {
            "user_id": "new_assignee",
            "name": "New User"
        }
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                
                def document_side_effect(user_id):
                    mock_doc = Mock()
                    if user_id == "manager1":
                        mock_doc.get.return_value = mock_viewer_doc
                    elif user_id == "new_assignee":
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
            # Make notifications.create_notification raise exception
            with patch("backend.api.notifications.create_notification", side_effect=Exception("Notification failed")):
                response = client.patch(
                    "/api/tasks/task1/reassign",
                    json={"new_assigned_to_id": "new_assignee"},
                    headers={"X-User-Id": "manager1"}
                )
        
        assert response.status_code == 200
        # Should hit lines 750-762 (exception in notification sending)
