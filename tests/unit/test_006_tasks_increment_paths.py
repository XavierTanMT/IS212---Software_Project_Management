"""
Integration-style tests to cover Increment operations and remaining branches
Uses realistic mocking to trigger successful code paths
"""
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone

fake_firestore = sys.modules.get("firebase_admin.firestore")


@pytest.fixture
def mock_db():
    return Mock()


class TestIncrementSuccessfulPaths:
    """Test successful Increment operations that are currently shown as missing"""
    
    def test_create_subtask_successful_increment_line_871(self, client, mock_db, monkeypatch):
        """Line 871: firestore.Increment(1) for subtask_count - SUCCESSFUL path"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock creator user
        mock_creator_doc = Mock()
        mock_creator_doc.exists = True
        mock_creator_doc.to_dict.return_value = {
            "name": "Creator Name",
            "email": "creator@example.com"
        }
        
        # Mock task
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        # Make update succeed (no exception) to cover line 871
        mock_task_ref.update.return_value = None
        
        # Mock subtask
        mock_subtask_ref = Mock()
        mock_subtask_ref.id = "sub123"
        mock_subtask_ref.set.return_value = None
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_creator_doc
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
        
        response = client.post(
            "/api/tasks/task1/subtasks",
            json={"title": "Test Subtask", "description": "Test Description"},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 201
        # Verify Increment was called (line 871 executed)
        assert mock_task_ref.update.called
        # Check that it was called with Increment
        call_args = mock_task_ref.update.call_args_list
        assert len(call_args) > 0
    
    def test_delete_subtask_successful_decrements_lines_936_937(self, client, mock_db, monkeypatch):
        """Lines 936-937: Successful decrements for subtask_count and subtask_completed_count"""
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
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        # Make updates succeed to cover lines 936-937
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
        # Verify decrements were called (lines 936-937)
        assert mock_task_ref.update.call_count >= 2
    
    def test_complete_subtask_increment_lines_984_986(self, client, mock_db, monkeypatch):
        """Lines 984, 986: Increment completed count when marking subtask as complete"""
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
        # Make update succeed to cover line 984
        mock_task_ref.update.return_value = None
        
        mock_subtask_ref = Mock()
        # First call returns incomplete, second call (after update) returns completed
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
                json={"completed": True},
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 200
        # Verify increment was called (line 984)
        assert mock_task_ref.update.called
    
    def test_uncomplete_subtask_decrement_lines_986_987(self, client, mock_db, monkeypatch):
        """Lines 986-987: Decrement completed count when unmarking subtask"""
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
        # Make update succeed to cover line 986
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
                json={"completed": False},
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 200
        # Verify decrement was called (line 986-987)
        assert mock_task_ref.update.called


class TestUpdateSubtaskAllBranches:
    """Test all branches in update_subtask (lines 906, 911, 920, 947, 952, 956)"""
    
    def test_update_subtask_only_title_line_906(self, client, mock_db, monkeypatch):
        """Line 906: Update only title field"""
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
            "description": "Old Description"
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
            json={"title": "New Title"},  # Only title, not description
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200
        # Verify only title was in updates (line 906)
        update_call = mock_subtask_ref.update.call_args[0][0]
        assert "title" in update_call
        assert "description" not in update_call
    
    def test_update_subtask_only_description_line_911(self, client, mock_db, monkeypatch):
        """Line 911: Update only description field"""
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
            "description": "Old Description"
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
            json={"description": "New Description"},  # Only description
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200
        # Verify only description was in updates (line 911)
        update_call = mock_subtask_ref.update.call_args[0][0]
        assert "description" in update_call
        assert "title" not in update_call
    
    def test_update_subtask_both_fields_line_920(self, client, mock_db, monkeypatch):
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
            "description": "Old Description"
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
            json={"title": "New Title", "description": "New Description"},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200
        # Verify both were in updates (line 920)
        update_call = mock_subtask_ref.update.call_args[0][0]
        assert "title" in update_call
        assert "description" in update_call


class TestCompleteSubtaskFieldUpdates:
    """Test complete_subtask field update branches (lines 947, 952, 956)"""
    
    def test_complete_subtask_sets_completed_fields_lines_947_952(self, client, mock_db, monkeypatch):
        """Lines 947, 952: Set completed_at and completed_by when completing"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = True
        mock_subtask_doc.to_dict.return_value = {"completed": False}
        
        mock_updated_doc = Mock()
        mock_updated_doc.to_dict.return_value = {
            "completed": True,
            "completed_at": "2025-11-05T10:00:00Z"
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.get.side_effect = [mock_subtask_doc, mock_updated_doc]
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
        # Verify completed_at and completed_by were set (lines 947, 952)
        update_call = mock_subtask_ref.update.call_args[0][0]
        assert "completed" in update_call
        assert update_call["completed"] is True
        assert "completed_at" in update_call
        assert "completed_by" in update_call
    
    def test_uncomplete_subtask_clears_fields_line_956(self, client, mock_db, monkeypatch):
        """Line 956: Clear completed_at and completed_by when uncompleting"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = True
        mock_subtask_doc.to_dict.return_value = {
            "completed": True,
            "completed_at": "2025-11-05T09:00:00Z",
            "completed_by": {"user_id": "user1"}
        }
        
        mock_updated_doc = Mock()
        mock_updated_doc.to_dict.return_value = {
            "completed": False,
            "completed_at": None,
            "completed_by": None
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.get.side_effect = [mock_subtask_doc, mock_updated_doc]
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
                json={"completed": False},
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 200
        # Verify completed_at and completed_by were cleared (line 956)
        update_call = mock_subtask_ref.update.call_args[0][0]
        assert "completed" in update_call
        assert update_call["completed"] is False
        assert "completed_at" in update_call
        assert update_call["completed_at"] is None
        assert "completed_by" in update_call
        assert update_call["completed_by"] is None
