"""
Final 2 branches for 100% coverage: 85, 477->491
"""

import pytest
import sys
from unittest.mock import Mock, patch

fake_firestore = sys.modules.get("firebase_admin.firestore")


@pytest.fixture
def mock_db():
    return Mock()


class TestLine85:
    """Line 85: is_managed_by returns False when user_id or manager_id is None/empty"""
    
    def test_line_85_is_managed_by_empty_user_id(self, client, mock_db, monkeypatch):
        """Line 85: Manager viewing task where creator_id or assignee_id is None/empty"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Manager doc
        mock_manager_doc = Mock()
        mock_manager_doc.exists = True
        mock_manager_doc.to_dict.return_value = {
            "user_id": "manager1",
            "role": "manager"
        }
        
        # Task where created_by is None or has no user_id
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {},  # No user_id field - creator_id will be None
            "assigned_to": {},  # No user_id field - assignee_id will be None
            "title": "Task"
            # NO project_id - ensures we reach the manager role check
        }
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                
                def document_side_effect(user_id):
                    mock_doc = Mock()
                    # Only return manager doc for manager1
                    if user_id == "manager1":
                        mock_doc.get.return_value = mock_manager_doc
                    else:
                        # For None or other user_ids (shouldn't be called if is_managed_by checks first)
                        other_doc = Mock()
                        other_doc.exists = False
                        mock_doc.get.return_value = other_doc
                    return mock_doc
                
                mock_users.document = document_side_effect
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value.get.return_value = mock_task_doc
                return mock_tasks
            return Mock()
        
        mock_db.collection = collection_side_effect
        
        response = client.get("/api/tasks/task1", headers={"X-User-Id": "manager1"})
        
        # Should get 404 because manager can't view
        # is_managed_by(None, "manager1") returns False at line 85 (user_id is None)
        assert response.status_code == 404


class TestLine477:
    """Line 477->491: vdoc.exists is False, skip manager_id check"""
    
    def test_line_477_viewer_doc_not_exists_in_owner_check(self, client, mock_db, monkeypatch):
        """Line 477->491: In list_tasks with project_id filter, viewer doc doesn't exist on owner check"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Track which calls are for role vs owner check
        viewer_get_count = [0]
        
        # First call(s) for role check - exists
        mock_viewer_for_role = Mock()
        mock_viewer_for_role.exists = True
        mock_viewer_for_role.to_dict.return_value = {
            "user_id": "staff1",
            "role": "staff"  # Not admin
        }
        
        # Later call for owner check - doesn't exist
        mock_viewer_for_owner = Mock()
        mock_viewer_for_owner.exists = False  # Line 477 check fails
        
        # Project with owner
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {
            "owner_id": "owner1"  # Not viewer
        }
        
        # No membership
        mock_no_membership = Mock()
        mock_no_membership.exists = False
        
        def collection_side_effect(name):
            if name == "users":
                mock_users = Mock()
                
                def document_side_effect(user_id):
                    mock_doc = Mock()
                    
                    def get_side_effect():
                        if user_id == "staff1":
                            viewer_get_count[0] += 1
                            # First call for role determination
                            if viewer_get_count[0] == 1:
                                return mock_viewer_for_role
                            else:
                                # Second call - owner check - doesn't exist (line 477)
                                return mock_viewer_for_owner
                        else:
                            other = Mock()
                            other.exists = True
                            other.to_dict.return_value = {"user_id": user_id}
                            return other
                    
                    mock_doc.get = get_side_effect
                    return mock_doc
                
                mock_users.document = document_side_effect
                return mock_users
            elif name == "projects":
                mock_projects = Mock()
                mock_projects.document.return_value.get.return_value = mock_project_doc
                return mock_projects
            elif name == "memberships":
                mock_memberships = Mock()
                mock_memberships.document.return_value.get.return_value = mock_no_membership
                return mock_memberships
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.where.return_value = mock_tasks
                mock_tasks.stream.return_value = []
                return mock_tasks
            return Mock()
        
        mock_db.collection = collection_side_effect
        
        response = client.get("/api/tasks?project_id=proj1", headers={"X-User-Id": "staff1"})
        
        assert response.status_code == 200
        # Verify owner check was reached (2 calls: 1 for role, 1 for owner check at line 477)
        assert viewer_get_count[0] == 2
