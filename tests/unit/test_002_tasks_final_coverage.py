"""
Final comprehensive tests to achieve 100% coverage for tasks.py
Covers all remaining missing branches including exception handlers and edge cases
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


class TestCanViewTaskDocExceptionPaths:
    """Test exception handling in _can_view_task_doc"""
    
    def test_can_view_project_membership_exception(self, mock_db):
        """Lines 65-66: Exception when checking project membership"""
        from backend.api.tasks import _can_view_task_doc
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "other"},
            "project_id": "proj123"
        }
        
        # Mock _require_membership to raise exception
        with patch("backend.api.tasks._viewer_id", return_value="viewer1"), \
             patch("backend.api.tasks._require_membership", side_effect=Exception("Membership error")):
            result = _can_view_task_doc(mock_db, mock_task)
            # Should continue and check other paths
            assert isinstance(result, bool)
    
    def test_can_view_user_not_exists(self, mock_db):
        """Lines 85: User document doesn't exist when checking is_managed_by"""
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
        
        # Mock creator doc doesn't exist
        mock_creator_doc = Mock()
        mock_creator_doc.exists = False
        
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
            # Should return False since user doesn't exist
            assert result is False
    
    def test_can_view_manager_exception_in_is_managed_by(self, mock_db):
        """Lines 92->97: Exception inside is_managed_by helper"""
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
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                def document_side_effect(user_id):
                    if user_id == "manager_user":
                        mock_doc_ref = Mock()
                        mock_doc_ref.get.return_value = mock_viewer_doc
                        return mock_doc_ref
                    elif user_id == "staff_user":
                        # Raise exception when getting staff user
                        raise Exception("DB error getting user")
                    return Mock()
                mock_users.document.side_effect = document_side_effect
                return mock_users
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._viewer_id", return_value="manager_user"):
            result = _can_view_task_doc(mock_db, mock_task)
            # Should return False due to exception
            assert result is False


class TestNotifyTaskChangesEditorName:
    """Test editor name resolution branches in _notify_task_changes"""
    
    def test_notify_editor_neither_creator_nor_assignee(self, mock_db):
        """Lines 158->166, 171->175, 182-189: Editor is neither creator nor assignee, DB lookup"""
        from backend.api.tasks import _notify_task_changes
        
        old_data = {
            "title": "Old Title",
            "created_by": {"user_id": "creator1", "name": "Creator"},
            "assigned_to": {"user_id": "assignee1", "name": "Assignee"}
        }
        updates = {"title": "New Title"}
        
        # Editor is different from creator and assignee
        mock_editor_doc = Mock()
        mock_editor_doc.exists = True
        mock_editor_doc.to_dict.return_value = {"name": "Editor Name"}
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_editor_doc
        mock_db.collection.return_value.where.return_value.stream.return_value = []
        
        mock_notifications = Mock()
        
        _notify_task_changes(mock_db, "task1", old_data, updates, "editor2", mock_notifications)
        
        # Should have looked up editor in DB
        assert mock_notifications.create_notification.called
    
    def test_notify_editor_doc_not_exists(self, mock_db):
        """Lines 182-189: Editor doc doesn't exist in DB"""
        from backend.api.tasks import _notify_task_changes
        
        old_data = {
            "title": "Old Title",
            "created_by": {"user_id": "creator1"}
        }
        updates = {"title": "New Title"}
        
        mock_editor_doc = Mock()
        mock_editor_doc.exists = False  # Doc doesn't exist
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_editor_doc
        mock_db.collection.return_value.where.return_value.stream.return_value = []
        
        mock_notifications = Mock()
        
        _notify_task_changes(mock_db, "task1", old_data, updates, "editor2", mock_notifications)
        
        # Should use default name "Someone"
        assert mock_notifications.create_notification.called


