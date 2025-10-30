import sys
import os
from unittest.mock import Mock
import pytest
from datetime import datetime, timezone

# Get fake_firestore from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")

from flask import Flask
from backend.api import dashboard_bp
from backend.api import dashboard as dashboard_module


# app and client fixtures provided by conftest.py


class TestTaskToJson:
    """Test the task_to_json helper function."""
    
    def test_task_to_json_with_all_fields(self):
        """Test task_to_json with all fields present."""
        mock_doc = Mock()
        mock_doc.id = "task123"
        mock_doc.to_dict = Mock(return_value={
            "title": "Test Task",
            "description": "Test Description",
            "priority": "High",
            "status": "In Progress",
            "due_date": "2025-12-31T23:59:59+00:00",
            "created_at": "2025-01-01T00:00:00+00:00",
            "created_by": {"user_id": "user1", "name": "John"},
            "assigned_to": {"user_id": "user2", "name": "Jane"},
        })
        
        result = dashboard_module.task_to_json(mock_doc)
        
        assert result["task_id"] == "task123"
        assert result["title"] == "Test Task"
        assert result["description"] == "Test Description"
        assert result["priority"] == "High"
        assert result["status"] == "In Progress"
        assert result["due_date"] == "2025-12-31T23:59:59+00:00"
        assert result["created_at"] == "2025-01-01T00:00:00+00:00"
        assert result["created_by"] == {"user_id": "user1", "name": "John"}
        assert result["assigned_to"] == {"user_id": "user2", "name": "Jane"}
    
    def test_task_to_json_with_missing_optional_fields(self):
        """Test task_to_json with missing optional fields uses defaults."""
        mock_doc = Mock()
        mock_doc.id = "task456"
        mock_doc.to_dict = Mock(return_value={
            "title": "Minimal Task",
        })
        
        result = dashboard_module.task_to_json(mock_doc)
        
        assert result["task_id"] == "task456"
        assert result["title"] == "Minimal Task"
        assert result["description"] is None
        assert result["priority"] == "Medium"  # Default
        assert result["status"] == "To Do"  # Default
        assert result["due_date"] is None
        assert result["created_at"] is None
        assert result["created_by"] is None
        assert result["assigned_to"] is None
    
    def test_task_to_json_with_partial_fields(self):
        """Test task_to_json with some fields missing."""
        mock_doc = Mock()
        mock_doc.id = "task789"
        mock_doc.to_dict = Mock(return_value={
            "title": "Partial Task",
            "status": "Completed",
            "created_at": "2025-06-15T10:30:00+00:00",
        })
        
        result = dashboard_module.task_to_json(mock_doc)
        
        assert result["task_id"] == "task789"
        assert result["title"] == "Partial Task"
        assert result["status"] == "Completed"
        assert result["priority"] == "Medium"  # Default when missing
        assert result["created_at"] == "2025-06-15T10:30:00+00:00"


class TestSafeIsoToDt:
    """Test the _safe_iso_to_dt helper function."""
    
    def test_safe_iso_to_dt_valid_iso_string(self):
        """Test converting a valid ISO string to datetime."""
        iso_string = "2025-10-19T12:30:00+00:00"
        result = dashboard_module._safe_iso_to_dt(iso_string)
        
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 19
        assert result.hour == 12
        assert result.minute == 30
    
    def test_safe_iso_to_dt_with_z_suffix(self):
        """Test converting ISO string with Z suffix."""
        iso_string = "2025-10-19T12:30:00Z"
        result = dashboard_module._safe_iso_to_dt(iso_string)
        
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 19
    
    def test_safe_iso_to_dt_empty_string(self):
        """Test that empty string returns None."""
        result = dashboard_module._safe_iso_to_dt("")
        assert result is None
    
    def test_safe_iso_to_dt_none_value(self):
        """Test that None returns None."""
        result = dashboard_module._safe_iso_to_dt(None)
        assert result is None
    
    def test_safe_iso_to_dt_invalid_string(self):
        """Test that invalid string returns None."""
        result = dashboard_module._safe_iso_to_dt("not a valid date")
        assert result is None
    
    def test_safe_iso_to_dt_malformed_iso(self):
        """Test that malformed ISO string returns None."""
        result = dashboard_module._safe_iso_to_dt("2025-13-45T99:99:99")
        assert result is None
    
    def test_safe_iso_to_dt_naive_datetime_becomes_aware(self):
        """Test that naive datetime (without timezone) becomes timezone-aware with UTC."""
        # ISO string without timezone info
        iso_string = "2025-10-19T12:30:00"
        result = dashboard_module._safe_iso_to_dt(iso_string)
        
        assert isinstance(result, datetime)
        assert result.tzinfo is not None  # Should be timezone-aware
        assert result.tzinfo == timezone.utc  # Should be UTC
        # Verify it can be compared with timezone-aware datetime
        now = datetime.now(timezone.utc)
        # This should not raise TypeError
        _ = result < now  # noqa


