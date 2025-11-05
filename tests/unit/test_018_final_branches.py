"""
Final missing branches - very specific edge cases
Lines: 85, 188->185, 469->491, 477->491, 479->491, 483-485, 750->762
"""

import pytest
import sys
from unittest.mock import Mock, patch

fake_firestore = sys.modules.get("firebase_admin.firestore")


@pytest.fixture
def mock_db():
    return Mock()


class TestFinalMissingBranches:
    """Ultra-specific tests for the exact missing branches"""
    
    def test_notify_member_without_user_id_line_188(self, client, mock_db, monkeypatch):
        """Line 188->185: Project member has no user_id in their data"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "user1",
            "role": "staff"
        }
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"},
            "assigned_to": {"user_id": "user1"},
            "project_id": "proj1",
            "title": "Old title"
        }
        
        # Mock project member with NO user_id field
        mock_member_no_uid = Mock()
        mock_member_no_uid.to_dict.return_value = {}  # No user_id - should skip line 189
        
        mock_member_with_uid = Mock()
        mock_member_with_uid.to_dict.return_value = {"user_id": "member2"}
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_task_ref = Mock()
                mock_task_ref.get.return_value = mock_task_doc
                mock_task_ref.update.return_value = None
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            elif name == "memberships":
                mock_memberships = Mock()
                mock_memberships.where.return_value = mock_memberships
                # Return member with no user_id and one with user_id
                mock_memberships.stream.return_value = [mock_member_no_uid, mock_member_with_uid]
                return mock_memberships
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_edit_task", return_value=True):
            response = client.put(
                "/api/tasks/task1",
                json={"title": "New title"},
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 200
        # Should skip member without user_id (line 188->185 branch when uid is falsy)
    
    def test_get_tasks_managed_by_with_exception_in_owner_check_line_483(self, client, mock_db, monkeypatch):
        """Lines 483-485: Exception occurs during project owner check logic"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "staff1",
            "role": "staff"
        }
        
        # Make project.to_dict() raise exception
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        
        call_count = [0]
        def to_dict_with_exception():
            call_count[0] += 1
            if call_count[0] == 1:
                # First call in the owner check logic - raise exception
                raise Exception("Database error during owner check")
            return {"owner_id": "owner1"}
        
        mock_project_doc.to_dict = to_dict_with_exception
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            elif name == "projects":
                mock_projects = Mock()
                mock_projects.document.return_value.get.return_value = mock_project_doc
                return mock_projects
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.where.return_value = mock_tasks
                mock_tasks.stream.return_value = []
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "staff1"}
        )
        
        assert response.status_code == 200
        # Should catch exception in lines 483-485
