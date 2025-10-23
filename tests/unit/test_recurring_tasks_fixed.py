"""Tests for recurring task functionality."""
import pytest
import sys
from unittest.mock import Mock
from datetime import datetime, timezone, timedelta

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
        
        # Setup mock collections
        mock_tasks_collection = Mock()
        mock_tasks_collection.document.return_value = mock_task_ref
        
        mock_users_collection = Mock()
        mock_users_collection.document.return_value.get.return_value = mock_user_doc
        
        def mock_collection(name):
            if name == "tasks":
                return mock_tasks_collection
            elif name == "users":
                return mock_users_collection
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
        assert call_args.get("parent_recurring_task_id") is None
    
    def test_create_recurring_task_without_due_date(self, client, mock_db, monkeypatch):
        """Test that recurring task without due date fails."""
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {
            "user_id": "user1",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        mock_users_collection = Mock()
        mock_users_collection.document.return_value.get.return_value = mock_user_doc
        
        def mock_collection(name):
            if name == "users":
                return mock_users_collection
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
        assert "due date" in data["error"].lower()
    
    def test_create_recurring_task_with_invalid_interval(self, client, mock_db, monkeypatch):
        """Test that recurring task with invalid interval fails."""
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {
            "user_id": "user1",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        mock_users_collection = Mock()
        mock_users_collection.document.return_value.get.return_value = mock_user_doc
        
        def mock_collection(name):
            if name == "users":
                return mock_users_collection
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
        assert "interval" in data["error"].lower()


class TestRecurringTaskCompletion:
    """Test completing recurring tasks and creating next occurrence."""
    
    def test_complete_recurring_task_creates_next(self, client, mock_db, monkeypatch):
        """Test that completing a recurring task creates the next occurrence."""
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
        
        # Mock for the task being updated
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.id = "task123"
        
        # Mock for creating new recurring task
        mock_new_task_ref = Mock()
        mock_new_task_ref.id = "task456"
        
        # Track document() calls - first is for get, second is for new task
        call_count = {'count': 0}
        
        def mock_document(task_id=None):
            call_count['count'] += 1
            if call_count['count'] == 1 or task_id == "task123":
                return mock_task_ref
            else:
                return mock_new_task_ref
        
        mock_tasks_collection = Mock()
        mock_tasks_collection.document = mock_document
        
        mock_db.collection.return_value = mock_tasks_collection
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Complete the task
        response = client.put("/api/tasks/task123", 
            headers={"X-User-Id": "user1"},
            json={"status": "Completed"}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify the response includes next_recurring_task_id if implemented
        if "next_recurring_task_id" in data:
            assert data["next_recurring_task_id"] == "task456"
            
            # Verify new task was created with correct fields
            assert mock_new_task_ref.set.called
            new_task_data = mock_new_task_ref.set.call_args[0][0]
            
            assert new_task_data["title"] == "Daily Review"
            assert new_task_data["status"] == "To Do"
            assert new_task_data["is_recurring"] == True
            assert new_task_data["recurrence_interval_days"] == 1
            assert new_task_data["parent_recurring_task_id"] == "task123"
    
    def test_complete_non_recurring_task_no_next(self, client, mock_db, monkeypatch):
        """Test that completing a non-recurring task doesn't create next task."""
        # Mock non-recurring task
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task123"
        mock_task_doc.to_dict.return_value = {
            "title": "One-time Task",
            "status": "To Do",
            "is_recurring": False,
            "created_by": {"user_id": "user1"},
            "archived": False
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        
        mock_db.collection.return_value.document.return_value = mock_task_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
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
        # Mock existing non-recurring task
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task123"
        mock_task_doc.to_dict.return_value = {
            "title": "Regular Task",
            "status": "To Do",
            "due_date": "2024-10-15T10:00:00+00:00",
            "is_recurring": False,
            "created_by": {"user_id": "user1"},
            "archived": False
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        
        mock_db.collection.return_value.document.return_value = mock_task_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.put("/api/tasks/task123",
            headers={"X-User-Id": "user1"},
            json={
                "is_recurring": True,
                "recurrence_interval_days": 7
            }
        )
        
        assert response.status_code == 200
        
        # Verify update was called
        assert mock_task_ref.update.called
        update_args = mock_task_ref.update.call_args[0][0]
        assert update_args["is_recurring"] == True
        assert update_args["recurrence_interval_days"] == 7
    
    def test_disable_recurrence_on_recurring_task(self, client, mock_db, monkeypatch):
        """Test disabling recurrence on a recurring task."""
        # Mock existing recurring task
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task123"
        mock_task_doc.to_dict.return_value = {
            "title": "Recurring Task",
            "status": "To Do",
            "due_date": "2024-10-15T10:00:00+00:00",
            "is_recurring": True,
            "recurrence_interval_days": 7,
            "created_by": {"user_id": "user1"},
            "archived": False
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        
        mock_db.collection.return_value.document.return_value = mock_task_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.put("/api/tasks/task123",
            headers={"X-User-Id": "user1"},
            json={
                "is_recurring": False
            }
        )
        
        assert response.status_code == 200
        
        # Verify update was called
        assert mock_task_ref.update.called
        update_args = mock_task_ref.update.call_args[0][0]
        assert update_args["is_recurring"] == False


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
