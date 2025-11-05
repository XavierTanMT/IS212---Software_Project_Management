"""
Comprehensive branch coverage tests for backend/api/tasks.py
Targets missing branches to achieve 100% coverage.
"""
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Get fake_firestore from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")

from backend.api import tasks as tasks_module


@pytest.fixture
def mock_db():
    """Create a mock Firestore database."""
    return Mock()


class TestCanViewTaskDoc:
    """Test _can_view_task_doc helper function branches"""
    
    def test_no_viewer_returns_false(self, mock_db):
        """Lines 65-66: No viewer returns False"""
        from backend.api.tasks import _can_view_task_doc
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {"title": "Test"}
        
        with patch("backend.api.tasks._viewer_id", return_value=""):
            result = _can_view_task_doc(mock_db, mock_task)
            assert result is False
    
    def test_viewer_is_creator(self, mock_db):
        """Branch 73-74: Viewer is creator"""
        from backend.api.tasks import _can_view_task_doc
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "user123"}
        }
        
        with patch("backend.api.tasks._viewer_id", return_value="user123"):
            result = _can_view_task_doc(mock_db, mock_task)
            assert result is True
    
    def test_viewer_is_assignee(self, mock_db):
        """Branch 73-74: Viewer is assignee"""
        from backend.api.tasks import _can_view_task_doc
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "creator"},
            "assigned_to": {"user_id": "user456"}
        }
        
        with patch("backend.api.tasks._viewer_id", return_value="user456"):
            result = _can_view_task_doc(mock_db, mock_task)
            assert result is True
    
    def test_viewer_is_project_member(self, mock_db):
        """Lines 85: Viewer is project member"""
        from backend.api.tasks import _can_view_task_doc
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "other"},
            "assigned_to": {"user_id": "other2"},
            "project_id": "proj123"
        }
        
        # Mock _require_membership to return True
        with patch("backend.api.tasks._viewer_id", return_value="viewer"), \
             patch("backend.api.tasks._require_membership", return_value=True):
            result = _can_view_task_doc(mock_db, mock_task)
            assert result is True
    
    def test_viewer_role_admin(self, mock_db):
        """Branch 92->97: Viewer role is admin"""
        from backend.api.tasks import _can_view_task_doc
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "other"}
        }
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "admin"}
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_viewer_doc
        
        with patch("backend.api.tasks._viewer_id", return_value="admin_user"):
            result = _can_view_task_doc(mock_db, mock_task)
            assert result is True
    
    def test_viewer_role_exception_defaults_to_staff(self, mock_db):
        """Lines 94-95: Exception when fetching viewer doc defaults to staff role"""
        from backend.api.tasks import _can_view_task_doc
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "other"}
        }
        
        # Mock exception when getting viewer doc
        mock_db.collection.return_value.document.return_value.get.side_effect = Exception("DB error")
        
        with patch("backend.api.tasks._viewer_id", return_value="viewer"):
            result = _can_view_task_doc(mock_db, mock_task)
            # Should return False since defaulting to staff and not creator/assignee
            assert result is False
    
    def test_manager_role_manages_creator(self, mock_db):
        """Branch 137-138: Manager manages the creator"""
        from backend.api.tasks import _can_view_task_doc
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "staff_user"},
            "assigned_to": {"user_id": "other"}
        }
        
        # Mock viewer as manager
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "manager"}
        
        # Mock creator doc with manager_id pointing to viewer
        mock_creator_doc = Mock()
        mock_creator_doc.exists = True
        mock_creator_doc.to_dict.return_value = {"manager_id": "manager_user"}
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                def document_side_effect(user_id):
                    mock_doc_ref = Mock()
                    if user_id == "manager_user":
                        mock_doc_ref.get.return_value = mock_viewer_doc
                    elif user_id == "staff_user":
                        mock_doc_ref.get.return_value = mock_creator_doc
                    return mock_doc_ref
                mock_users.document.side_effect = document_side_effect
                return mock_users
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._viewer_id", return_value="manager_user"):
            result = _can_view_task_doc(mock_db, mock_task)
            assert result is True
    
    def test_manager_role_manages_assignee(self, mock_db):
        """Branch 137-138: Manager manages the assignee"""
        from backend.api.tasks import _can_view_task_doc
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "other"},
            "assigned_to": {"user_id": "staff_user"}
        }
        
        # Mock viewer as manager
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "manager"}
        
        # Mock assignee doc with manager_id pointing to viewer
        mock_assignee_doc = Mock()
        mock_assignee_doc.exists = True
        mock_assignee_doc.to_dict.return_value = {"manager_id": "manager_user"}
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                def document_side_effect(user_id):
                    mock_doc_ref = Mock()
                    if user_id == "manager_user":
                        mock_doc_ref.get.return_value = mock_viewer_doc
                    elif user_id == "staff_user":
                        mock_doc_ref.get.return_value = mock_assignee_doc
                    return mock_doc_ref
                mock_users.document.side_effect = document_side_effect
                return mock_users
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._viewer_id", return_value="manager_user"):
            result = _can_view_task_doc(mock_db, mock_task)
            assert result is True


