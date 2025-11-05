"""
Additional tests to achieve 100% branch coverage for tasks.py
Targets remaining specific branches identified in coverage report
"""
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Get fake_firestore from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")

from backend.api import tasks as tasks_module


@pytest.fixture
def mock_db():
    """Create a mock Firestore database."""
    return Mock()


class TestListTasksProjectOwnerBranches:
    """Test specific project owner branches in list_tasks (lines 469-491)"""
    
    def test_list_tasks_viewer_is_project_owner(self, client, mock_db, monkeypatch):
        """Lines 469->491: Viewer is the project owner"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "staff"}
        
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {"owner_id": "user1"}  # viewer is owner
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                mock_users.where.return_value.stream.return_value = []
                return mock_users
            elif name == "memberships":
                mock_memberships = Mock()
                # Mock membership doc
                mock_membership_doc = Mock()
                mock_membership_doc.exists = True
                mock_membership_doc.to_dict.return_value = {}
                mock_memberships.document.return_value.get.return_value = mock_membership_doc
                mock_memberships.where.return_value.stream.return_value = []
                return mock_memberships
            elif name == "projects":
                mock_projects = Mock()
                mock_projects.document.return_value.get.return_value = mock_project_doc
                return mock_projects
            elif name == "tasks":
                mock_tasks = Mock()
                mock_query = Mock()
                mock_query.limit.return_value.stream.return_value = []
                mock_tasks.where.return_value = mock_query
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200
    
    def test_list_tasks_viewer_reports_to_owner(self, client, mock_db, monkeypatch):
        """Lines 477->491, 479->491, 483-485: Viewer's manager is project owner"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc_role = Mock()
        mock_viewer_doc_role.exists = True
        mock_viewer_doc_role.to_dict.return_value = {"role": "staff"}
        
        mock_viewer_doc_manager = Mock()
        mock_viewer_doc_manager.exists = True
        mock_viewer_doc_manager.to_dict.return_value = {
            "manager_id": "owner1"  # Reports to owner
        }
        
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {"owner_id": "owner1"}
        
        call_count = [0]
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                
                def doc_side_effect(user_id):
                    mock_doc_ref = Mock()
                    if user_id == "user1":
                        call_count[0] += 1
                        if call_count[0] == 1:
                            # First call for role check
                            mock_doc_ref.get.return_value = mock_viewer_doc_role
                        else:
                            # Second call for manager check
                            mock_doc_ref.get.return_value = mock_viewer_doc_manager
                    return mock_doc_ref
                
                mock_users.document.side_effect = doc_side_effect
                mock_users.where.return_value.stream.return_value = []
                return mock_users
            elif name == "memberships":
                mock_memberships = Mock()
                mock_membership_doc = Mock()
                mock_membership_doc.exists = True
                mock_membership_doc.to_dict.return_value = {}
                mock_memberships.document.return_value.get.return_value = mock_membership_doc
                mock_memberships.where.return_value.stream.return_value = []
                return mock_memberships
            elif name == "projects":
                mock_projects = Mock()
                mock_projects.document.return_value.get.return_value = mock_project_doc
                return mock_projects
            elif name == "tasks":
                mock_tasks = Mock()
                mock_query = Mock()
                mock_query.limit.return_value.stream.return_value = []
                mock_tasks.where.return_value = mock_query
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200


class TestReassignTaskBranches:
    """Test reassign_task branches (lines 682, 708, 716)"""
    
    def test_reassign_task_already_assigned(self, client, mock_db, monkeypatch):
        """Lines 708, 716: Task already assigned to same user"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "manager"}
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "assigned_to": {"user_id": "user2"}  # Already assigned to user2
        }
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value.get.return_value = mock_task_doc
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.patch(  # PATCH not POST
            "/api/tasks/task1/reassign",
            json={"new_assigned_to_id": "user2"},  # Same as current
            headers={"X-User-Id": "manager1"}
        )
        
        assert response.status_code == 200
        assert b"already assigned" in response.data


class TestDeleteTaskRoleBranches:
    """Test delete_task role checking branches (lines 750->762, 759-760)"""
    
    def test_delete_task_as_hr(self, client, mock_db, monkeypatch):
        """Lines 750->762: HR role can delete"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "hr1"}  # User IS the creator
        }
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "hr"}
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            elif name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.delete(
            "/api/tasks/task1",
            headers={"X-User-Id": "hr1"}
        )
        
        assert response.status_code == 200
    
    def test_delete_task_as_director(self, client, mock_db, monkeypatch):
        """Lines 759-760: Director role can delete"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "director1"}  # User IS the creator
        }
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "director"}
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            elif name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.delete(
            "/api/tasks/task1",
            headers={"X-User-Id": "director1"}
        )
        
        assert response.status_code == 200


# No separate archive endpoint - delete does the archiving
# Increment tests removed - fake_firestore doesn't have Increment mock


class TestUpdateSubtaskBranches:
    """Test update_subtask branches (lines 906, 911, 920)"""
    
    def test_update_subtask_title_only(self, client, mock_db, monkeypatch):
        """Lines 906: Update only title"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = True
        mock_subtask_doc.to_dict.return_value = {
            "title": "Old Title"
        }
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.get.return_value = mock_subtask_doc
        mock_subtask_ref.update.return_value = None
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value.get.return_value = mock_task_doc
                return mock_tasks
            elif name == "subtasks":
                mock_subtasks = Mock()
                mock_subtasks.document.return_value = mock_subtask_ref
                return mock_subtasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.put(
            "/api/tasks/task1/subtasks/sub1",
            json={"title": "New Title"},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200
    
    def test_update_subtask_description_only(self, client, mock_db, monkeypatch):
        """Lines 911: Update only description"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = True
        mock_subtask_doc.to_dict.return_value = {
            "description": "Old Desc"
        }
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.get.return_value = mock_subtask_doc
        mock_subtask_ref.update.return_value = None
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value.get.return_value = mock_task_doc
                return mock_tasks
            elif name == "subtasks":
                mock_subtasks = Mock()
                mock_subtasks.document.return_value = mock_subtask_ref
                return mock_subtasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.put(
            "/api/tasks/task1/subtasks/sub1",
            json={"description": "New Desc"},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200
    
    def test_update_subtask_both_fields(self, client, mock_db, monkeypatch):
        """Lines 920: Update both title and description"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_subtask_doc = Mock()
        mock_subtask_doc.exists = True
        mock_subtask_doc.to_dict.return_value = {
            "title": "Old Title",
            "description": "Old Desc"
        }
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.get.return_value = mock_subtask_doc
        mock_subtask_ref.update.return_value = None
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value.get.return_value = mock_task_doc
                return mock_tasks
            elif name == "subtasks":
                mock_subtasks = Mock()
                mock_subtasks.document.return_value = mock_subtask_ref
                return mock_subtasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.put(
            "/api/tasks/task1/subtasks/sub1",
            json={"title": "New Title", "description": "New Desc"},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200


class TestRemainingEdgeCases:
    """Test remaining edge cases"""
    
    def test_create_subtask_empty_title(self, client, mock_db, monkeypatch):
        """Lines 818, 823: Empty title validation"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"}
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task_doc
        
        # Test None title
        response = client.post(
            "/api/tasks/task1/subtasks",
            json={"title": None},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 400
    
    def test_update_task_no_fields(self, client, mock_db, monkeypatch):
        """Line 554: No fields to update"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"},
            "status": "To Do"
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task_doc
        
        # Empty json body
        response = client.put(
            "/api/tasks/task1",
            json={},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 400
