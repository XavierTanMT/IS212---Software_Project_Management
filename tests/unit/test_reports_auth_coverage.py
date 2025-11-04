"""
Minimal test file to ensure lines 25 and 28 in reports.py are covered
This file uses ONLY endpoint tests to avoid any coverage tracing issues
"""
import pytest
from unittest.mock import Mock


class TestReportsAuthCoverage:
    """Endpoint tests to cover authorization edge cases"""
    
    def test_task_completion_empty_user_id_header(self, client, mock_db):
        """Cover line 25: empty user_id from header"""
        mock_doc = Mock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Empty string in header
        response = client.get(
            "/api/reports/task-completion",
            headers={"X-User-Id": ""}
        )
        assert response.status_code == 403
    
    def test_task_completion_no_user_id_at_all(self, client, mock_db):
        """Cover line 25: no user_id provided"""
        mock_doc = Mock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # No header at all
        response = client.get("/api/reports/task-completion")
        assert response.status_code == 403
    
    def test_task_completion_user_does_not_exist(self, client, mock_db):
        """Cover line 28: user document doesn't exist"""
        mock_doc = Mock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        response = client.get(
            "/api/reports/task-completion",
            headers={"X-User-Id": "nonexistent_user_123"}
        )
        assert response.status_code == 403
    
    def test_weekly_summary_empty_user_id(self, client, mock_db):
        """Cover line 25: empty user_id for weekly summary"""
        mock_doc = Mock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        response = client.get(
            "/api/reports/weekly-summary",
            headers={"X-User-Id": "   "}  # Whitespace that gets stripped to empty
        )
        assert response.status_code == 403
    
    def test_weekly_summary_user_not_found(self, client, mock_db):
        """Cover line 28: user not found for weekly summary"""
        mock_doc = Mock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        response = client.get(
            "/api/reports/weekly-summary",
            headers={"X-User-Id": "ghost_user_456"}
        )
        assert response.status_code == 403
