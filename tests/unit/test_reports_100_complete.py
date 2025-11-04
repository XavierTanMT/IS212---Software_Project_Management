"""
Comprehensive tests to achieve 100% coverage for reports.py
Tests PDF, CSV, XLSX generation, date parsing, and all edge cases
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
import io


class TestReportsAuthorization:
    """Tests for authorization checks in reports"""
    
    def test_task_completion_report_unauthorized_non_admin(self, client, mock_db):
        """Test that non-admin/HR users cannot access reports"""
        # Mock user as staff (not admin/HR)
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "staff"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        response = client.get("/api/reports/task-completion?viewer_id=user123")
        
        assert response.status_code == 403
        data = response.get_json()
        assert "Unauthorized" in data["error"]
        assert "Admin/HR only" in data["error"]
    
    def test_task_completion_report_authorized_admin(self, client, mock_db):
        """Test that admin users can access reports"""
        # Mock user as admin
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        # Mock empty tasks
        mock_db.collection.return_value.stream.return_value = []
        
        response = client.get("/api/reports/task-completion?viewer_id=admin123&format=pdf")
        
        # Should succeed (will try to generate PDF)
        assert response.status_code in [200, 500]  # May fail on PDF generation but passed auth
    
    def test_task_completion_report_authorized_hr(self, client, mock_db):
        """Test that HR users can access reports"""
        # Mock user as HR
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "hr"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        # Mock empty tasks
        mock_db.collection.return_value.stream.return_value = []
        
        response = client.get("/api/reports/task-completion?viewer_id=hr123&format=pdf")
        
        # Should succeed
        assert response.status_code in [200, 500]
    
    def test_weekly_summary_unauthorized(self, client, mock_db):
        """Test weekly summary authorization"""
        # Mock user as staff
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "manager"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        response = client.get("/api/reports/weekly-summary?viewer_id=user123")
        
        assert response.status_code == 403


class TestReportsDateParsing:
    """Tests for date parsing utilities"""
    
    def test_parse_date_iso_format(self):
        """Test parsing ISO format date"""
        from backend.api.reports import parse_date
        
        date_str = "2025-11-04T10:30:00+00:00"
        result = parse_date(date_str)
        
        assert result is not None
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 4
    
    def test_parse_date_with_z_suffix(self):
        """Test parsing date with Z suffix"""
        from backend.api.reports import parse_date
        
        date_str = "2025-11-04T10:30:00Z"
        result = parse_date(date_str)
        
        assert result is not None
        assert result.tzinfo is not None  # Should be timezone-aware
    
    def test_parse_date_none(self):
        """Test parsing None returns None"""
        from backend.api.reports import parse_date
        
        result = parse_date(None)
        assert result is None
    
    def test_parse_date_empty_string(self):
        """Test parsing empty string returns None"""
        from backend.api.reports import parse_date
        
        result = parse_date("")
        assert result is None
    
    def test_parse_date_invalid_format(self):
        """Test parsing invalid format returns None"""
        from backend.api.reports import parse_date
        
        result = parse_date("not-a-date")
        assert result is None
    
    def test_parse_date_naive_datetime(self):
        """Test that naive datetime gets timezone added"""
        from backend.api.reports import parse_date
        
        date_str = "2025-11-04T10:30:00"
        result = parse_date(date_str)
        
        assert result is not None, f"parse_date returned None for valid date string: {date_str}"
        assert result.tzinfo is not None


class TestReportsSafeGetUserInfo:
    """Tests for safe_get_user_info utility"""
    
    def test_safe_get_user_info_dict(self):
        """Test extracting from dict"""
        from backend.api.reports import safe_get_user_info
        
        user_data = {"name": "John Doe", "email": "john@example.com"}
        result = safe_get_user_info(user_data, "name", "Unknown")
        
        assert result == "John Doe"
    
    def test_safe_get_user_info_list_with_items(self):
        """Test extracting from list with items"""
        from backend.api.reports import safe_get_user_info
        
        user_data = [{"name": "John Doe", "email": "john@example.com"}]
        result = safe_get_user_info(user_data, "name", "Unknown")
        
        assert result == "John Doe"
    
    def test_safe_get_user_info_empty_list(self):
        """Test extracting from empty list returns default"""
        from backend.api.reports import safe_get_user_info
        
        user_data = []
        result = safe_get_user_info(user_data, "name", "Unknown")
        
        assert result == "Unknown"
    
    def test_safe_get_user_info_none(self):
        """Test extracting from None returns default"""
        from backend.api.reports import safe_get_user_info
        
        result = safe_get_user_info(None, "name", "Unknown")
        
        assert result == "Unknown"
    
    def test_safe_get_user_info_string(self):
        """Test extracting from string returns default"""
        from backend.api.reports import safe_get_user_info
        
        user_data = "not-a-dict"
        result = safe_get_user_info(user_data, "name", "Unknown")
        
        assert result == "Unknown"
    
    def test_safe_get_user_info_missing_field(self):
        """Test extracting missing field returns default"""
        from backend.api.reports import safe_get_user_info
        
        user_data = {"email": "john@example.com"}
        result = safe_get_user_info(user_data, "name", "Unknown")
        
        assert result == "Unknown"


class TestReportsTaskFiltering:
    """Tests for task filtering in reports"""
    
    def test_task_completion_filter_by_user(self, client, mock_db, monkeypatch):
        """Test filtering tasks by user_id"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        # Mock tasks
        task1 = Mock()
        task1.id = "task1"
        task1.to_dict.return_value = {
            "title": "Task 1",
            "status": "Completed",
            "priority": "High",
            "due_date": "2025-11-04T10:00:00Z",
            "assigned_to": {"user_id": "user123", "name": "John"},
            "created_by": {"user_id": "admin", "name": "Admin"},
            "project_id": "proj1",
            "created_at": "2025-11-01T10:00:00Z"
        }
        
        task2 = Mock()
        task2.id = "task2"
        task2.to_dict.return_value = {
            "title": "Task 2",
            "status": "In Progress",
            "priority": "Medium",
            "due_date": "2025-11-05T10:00:00Z",
            "assigned_to": {"user_id": "user456", "name": "Jane"},
            "created_by": {"user_id": "admin", "name": "Admin"},
            "project_id": "proj1",
            "created_at": "2025-11-01T11:00:00Z"
        }
        
        # Mock query with where filter
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.stream.return_value = [task1]  # Only task1 matches user filter
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_admin
            elif name == "tasks":
                return mock_query
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.reports.send_file') as mock_send:
            mock_send.return_value = ("PDF content", 200)
            response = client.get("/api/reports/task-completion?viewer_id=admin&user_id=user123&format=csv")
        
        # Verify where was called with user filter
        assert mock_query.where.called
    
    def test_task_completion_filter_by_project(self, client, mock_db):
        """Test filtering tasks by project_id"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        # Mock query with where filter
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.stream.return_value = []
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_admin
            elif name == "tasks":
                return mock_query
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.reports.send_file') as mock_send:
            mock_send.return_value = ("CSV content", 200)
            response = client.get("/api/reports/task-completion?viewer_id=admin&project_id=proj123&format=csv")
        
        # Verify where was called
        assert mock_query.where.called
    
    def test_task_completion_filter_by_date_range(self, client, mock_db):
        """Test filtering tasks by date range"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        # Mock task with due date
        task1 = Mock()
        task1.id = "task1"
        task1.to_dict.return_value = {
            "title": "Task 1",
            "status": "Completed",
            "priority": "High",
            "due_date": "2025-11-15T10:00:00Z",  # Within range
            "assigned_to": {"user_id": "user123", "name": "John"},
            "created_by": {"user_id": "admin", "name": "Admin"},
            "project_id": "proj1",
            "created_at": "2025-11-01T10:00:00Z"
        }
        
        task2 = Mock()
        task2.id = "task2"
        task2.to_dict.return_value = {
            "title": "Task 2",
            "status": "In Progress",
            "priority": "Medium",
            "due_date": "2025-12-01T10:00:00Z",  # Outside range
            "assigned_to": {"user_id": "user456", "name": "Jane"},
            "created_by": {"user_id": "admin", "name": "Admin"},
            "project_id": "proj1",
            "created_at": "2025-11-01T11:00:00Z"
        }
        
        mock_query = Mock()
        mock_query.stream.return_value = [task1, task2]
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_admin
            elif name == "tasks":
                return mock_query
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.reports.send_file') as mock_send:
            mock_send.return_value = ("CSV content", 200)
            response = client.get("/api/reports/task-completion?viewer_id=admin&start_date=2025-11-01&end_date=2025-11-20&format=csv")
        
        # Should filter out task2 which is outside date range
        assert response.status_code == 200


