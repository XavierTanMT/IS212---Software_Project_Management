"""
Specific branch coverage tests for reports.py to achieve 100%
Targets missing lines: 25, 28, 61, 127, 208, 246-274, 456
Targets missing branches: 124->132 and others
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta


class TestIsAdminOrHR:
    """Test _is_admin_or_hr function for missing branches"""
    
    def test_is_admin_or_hr_with_empty_user_id(self):
        """Test line 25: if not user_id"""
        from backend.api.reports import _is_admin_or_hr
        
        mock_db = Mock()
        result = _is_admin_or_hr(mock_db, "")
        assert result is False
        
        result = _is_admin_or_hr(mock_db, None)
        assert result is False
    
    def test_is_admin_or_hr_user_not_exists(self):
        """Test line 28: if not user_doc.exists"""
        from backend.api.reports import _is_admin_or_hr
        
        mock_db = Mock()
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = _is_admin_or_hr(mock_db, "user123")
        assert result is False
    
    def test_endpoint_with_no_user_id(self, client, mock_db):
        """Test line 25: endpoint called without user_id - triggers empty user_id check"""
        # Mock to capture the call but return a non-existent user
        mock_doc = Mock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # No user_id provided in headers or query params
        response = client.get("/api/reports/task-completion")
        
        # Should fail authorization due to no user_id
        assert response.status_code == 403
        data = response.get_json()
        assert "Unauthorized" in data["error"]
    
    def test_endpoint_with_non_existent_user(self, client, mock_db):
        """Test line 28: endpoint with non-existent user"""
        # Mock user document that doesn't exist
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        response = client.get(
            "/api/reports/task-completion",
            headers={"X-User-Id": "nonexistent123"}
        )
        
        # Should fail authorization
        assert response.status_code == 403
        data = response.get_json()
        assert "Unauthorized" in data["error"]
    
    def test_weekly_summary_with_no_user_id(self, client, mock_db):
        """Test line 25: weekly-summary endpoint without user_id"""
        mock_doc = Mock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        response = client.get("/api/reports/weekly-summary")
        
        assert response.status_code == 403
        data = response.get_json()
        assert "Unauthorized" in data["error"]
    
    def test_weekly_summary_with_non_existent_user(self, client, mock_db):
        """Test line 28: weekly-summary with non-existent user"""
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        response = client.get(
            "/api/reports/weekly-summary",
            headers={"X-User-Id": "nonexistent456"}
        )
        
        assert response.status_code == 403
        data = response.get_json()
        assert "Unauthorized" in data["error"]


class TestSafeGetUserInfo:
    """Test safe_get_user_info for missing branches"""
    
    def test_safe_get_user_info_with_empty_list(self):
        """Test line 61: else return default when list is empty"""
        from backend.api.reports import safe_get_user_info
        
        result = safe_get_user_info([], "name", "default_value")
        assert result == "default_value"
    
    def test_safe_get_user_info_with_non_dict_non_list(self):
        """Test returning default when data is not dict or list"""
        from backend.api.reports import safe_get_user_info
        
        # Test with a string
        result = safe_get_user_info("some_string", "name", "default")
        assert result == "default"
        
        # Test with a number
        result = safe_get_user_info(123, "name", "default")
        assert result == "default"


class TestParseDateFallback:
    """Test parse_date fallback exception handling"""
    
    def test_parse_date_fallback_exception(self):
        """Test line 48-49: fallback exception handling"""
        from backend.api.reports import parse_date
        
        # Invalid format that will trigger fallback
        result = parse_date("invalid-date-format")
        assert result is None
        
        # Another invalid format
        result = parse_date("2025/11/04")  # Wrong separator
        assert result is None


class TestTaskCompletionReportBranches:
    """Test task_completion_report for missing branches"""
    
    def test_task_completion_no_due_date(self, client, mock_db):
        """Test line 124->132: task without due_date continues to next iteration"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        
        # Task without due_date
        mock_task = Mock()
        mock_task.id = "task1"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "status": "To Do",
            "priority": "High",
            "assigned_to": {"name": "User", "user_id": "user1"},
            "created_by": {"name": "Creator", "user_id": "creator1"},
            "project_id": "proj1",
            "created_at": "2025-11-01T00:00:00Z",
            # No due_date field
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "tasks":
                mock_coll.stream.return_value = [mock_task]
                mock_coll.where.return_value = mock_coll
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/reports/task-completion",
            headers={"X-User-Id": "admin123"},
            query_string={"format": "csv"}
        )
        
        assert response.status_code == 200
    
    def test_task_completion_due_date_before_start_date(self, client, mock_db):
        """Test line 127: if start_date and due_date < start_date: continue"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        
        # Task with due_date before start_date filter
        mock_task = Mock()
        mock_task.id = "task1"
        mock_task.to_dict.return_value = {
            "title": "Old Task",
            "status": "Completed",
            "priority": "Low",
            "due_date": "2025-10-01T00:00:00Z",  # Before our start_date filter
            "assigned_to": {"name": "User", "user_id": "user1"},
            "created_by": {"name": "Creator", "user_id": "creator1"},
            "project_id": "proj1",
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "tasks":
                mock_coll.stream.return_value = [mock_task]
                mock_coll.where.return_value = mock_coll
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/reports/task-completion",
            headers={"X-User-Id": "admin123"},
            query_string={
                "format": "csv",
                "start_date": "2025-11-01T00:00:00Z"
            }
        )
        
        assert response.status_code == 200


class TestGeneratePDFReport:
    """Test PDF generation for missing lines 246-274"""
    
    def test_generate_pdf_with_long_titles_and_assignees(self, client, mock_db):
        """Test lines 251-254: truncation logic for long titles and assignee names"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        
        # Task with very long title and assignee name
        mock_task = Mock()
        mock_task.id = "task1"
        mock_task.to_dict.return_value = {
            "title": "This is a very long task title that should definitely be truncated in the PDF report",
            "status": "In Progress",
            "priority": "High",
            "due_date": "2025-11-10T00:00:00Z",
            "assigned_to": {
                "name": "Very Long Name That Should Be Truncated",
                "user_id": "user1"
            },
            "created_by": {"name": "Creator", "user_id": "creator1"},
            "project_id": "proj1",
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "tasks":
                mock_coll.stream.return_value = [mock_task]
                mock_coll.where.return_value = mock_coll
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/reports/task-completion",
            headers={"X-User-Id": "admin123"},
            query_string={"format": "pdf"}
        )
        
        assert response.status_code == 200
        assert response.content_type == "application/pdf"
    
    def test_generate_pdf_with_more_than_50_tasks(self, client, mock_db):
        """Test lines 272-274: message when more than 50 tasks"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        
        # Create 60 tasks to trigger the "showing first 50" message
        tasks = []
        for i in range(60):
            mock_task = Mock()
            mock_task.id = f"task{i}"
            mock_task.to_dict.return_value = {
                "title": f"Task {i}",
                "status": "To Do",
                "priority": "Medium",
                "due_date": "2025-11-10T00:00:00Z",
                "assigned_to": {"name": f"User {i}", "user_id": f"user{i}"},
                "created_by": {"name": "Creator", "user_id": "creator1"},
                "project_id": "proj1",
            }
            tasks.append(mock_task)
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "tasks":
                mock_coll.stream.return_value = tasks
                mock_coll.where.return_value = mock_coll
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/reports/task-completion",
            headers={"X-User-Id": "admin123"},
            query_string={"format": "pdf"}
        )
        
        assert response.status_code == 200
        assert response.content_type == "application/pdf"
    
    def test_generate_pdf_with_no_tasks(self, client, mock_db):
        """Test line 276: else branch when no tasks found"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "tasks":
                mock_coll.stream.return_value = []
                mock_coll.where.return_value = mock_coll
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/reports/task-completion",
            headers={"X-User-Id": "admin123"},
            query_string={"format": "pdf"}
        )
        
        assert response.status_code == 200
        assert response.content_type == "application/pdf"


