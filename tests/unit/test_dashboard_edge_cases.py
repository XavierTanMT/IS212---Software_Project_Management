"""
Unit tests for dashboard.py edge cases to achieve 100% coverage
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from backend.api.dashboard import task_to_json, enrich_task_with_timeline_status, detect_conflicts


class TestTaskToJsonEdgeCases:
    """Test edge cases in task_to_json function"""
    
    def test_priority_non_string_non_int(self):
        """Test priority that is neither string nor int defaults to Medium"""
        mock_task = Mock()
        mock_task.id = "task-123"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "priority": None,  # None is neither string nor int
            "status": "To Do"
        }
        
        result = task_to_json(mock_task)
        
        assert result["priority"] == "Medium"
    
    def test_priority_list_defaults_to_medium(self):
        """Test priority as list (non-string, non-int) defaults to Medium"""
        mock_task = Mock()
        mock_task.id = "task-456"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "priority": ["high", "low"],  # List type
            "status": "To Do"
        }
        
        result = task_to_json(mock_task)
        
        assert result["priority"] == "Medium"
    
    def test_priority_dict_defaults_to_medium(self):
        """Test priority as dict (non-string, non-int) defaults to Medium"""
        mock_task = Mock()
        mock_task.id = "task-789"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "priority": {"level": "high"},  # Dict type
            "status": "To Do"
        }
        
        result = task_to_json(mock_task)
        
        assert result["priority"] == "Medium"


class TestEnrichTaskEdgeCases:
    """Test edge cases in enrich_task_with_timeline_status"""
    
    def test_due_date_non_string_non_datetime(self):
        """Test due_date that is neither string nor datetime"""
        task = {
            "task_id": "task-123",
            "title": "Test Task",
            "status": "To Do",
            "due_date": 12345,  # Integer, not string or datetime
        }
        
        result = enrich_task_with_timeline_status(task)
        
        assert result["timeline_status"] == "invalid_date"
        assert result["is_overdue"] is False
        assert result["is_upcoming"] is False
    
    def test_due_date_list_invalid(self):
        """Test due_date as list (invalid type)"""
        task = {
            "task_id": "task-456",
            "title": "Test Task",
            "status": "To Do",
            "due_date": ["2025-01-01"],  # List, not string or datetime
        }
        
        result = enrich_task_with_timeline_status(task)
        
        assert result["timeline_status"] == "invalid_date"
        assert result["is_overdue"] is False
        assert result["is_upcoming"] is False
    
    def test_due_date_invalid_string_format(self):
        """Test due_date with invalid string format that _safe_iso_to_dt returns None"""
        task = {
            "task_id": "task-789",
            "title": "Test Task",
            "status": "To Do",
            "due_date": "not-a-valid-date",
        }
        
        result = enrich_task_with_timeline_status(task)
        
        assert result["timeline_status"] == "invalid_date"
        assert result["is_overdue"] is False
        assert result["is_upcoming"] is False
    
    def test_due_date_datetime_object(self):
        """Test due_date as datetime object"""
        future_date = datetime.now(timezone.utc) + timedelta(days=10)
        task = {
            "task_id": "task-dt1",
            "title": "Test Task",
            "status": "To Do",
            "due_date": future_date,  # Datetime object
        }
        
        result = enrich_task_with_timeline_status(task)
        
        assert result["timeline_status"] == "future"
        assert result["is_overdue"] is False
        assert result["is_upcoming"] is False


class TestDetectConflictsEdgeCases:
    """Test edge cases in detect_conflicts function"""
    
    def test_detect_conflicts_with_datetime_object(self):
        """Test conflict detection with datetime objects"""
        date1 = datetime(2025, 12, 25, 10, 0, 0, tzinfo=timezone.utc)
        date2 = datetime(2025, 12, 25, 14, 0, 0, tzinfo=timezone.utc)
        
        tasks = [
            {
                "task_id": "task-1",
                "title": "Task 1",
                "due_date": date1,
            },
            {
                "task_id": "task-2",
                "title": "Task 2",
                "due_date": date2,
            }
        ]
        
        conflicts = detect_conflicts(tasks)
        
        assert len(conflicts) == 1
        assert conflicts[0]["date"] == "2025-12-25"
        assert conflicts[0]["count"] == 2
    
    def test_detect_conflicts_with_non_string_non_datetime(self):
        """Test conflict detection skips non-string, non-datetime due dates"""
        tasks = [
            {
                "task_id": "task-1",
                "title": "Task 1",
                "due_date": "2025-12-25T10:00:00Z",
            },
            {
                "task_id": "task-2",
                "title": "Task 2",
                "due_date": 12345,  # Integer - should be skipped
            },
            {
                "task_id": "task-3",
                "title": "Task 3",
                "due_date": ["2025-12-25"],  # List - should be skipped
            }
        ]
        
        conflicts = detect_conflicts(tasks)
        
        # Should be empty since only 1 valid task on that date
        assert len(conflicts) == 0
