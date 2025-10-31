import sys
from unittest.mock import Mock
from datetime import datetime, timezone, timedelta
import pytest
from conftest import make_tasks_collection  # type: ignore

fake_firestore = sys.modules.get("firebase_admin.firestore")

from backend.api import dashboard_bp
from backend.api import dashboard as dashboard_module


class TestTaskToJson:
    def test_task_to_json_with_all_fields(self):
        mock_doc = Mock()
        mock_doc.id = "task123"
        mock_doc.to_dict.return_value = {
            "title": "Test Task",
            "description": "Test Description",
            "priority": "High",
            "status": "In Progress",
            "due_date": "2025-12-31T23:59:59+00:00",
            "created_at": "2025-01-01T00:00:00+00:00",
            "created_by": {"user_id": "user1"},
            "assigned_to": {"user_id": "user2"},
        }
        res = dashboard_module.task_to_json(mock_doc)
        assert res["priority"] == "High"
        assert res["status"] == "In Progress"
        assert res["created_by"]["user_id"] == "user1"
        assert res["assigned_to"]["user_id"] == "user2"

    def test_task_to_json_with_missing_optional_fields(self):
        mock_doc = Mock()
        mock_doc.id = "task456"
        mock_doc.to_dict.return_value = {"title": "Minimal Task"}
        res = dashboard_module.task_to_json(mock_doc)
        assert res["priority"] == "Medium"
        assert res["status"] == "To Do"

    def test_task_to_json_with_partial_fields(self):
        mock_doc = Mock()
        mock_doc.id = "task789"
        mock_doc.to_dict.return_value = {
            "title": "Partial Task",
            "status": "Completed",
            "created_at": "2025-06-15T10:30:00+00:00",
        }
        res = dashboard_module.task_to_json(mock_doc)
        assert res["status"] == "Completed"
        assert res["priority"] == "Medium"


class TestSafeIsoToDt:
    def test_valid_and_invalid_cases(self):
        valid = "2025-10-19T12:30:00+00:00"
        z = "2025-10-19T12:30:00Z"
        bad = "not-a-date"
        none = None
        empty = ""
        malformed = "2025-13-45T99:99:99"
        naive = "2025-10-19T12:30:00"
        for val in [valid, z, naive]:
            dt = dashboard_module._safe_iso_to_dt(val)
            assert isinstance(dt, datetime)
            assert dt.tzinfo == timezone.utc
        for val in [bad, none, empty, malformed]:
            assert dashboard_module._safe_iso_to_dt(val) is None