class TestWeeklySummaryBranches:
    """Test weekly_summary for missing line 456"""
    
    def test_weekly_summary_with_invalid_week_start(self, client, mock_db):
        """Test line 456: invalid week_start date format returns 400"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        response = client.get(
            "/api/reports/weekly-summary",
            headers={"X-User-Id": "admin123"},
            query_string={"week_start": "invalid-date"}
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Invalid week_start date format" in data["error"]
    
    def test_weekly_summary_with_valid_week_start(self, client, mock_db):
        """Test weekly summary with valid week_start"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        response = client.get(
            "/api/reports/weekly-summary",
            headers={"X-User-Id": "admin123"},
            query_string={"week_start": "2025-11-04T00:00:00Z"}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert "week_start" in data
        assert "week_end" in data


class TestInvalidFormatType:
    """Test invalid format type returns 400"""
    
    def test_invalid_format_type(self, client, mock_db):
        """Test that invalid format returns 400 error"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "tasks":
                mock_coll.stream.return_value = []
                mock_coll.where.return_value = mock_coll
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/reports/task-completion",
            headers={"X-User-Id": "admin123"},
            query_string={"format": "invalid_format"}
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Invalid format" in data["error"]


class TestTaskWithNullDueDate:
    """Test task with None due_date after parse_date"""
    
    def test_task_with_unparseable_due_date(self, client, mock_db):
        """Test when due_date exists but parse_date returns None"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        
        # Task with unparseable due_date
        mock_task = Mock()
        mock_task.id = "task1"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "status": "To Do",
            "priority": "High",
            "due_date": "not-a-valid-date",  # Will fail to parse
            "assigned_to": {"name": "User", "user_id": "user1"},
            "created_by": {"name": "Creator", "user_id": "creator1"},
            "project_id": "proj1",
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "tasks":
                mock_coll.stream.return_value = [mock_task]
                mock_coll.where.return_value = mock_coll
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/reports/task-completion",
            headers={"X-User-Id": "admin123"},
            query_string={"format": "csv"}
        )
        
        assert response.status_code == 200