class TestNotifyTaskChanges:
    """Test _notify_task_changes helper function branches"""
    
    def test_no_changes_returns_early(self, mock_db):
        """Lines 157-163: No changes in updates returns early"""
        from backend.api.tasks import _notify_task_changes
        
        old_data = {"title": "Task 1", "status": "To Do"}
        updates = {"title": "Task 1"}  # Same as old
        
        mock_notifications = Mock()
        
        # Should return early without creating notifications
        _notify_task_changes(mock_db, "task1", old_data, updates, "editor1", mock_notifications)
        
        # Verify no notifications were created
        mock_notifications.create_notification.assert_not_called()
    
    def test_editor_is_creator(self, mock_db):
        """Branch 171->175: Editor is the creator"""
        from backend.api.tasks import _notify_task_changes
        
        old_data = {
            "title": "Old Title",
            "created_by": {"user_id": "editor1", "name": "Editor One"}
        }
        updates = {"title": "New Title"}
        
        mock_notifications = Mock()
        
        _notify_task_changes(mock_db, "task1", old_data, updates, "editor1", mock_notifications)
        
        # Should use creator name from old_data
        assert mock_notifications.create_notification.called
    
    def test_editor_is_assignee(self, mock_db):
        """Branch 171->175: Editor is the assignee"""
        from backend.api.tasks import _notify_task_changes
        
        old_data = {
            "title": "Old Title",
            "created_by": {"user_id": "creator1"},
            "assigned_to": {"user_id": "editor1", "name": "Assignee One"}
        }
        updates = {"title": "New Title"}
        
        mock_notifications = Mock()
        
        _notify_task_changes(mock_db, "task1", old_data, updates, "editor1", mock_notifications)
        
        # Should use assignee name from old_data
        assert mock_notifications.create_notification.called
    
    def test_editor_db_lookup_success(self, mock_db):
        """Lines 182-189: Editor name from DB lookup"""
        from backend.api.tasks import _notify_task_changes
        
        old_data = {
            "title": "Old Title",
            "created_by": {"user_id": "creator1"}
        }
        updates = {"title": "New Title"}
        
        mock_editor_doc = Mock()
        mock_editor_doc.exists = True
        mock_editor_doc.to_dict.return_value = {"name": "Editor From DB"}
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_editor_doc
        
        mock_notifications = Mock()
        
        _notify_task_changes(mock_db, "task1", old_data, updates, "editor2", mock_notifications)
        
        assert mock_notifications.create_notification.called
    
    def test_editor_db_lookup_exception(self, mock_db):
        """Lines 208-209: Exception during editor lookup defaults to 'Someone'"""
        from backend.api.tasks import _notify_task_changes
        
        old_data = {
            "title": "Old Title",
            "created_by": {"user_id": "creator1"}
        }
        updates = {"title": "New Title"}
        
        mock_db.collection.return_value.document.return_value.get.side_effect = Exception("DB error")
        
        mock_notifications = Mock()
        
        _notify_task_changes(mock_db, "task1", old_data, updates, "editor2", mock_notifications)
        
        # Should still create notification with default name
        assert mock_notifications.create_notification.called


