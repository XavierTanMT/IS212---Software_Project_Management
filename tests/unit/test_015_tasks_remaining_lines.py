"""
Complete 100% coverage - targeting all remaining lines and branches
Lines: 689, 724, 780, 794->810, 795-796, 827, 880, 885, 915, 934->939, 961
"""
import pytest
import sys
from unittest.mock import Mock, patch

fake_firestore = sys.modules.get("firebase_admin.firestore")


@pytest.fixture
def mock_db():
    return Mock()


class TestReassignTaskErrors:
    """Lines 689, 724: Reassign task error paths"""
    
    def test_reassign_missing_new_assigned_to_id_line_689(self, client, mock_db, monkeypatch):
        """Line 689: new_assigned_to_id is missing/empty"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "manager"}
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        # Missing new_assigned_to_id
        response = client.patch(
            "/api/tasks/task1/reassign",
            json={},  # No new_assigned_to_id
            headers={"X-User-Id": "manager1"}
        )
        
        assert response.status_code == 400
        assert "new_assigned_to_id is required" in response.get_json()["error"]
    
    def test_reassign_new_assignee_not_found_line_724(self, client, mock_db, monkeypatch):
        """Line 724: New assignee user doesn't exist"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "manager"}
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "creator1"},
            "assigned_to": {"user_id": "old_user"}
        }
        
        # New assignee doesn't exist
        mock_new_assignee_doc = Mock()
        mock_new_assignee_doc.exists = False  # Line 724
        
        def collection_side_effect(name):
            if name == "users":
                def user_doc_side_effect(user_id):
                    mock_user = Mock()
                    if user_id == "manager1":
                        mock_user.get.return_value = mock_viewer_doc
                    elif user_id == "nonexistent":
                        mock_user.get.return_value = mock_new_assignee_doc
                    return mock_user
                mock_users = Mock()
                mock_users.document.side_effect = user_doc_side_effect
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value.get.return_value = mock_task_doc
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.patch(
            "/api/tasks/task1/reassign",
            json={"new_assigned_to_id": "nonexistent"},
            headers={"X-User-Id": "manager1"}
        )
        
        assert response.status_code == 404
        assert "New assignee user not found" in response.get_json()["error"]


class TestListSubtasksErrors:
    """Lines 780, 794->810: List subtasks error paths"""
    
    def test_list_subtasks_task_not_found_line_780(self, client, mock_db, monkeypatch):
        """Line 780: Task doesn't exist when listing subtasks"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = False  # Line 780
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value.get.return_value = mock_task_doc
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks/task1/subtasks",
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 404
        assert "Task not found" in response.get_json()["error"]
    
    def test_list_subtasks_exception_lines_794_810(self, client, mock_db, monkeypatch):
        """Lines 794-810: Exception when querying subtasks (returns empty list)"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        # Mock subtasks query that raises exception during stream()
        mock_subtasks_query = Mock()
        mock_subtasks_query.stream.side_effect = Exception("Database error")
        
        mock_subtasks = Mock()
        mock_subtasks.where.return_value = mock_subtasks_query
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value.get.return_value = mock_task_doc
                return mock_tasks
            elif name == "subtasks":
                return mock_subtasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_view_task_doc", return_value=True):
            # Should return empty list on exception
            response = client.get(
                "/api/tasks/task1/subtasks",
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 200
        assert response.get_json() == []


class TestCreateSubtaskErrors:
    """Line 827: Create subtask error paths"""
    
    def test_create_subtask_forbidden_line_827(self, client, mock_db, monkeypatch):
        """Line 827: User is not creator (forbidden)"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "other_user",
            "role": "staff"
        }
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "creator_user"}  # Different from viewer
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
        
        response = client.post(
            "/api/tasks/task1/subtasks",
            json={"title": "Subtask Title", "description": "Description"},
            headers={"X-User-Id": "other_user"}
        )
        
        assert response.status_code == 403
        assert "forbidden" in response.get_json()["error"]


class TestCompleteSubtaskErrors:
    """Lines 880, 885, 915: Complete subtask error paths"""
    
    def test_complete_subtask_forbidden_line_880(self, client, mock_db, monkeypatch):
        """Line 880: User is not task creator (forbidden) - update_subtask endpoint"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "other_user",
            "role": "staff"
        }
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "creator_user"}  # Different from viewer
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
        
        response = client.put(
            "/api/tasks/task1/subtasks/subtask1",
            json={"title": "Updated title"},
            headers={"X-User-Id": "other_user"}
        )
        
        assert response.status_code == 403
        assert "forbidden" in response.get_json()["error"]
    
    def test_complete_subtask_not_found_line_885(self, client, mock_db, monkeypatch):
        """Line 885: Subtask doesn't exist"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "staff"}
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = False  # Line 885
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value.get.return_value = mock_task_doc
                return mock_tasks
            elif name == "subtasks":
                mock_subtasks = Mock()
                mock_subtasks.document.return_value.get.return_value = mock_subtask_doc
                return mock_subtasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_edit_task", return_value=True):
            response = client.patch(
                "/api/tasks/task1/subtasks/subtask1/complete",
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 404
        assert "Subtask not found" in response.get_json()["error"]


class TestDeleteSubtaskErrors:
    """Lines 915, 934->939, 961: Delete subtask error paths"""
    
    def test_delete_subtask_forbidden_line_915(self, client, mock_db, monkeypatch):
        """Line 915: User can't edit task (forbidden)"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "other_user",
            "role": "staff"
        }
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "creator_user"}  # Different from viewer
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
        
        response = client.delete(
            "/api/tasks/task1/subtasks/subtask1",
            headers={"X-User-Id": "other_user"}
        )
        
        assert response.status_code == 403
        assert "forbidden" in response.get_json()["error"]
    
    def test_delete_subtask_was_completed_lines_934_939(self, client, mock_db, monkeypatch):
        """Lines 934-939: Delete completed subtask (decrement count)"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "staff"}
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        # Subtask that was completed
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = True
        mock_subtask_doc.to_dict.return_value = {
            "task_id": "task1",
            "completed": True  # was_completed = True, triggers line 935
        }
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.get.return_value = mock_subtask_doc
        mock_subtask_ref.delete.return_value = None
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            elif name == "subtasks":
                mock_subtasks = Mock()
                mock_subtasks.document.return_value = mock_subtask_ref
                return mock_subtasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_edit_task", return_value=True):
            response = client.delete(
                "/api/tasks/task1/subtasks/subtask1",
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 200
        # Should have called update with Increment(-1) for completed subtask
        mock_task_ref.update.assert_called()
    
    def test_delete_subtask_not_found_line_961(self, client, mock_db, monkeypatch):
        """Line 961: Subtask doesn't exist when deleting"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "staff"}
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = False  # Line 961
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value.get.return_value = mock_task_doc
                return mock_tasks
            elif name == "subtasks":
                mock_subtasks = Mock()
                mock_subtasks.document.return_value.get.return_value = mock_subtask_doc
                return mock_subtasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_edit_task", return_value=True):
            response = client.delete(
                "/api/tasks/task1/subtasks/subtask1",
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 404
        assert "Subtask not found" in response.get_json()["error"]