class TestPDFReportDifferentTypes:
    """Test PDF generation with different report types"""
    
    def test_pdf_with_user_report_type(self, client, mock_db):
        """Test PDF generation with report_type=user"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "tasks":
                mock_coll.stream.return_value = []
                mock_coll.where.return_value = mock_coll
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/reports/task-completion",
            headers={"X-User-Id": "admin123"},
            query_string={"format": "pdf", "report_type": "user"}
        )
        
        assert response.status_code == 200
        assert response.content_type == "application/pdf"
    
    def test_pdf_with_project_report_type(self, client, mock_db):
        """Test PDF generation with report_type=project"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "tasks":
                mock_coll.stream.return_value = []
                mock_coll.where.return_value = mock_coll
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/reports/task-completion",
            headers={"X-User-Id": "admin123"},
            query_string={"format": "pdf", "report_type": "project"}
        )
        
        assert response.status_code == 200
        assert response.content_type == "application/pdf"
    
    def test_pdf_with_filters(self, client, mock_db):
        """Test line 208: PDF generation with filters applied"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "tasks":
                mock_coll.stream.return_value = []
                mock_coll.where.return_value = mock_coll
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/reports/task-completion",
            headers={"X-User-Id": "admin123"},
            query_string={
                "format": "pdf",
                "user_id": "user123",
                "project_id": "proj456",
                "start_date": "2025-11-01T00:00:00Z",
                "end_date": "2025-11-30T00:00:00Z"
            }
        )
        
        assert response.status_code == 200
        assert response.content_type == "application/pdf"


class TestSafeGetUserInfoReturnsDefault:
    """Test line 61: safe_get_user_info returns default for non-dict/list"""
    
    def test_safe_get_user_info_with_none(self):
        """Test line 61: None returns default"""
        from backend.api.reports import safe_get_user_info
        
        result = safe_get_user_info(None, "name", "default")
        assert result == "default"
    
    def test_safe_get_user_info_with_non_dict_non_list_returns_default(self):
        """Test line 65-66: return default when not dict or list"""
        from backend.api.reports import safe_get_user_info
        
        # Test with a string - should return default
        result = safe_get_user_info("some_string", "name", "default_value")
        assert result == "default_value"
        
        # Test with a number - should return default
        result = safe_get_user_info(123, "name", "default_value")
        assert result == "default_value"
        
        # Test with a boolean - should return default
        result = safe_get_user_info(True, "name", "default_value")
        assert result == "default_value"
    
    def test_task_with_empty_list_assigned_to(self, client, mock_db):
        """Test line 61: task with empty list for assigned_to field"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        
        # Task with empty list for assigned_to
        mock_task = Mock()
        mock_task.id = "task1"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "status": "To Do",
            "priority": "High",
            "due_date": "2025-11-10T00:00:00Z",
            "assigned_to": [],  # Empty list - should trigger line 61
            "created_by": [],  # Empty list - should trigger line 61 again
            "project_id": "proj1",
            "created_at": "2025-11-01T00:00:00Z",
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "tasks":
                mock_coll.stream.return_value = [mock_task]
                mock_coll.where.return_value = mock_coll
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/reports/task-completion",
            headers={"X-User-Id": "admin123"},
            query_string={"format": "csv"}
        )
        
        assert response.status_code == 200
        # Verify the CSV contains the default values
        content = response.get_data(as_text=True)
        assert "Unassigned" in content  # Default for empty assigned_to list
        assert "Unknown" in content  # Default for empty created_by list
    
    def test_task_with_empty_list_pdf_format(self, client, mock_db):
        """Test line 61: empty list with PDF format"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        
        mock_task = Mock()
        mock_task.id = "task1"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "status": "Completed",
            "priority": "Medium",
            "due_date": "2025-11-10T00:00:00Z",
            "assigned_to": [],  # Empty list
            "created_by": [],  # Empty list
            "project_id": "proj1",
            "created_at": "2025-11-01T00:00:00Z",
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "tasks":
                mock_coll.stream.return_value = [mock_task]
                mock_coll.where.return_value = mock_coll
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/reports/task-completion",
            headers={"X-User-Id": "admin123"},
            query_string={"format": "pdf"}
        )
        
        assert response.status_code == 200
        assert response.content_type == "application/pdf"
    
    def test_task_with_empty_list_xlsx_format(self, client, mock_db):
        """Test line 61: empty list with XLSX format"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        
        mock_task = Mock()
        mock_task.id = "task1"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "status": "In Progress",
            "priority": "High",
            "due_date": "2025-11-10T00:00:00Z",
            "assigned_to": [],  # Empty list
            "created_by": [],  # Empty list
            "project_id": "proj1",
            "created_at": "2025-11-01T00:00:00Z",
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "tasks":
                mock_coll.stream.return_value = [mock_task]
                mock_coll.where.return_value = mock_coll
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/reports/task-completion",
            headers={"X-User-Id": "admin123"},
            query_string={"format": "xlsx"}
        )
        
        assert response.status_code == 200
        assert response.content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
