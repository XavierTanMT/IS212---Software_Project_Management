"""
Final 5 missing branches for 100% coverage
Lines: 85, 188->185, 239, 477->491, 750->762
"""

import pytest
import sys
from unittest.mock import Mock, patch

fake_firestore = sys.modules.get("firebase_admin.firestore")


@pytest.fixture
def mock_db():
    return Mock()


class TestFinal5Branches:
    """The last 5 missing branch paths"""
    
    def test_line_85_manager_views_task_creator_not_exists(self, client, mock_db, monkeypatch):
        """Line 85: is_managed_by returns False when user doesn't exist"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_manager_doc = Mock()
        mock_manager_doc.exists = True
        mock_manager_doc.to_dict.return_value = {
            "user_id": "manager1",
            "role": "manager"
        }
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "ghost_creator"},
            "assigned_to": {"user_id": "ghost_assignee"},
            "project_id": "proj1",
            "title": "Task"
        }
        
        mock_ghost_user = Mock()
        mock_ghost_user.exists = False  # User doesn't exist - line 85
        
        mock_no_membership = Mock()
        mock_no_membership.exists = False
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                def doc_side_effect(uid):
                    mock_doc = Mock()
                    if uid == "manager1":
                        mock_doc.get.return_value = mock_manager_doc
                    elif uid in ["ghost_creator", "ghost_assignee"]:
                        mock_doc.get.return_value = mock_ghost_user
                    else:
                        other = Mock()
                        other.exists = True
                        other.to_dict.return_value = {"user_id": uid}
                        mock_doc.get.return_value = other
                    return mock_doc
                mock_users.document.side_effect = doc_side_effect
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value.get.return_value = mock_task_doc
                return mock_tasks
            elif name == "memberships":
                mock_memberships = Mock()
                mock_memberships.document.return_value.get.return_value = mock_no_membership
                return mock_memberships
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get("/api/tasks/task1", headers={"X-User-Id": "manager1"})
        assert response.status_code == 404  # Can't view - line 85 returns False
    
    def test_line_188_member_has_empty_user_id(self, client, mock_db, monkeypatch):
        """Line 188->185: Project member dict has no user_id, skip to next iteration"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"user_id": "user1", "role": "staff"}
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"},
            "assigned_to": {"user_id": "user1"},
            "project_id": "proj1",
            "title": "Old"
        }
        
        # Member with no user_id
        mock_bad_member = Mock()
        mock_bad_member.to_dict.return_value = {}  # No user_id - line 188 is False, go to 185
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_ref = Mock()
                mock_ref.get.return_value = mock_task_doc
                mock_ref.update.return_value = None
                mock_tasks.document.return_value = mock_ref
                return mock_tasks
            elif name == "memberships":
                mock_memberships = Mock()
                mock_memberships.where.return_value = mock_memberships
                mock_memberships.stream.return_value = [mock_bad_member]
                return mock_memberships
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_edit_task", return_value=True):
            response = client.put(
                "/api/tasks/task1",
                json={"title": "New"},
                headers={"X-User-Id": "user1"}
            )
        assert response.status_code == 200
    
    def test_line_239_recurring_task_due_has_timezone(self, client, mock_db, monkeypatch):
        """Line 239: Due date already has timezone, skip the replacement (branch not taken)"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"user_id": "user1", "role": "staff"}
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"},
            "assigned_to": {"user_id": "user1"},
            "status": "In Progress",
            "recurring": True,
            "recurring_interval_days": 7,
            "recurring_original_due_date": "2024-01-15T10:00:00+00:00"  # HAS timezone
        }
        
        mock_new_ref = Mock()
        mock_new_ref.id = "new_task"
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_viewer_doc
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_ref = Mock()
                mock_ref.get.return_value = mock_task_doc
                mock_ref.update.return_value = None
                mock_tasks.document.return_value = mock_ref
                mock_tasks.add.return_value = (None, mock_new_ref)
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_edit_task", return_value=True):
            response = client.put(
                "/api/tasks/task1",
                json={"status": "Completed"},
                headers={"X-User-Id": "user1"}
            )
        assert response.status_code == 200
    
    def test_line_477_viewer_doc_not_exists_in_manager_check(self, client, mock_db, monkeypatch):
        """Line 477->491: When checking if viewer reports to owner, viewer doc doesn't exist"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        call_count = [0]
        
        mock_viewer_exists = Mock()
        mock_viewer_exists.exists = True
        mock_viewer_exists.to_dict.return_value = {"user_id": "staff1", "role": "staff"}
        
        mock_viewer_not_exists = Mock()
        mock_viewer_not_exists.exists = False  # Line 477 check fails
        
        mock_project = Mock()
        mock_project.exists = True
        mock_project.to_dict.return_value = {"owner_id": "owner1"}
        
        mock_no_member = Mock()
        mock_no_member.exists = False
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                def doc_side_effect(uid):
                    mock_doc = Mock()
                    if uid == "staff1":
                        call_count[0] += 1
                        # First 2 calls for role check
                        if call_count[0] <= 2:
                            mock_doc.get.return_value = mock_viewer_exists
                        else:  # Manager check - doesn't exist
                            mock_doc.get.return_value = mock_viewer_not_exists
                    else:
                        other = Mock()
                        other.exists = True
                        other.to_dict.return_value = {"user_id": uid}
                        mock_doc.get.return_value = other
                    return mock_doc
                mock_users.document.side_effect = doc_side_effect
                return mock_users
            elif name == "projects":
                mock_projects = Mock()
                mock_projects.document.return_value.get.return_value = mock_project
                return mock_projects
            elif name == "memberships":
                mock_memberships = Mock()
                mock_memberships.document.return_value.get.return_value = mock_no_member
                return mock_memberships
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.where.return_value = mock_tasks
                mock_tasks.stream.return_value = []
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get("/api/tasks?project_id=proj1", headers={"X-User-Id": "staff1"})
        assert response.status_code == 200
    
    def test_line_750_reassign_no_previous_assignee(self, client, mock_db, monkeypatch):
        """Line 750->762: No previous assignee, skip notification to old assignee"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer = Mock()
        mock_viewer.exists = True
        mock_viewer.to_dict.return_value = {"user_id": "mgr", "role": "manager"}
        
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "creator"},
            # NO assigned_to - line 750 condition is False
            "project_id": "proj1"
        }
        
        mock_new_user = Mock()
        mock_new_user.exists = True
        mock_new_user.to_dict.return_value = {"user_id": "new", "name": "New"}
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                def doc_side_effect(uid):
                    mock_doc = Mock()
                    if uid == "mgr":
                        mock_doc.get.return_value = mock_viewer
                    elif uid == "new":
                        mock_doc.get.return_value = mock_new_user
                    else:
                        other = Mock()
                        other.exists = True
                        other.to_dict.return_value = {"user_id": uid}
                        mock_doc.get.return_value = other
                    return mock_doc
                mock_users.document.side_effect = doc_side_effect
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_ref = Mock()
                mock_ref.get.return_value = mock_task
                mock_ref.update.return_value = None
                mock_tasks.document.return_value = mock_ref
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_edit_task", return_value=True):
            with patch("backend.api.notifications.create_notification"):
                response = client.patch(
                    "/api/tasks/task1/reassign",
                    json={"new_assigned_to_id": "new"},
                    headers={"X-User-Id": "mgr"}
                )
        assert response.status_code == 200
