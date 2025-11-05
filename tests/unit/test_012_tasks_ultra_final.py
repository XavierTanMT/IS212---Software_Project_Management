"""
FINAL ULTRA tests - using proven patterns from existing tests
Targeting: 85, 171-175, 182-189, 239, 369-370, 469-491, 622-623, 750-762
"""
import pytest
import sys
from unittest.mock import Mock, patch

fake_firestore = sys.modules.get("firebase_admin.firestore")


@pytest.fixture
def mock_db():
    return Mock()


class TestMissingLinesWithProvenPatterns:
    """Using patterns from existing passing tests"""
    
    def test_line_554_already_covered_by_test_009(self, client):
        """Line 554 was already covered - this confirms it"""
        response = client.get("/api/tasks/task1")
        assert response.status_code == 401
    
    def test_lines_750_762_reassign_previous_assignee_notification(self, client, mock_db, monkeypatch):
        """Lines 750-762: Using working pattern from test_009"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "manager"}
        
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "assigned_to": {"user_id": "user2"},  # Has previous assignee
            "title": "Task"
        }
        
        mock_task_ref = Mock()
        mock_task_ref.id = "task1"
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        mock_new_assignee = Mock()
        mock_new_assignee.exists = True
        mock_new_assignee.to_dict.return_value = {
            "name": "New User",
            "email": "new@example.com"
        }
        
        def collection_side_effect(name):
            if name == "users":
                def user_doc(uid):
                    m = Mock()
                    if uid == "manager1":
                        m.get.return_value = mock_viewer_doc
                    else:
                        m.get.return_value = mock_new_assignee
                    return m
                mock_users = Mock()
                mock_users.document.side_effect = user_doc
                return mock_users
            elif name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.notifications") as mock_notif:
            # First call succeeds, second call fails (line 759-760 exception)
            mock_notif.create_notification.side_effect = [
                None,  # First notification succeeds
                Exception("Second notification fails")  # Lines 759-760
            ]
            
            response = client.patch(
                "/api/tasks/task1/reassign",
                json={"new_assigned_to_id": "user3"},
                headers={"X-User-Id": "manager1"}
            )
        
        assert response.status_code == 200
        # Line 750: current_assigned_to_id != new_assigned_to_id triggers notification
        # Lines 759-760: Exception handler catches second notification failure
        # Line 762: Returns success despite exception


class TestComplexProjectFilteringRealScenarios:
    """Lines 469-491: Real scenarios that trigger each branch"""
    
    def test_lines_469_473_viewer_is_project_owner(self, client, mock_db, monkeypatch):
        """Lines 469-473: owner_id exists and viewer IS the owner"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "staff"}
        
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {
            "owner_id": "viewer1",  # Line 469: owner_id exists
            "name": "Project"
        }
        
        mock_tasks_query = Mock()
        mock_tasks_query.limit.return_value = Mock(stream=Mock(return_value=[]))
        mock_tasks_where = Mock()
        mock_tasks_where.where.return_value = mock_tasks_query
        
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
                return mock_tasks_where
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        # Line 471: viewer == owner_id
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "viewer1"}
        )
        
        assert response.status_code == 200
    
    def test_lines_477_482_viewer_reports_to_owner(self, client, mock_db, monkeypatch):
        """Lines 477-482: viewer's manager_id matches owner_id"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True  # Line 477
        mock_viewer_doc.to_dict.return_value = {
            "role": "staff",
            "manager_id": "owner1"  # Line 479
        }
        
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {
            "owner_id": "owner1",
            "name": "Project"
        }
        
        mock_tasks_query = Mock()
        mock_tasks_query.limit.return_value = Mock(stream=Mock(return_value=[]))
        mock_tasks_where = Mock()
        mock_tasks_where.where.return_value = mock_tasks_query
        
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
                return mock_tasks_where
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        response = client.get(
            "/api/tasks?project_id=proj1",
            headers={"X-User-Id": "viewer2"}
        )
        
        assert response.status_code == 200