class TestUserDashboard:
    """Test the user_dashboard endpoint."""
    
    def test_user_dashboard_user_not_found(self, client, mock_db, monkeypatch):
        """Test dashboard returns 404 when user doesn't exist."""
        # Mock user document that doesn't exist
        mock_user_doc = Mock()
        mock_user_doc.exists = False
        
        mock_user_collection = Mock()
        mock_user_collection.document = Mock(return_value=Mock(get=Mock(return_value=mock_user_doc)))
        
        def collection_side_effect(name):
            if name == "users":
                return mock_user_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/users/nonexistent_user/dashboard")
        
        assert response.status_code == 404
        data = response.get_json()
        assert data is not None
        assert "error" in data
        assert data["error"] == "User not found"
    
    def test_user_dashboard_no_tasks(self, client, mock_db, monkeypatch):
        """Test dashboard with user that has no tasks."""
        # Mock user document that exists
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        
        mock_user_collection = Mock()
        mock_user_collection.document = Mock(return_value=Mock(get=Mock(return_value=mock_user_doc)))
        
        # Mock empty task collections
        mock_created_where = Mock()
        mock_created_where.stream = Mock(return_value=[])
        
        mock_assigned_where = Mock()
        mock_assigned_where.stream = Mock(return_value=[])
        
        mock_task_collection = Mock()
        def where_side_effect(field=None, op=None, value=None, filter=None):
            # Handle both old and new FieldFilter syntax
            if filter is not None:
                field = getattr(filter, "field_path", field)
                value = getattr(filter, "value", value)
            if "created_by" in field:
                return mock_created_where
            elif "assigned_to" in field:
                return mock_assigned_where
            return Mock()
        
        mock_task_collection.where = Mock(side_effect=where_side_effect)
        
        def collection_side_effect(name):
            if name == "users":
                return mock_user_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/users/user123/dashboard")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify statistics
        assert data["statistics"]["total_created"] == 0
        assert data["statistics"]["total_assigned"] == 0
        assert data["statistics"]["status_breakdown"] == {}
        assert data["statistics"]["priority_breakdown"] == {}
        assert data["statistics"]["overdue_count"] == 0
        
        # Verify empty task lists
        assert data["recent_created_tasks"] == []
        assert data["recent_assigned_tasks"] == []
    
    def test_user_dashboard_with_created_tasks(self, client, mock_db, monkeypatch):
        """Test dashboard with created tasks."""
        # Mock user document
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        
        # Mock created tasks
        mock_task1 = Mock()
        mock_task1.id = "task1"
        mock_task1.to_dict = Mock(return_value={
            "title": "Task 1",
            "priority": "High",
            "status": "To Do",
            "created_at": "2025-10-19T10:00:00+00:00",
            "created_by": {"user_id": "user123"},
            "assigned_to": {"user_id": "user456"},
        })
        
        mock_task2 = Mock()
        mock_task2.id = "task2"
        mock_task2.to_dict = Mock(return_value={
            "title": "Task 2",
            "priority": "Medium",
            "status": "In Progress",
            "created_at": "2025-10-18T10:00:00+00:00",
            "created_by": {"user_id": "user123"},
        })
        
        mock_user_collection = Mock()
        mock_user_collection.document = Mock(return_value=Mock(get=Mock(return_value=mock_user_doc)))
        
        # Mock task collections
        mock_created_where = Mock()
        mock_created_where.stream = Mock(return_value=[mock_task1, mock_task2])
        
        mock_assigned_where = Mock()
        mock_assigned_where.stream = Mock(return_value=[])
        
        mock_task_collection = Mock()
        def where_side_effect(field=None, op=None, value=None, filter=None):
            # Handle both old and new FieldFilter syntax
            if filter is not None:
                field = getattr(filter, "field_path", field)
                value = getattr(filter, "value", value)
            if "created_by" in field:
                return mock_created_where
            elif "assigned_to" in field:
                return mock_assigned_where
            return Mock()
        
        mock_task_collection.where = Mock(side_effect=where_side_effect)
        
        def collection_side_effect(name):
            if name == "users":
                return mock_user_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/users/user123/dashboard")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify statistics
        assert data["statistics"]["total_created"] == 2
        assert data["statistics"]["total_assigned"] == 0
        assert data["statistics"]["status_breakdown"] == {"To Do": 1, "In Progress": 1}
        assert data["statistics"]["priority_breakdown"] == {"High": 1, "Medium": 1}
        
        # Verify tasks are sorted by created_at desc (task1 before task2)
        assert len(data["recent_created_tasks"]) == 2
        assert data["recent_created_tasks"][0]["task_id"] == "task1"
        assert data["recent_created_tasks"][1]["task_id"] == "task2"
    
    def test_user_dashboard_with_assigned_tasks(self, client, mock_db, monkeypatch):
        """Test dashboard with assigned tasks."""
        # Mock user document
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        
        # Mock assigned tasks
        mock_task1 = Mock()
        mock_task1.id = "assigned1"
        mock_task1.to_dict = Mock(return_value={
            "title": "Assigned Task 1",
            "priority": "Low",
            "status": "Completed",
            "created_at": "2025-10-17T10:00:00+00:00",
            "assigned_to": {"user_id": "user123"},
        })
        
        mock_user_collection = Mock()
        mock_user_collection.document = Mock(return_value=Mock(get=Mock(return_value=mock_user_doc)))
        
        # Mock task collections
        mock_created_where = Mock()
        mock_created_where.stream = Mock(return_value=[])
        
        mock_assigned_where = Mock()
        mock_assigned_where.stream = Mock(return_value=[mock_task1])
        
        mock_task_collection = Mock()
        def where_side_effect(field=None, op=None, value=None, filter=None):
            # Handle both old and new FieldFilter syntax
            if filter is not None:
                field = getattr(filter, "field_path", field)
                value = getattr(filter, "value", value)
            if "created_by" in field:
                return mock_created_where
            elif "assigned_to" in field:
                return mock_assigned_where
            return Mock()
        
        mock_task_collection.where = Mock(side_effect=where_side_effect)
        
        def collection_side_effect(name):
            if name == "users":
                return mock_user_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/users/user123/dashboard")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify statistics (based on created tasks, which is 0)
        assert data["statistics"]["total_created"] == 0
        assert data["statistics"]["total_assigned"] == 1
        
        # Verify assigned tasks
        assert len(data["recent_assigned_tasks"]) == 1
        assert data["recent_assigned_tasks"][0]["task_id"] == "assigned1"
    
    def test_user_dashboard_with_overdue_tasks(self, client, mock_db, monkeypatch):
        """Test dashboard correctly counts overdue tasks."""
        # Mock user document
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        
        # Create tasks with different due dates
        # Overdue task (past date, not completed)
        mock_overdue = Mock()
        mock_overdue.id = "overdue1"
        mock_overdue.to_dict = Mock(return_value={
            "title": "Overdue Task",
            "priority": "High",
            "status": "To Do",
            "due_date": "2020-01-01T00:00:00+00:00",  # Past date
            "created_at": "2025-10-01T10:00:00+00:00",
            "created_by": {"user_id": "user123"},
        })
        
        # Completed overdue task (should not count as overdue)
        mock_completed_late = Mock()
        mock_completed_late.id = "completed1"
        mock_completed_late.to_dict = Mock(return_value={
            "title": "Completed Late",
            "priority": "Medium",
            "status": "Completed",
            "due_date": "2020-01-01T00:00:00+00:00",  # Past date but completed
            "created_at": "2025-10-02T10:00:00+00:00",
            "created_by": {"user_id": "user123"},
        })
        
        # Future task (not overdue)
        mock_future = Mock()
        mock_future.id = "future1"
        mock_future.to_dict = Mock(return_value={
            "title": "Future Task",
            "priority": "Low",
            "status": "In Progress",
            "due_date": "2030-12-31T23:59:59+00:00",  # Future date
            "created_at": "2025-10-03T10:00:00+00:00",
            "created_by": {"user_id": "user123"},
        })
        
        # Task with no due date (not overdue)
        mock_no_due = Mock()
        mock_no_due.id = "nodue1"
        mock_no_due.to_dict = Mock(return_value={
            "title": "No Due Date",
            "priority": "Medium",
            "status": "To Do",
            "created_at": "2025-10-04T10:00:00+00:00",
            "created_by": {"user_id": "user123"},
        })
        
        mock_user_collection = Mock()
        mock_user_collection.document = Mock(return_value=Mock(get=Mock(return_value=mock_user_doc)))
        
        # Mock task collections
        mock_created_where = Mock()
        mock_created_where.stream = Mock(return_value=[mock_overdue, mock_completed_late, mock_future, mock_no_due])
        
        mock_assigned_where = Mock()
        mock_assigned_where.stream = Mock(return_value=[])
        
        mock_task_collection = Mock()
        def where_side_effect(field=None, op=None, value=None, filter=None):
            # Handle both old and new FieldFilter syntax
            if filter is not None:
                field = getattr(filter, "field_path", field)
                value = getattr(filter, "value", value)
            if "created_by" in field:
                return mock_created_where
            elif "assigned_to" in field:
                return mock_assigned_where
            return Mock()
        
        mock_task_collection.where = Mock(side_effect=where_side_effect)
        
        def collection_side_effect(name):
            if name == "users":
                return mock_user_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/users/user123/dashboard")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Only one overdue task (the first one that's not completed)
        assert data["statistics"]["overdue_count"] == 1
        assert data["statistics"]["total_created"] == 4
        assert data["statistics"]["status_breakdown"] == {"To Do": 2, "Completed": 1, "In Progress": 1}
        assert data["statistics"]["priority_breakdown"] == {"High": 1, "Medium": 2, "Low": 1}
    
    def test_user_dashboard_limits_to_5_recent_tasks(self, client, mock_db, monkeypatch):
        """Test dashboard only returns 5 most recent tasks."""
        # Mock user document
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        
        # Create 7 tasks with different created_at times
        mock_tasks = []
        for i in range(7):
            mock_task = Mock()
            mock_task.id = f"task{i}"
            mock_task.to_dict = Mock(return_value={
                "title": f"Task {i}",
                "priority": "Medium",
                "status": "To Do",
                "created_at": f"2025-10-{19-i:02d}T10:00:00+00:00",  # Descending dates
                "created_by": {"user_id": "user123"},
            })
            mock_tasks.append(mock_task)
        
        mock_user_collection = Mock()
        mock_user_collection.document = Mock(return_value=Mock(get=Mock(return_value=mock_user_doc)))
        
        # Mock task collections
        mock_created_where = Mock()
        mock_created_where.stream = Mock(return_value=mock_tasks)
        
        mock_assigned_where = Mock()
        mock_assigned_where.stream = Mock(return_value=mock_tasks)  # Same for assigned
        
        mock_task_collection = Mock()
        def where_side_effect(field=None, op=None, value=None, filter=None):
            # Handle both old and new FieldFilter syntax
            if filter is not None:
                field = getattr(filter, "field_path", field)
                value = getattr(filter, "value", value)
            if "created_by" in field:
                return mock_created_where
            elif "assigned_to" in field:
                return mock_assigned_where
            return Mock()
        
        mock_task_collection.where = Mock(side_effect=where_side_effect)
        
        def collection_side_effect(name):
            if name == "users":
                return mock_user_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/users/user123/dashboard")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Should only return 5 tasks
        assert len(data["recent_created_tasks"]) == 5
        assert len(data["recent_assigned_tasks"]) == 5
        
        # Should be the 5 most recent (task0 through task4)
        assert data["recent_created_tasks"][0]["task_id"] == "task0"
        assert data["recent_created_tasks"][4]["task_id"] == "task4"
    
    def test_user_dashboard_sorting_with_null_created_at(self, client, mock_db, monkeypatch):
        """Test dashboard handles tasks with null/missing created_at dates."""
        # Mock user document
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        
        # Task with valid created_at
        mock_task_valid = Mock()
        mock_task_valid.id = "valid"
        mock_task_valid.to_dict = Mock(return_value={
            "title": "Valid Date",
            "priority": "High",
            "status": "To Do",
            "created_at": "2025-10-19T10:00:00+00:00",
            "created_by": {"user_id": "user123"},
        })
        
        # Task with null created_at
        mock_task_null = Mock()
        mock_task_null.id = "null"
        mock_task_null.to_dict = Mock(return_value={
            "title": "Null Date",
            "priority": "Medium",
            "status": "To Do",
            "created_at": None,
            "created_by": {"user_id": "user123"},
        })
        
        # Task with missing created_at
        mock_task_missing = Mock()
        mock_task_missing.id = "missing"
        mock_task_missing.to_dict = Mock(return_value={
            "title": "Missing Date",
            "priority": "Low",
            "status": "To Do",
            "created_by": {"user_id": "user123"},
        })
        
        mock_user_collection = Mock()
        mock_user_collection.document = Mock(return_value=Mock(get=Mock(return_value=mock_user_doc)))
        
        # Mock task collections
        mock_created_where = Mock()
        mock_created_where.stream = Mock(return_value=[mock_task_valid, mock_task_null, mock_task_missing])
        
        mock_assigned_where = Mock()
        mock_assigned_where.stream = Mock(return_value=[])
        
        mock_task_collection = Mock()
        def where_side_effect(field=None, op=None, value=None, filter=None):
            # Handle both old and new FieldFilter syntax
            if filter is not None:
                field = getattr(filter, "field_path", field)
                value = getattr(filter, "value", value)
            if "created_by" in field:
                return mock_created_where
            elif "assigned_to" in field:
                return mock_assigned_where
            return Mock()
        
        mock_task_collection.where = Mock(side_effect=where_side_effect)
        
        def collection_side_effect(name):
            if name == "users":
                return mock_user_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/users/user123/dashboard")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Should have all 3 tasks
        assert data["statistics"]["total_created"] == 3
        
        # Valid date should be first, null/missing should be last
        assert data["recent_created_tasks"][0]["task_id"] == "valid"
        # null and missing can be in any order after valid