class TestListTasksComplexBranches:
    """Test complex filtering branches in list_tasks"""
    
    def test_list_tasks_with_project_memberships(self, client, mock_db, monkeypatch):
        """Lines 469->491, 477->491, 479->491, 483-488: User has project memberships"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "staff"}
        
        # Mock membership documents
        mock_membership1 = Mock()
        mock_membership1.to_dict.return_value = {"project_id": "proj1"}
        mock_membership2 = Mock()
        mock_membership2.to_dict.return_value = {"project_id": "proj2"}
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                mock_users.where.return_value.stream.return_value = []
                return mock_users
            elif name == "memberships":
                mock_memberships = Mock()
                # Return memberships for viewer
                mock_memberships.where.return_value.stream.return_value = [mock_membership1, mock_membership2]
                return mock_memberships
            elif name == "tasks":
                mock_tasks = Mock()
                mock_query = Mock()
                mock_query.limit.return_value.stream.return_value = []
                mock_tasks.where.return_value = mock_query
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks",
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200
    
    def test_list_tasks_admin_with_project_filter(self, client, mock_db, monkeypatch):
        """Lines 469->491: Admin viewing specific project"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "admin"}
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                mock_users.where.return_value.stream.return_value = []
                return mock_users
            elif name == "memberships":
                mock_memberships = Mock()
                mock_memberships.where.return_value.stream.return_value = []
                return mock_memberships
            elif name == "tasks":
                mock_tasks = Mock()
                mock_query = Mock()
                mock_query.limit.return_value.stream.return_value = []
                mock_tasks.where.return_value = mock_query
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "admin1"}
        )
        
        assert response.status_code == 200
    
    def test_list_tasks_outer_exception_handling(self, client, mock_db, monkeypatch):
        """Lines 492-494: Outer exception in project filtering continues"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "staff"}
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                mock_users.where.return_value.stream.return_value = []
                return mock_users
            elif name == "memberships":
                mock_memberships = Mock()
                # Raise exception when getting membership doc for project filter
                mock_memberships.document.return_value.get.side_effect = Exception("DB error")
                mock_memberships.where.return_value.stream.return_value = []
                return mock_memberships
            elif name == "tasks":
                mock_tasks = Mock()
                mock_query = Mock()
                mock_query.limit.return_value.stream.return_value = []
                mock_tasks.where.return_value = mock_query
                return mock_tasks
            elif name == "projects":
                # Raise exception when getting project doc
                raise Exception("Projects collection error")
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "user1"}
        )
        
        # Should still return 200
        assert response.status_code == 200


class TestUpdateTaskBranches:
    """Test remaining update_task branches"""
    
    def test_update_task_no_updates_error(self, client, mock_db, monkeypatch):
        """Line 554: No fields to update returns 400"""
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
            json={},  # No fields
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 400
        assert b"No fields to update" in response.data


class TestDeleteTaskBranches:
    """Test delete_task remaining branches"""
    
    def test_delete_task_viewer_role_exception(self, client, mock_db, monkeypatch):
        """Lines 750->762, 759-760: Exception when getting viewer role"""
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
            elif name == "users":
                # Raise exception when getting user doc
                raise Exception("User lookup error")
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.delete(
            "/api/tasks/task1",
            headers={"X-User-Id": "user1"}
        )
        
        # Should default to staff role and deny
        assert response.status_code == 403


class TestSubtaskAdditionalBranches:
    """Test remaining subtask branches"""
    
    def test_create_subtask_title_validation(self, client, mock_db, monkeypatch):
        """Lines 818, 823: Title validation in create_subtask"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task_doc
        
        # Test with empty title
        response = client.post(
            "/api/tasks/task1/subtasks",
            json={"title": ""},  # Empty title
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 400
        assert b"title required" in response.data.lower()
    
    def test_update_subtask_success(self, client, mock_db, monkeypatch):
        """Lines 906, 911, 920: Update subtask title and description"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = True
        mock_subtask_doc.to_dict.return_value = {
            "title": "Old Title",
            "description": "Old Desc"
        }
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.get.return_value = mock_subtask_doc
        mock_subtask_ref.update.return_value = None
        
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
        
        response = client.put(
            "/api/tasks/task1/subtasks/sub1",
            json={
                "title": "New Title",
                "description": "New Desc"
            },
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200


class TestRecurringTaskBranches:
    """Test remaining recurring task branches"""
    
    def test_recurring_task_without_due_date_in_data(self, mock_db):
        """Lines 431-437: Recurring task with no due_date in current data"""
        from backend.api.tasks import _create_next_recurring_task
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "is_recurring": True,
            "recurrence_interval_days": 7,
            # No due_date field
        }
        
        result = _create_next_recurring_task(mock_db, mock_task)
        assert result is None


class TestArchiveAndDeleteBranches:
    """Test archive and delete related branches"""
    
    def test_archive_workflow(self, client, mock_db, monkeypatch):
        """Lines 785, 788: Test archive functionality"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "admin1"},
            "archived": False
        }
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "admin"}
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            elif name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        # Delete actually archives the task
        response = client.delete(
            "/api/tasks/task1",
            headers={"X-User-Id": "admin1"}
        )
        
        # Should archive successfully
        assert response.status_code == 200


class TestCompleteSubtaskBranches:
    """Test complete_subtask remaining branches"""
    
    def test_complete_subtask_setting_completed(self, client, mock_db, monkeypatch):
        """Lines 947, 952, 956: Setting completed to True"""
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
        mock_subtask_ref.update.return_value = None
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            elif name == "subtasks":
                mock_subtasks = Mock()
                mock_subtasks.document.return_value = mock_subtask_ref
                return mock_subtasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_view_task_doc", return_value=True):
            response = client.patch(
                "/api/tasks/task1/subtasks/sub1/complete",
                json={"completed": True},
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 200


class TestMiscellaneousBranches:
    """Test miscellaneous remaining branches"""
    
    def test_notify_with_labels_change(self, mock_db):
        """Lines 239: Label changes in notifications"""
        from backend.api.tasks import _notify_task_changes
        
        old_data = {
            "title": "Task",
            "labels": ["label1", "label2"],
            "created_by": {"user_id": "user1"}
        }
        updates = {
            "labels": ["label3"]  # Changed labels
        }
        
        mock_db.collection.return_value.where.return_value.stream.return_value = []
        
        mock_notifications = Mock()
        
        _notify_task_changes(mock_db, "task1", old_data, updates, "user1", mock_notifications)
        
        # Should create notification for label change
        assert mock_notifications.create_notification.called
    
    def test_list_tasks_debug_mode(self, client, mock_db, monkeypatch):
        """Lines 541-542: Debug mode returns diagnostics"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "staff"}
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                mock_users.where.return_value.stream.return_value = []
                return mock_users
            elif name == "memberships":
                mock_memberships = Mock()
                mock_memberships.where.return_value.stream.return_value = []
                return mock_memberships
            elif name == "tasks":
                mock_tasks = Mock()
                mock_query = Mock()
                mock_query.limit.return_value.stream.return_value = []
                mock_tasks.where.return_value = mock_query
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks?debug=1",
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert "_diag" in data
