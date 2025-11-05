"""
FINAL PUSH TO 100% COVERAGE
Targeting the exact remaining 18 lines with surgical precision
Lines: 85, 171-175, 182-189, 239, 369-370, 469-491, 554, 622-623, 750-762
"""
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

fake_firestore = sys.modules.get("firebase_admin.firestore")


@pytest.fixture
def mock_db():
    return Mock()


class TestLine85IsManagedByNullCheck:
    """Line 85: is_managed_by returns False when user_id or manager_id is None"""
    
    def test_get_task_triggers_is_managed_by_null_check_line_85(self, client, mock_db, monkeypatch):
        """Line 85: is_managed_by with None user_id returns False"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Create task with None manager_id in created_by to trigger line 84-85
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": None,  # This triggers the is_managed_by check with None
            "project": {"id": "proj1"},
            "title": "Task"
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        
        # Mock project with None owner
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {
            "owner_id": None,  # None owner
            "created_by": {"user_id": None}
        }
        
        # Mock viewer
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "role": "staff",
            "manager_id": None
        }
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            elif name == "projects":
                mock_projects = Mock()
                mock_projects.document.return_value.get.return_value = mock_project_doc
                return mock_projects
            elif name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks/task1",
            headers={"X-User-Id": "user1"}
        )
        
        # The is_managed_by check with None values returns False (line 85)
        assert response.status_code in [200, 404]


class TestLines171To175NotifyCreator:
    """Lines 171-175: Notify creator path in _notify_task_changes"""
    
    def test_update_task_notifies_creator_lines_171_175(self, client, mock_db, monkeypatch):
        """Lines 171-175: creator_id exists and gets added to recipients"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock task with creator
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "creator123"},  # Line 170-172
            "title": "Old Title"
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        # Mock editor (different from creator)
        mock_editor_doc = Mock()
        mock_editor_doc.exists = True
        mock_editor_doc.to_dict.return_value = {
            "name": "Editor",
            "email": "editor@example.com",
            "role": "staff"
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
                json={"title": "New Title"},
                headers={"X-User-Id": "editor1"}
            )
        
        assert response.status_code == 200


class TestLines182To189NotifyProjectMembers:
    """Lines 182-189: Notify project members via memberships query"""
    
    def test_update_task_notifies_project_members_lines_182_189(self, client, mock_db, monkeypatch):
        """Lines 182-189: Query memberships and add user_ids to recipients"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock task with project_id
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "creator1"},
            "project_id": "proj123",  # Line 180-181 triggers membership query
            "title": "Old Title"
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        # Mock editor
        mock_editor_doc = Mock()
        mock_editor_doc.exists = True
        mock_editor_doc.to_dict.return_value = {
            "name": "Editor",
            "email": "editor@example.com",
            "role": "manager"
        }
        
        # Mock memberships - Lines 182-189
        mock_member1 = Mock()
        mock_member1.to_dict.return_value = {"user_id": "member1"}  # Line 186-187
        mock_member2 = Mock()
        mock_member2.to_dict.return_value = {"user_id": "member2"}  # Line 188-189
        
        mock_memberships_query = Mock()
        mock_memberships_query.stream.return_value = [mock_member1, mock_member2]  # Line 185
        
        mock_memberships_collection = Mock()
        mock_memberships_collection.where.return_value = mock_memberships_query  # Line 182-184
        
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
                return mock_memberships_collection
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.notifications") as mock_notifications, \
             patch("backend.api.tasks._can_edit_task", return_value=True):
            mock_notifications.create_notification = Mock()
            
            response = client.put(
                "/api/tasks/task1",
                json={"title": "New Title"},
                headers={"X-User-Id": "editor1"}
            )
        
        assert response.status_code == 200
        # Verify memberships.where was called (line 182-184)
        assert mock_memberships_collection.where.called


class TestLine239RecurringTaskTimezone:
    """Line 239: Replace tzinfo when datetime has no timezone"""
    
    def test_recurring_task_due_date_no_timezone_line_239(self, client, mock_db, monkeypatch):
        """Line 239: due_dt.tzinfo is None, so replace with UTC"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock recurring task with due_date that parses to naive datetime
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"},
            "title": "Recurring Task",
            "status": "to_do",
            "recurring": {
                "enabled": True,
                "frequency": "weekly",
                "interval": 1
            },
            "due_date": "2025-11-12T00:00:00"  # No Z, no timezone info -> naive datetime
        }
        
        mock_task_ref = Mock()
        mock_task_ref.id = "task1"
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        # Mock editor
        mock_editor_doc = Mock()
        mock_editor_doc.exists = True
        mock_editor_doc.to_dict.return_value = {
            "name": "User 1",
            "email": "user1@example.com",
            "role": "staff"
        }
        
        # Mock new task creation
        mock_new_task_ref = Mock()
        mock_new_task_ref.id = "new_task_id"
        mock_new_task_ref.set.return_value = None
        
        task_refs = [mock_task_ref, mock_new_task_ref]
        task_ref_index = [0]
        
        def document_side_effect(task_id):
            idx = task_ref_index[0]
            task_ref_index[0] += 1
            return task_refs[idx] if idx < len(task_refs) else Mock()
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.side_effect = document_side_effect
                return mock_tasks
            elif name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_editor_doc
                return mock_users
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        # Mark task as done to trigger recurring task creation
        with patch("backend.api.tasks._can_edit_task", return_value=True):
            # Mock the final task doc returned after update with proper ID
            mock_updated_task = Mock()
            mock_updated_task.id = "task1"
            mock_updated_task.to_dict.return_value = {
                "created_by": {"user_id": "user1"},
                "title": "Recurring Task",
                "status": "done"
            }
            mock_task_ref.get.return_value = mock_updated_task
            
            response = client.put(
                "/api/tasks/task1",
                json={"status": "done"},
                headers={"X-User-Id": "user1"}
            )
        
        # Should succeed, line 239 adds timezone to naive datetime
        assert response.status_code == 200


