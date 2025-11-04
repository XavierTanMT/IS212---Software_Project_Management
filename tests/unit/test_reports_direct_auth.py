"""
Direct tests for _is_admin_or_hr function to ensure lines 25 and 28 are covered
This file uses direct function calls to guarantee coverage tracing
"""
import pytest
from unittest.mock import Mock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def test_is_admin_or_hr_empty_user_id(mock_db):
    """Directly test line 25: empty user_id"""
    from backend.api.reports import _is_admin_or_hr
    
    # Test with empty string
    result = _is_admin_or_hr(mock_db, "")
    assert result is False
    
    # Test with None
    result = _is_admin_or_hr(mock_db, None)
    assert result is False


def test_is_admin_or_hr_user_not_exists(mock_db):
    """Directly test line 28: user doesn't exist"""
    from backend.api.reports import _is_admin_or_hr
    
    mock_doc = Mock()
    mock_doc.exists = False
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    
    result = _is_admin_or_hr(mock_db, "nonexistent_user")
    assert result is False


def test_is_admin_or_hr_admin_user(mock_db):
    """Test successful admin check"""
    from backend.api.reports import _is_admin_or_hr
    
    mock_doc = Mock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"role": "admin"}
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    
    result = _is_admin_or_hr(mock_db, "admin_user")
    assert result is True


def test_is_admin_or_hr_hr_user(mock_db):
    """Test successful HR check"""
    from backend.api.reports import _is_admin_or_hr
    
    mock_doc = Mock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"role": "HR"}
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    
    result = _is_admin_or_hr(mock_db, "hr_user")
    assert result is True


def test_is_admin_or_hr_non_privileged_user(mock_db):
    """Test non-privileged user"""
    from backend.api.reports import _is_admin_or_hr
    
    mock_doc = Mock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"role": "staff"}
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    
    result = _is_admin_or_hr(mock_db, "staff_user")
    assert result is False
