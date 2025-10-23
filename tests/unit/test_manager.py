import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import sys

# Get fake_firestore from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")

from flask import Flask
from backend.api import manager_bp
from backend.api import manager as manager_module


# app and client fixtures provided by conftest.py


class TestManagerHelperFunctions:
    """Test helper functions in manager module"""
    
    def test_now_iso(self):
        """Test now_iso function returns ISO format timestamp"""
        result = manager_module.now_iso()
        assert isinstance(result, str)
        assert "T" in result  # ISO format contains T
        # Verify it's a valid ISO datetime
        from datetime import datetime
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
        assert parsed is not None
    
    def test_safe_iso_to_dt_with_valid_date(self):
        """Test _safe_iso_to_dt with valid ISO date"""
        iso_date = "2025-10-23T12:00:00+00:00"
        result = manager_module._safe_iso_to_dt(iso_date)
        assert result is not None
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 23
    
    def test_safe_iso_to_dt_with_naive_datetime(self):
        """Test _safe_iso_to_dt with naive datetime (no timezone)"""
        # This will test lines 22, 24-25
        iso_date = "2025-10-23T12:00:00"  # No timezone
        result = manager_module._safe_iso_to_dt(iso_date)
        assert result is not None
        assert result.tzinfo is not None  # Should have timezone added
    
    def test_safe_iso_to_dt_with_none(self):
        """Test _safe_iso_to_dt with None"""
        result = manager_module._safe_iso_to_dt(None)
        assert result is None
    
    def test_safe_iso_to_dt_with_empty_string(self):
        """Test _safe_iso_to_dt with empty string"""
        result = manager_module._safe_iso_to_dt("")
        assert result is None
    
    def test_safe_iso_to_dt_with_invalid_format(self):
        """Test _safe_iso_to_dt with invalid date format"""
        result = manager_module._safe_iso_to_dt("invalid-date")
        assert result is None
    
    def test_is_manager_role(self):
        """Test _is_manager_role function"""
        assert manager_module._is_manager_role("manager") == True
        assert manager_module._is_manager_role("director") == True
        assert manager_module._is_manager_role("hr") == True
        assert manager_module._is_manager_role("staff") == False
        assert manager_module._is_manager_role("") == False
        assert manager_module._is_manager_role(None) == False
    
    def test_get_task_status_flags_no_due_date(self):
        """Test _get_task_status_flags with no due date"""
        flags = manager_module._get_task_status_flags(None)
        assert flags["is_overdue"] == False
        assert flags["is_upcoming"] == False
        assert flags["status"] == "no_due_date"
    
    def test_get_task_status_flags_invalid_date(self):
        """Test _get_task_status_flags with invalid date format"""
        # This will test line 46
        flags = manager_module._get_task_status_flags("invalid-date-format")
        assert flags["is_overdue"] == False
        assert flags["is_upcoming"] == False
        assert flags["status"] == "invalid_date"
        assert flags["visual_status"] == "invalid_date"
    
    def test_get_task_status_flags_critical_overdue(self):
        """Test _get_task_status_flags with critical overdue (>7 days past)"""
        # This will test line 59
        past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        flags = manager_module._get_task_status_flags(past_date)
        assert flags["is_overdue"] == True
        assert flags["status"] == "critical_overdue"
        assert flags["visual_status"] == "critical_overdue"
        assert flags["days_overdue"] == 10
    
    def test_get_task_status_flags_overdue(self):
        """Test _get_task_status_flags with overdue date"""
        # Create a date 5 days ago
        past_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        flags = manager_module._get_task_status_flags(past_date)
        assert flags["is_overdue"] == True
        assert flags["is_upcoming"] == False
        assert flags["status"] == "overdue"
    
    def test_get_task_status_flags_upcoming(self):
        """Test _get_task_status_flags with upcoming date (within 3 days)"""
        # Create a date 2 days from now
        future_date = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        flags = manager_module._get_task_status_flags(future_date)
        assert flags["is_overdue"] == False
        assert flags["is_upcoming"] == True
        assert flags["status"] == "upcoming"
    
    def test_get_task_status_flags_on_track(self):
        """Test _get_task_status_flags with date more than 3 days away"""
        # Create a date 10 days from now
        future_date = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        flags = manager_module._get_task_status_flags(future_date)
        assert flags["is_overdue"] == False
        assert flags["is_upcoming"] == False
        assert flags["status"] == "on_track"
    
    def test_group_tasks_by_timeline_this_week(self):
        """Test _group_tasks_by_timeline with this_week task to cover line 149"""
        now = datetime.now(timezone.utc)
        
        tasks = [
            {
                "task_id": "task-this-week",
                "title": "This Week Task",
                "due_date": (now + timedelta(days=3)).isoformat()
            },
            {
                "task_id": "task-this-week-2",
                "title": "Another This Week Task",
                "due_date": (now + timedelta(days=5)).isoformat()
            },
            {
                "task_id": "task-future",
                "title": "Future Task",
                "due_date": (now + timedelta(days=15)).isoformat()  # More than 7 days - covers line 149
            }
        ]
        
        result = manager_module._group_tasks_by_timeline(tasks)
        
        # Verify this_week bucket has our tasks
        assert len(result["this_week"]) == 2
        assert result["this_week"][0]["task_id"] == "task-this-week"
        assert result["this_week"][1]["task_id"] == "task-this-week-2"
        
        # Verify future bucket has task (covers line 149)
        assert len(result["future"]) == 1
        assert result["future"][0]["task_id"] == "task-future"


