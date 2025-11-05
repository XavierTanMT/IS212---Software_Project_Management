"""
Comprehensive tests to achieve 100% branch coverage for tasks.py
Covers all remaining missing branches including Increment operations and exception handlers
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


class TestIncrementOperations:
    """Test all Firestore.Increment operations (lines 871, 876, 934-935, 947, 952, 956, 984->989)"""
    
    # Note: The successful Increment paths are already covered by test_001_tasks_additional.py
    # test_create_subtask_increment_exception, etc.
    # The lines with Increment are executed when exceptions don't occur in the existing comprehensive tests
    
    def test_delete_subtask_with_decrement_success(self, client, mock_db, monkeypatch):
        """Lines 934-935: Successful subtask count decrement for completed subtask"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = True
        mock_subtask_doc.to_dict.return_value = {"completed": True}  # Completed subtask
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.get.return_value = mock_subtask_doc
        mock_subtask_ref.delete.return_value = None
        
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
            response = client.delete(
                "/api/tasks/task1/subtasks/sub1",
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 200
        # Verify decrement was called twice (subtask_count and subtask_completed_count)
        assert mock_task_ref.update.call_count >= 2
    
    def test_complete_subtask_increment_completed_count(self, client, mock_db, monkeypatch):
        """Lines 947, 952, 956, 984->989: Increment completed count when marking as complete"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = True
        mock_subtask_doc.to_dict.return_value = {"completed": False}  # Not completed yet
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.get.return_value = mock_subtask_doc
        mock_subtask_ref.update.return_value = None
        
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
        # Verify increment was called
        assert mock_task_ref.update.called
    
    def test_uncomplete_subtask_decrement_completed_count(self, client, mock_db, monkeypatch):
        """Lines 984->989: Decrement completed count when unmarking as complete"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = True
        mock_subtask_doc.to_dict.return_value = {"completed": True}  # Already completed
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.get.return_value = mock_subtask_doc
        mock_subtask_ref.update.return_value = None
        
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
                json={"completed": False},  # Unmark as complete
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 200
        # Verify decrement was called
        assert mock_task_ref.update.called


class TestUpdateSubtaskAllFields:
    """Test all update_subtask field assignment branches (lines 906, 911, 920)"""
    
    def test_update_subtask_title_field(self, client, mock_db, monkeypatch):
        """Line 906: Update title field"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = True
        mock_subtask_doc.to_dict.return_value = {"title": "Old"}
        
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
            json={"title": "New Title"},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200
    
    def test_update_subtask_description_field(self, client, mock_db, monkeypatch):
        """Line 911: Update description field"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = True
        mock_subtask_doc.to_dict.return_value = {"description": "Old"}
        
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
            json={"description": "New Description"},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200
    
    def test_update_subtask_both_title_and_description(self, client, mock_db, monkeypatch):
        """Line 920: Update both title and description"""
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
            json={"title": "New Title", "description": "New Desc"},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200


class TestCreateSubtaskValidation:
    """Test create_subtask validation branches (lines 818, 823)"""
    
    def test_create_subtask_none_title(self, client, mock_db, monkeypatch):
        """Line 818: Title is None"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task_doc
        
        response = client.post(
            "/api/tasks/task1/subtasks",
            json={"title": None},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 400
    
    def test_create_subtask_whitespace_title(self, client, mock_db, monkeypatch):
        """Line 823: Title is whitespace only"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task_doc
        
        response = client.post(
            "/api/tasks/task1/subtasks",
            json={"title": "   "},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 400


class TestNotificationExceptionBranches:
    """Test notification exception handlers (lines 208-209, 369-370, 622-623)"""
    
    def test_notify_task_changes_notification_exception(self, mock_db):
        """Lines 208-209: Exception when creating notification in _notify_task_changes"""
        from backend.api.tasks import _notify_task_changes
        
        old_data = {
            "title": "Old",
            "created_by": {"user_id": "user1"}
        }
        updates = {"title": "New"}
        
        mock_db.collection.return_value.where.return_value.stream.return_value = []
        
        mock_notifications = Mock()
        mock_notifications.create_notification.side_effect = Exception("Notification error")
        
        # Should not raise, just print error
        _notify_task_changes(mock_db, "task1", old_data, updates, "user1", mock_notifications)
        
        # Verify it tried to create notification
        assert mock_notifications.create_notification.called
    
    # Lines 369-370 and 622-623 are already covered by the exception tests
    # The notification creation happens inside a try/except that continues on error


class TestHelperExceptionBranches:
    """Test exception handlers in helper functions (lines 85, 239)"""
    
    def test_can_view_task_viewer_role_exception(self, mock_db):
        """Line 85: Exception when getting viewer role in is_managed_by"""
        from backend.api.tasks import _can_view_task_doc
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "creator1"},
            "assigned_to": {"user_id": "other"}
        }
        
        # Mock viewer as manager
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "manager"}
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                def doc_side_effect(user_id):
                    if user_id == "viewer1":
                        mock_doc_ref = Mock()
                        mock_doc_ref.get.return_value = mock_viewer_doc
                        return mock_doc_ref
                    elif user_id == "creator1":
                        # Raise exception when checking if creator is managed by viewer
                        raise Exception("DB error")
                    return Mock()
                mock_users.document.side_effect = doc_side_effect
                return mock_users
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._viewer_id", return_value="viewer1"):
            result = _can_view_task_doc(mock_db, mock_task)
            # Should return False due to exception
            assert result is False
    
    def test_create_next_recurring_invalid_date_exception(self, mock_db):
        """Line 239: Exception when parsing due date in _create_next_recurring_task"""
        from backend.api.tasks import _create_next_recurring_task
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "is_recurring": True,
            "recurrence_interval_days": 7,
            "due_date": "invalid-date-format"  # Invalid date
        }
        
        result = _create_next_recurring_task(mock_db, mock_task)
        # Should return None due to exception
        assert result is None


