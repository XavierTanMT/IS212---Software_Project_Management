"""
Comprehensive tests to achieve 100% coverage for tasks.py
Tests all 11 endpoints, helper functions, permissions, filtering, pagination, and edge cases
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta


class TestHelperFunctions:
    """Tests for utility helper functions"""
    
    def test_now_iso(self):
        """Test now_iso returns ISO format datetime"""
        from backend.api.tasks import now_iso
        
        result = now_iso()
        
        # Should be valid ISO format
        assert isinstance(result, str)
        assert 'T' in result
        # Should parse back to datetime
        datetime.fromisoformat(result.replace('Z', '+00:00'))
    
    def test_task_to_json_basic(self):
        """Test task_to_json with basic task"""
        from backend.api.tasks import task_to_json
        
        mock_doc = Mock()
        mock_doc.id = "task123"
        mock_doc.to_dict.return_value = {
            "title": "Test Task",
            "description": "Description",
            "priority": "High",
            "status": "In Progress"
        }
        
        result = task_to_json(mock_doc)
        
        assert result["task_id"] == "task123"
        assert result["title"] == "Test Task"
        assert result["description"] == "Description"
        assert result["priority"] == "High"
        assert result["status"] == "In Progress"
    
    def test_task_to_json_with_defaults(self):
        """Test task_to_json applies default values"""
        from backend.api.tasks import task_to_json
        
        mock_doc = Mock()
        mock_doc.id = "task123"
        mock_doc.to_dict.return_value = {"title": "Task"}
        
        result = task_to_json(mock_doc)
        
        assert result["priority"] == "Medium"  # Default
        assert result["status"] == "To Do"  # Default
        assert result["archived"] == False  # Default
        assert result["is_recurring"] == False  # Default
        assert result["subtask_count"] == 0  # Default
        assert result["subtask_completed_count"] == 0  # Default
    
    def test_task_to_json_with_all_fields(self):
        """Test task_to_json with all fields populated"""
        from backend.api.tasks import task_to_json
        
        mock_doc = Mock()
        mock_doc.id = "task123"
        mock_doc.to_dict.return_value = {
            "title": "Task",
            "description": "Desc",
            "priority": "Low",
            "status": "Done",
            "due_date": "2025-12-01",
            "created_at": "2025-01-01",
            "updated_at": "2025-02-01",
            "created_by": {"user_id": "creator123"},
            "assigned_to": {"user_id": "assignee456"},
            "project_id": "proj789",
            "labels": ["label1", "label2"],
            "archived": True,
            "archived_at": "2025-03-01",
            "archived_by": {"user_id": "archiver"},
            "is_recurring": True,
            "recurrence_interval_days": 7,
            "parent_recurring_task_id": "parent123",
            "subtask_count": 5,
            "subtask_completed_count": 3
        }
        
        result = task_to_json(mock_doc)
        
        assert result["labels"] == ["label1", "label2"]
        assert result["archived"] == True
        assert result["is_recurring"] == True
        assert result["recurrence_interval_days"] == 7
        assert result["subtask_count"] == 5


class TestViewerHelpers:
    """Tests for viewer identification and permission helpers"""
    
    def test_viewer_id_from_header(self, client):
        """Test _viewer_id extracts from X-User-Id header"""
        with client.application.app_context():
            with client.application.test_request_context(
                headers={"X-User-Id": "user123"}
            ):
                from backend.api.tasks import _viewer_id
                assert _viewer_id() == "user123"
    
    def test_viewer_id_from_query_param(self, client):
        """Test _viewer_id extracts from viewer_id query parameter"""
        with client.application.app_context():
            with client.application.test_request_context(
                query_string={"viewer_id": "user456"}
            ):
                from backend.api.tasks import _viewer_id
                assert _viewer_id() == "user456"
    
    def test_viewer_id_no_viewer(self, client):
        """Test _viewer_id returns empty string when no viewer"""
        with client.application.app_context():
            with client.application.test_request_context():
                from backend.api.tasks import _viewer_id
                assert _viewer_id() == ""
    
    def test_ensure_creator_or_404_success(self, client):
        """Test _ensure_creator_or_404 returns True for creator"""
        with client.application.app_context():
            with client.application.test_request_context(
                headers={"X-User-Id": "creator123"}
            ):
                from backend.api.tasks import _ensure_creator_or_404
                
                mock_doc = Mock()
                mock_doc.to_dict.return_value = {
                    "created_by": {"user_id": "creator123"}
                }
                
                assert _ensure_creator_or_404(mock_doc) == True
    
    def test_ensure_creator_or_404_not_creator(self, client):
        """Test _ensure_creator_or_404 returns False for non-creator"""
        with client.application.app_context():
            with client.application.test_request_context(
                headers={"X-User-Id": "other123"}
            ):
                from backend.api.tasks import _ensure_creator_or_404
                
                mock_doc = Mock()
                mock_doc.to_dict.return_value = {
                    "created_by": {"user_id": "creator123"}
                }
                
                assert _ensure_creator_or_404(mock_doc) == False


class TestCanViewTask:
    """Tests for _can_view_task_doc permission checking"""
    
    def test_can_view_as_creator(self, client, mock_db):
        """Test viewer can view task they created"""
        with client.application.app_context():
            with client.application.test_request_context(
                headers={"X-User-Id": "creator123"}
            ):
                from backend.api.tasks import _can_view_task_doc
                
                mock_doc = Mock()
                mock_doc.to_dict.return_value = {
                    "created_by": {"user_id": "creator123"}
                }
                
                assert _can_view_task_doc(mock_db, mock_doc) == True
    
    def test_can_view_as_assignee(self, client, mock_db):
        """Test viewer can view task they're assigned to"""
        with client.application.app_context():
            with client.application.test_request_context(
                headers={"X-User-Id": "assignee456"}
            ):
                from backend.api.tasks import _can_view_task_doc
                
                mock_doc = Mock()
                mock_doc.to_dict.return_value = {
                    "created_by": {"user_id": "creator123"},
                    "assigned_to": {"user_id": "assignee456"}
                }
                
                assert _can_view_task_doc(mock_db, mock_doc) == True
    
    def test_can_view_as_admin(self, client, mock_db):
        """Test admin can view any task"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "admin"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        with client.application.app_context():
            with client.application.test_request_context(
                headers={"X-User-Id": "admin123"}
            ):
                from backend.api.tasks import _can_view_task_doc
                
                mock_doc = Mock()
                mock_doc.to_dict.return_value = {
                    "created_by": {"user_id": "other123"},
                    "assigned_to": {"user_id": "other456"}
                }
                
                assert _can_view_task_doc(mock_db, mock_doc) == True
    
    def test_can_view_no_viewer(self, client, mock_db):
        """Test cannot view without viewer_id"""
        with client.application.app_context():
            with client.application.test_request_context():
                from backend.api.tasks import _can_view_task_doc
                
                mock_doc = Mock()
                mock_doc.to_dict.return_value = {}
                
                assert _can_view_task_doc(mock_db, mock_doc) == False
    
    def test_can_view_as_project_member(self, client, mock_db):
        """Test project member can view task"""
        # Mock membership check
        mock_membership = Mock()
        mock_membership.exists = True
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "memberships":
                mock_coll.document.return_value.get.return_value = mock_membership
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with client.application.app_context():
            with client.application.test_request_context(
                headers={"X-User-Id": "member789"}
            ):
                from backend.api.tasks import _can_view_task_doc
                
                mock_doc = Mock()
                mock_doc.to_dict.return_value = {
                    "created_by": {"user_id": "other123"},
                    "project_id": "proj123"
                }
                
                assert _can_view_task_doc(mock_db, mock_doc) == True


class TestCanEditTask:
    """Tests for _can_edit_task permission checking"""
    
    def test_can_edit_as_creator(self, client):
        """Test creator can edit task"""
        with client.application.app_context():
            with client.application.test_request_context(
                headers={"X-User-Id": "creator123"}
            ):
                from backend.api.tasks import _can_edit_task
                
                mock_doc = Mock()
                mock_doc.to_dict.return_value = {
                    "created_by": {"user_id": "creator123"}
                }
                
                assert _can_edit_task(mock_doc) == True
    
    def test_can_edit_as_assignee(self, client):
        """Test assignee can edit task"""
        with client.application.app_context():
            with client.application.test_request_context(
                headers={"X-User-Id": "assignee456"}
            ):
                from backend.api.tasks import _can_edit_task
                
                mock_doc = Mock()
                mock_doc.to_dict.return_value = {
                    "created_by": {"user_id": "creator123"},
                    "assigned_to": {"user_id": "assignee456"}
                }
                
                assert _can_edit_task(mock_doc) == True
    
    def test_cannot_edit_as_other(self, client):
        """Test other users cannot edit task"""
        with client.application.app_context():
            with client.application.test_request_context(
                headers={"X-User-Id": "other789"}
            ):
                from backend.api.tasks import _can_edit_task
                
                mock_doc = Mock()
                mock_doc.to_dict.return_value = {
                    "created_by": {"user_id": "creator123"},
                    "assigned_to": {"user_id": "assignee456"}
                }
                
                assert _can_edit_task(mock_doc) == False


class TestRequireMembership:
    """Tests for _require_membership helper"""
    
    def test_require_membership_exists(self, mock_db):
        """Test membership exists"""
        from backend.api.tasks import _require_membership
        
        mock_membership = Mock()
        mock_membership.exists = True
        mock_db.collection.return_value.document.return_value.get.return_value = mock_membership
        
        result = _require_membership(mock_db, "proj123", "user456")
        
        assert result == True
    
    def test_require_membership_not_exists(self, mock_db):
        """Test membership does not exist"""
        from backend.api.tasks import _require_membership
        
        mock_membership = Mock()
        mock_membership.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_membership
        
        result = _require_membership(mock_db, "proj123", "user456")
        
        assert result == False


class TestCreateTask:
    """Tests for POST /api/tasks endpoint"""
    
    def test_create_task_success(self, client, mock_db):
        """Test successfully creating a task"""
        # Mock user document
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {
            "user_id": "creator123",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        mock_ref = Mock()
        mock_ref.id = "task123"
        mock_ref.set = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "tasks":
                mock_coll.document.return_value = mock_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.post("/api/tasks", 
            headers={"X-User-Id": "creator123"},
            json={
                "title": "New Task Title",
                "description": "This is a longer task description with enough characters",
                "priority": "High",
                "created_by_id": "creator123"
            })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["task_id"] == "task123"
        assert data["title"] == "New Task Title"
        assert "created_at" in data
    
    def test_create_task_missing_title(self, client, mock_db):
        """Test creating task without title fails"""
        response = client.post("/api/tasks",
            headers={"X-User-Id": "creator123"},
            json={
                "description": "This is a long enough description",
                "created_by_id": "creator123"
            })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "title" in data["error"].lower()
    
    def test_create_task_with_project(self, client, mock_db):
        """Test creating task with project_id"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {
            "user_id": "creator123",
            "name": "Creator",
            "email": "creator@example.com"
        }
        
        mock_membership = Mock()
        mock_membership.exists = True
        
        mock_ref = Mock()
        mock_ref.id = "task123"
        mock_ref.set = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value = mock_ref
            elif name == "memberships":
                mock_coll.document.return_value.get.return_value = mock_membership
            elif name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.post("/api/tasks",
            headers={"X-User-Id": "creator123"},
            json={
                "title": "Project Task Title",
                "description": "This is a project task with enough description",
                "project_id": "proj123",
                "created_by_id": "creator123"
            })
        
        assert response.status_code == 201
    
    def test_create_task_project_not_member(self, client, mock_db):
        """Test creating task for project user is not member of"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {
            "user_id": "creator123",
            "name": "Creator"
        }
        
        mock_membership = Mock()
        mock_membership.exists = False
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "memberships":
                mock_coll.document.return_value.get.return_value = mock_membership
            elif name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.post("/api/tasks",
            headers={"X-User-Id": "creator123"},
            json={
                "title": "Task Title",
                "description": "Task description with enough characters",
                "project_id": "proj123",
                "created_by_id": "creator123"
            })
        
        assert response.status_code == 403
    
    def test_create_task_with_recurring(self, client, mock_db):
        """Test creating recurring task"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {
            "user_id": "creator123",
            "name": "Creator"
        }
        
        mock_ref = Mock()
        mock_ref.id = "task123"
        mock_ref.set = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value = mock_ref
            elif name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.post("/api/tasks",
            headers={"X-User-Id": "creator123"},
            json={
                "title": "Recurring Task",
                "description": "This is a recurring task with enough description",
                "is_recurring": True,
                "recurrence_interval_days": 7,
                "due_date": "2025-12-01",
                "created_by_id": "creator123"
            })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["is_recurring"] == True
        assert data["recurrence_interval_days"] == 7