class TestCreateNextRecurringTask:
    """Test _create_next_recurring_task helper function branches"""
    
    def test_not_recurring_returns_none(self, mock_db):
        """Lines 369-370: Not a recurring task returns None"""
        from backend.api.tasks import _create_next_recurring_task
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {"is_recurring": False}
        
        result = _create_next_recurring_task(mock_db, mock_task)
        assert result is None
    
    def test_no_interval_returns_none(self, mock_db):
        """Lines 407-408: No interval or interval <= 0 returns None"""
        from backend.api.tasks import _create_next_recurring_task
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "is_recurring": True,
            "recurrence_interval_days": 0
        }
        
        result = _create_next_recurring_task(mock_db, mock_task)
        assert result is None
    
    def test_negative_interval_returns_none(self, mock_db):
        """Lines 407-408: Negative interval returns None"""
        from backend.api.tasks import _create_next_recurring_task
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "is_recurring": True,
            "recurrence_interval_days": -5
        }
        
        result = _create_next_recurring_task(mock_db, mock_task)
        assert result is None
    
    def test_no_due_date_returns_none(self, mock_db):
        """Lines 431-437: No due date returns None"""
        from backend.api.tasks import _create_next_recurring_task
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "is_recurring": True,
            "recurrence_interval_days": 7,
            "due_date": None
        }
        
        result = _create_next_recurring_task(mock_db, mock_task)
        assert result is None
    
    def test_invalid_due_date_format_returns_none(self, mock_db):
        """Lines 449-451: Invalid due date format raises exception, returns None"""
        from backend.api.tasks import _create_next_recurring_task
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "is_recurring": True,
            "recurrence_interval_days": 7,
            "due_date": "not-a-valid-date"
        }
        
        result = _create_next_recurring_task(mock_db, mock_task)
        assert result is None


class TestListTasksEndpoint:
    """Test list_tasks endpoint branches"""
    
    def test_no_viewer_returns_401(self, client, mock_db, monkeypatch):
        """Lines 466-488: No viewer returns 401"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        response = client.get("/api/tasks")
        assert response.status_code == 401


class TestUpdateTaskEndpoint:
    """Test update_task endpoint branches"""
    
    def test_recurring_task_no_due_date_error(self, client, mock_db, monkeypatch):
        """Lines 622-623: Recurring task without due date returns 400"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"},
            "status": "To Do"
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task_doc
        
        response = client.put(
            "/api/tasks/task1",
            json={"is_recurring": True, "recurrence_interval_days": 7},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 400
        assert b"must have a due date" in response.data
    
    def test_recurring_task_invalid_interval_error(self, client, mock_db, monkeypatch):
        """Lines 654: Recurring task with invalid interval returns 400"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"},
            "status": "To Do",
            "due_date": "2025-12-01T10:00:00Z"
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task_doc
        
        response = client.put(
            "/api/tasks/task1",
            json={"is_recurring": True, "recurrence_interval_days": 0, "due_date": "2025-12-01T10:00:00Z"},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 400
        assert b"positive interval" in response.data
    
    def test_invalid_due_date_format_error(self, client, mock_db, monkeypatch):
        """Lines 659-660: Invalid due date format returns 400"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"},
            "status": "To Do"
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task_doc
        
        response = client.put(
            "/api/tasks/task1",
            json={"due_date": "not-a-valid-date"},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 400
        assert b"Invalid due date format" in response.data


class TestDeleteTaskEndpoint:
    """Test delete_task endpoint branches"""
    
    def test_staff_role_cannot_delete(self, client, mock_db, monkeypatch):
        """Lines 750->762, 759-760: Staff role cannot delete even if creator"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "staff"}
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value.get.return_value = mock_task_doc
                return mock_tasks
            elif name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.delete(
            "/api/tasks/task1",
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 403
        assert b"Permission denied" in response.data


class TestSubtaskEndpoints:
    """Test subtask endpoint branches"""
    
    def test_list_subtasks_exception_continues(self, client, mock_db, monkeypatch):
        """Lines 807-808: Exception while streaming subtasks continues"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value.get.return_value = mock_task_doc
                return mock_tasks
            elif name == "subtasks":
                mock_subtasks = Mock()
                # Raise exception during stream
                mock_subtasks.where.return_value.stream.side_effect = Exception("Stream error")
                return mock_subtasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_view_task_doc", return_value=True):
            response = client.get(
                "/api/tasks/task1/subtasks",
                headers={"X-User-Id": "user1"}
            )
            
            # Should still return 200 with empty list
            assert response.status_code == 200
            data = response.get_json()
            assert data == []
    
    def test_delete_subtask_exception_returns_500(self, client, mock_db, monkeypatch):
        """Lines 928-929: Exception during subtask delete returns 500"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = True
        mock_subtask_doc.to_dict.return_value = {"completed": False}
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.get.return_value = mock_subtask_doc
        # Raise exception during delete
        mock_subtask_ref.delete.side_effect = Exception("Delete error")
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value.get.return_value = mock_task_doc
                return mock_tasks
            elif name == "subtasks":
                mock_subtasks = Mock()
                mock_subtasks.document.return_value = mock_subtask_ref
                return mock_subtasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.delete(
            "/api/tasks/task1/subtasks/sub1",
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 500
        assert b"Failed to delete subtask" in response.data