class TestBlueprintRegistration:
    """Test that the blueprint is properly configured."""
    
    def test_blueprint_url_prefix(self):
        """Test that the blueprint has the correct URL prefix."""
        assert dashboard_bp.url_prefix == "/api"
    
    def test_blueprint_name(self):
        """Test that the blueprint has the correct name."""
        assert dashboard_bp.name == "dashboard"


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_dashboard_with_invalid_due_date(self, client, mock_db, monkeypatch):
        """Test dashboard handles tasks with invalid due_date strings."""
        # Mock user document
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        
        # Task with invalid due date
        mock_task = Mock()
        mock_task.id = "invalid_due"
        mock_task.to_dict = Mock(return_value={
            "title": "Invalid Due Date",
            "priority": "High",
            "status": "To Do",
            "due_date": "not-a-date",  # Invalid date
            "created_at": "2025-10-19T10:00:00+00:00",
            "created_by": {"user_id": "user123"},
        })
        
        mock_user_collection = Mock()
        mock_user_collection.document = Mock(return_value=Mock(get=Mock(return_value=mock_user_doc)))
        
        mock_created_where = Mock()
        mock_created_where.stream = Mock(return_value=[mock_task])
        
        mock_assigned_where = Mock()
        mock_assigned_where.stream = Mock(return_value=[])
        
        mock_task_collection = Mock()
        def where_side_effect(field=None, op=None, value=None, filter=None):
            # Handle both old and new FieldFilter syntax
            if filter is not None:
                field = getattr(filter, "field_path", field)
                value = getattr(filter, "value", value)
            if "created_by" in field:
                return mock_created_where
            elif "assigned_to" in field:
                return mock_assigned_where
            return Mock()
        
        mock_task_collection.where = Mock(side_effect=where_side_effect)
        
        def collection_side_effect(name):
            if name == "users":
                return mock_user_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/users/user123/dashboard")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Invalid due date should not crash, should not count as overdue
        assert data["statistics"]["overdue_count"] == 0
    
    def test_dashboard_response_structure(self, client, mock_db, monkeypatch):
        """Test that dashboard response has correct structure."""
        # Mock user document
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        
        mock_user_collection = Mock()
        mock_user_collection.document = Mock(return_value=Mock(get=Mock(return_value=mock_user_doc)))
        
        mock_created_where = Mock()
        mock_created_where.stream = Mock(return_value=[])
        
        mock_assigned_where = Mock()
        mock_assigned_where.stream = Mock(return_value=[])
        
        mock_task_collection = Mock()
        def where_side_effect(field=None, op=None, value=None, filter=None):
            # Handle both old and new FieldFilter syntax
            if filter is not None:
                field = getattr(filter, "field_path", field)
                value = getattr(filter, "value", value)
            if "created_by" in field:
                return mock_created_where
            elif "assigned_to" in field:
                return mock_assigned_where
            return Mock()
        
        mock_task_collection.where = Mock(side_effect=where_side_effect)
        
        def collection_side_effect(name):
            if name == "users":
                return mock_user_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/users/user123/dashboard")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify all required keys are present
        assert "statistics" in data
        assert "recent_created_tasks" in data
        assert "recent_assigned_tasks" in data
        
        # Verify statistics structure
        stats = data["statistics"]
        assert "total_created" in stats
        assert "total_assigned" in stats
        assert "status_breakdown" in stats
        assert "priority_breakdown" in stats
        assert "overdue_count" in stats