class TestUserDashboard:
    def test_user_dashboard_user_not_found(self, client, mock_db, monkeypatch):
        mock_user_doc = Mock()
        mock_user_doc.exists = False
        mock_user_collection = Mock()
        mock_user_collection.document.return_value.get.return_value = mock_user_doc
        mock_db.collection.side_effect = lambda n: mock_user_collection if n == "users" else Mock()
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        resp = client.get("/api/users/nonexistent/dashboard")
        assert resp.status_code == 404
        assert "User not found" in resp.get_json()["error"]

    def test_user_dashboard_no_tasks(self, client, mock_db, monkeypatch):
        mock_user_doc = Mock(); mock_user_doc.exists = True
        mock_user_collection = Mock()
        mock_user_collection.document = Mock(return_value=Mock(get=Mock(return_value=mock_user_doc)))
        
        # Mock empty task collections
        mock_created_where = Mock()
        mock_created_where.stream = Mock(return_value=[])
        
        mock_assigned_where = Mock()
        mock_assigned_where.stream = Mock(return_value=[])
        
        mock_task_collection = Mock()
        def where_side_effect(field=None, op=None, value=None, filter=None):
            # Handle both old and new FieldFilter syntax
            if filter is not None:
                field = getattr(filter, "field_path", field)
                value = getattr(filter, "value", value)
            if "created_by" in field:
                return mock_created_where
            elif "assigned_to" in field:
                return mock_assigned_where
            return Mock()
        
        mock_task_collection.where = Mock(side_effect=where_side_effect)
        
        def collection_side_effect(name):
            if name == "users":
                return mock_user_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        resp = client.get("/api/users/u1/dashboard")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["statistics"]["total_created"] == 0
        assert data["statistics"]["total_assigned"] == 0

    def test_user_dashboard_with_created_tasks(self, client, mock_db, monkeypatch):
        mock_user_doc = Mock(); mock_user_doc.exists = True
        mock_user_collection = Mock()
        mock_user_collection.document = Mock(return_value=Mock(get=Mock(return_value=mock_user_doc)))
        
        # Mock task collections
        mock_created_where = Mock()
        mock_created_where.stream = Mock(return_value=[mock_task1, mock_task2])
        
        mock_assigned_where = Mock()
        mock_assigned_where.stream = Mock(return_value=[])
        
        mock_task_collection = Mock()
        def where_side_effect(field=None, op=None, value=None, filter=None):
            # Handle both old and new FieldFilter syntax
            if filter is not None:
                field = getattr(filter, "field_path", field)
                value = getattr(filter, "value", value)
            if "created_by" in field:
                return mock_created_where
            elif "assigned_to" in field:
                return mock_assigned_where
            return Mock()
        
        mock_task_collection.where = Mock(side_effect=where_side_effect)
        
        def collection_side_effect(name):
            if name == "users":
                return mock_user_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        resp = client.get("/api/users/u1/dashboard")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["statistics"]["total_created"] == 2
        assert data["statistics"]["status_breakdown"] == {"To Do": 1, "In Progress": 1}


    def test_user_dashboard_with_assigned_tasks(self, client, mock_db, monkeypatch):
        mock_user_doc = Mock(); mock_user_doc.exists = True
        mock_user_collection = Mock()
        mock_user_collection.document = Mock(return_value=Mock(get=Mock(return_value=mock_user_doc)))
        
        # Mock task collections
        mock_created_where = Mock()
        mock_created_where.stream = Mock(return_value=[])
        
        mock_assigned_where = Mock()
        mock_assigned_where.stream = Mock(return_value=[mock_task1])
        
        mock_task_collection = Mock()
        def where_side_effect(field=None, op=None, value=None, filter=None):
            # Handle both old and new FieldFilter syntax
            if filter is not None:
                field = getattr(filter, "field_path", field)
                value = getattr(filter, "value", value)
            if "created_by" in field:
                return mock_created_where
            elif "assigned_to" in field:
                return mock_assigned_where
            return Mock()
        
        mock_task_collection.where = Mock(side_effect=where_side_effect)
        
        def collection_side_effect(name):
            if name == "users":
                return mock_user_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        resp = client.get("/api/users/u1/dashboard")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["statistics"]["total_assigned"] == 1

    def test_user_dashboard_with_overdue_tasks(self, client, mock_db, monkeypatch):
        now = datetime.now(timezone.utc)
        mock_user_doc = Mock(); mock_user_doc.exists = True
        mock_user_collection = Mock()
        mock_user_collection.document = Mock(return_value=Mock(get=Mock(return_value=mock_user_doc)))
        
        # Mock task collections
        mock_created_where = Mock()
        mock_created_where.stream = Mock(return_value=[mock_overdue, mock_completed_late, mock_future, mock_no_due])
        
        mock_assigned_where = Mock()
        mock_assigned_where.stream = Mock(return_value=[])
        
        mock_task_collection = Mock()
        def where_side_effect(field=None, op=None, value=None, filter=None):
            # Handle both old and new FieldFilter syntax
            if filter is not None:
                field = getattr(filter, "field_path", field)
                value = getattr(filter, "value", value)
            if "created_by" in field:
                return mock_created_where
            elif "assigned_to" in field:
                return mock_assigned_where
            return Mock()
        
        mock_task_collection.where = Mock(side_effect=where_side_effect)
        
        def collection_side_effect(name):
            if name == "users":
                return mock_user_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        resp = client.get("/api/users/u1/dashboard")
        data = resp.get_json()
        assert data["statistics"]["overdue_count"] == 1

    def test_user_dashboard_limits_to_5(self, client, mock_db, monkeypatch):
        mock_user_doc = Mock(); mock_user_doc.exists = True
        mock_user_collection = Mock()
        mock_user_collection.document = Mock(return_value=Mock(get=Mock(return_value=mock_user_doc)))
        
        # Mock task collections
        mock_created_where = Mock()
        mock_created_where.stream = Mock(return_value=mock_tasks)
        
        mock_assigned_where = Mock()
        mock_assigned_where.stream = Mock(return_value=mock_tasks)  # Same for assigned
        
        mock_task_collection = Mock()
        def where_side_effect(field=None, op=None, value=None, filter=None):
            # Handle both old and new FieldFilter syntax
            if filter is not None:
                field = getattr(filter, "field_path", field)
                value = getattr(filter, "value", value)
            if "created_by" in field:
                return mock_created_where
            elif "assigned_to" in field:
                return mock_assigned_where
            return Mock()
        
        mock_task_collection.where = Mock(side_effect=where_side_effect)
        
        def collection_side_effect(name):
            if name == "users":
                return mock_user_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        resp = client.get("/api/users/u1/dashboard")
        data = resp.get_json()
        assert len(data["recent_created_tasks"]) == 5
        assert len(data["recent_assigned_tasks"]) == 5
        
        # Should be the 5 most recent (task0 through task4)
        assert data["recent_created_tasks"][0]["task_id"] == "task0"
        assert data["recent_created_tasks"][4]["task_id"] == "task4"
    
    def test_user_dashboard_sorting_with_null_created_at(self, client, mock_db, monkeypatch):
        """Test dashboard handles tasks with null/missing created_at dates."""
        # Mock user document
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        
        # Task with valid created_at
        mock_task_valid = Mock()
        mock_task_valid.id = "valid"
        mock_task_valid.to_dict = Mock(return_value={
            "title": "Valid Date",
            "priority": "High",
            "status": "To Do",
            "created_at": "2025-10-19T10:00:00+00:00",
            "created_by": {"user_id": "user123"},
        })
        
        # Task with null created_at
        mock_task_null = Mock()
        mock_task_null.id = "null"
        mock_task_null.to_dict = Mock(return_value={
            "title": "Null Date",
            "priority": "Medium",
            "status": "To Do",
            "created_at": None,
            "created_by": {"user_id": "user123"},
        })
        
        # Task with missing created_at
        mock_task_missing = Mock()
        mock_task_missing.id = "missing"
        mock_task_missing.to_dict = Mock(return_value={
            "title": "Missing Date",
            "priority": "Low",
            "status": "To Do",
            "created_by": {"user_id": "user123"},
        })
        
        mock_user_collection = Mock()
        mock_user_collection.document = Mock(return_value=Mock(get=Mock(return_value=mock_user_doc)))
        
        # Mock task collections
        mock_created_where = Mock()
        mock_created_where.stream = Mock(return_value=[mock_task_valid, mock_task_null, mock_task_missing])
        
        mock_assigned_where = Mock()
        mock_assigned_where.stream = Mock(return_value=[])
        
        mock_task_collection = Mock()
        def where_side_effect(field=None, op=None, value=None, filter=None):
            # Handle both old and new FieldFilter syntax
            if filter is not None:
                field = getattr(filter, "field_path", field)
                value = getattr(filter, "value", value)
            if "created_by" in field:
                return mock_created_where
            elif "assigned_to" in field:
                return mock_assigned_where
            return Mock()
        
        mock_task_collection.where = Mock(side_effect=where_side_effect)
        
        def collection_side_effect(name):
            if name == "users":
                return mock_user_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/users/user123/dashboard")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Should have all 3 tasks
        assert data["statistics"]["total_created"] == 3
        
        # Valid date should be first, null/missing should be last
        assert data["recent_created_tasks"][0]["task_id"] == "valid"
        # null and missing can be in any order after valid