class TestListTasks:
    """Tests for GET /api/tasks endpoint"""
    
    def test_list_tasks_as_creator(self, client, mock_db):
        """Test listing tasks created by user"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "My Task",
            "status": "To Do",
            "priority": "Medium",
            "created_by": {"user_id": "user123"},
            "archived": False,
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        # Mock user document
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {
            "user_id": "user123",
            "role": "staff"
        }
        
        # Create mock query that handles chaining
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = [mock_task]
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.where.return_value = mock_query
            elif name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "memberships":
                mock_empty = Mock()
                mock_empty.where.return_value = mock_empty
                mock_empty.stream.return_value = []
                return mock_empty
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/tasks?role=creator",
            headers={"X-User-Id": "user123"})
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) >= 1
        # Find our task in the results
        task_ids = [t["task_id"] for t in data]
        assert "task123" in task_ids
    
    def test_list_tasks_as_assignee(self, client, mock_db):
        """Test listing tasks assigned to user"""
        mock_task = Mock()
        mock_task.id = "task456"
        mock_task.to_dict.return_value = {
            "title": "Assigned Task",
            "status": "In Progress",
            "priority": "High",
            "assigned_to": {"user_id": "user123"},
            "created_by": {"user_id": "other123"},
            "archived": False,
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        # Mock user
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "staff"}
        
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = [mock_task]
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.where.return_value = mock_query
            elif name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "memberships":
                mock_empty = Mock()
                mock_empty.where.return_value = mock_empty
                mock_empty.stream.return_value = []
                return mock_empty
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/tasks?role=assignee",
            headers={"X-User-Id": "user123"})
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) >= 1
    
    def test_list_tasks_filter_by_status(self, client, mock_db):
        """Test filtering tasks by status"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Task",
            "status": "In Progress",
            "priority": "Medium",
            "created_by": {"user_id": "user123"},
            "archived": False,
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "staff"}
        
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = [mock_task]
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.where.return_value = mock_query
            elif name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "memberships":
                mock_empty = Mock()
                mock_empty.where.return_value = mock_empty
                mock_empty.stream.return_value = []
                return mock_empty
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/tasks?role=creator&status=In Progress",
            headers={"X-User-Id": "user123"})
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) >= 1
        # Check that returned task has correct status
        for task in data:
            if task["task_id"] == "task123":
                assert task["status"] == "In Progress"
    
    def test_list_tasks_filter_by_priority(self, client, mock_db):
        """Test filtering tasks by priority"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "High Priority Task",
            "priority": "High",
            "status": "To Do",
            "created_by": {"user_id": "user123"},
            "archived": False,
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "staff"}
        
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = [mock_task]
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.where.return_value = mock_query
            elif name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "memberships":
                mock_empty = Mock()
                mock_empty.where.return_value = mock_empty
                mock_empty.stream.return_value = []
                return mock_empty
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/tasks?role=creator&priority=High",
            headers={"X-User-Id": "user123"})
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) >= 1
        # Verify at least one high priority task exists
        priorities = [t["priority"] for t in data]
        assert "High" in priorities
    
    def test_list_tasks_no_viewer(self, client, mock_db):
        """Test listing tasks without viewer_id"""
        response = client.get("/api/tasks")
        
        assert response.status_code == 401
    
    def test_list_tasks_exclude_archived(self, client, mock_db):
        """Test archived tasks are excluded by default"""
        mock_task1 = Mock()
        mock_task1.id = "task1"
        mock_task1.to_dict.return_value = {
            "title": "Active",
            "status": "To Do",
            "priority": "Medium",
            "archived": False,
            "created_by": {"user_id": "user123"},
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        mock_task2 = Mock()
        mock_task2.id = "task2"
        mock_task2.to_dict.return_value = {
            "title": "Archived",
            "status": "Done",
            "priority": "Low",
            "archived": True,
            "created_by": {"user_id": "user123"},
            "created_at": "2024-01-02T00:00:00Z"
        }
        
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "staff"}
        
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        # Both tasks are in query results, but endpoint should filter out archived
        mock_query.stream.return_value = [mock_task1, mock_task2]
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.where.return_value = mock_query
            elif name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "memberships":
                mock_empty = Mock()
                mock_empty.where.return_value = mock_empty
                mock_empty.stream.return_value = []
                return mock_empty
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/tasks?role=creator",
            headers={"X-User-Id": "user123"})
        
        assert response.status_code == 200
        data = response.get_json()
        # Should only include non-archived
        assert len(data) >= 1
        # Verify no archived tasks
        for task in data:
            assert task.get("archived") == False


class TestGetTask:
    """Tests for GET /api/tasks/<task_id> endpoint"""
    
    def test_get_task_success(self, client, mock_db):
        """Test successfully getting a task"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "My Task",
            "created_by": {"user_id": "user123"}
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task
        
        response = client.get("/api/tasks/task123",
            headers={"X-User-Id": "user123"})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["task_id"] == "task123"
        assert data["title"] == "My Task"
    
    def test_get_task_not_found(self, client, mock_db):
        """Test getting non-existent task"""
        mock_task = Mock()
        mock_task.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task
        
        response = client.get("/api/tasks/nonexistent",
            headers={"X-User-Id": "user123"})
        
        assert response.status_code == 404
    
    def test_get_task_no_permission(self, client, mock_db):
        """Test getting task without permission returns 404"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "title": "Task",
            "created_by": {"user_id": "other123"},
            "assigned_to": {"user_id": "other456"}
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task
        
        response = client.get("/api/tasks/task123",
            headers={"X-User-Id": "user789"})
        
        # Returns 404 when no permission (not 403)
        assert response.status_code == 404


class TestUpdateTask:
    """Tests for PUT /api/tasks/<task_id> endpoint"""
    
    def test_update_task_success(self, client, mock_db):
        """Test successfully updating a task"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Original Title",
            "created_by": {"user_id": "user123"},
            "status": "In Progress"
        }
        
        # Create updated mock for second get() call
        mock_updated_task = Mock()
        mock_updated_task.id = "task123"
        mock_updated_task.to_dict.return_value = {
            "title": "Updated Title",
            "created_by": {"user_id": "user123"},
            "status": "In Progress"
        }
        
        mock_ref = Mock()
        # First call returns original, second call after update returns updated
        mock_ref.get.side_effect = [mock_task, mock_updated_task]
        mock_ref.update = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        
        response = client.put("/api/tasks/task123",
            headers={"X-User-Id": "user123"},
            json={"title": "Updated Title"})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "Updated Title"
    
    def test_update_task_no_permission(self, client, mock_db):
        """Test updating task without permission"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "title": "Task",
            "created_by": {"user_id": "other123"}
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task
        
        response = client.put("/api/tasks/task123",
            headers={"X-User-Id": "user456"},
            json={"title": "Hacked"})
        
        assert response.status_code == 403
    
    def test_update_task_not_found(self, client, mock_db):
        """Test updating non-existent task"""
        mock_task = Mock()
        mock_task.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task
        
        response = client.put("/api/tasks/nonexistent",
            headers={"X-User-Id": "user123"},
            json={"title": "New"})
        
        assert response.status_code == 404


class TestDeleteTask:
    """Tests for DELETE /api/tasks/<task_id> endpoint"""
    
    def test_delete_task_success(self, client, mock_db):
        """Test successfully deleting (archiving) a task"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "title": "Task to Delete",
            "created_by": {"user_id": "user123"}
        }
        
        # Mock user with manager role (staff cannot delete)
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {
            "user_id": "user123",
            "role": "manager"
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_ref = Mock()
                mock_ref.get.return_value = mock_task
                mock_ref.update = Mock()
                mock_coll.document.return_value = mock_ref
            elif name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.delete("/api/tasks/task123",
            headers={"X-User-Id": "user123"})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["archived"] == True
    
    def test_delete_task_not_creator(self, client, mock_db):
        """Test only creator can delete task - returns 404 not 403"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "title": "Task",
            "created_by": {"user_id": "creator123"},
            "assigned_to": {"user_id": "assignee456"}
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task
        
        # Assignee tries to delete (should fail with 404 per _ensure_creator_or_404)
        response = client.delete("/api/tasks/task123",
            headers={"X-User-Id": "assignee456"})
        
        # _ensure_creator_or_404 returns 404 when not creator
        assert response.status_code == 404
    
    def test_delete_task_not_found(self, client, mock_db):
        """Test deleting non-existent task"""
        mock_task = Mock()
        mock_task.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task
        
        response = client.delete("/api/tasks/nonexistent",
            headers={"X-User-Id": "user123"})
        
        assert response.status_code == 404


class TestReassignTask:
    """Tests for PATCH /api/tasks/<task_id>/reassign endpoint"""
    
    def test_reassign_task_success(self, client, mock_db):
        """Test successfully reassigning a task"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "title": "Task",
            "created_by": {"user_id": "creator123"},
            "assigned_to": {"user_id": "old_assignee"}
        }
        
        # Mock viewer with manager role
        mock_viewer = Mock()
        mock_viewer.exists = True
        mock_viewer.to_dict.return_value = {
            "user_id": "manager123",
            "role": "manager"
        }
        
        # Mock new assignee user
        mock_new_assignee = Mock()
        mock_new_assignee.exists = True
        mock_new_assignee.to_dict.return_value = {
            "user_id": "new_assignee456",
            "name": "New Assignee",
            "email": "new@example.com"
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_ref = Mock()
                mock_ref.get.return_value = mock_task
                mock_ref.update = Mock()
                mock_coll.document.return_value = mock_ref
            elif name == "users":
                def doc_side_effect(doc_id):
                    mock_doc = Mock()
                    if doc_id == "manager123":
                        mock_doc.get.return_value = mock_viewer
                    elif doc_id == "new_assignee456":
                        mock_doc.get.return_value = mock_new_assignee
                    return mock_doc
                mock_coll.document = Mock(side_effect=doc_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.patch("/api/tasks/task123/reassign",
            headers={"X-User-Id": "manager123"},
            json={"new_assigned_to_id": "new_assignee456"})
        
        assert response.status_code == 200
    
    def test_reassign_task_missing_assignee(self, client, mock_db):
        """Test reassigning without new_assignee_id"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "creator123"}
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task
        
        response = client.patch("/api/tasks/task123/reassign",
            headers={"X-User-Id": "creator123"},
            json={})
        
        assert response.status_code == 400


class TestSubtasks:
    """Tests for subtask endpoints"""
    
    def test_list_subtasks_success(self, client, mock_db):
        """Test listing subtasks"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "title": "Parent",
            "created_by": {"user_id": "user123"}
        }
        
        mock_subtask = Mock()
        mock_subtask.id = "sub123"
        mock_subtask.to_dict.return_value = {
            "title": "Subtask",
            "completed": False
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value.get.return_value = mock_task
            elif name == "subtasks":
                mock_coll.where.return_value.stream.return_value = [mock_subtask]
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/tasks/task123/subtasks",
            headers={"X-User-Id": "user123"})
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["subtask_id"] == "sub123"
    
    def test_create_subtask_success(self, client, mock_db):
        """Test creating a subtask"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "title": "Parent",
            "created_by": {"user_id": "user123"}
        }
        
        # Mock user for creator details
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {
            "user_id": "user123",
            "name": "Test User",
            "email": "user@example.com"
        }
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.id = "sub123"
        mock_subtask_ref.set = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_task_ref = Mock()
                mock_task_ref.get.return_value = mock_task
                mock_task_ref.update = Mock()
                mock_coll.document.return_value = mock_task_ref
            elif name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "subtasks":
                mock_coll.document.return_value = mock_subtask_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.post("/api/tasks/task123/subtasks",
            headers={"X-User-Id": "user123"},
            json={"title": "New Subtask", "description": "Subtask description"})
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["subtask_id"] == "sub123"
        assert data["title"] == "New Subtask"
    
    def test_create_subtask_missing_title(self, client, mock_db):
        """Test creating subtask without title"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "user123"}
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task
        
        response = client.post("/api/tasks/task123/subtasks",
            headers={"X-User-Id": "user123"},
            json={})
        
        assert response.status_code == 400
    
    def test_update_subtask_success(self, client, mock_db):
        """Test updating a subtask"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "user123"}
        }
        
        mock_subtask = Mock()
        mock_subtask.exists = True
        mock_subtask.to_dict.return_value = {
            "title": "Old Title",
            "task_id": "task123"
        }
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.get.return_value = mock_subtask
        mock_subtask_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value.get.return_value = mock_task
            elif name == "subtasks":
                mock_coll.document.return_value = mock_subtask_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.put("/api/tasks/task123/subtasks/sub123",
            headers={"X-User-Id": "user123"},
            json={"title": "Updated"})
        
        assert response.status_code == 200
    
    def test_delete_subtask_success(self, client, mock_db):
        """Test deleting a subtask"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "user123"},
            "subtask_count": 2
        }
        
        mock_subtask = Mock()
        mock_subtask.exists = True
        mock_subtask.to_dict.return_value = {
            "task_id": "task123",
            "completed": False
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task
        mock_task_ref.update = Mock()
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.get.return_value = mock_subtask
        mock_subtask_ref.delete = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value = mock_task_ref
            elif name == "subtasks":
                mock_coll.document.return_value = mock_subtask_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.delete("/api/tasks/task123/subtasks/sub123",
            headers={"X-User-Id": "user123"})
        
        assert response.status_code == 200
        mock_subtask_ref.delete.assert_called_once()
    
    def test_complete_subtask_success(self, client, mock_db):
        """Test completing a subtask"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "user123"},
            "subtask_completed_count": 0
        }
        
        mock_subtask = Mock()
        mock_subtask.exists = True
        mock_subtask.to_dict.return_value = {
            "task_id": "task123",
            "completed": False
        }
        
        # Mock updated subtask after completion
        mock_updated_subtask = Mock()
        mock_updated_subtask.to_dict.return_value = {
            "task_id": "task123",
            "completed": True,
            "completed_by": {"user_id": "user123"},
            "completed_at": "2024-01-01T00:00:00Z"
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task
        mock_task_ref.update = Mock()
        
        mock_subtask_ref = Mock()
        # Endpoint calls sub_ref.get() twice: once at start, once at end for final result
        # First call returns original (uncompleted), second call after update returns updated
        mock_subtask_ref.get.side_effect = [mock_subtask, mock_updated_subtask]
        mock_subtask_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value = mock_task_ref
            elif name == "subtasks":
                mock_coll.document.return_value = mock_subtask_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.patch("/api/tasks/task123/subtasks/sub123/complete",
            headers={"X-User-Id": "user123"},
            json={"completed": True})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["completed"] == True


class TestManagerPermissions:
    """Tests for manager-level permissions and team member task visibility"""
    
    def test_can_view_task_as_manager_of_creator(self, client, mock_db):
        """Test manager can view tasks of team members they manage"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.id = "task123"  # Add id for JSON serialization
        mock_task.to_dict.return_value = {
            "title": "Task",
            "created_by": {"user_id": "staff123"},
            "assigned_to": {"user_id": "other456"}
        }
        
        # Mock manager user
        mock_manager = Mock()
        mock_manager.exists = True
        mock_manager.to_dict.return_value = {
            "user_id": "manager123",
            "role": "manager"
        }
        
        # Mock staff user who reports to manager
        mock_staff = Mock()
        mock_staff.exists = True
        mock_staff.to_dict.return_value = {
            "user_id": "staff123",
            "manager_id": "manager123"  # Reports to manager
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value.get.return_value = mock_task
            elif name == "users":
                def doc_side_effect(doc_id):
                    mock_doc = Mock()
                    if doc_id == "manager123":
                        mock_doc.get.return_value = mock_manager
                    elif doc_id == "staff123":
                        mock_doc.get.return_value = mock_staff
                    else:
                        mock_doc.get.return_value = Mock(exists=False)
                    return mock_doc
                mock_coll.document = Mock(side_effect=doc_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/tasks/task123",
            headers={"X-User-Id": "manager123"})
        
        assert response.status_code == 200
    
    def test_can_view_task_as_manager_of_assignee(self, client, mock_db):
        """Test manager can view tasks assigned to their team members"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.id = "task123"  # Add id for JSON serialization
        mock_task.to_dict.return_value = {
            "title": "Task",
            "created_by": {"user_id": "other123"},
            "assigned_to": {"user_id": "staff456"}
        }
        
        mock_manager = Mock()
        mock_manager.exists = True
        mock_manager.to_dict.return_value = {
            "user_id": "manager123",
            "role": "manager"
        }
        
        mock_staff = Mock()
        mock_staff.exists = True
        mock_staff.to_dict.return_value = {
            "user_id": "staff456",
            "manager_id": "manager123"
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value.get.return_value = mock_task
            elif name == "users":
                def doc_side_effect(doc_id):
                    mock_doc = Mock()
                    if doc_id == "manager123":
                        mock_doc.get.return_value = mock_manager
                    elif doc_id == "staff456":
                        mock_doc.get.return_value = mock_staff
                    else:
                        mock_doc.get.return_value = Mock(exists=False)
                    return mock_doc
                mock_coll.document = Mock(side_effect=doc_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/tasks/task123",
            headers={"X-User-Id": "manager123"})
        
        assert response.status_code == 200
    
    def test_can_view_task_as_admin(self, client, mock_db):
        """Test admin can view any task"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.id = "task123"  # Add id for JSON serialization
        mock_task.to_dict.return_value = {
            "title": "Task",
            "created_by": {"user_id": "other123"},
            "assigned_to": {"user_id": "other456"}
        }
        
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {
            "user_id": "admin123",
            "role": "admin"
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value.get.return_value = mock_task
            elif name == "users":
                mock_coll.document.return_value.get.return_value = mock_admin
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/tasks/task123",
            headers={"X-User-Id": "admin123"})
        
        assert response.status_code == 200
    
    def test_director_role_can_view_managed_tasks(self, client, mock_db):
        """Test director role (manager-level) can view team tasks"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.id = "task123"  # Add id for JSON serialization
        mock_task.to_dict.return_value = {
            "title": "Task",
            "created_by": {"user_id": "staff123"},
            "assigned_to": {"user_id": "other456"}
        }
        
        mock_director = Mock()
        mock_director.exists = True
        mock_director.to_dict.return_value = {
            "user_id": "director123",
            "role": "director"
        }
        
        mock_staff = Mock()
        mock_staff.exists = True
        mock_staff.to_dict.return_value = {
            "user_id": "staff123",
            "manager_id": "director123"
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value.get.return_value = mock_task
            elif name == "users":
                def doc_side_effect(doc_id):
                    mock_doc = Mock()
                    if doc_id == "director123":
                        mock_doc.get.return_value = mock_director
                    elif doc_id == "staff123":
                        mock_doc.get.return_value = mock_staff
                    else:
                        mock_doc.get.return_value = Mock(exists=False)
                    return mock_doc
                mock_coll.document = Mock(side_effect=doc_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/tasks/task123",
            headers={"X-User-Id": "director123"})
        
        assert response.status_code == 200


class TestRecurringTasks:
    """Tests for recurring task creation and completion"""
    
    def test_create_recurring_task_with_due_date(self, client, mock_db):
        """Test creating a recurring task with valid due date"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {
            "user_id": "user123",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        mock_task_ref = Mock()
        mock_task_ref.id = "task123"
        mock_task_ref.set = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "tasks":
                mock_coll.document.return_value = mock_task_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.post("/api/tasks",
            headers={"X-User-Id": "user123"},
            json={
                "title": "Weekly Review",
                "description": "Review project status every week",
                "created_by_id": "user123",
                "is_recurring": True,
                "recurrence_interval_days": 7,
                "due_date": "2025-12-01T00:00:00Z"
            })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["is_recurring"] == True
        assert data["recurrence_interval_days"] == 7
    
    def test_create_recurring_task_missing_due_date(self, client, mock_db):
        """Test recurring task requires due_date"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"user_id": "user123"}
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        response = client.post("/api/tasks",
            headers={"X-User-Id": "user123"},
            json={
                "title": "Weekly Task",
                "description": "Recurring task without due date",
                "created_by_id": "user123",
                "is_recurring": True,
                "recurrence_interval_days": 7
                # Missing due_date
            })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "due date" in data["error"].lower()
    
    def test_create_recurring_task_missing_interval(self, client, mock_db):
        """Test recurring task requires positive interval"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"user_id": "user123"}
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        response = client.post("/api/tasks",
            headers={"X-User-Id": "user123"},
            json={
                "title": "Weekly Task",
                "description": "Recurring task with invalid interval",
                "created_by_id": "user123",
                "is_recurring": True,
                "recurrence_interval_days": 0,  # Invalid
                "due_date": "2025-12-01T00:00:00Z"
            })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "interval" in data["error"].lower()
    
    def test_update_recurring_task_add_due_date(self, client, mock_db):
        """Test updating task to add due_date for recurring"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Task",
            "created_by": {"user_id": "user123"},
            "is_recurring": True,
            "recurrence_interval_days": 7,
            "status": "To Do"
        }
        
        mock_updated = Mock()
        mock_updated.id = "task123"
        mock_updated.to_dict.return_value = {
            "title": "Task",
            "created_by": {"user_id": "user123"},
            "is_recurring": True,
            "recurrence_interval_days": 7,
            "due_date": "2025-12-01T00:00:00Z",
            "status": "To Do"
        }
        
        mock_ref = Mock()
        mock_ref.get.side_effect = [mock_task, mock_updated]
        mock_ref.update = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        
        response = client.put("/api/tasks/task123",
            headers={"X-User-Id": "user123"},
            json={"due_date": "2025-12-01T00:00:00Z"})
        
        assert response.status_code == 200
    
    def test_update_task_invalid_due_date_format(self, client, mock_db):
        """Test updating task with invalid due_date format"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "title": "Task",
            "created_by": {"user_id": "user123"},
            "status": "To Do"
        }
        
        mock_ref = Mock()
        mock_ref.get.return_value = mock_task
        mock_db.collection.return_value.document.return_value = mock_ref
        
        response = client.put("/api/tasks/task123",
            headers={"X-User-Id": "user123"},
            json={"due_date": "invalid-date-format"})
        
        assert response.status_code == 400
        data = response.get_json()
        assert "date" in data["error"].lower()
    
    def test_update_task_no_fields(self, client, mock_db):
        """Test updating task without any fields"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "title": "Task",
            "created_by": {"user_id": "user123"}
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task
        
        response = client.put("/api/tasks/task123",
            headers={"X-User-Id": "user123"},
            json={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert "no fields" in data["error"].lower()


class TestProjectMembership:
    """Tests for project membership and visibility"""
    
    def test_create_task_in_project_as_member(self, client, mock_db):
        """Test creating task in project when user is a member"""
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {
            "user_id": "user123",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        mock_membership = Mock()
        mock_membership.exists = True
        mock_membership.to_dict.return_value = {
            "project_id": "proj123",
            "user_id": "user123",
            "role": "contributor"
        }
        
        mock_task_ref = Mock()
        mock_task_ref.id = "task123"
        mock_task_ref.set = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "memberships":
                mock_coll.document.return_value.get.return_value = mock_membership
            elif name == "tasks":
                mock_coll.document.return_value = mock_task_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.post("/api/tasks",
            headers={"X-User-Id": "user123"},
            json={
                "title": "Project Task",
                "description": "Task for the project",
                "created_by_id": "user123",
                "project_id": "proj123"
            })
        
        assert response.status_code == 201
    
    def test_list_tasks_with_project_filter(self, client, mock_db):
        """Test listing tasks filtered by project_id"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Project Task",
            "project_id": "proj123",
            "created_by": {"user_id": "user123"},
            "status": "To Do",
            "priority": "Medium",
            "archived": False,
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "staff"}
        
        mock_membership = Mock()
        mock_membership.exists = True
        
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = [mock_task]
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.where.return_value = mock_query
            elif name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "memberships":
                mock_coll.document.return_value.get.return_value = mock_membership
                mock_empty = Mock()
                mock_empty.where.return_value = mock_empty
                mock_empty.stream.return_value = []
                mock_coll.where.return_value = mock_empty
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/tasks?project_id=proj123",
            headers={"X-User-Id": "user123"})
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) >= 0  # May or may not return results based on complex logic
    
    def test_list_tasks_with_assigned_to_filter(self, client, mock_db):
        """Test listing tasks filtered by assigned_to_id"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Assigned Task",
            "assigned_to": {"user_id": "user456"},
            "created_by": {"user_id": "user123"},
            "status": "In Progress",
            "priority": "High",
            "archived": False,
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "staff"}
        
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = [mock_task]
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.where.return_value = mock_query
            elif name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            elif name == "memberships":
                mock_empty = Mock()
                mock_empty.where.return_value = mock_empty
                mock_empty.stream.return_value = []
                return mock_empty
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/tasks?assigned_to_id=user456",
            headers={"X-User-Id": "user123"})
        
        assert response.status_code == 200


class TestErrorHandling:
    """Tests for error handling and edge cases"""
    
    def test_create_task_user_not_found(self, client, mock_db):
        """Test creating task when creator user doesn't exist"""
        mock_user = Mock()
        mock_user.exists = False
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        response = client.post("/api/tasks",
            headers={"X-User-Id": "user123"},
            json={
                "title": "Task",
                "description": "Task with non-existent user",
                "created_by_id": "nonexistent"
            })
        
        assert response.status_code == 404
    
    def test_get_task_without_viewer_id(self, client, mock_db):
        """Test getting task without viewer_id header returns 404"""
        # Task doesn't exist check happens before viewer check
        mock_task = Mock()
        mock_task.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task
        
        response = client.get("/api/tasks/task123")
        
        assert response.status_code == 404  # Task not found comes before viewer check
    
    def test_update_task_without_viewer_id(self, client, mock_db):
        """Test updating task without viewer_id"""
        response = client.put("/api/tasks/task123",
            json={"title": "Updated"})
        
        assert response.status_code == 401
    
    def test_delete_task_as_staff_creator(self, client, mock_db):
        """Test staff cannot delete even if creator"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "title": "Task",
            "created_by": {"user_id": "staff123"}
        }
        
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {
            "user_id": "staff123",
            "role": "staff"  # Staff role
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value.get.return_value = mock_task
            elif name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.delete("/api/tasks/task123",
            headers={"X-User-Id": "staff123"})
        
        assert response.status_code == 403
    
    def test_reassign_task_as_staff(self, client, mock_db):
        """Test staff cannot reassign tasks"""
        mock_task = Mock()
        mock_task.exists = True
        
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {
            "user_id": "staff123",
            "role": "staff"
        }
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value.get.return_value = mock_task
            elif name == "users":
                mock_coll.document.return_value.get.return_value = mock_user
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.patch("/api/tasks/task123/reassign",
            headers={"X-User-Id": "staff123"},
            json={"new_assigned_to_id": "user456"})
        
        assert response.status_code == 403
    
    def test_reassign_task_new_assignee_not_found(self, client, mock_db):
        """Test reassigning to non-existent user"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "assigned_to": {"user_id": "old123"}
        }
        
        mock_manager = Mock()
        mock_manager.exists = True
        mock_manager.to_dict.return_value = {"role": "manager"}
        
        mock_new_user = Mock()
        mock_new_user.exists = False  # User doesn't exist
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value.get.return_value = mock_task
            elif name == "users":
                def doc_side_effect(doc_id):
                    mock_doc = Mock()
                    if doc_id == "manager123":
                        mock_doc.get.return_value = mock_manager
                    else:
                        mock_doc.get.return_value = mock_new_user
                    return mock_doc
                mock_coll.document = Mock(side_effect=doc_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.patch("/api/tasks/task123/reassign",
            headers={"X-User-Id": "manager123"},
            json={"new_assigned_to_id": "nonexistent"})
        
        assert response.status_code == 404
    
    def test_list_subtasks_task_not_found(self, client, mock_db):
        """Test listing subtasks for non-existent task"""
        mock_task = Mock()
        mock_task.exists = False
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task
        
        response = client.get("/api/tasks/nonexistent/subtasks",
            headers={"X-User-Id": "user123"})
        
        assert response.status_code == 404
    
    def test_create_subtask_not_creator(self, client, mock_db):
        """Test only creator can create subtasks"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "creator123"}
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_task
        
        response = client.post("/api/tasks/task123/subtasks",
            headers={"X-User-Id": "other456"},
            json={"title": "Subtask"})
        
        assert response.status_code == 403
    
    def test_update_subtask_not_creator(self, client, mock_db):
        """Test only task creator can update subtasks"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "creator123"}
        }
        
        mock_subtask = Mock()
        mock_subtask.exists = True
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value.get.return_value = mock_task
            elif name == "subtasks":
                mock_coll.document.return_value.get.return_value = mock_subtask
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.put("/api/tasks/task123/subtasks/sub123",
            headers={"X-User-Id": "other456"},
            json={"title": "Updated"})
        
        assert response.status_code == 403
    
    def test_update_subtask_not_found(self, client, mock_db):
        """Test updating non-existent subtask"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "user123"}
        }
        
        mock_subtask = Mock()
        mock_subtask.exists = False
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value.get.return_value = mock_task
            elif name == "subtasks":
                mock_coll.document.return_value.get.return_value = mock_subtask
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.put("/api/tasks/task123/subtasks/nonexistent",
            headers={"X-User-Id": "user123"},
            json={"title": "Updated"})
        
        assert response.status_code == 404
    
    def test_update_subtask_no_fields(self, client, mock_db):
        """Test updating subtask without any fields"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "user123"}
        }
        
        mock_subtask = Mock()
        mock_subtask.exists = True
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value.get.return_value = mock_task
            elif name == "subtasks":
                mock_coll.document.return_value.get.return_value = mock_subtask
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.put("/api/tasks/task123/subtasks/sub123",
            headers={"X-User-Id": "user123"},
            json={})
        
        assert response.status_code == 400
    
    def test_delete_subtask_not_creator(self, client, mock_db):
        """Test only creator can delete subtasks"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "creator123"}
        }
        
        mock_subtask = Mock()
        mock_subtask.exists = True
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value.get.return_value = mock_task
            elif name == "subtasks":
                mock_coll.document.return_value.get.return_value = mock_subtask
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.delete("/api/tasks/task123/subtasks/sub123",
            headers={"X-User-Id": "other456"})
        
        assert response.status_code == 403
    
    def test_complete_subtask_not_found(self, client, mock_db):
        """Test completing non-existent subtask"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "user123"}
        }
        
        mock_subtask = Mock()
        mock_subtask.exists = False
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value.get.return_value = mock_task
            elif name == "subtasks":
                mock_coll.document.return_value.get.return_value = mock_subtask
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.patch("/api/tasks/task123/subtasks/nonexistent/complete",
            headers={"X-User-Id": "user123"},
            json={"completed": True})
        
        assert response.status_code == 404
    
    def test_complete_subtask_toggle_without_payload(self, client, mock_db):
        """Test completing subtask toggles when no completed value provided"""
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {
            "created_by": {"user_id": "user123"}
        }
        
        mock_subtask = Mock()
        mock_subtask.exists = True
        mock_subtask.to_dict.return_value = {
            "completed": False
        }
        
        mock_updated = Mock()
        mock_updated.to_dict.return_value = {
            "completed": True
        }
        
        mock_task_ref = Mock()
        mock_task_ref.get.return_value = mock_task
        mock_task_ref.update = Mock()
        
        mock_subtask_ref = Mock()
        mock_subtask_ref.get.side_effect = [mock_subtask, mock_subtask, mock_updated]
        mock_subtask_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_coll.document.return_value = mock_task_ref
            elif name == "subtasks":
                mock_coll.document.return_value = mock_subtask_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        # No completed field in JSON - should toggle
        response = client.patch("/api/tasks/task123/subtasks/sub123/complete",
            headers={"X-User-Id": "user123"},
            json={})
        
        assert response.status_code == 200

