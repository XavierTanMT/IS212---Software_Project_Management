"""
Tests for the final 1% - missing branch coverage
Targeting: 85, 171->175, 188->185, 469->491, 477->491, 479->491, 483-485, 750->762
"""

import pytest
import sys
from unittest.mock import Mock, patch

fake_firestore = sys.modules.get("firebase_admin.firestore")


@pytest.fixture
def mock_db():
    return Mock()


class TestLine85IsManagedBy:
    """Line 85: User doesn't exist in is_managed_by check"""
    
    def test_managed_by_filter_user_not_exists_line_85(self, client, mock_db, monkeypatch):
        """Line 85: In is_managed_by, the user document doesn't exist"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "manager1",
            "role": "manager"
        }
        
        # Mock a task where creator doesn't exist as a user
        mock_task = Mock()
        mock_task.id = "task1"
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "nonexistent_creator"},  # This user doesn't exist
            "assigned_to": {"user_id": "some_assignee"}
        }
        
        # Mock non-existent user
        mock_nonexistent_user = Mock()
        mock_nonexistent_user.exists = False  # User doesn't exist - triggers line 85
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                
                def document_side_effect(user_id):
                    mock_doc = Mock()
                    if user_id == "manager1":
                        mock_doc.get.return_value = mock_viewer_doc
                    elif user_id == "nonexistent_creator" or user_id == "some_assignee":
                        # Return non-existent user - this triggers line 85
                        mock_doc.get.return_value = mock_nonexistent_user
                    else:
                        mock_other = Mock()
                        mock_other.exists = True
                        mock_other.to_dict.return_value = {"user_id": user_id}
                        mock_doc.get.return_value = mock_other
                    return mock_doc
                
                mock_users.document.side_effect = document_side_effect
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.where.return_value = mock_tasks
                mock_tasks.stream.return_value = [mock_task]
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        # Request with managed_by filter - will check if nonexistent_creator is managed by manager1
        response = client.get(
            "/api/tasks?managed_by=manager1",
            headers={"X-User-Id": "manager1"}
        )
        
        assert response.status_code == 200
        # Should hit line 85 when checking if nonexistent user is managed by manager1


class TestMissingBranches:
    """Test the branches that skip certain paths"""
    
    def test_update_task_no_creator_line_171(self, client, mock_db, monkeypatch):
        """Line 171->175: Task has no created_by (skip creator notification)"""
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
            # NO created_by field - should skip line 171-173
            "assigned_to": {"user_id": "user1"},
            "title": "Old title"
        }
        
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
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_edit_task", return_value=True):
            response = client.put(
                "/api/tasks/task1",
                json={"title": "New title"},
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 200
        # Should skip creator notification (line 171->175 branch not taken)
    
    def test_update_task_no_assignee_line_188(self, client, mock_db, monkeypatch):
        """Line 188->185: Task has no assigned_to (skip assignee notification)"""
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
            # NO assigned_to field - should skip line 175-177
            "title": "Old title"
        }
        
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
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_edit_task", return_value=True):
            response = client.put(
                "/api/tasks/task1",
                json={"title": "New title"},
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 200
        # Should skip assignee notification (line 188->185 branch not taken)
    
    def test_project_no_owner_id_line_469(self, client, mock_db, monkeypatch):
        """Line 469->491: Project has no owner_id (skip owner checks)"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "staff1",
            "role": "staff"
        }
        
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {
            # NO owner_id field - should skip lines 469-482
        }
        
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
        # Should skip owner checks (line 469->491 branch not taken)
    
    def test_project_viewer_not_owner_vdoc_not_exists_line_477(self, client, mock_db, monkeypatch):
        """Line 477->491: Viewer is not owner and vdoc doesn't exist"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = False  # Viewer doc doesn't exist
        
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {
            "owner_id": "owner1"  # Different from viewer
        }
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                
                def document_side_effect(user_id):
                    mock_doc = Mock()
                    if user_id == "staff1":
                        mock_doc.get.return_value = mock_viewer_doc
                    else:
                        mock_other = Mock()
                        mock_other.exists = True
                        mock_other.to_dict.return_value = {"user_id": user_id, "role": "staff"}
                        mock_doc.get.return_value = mock_other
                    return mock_doc
                
                mock_users.document.side_effect = document_side_effect
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
        # Should skip manager check (line 477->491 branch when vdoc.exists is False)
    
    def test_project_viewer_manager_not_owner_line_479(self, client, mock_db, monkeypatch):
        """Line 479->491: Viewer reports to different manager (not project owner)"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "staff1",
            "role": "staff",
            "manager_id": "manager2"  # Different from project owner
        }
        
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {
            "owner_id": "owner1"
        }
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                
                def document_side_effect(user_id):
                    mock_doc = Mock()
                    if user_id == "staff1":
                        mock_doc.get.return_value = mock_viewer_doc
                    else:
                        mock_other = Mock()
                        mock_other.exists = True
                        mock_other.to_dict.return_value = {"user_id": user_id, "role": "staff"}
                        mock_doc.get.return_value = mock_other
                    return mock_doc
                
                mock_users.document.side_effect = document_side_effect
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
        # Should skip adding project tasks (line 479->491, manager_id doesn't match)
    
    def test_project_owner_check_exception_line_483(self, client, mock_db, monkeypatch):
        """Line 483-485: Exception during owner check"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "staff1",
            "role": "staff"
        }
        
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.side_effect = Exception("Database error")
        
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
        # Should catch exception and continue (lines 483-485)
    
    def test_reassign_with_previous_assignee_notification_exception_line_750(self, client, mock_db, monkeypatch):
        """Line 750->762: Exception notifying previous assignee (when they exist)"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {
            "user_id": "manager1",
            "role": "manager"
        }
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"},
            "assigned_to": {"user_id": "old_assignee"},  # Has previous assignee
            "project_id": "proj1"
        }
        
        mock_new_assignee_doc = Mock()
        mock_new_assignee_doc.exists = True
        mock_new_assignee_doc.to_dict.return_value = {
            "user_id": "new_assignee",
            "name": "New User"
        }
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                
                def document_side_effect(user_id):
                    mock_doc = Mock()
                    if user_id == "manager1":
                        mock_doc.get.return_value = mock_viewer_doc
                    elif user_id == "new_assignee":
                        mock_doc.get.return_value = mock_new_assignee_doc
                    else:
                        mock_other = Mock()
                        mock_other.exists = True
                        mock_other.to_dict.return_value = {"user_id": user_id}
                        mock_doc.get.return_value = mock_other
                    return mock_doc
                
                mock_users.document.side_effect = document_side_effect
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_task_ref = Mock()
                mock_task_ref.get.return_value = mock_task_doc
                mock_task_ref.update.return_value = None
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        # Track notification calls
        notification_calls = []
        
        def mock_create_notification(*args, **kwargs):
            notification_calls.append((args, kwargs))
            if len(notification_calls) == 2:  # Second call (to previous assignee)
                raise Exception("Notification failed")
        
        with patch("backend.api.tasks._can_edit_task", return_value=True):
            with patch("backend.api.notifications.create_notification", side_effect=mock_create_notification):
                response = client.patch(
                    "/api/tasks/task1/reassign",
                    json={"new_assigned_to_id": "new_assignee"},
                    headers={"X-User-Id": "manager1"}
                )
        
        assert response.status_code == 200
        # Should catch exception when notifying previous assignee (line 750->762)
