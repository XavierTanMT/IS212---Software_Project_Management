"""Tests for recurring task functionality."""
import pytest
from unittest.mock import Mock
from datetime import datetime, timezone, timedelta
import sys

# Get fake_firestore from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")

from backend.api import tasks_bp
from backend.api import tasks as tasks_module


class TestRecurringTaskCreation:
    """Test creating recurring tasks."""
    
    def test_create_recurring_task_success(self, client, mock_db, monkeypatch):
        """Test successfully creating a recurring task."""
        mock_task_ref = Mock()
        mock_task_ref.id = "task123"
        
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {
            "user_id": "user1",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        def mock_collection(name):
            if name == "tasks":
                tasks_collection = Mock()
                tasks_collection.document.return_value = mock_task_ref
                return tasks_collection
            elif name == "users":
                users_collection = Mock()
                users_collection.document.return_value.get.return_value = mock_user_doc
                return users_collection
            return Mock()
        
        mock_db.collection = mock_collection
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        due_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        
        response = client.post("/api/tasks", json={
            "title": "Daily Standup",
            "description": "Team standup meeting every day",
            "priority": "Medium",
            "status": "To Do",
            "due_date": due_date,
            "created_by_id": "user1",
            "is_recurring": True,
            "recurrence_interval_days": 1
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "Daily Standup"
        assert data["is_recurring"] == True
        assert data["recurrence_interval_days"] == 1
        
        # Verify task was saved with recurring fields
        mock_task_ref.set.assert_called_once()
        call_args = mock_task_ref.set.call_args[0][0]
        assert call_args["is_recurring"] == True
        assert call_args["recurrence_interval_days"] == 1
        assert call_args["parent_recurring_task_id"] is None
    
    def test_create_recurring_task_without_due_date(self, client, mock_db, monkeypatch):
        """Test that recurring task without due date fails."""
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {
            "user_id": "user1",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        def mock_collection(name):
            if name == "users":
                users_collection = Mock()
                users_collection.document.return_value.get.return_value = mock_user_doc
                return users_collection
            return Mock()
        
        mock_db.collection = mock_collection
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post("/api/tasks", json={
            "title": "Daily Task",
            "description": "This should fail",
            "created_by_id": "user1",
            "is_recurring": True,
            "recurrence_interval_days": 1
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "must have a due date" in data["error"].lower()
    
    def test_create_recurring_task_with_invalid_interval(self, client, mock_db, monkeypatch):
        """Test that recurring task with invalid interval fails."""
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {
            "user_id": "user1",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        def mock_collection(name):
            if name == "users":
                users_collection = Mock()
                users_collection.document.return_value.get.return_value = mock_user_doc
                return users_collection
            return Mock()
        
        mock_db.collection = mock_collection
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        due_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        
        response = client.post("/api/tasks", json={
            "title": "Bad Recurring Task",
            "description": "This should fail",
            "created_by_id": "user1",
            "due_date": due_date,
            "is_recurring": True,
            "recurrence_interval_days": 0  # Invalid
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "positive interval" in data["error"].lower()


class TestRecurringTaskCompletion:
    """Test completing recurring tasks and creating next occurrence."""
    
    def test_complete_recurring_task_creates_next(self, client, mock_db, monkeypatch):
        """Test that completing a recurring task creates the next occurrence."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        original_due_date = "2024-10-01T10:00:00+00:00"
        
        # Mock existing recurring task
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task123"
        mock_task_doc.to_dict.return_value = {
            "title": "Daily Review",
            "description": "Review daily metrics",
            "priority": "Medium",
            "status": "To Do",
            "due_date": original_due_date,
            "is_recurring": True,
            "recurrence_interval_days": 1,
            "created_by": {"user_id": "user1", "name": "Test User"},
            "assigned_to": None,
            "project_id": None,
            "labels": ["review"],
            "archived": False
        }
        
        # Mock for getting the task
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        
        # Mock for creating new task
        mock_new_task_ref = Mock()
        mock_new_task_ref.id = "task456"
        
        def mock_collection(collection_name):
            mock_collection_obj = Mock()
            if collection_name == "tasks":
                # First call is for document(task_id).get()
                # Second call is for document() to create new task
                mock_collection_obj.document.side_effect = [
                    mock_task_ref,  # For update
                    mock_new_task_ref  # For new task creation
                ]
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        # Complete the task
        response = client.put("/api/tasks/task123", 
            headers={"X-User-Id": "user1"},
            json={"status": "Completed"}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify next task was created
        assert "next_recurring_task_id" in data
        assert data["next_recurring_task_id"] == "task456"
        
        # Verify new task was created with correct due date
        mock_new_task_ref.set.assert_called_once()
        new_task_data = mock_new_task_ref.set.call_args[0][0]
        
        assert new_task_data["title"] == "Daily Review"
        assert new_task_data["status"] == "To Do"
        assert new_task_data["is_recurring"] == True
        assert new_task_data["recurrence_interval_days"] == 1
        assert new_task_data["parent_recurring_task_id"] == "task123"
        
        # Verify due date is original + 1 day
        expected_due = datetime.fromisoformat(original_due_date.replace("Z", "+00:00")) + timedelta(days=1)
        actual_due = datetime.fromisoformat(new_task_data["due_date"].replace("Z", "+00:00"))
        assert abs((actual_due - expected_due).total_seconds()) < 1
    
    def test_complete_non_recurring_task_no_next(self, client, mock_db, monkeypatch):
        """Test that completing a non-recurring task doesn't create next task."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock non-recurring task
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task123"
        mock_task_doc.to_dict.return_value = {
            "title": "One-time Task",
            "status": "To Do",
            "is_recurring": False,
            "created_by": {"user_id": "user1"}
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_db.collection.return_value.document.return_value = mock_task_ref
        
        response = client.put("/api/tasks/task123",
            headers={"X-User-Id": "user1"},
            json={"status": "Completed"}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify no next task was created
        assert "next_recurring_task_id" not in data


class TestRecurringTaskUpdate:
    """Test updating recurring task settings."""
    
    def test_enable_recurrence_on_existing_task(self, client, mock_db, monkeypatch):
        """Test enabling recurrence on an existing task."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock existing non-recurring task
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "title": "Regular Task",
            "status": "To Do",
            "due_date": "2024-10-15T10:00:00+00:00",
            "is_recurring": False,
            "created_by": {"user_id": "user1"}
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_db.collection.return_value.document.return_value = mock_task_ref
        
        response = client.put("/api/tasks/task123",
            headers={"X-User-Id": "user1"},
            json={
                "is_recurring": True,
                "recurrence_interval_days": 7
            }
        )
        
        assert response.status_code == 200
        
        # Verify update was called with recurring fields
        mock_task_ref.update.assert_called_once()
        update_args = mock_task_ref.update.call_args[0][0]
        assert update_args["is_recurring"] == True
        assert update_args["recurrence_interval_days"] == 7
    
    def test_disable_recurrence_on_recurring_task(self, client, mock_db, monkeypatch):
        """Test disabling recurrence on a recurring task."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock existing recurring task
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "title": "Recurring Task",
            "status": "To Do",
            "due_date": "2024-10-15T10:00:00+00:00",
            "is_recurring": True,
            "recurrence_interval_days": 7,
            "created_by": {"user_id": "user1"}
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_db.collection.return_value.document.return_value = mock_task_ref
        
        response = client.put("/api/tasks/task123",
            headers={"X-User-Id": "user1"},
            json={
                "is_recurring": False
            }
        )
        
        assert response.status_code == 200
        
        # Verify update was called
        mock_task_ref.update.assert_called_once()
        update_args = mock_task_ref.update.call_args[0][0]
        assert update_args["is_recurring"] == False


class TestOverdueRecurringTask:
    """Test overdue recurring task behavior."""
    
    def test_overdue_recurring_task_calculates_from_original(self, client, mock_db, monkeypatch):
        """Test that overdue recurring tasks calculate next due date from original due date."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Original due date was Sep 29, but marked complete on Oct 1
        original_due_date = "2024-09-29T10:00:00+00:00"
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task_overdue"
        mock_task_doc.to_dict.return_value = {
            "title": "Daily Task",
            "status": "To Do",
            "due_date": original_due_date,
            "is_recurring": True,
            "recurrence_interval_days": 1,
            "created_by": {"user_id": "user1"},
            "assigned_to": None,
            "project_id": None,
            "labels": [],
            "archived": False
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        
        mock_new_task_ref = Mock()
        mock_new_task_ref.id = "task_next"
        
        def mock_collection(collection_name):
            mock_collection_obj = Mock()
            if collection_name == "tasks":
                mock_collection_obj.document.side_effect = [
                    mock_task_ref,
                    mock_new_task_ref
                ]
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        # Mark as completed on Oct 1
        response = client.put("/api/tasks/task_overdue",
            headers={"X-User-Id": "user1"},
            json={"status": "Completed"}
        )
        
        assert response.status_code == 200
        
        # Verify new task due date is Sep 30 (original + 1 day), not Oct 2 (today + 1)
        mock_new_task_ref.set.assert_called_once()
        new_task_data = mock_new_task_ref.set.call_args[0][0]
        
        expected_due = datetime.fromisoformat(original_due_date.replace("Z", "+00:00")) + timedelta(days=1)
        actual_due = datetime.fromisoformat(new_task_data["due_date"].replace("Z", "+00:00"))
        
        # Should be Sep 30, not Oct 2
        assert expected_due.day == 30
        assert actual_due.day == 30
        assert abs((actual_due - expected_due).total_seconds()) < 1


class TestRecurringTaskSerialization:
    """Test that recurring task fields are properly serialized."""
    
    def test_task_to_json_includes_recurring_fields(self):
        """Test that task_to_json includes recurring fields."""
        mock_doc = Mock()
        mock_doc.id = "task123"
        mock_doc.to_dict.return_value = {
            "title": "Test",
            "is_recurring": True,
            "recurrence_interval_days": 7,
            "parent_recurring_task_id": "task_parent"
        }
        
        result = tasks_module.task_to_json(mock_doc)
        
        assert result["is_recurring"] == True
        assert result["recurrence_interval_days"] == 7
        assert result["parent_recurring_task_id"] == "task_parent"
    
    def test_task_to_json_defaults_for_non_recurring(self):
        """Test that non-recurring tasks have proper defaults."""
        mock_doc = Mock()
        mock_doc.id = "task123"
        mock_doc.to_dict.return_value = {
            "title": "Test"
        }
        
        result = tasks_module.task_to_json(mock_doc)
        
        assert result["is_recurring"] == False
        assert result["recurrence_interval_days"] is None
        assert result["parent_recurring_task_id"] is None