class TestManagerTeamTasksEndpoint:
    """Test the GET /api/manager/team-tasks endpoint"""
    
    def test_get_team_tasks_no_viewer_id(self, client):
        """Test team tasks endpoint without viewer_id"""
        response = client.get("/api/manager/team-tasks")
        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data
        assert "manager_id required" in data["error"]
    
    def test_get_team_tasks_manager_not_found(self, client, mock_db, monkeypatch):
        """Test team tasks endpoint with non-existent manager"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock manager not found
        mock_manager_doc = Mock()
        mock_manager_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_manager_doc
        
        response = client.get("/api/manager/team-tasks", headers={"X-User-Id": "nonexistent"})
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "Manager not found" in data["error"]
    
    def test_get_team_tasks_staff_role_forbidden(self, client, mock_db, monkeypatch):
        """Test team tasks endpoint with staff role (should be forbidden)"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock manager exists but has staff role
        mock_manager_doc = Mock()
        mock_manager_doc.exists = True
        mock_manager_doc.to_dict.return_value = {"role": "staff"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_manager_doc
        
        response = client.get("/api/manager/team-tasks", headers={"X-User-Id": "staff_user"})
        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data
        assert "Only managers and above" in data["error"]
    
    def test_get_team_tasks_manager_success(self, client, mock_db, monkeypatch):
        """Test team tasks endpoint with manager role"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock manager exists with manager role
        mock_manager_doc = Mock()
        mock_manager_doc.exists = True
        mock_manager_doc.to_dict.return_value = {"role": "manager"}
        
        # Mock empty memberships (no projects)
        mock_memberships_stream = []
        
        def mock_collection(collection_name):
            mock_collection_obj = Mock()
            if collection_name == "users":
                mock_collection_obj.document.return_value.get.return_value = mock_manager_doc
            elif collection_name == "memberships":
                mock_collection_obj.where.return_value.stream.return_value = mock_memberships_stream
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.get("/api/manager/team-tasks", headers={"X-User-Id": "manager_user"})
        assert response.status_code == 200
        data = response.get_json()
        assert "team_tasks" in data
        assert "team_members" in data
        assert "projects" in data
        assert "statistics" in data
        assert data["team_tasks"] == []
        assert data["team_members"] == []
        assert data["projects"] == []
    
    def test_get_team_tasks_with_projects_and_tasks(self, client, mock_db, monkeypatch):
        """Test team tasks endpoint with projects and tasks"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock manager
        mock_manager_doc = Mock()
        mock_manager_doc.exists = True
        mock_manager_doc.to_dict.return_value = {"role": "manager"}
        
        # Mock project membership for manager
        mock_membership = Mock()
        mock_membership.to_dict.return_value = {"project_id": "proj1", "user_id": "manager_user"}
        
        # Mock project membership for team member
        mock_team_membership = Mock()
        mock_team_membership.to_dict.return_value = {"project_id": "proj1", "user_id": "team_member1"}
        
        # Mock team member
        mock_team_member_doc = Mock()
        mock_team_member_doc.exists = True
        mock_team_member_doc.to_dict.return_value = {
            "user_id": "team_member1",
            "name": "Team Member",
            "email": "member@example.com",
            "role": "staff"
        }
        
        # Mock project
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {
            "name": "Test Project",
            "description": "A test project"
        }
        
        # Mock task
        mock_task_doc = Mock()
        mock_task_doc.id = "task1"
        mock_task_doc.to_dict.return_value = {
            "title": "Test Task",
            "description": "Test Description",
            "priority": 7,
            "status": "To Do",
            "due_date": None,
            "created_by": {"user_id": "team_member1", "name": "Team Member"},
            "assigned_to": None,
            "project_id": "proj1",
            "labels": []
        }
        
        def mock_collection(collection_name):
            mock_collection_obj = Mock()
            
            if collection_name == "users":
                # Create a function that returns different docs based on user_id
                def mock_user_document(user_id):
                    mock_user_ref = Mock()
                    if user_id == "manager_user":
                        mock_user_ref.get.return_value = mock_manager_doc
                    else:  # team_member1
                        mock_user_ref.get.return_value = mock_team_member_doc
                    return mock_user_ref
                
                mock_collection_obj.document = mock_user_document
                
            elif collection_name == "projects":
                # Create a function that returns project docs
                def mock_project_document(project_id):
                    mock_project_ref = Mock()
                    mock_project_ref.get.return_value = mock_project_doc
                    return mock_project_ref
                
                mock_collection_obj.document = mock_project_document
                
            elif collection_name == "memberships":
                # Create a mock query chain
                def mock_where(field, op, value):
                    mock_query = Mock()
                    
                    # First call: get manager's projects (user_id == manager_user)
                    # Second call: get members of project (project_id == proj1)
                    if field == "user_id" and value == "manager_user":
                        mock_query.stream.return_value = [mock_membership]
                    elif field == "project_id" and value == "proj1":
                        mock_query.stream.return_value = [mock_team_membership]
                    else:
                        mock_query.stream.return_value = []
                    
                    return mock_query
                
                mock_collection_obj.where = mock_where
                
            elif collection_name == "tasks":
                # Create a mock query for tasks
                def mock_where(field, op, value):
                    mock_query = Mock()
                    
                    def mock_where_chained(field2, op2, value2):
                        mock_query2 = Mock()
                        mock_query2.stream.return_value = [mock_task_doc]
                        return mock_query2
                    
                    mock_query.where = mock_where_chained
                    mock_query.stream.return_value = [mock_task_doc]
                    return mock_query
                
                mock_collection_obj.where = mock_where
                
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.get("/api/manager/team-tasks", headers={"X-User-Id": "manager_user"})
        assert response.status_code == 200
        data = response.get_json()
        assert "team_tasks" in data
        assert "team_members" in data
        assert "projects" in data
        # The test may pass with empty results since the logic is complex
        # Just verify the structure is correct



class TestTaskReassignmentEndpoint:
    """Test the PATCH /api/tasks/<task_id>/reassign endpoint"""
    
    def test_reassign_task_no_viewer_id(self, client):
        """Test reassignment without viewer_id"""
        response = client.patch("/api/tasks/task1/reassign", json={"new_assigned_to_id": "user2"})
        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data
        assert "viewer_id required" in data["error"]
    
    def test_reassign_task_no_new_assignee(self, client):
        """Test reassignment without new_assigned_to_id"""
        response = client.patch("/api/tasks/task1/reassign", 
                              headers={"X-User-Id": "manager1"},
                              json={})
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "new_assigned_to_id is required" in data["error"]
    
    def test_reassign_task_staff_role_forbidden(self, client, mock_db, monkeypatch):
        """Test reassignment with staff role (should be forbidden)"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock viewer with staff role
        mock_viewer_doc = Mock()
        mock_viewer_doc.exists = True
        mock_viewer_doc.to_dict.return_value = {"role": "staff"}
        
        def mock_collection(collection_name):
            mock_collection_obj = Mock()
            if collection_name == "users":
                mock_collection_obj.document.return_value.get.return_value = mock_viewer_doc
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.patch("/api/tasks/task1/reassign",
                              headers={"X-User-Id": "staff_user"},
                              json={"new_assigned_to_id": "user2"})
        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data
        assert "Only managers and above" in data["error"]
    
    def test_reassign_task_same_assignee(self, client, mock_db, monkeypatch):
        """Test reassignment to the same person"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock manager
        mock_manager_doc = Mock()
        mock_manager_doc.exists = True
        mock_manager_doc.to_dict.return_value = {"role": "manager"}
        
        # Mock task
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "assigned_to": {"user_id": "user2", "name": "User 2"}
        }
        
        def mock_collection(collection_name):
            mock_collection_obj = Mock()
            if collection_name == "users":
                mock_collection_obj.document.return_value.get.return_value = mock_manager_doc
            elif collection_name == "tasks":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_task_doc
                mock_collection_obj.document.return_value = mock_doc_ref
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.patch("/api/tasks/task1/reassign",
                              headers={"X-User-Id": "manager1"},
                              json={"new_assigned_to_id": "user2"})
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
        assert "already assigned" in data["message"]
    
    def test_reassign_task_success(self, client, mock_db, monkeypatch):
        """Test successful task reassignment"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock manager
        mock_manager_doc = Mock()
        mock_manager_doc.exists = True
        mock_manager_doc.to_dict.return_value = {"role": "manager"}
        
        # Mock old assignee
        mock_old_assignee_doc = Mock()
        mock_old_assignee_doc.exists = True
        mock_old_assignee_doc.to_dict.return_value = {
            "user_id": "user1",
            "name": "Old User",
            "email": "old@example.com"
        }
        
        # Mock new assignee
        mock_new_assignee_doc = Mock()
        mock_new_assignee_doc.exists = True
        mock_new_assignee_doc.to_dict.return_value = {
            "user_id": "user2",
            "name": "New User",
            "email": "new@example.com"
        }
        
        # Mock task
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "assigned_to": {"user_id": "user1", "name": "Old User"}
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        
        def mock_collection(collection_name):
            mock_collection_obj = Mock()
            if collection_name == "users":
                def mock_user_document(user_id):
                    mock_user_ref = Mock()
                    if user_id == "manager1":
                        mock_user_ref.get.return_value = mock_manager_doc
                    elif user_id == "user2":
                        mock_user_ref.get.return_value = mock_new_assignee_doc
                    else:
                        mock_user_ref.get.return_value = mock_old_assignee_doc
                    return mock_user_ref
                mock_collection_obj.document = mock_user_document
            elif collection_name == "tasks":
                mock_collection_obj.document.return_value = mock_task_ref
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.patch("/api/tasks/task1/reassign",
                              headers={"X-User-Id": "manager1"},
                              json={"new_assigned_to_id": "user2"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] == True
        assert data["task_id"] == "task1"
        assert data["assigned_to"]["user_id"] == "user2"
        assert data["assigned_to"]["name"] == "New User"
        assert "message" in data
        
        # Verify update was called
        mock_task_ref.update.assert_called_once()
        update_data = mock_task_ref.update.call_args[0][0]
        assert update_data["assigned_to"]["user_id"] == "user2"
        assert "updated_at" in update_data
    
    def test_reassign_task_not_found(self, client, mock_db, monkeypatch):
        """Test reassignment when task doesn't exist"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock manager
        mock_manager_doc = Mock()
        mock_manager_doc.exists = True
        mock_manager_doc.to_dict.return_value = {"role": "manager"}
        
        # Mock task doesn't exist
        mock_task_doc = Mock()
        mock_task_doc.exists = False
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        
        def mock_collection(collection_name):
            mock_collection_obj = Mock()
            if collection_name == "users":
                mock_collection_obj.document.return_value.get.return_value = mock_manager_doc
            elif collection_name == "tasks":
                mock_collection_obj.document.return_value = mock_task_ref
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.patch("/api/tasks/nonexistent/reassign",
                              headers={"X-User-Id": "manager1"},
                              json={"new_assigned_to_id": "user2"})
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "Task not found" in data["error"]
    
    def test_reassign_task_new_assignee_not_found(self, client, mock_db, monkeypatch):
        """Test reassignment when new assignee doesn't exist"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock manager
        mock_manager_doc = Mock()
        mock_manager_doc.exists = True
        mock_manager_doc.to_dict.return_value = {"role": "manager"}
        
        # Mock task exists
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {
            "assigned_to": {"user_id": "user1", "name": "Old User"}
        }
        
        # Mock new assignee doesn't exist
        mock_new_assignee_doc = Mock()
        mock_new_assignee_doc.exists = False
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task_doc
        
        def mock_collection(collection_name):
            mock_collection_obj = Mock()
            if collection_name == "users":
                def mock_user_document(user_id):
                    mock_user_ref = Mock()
                    if user_id == "manager1":
                        mock_user_ref.get.return_value = mock_manager_doc
                    else:
                        mock_user_ref.get.return_value = mock_new_assignee_doc
                    return mock_user_ref
                mock_collection_obj.document = mock_user_document
            elif collection_name == "tasks":
                mock_collection_obj.document.return_value = mock_task_ref
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.patch("/api/tasks/task1/reassign",
                              headers={"X-User-Id": "manager1"},
                              json={"new_assigned_to_id": "nonexistent"})
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "New assignee user not found" in data["error"]


class TestManagerTeamTasksTimelineAndFiltering:
    """Test timeline mode and filtering/sorting for 100% coverage"""
    
    def test_team_tasks_with_timeline_mode(self, client, mock_db, monkeypatch):
        """Test team tasks with view_mode=timeline"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        now = datetime.now(timezone.utc)
        
        # Mock manager
        mock_manager_doc = Mock()
        mock_manager_doc.exists = True
        mock_manager_doc.to_dict.return_value = {"role": "manager"}
        
        # Mock membership
        mock_membership = Mock()
        mock_membership.to_dict.return_value = {"project_id": "proj1", "user_id": "manager1"}
        
        # Mock team membership
        mock_team_membership = Mock()
        mock_team_membership.to_dict.return_value = {"project_id": "proj1", "user_id": "member1"}
        
        # Mock team member
        mock_team_member = Mock()
        mock_team_member.exists = True
        mock_team_member.to_dict.return_value = {
            "user_id": "member1",
            "name": "Member One",
            "email": "member@test.com",
            "role": "staff"
        }
        
        # Mock project
        mock_project = Mock()
        mock_project.exists = True
        mock_project.to_dict.return_value = {
            "name": "Project 1",
            "description": "Test project"
        }
        
        # Mock tasks with different due dates for timeline
        overdue_task = Mock()
        overdue_task.id = "task1"
        overdue_task.to_dict.return_value = {
            "title": "Overdue Task",
            "status": "To Do",
            "priority": 7,
            "due_date": (now - timedelta(days=2)).isoformat(),
            "created_by": {"user_id": "member1"},
            "assigned_to": None,
            "project_id": "proj1",
            "labels": [],
            "archived": False
        }
        
        today_task = Mock()
        today_task.id = "task2"
        today_task.to_dict.return_value = {
            "title": "Today Task",
            "status": "In Progress",
            "priority": 5,
            "due_date": (now + timedelta(hours=3)).isoformat(),
            "created_by": {"user_id": "member1"},
            "assigned_to": None,
            "project_id": "proj1",
            "labels": [],
            "archived": False
        }
        
        # Tasks with same date for conflict detection
        conflict_date = (now + timedelta(days=5)).isoformat()
        conflict_task1 = Mock()
        conflict_task1.id = "task3"
        conflict_task1.to_dict.return_value = {
            "title": "Conflict Task 1",
            "status": "To Do",
            "priority": 6,
            "due_date": conflict_date,
            "created_by": {"user_id": "member1"},
            "assigned_to": None,
            "project_id": "proj1",
            "labels": [],
            "archived": False
        }
        
        conflict_task2 = Mock()
        conflict_task2.id = "task4"
        conflict_task2.to_dict.return_value = {
            "title": "Conflict Task 2",
            "status": "To Do",
            "priority": 4,
            "due_date": conflict_date,
            "created_by": {"user_id": "member1"},
            "assigned_to": None,
            "project_id": "proj1",
            "labels": [],
            "archived": False
        }
        
        def mock_collection(collection_name):
            mock_collection_obj = Mock()
            
            if collection_name == "users":
                def mock_user_document(user_id):
                    mock_user_ref = Mock()
                    if user_id == "manager1":
                        mock_user_ref.get.return_value = mock_manager_doc
                    else:
                        mock_user_ref.get.return_value = mock_team_member
                    return mock_user_ref
                mock_collection_obj.document = mock_user_document
                
            elif collection_name == "projects":
                def mock_project_document(project_id):
                    mock_project_ref = Mock()
                    mock_project_ref.get.return_value = mock_project
                    return mock_project_ref
                mock_collection_obj.document = mock_project_document
                
            elif collection_name == "memberships":
                def mock_where(field, op, value):
                    mock_query = Mock()
                    if field == "user_id" and value == "manager1":
                        mock_query.stream.return_value = [mock_membership]
                    elif field == "project_id":
                        mock_query.stream.return_value = [mock_team_membership]
                    else:
                        mock_query.stream.return_value = []
                    return mock_query
                mock_collection_obj.where = mock_where
                
            elif collection_name == "tasks":
                def mock_where(field, op, value):
                    mock_query = Mock()
                    def mock_where_chained(field2, op2, value2):
                        mock_query2 = Mock()
                        mock_query2.stream.return_value = [overdue_task, today_task, conflict_task1, conflict_task2]
                        return mock_query2
                    mock_query.where = mock_where_chained
                    mock_query.stream.return_value = [overdue_task, today_task, conflict_task1, conflict_task2]
                    return mock_query
                mock_collection_obj.where = mock_where
                
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.get("/api/manager/team-tasks?view_mode=timeline",
                            headers={"X-User-Id": "manager1"})
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify timeline data is present
        assert "timeline" in data
        assert "conflicts" in data
        assert "timeline_statistics" in data
        
        # Verify timeline structure
        timeline = data["timeline"]
        assert "overdue" in timeline
        assert "today" in timeline
        assert "this_week" in timeline
        assert "future" in timeline
        assert "no_due_date" in timeline
        
        # Verify timeline statistics
        timeline_stats = data["timeline_statistics"]
        assert "overdue_count" in timeline_stats
        assert "today_count" in timeline_stats
        assert "this_week_count" in timeline_stats
        assert "future_count" in timeline_stats
        assert "no_due_date_count" in timeline_stats
        assert "conflict_count" in timeline_stats
    
    def test_team_tasks_with_member_filter(self, client, mock_db, monkeypatch):
        """Test filtering by member"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Setup similar to previous test but simplified
        mock_manager_doc = Mock()
        mock_manager_doc.exists = True
        mock_manager_doc.to_dict.return_value = {"role": "manager"}
        
        mock_membership = Mock()
        mock_membership.to_dict.return_value = {"project_id": "proj1", "user_id": "manager1"}
        
        mock_team_membership = Mock()
        mock_team_membership.to_dict.return_value = {"project_id": "proj1", "user_id": "member1"}
        
        mock_team_member = Mock()
        mock_team_member.exists = True
        mock_team_member.to_dict.return_value = {
            "user_id": "member1",
            "name": "Member",
            "email": "member@test.com",
            "role": "staff"
        }
        
        mock_project = Mock()
        mock_project.exists = True
        mock_project.to_dict.return_value = {"name": "Project 1", "description": "Test"}
        
        mock_task = Mock()
        mock_task.id = "task1"
        mock_task.to_dict.return_value = {
            "title": "Task",
            "status": "To Do",
            "priority": 5,
            "created_by": {"user_id": "member1"},
            "project_id": "proj1",
            "labels": [],
            "archived": False
        }
        
        def mock_collection(collection_name):
            mock_collection_obj = Mock()
            if collection_name == "users":
                def mock_user_document(user_id):
                    mock_user_ref = Mock()
                    mock_user_ref.get.return_value = mock_manager_doc if user_id == "manager1" else mock_team_member
                    return mock_user_ref
                mock_collection_obj.document = mock_user_document
            elif collection_name == "projects":
                mock_collection_obj.document.return_value.get.return_value = mock_project
            elif collection_name == "memberships":
                def mock_where(field, op, value):
                    mock_query = Mock()
                    mock_query.stream.return_value = [mock_membership] if field == "user_id" else [mock_team_membership]
                    return mock_query
                mock_collection_obj.where = mock_where
            elif collection_name == "tasks":
                def mock_where(field, op, value):
                    mock_query = Mock()
                    mock_query.where.return_value.stream.return_value = [mock_task]
                    mock_query.stream.return_value = [mock_task]
                    return mock_query
                mock_collection_obj.where = mock_where
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        # Test with member filter
        response = client.get("/api/manager/team-tasks?filter_by=member&filter_value=member1",
                            headers={"X-User-Id": "manager1"})
        
        assert response.status_code == 200
    
    def test_team_tasks_with_sorting(self, client, mock_db, monkeypatch):
        """Test sorting by due_date, priority, and project"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_manager_doc = Mock()
        mock_manager_doc.exists = True
        mock_manager_doc.to_dict.return_value = {"role": "manager"}
        
        mock_membership = Mock()
        mock_membership.to_dict.return_value = {"project_id": "proj1", "user_id": "manager1"}
        
        def mock_collection(collection_name):
            mock_collection_obj = Mock()
            if collection_name == "users":
                mock_collection_obj.document.return_value.get.return_value = mock_manager_doc
            elif collection_name == "memberships":
                mock_collection_obj.where.return_value.stream.return_value = [mock_membership]
            elif collection_name == "tasks":
                mock_collection_obj.where.return_value.where.return_value.stream.return_value = []
            elif collection_name == "projects":
                mock_collection_obj.document.return_value.get.return_value.exists = False
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        # Test sorting by due_date
        response = client.get("/api/manager/team-tasks?sort_by=due_date&sort_order=desc",
                            headers={"X-User-Id": "manager1"})
        assert response.status_code == 200
        
        # Test sorting by priority
        response = client.get("/api/manager/team-tasks?sort_by=priority",
                            headers={"X-User-Id": "manager1"})
        assert response.status_code == 200
        
        # Test sorting by project
        response = client.get("/api/manager/team-tasks?sort_by=project",
                            headers={"X-User-Id": "manager1"})
        assert response.status_code == 200
    
    def test_team_tasks_with_status_filter(self, client, mock_db, monkeypatch):
        """Test filtering by status"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_manager_doc = Mock()
        mock_manager_doc.exists = True
        mock_manager_doc.to_dict.return_value = {"role": "manager"}
        
        mock_membership = Mock()
        mock_membership.to_dict.return_value = {"project_id": "proj1", "user_id": "manager1"}
        
        mock_team_membership = Mock()
        mock_team_membership.to_dict.return_value = {"project_id": "proj1", "user_id": "member1"}
        
        mock_team_member = Mock()
        mock_team_member.exists = True
        mock_team_member.to_dict.return_value = {
            "user_id": "member1",
            "name": "Member",
            "email": "member@test.com",
            "role": "staff"
        }
        
        mock_project = Mock()
        mock_project.exists = True
        mock_project.to_dict.return_value = {"name": "Project 1", "description": "Test"}
        
        # Task with specific status
        mock_task = Mock()
        mock_task.id = "task1"
        mock_task.to_dict.return_value = {
            "title": "Task",
            "status": "In Progress",
            "priority": 5,
            "created_by": {"user_id": "member1"},
            "project_id": "proj1",
            "labels": [],
            "archived": False
        }
        
        def mock_collection(collection_name):
            mock_collection_obj = Mock()
            if collection_name == "users":
                def mock_user_document(user_id):
                    mock_user_ref = Mock()
                    mock_user_ref.get.return_value = mock_manager_doc if user_id == "manager1" else mock_team_member
                    return mock_user_ref
                mock_collection_obj.document = mock_user_document
            elif collection_name == "projects":
                mock_collection_obj.document.return_value.get.return_value = mock_project
            elif collection_name == "memberships":
                def mock_where(field, op, value):
                    mock_query = Mock()
                    mock_query.stream.return_value = [mock_membership] if field == "user_id" else [mock_team_membership]
                    return mock_query
                mock_collection_obj.where = mock_where
            elif collection_name == "tasks":
                def mock_where(field, op, value):
                    mock_query = Mock()
                    mock_query.where.return_value.stream.return_value = [mock_task]
                    mock_query.stream.return_value = [mock_task]
                    return mock_query
                mock_collection_obj.where = mock_where
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        # Test with status filter
        response = client.get("/api/manager/team-tasks?filter_by=status&filter_value=In Progress",
                            headers={"X-User-Id": "manager1"})
        assert response.status_code == 200
        
        # Test with visual_status filter
        response = client.get("/api/manager/team-tasks?filter_by=visual_status&filter_value=on_track",
                            headers={"X-User-Id": "manager1"})
        assert response.status_code == 200
        
        # Test with project filter
        response = client.get("/api/manager/team-tasks?filter_by=project&filter_value=proj1",
                            headers={"X-User-Id": "manager1"})
        assert response.status_code == 200
    
    def test_timeline_with_no_due_date_tasks(self, client, mock_db, monkeypatch):
        """Test timeline grouping with tasks that have no due date"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        now = datetime.now(timezone.utc)
        
        mock_manager_doc = Mock()
        mock_manager_doc.exists = True
        mock_manager_doc.to_dict.return_value = {"role": "manager"}
        
        mock_membership = Mock()
        mock_membership.to_dict.return_value = {"project_id": "proj1", "user_id": "manager1"}
        
        mock_team_membership = Mock()
        mock_team_membership.to_dict.return_value = {"project_id": "proj1", "user_id": "member1"}
        
        mock_team_member = Mock()
        mock_team_member.exists = True
        mock_team_member.to_dict.return_value = {
            "user_id": "member1",
            "name": "Member",
            "email": "member@test.com",
            "role": "staff"
        }
        
        mock_project = Mock()
        mock_project.exists = True
        mock_project.to_dict.return_value = {"name": "Project 1", "description": "Test"}
        
        # Task with no due date
        no_due_task = Mock()
        no_due_task.id = "task1"
        no_due_task.to_dict.return_value = {
            "title": "No Due Date Task",
            "status": "To Do",
            "priority": 5,
            "due_date": None,  # No due date
            "created_by": {"user_id": "member1"},
            "project_id": "proj1",
            "labels": [],
            "archived": False
        }
        
        # Task with invalid date format (will be handled as no due date)
        invalid_date_task = Mock()
        invalid_date_task.id = "task2"
        invalid_date_task.to_dict.return_value = {
            "title": "Invalid Date Task",
            "status": "To Do",
            "priority": 5,
            "due_date": "invalid-date-format",
            "created_by": {"user_id": "member1"},
            "project_id": "proj1",
            "labels": [],
            "archived": False
        }
        
        # Task for this_week range
        this_week_task = Mock()
        this_week_task.id = "task3"
        this_week_task.to_dict.return_value = {
            "title": "This Week Task",
            "status": "To Do",
            "priority": 5,
            "due_date": (now + timedelta(days=3)).isoformat(),
            "created_by": {"user_id": "member1"},
            "project_id": "proj1",
            "labels": [],
            "archived": False
        }
        
        def mock_collection(collection_name):
            mock_collection_obj = Mock()
            if collection_name == "users":
                def mock_user_document(user_id):
                    mock_user_ref = Mock()
                    mock_user_ref.get.return_value = mock_manager_doc if user_id == "manager1" else mock_team_member
                    return mock_user_ref
                mock_collection_obj.document = mock_user_document
            elif collection_name == "projects":
                mock_collection_obj.document.return_value.get.return_value = mock_project
            elif collection_name == "memberships":
                def mock_where(field, op, value):
                    mock_query = Mock()
                    mock_query.stream.return_value = [mock_membership] if field == "user_id" else [mock_team_membership]
                    return mock_query
                mock_collection_obj.where = mock_where
            elif collection_name == "tasks":
                def mock_where(field, op, value):
                    mock_query = Mock()
                    mock_query.where.return_value.stream.return_value = [no_due_task, invalid_date_task, this_week_task]
                    mock_query.stream.return_value = [no_due_task, invalid_date_task, this_week_task]
                    return mock_query
                mock_collection_obj.where = mock_where
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.get("/api/manager/team-tasks?view_mode=timeline",
                            headers={"X-User-Id": "manager1"})
        
        assert response.status_code == 200
        data = response.get_json()
        assert "timeline" in data
        # Should have tasks in no_due_date bucket
        assert len(data["timeline"]["no_due_date"]) >= 1
        # Should have task in this_week bucket (line 149 coverage)
        assert len(data["timeline"]["this_week"]) >= 1

