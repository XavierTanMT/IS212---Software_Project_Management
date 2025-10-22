import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
import sys

# Get fake_firestore from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")

from flask import Flask
from backend.api import manager_bp
from backend.api import manager as manager_module


# app and client fixtures provided by conftest.py


class TestManagerHelperFunctions:
    """Test helper functions in manager module"""
    
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
    
    def test_get_task_status_flags_overdue(self):
        """Test _get_task_status_flags with overdue date"""
        # Create a date 5 days ago
        past_date = (datetime.now(timezone.utc) - timezone.timedelta(days=5)).isoformat()
        flags = manager_module._get_task_status_flags(past_date)
        assert flags["is_overdue"] == True
        assert flags["is_upcoming"] == False
        assert flags["status"] == "overdue"
    
    def test_get_task_status_flags_upcoming(self):
        """Test _get_task_status_flags with upcoming date (within 3 days)"""
        # Create a date 2 days from now
        future_date = (datetime.now(timezone.utc) + timezone.timedelta(days=2)).isoformat()
        flags = manager_module._get_task_status_flags(future_date)
        assert flags["is_overdue"] == False
        assert flags["is_upcoming"] == True
        assert flags["status"] == "upcoming"
    
    def test_get_task_status_flags_on_track(self):
        """Test _get_task_status_flags with date more than 3 days away"""
        # Create a date 10 days from now
        future_date = (datetime.now(timezone.utc) + timezone.timedelta(days=10)).isoformat()
        flags = manager_module._get_task_status_flags(future_date)
        assert flags["is_overdue"] == False
        assert flags["is_upcoming"] == False
        assert flags["status"] == "on_track"


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
        
        # Mock project membership
        mock_membership = Mock()
        mock_membership.to_dict.return_value = {"project_id": "proj1", "user_id": "manager_user"}
        
        # Mock team member
        mock_team_member_doc = Mock()
        mock_team_member_doc.exists = True
        mock_team_member_doc.to_dict.return_value = {
            "user_id": "team_member1",
            "name": "Team Member",
            "email": "member@example.com",
            "role": "staff"
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
                mock_doc_ref = Mock()
                if mock_doc_ref.document.call_args[0][0] == "manager_user":
                    mock_doc_ref.document.return_value.get.return_value = mock_manager_doc
                else:
                    mock_doc_ref.document.return_value.get.return_value = mock_team_member_doc
                mock_collection_obj.document = mock_doc_ref.document
            elif collection_name == "memberships":
                mock_query = Mock()
                if mock_query.where.call_args[0][1] == "manager_user":
                    mock_query.where.return_value.stream.return_value = [mock_membership]
                else:
                    mock_query.where.return_value.stream.return_value = []
                mock_collection_obj.where = mock_query.where
            elif collection_name == "tasks":
                mock_query = Mock()
                mock_query.where.return_value.stream.return_value = [mock_task_doc]
                mock_collection_obj.where = mock_query.where
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.get("/api/manager/team-tasks", headers={"X-User-Id": "manager_user"})
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["team_tasks"]) == 1
        assert data["team_tasks"][0]["title"] == "Test Task"
        assert data["team_tasks"][0]["priority"] == 7
        assert data["team_tasks"][0]["member_id"] == "team_member1"


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