class TestEditorNameResolution:
    """Test editor name resolution branches in _notify_task_changes (lines 171->175, 182-189)"""
    
    def test_notify_editor_is_neither_creator_nor_assignee(self, mock_db):
        """Lines 171->175, 182-189: Editor is neither creator nor assignee, lookup name from DB"""
        from backend.api.tasks import _notify_task_changes
        
        old_data = {
            "title": "Old",
            "created_by": {"user_id": "creator1", "name": "Creator"},
            "assigned_to": {"user_id": "assignee1", "name": "Assignee"}
        }
        updates = {"title": "New"}
        editor_id = "editor2"  # Different from creator and assignee
        
        # Mock editor document
        mock_editor_doc = Mock()
        mock_editor_doc.exists = True
        mock_editor_doc.to_dict.return_value = {"name": "Editor Name"}
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_editor_doc
        mock_db.collection.return_value.where.return_value.stream.return_value = []
        
        mock_notifications = Mock()
        
        _notify_task_changes(mock_db, "task1", old_data, updates, editor_id, mock_notifications)
        
        # Should have looked up editor name
        assert mock_db.collection.return_value.document.called
    
    def test_notify_editor_doc_not_exists(self, mock_db):
        """Lines 182-189: Editor document doesn't exist, use default name"""
        from backend.api.tasks import _notify_task_changes
        
        old_data = {
            "title": "Old",
            "created_by": {"user_id": "creator1"}
        }
        updates = {"title": "New"}
        editor_id = "editor2"
        
        # Mock editor document doesn't exist
        mock_editor_doc = Mock()
        mock_editor_doc.exists = False
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_editor_doc
        mock_db.collection.return_value.where.return_value.stream.return_value = []
        
        mock_notifications = Mock()
        
        _notify_task_changes(mock_db, "task1", old_data, updates, editor_id, mock_notifications)
        
        # Should use default name "Someone"
        assert mock_notifications.create_notification.called