class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_dashboard_with_invalid_due_date(self, client, mock_db, monkeypatch):
        """Test dashboard handles tasks with invalid due_date strings."""
        # Mock user document
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        
        # Task with invalid due date
        mock_task = Mock()
        mock_task.id = "invalid_due"
        mock_task.to_dict = Mock(return_value={
            "title": "Invalid Due Date",
            "priority": "High",
            "status": "To Do",
            "due_date": "not-a-date",  # Invalid date
            "created_at": "2025-10-19T10:00:00+00:00",
            "created_by": {"user_id": "user123"},
        })
        
        mock_user_collection = Mock()
        mock_user_collection.document = Mock(return_value=Mock(get=Mock(return_value=mock_user_doc)))
        
        mock_created_where = Mock()
        mock_created_where.stream = Mock(return_value=[mock_task])
        
        mock_assigned_where = Mock()
        mock_assigned_where.stream = Mock(return_value=[])
        
        mock_task_collection = Mock()
        def where_side_effect(field=None, op=None, value=None, filter=None):
            # Handle both old and new FieldFilter syntax
            if filter is not None:
                field = getattr(filter, "field_path", field)
                value = getattr(filter, "value", value)
            if "created_by" in field:
                return mock_created_where
            elif "assigned_to" in field:
                return mock_assigned_where
            return Mock()
        
        mock_task_collection.where = Mock(side_effect=where_side_effect)
        
        def collection_side_effect(name):
            if name == "users":
                return mock_user_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/users/user123/dashboard")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Invalid due date should not crash, should not count as overdue
        assert data["statistics"]["overdue_count"] == 0
    
    def test_dashboard_response_structure(self, client, mock_db, monkeypatch):
        """Test that dashboard response has correct structure."""
        # Mock user document
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        
        mock_user_collection = Mock()
        mock_user_collection.document = Mock(return_value=Mock(get=Mock(return_value=mock_user_doc)))
        
        mock_created_where = Mock()
        mock_created_where.stream = Mock(return_value=[])
        
        mock_assigned_where = Mock()
        mock_assigned_where.stream = Mock(return_value=[])
        
        mock_task_collection = Mock()
        def where_side_effect(field=None, op=None, value=None, filter=None):
            # Handle both old and new FieldFilter syntax
            if filter is not None:
                field = getattr(filter, "field_path", field)
                value = getattr(filter, "value", value)
            if "created_by" in field:
                return mock_created_where
            elif "assigned_to" in field:
                return mock_assigned_where
            return Mock()
        
        mock_task_collection.where = Mock(side_effect=where_side_effect)
        
        def collection_side_effect(name):
            if name == "users":
                return mock_user_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/users/user123/dashboard")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify all required keys are present
        assert "statistics" in data
        assert "recent_created_tasks" in data
        assert "recent_assigned_tasks" in data
        
        # Verify statistics structure
        stats = data["statistics"]
        assert "total_created" in stats
        assert "total_assigned" in stats
        assert "status_breakdown" in stats
        assert "priority_breakdown" in stats
        assert "overdue_count" in stats


