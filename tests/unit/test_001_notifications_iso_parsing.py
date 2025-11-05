"""
Additional branch coverage tests for remaining missing branches in notifications.py
These tests target the specific ISO date parsing edge cases
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta
import sys

fake_firestore = sys.modules.get("firebase_admin.firestore")


class TestCheckDeadlinesIsoParsing:
    """Test ISO date parsing branches in check_deadlines"""
    
    def test_check_deadlines_sample_due_matching_regex_success(self, client, mock_db):
        """Branch 137->139: sample_due matches regex and ISO parsing succeeds"""
        mock_task = Mock()
        # Exact minute format that matches regex
        mock_task.to_dict.return_value = {"due_date": "2025-01-15T14:30"}
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([mock_task])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "users":
                return Mock(stream=Mock(return_value=[]))
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.post(
            "/api/notifications/check-deadlines",
            query_string={
                "start_iso": "2025-01-15T00:00:00+00:00",
                "end_iso": "2025-01-16T00:00:00+00:00"
            }
        )
        
        assert response.status_code == 200
    
    def test_check_deadlines_no_sample_task(self, client, mock_db):
        """Branch 135->137: no sample task found (sample is None)"""
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                # Empty iterator - no tasks
                mock_tasks.limit.return_value.stream.return_value = iter([])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "users":
                return Mock(stream=Mock(return_value=[]))
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.post(
            "/api/notifications/check-deadlines",
            query_string={
                "start_iso": "2025-01-15T00:00:00+00:00",
                "end_iso": "2025-01-16T00:00:00+00:00"
            }
        )
        
        assert response.status_code == 200
    
    def test_check_deadlines_sample_due_not_matching_regex(self, client, mock_db):
        """Branch 135->137: sample_due doesn't match minute regex pattern (line 137->else 152)"""
        mock_task = Mock()
        # Use a different format that won't match the regex
        mock_task.to_dict.return_value = {"due_date": "2025-01-15"}  # Date only, no time
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([mock_task])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "users":
                return Mock(stream=Mock(return_value=[]))
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.post(
            "/api/notifications/check-deadlines",
            query_string={
                "start_iso": "2025-01-15T00:00:00+00:00",
                "end_iso": "2025-01-16T00:00:00+00:00"
            }
        )
        
        assert response.status_code == 200
    
    def test_check_deadlines_sample_due_full_iso_format(self, client, mock_db):
        """Branch: sample_due is full ISO format (not matching minute pattern)"""
        mock_task = Mock()
        # Full ISO with seconds and timezone
        mock_task.to_dict.return_value = {"due_date": "2025-01-15T14:30:45+00:00"}
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([mock_task])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "users":
                return Mock(stream=Mock(return_value=[]))
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200
    
    def test_check_deadlines_sample_due_not_string(self, client, mock_db):
        """Branch 135->137: sample_due is not a string (line 137->else 152)"""
        mock_task = Mock()
        # due_date is a number instead of string
        mock_task.to_dict.return_value = {"due_date": 1234567890}
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([mock_task])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "users":
                return Mock(stream=Mock(return_value=[]))
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200
    
    def test_check_deadlines_per_user_with_user_id_field(self, client, mock_db):
        """Branch 243-246: user has user_id field in document"""
        mock_user = Mock()
        mock_user.id = "user_doc_id"
        mock_user.to_dict.return_value = {"user_id": "custom_user_123"}
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([Mock()])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "users":
                return Mock(stream=Mock(return_value=[mock_user]))
        
        mock_db.collection.side_effect = mock_collection
        
        with patch('backend.api.notifications._notify_user_due_tasks', return_value=0) as mock_notify:
            response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200
        # Should have called with the user_id from to_dict
        mock_notify.assert_called()
    
    def test_check_deadlines_per_user_with_empty_user_id(self, client, mock_db):
        """Branch 244-245: user has no user_id, skip"""
        mock_user = Mock()
        mock_user.id = ""
        mock_user.to_dict.return_value = {}  # No user_id field
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([Mock()])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "users":
                return Mock(stream=Mock(return_value=[mock_user]))
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200
    
    def test_check_deadlines_per_user_uses_doc_id(self, client, mock_db):
        """Branch 243: user_id from to_dict is empty, use document id"""
        mock_user = Mock()
        mock_user.id = "doc_id_123"
        mock_user.to_dict.return_value = {"user_id": ""}  # Empty string
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([Mock()])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "users":
                return Mock(stream=Mock(return_value=[mock_user]))
        
        mock_db.collection.side_effect = mock_collection
        
        with patch('backend.api.notifications._notify_user_due_tasks', return_value=0) as mock_notify:
            response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200
        # Should use the doc id
        mock_notify.assert_called()
    
    def test_check_deadlines_iso_parse_exception(self, client, mock_db):
        """Lines 149-152: Exception when parsing ISO dates"""
        mock_task = Mock()
        # Has minute format to trigger the parsing code
        mock_task.to_dict.return_value = {"due_date": "2025-01-15T14:30"}
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([mock_task])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "users":
                return Mock(stream=Mock(return_value=[]))
        
        mock_db.collection.side_effect = mock_collection
        
        # Pass malformed ISO strings that will fail fromisoformat()
        response = client.post(
            "/api/notifications/check-deadlines",
            query_string={
                "start_iso": "not-a-valid-iso-date",
                "end_iso": "also-not-valid"
            }
        )
        
        assert response.status_code == 200