class TestLines369To370NotificationException:
    """Lines 369-370: Exception handler when create_notification fails"""
    
    def test_create_task_notification_fails_lines_369_370(self, client, mock_db, monkeypatch):
        """Lines 369-370: Exception caught and printed when notification fails"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock creator
        mock_creator_doc = Mock()
        mock_creator_doc.exists = True
        mock_creator_doc.to_dict.return_value = {
            "user_id": "creator1",
            "name": "Creator",
            "email": "creator@example.com",
            "role": "manager"
        }
        
        # Mock project
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {"name": "Project"}
        
        # Mock assigned user
        mock_assigned_doc = Mock()
        mock_assigned_doc.exists = True
        mock_assigned_doc.to_dict.return_value = {
            "user_id": "user2",
            "name": "Assigned User",
            "email": "assigned@example.com"
        }
        
        # Mock membership
        mock_membership_doc = Mock()
        mock_membership_doc.exists = True
        
        # Mock new task
        mock_new_task_ref = Mock()
        mock_new_task_ref.id = "new_task_id"
        mock_new_task_ref.set.return_value = None
        
        def collection_side_effect(name):
            if name == "users":
                def user_doc_side_effect(user_id):
                    mock_user = Mock()
                    if user_id == "creator1":
                        mock_user.get.return_value = mock_creator_doc
                    else:
                        mock_user.get.return_value = mock_assigned_doc
                    return mock_user
                mock_users = Mock()
                mock_users.document.side_effect = user_doc_side_effect
                return mock_users
            elif name == "projects":
                mock_projects = Mock()
                mock_projects.document.return_value.get.return_value = mock_project_doc
                return mock_projects
            elif name == "memberships":
                mock_memberships = Mock()
                mock_memberships.document.return_value.get.return_value = mock_membership_doc
                return mock_memberships
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value = mock_new_task_ref
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        # Make notification raise exception (lines 369-370)
        with patch("backend.api.notifications") as mock_notifications, \
             patch("builtins.print") as mock_print:
            mock_notifications.create_notification.side_effect = Exception("Notification service down")
            
            response = client.post(
                "/api/tasks",
                json={
                    "title": "New Task",
                    "description": "Task Description With 10+ Characters",  # Add description >= 10 chars
                    "created_by_id": "creator1",
                    "project_id": "proj1",
                    "assigned_to_id": "user2"
                },
                headers={"X-User-Id": "creator1"}
            )
        
        # Should succeed despite notification failure
        assert response.status_code == 201, f"Got {response.status_code}: {response.get_json()}"
        # Verify exception was caught and printed (line 370)
        assert mock_print.called


class TestLine554GetTaskNoViewer:
    """Line 554: get_task returns 401 when no viewer_id"""
    
    def test_get_task_no_viewer_line_554(self, client):
        """Line 554: Missing viewer_id in get_task"""
        # No X-User-Id header, no ?viewer_id param
        response = client.get("/api/tasks/task1")
        
        assert response.status_code == 401
        data = response.get_json()
        assert "viewer_id required" in data["error"]


class TestLines622To623UpdateTaskNotificationException:
    """Lines 622-623: Exception handler when update notifications fail"""
    
    def test_update_task_notification_fails_lines_622_623(self, client, mock_db, monkeypatch):
        """Lines 622-623: Exception caught when _notify_task_changes fails"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock task
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "creator1"},
            "title": "Old Title"
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        # Mock editor
        mock_editor_doc = Mock()
        mock_editor_doc.exists = True
        mock_editor_doc.to_dict.return_value = {
            "name": "Editor",
            "email": "editor@example.com",
            "role": "staff"
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
        
        # Make notification module raise exception (lines 622-623)
        with patch("backend.api.notifications") as mock_notifications, \
             patch("builtins.print") as mock_print, \
             patch("backend.api.tasks._can_edit_task", return_value=True):
            mock_notifications.create_notification.side_effect = Exception("Notification failed")
            
            response = client.put(
                "/api/tasks/task1",
                json={"title": "New Title"},
                headers={"X-User-Id": "editor1"}
            )
        
        # Should succeed despite notification failure
        assert response.status_code == 200
        # Verify exception was caught and printed (line 623)
        assert mock_print.called


class TestLines750To762ReassignNotificationException:
    """Lines 750-762: Reassignment notification to previous assignee + exception handler"""
    
    def test_reassign_task_notifies_previous_assignee_lines_750_762(self, client, mock_db, monkeypatch):
        """Lines 750-762: Notify previous assignee when reassigning, handle exceptions"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock viewer (manager)
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "manager"}
        
        # Mock task currently assigned to user2
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "assigned_to": {"user_id": "user2"},  # Current assignee (line 750)
            "title": "Task Title"
        }
        
        mock_task_ref = Mock()
        mock_task_ref.id = "task1"
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        # Mock new assignee
        mock_new_assignee_doc = Mock()
        mock_new_assignee_doc.exists = True
        mock_new_assignee_doc.to_dict.return_value = {
            "name": "New Assignee",
            "email": "new@example.com"
        }
        
        def collection_side_effect(name):
            if name == "users":
                def user_doc_side_effect(user_id):
                    mock_user = Mock()
                    if user_id == "manager1":
                        mock_user.get.return_value = mock_viewer_doc
                    else:
                        mock_user.get.return_value = mock_new_assignee_doc
                    return mock_user
                mock_users = Mock()
                mock_users.document.side_effect = user_doc_side_effect
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        # Make notification raise exception (lines 759-760)
        with patch("backend.api.notifications") as mock_notifications, \
             patch("builtins.print") as mock_print:
            mock_notifications.create_notification.side_effect = Exception("Notification failed")
            
            response = client.patch(
                "/api/tasks/task1/reassign",
                json={"new_assigned_to_id": "user3"},  # Different from user2
                headers={"X-User-Id": "manager1"}
            )
        
        # Should succeed despite notification failure (line 762)
        assert response.status_code == 200
        # Verify exception was caught and printed (line 760)
        assert mock_print.called


class TestLines469To491ComplexProjectFiltering:
    """Lines 469-491: Complex project owner/manager filtering logic"""
    
    def test_list_tasks_project_owner_check_lines_469_491(self, client, mock_db, monkeypatch):
        """Lines 469-491: Project has owner_id, viewer is owner"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock viewer (staff role)
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "role": "staff",
            "manager_id": "other_manager"
        }
        
        # Mock project with owner_id matching viewer (line 469-473)
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {
            "owner_id": "viewer1",  # Line 467, 469
            "name": "Project 1"
        }
        
        # Mock tasks query
        mock_tasks_query = Mock()
        mock_tasks_query.limit.return_value = Mock(stream=Mock(return_value=[]))
        
        mock_tasks_where = Mock()
        mock_tasks_where.where.return_value = mock_tasks_query
        
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
                return mock_tasks_where
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "viewer1"}  # Viewer IS owner (line 471)
        )
        
        assert response.status_code == 200
    
    def test_list_tasks_viewer_reports_to_owner_lines_477_482(self, client, mock_db, monkeypatch):
        """Lines 477-482: Viewer's manager_id matches project owner_id"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock viewer doc (line 476-478)
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True  # Line 477
        mock_viewer_doc.to_dict.return_value = {
            "role": "staff",
            "manager_id": "owner1"  # Line 479 - viewer reports to owner
        }
        
        # Mock project with owner
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {
            "owner_id": "owner1",  # Matches viewer's manager_id
            "name": "Project 1"
        }
        
        # Mock tasks query
        mock_tasks_query = Mock()
        mock_tasks_query.limit.return_value = Mock(stream=Mock(return_value=[]))
        
        mock_tasks_where = Mock()
        mock_tasks_where.where.return_value = mock_tasks_query
        
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
                return mock_tasks_where
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "viewer1"}
        )
        
        assert response.status_code == 200
    
    def test_list_tasks_owner_check_exception_lines_483_485(self, client, mock_db, monkeypatch):
        """Lines 483-485: Exception during owner check, continues gracefully"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock viewer
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "staff"}
        
        # Mock project that raises exception during owner check
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.side_effect = Exception("Database error")  # Line 483
        
        # Mock tasks query for fallback
        mock_tasks_query = Mock()
        mock_tasks_query.limit.return_value = Mock(stream=Mock(return_value=[]))
        
        mock_tasks_where = Mock()
        mock_tasks_where.where.return_value = mock_tasks_query
        
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
                return mock_tasks_where
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "viewer1"}
        )
        
        # Should continue despite exception (line 485: pass)
        assert response.status_code == 200