class TestDashboardTimelineMode:
    """Test timeline mode view to achieve 100% coverage"""
    
    def test_dashboard_with_timeline_mode(self, client, mock_db, monkeypatch):
        """Test dashboard with view_mode=timeline includes timeline data"""
        from datetime import datetime, timezone, timedelta
        
        now = datetime.now(timezone.utc)
        mock_user_doc = Mock(); mock_user_doc.exists = True
        mock_user_collection = Mock()
        mock_user_collection.document.return_value.get.return_value = mock_user_doc
        overdue = Mock(); overdue.id = "t1"
        overdue.to_dict.return_value = {
            "title": "Overdue", "status": "To Do", "priority": 5,
            "due_date": (now - timedelta(days=1)).isoformat(),
            "created_by": {"user_id": "u1"}, "archived": False
        }
        today = Mock(); today.id = "t2"
        today.to_dict.return_value = {
            "title": "Today", "status": "To Do", "priority": 7,
            "due_date": (now + timedelta(hours=5)).isoformat(),
            "created_by": {"user_id": "u1"}, "archived": False
        }
        future = Mock(); future.id = "t3"
        future.to_dict.return_value = {
            "title": "Future", "status": "To Do", "priority": 3,
            "due_date": (now + timedelta(days=10)).isoformat(),
            "created_by": {"user_id": "u1"}, "archived": False
        }
        c1 = Mock(); c2 = Mock()
        same = (now + timedelta(days=15)).isoformat()
        for i, m in enumerate([c1, c2], 1):
            m.id = f"c{i}"
            m.to_dict.return_value = {
                "title": f"Conflict {i}", "status": "To Do", "priority": 5,
                "due_date": same, "created_by": {"user_id": "u1"}, "archived": False
            }
        mock_db.collection.side_effect = lambda n: (
            mock_user_collection if n == "users" else make_tasks_collection(
                [overdue, today, future, c1, c2], []
            )
        )
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        resp = client.get("/api/users/u1/dashboard?view_mode=timeline")
        data = resp.get_json()
        assert resp.status_code == 200
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
        
        # Verify timeline_statistics
        timeline_stats = data["timeline_statistics"]
        assert "total_tasks" in timeline_stats
        assert "overdue_count" in timeline_stats
        assert "today_count" in timeline_stats
        assert "this_week_count" in timeline_stats
        assert "future_count" in timeline_stats
        assert "no_due_date_count" in timeline_stats
        assert "conflict_count" in timeline_stats
        
        # Verify conflicts detected (2 tasks on same date)
        conflicts = data["conflicts"]
        assert len(conflicts) >= 1  # At least one conflict
        assert conflicts[0]["count"] == 2  # Two tasks on same date
    
    def test_dashboard_timeline_handles_unknown_status(self, client, mock_db, monkeypatch):
        """Test timeline mode handles tasks with unknown timeline_status gracefully.
        This tests the 'status not in timeline' branch at line 93"""
        from datetime import datetime, timezone, timedelta
        
        now = datetime.now(timezone.utc)
        
        # Mock user doc
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"user_id": "user123", "name": "Test User"}
        
        # Create a task that will have an unknown status not in the timeline dict
        # The enrich_task_with_timeline_status function might return unexpected values
        # We'll patch it to return a task with unknown status
        unknown_status_task = Mock()
        unknown_status_task.id = "task_unknown"
        unknown_status_task.to_dict.return_value = {
            "title": "Unknown Status Task",
            "status": "To Do",
            "priority": 5,
            "due_date": (now + timedelta(days=5)).isoformat(),
            "created_by": {"user_id": "user123", "name": "Test User"},
            "assigned_to": None,
            "archived": False
        }
        
        def collection_side_effect(col_name):
            mock_collection = Mock()
            if col_name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_user_doc
                mock_collection.document.return_value = mock_doc_ref
            elif col_name == "tasks":
                mock_query = Mock()
                mock_query.where.return_value.stream.return_value = [unknown_status_task]
                mock_collection.where = mock_query.where
            return mock_collection
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Patch enrich_task_with_timeline_status to return a task with unknown status
        def mock_enrich(task):
            task["timeline_status"] = "unknown_custom_status"  # Not in timeline dict
            return task
        
        monkeypatch.setattr(dashboard_module, "enrich_task_with_timeline_status", mock_enrich)
        
        # Request with timeline mode
        response = client.get("/api/users/user123/dashboard?view_mode=timeline")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify timeline data is present
        assert "timeline" in data
        
        # The task with unknown status should NOT appear in any timeline category
        # because the 'status not in timeline' branch skips adding it
        total_tasks_in_timeline = 0
        for category in data["timeline"].values():
            total_tasks_in_timeline += len(category)
        
        # Should be 0 since unknown status is not added to timeline
        assert total_tasks_in_timeline == 0


class TestBlueprint:
    def test_blueprint_setup(self):
        assert dashboard_bp.url_prefix == "/api"
        assert dashboard_bp.name == "dashboard"