class TestDashboardTimelineMode:
    """Test timeline mode view to achieve 100% coverage"""
    
    def test_dashboard_with_timeline_mode(self, client, mock_db, monkeypatch):
        """Test dashboard with view_mode=timeline includes timeline data"""
        from datetime import datetime, timezone, timedelta
        
        now = datetime.now(timezone.utc)
        
        # Mock user doc
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"user_id": "user123", "name": "Test User"}
        
        # Mock tasks with various due dates for timeline grouping
        overdue_task = Mock()
        overdue_task.id = "task1"
        overdue_task.to_dict.return_value = {
            "title": "Overdue Task",
            "status": "To Do",
            "priority": 5,
            "due_date": (now - timedelta(days=1)).isoformat(),
            "created_by": {"user_id": "user123", "name": "Test User"},
            "assigned_to": None,
            "archived": False
        }
        
        today_task = Mock()
        today_task.id = "task2"
        today_task.to_dict.return_value = {
            "title": "Today Task",
            "status": "To Do",
            "priority": 7,
            "due_date": (now + timedelta(hours=5)).isoformat(),
            "created_by": {"user_id": "user123", "name": "Test User"},
            "assigned_to": None,
            "archived": False
        }
        
        future_task = Mock()
        future_task.id = "task3"
        future_task.to_dict.return_value = {
            "title": "Future Task",
            "status": "To Do",
            "priority": 3,
            "due_date": (now + timedelta(days=10)).isoformat(),
            "created_by": {"user_id": "user123", "name": "Test User"},
            "assigned_to": None,
            "archived": False
        }
        
        # Mock conflicts - two tasks on same date
        conflict_task1 = Mock()
        conflict_task1.id = "task4"
        same_date = (now + timedelta(days=15)).isoformat()
        conflict_task1.to_dict.return_value = {
            "title": "Conflict Task 1",
            "status": "To Do",
            "priority": 5,
            "due_date": same_date,
            "created_by": {"user_id": "user123", "name": "Test User"},
            "assigned_to": None,
            "archived": False
        }
        
        conflict_task2 = Mock()
        conflict_task2.id = "task5"
        conflict_task2.to_dict.return_value = {
            "title": "Conflict Task 2",
            "status": "To Do",
            "priority": 6,
            "due_date": same_date,
            "created_by": {"user_id": "user123", "name": "Test User"},
            "assigned_to": None,
            "archived": False
        }
        
        def collection_side_effect(col_name):
            mock_collection = Mock()
            if col_name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_user_doc
                mock_collection.document.return_value = mock_doc_ref
            elif col_name == "tasks":
                mock_query = Mock()
                mock_query.where.return_value.stream.return_value = [
                    overdue_task, today_task, future_task, conflict_task1, conflict_task2
                ]
                mock_collection.where = mock_query.where
            return mock_collection
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Request with timeline mode
        response = client.get("/api/users/user123/dashboard?view_mode=timeline")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify timeline data is present
        assert "timeline" in data
        assert "conflicts" in data
        assert "timeline_statistics" in data
        
        # Verify timeline structure
        timeline = data["timeline"]
        assert "overdue" in timeline
        assert "today" in timeline
        assert "this_week" in timeline
        assert "future" in timeline
        assert "no_due_date" in timeline
        
        # Verify timeline_statistics
        timeline_stats = data["timeline_statistics"]
        assert "total_tasks" in timeline_stats
        assert "overdue_count" in timeline_stats
        assert "today_count" in timeline_stats
        assert "this_week_count" in timeline_stats
        assert "future_count" in timeline_stats
        assert "no_due_date_count" in timeline_stats
        assert "conflict_count" in timeline_stats
        
        # Verify conflicts detected (2 tasks on same date)
        conflicts = data["conflicts"]
        assert len(conflicts) >= 1  # At least one conflict
        assert conflicts[0]["count"] == 2  # Two tasks on same date

