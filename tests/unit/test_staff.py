"""Unit tests for staff.py module"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import sys

# Get fake_firestore from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")

from flask import Flask
from backend.api import staff as staff_module


class TestGetStaffDashboard:
    """Test the get_staff_dashboard endpoint"""
    
    def test_get_staff_dashboard_success(self, client, mock_db, monkeypatch):
        """Test staff dashboard returns correct data"""
        user_id = "staff123"
        current_user = {
            "user_id": user_id,
            "name": "John Doe",
            "email": "john@example.com"
        }
        
        # Mock tasks created by staff
        mock_task1 = Mock()
        mock_task1.id = "task1"
        mock_task1.to_dict.return_value = {
            "title": "My Task",
            "status": "In Progress",
            "created_by": {"user_id": user_id}
        }
        
        # Mock tasks assigned to staff
        mock_task2 = Mock()
        mock_task2.id = "task2"
        mock_task2.to_dict.return_value = {
            "title": "Assigned Task",
            "status": "To Do",
            "assigned_to": {"user_id": user_id}
        }
        
        # Mock membership
        mock_membership = Mock()
        mock_membership.to_dict.return_value = {
            "project_id": "proj1",
            "user_id": user_id
        }
        
        # Mock project
        mock_project = Mock()
        mock_project.exists = True
        mock_project.to_dict.return_value = {
            "name": "Test Project",
            "status": "active"
        }
        
        # Setup mock collection responses
        def collection_router(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_query = Mock()
                # First call for created_by tasks
                mock_query.stream.side_effect = [[mock_task1], [mock_task2]]
                mock_coll.where.return_value = mock_query
                return mock_coll
            elif name == "memberships":
                mock_query = Mock()
                mock_query.stream.return_value = [mock_membership]
                mock_coll.where.return_value = mock_query
                return mock_coll
            elif name == "projects":
                mock_coll.document.return_value.get.return_value = mock_project
                return mock_coll
            return Mock()
        
        mock_db.collection.side_effect = collection_router
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock the decorator to pass through current_user
        with patch('backend.api.staff.firebase_required', lambda f: lambda *args, **kwargs: f(current_user, *args, **kwargs)):
            response = client.get('/staff/dashboard')
            
        assert response.status_code == 200
        data = response.get_json()
        assert data["view"] == "staff"
        assert "user" in data
        assert "my_tasks" in data
        assert "assigned_tasks" in data
        assert "projects" in data
        assert "statistics" in data
        assert data["statistics"]["my_tasks_count"] == 1
        assert data["statistics"]["assigned_tasks_count"] == 1
        assert data["statistics"]["projects_count"] == 1
        
    def test_get_staff_dashboard_no_tasks(self, client, mock_db, monkeypatch):
        """Test staff dashboard with no tasks"""
        user_id = "staff456"
        current_user = {
            "user_id": user_id,
            "name": "Jane Doe",
            "email": "jane@example.com"
        }
        
        # Setup mock with empty collections
        def collection_router(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_query = Mock()
                mock_query.stream.side_effect = [[], []]
                mock_coll.where.return_value = mock_query
                return mock_coll
            elif name == "memberships":
                mock_query = Mock()
                mock_query.stream.return_value = []
                mock_coll.where.return_value = mock_query
                return mock_coll
            return Mock()
        
        mock_db.collection.side_effect = collection_router
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.staff.firebase_required', lambda f: lambda *args, **kwargs: f(current_user, *args, **kwargs)):
            response = client.get('/staff/dashboard')
            
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["my_tasks"]) == 0
        assert len(data["assigned_tasks"]) == 0
        assert len(data["projects"]) == 0
        assert data["statistics"]["total_tasks"] == 0


class TestGetMyTasks:
    """Test the get_my_tasks endpoint"""
    
    def test_get_my_tasks_success(self, client, mock_db, monkeypatch):
        """Test getting staff member's own tasks"""
        user_id = "staff123"
        current_user = {
            "user_id": user_id,
            "name": "John Doe",
            "email": "john@example.com"
        }
        
        # Mock tasks
        mock_task1 = Mock()
        mock_task1.id = "task1"
        mock_task1.to_dict.return_value = {
            "title": "Task 1",
            "status": "In Progress",
            "created_by": {"user_id": user_id}
        }
        
        mock_task2 = Mock()
        mock_task2.id = "task2"
        mock_task2.to_dict.return_value = {
            "title": "Task 2",
            "status": "To Do",
            "created_by": {"user_id": user_id}
        }
        
        mock_collection = Mock()
        mock_query = Mock()
        mock_query.stream.return_value = [mock_task1, mock_task2]
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.staff.firebase_required', lambda f: lambda *args, **kwargs: f(current_user, *args, **kwargs)):
            response = client.get('/staff/tasks')
            
        assert response.status_code == 200
        data = response.get_json()
        assert "tasks" in data
        assert len(data["tasks"]) == 2
        assert data["tasks"][0]["task_id"] == "task1"
        assert data["tasks"][1]["task_id"] == "task2"
        
    def test_get_my_tasks_empty(self, client, mock_db, monkeypatch):
        """Test getting tasks when staff has none"""
        user_id = "staff456"
        current_user = {
            "user_id": user_id,
            "name": "Jane Doe",
            "email": "jane@example.com"
        }
        
        mock_collection = Mock()
        mock_query = Mock()
        mock_query.stream.return_value = []
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.staff.firebase_required', lambda f: lambda *args, **kwargs: f(current_user, *args, **kwargs)):
            response = client.get('/staff/tasks')
            
        assert response.status_code == 200
        data = response.get_json()
        assert "tasks" in data
        assert len(data["tasks"]) == 0


