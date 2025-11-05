"""
Comprehensive tests for ALL remaining missing lines in subtask endpoints
Lines: 818, 823, 871, 876, 936-937, 947, 952, 956, 984-987
"""
import pytest
import sys
from unittest.mock import Mock, patch

fake_firestore = sys.modules.get("firebase_admin.firestore")


@pytest.fixture
def mock_db():
    return Mock()


class TestCreateSubtaskValidationErrors:
    """Lines 818, 823 in create_subtask"""
    
    def test_create_subtask_missing_viewer_line_818(self, client):
        """Line 818: No X-User-Id header in create_subtask"""
        response = client.post(
            "/api/tasks/task1/subtasks",
            json={"title": "Test Subtask"}
        )
        
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"] == "viewer_id required"
    
    def test_create_subtask_task_not_found_line_823(self, client, mock_db, monkeypatch):
        """Line 823: Task does not exist in create_subtask"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock task not found
        mock_task_doc = Mock()
        mock_task_doc.exists = False
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        
        mock_db.collection.return_value.document.return_value = mock_task_ref
        
        response = client.post(
            "/api/tasks/nonexistent_task/subtasks",
            json={"title": "Test Subtask"},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "Task not found"


class TestUpdateSubtaskValidationErrors:
    """Lines 871, 876 in update_subtask"""
    
    def test_update_subtask_missing_viewer_line_871(self, client):
        """Line 871: No X-User-Id header in update_subtask"""
        response = client.put(
            "/api/tasks/task1/subtasks/sub1",
            json={"title": "New Title"}
        )
        
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"] == "viewer_id required"
    
    def test_update_subtask_task_not_found_line_876(self, client, mock_db, monkeypatch):
        """Line 876: Task does not exist in update_subtask"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock task not found
        mock_task_doc = Mock()
        mock_task_doc.exists = False
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        
        mock_db.collection.return_value.document.return_value = mock_task_ref
        
        response = client.put(
            "/api/tasks/nonexistent_task/subtasks/sub1",
            json={"title": "New Title"},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "Task not found"


class TestDeleteSubtaskIncrementException:
    """Lines 936-937: Exception handler in delete_subtask Increment operations"""
    
    def test_delete_subtask_increment_exception_lines_936_937(self, client, mock_db, monkeypatch):
        """Lines 936-937: Exception when decrementing subtask counts"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock task
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        # Mock subtask (completed)
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = True
        mock_subtask_doc.to_dict.return_value = {"completed": True}
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        # Make update raise exception to trigger except block (lines 936-937)
        mock_task_ref.update.side_effect = Exception("Firestore error")
        
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
        
        # Should still succeed despite Increment exception
        response = client.delete(
            "/api/tasks/task1/subtasks/sub1",
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True


class TestCompleteSubtaskValidationErrors:
    """Lines 947, 952, 956 in complete_subtask"""
    
    def test_complete_subtask_missing_viewer_line_947(self, client):
        """Line 947: No X-User-Id header in complete_subtask"""
        response = client.patch(
            "/api/tasks/task1/subtasks/sub1/complete",
            json={"completed": True}
        )
        
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"] == "viewer_id required"
    
    def test_complete_subtask_task_not_found_line_952(self, client, mock_db, monkeypatch):
        """Line 952: Task does not exist in complete_subtask"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock task not found
        mock_task_doc = Mock()
        mock_task_doc.exists = False
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        
        mock_db.collection.return_value.document.return_value = mock_task_ref
        
        response = client.patch(
            "/api/tasks/nonexistent_task/subtasks/sub1/complete",
            json={"completed": True},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "Task not found"
    
    def test_complete_subtask_viewer_cannot_view_line_956(self, client, mock_db, monkeypatch):
        """Line 956: Viewer cannot view task in complete_subtask"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock task exists
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user999"},  # Different user
            "project": {"id": "proj1"}
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        
        mock_db.collection.return_value.document.return_value = mock_task_ref
        
        # Mock _can_view_task_doc to return False
        with patch("backend.api.tasks._can_view_task_doc", return_value=False):
            response = client.patch(
                "/api/tasks/task1/subtasks/sub1/complete",
                json={"completed": True},
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "Not found"


class TestCompleteSubtaskDecrementBranch:
    """Lines 984-987: elif branch for decrementing completed count"""
    
    def test_complete_subtask_decrement_branch_lines_984_987(self, client, mock_db, monkeypatch):
        """Lines 984-987: Uncomplete a subtask (decrement completed count)"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock task
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        # Mock completed subtask
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = True
        mock_subtask_doc.to_dict.return_value = {"completed": True}
        
        # Mock subtask after update
        mock_updated_subtask_doc = Mock()
        mock_updated_subtask_doc.to_dict.return_value = {
            "completed": False,
            "completed_at": None,
            "completed_by": None
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.get.side_effect = [mock_subtask_doc, mock_updated_subtask_doc]
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
                json={"completed": False},  # Uncomplete the subtask
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 200
        # Verify decrement was called (line 985: Increment(-1))
        assert mock_task_ref.update.called
        update_calls = mock_task_ref.update.call_args_list
        # Should have called update with Increment(-1)
        assert len(update_calls) > 0
    
    def test_complete_subtask_increment_exception_lines_986_987(self, client, mock_db, monkeypatch):
        """Lines 986-987: Exception handler for Increment operations"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock task
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        # Mock incomplete subtask
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = True
        mock_subtask_doc.to_dict.return_value = {"completed": False}
        
        # Mock subtask after update
        mock_updated_subtask_doc = Mock()
        mock_updated_subtask_doc.to_dict.return_value = {
            "completed": True,
            "completed_at": "2025-11-05T10:00:00Z",
            "completed_by": {"user_id": "user1"}
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        # Make task_ref.update raise exception to trigger except block
        mock_task_ref.update.side_effect = Exception("Firestore error")
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.get.side_effect = [mock_subtask_doc, mock_updated_subtask_doc]
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
            # Should still succeed despite Increment exception
            response = client.patch(
                "/api/tasks/task1/subtasks/sub1/complete",
                json={"completed": True},
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["subtask_id"] == "sub1"