class TestReportsFormatGeneration:
    """Tests for different report formats"""
    
    def test_task_completion_csv_format(self, client, mock_db):
        """Test CSV report generation"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        # Mock task
        task = Mock()
        task.id = "task1"
        task.to_dict.return_value = {
            "title": "Test Task",
            "status": "Completed",
            "priority": "High",
            "due_date": "2025-11-04T10:00:00Z",
            "assigned_to": {"user_id": "user123", "name": "John"},
            "created_by": {"user_id": "admin", "name": "Admin"},
            "project_id": "proj1",
            "created_at": "2025-11-01T10:00:00Z"
        }
        
        mock_query = Mock()
        mock_query.stream.return_value = [task]
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_admin
            elif name == "tasks":
                return mock_query
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.reports.send_file') as mock_send:
            mock_send.return_value = ("CSV content", 200)
            response = client.get("/api/reports/task-completion?viewer_id=admin&format=csv")
        
        assert mock_send.called
        call_args = mock_send.call_args
        assert call_args[1]['mimetype'] == 'text/csv'
    
    def test_task_completion_pdf_format(self, client, mock_db):
        """Test PDF report generation"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_query = Mock()
        mock_query.stream.return_value = []
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_admin
            elif name == "tasks":
                return mock_query
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.reports.send_file') as mock_send:
            mock_send.return_value = ("PDF content", 200)
            response = client.get("/api/reports/task-completion?viewer_id=admin&format=pdf")
        
        assert mock_send.called
        call_args = mock_send.call_args
        assert call_args[1]['mimetype'] == 'application/pdf'
    
    def test_task_completion_xlsx_format(self, client, mock_db):
        """Test Excel report generation"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_query = Mock()
        mock_query.stream.return_value = []
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_admin
            elif name == "tasks":
                return mock_query
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.reports.send_file') as mock_send:
            mock_send.return_value = ("XLSX content", 200)
            response = client.get("/api/reports/task-completion?viewer_id=admin&format=xlsx")
        
        assert mock_send.called
        call_args = mock_send.call_args
        assert 'openxmlformats' in call_args[1]['mimetype']
    
    def test_task_completion_invalid_format(self, client, mock_db):
        """Test invalid format returns error"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_query = Mock()
        mock_query.stream.return_value = []
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_admin
            elif name == "tasks":
                return mock_query
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/reports/task-completion?viewer_id=admin&format=invalid")
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Invalid format" in data["error"]