class TestCreateTask:
    """Test the create_task endpoint"""
    
    def test_create_task_success(self, client, mock_db, monkeypatch):
        """Test staff successfully creates a task"""
        user_id = "staff123"
        current_user = {
            "user_id": user_id,
            "name": "John Doe",
            "email": "john@example.com"
        }
        
        task_data = {
            "title": "New Task",
            "description": "Task description",
            "priority": 7,
            "status": "To Do",
            "due_date": "2024-12-31T23:59:59+00:00",
            "project_id": "proj1",
            "labels": ["urgent"]
        }
        
        # Mock Firestore add response
        mock_doc_ref = Mock()
        mock_doc_ref.id = "new_task_123"
        mock_collection = Mock()
        mock_collection.add.return_value = (None, mock_doc_ref)
        mock_db.collection.return_value = mock_collection
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.staff.firebase_required', lambda f: lambda *args, **kwargs: f(current_user, *args, **kwargs)):
            response = client.post('/staff/tasks', json=task_data)
            
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] == True
        assert data["task_id"] == "new_task_123"
        assert "message" in data
        
        # Verify task was added with correct data
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args[0][0]
        assert call_args["title"] == "New Task"
        assert call_args["description"] == "Task description"
        assert call_args["priority"] == 7
        assert call_args["status"] == "To Do"
        assert call_args["created_by"]["user_id"] == user_id
        assert call_args["created_by"]["name"] == "John Doe"
        assert "created_at" in call_args
        assert "updated_at" in call_args
        
    def test_create_task_with_defaults(self, client, mock_db, monkeypatch):
        """Test creating task with minimal data (defaults applied)"""
        user_id = "staff456"
        current_user = {
            "user_id": user_id,
            "name": "Jane Doe",
            "email": "jane@example.com"
        }
        
        task_data = {
            "title": "Minimal Task"
        }
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = "minimal_task_456"
        mock_collection = Mock()
        mock_collection.add.return_value = (None, mock_doc_ref)
        mock_db.collection.return_value = mock_collection
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.staff.firebase_required', lambda f: lambda *args, **kwargs: f(current_user, *args, **kwargs)):
            response = client.post('/staff/tasks', json=task_data)
            
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] == True
        
        # Verify defaults were applied
        call_args = mock_collection.add.call_args[0][0]
        assert call_args["title"] == "Minimal Task"
        assert call_args["description"] == ""  # default
        assert call_args["priority"] == 5  # default
        assert call_args["status"] == "To Do"  # default
        assert call_args["labels"] == []  # default
        assert call_args["assigned_to"] == {}  # default
        
    def test_create_task_with_assigned_to(self, client, mock_db, monkeypatch):
        """Test creating task with assignee"""
        user_id = "staff789"
        current_user = {
            "user_id": user_id,
            "name": "Bob Smith",
            "email": "bob@example.com"
        }
        
        task_data = {
            "title": "Assigned Task",
            "assigned_to": {
                "user_id": "other_user",
                "name": "Other User",
                "email": "other@example.com"
            }
        }
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = "assigned_task_789"
        mock_collection = Mock()
        mock_collection.add.return_value = (None, mock_doc_ref)
        mock_db.collection.return_value = mock_collection
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.staff.firebase_required', lambda f: lambda *args, **kwargs: f(current_user, *args, **kwargs)):
            response = client.post('/staff/tasks', json=task_data)
            
        assert response.status_code == 201
        
        # Verify assigned_to was included
        call_args = mock_collection.add.call_args[0][0]
        assert call_args["assigned_to"]["user_id"] == "other_user"
        assert call_args["assigned_to"]["name"] == "Other User"


class TestStaffEndpointsIntegration:
    """Integration tests for staff endpoints"""
    
    def test_staff_workflow_create_and_retrieve(self, client, mock_db, monkeypatch):
        """Test complete workflow: create task then retrieve it"""
        user_id = "staff_workflow"
        current_user = {
            "user_id": user_id,
            "name": "Workflow User",
            "email": "workflow@example.com"
        }
        
        # First, create a task
        task_data = {
            "title": "Workflow Task",
            "description": "Testing workflow",
            "status": "In Progress"
        }
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = "workflow_task"
        
        def collection_router(name):
            mock_coll = Mock()
            if name == "tasks":
                # For POST: add task
                mock_coll.add.return_value = (None, mock_doc_ref)
                
                # For GET: return the task
                mock_task = Mock()
                mock_task.id = "workflow_task"
                mock_task.to_dict.return_value = {
                    "title": "Workflow Task",
                    "description": "Testing workflow",
                    "status": "In Progress",
                    "created_by": {"user_id": user_id}
                }
                mock_query = Mock()
                mock_query.stream.return_value = [mock_task]
                mock_coll.where.return_value = mock_query
                
            return mock_coll
        
        mock_db.collection.side_effect = collection_router
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.staff.firebase_required', lambda f: lambda *args, **kwargs: f(current_user, *args, **kwargs)):
            # Create task
            create_response = client.post('/staff/tasks', json=task_data)
            assert create_response.status_code == 201
            
            # Retrieve tasks
            get_response = client.get('/staff/tasks')
            assert get_response.status_code == 200
            data = get_response.get_json()
            assert len(data["tasks"]) == 1
            assert data["tasks"][0]["title"] == "Workflow Task"
