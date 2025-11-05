"""
Tests for delete_subtask validation error paths (lines 906, 911, 920)
"""
import pytest
import sys
from unittest.mock import Mock, patch

fake_firestore = sys.modules.get("firebase_admin.firestore")


@pytest.fixture
def mock_db():
    return Mock()


class TestDeleteSubtaskValidationErrors:
    """Cover lines 906, 911, 920 in delete_subtask"""
    
    def test_delete_subtask_missing_viewer_line_906(self, client):
        """Line 906: No X-User-Id header in delete_subtask"""
        response = client.delete("/api/tasks/task1/subtasks/sub1")
        
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"] == "viewer_id required"
    
    def test_delete_subtask_task_not_found_line_911(self, client, mock_db, monkeypatch):
        """Line 911: Task does not exist in delete_subtask"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock task not found
        mock_task_doc = Mock()
        mock_task_doc.exists = False
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        
        mock_db.collection.return_value.document.return_value = mock_task_ref
        
        response = client.delete(
            "/api/tasks/nonexistent_task/subtasks/sub1",
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "Task not found"
    
    def test_delete_subtask_subtask_not_found_line_920(self, client, mock_db, monkeypatch):
        """Line 920: Subtask does not exist in delete_subtask"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock task exists
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        # Mock subtask NOT found
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = False
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.get.return_value = mock_subtask_doc
        
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
        
        response = client.delete(
            "/api/tasks/task1/subtasks/nonexistent_sub",
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "Subtask not found"