class TestNotifyUserDueTasksIsoParsing:
    """Test ISO date parsing branches in _notify_user_due_tasks"""
    
    def test_notify_user_sample_due_matching_regex_success(self, mock_db):
        """Branch 266->268: sample_due matches regex and ISO parsing succeeds"""
        from backend.api.notifications import _notify_user_due_tasks
        
        mock_task = Mock()
        # Exact minute format that matches regex
        mock_task.to_dict.return_value = {"due_date": "2025-01-15T14:30"}
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([mock_task])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                return mock_tasks
        
        mock_db.collection.side_effect = mock_collection
        
        result = _notify_user_due_tasks(
            mock_db,
            "user123",
            "2025-01-15T00:00:00+00:00",
            "2025-01-16T00:00:00+00:00"
        )
        
        assert result == 0
    
    def test_notify_user_no_sample_task(self, mock_db):
        """Branch 264->266: no sample task found (sample is None)"""
        from backend.api.notifications import _notify_user_due_tasks
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                # Empty iterator - no tasks
                mock_tasks.limit.return_value.stream.return_value = iter([])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                return mock_tasks
        
        mock_db.collection.side_effect = mock_collection
        
        result = _notify_user_due_tasks(
            mock_db,
            "user123",
            "2025-01-15T00:00:00+00:00",
            "2025-01-16T00:00:00+00:00"
        )
        
        assert result == 0
    
    def test_notify_user_sample_due_not_matching_regex(self, mock_db):
        """Branch 264->266: sample_due doesn't match regex (line 266->else 274)"""
        from backend.api.notifications import _notify_user_due_tasks
        
        mock_task = Mock()
        # Date-only format that won't match regex
        mock_task.to_dict.return_value = {"due_date": "2025-01-15"}
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([mock_task])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                return mock_tasks
        
        mock_db.collection.side_effect = mock_collection
        
        result = _notify_user_due_tasks(
            mock_db,
            "user123",
            "2025-01-15T00:00:00+00:00",
            "2025-01-16T00:00:00+00:00"
        )
        
        assert result == 0
    
    def test_notify_user_sample_due_full_iso(self, mock_db):
        """Branch: sample_due is full ISO format with seconds"""
        from backend.api.notifications import _notify_user_due_tasks
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {"due_date": "2025-01-15T14:30:45+00:00"}
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([mock_task])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                return mock_tasks
        
        mock_db.collection.side_effect = mock_collection
        
        result = _notify_user_due_tasks(
            mock_db,
            "user123",
            "2025-01-15T00:00:00+00:00",
            "2025-01-16T00:00:00+00:00"
        )
        
        assert result == 0
    
    def test_notify_user_sample_due_not_string(self, mock_db):
        """Branch 264->266: sample_due is not a string"""
        from backend.api.notifications import _notify_user_due_tasks
        
        mock_task = Mock()
        # Numeric due_date
        mock_task.to_dict.return_value = {"due_date": 1705334400}
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([mock_task])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                return mock_tasks
        
        mock_db.collection.side_effect = mock_collection
        
        result = _notify_user_due_tasks(
            mock_db,
            "user123",
            "2025-01-15T00:00:00+00:00",
            "2025-01-16T00:00:00+00:00"
        )
        
        assert result == 0
    
    def test_notify_user_sample_due_none(self, mock_db):
        """Branch: sample exists but has no due_date field"""
        from backend.api.notifications import _notify_user_due_tasks
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {"title": "Task without due date"}
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([mock_task])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                return mock_tasks
        
        mock_db.collection.side_effect = mock_collection
        
        result = _notify_user_due_tasks(
            mock_db,
            "user123",
            "2025-01-15T00:00:00+00:00",
            "2025-01-16T00:00:00+00:00"
        )
        
        assert result == 0
    
    def test_notify_user_sample_to_dict_none(self, mock_db):
        """Branch: sample.to_dict() returns None"""
        from backend.api.notifications import _notify_user_due_tasks
        
        mock_task = Mock()
        mock_task.to_dict.return_value = None
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([mock_task])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                return mock_tasks
        
        mock_db.collection.side_effect = mock_collection
        
        result = _notify_user_due_tasks(
            mock_db,
            "user123",
            "2025-01-15T00:00:00+00:00",
            "2025-01-16T00:00:00+00:00"
        )
        
        assert result == 0
    
    def test_notify_user_iso_parse_exception(self, mock_db):
        """Lines 272-274: Exception when parsing ISO dates"""
        from backend.api.notifications import _notify_user_due_tasks
        
        mock_task = Mock()
        # Has minute format to trigger the parsing code
        mock_task.to_dict.return_value = {"due_date": "2025-01-15T14:30"}
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([mock_task])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                return mock_tasks
        
        mock_db.collection.side_effect = mock_collection
        
        # Pass malformed ISO strings that will fail fromisoformat()
        result = _notify_user_due_tasks(
            mock_db,
            "user123",
            "not-a-valid-iso-date",
            "also-not-valid"
        )
        
        assert result == 0
