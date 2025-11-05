"""
Tests for branch coverage of _is_admin_or_hr function in reports.py
Numbered 000 to ensure this runs FIRST in the test suite (pytest runs alphabetically)
This ensures the coverage tracer is active before the module is imported
"""
import pytest
from unittest.mock import Mock, patch


class TestReportsBranchCoverage:
    """Test both branches of each conditional in _is_admin_or_hr"""
    
    def test_branch_user_id_is_falsy_empty_string(self, mock_db):
        """Branch: if not user_id -> TRUE (line 24->25, return False for empty string)"""
        from backend.api.reports import _is_admin_or_hr
        result = _is_admin_or_hr(mock_db, "")
        assert result is False
    
    def test_branch_user_id_is_falsy_none(self, mock_db):
        """Branch: if not user_id -> TRUE (line 24->25, return False for None)"""
        from backend.api.reports import _is_admin_or_hr
        result = _is_admin_or_hr(mock_db, None)
        assert result is False
    
    def test_branch_user_id_is_truthy(self, mock_db):
        """Branch: if not user_id -> FALSE (line 24->26, continue to check user_doc)"""
        from backend.api.reports import _is_admin_or_hr
        mock_doc = Mock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = _is_admin_or_hr(mock_db, "user123")
        # Should reach line 27 and return False because user doesn't exist
        assert result is False
    
    def test_branch_user_doc_not_exists(self, mock_db):
        """Branch: if not user_doc.exists -> TRUE (line 27->28, return False)"""
        from backend.api.reports import _is_admin_or_hr
        mock_doc = Mock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = _is_admin_or_hr(mock_db, "nonexistent_user")
        assert result is False
    
    def test_branch_user_doc_exists_admin(self, mock_db):
        """Branch: if not user_doc.exists -> FALSE (line 27->29, check role for admin)"""
        from backend.api.reports import _is_admin_or_hr
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"role": "admin"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = _is_admin_or_hr(mock_db, "admin_user")
        assert result is True
    
    def test_branch_user_doc_exists_hr(self, mock_db):
        """Branch: if not user_doc.exists -> FALSE (line 27->29, check role for HR)"""
        from backend.api.reports import _is_admin_or_hr
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"role": "HR"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = _is_admin_or_hr(mock_db, "hr_user")
        assert result is True
    
    def test_branch_user_doc_exists_not_admin_or_hr(self, mock_db):
        """Branch: if not user_doc.exists -> FALSE, but role check returns False"""
        from backend.api.reports import _is_admin_or_hr
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"role": "staff"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = _is_admin_or_hr(mock_db, "staff_user")
        assert result is False
    
    def test_branch_user_doc_exists_no_role(self, mock_db):
        """Branch: user exists but has no role field"""
        from backend.api.reports import _is_admin_or_hr
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {}  # No role field
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = _is_admin_or_hr(mock_db, "user_no_role")
        assert result is False
    
    def test_branch_user_doc_to_dict_returns_none(self, mock_db):
        """Branch: user exists but to_dict returns None"""
        from backend.api.reports import _is_admin_or_hr
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = None  # Edge case
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = _is_admin_or_hr(mock_db, "user_none_dict")
        assert result is False
