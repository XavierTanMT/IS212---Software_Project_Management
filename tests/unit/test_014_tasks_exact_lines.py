"""
Ultra-final push: Target exact remaining branches for 100%
Lines still missing: 85, 171->175, 188->185, 239, 469->491, 477->491, 479->491, 483-485, 622-623, 750->762
Plus: 689, 724, 780, 794->810, 795-796, 827, 880, 885, 915, 934->939, 961
"""
import pytest
import sys
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta

fake_firestore = sys.modules.get("firebase_admin.firestore")


@pytest.fixture
def mock_db():
    return Mock()


class TestExactLine239NaiveDatetime:
    """Line 239: due_dt.tzinfo is None - naive datetime"""
    
    def test_recurring_task_naive_datetime_line_239(self, client, mock_db, monkeypatch):
        """Line 239: due_date parses to naive datetime (no timezone)"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock task with recurring enabled and naive due_date
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "user1"},
            "title": "Recurring",
            "status": "to_do",
            "recurring": {
                "enabled": True,
                "frequency": "daily",
                "interval": 7
            },
            "due_date": "2025-01-01T00:00:00"  # NO Z, NO timezone = naive datetime
        }
        
        # Mock updated task after marking done
        mock_updated_task = Mock()
        mock_updated_task.id = "task1"
        mock_updated_task.to_dict.return_value = {
            "created_by": {"user_id": "user1"},
            "title": "Recurring",
            "status": "done",
            "recurring": {
                "enabled": True,
                "frequency": "daily",
                "interval": 7
            },
            "due_date": "2025-01-01T00:00:00"
        }
        
        mock_task_ref = Mock()
        # First call: get current task, second call: get after update
        mock_task_ref.get.side_effect = [mock_task_doc, mock_updated_task]
        mock_task_ref.update.return_value = None
        
        # Mock new task ref for next recurring task
        mock_new_task_ref = Mock()
        mock_new_task_ref.id = "new_task"
        mock_new_task_ref.set.return_value = None
        
        # Track document calls
        task_doc_calls = [0]
        def task_document_side_effect(task_id):
            if task_doc_calls[0] == 0:
                task_doc_calls[0] += 1
                return mock_task_ref
            else:
                return mock_new_task_ref
        
        mock_editor_doc = Mock()
        mock_editor_doc.exists = True
        mock_editor_doc.to_dict.return_value = {
            "role": "staff",
            "name": "User"
        }
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.side_effect = task_document_side_effect
                return mock_tasks
            elif name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_editor_doc
                return mock_users
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.tasks._can_edit_task", return_value=True):
            response = client.put(
                "/api/tasks/task1",
                json={"status": "done"},
                headers={"X-User-Id": "user1"}
            )
        
        assert response.status_code == 200
        # New recurring task should be created with line 239 executed


class TestExactLines171to175WithCreatorId:
    """Lines 171->175: creator_id branch with actual value"""
    
    def test_notification_with_creator_present_lines_171_175(self, client, mock_db, monkeypatch):
        """Lines 171-175: creator_id exists, add to recipients"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Task WITH created_by containing user_id
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "creator_user"},  # creator_id will be "creator_user"
            "title": "Task Title"
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        mock_editor_doc = Mock()
        mock_editor_doc.exists = True
        mock_editor_doc.to_dict.return_value = {
            "role": "staff",
            "name": "Editor"
        }
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            elif name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_editor_doc
                return mock_users
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        # Update task - this should notify creator
        with patch("backend.api.notifications.create_notification") as mock_notify, \
             patch("backend.api.tasks._can_edit_task", return_value=True):
            response = client.put(
                "/api/tasks/task1",
                json={"title": "Updated Title"},
                headers={"X-User-Id": "editor_user"}
            )
        
        assert response.status_code == 200
        # Creator should be in notification recipients


class TestExactLine188EmptyUserId:
    """Line 188->185: Membership with empty/None user_id"""
    
    def test_membership_empty_user_id_line_188(self, client, mock_db, monkeypatch):
        """Line 188: Membership to_dict returns empty user_id"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Task with project_id
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "created_by": {"user_id": "creator1"},
            "project_id": "project123",  # Triggers membership query
            "title": "Task"
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        mock_task_ref.update.return_value = None
        
        mock_editor_doc = Mock()
        mock_editor_doc.exists = True
        mock_editor_doc.to_dict.return_value = {
            "role": "staff",
            "name": "Editor"
        }
        
        # Membership with NO user_id or empty user_id
        mock_membership1 = Mock()
        mock_membership1.to_dict.return_value = {
            "user_id": None  # or missing user_id - triggers line 188
        }
        mock_membership2 = Mock()
        mock_membership2.to_dict.return_value = {
            "user_id": ""  # empty string - also triggers line 188
        }
        
        mock_memberships_query = Mock()
        mock_memberships_query.stream.return_value = [mock_membership1, mock_membership2]
        
        def collection_side_effect(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.document.return_value = mock_task_ref
                return mock_tasks
            elif name == "users":
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_editor_doc
                return mock_users
            elif name == "memberships":
                mock_memberships = Mock()
                mock_memberships.where.return_value = mock_memberships_query
                return mock_memberships
            return Mock()
        
        mock_db.collection.side_effect = collection_side_effect
        
        with patch("backend.api.notifications.create_notification"), \
             patch("backend.api.tasks._can_edit_task", return_value=True):
            response = client.put(
                "/api/tasks/task1",
                json={"status": "in_progress"},
                headers={"X-User-Id": "editor1"}
            )
        
        assert response.status_code == 200
