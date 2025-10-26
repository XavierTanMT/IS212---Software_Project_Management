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
        mock_user_collection.document.return_value.get.return_value = mock_user_doc
        mock_db.collection.side_effect = lambda n: (
            mock_user_collection if n == "users" else make_tasks_collection([], [])
        )
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        resp = client.get("/api/users/u1/dashboard")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["statistics"]["total_created"] == 0
        assert data["statistics"]["total_assigned"] == 0

    def test_user_dashboard_with_created_tasks(self, client, mock_db, monkeypatch):
        mock_user_doc = Mock(); mock_user_doc.exists = True
        mock_user_collection = Mock()
        mock_user_collection.document.return_value.get.return_value = mock_user_doc
        t1, t2 = Mock(), Mock()
        t1.id, t2.id = "t1", "t2"
        t1.to_dict.return_value = {
            "title": "A", "priority": "High", "status": "To Do",
            "created_at": "2025-10-19T10:00:00+00:00", "created_by": {"user_id": "u1"},
        }
        t2.to_dict.return_value = {
            "title": "B", "priority": "Medium", "status": "In Progress",
            "created_at": "2025-10-18T10:00:00+00:00", "created_by": {"user_id": "u1"},
        }
        mock_db.collection.side_effect = lambda n: (
            mock_user_collection if n == "users" else make_tasks_collection([t1, t2], [])
        )
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        resp = client.get("/api/users/u1/dashboard")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["statistics"]["total_created"] == 2
        assert data["statistics"]["status_breakdown"] == {"To Do": 1, "In Progress": 1}


    def test_user_dashboard_with_assigned_tasks(self, client, mock_db, monkeypatch):
        mock_user_doc = Mock(); mock_user_doc.exists = True
        mock_user_collection = Mock()
        mock_user_collection.document.return_value.get.return_value = mock_user_doc
        task = Mock()
        task.id = "a1"
        task.to_dict.return_value = {
            "title": "Assigned", "priority": "Low", "status": "Completed",
            "created_at": "2025-10-17T10:00:00+00:00", "assigned_to": {"user_id": "u1"}
        }
        mock_db.collection.side_effect = lambda n: (
            mock_user_collection if n == "users" else make_tasks_collection([], [task])
        )
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        resp = client.get("/api/users/u1/dashboard")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["statistics"]["total_assigned"] == 1

    def test_user_dashboard_with_overdue_tasks(self, client, mock_db, monkeypatch):
        now = datetime.now(timezone.utc)
        mock_user_doc = Mock(); mock_user_doc.exists = True
        mock_user_collection = Mock()
        mock_user_collection.document.return_value.get.return_value = mock_user_doc
        overdue = Mock(); overdue.id = "o"
        overdue.to_dict.return_value = {
            "title": "Overdue", "priority": "High", "status": "To Do",
            "due_date": (now - timedelta(days=5)).isoformat(), "created_by": {"user_id": "u1"}
        }
        future = Mock(); future.id = "f"
        future.to_dict.return_value = {
            "title": "Future", "priority": "Low", "status": "In Progress",
            "due_date": (now + timedelta(days=3)).isoformat(), "created_by": {"user_id": "u1"}
        }
        mock_db.collection.side_effect = lambda n: (
            mock_user_collection if n == "users" else make_tasks_collection([overdue, future], [])
        )
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        resp = client.get("/api/users/u1/dashboard")
        data = resp.get_json()
        assert data["statistics"]["overdue_count"] == 1

    def test_user_dashboard_limits_to_5(self, client, mock_db, monkeypatch):
        mock_user_doc = Mock(); mock_user_doc.exists = True
        mock_user_collection = Mock()
        mock_user_collection.document.return_value.get.return_value = mock_user_doc
        tasks = []
        for i in range(7):
            m = Mock(); m.id = f"t{i}"
            m.to_dict.return_value = {
                "title": f"T{i}", "priority": "Medium", "status": "To Do",
                "created_at": f"2025-10-{19-i:02d}T10:00:00+00:00",
                "created_by": {"user_id": "u1"}
            }
            tasks.append(m)
        mock_db.collection.side_effect = lambda n: (
            mock_user_collection if n == "users" else make_tasks_collection(tasks, tasks)
        )
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        resp = client.get("/api/users/u1/dashboard")
        data = resp.get_json()
        assert len(data["recent_created_tasks"]) == 5
        assert len(data["recent_assigned_tasks"]) == 5


class TestDashboardTimeline:
    def test_timeline_mode(self, client, mock_db, monkeypatch):
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
        assert data["timeline_statistics"]["conflict_count"] >= 1


class TestBlueprint:
    def test_blueprint_setup(self):
        assert dashboard_bp.url_prefix == "/api"
        assert dashboard_bp.name == "dashboard"