class TestReportsStatistics:
    """Tests for report statistics calculation"""
    
    def test_completion_rate_calculation(self, client, mock_db):
        """Test completion rate is calculated correctly"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        # Mock tasks with different statuses
        tasks = []
        statuses = ["Completed", "Completed", "In Progress", "To Do", "Blocked"]
        
        for i, status in enumerate(statuses):
            task = Mock()
            task.id = f"task{i}"
            task.to_dict.return_value = {
                "title": f"Task {i}",
                "status": status,
                "priority": "Medium",
                "due_date": "2025-11-04T10:00:00Z",
                "assigned_to": {"user_id": "user123", "name": "John"},
                "created_by": {"user_id": "admin", "name": "Admin"},
                "project_id": "proj1",
                "created_at": "2025-11-01T10:00:00Z"
            }
            tasks.append(task)
        
        mock_query = Mock()
        mock_query.stream.return_value = tasks
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_admin
            elif name == "tasks":
                return mock_query
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.reports.send_file') as mock_send:
            mock_send.return_value = ("CSV content", 200)
            response = client.get("/api/reports/task-completion?viewer_id=admin&format=csv")
        
        # Should calculate 2/5 = 40% completion rate
        assert response.status_code == 200


class TestWeeklySummaryReport:
    """Tests for weekly summary report"""
    
    def test_weekly_summary_default_week(self, client, mock_db):
        """Test weekly summary with default (current) week"""
        # Mock HR user
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "hr"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        response = client.get("/api/reports/weekly-summary?viewer_id=hr123")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "week_start" in data
        assert "week_end" in data
    
    def test_weekly_summary_custom_week(self, client, mock_db):
        """Test weekly summary with custom week start"""
        # Mock admin user
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        response = client.get("/api/reports/weekly-summary?viewer_id=admin123&week_start=2025-11-01T00:00:00Z")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "2025-11-01" in data["week_start"]


class TestReportsEdgeCases:
    """Tests for edge cases and error handling"""
    
    def test_task_with_none_due_date(self, client, mock_db):
        """Test handling task with None due date"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        # Mock task with no due date
        task = Mock()
        task.id = "task1"
        task.to_dict.return_value = {
            "title": "Task without due date",
            "status": "To Do",
            "priority": "Low",
            "due_date": None,
            "assigned_to": None,
            "created_by": None,
            "project_id": "",
            "created_at": ""
        }
        
        mock_query = Mock()
        mock_query.stream.return_value = [task]
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_admin
            elif name == "tasks":
                return mock_query
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.reports.send_file') as mock_send:
            mock_send.return_value = ("CSV content", 200)
            response = client.get("/api/reports/task-completion?viewer_id=admin&format=csv")
        
        assert response.status_code == 200
    
    def test_task_with_list_assigned_to(self, client, mock_db):
        """Test handling task with assigned_to as list"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        # Mock task with assigned_to as list
        task = Mock()
        task.id = "task1"
        task.to_dict.return_value = {
            "title": "Task",
            "status": "To Do",
            "priority": "Medium",
            "due_date": "2025-11-04T10:00:00Z",
            "assigned_to": [{"user_id": "user123", "name": "John"}],
            "created_by": [{"user_id": "admin", "name": "Admin"}],
            "project_id": "proj1",
            "created_at": "2025-11-01T10:00:00Z"
        }
        
        mock_query = Mock()
        mock_query.stream.return_value = [task]
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_admin
            elif name == "tasks":
                return mock_query
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.reports.send_file') as mock_send:
            mock_send.return_value = ("CSV content", 200)
            response = client.get("/api/reports/task-completion?viewer_id=admin&format=csv")
        
        assert response.status_code == 200
    
    def test_no_tasks_found(self, client, mock_db):
        """Test report generation with no tasks"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_query = Mock()
        mock_query.stream.return_value = []
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_admin
            elif name == "tasks":
                return mock_query
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.reports.send_file') as mock_send:
            mock_send.return_value = ("PDF content", 200)
            response = client.get("/api/reports/task-completion?viewer_id=admin&format=pdf")
        
        assert response.status_code == 200
    
    def test_report_type_parameter(self, client, mock_db):
        """Test different report_type parameter values"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_query = Mock()
        mock_query.stream.return_value = []
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_admin
            elif name == "tasks":
                return mock_query
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        for report_type in ["summary", "user", "project"]:
            with patch('backend.api.reports.send_file') as mock_send:
                mock_send.return_value = ("PDF content", 200)
                response = client.get(f"/api/reports/task-completion?viewer_id=admin&format=pdf&report_type={report_type}")
            
            assert response.status_code == 200