class TestListTasksComplexFiltering:
    """Test complex list_tasks filtering (lines 469->491, 477->491, 479->491, 483-485)"""
    
    def test_list_tasks_viewer_is_project_owner_branch(self, client, mock_db, monkeypatch):
        """Lines 469->491: Viewer is the project owner"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        viewer_id = "owner1"
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "staff"}
        
        # Mock membership exists for project filter
        mock_membership_doc = Mock()
        mock_membership_doc.exists = True
        
        # Mock project with viewer as owner
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {"owner_id": viewer_id}  # Viewer IS owner
        
        call_count = [0]
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                mock_users.where.return_value.stream.return_value = []
                return mock_users
            elif name == "memberships":
                mock_memberships = Mock()
                mock_memberships.document.return_value.get.return_value = mock_membership_doc
                mock_memberships.where.return_value.stream.return_value = []
                return mock_memberships
            elif name == "projects":
                mock_projects = Mock()
                mock_projects.document.return_value.get.return_value = mock_project_doc
                return mock_projects
            elif name == "tasks":
                mock_tasks = Mock()
                call_count[0] += 1
                mock_query = Mock()
                mock_query.limit.return_value.stream.return_value = []
                mock_tasks.where.return_value = mock_query
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            f"/api/tasks?project_id=proj1",
            headers={"X-User-Id": viewer_id}
        )
        
        assert response.status_code == 200
    
    def test_list_tasks_viewer_reports_to_project_owner(self, client, mock_db, monkeypatch):
        """Lines 477->491, 479->491, 483-485: Viewer's manager is project owner"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        viewer_id = "staff1"
        owner_id = "owner1"
        
        mock_viewer_doc_for_role = Mock()
        mock_viewer_doc_for_role.exists = True
        mock_viewer_doc_for_role.to_dict.return_value = {"role": "staff"}
        
        mock_viewer_doc_for_manager = Mock()
        mock_viewer_doc_for_manager.exists = True
        mock_viewer_doc_for_manager.to_dict.return_value = {"manager_id": owner_id}  # Reports to owner
        
        mock_membership_doc = Mock()
        mock_membership_doc.exists = True
        
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {"owner_id": owner_id}
        
        get_call_count = [0]
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                
                def doc_side_effect(user_id):
                    mock_doc_ref = Mock()
                    if user_id == viewer_id:
                        get_call_count[0] += 1
                        if get_call_count[0] == 1:
                            # First call for role check
                            mock_doc_ref.get.return_value = mock_viewer_doc_for_role
                        else:
                            # Second call for manager check
                            mock_doc_ref.get.return_value = mock_viewer_doc_for_manager
                    return mock_doc_ref
                
                mock_users.document.side_effect = doc_side_effect
                mock_users.where.return_value.stream.return_value = []
                return mock_users
            elif name == "memberships":
                mock_memberships = Mock()
                mock_memberships.document.return_value.get.return_value = mock_membership_doc
                mock_memberships.where.return_value.stream.return_value = []
                return mock_memberships
            elif name == "projects":
                mock_projects = Mock()
                mock_projects.document.return_value.get.return_value = mock_project_doc
                return mock_projects
            elif name == "tasks":
                mock_tasks = Mock()
                mock_query = Mock()
                mock_query.limit.return_value.stream.return_value = []
                mock_tasks.where.return_value = mock_query
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            f"/api/tasks?project_id=proj1",
            headers={"X-User-Id": viewer_id}
        )
        
        assert response.status_code == 200


class TestRemainingEdgeCases:
    """Test remaining edge cases (lines 554, 682, 708, 750->762, 759-760, 785, 788)"""
    
    def test_get_task_not_viewable(self, client, mock_db, monkeypatch):
        """Line 554: User cannot view task"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "other"}
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task_doc
        
        with patch("backend.api.tasks._can_view_task_doc", return_value=False):
            response = client.get(
                "/api/tasks/task1",
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 404
    
    def test_reassign_task_not_manager_role(self, client, mock_db, monkeypatch):
        """Line 682: User is not manager, cannot reassign"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "staff"}  # Not manager
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_viewer_doc
        
        response = client.patch(
            "/api/tasks/task1/reassign",
            json={"new_assigned_to_id": "user2"},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 403
    
    def test_reassign_task_same_assignee(self, client, mock_db, monkeypatch):
        """Line 708: Already assigned to same user"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "manager"}
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "assigned_to": {"user_id": "user2"}
        }
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value.get.return_value = mock_task_doc
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.patch(
            "/api/tasks/task1/reassign",
            json={"new_assigned_to_id": "user2"},  # Same as current
            headers={"X-User-Id": "manager1"}
        )
        
        assert response.status_code == 200
        assert b"already assigned" in response.data
    
    def test_delete_task_hr_role(self, client, mock_db, monkeypatch):
        """Lines 750->762, 759-760: HR role can delete"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "hr1"}
        }
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "hr"}
        
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
        
        response = client.delete(
            "/api/tasks/task1",
            headers={"X-User-Id": "hr1"}
        )
        
        # Lines 785, 788: Archive fields updated
        assert response.status_code == 200
        assert mock_task_ref.update.called
