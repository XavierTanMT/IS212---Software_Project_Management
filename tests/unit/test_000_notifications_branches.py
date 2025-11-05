"""
Branch coverage tests for notifications.py
Numbered 000 to run first and ensure coverage tracer is active
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone, timedelta
import sys

fake_firestore = sys.modules.get("firebase_admin.firestore")


class TestNotificationsBranchCoverage:
    """Test missing branches in notifications.py"""
    
    def test_create_notification_no_user_id_empty_string(self, mock_db):
        """Branch: if not user_id -> TRUE with empty string (line 21->22)"""
        from backend.api.notifications import create_notification
        
        result = create_notification(mock_db, "", "Title", "Body")
        assert result is None
    
    def test_create_notification_no_user_id_none(self, mock_db):
        """Branch: if not user_id -> TRUE with None (line 21->22)"""
        from backend.api.notifications import create_notification
        
        result = create_notification(mock_db, None, "Title", "Body")
        assert result is None
    
    def test_create_notification_send_email_false(self, mock_db):
        """Branch: if send_email -> FALSE (line 26->skip 27-33)"""
        from backend.api.notifications import create_notification
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = "notif123"
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        result = create_notification(mock_db, "user123", "Title", "Body", send_email=False)
        assert result == "notif123"
    
    def test_create_notification_send_email_true_user_exists(self, mock_db):
        """Branch: if send_email -> TRUE, user exists (line 26->27)"""
        from backend.api.notifications import create_notification
        
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = "notif123"
        mock_db.collection.return_value.document.side_effect = [
            Mock(get=Mock(return_value=mock_user_doc)),  # user lookup
            mock_doc_ref  # notification creation
        ]
        
        with patch('backend.api.notifications.send_email_util', return_value=True):
            result = create_notification(mock_db, "user123", "Title", "Body", send_email=True)
        
        assert result == "notif123"
    
    def test_create_notification_send_email_user_not_exists(self, mock_db):
        """Branch: user_doc.exists -> FALSE (line 29)"""
        from backend.api.notifications import create_notification
        
        mock_user_doc = Mock()
        mock_user_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = "notif123"
        mock_db.collection.return_value.document.side_effect = [
            Mock(get=Mock(return_value=mock_user_doc)),
            mock_doc_ref
        ]
        
        result = create_notification(mock_db, "user123", "Title", "Body", send_email=True)
        assert result == "notif123"
    
    def test_create_notification_exception_getting_user(self, mock_db):
        """Branch: exception in try block (line 27-33)"""
        from backend.api.notifications import create_notification
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = "notif123"
        
        def side_effect_func(collection):
            if collection == "users":
                raise Exception("DB error")
            return Mock(document=Mock(return_value=mock_doc_ref))
        
        mock_db.collection.side_effect = side_effect_func
        
        result = create_notification(mock_db, "user123", "Title", "Body", send_email=True)
        assert result == "notif123"
    
    def test_create_notification_send_email_but_no_email_address(self, mock_db):
        """Branch: send_email and user_email -> user_email is None (line 52)"""
        from backend.api.notifications import create_notification
        
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {}  # No email field
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = "notif123"
        mock_db.collection.return_value.document.side_effect = [
            Mock(get=Mock(return_value=mock_user_doc)),
            mock_doc_ref
        ]
        
        result = create_notification(mock_db, "user123", "Title", "Body", send_email=True)
        assert result == "notif123"
    
    def test_create_notification_email_send_success(self, mock_db):
        """Branch: send_email_util returns True (line 53->54)"""
        from backend.api.notifications import create_notification
        
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = "notif123"
        mock_db.collection.return_value.document.side_effect = [
            Mock(get=Mock(return_value=mock_user_doc)),
            mock_doc_ref
        ]
        
        with patch('backend.api.notifications.send_email_util', return_value=True):
            result = create_notification(mock_db, "user123", "Title", "Body", send_email=True)
        
        mock_doc_ref.update.assert_called_once()
        assert result == "notif123"
    
    def test_create_notification_email_send_failure(self, mock_db):
        """Branch: send_email_util returns False (line 53->skip 54)"""
        from backend.api.notifications import create_notification
        
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = "notif123"
        mock_db.collection.return_value.document.side_effect = [
            Mock(get=Mock(return_value=mock_user_doc)),
            mock_doc_ref
        ]
        
        with patch('backend.api.notifications.send_email_util', return_value=False):
            result = create_notification(mock_db, "user123", "Title", "Body", send_email=True)
        
        mock_doc_ref.update.assert_not_called()
        assert result == "notif123"


class TestCheckDeadlinesBranches:
    """Test branches in check_deadlines endpoint"""
    
    def test_check_deadlines_with_start_end_iso(self, client, mock_db):
        """Branch: start_iso and end_iso provided (line 117->119 skip)"""
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
        mock_db.collection.return_value.stream.return_value = []
        
        response = client.post(
            "/api/notifications/check-deadlines",
            query_string={
                "start_iso": "2025-01-01T00:00:00+00:00",
                "end_iso": "2025-01-02T00:00:00+00:00"
            }
        )
        
        assert response.status_code == 200
    
    def test_check_deadlines_without_iso_params(self, client, mock_db):
        """Branch: no start_iso/end_iso, use hours (line 117->119)"""
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
        mock_db.collection.return_value.stream.return_value = []
        
        response = client.post(
            "/api/notifications/check-deadlines",
            query_string={"hours": "48"}
        )
        
        assert response.status_code == 200
    
    def test_check_deadlines_invalid_hours_exception(self, client, mock_db):
        """Branch: exception parsing hours (line 120->121)"""
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
        mock_db.collection.return_value.stream.return_value = []
        
        response = client.post(
            "/api/notifications/check-deadlines",
            query_string={"hours": "invalid"}
        )
        
        assert response.status_code == 200
    
    def test_check_deadlines_sample_task_exists(self, client, mock_db):
        """Branch: sample task exists (line 134)"""
        mock_task = Mock()
        mock_task.to_dict.return_value = {"due_date": "2025-01-01T10:00"}
        
        mock_db.collection.return_value.limit.return_value.stream.return_value = iter([mock_task])
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
        mock_db.collection.return_value.stream.return_value = []
        
        response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200
    
    def test_check_deadlines_sample_task_no_due_date(self, client, mock_db):
        """Branch: sample exists but no due_date (line 136)"""
        mock_task = Mock()
        mock_task.to_dict.return_value = {}  # No due_date
        
        mock_db.collection.return_value.limit.return_value.stream.return_value = iter([mock_task])
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
        mock_db.collection.return_value.stream.return_value = []
        
        response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200
    
    def test_check_deadlines_sample_due_date_minute_format(self, client, mock_db):
        """Branch: sample_due matches minute pattern (line 137->138)"""
        mock_task = Mock()
        mock_task.to_dict.return_value = {"due_date": "2025-01-15T14:30"}
        
        mock_db.collection.return_value.limit.return_value.stream.return_value = iter([mock_task])
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
        mock_db.collection.return_value.stream.return_value = []
        
        response = client.post(
            "/api/notifications/check-deadlines",
            query_string={
                "start_iso": "2025-01-15T00:00:00+00:00",
                "end_iso": "2025-01-16T00:00:00+00:00"
            }
        )
        
        assert response.status_code == 200
    
    def test_check_deadlines_iso_parse_exception(self, client, mock_db):
        """Branch: exception parsing ISO datetimes (line 145->149)"""
        mock_task = Mock()
        mock_task.to_dict.return_value = {"due_date": "2025-01-15T14:30"}
        
        mock_db.collection.return_value.limit.return_value.stream.return_value = iter([mock_task])
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
        mock_db.collection.return_value.stream.return_value = []
        
        response = client.post(
            "/api/notifications/check-deadlines",
            query_string={
                "start_iso": "invalid-datetime",
                "end_iso": "also-invalid"
            }
        )
        
        assert response.status_code == 200
    
    def test_check_deadlines_sample_lookup_exception(self, client, mock_db):
        """Branch: exception in sample lookup (line 154->158)"""
        call_count = [0]
        
        def raise_on_first_call(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Database error")
            return []
        
        mock_db.collection.return_value.limit.return_value.stream.side_effect = raise_on_first_call
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
        mock_db.collection.return_value.stream.return_value = []
        
        response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200
    
    def test_check_deadlines_query_preview_exception(self, client, mock_db):
        """Branch: exception in query preview (line 164->166)"""
        mock_task = Mock()
        mock_task.to_dict.return_value = {"due_date": "2025-01-15T14:30"}
        
        mock_db.collection.return_value.limit.return_value.stream.return_value = iter([mock_task])
        
        def raise_on_stream(*args, **kwargs):
            raise Exception("Stream error")
        
        mock_where = Mock()
        mock_where.where.return_value.limit.return_value.stream.side_effect = raise_on_stream
        mock_where.where.return_value.stream.return_value = []
        mock_db.collection.return_value.where.return_value = mock_where
        mock_db.collection.return_value.stream.return_value = []
        
        response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200
    
    def test_check_deadlines_with_task_no_creator(self, client, mock_db):
        """Branch: created_by exists but no user_id (line 184)"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "due_date": "2025-01-15T14:30",
            "created_by": {}  # Empty dict, no user_id
        }
        
        mock_db.collection.return_value.limit.return_value.stream.return_value = iter([Mock()])
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = [mock_task]
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
        mock_db.collection.return_value.stream.return_value = []
        
        response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200
    
    def test_check_deadlines_with_creator_user_id(self, client, mock_db):
        """Branch: creator user_id exists (line 184->186)"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "due_date": "2025-01-15T14:30",
            "created_by": {"user_id": "creator123"}
        }
        
        mock_db.collection.return_value.limit.return_value.stream.return_value = iter([Mock()])
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = [mock_task]
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
        mock_db.collection.return_value.stream.return_value = []
        
        response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200
    
    def test_check_deadlines_with_assignee_user_id(self, client, mock_db):
        """Branch: assignee user_id exists (line 188->190)"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "due_date": "2025-01-15T14:30",
            "assigned_to": {"user_id": "assignee123"}
        }
        
        mock_db.collection.return_value.limit.return_value.stream.return_value = iter([Mock()])
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = [mock_task]
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
        mock_db.collection.return_value.stream.return_value = []
        
        response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200
    
    def test_check_deadlines_with_project_members(self, client, mock_db):
        """Branch: project_id exists and has members (line 192->193)"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "due_date": "2025-01-15T14:30",
            "project_id": "proj123"
        }
        
        mock_member = Mock()
        mock_member.to_dict.return_value = {"user_id": "member123"}
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([Mock()])
                mock_tasks.where.return_value.where.return_value.stream.return_value = [mock_task]
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "memberships":
                mock_mems = Mock()
                mock_mems.where.return_value.stream.return_value = [mock_member]
                return mock_mems
            elif name == "users":
                mock_users = Mock()
                mock_user_doc = Mock()
                mock_user_doc.exists = True
                mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
                mock_users.document.return_value.get.return_value = mock_user_doc
                mock_users.stream.return_value = []
                return mock_users
            elif name == "notifications":
                mock_notifs = Mock()
                mock_notifs.where.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                mock_notifs.document.return_value = Mock(id="notif123")
                return mock_notifs
        
        mock_db.collection.side_effect = mock_collection
        
        with patch('backend.api.notifications.send_email_util', return_value=True):
            response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200
    
    def test_check_deadlines_membership_no_user_id(self, client, mock_db):
        """Branch: membership exists but no user_id (line 196->197)"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "due_date": "2025-01-15T14:30",
            "project_id": "proj123"
        }
        
        mock_member = Mock()
        mock_member.to_dict.return_value = {}  # No user_id
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([Mock()])
                mock_tasks.where.return_value.where.return_value.stream.return_value = [mock_task]
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "memberships":
                mock_mems = Mock()
                mock_mems.where.return_value.stream.return_value = [mock_member]
                return mock_mems
            elif name == "users":
                return Mock(stream=Mock(return_value=[]))
            elif name == "notifications":
                return Mock(document=Mock(return_value=Mock(id="notif123")))
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200
    
    def test_check_deadlines_user_email_exception(self, client, mock_db):
        """Branch: exception getting user email (line 205->206)"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "due_date": "2025-01-15T14:30",
            "created_by": {"user_id": "user123"}
        }
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([Mock()])
                mock_tasks.where.return_value.where.return_value.stream.return_value = [mock_task]
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "users":
                def raise_error(*args, **kwargs):
                    raise Exception("DB error")
                mock_users = Mock()
                mock_users.document.return_value.get.side_effect = raise_error
                mock_users.stream.return_value = []
                return mock_users
            elif name == "notifications":
                mock_notifs = Mock()
                mock_notifs.where.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                mock_notifs.document.return_value = Mock(id="notif123")
                return mock_notifs
        
        mock_db.collection.side_effect = mock_collection
        
        with patch('backend.api.notifications.send_email_util', return_value=True):
            response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200
    
    def test_check_deadlines_existing_notification_found(self, client, mock_db):
        """Branch: existing notification exists (line 211->212)"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "due_date": "2025-01-15T14:30",
            "created_by": {"user_id": "user123"}
        }
        
        mock_existing_notif = Mock()
        mock_existing_notif.to_dict.return_value = {"email_sent": True}
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([Mock()])
                mock_tasks.where.return_value.where.return_value.stream.return_value = [mock_task]
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "users":
                mock_user_doc = Mock()
                mock_user_doc.exists = True
                mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_user_doc
                mock_users.stream.return_value = []
                return mock_users
            elif name == "notifications":
                mock_notifs = Mock()
                mock_notifs.where.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = [mock_existing_notif]
                return mock_notifs
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200
    
    def test_check_deadlines_resend_existing_true_email_not_sent(self, client, mock_db):
        """Branch: resend_existing=true, email_sent=false, user has email (line 216->217)"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "due_date": "2025-01-15T14:30",
            "created_by": {"user_id": "user123"}
        }
        
        mock_existing_notif = Mock()
        mock_existing_notif.to_dict.return_value = {"email_sent": False}
        mock_existing_notif.reference = Mock()
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([Mock()])
                mock_tasks.where.return_value.where.return_value.stream.return_value = [mock_task]
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "users":
                mock_user_doc = Mock()
                mock_user_doc.exists = True
                mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_user_doc
                mock_users.stream.return_value = []
                return mock_users
            elif name == "notifications":
                mock_notifs = Mock()
                mock_notifs.where.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = [mock_existing_notif]
                return mock_notifs
        
        mock_db.collection.side_effect = mock_collection
        
        with patch('backend.api.notifications.send_email_util', return_value=True):
            response = client.post(
                "/api/notifications/check-deadlines",
                query_string={"resend_existing": "true"}
            )
        
        assert response.status_code == 200
        mock_existing_notif.reference.update.assert_called_once()
    
    def test_check_deadlines_resend_email_failure(self, client, mock_db):
        """Branch: resend email returns False (line 219->224)"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "due_date": "2025-01-15T14:30",
            "created_by": {"user_id": "user123"}
        }
        
        mock_existing_notif = Mock()
        mock_existing_notif.to_dict.return_value = {"email_sent": False}
        mock_existing_notif.reference = Mock()
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([Mock()])
                mock_tasks.where.return_value.where.return_value.stream.return_value = [mock_task]
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "users":
                mock_user_doc = Mock()
                mock_user_doc.exists = True
                mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_user_doc
                mock_users.stream.return_value = []
                return mock_users
            elif name == "notifications":
                mock_notifs = Mock()
                mock_notifs.where.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = [mock_existing_notif]
                return mock_notifs
        
        mock_db.collection.side_effect = mock_collection
        
        with patch('backend.api.notifications.send_email_util', return_value=False):
            response = client.post(
                "/api/notifications/check-deadlines",
                query_string={"resend_existing": "1"}
            )
        
        assert response.status_code == 200
        mock_existing_notif.reference.update.assert_not_called()
    
    def test_check_deadlines_resend_exception(self, client, mock_db):
        """Branch: exception during resend (line 226->228)"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "due_date": "2025-01-15T14:30",
            "created_by": {"user_id": "user123"}
        }
        
        mock_existing_notif = Mock()
        mock_existing_notif.id = "notif123"
        mock_existing_notif.to_dict.return_value = {"email_sent": False}
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([Mock()])
                mock_tasks.where.return_value.where.return_value.stream.return_value = [mock_task]
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "users":
                mock_user_doc = Mock()
                mock_user_doc.exists = True
                mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
                mock_users = Mock()
                mock_users.document.return_value.get.return_value = mock_user_doc
                mock_users.stream.return_value = []
                return mock_users
            elif name == "notifications":
                mock_notifs = Mock()
                mock_notifs.where.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = [mock_existing_notif]
                return mock_notifs
        
        mock_db.collection.side_effect = mock_collection
        
        with patch('backend.api.notifications.send_email_util', side_effect=Exception("Email error")):
            response = client.post(
                "/api/notifications/check-deadlines",
                query_string={"resend_existing": "yes"}
            )
        
        assert response.status_code == 200
    
    def test_check_deadlines_per_user_notification_exception(self, client, mock_db):
        """Branch: exception in per-user notification pass (line 243->248)"""
        
        def bad_generator():
            """Generator that raises exception when iterated"""
            raise Exception("User stream error")
            yield  # Never reached
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([Mock()])
                mock_tasks.where.return_value.where.return_value.stream.return_value = []
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "users":
                # Return a stream that will raise exception when iterated
                return Mock(stream=Mock(return_value=bad_generator()))
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200


class TestNotifyUserDueTasksBranches:
    """Test branches in _notify_user_due_tasks function"""
    
    def test_notify_user_sample_task_exists(self, mock_db):
        """Branch: sample task exists with due_date (line 263->264)"""
        from backend.api.notifications import _notify_user_due_tasks
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {"due_date": "2025-01-15T14:30"}
        
        mock_db.collection.return_value.limit.return_value.stream.return_value = iter([mock_task])
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
        
        result = _notify_user_due_tasks(
            mock_db,
            "user123",
            "2025-01-15T00:00:00+00:00",
            "2025-01-16T00:00:00+00:00"
        )
        
        assert result == 0
    
    def test_notify_user_sample_task_minute_format_parse_exception(self, mock_db):
        """Branch: minute format but parse fails (line 270->272)"""
        from backend.api.notifications import _notify_user_due_tasks
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {"due_date": "2025-01-15T14:30"}
        
        mock_db.collection.return_value.limit.return_value.stream.return_value = iter([mock_task])
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
        
        result = _notify_user_due_tasks(
            mock_db,
            "user123",
            "invalid-iso",
            "also-invalid"
        )
        
        assert result == 0
    
    def test_notify_user_sample_exception(self, mock_db):
        """Branch: exception in sample lookup (line 277->278)"""
        from backend.api.notifications import _notify_user_due_tasks
        
        call_count = [0]
        
        def raise_on_first_limit(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("DB error")
            # For subsequent calls, return empty
            return Mock(stream=Mock(return_value=[]))
        
        mock_db.collection.return_value.limit.side_effect = raise_on_first_limit
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
        
        result = _notify_user_due_tasks(
            mock_db,
            "user123",
            "2025-01-15T00:00:00+00:00",
            "2025-01-16T00:00:00+00:00"
        )
        
        assert result == 0
    
    def test_notify_user_archived_task(self, mock_db):
        """Branch: task is archived (line 288->289)"""
        from backend.api.notifications import _notify_user_due_tasks
        
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "archived": True,
            "title": "Archived Task",
            "due_date": "2025-01-15T14:30"
        }
        
        mock_db.collection.return_value.limit.return_value.stream.return_value = iter([Mock()])
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = [mock_task]
        
        result = _notify_user_due_tasks(
            mock_db,
            "user123",
            "2025-01-15T00:00:00+00:00",
            "2025-01-16T00:00:00+00:00"
        )
        
        assert result == 0
    
    def test_notify_user_creator_matches(self, mock_db):
        """Branch: creator matches user_id (line 293->295)"""
        from backend.api.notifications import _notify_user_due_tasks
        
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "My Task",
            "due_date": "2025-01-15T14:30",
            "created_by": {"user_id": "user123"}
        }
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([Mock()])
                mock_tasks.where.return_value.where.return_value.stream.return_value = [mock_task]
                return mock_tasks
            elif name == "users":
                mock_user_doc = Mock()
                mock_user_doc.exists = True
                mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
                return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_user_doc))))
            elif name == "notifications":
                mock_notifs = Mock()
                mock_notifs.where.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = iter([])
                mock_notifs.document.return_value = Mock(id="notif123")
                return mock_notifs
        
        mock_db.collection.side_effect = mock_collection
        
        with patch('backend.api.notifications.send_email_util', return_value=True):
            result = _notify_user_due_tasks(
                mock_db,
                "user123",
                "2025-01-15T00:00:00+00:00",
                "2025-01-16T00:00:00+00:00"
            )
        
        assert result == 1
    
    def test_notify_user_assignee_matches(self, mock_db):
        """Branch: assignee matches user_id (line 297->298)"""
        from backend.api.notifications import _notify_user_due_tasks
        
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Assigned Task",
            "due_date": "2025-01-15T14:30",
            "assigned_to": {"user_id": "user123"}
        }
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([Mock()])
                mock_tasks.where.return_value.where.return_value.stream.return_value = [mock_task]
                return mock_tasks
            elif name == "users":
                mock_user_doc = Mock()
                mock_user_doc.exists = True
                mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
                return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_user_doc))))
            elif name == "notifications":
                mock_notifs = Mock()
                mock_notifs.where.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = iter([])
                mock_notifs.document.return_value = Mock(id="notif123")
                return mock_notifs
        
        mock_db.collection.side_effect = mock_collection
        
        with patch('backend.api.notifications.send_email_util', return_value=True):
            result = _notify_user_due_tasks(
                mock_db,
                "user123",
                "2025-01-15T00:00:00+00:00",
                "2025-01-16T00:00:00+00:00"
            )
        
        assert result == 1
    
    def test_notify_user_not_involved_no_project(self, mock_db):
        """Branch: not involved, no project_id (line 300->skip 301-304)"""
        from backend.api.notifications import _notify_user_due_tasks
        
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Other Task",
            "due_date": "2025-01-15T14:30",
            "created_by": {"user_id": "other_user"},
            "assigned_to": {"user_id": "another_user"}
        }
        
        mock_db.collection.return_value.limit.return_value.stream.return_value = iter([Mock()])
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = [mock_task]
        
        result = _notify_user_due_tasks(
            mock_db,
            "user123",
            "2025-01-15T00:00:00+00:00",
            "2025-01-16T00:00:00+00:00"
        )
        
        assert result == 0
    
    def test_notify_user_project_member_exists(self, mock_db):
        """Branch: project_id exists and user is member (line 301->302->304)"""
        from backend.api.notifications import _notify_user_due_tasks
        
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Project Task",
            "due_date": "2025-01-15T14:30",
            "created_by": {"user_id": "other_user"},
            "project_id": "proj123"
        }
        
        mock_membership_doc = Mock()
        mock_membership_doc.exists = True
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([Mock()])
                mock_tasks.where.return_value.where.return_value.stream.return_value = [mock_task]
                return mock_tasks
            elif name == "memberships":
                mock_mems = Mock()
                mock_mems.document.return_value.get.return_value = mock_membership_doc
                return mock_mems
            elif name == "users":
                mock_user_doc = Mock()
                mock_user_doc.exists = True
                mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
                return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_user_doc))))
            elif name == "notifications":
                mock_notifs = Mock()
                mock_notifs.where.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                mock_notifs.document.return_value = Mock(id="notif123")
                return mock_notifs
        
        mock_db.collection.side_effect = mock_collection
        
        with patch('backend.api.notifications.send_email_util', return_value=True):
            result = _notify_user_due_tasks(
                mock_db,
                "user123",
                "2025-01-15T00:00:00+00:00",
                "2025-01-16T00:00:00+00:00"
            )
        
        assert result == 1
    
    def test_notify_user_project_member_not_exists(self, mock_db):
        """Branch: project_id exists but user is not member (line 303->False)"""
        from backend.api.notifications import _notify_user_due_tasks
        
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Project Task",
            "due_date": "2025-01-15T14:30",
            "created_by": {"user_id": "other_user"},
            "project_id": "proj123"
        }
        
        mock_membership_doc = Mock()
        mock_membership_doc.exists = False
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([Mock()])
                mock_tasks.where.return_value.where.return_value.stream.return_value = [mock_task]
                return mock_tasks
            elif name == "memberships":
                mock_mems = Mock()
                mock_mems.document.return_value.get.return_value = mock_membership_doc
                return mock_mems
        
        mock_db.collection.side_effect = mock_collection
        
        result = _notify_user_due_tasks(
            mock_db,
            "user123",
            "2025-01-15T00:00:00+00:00",
            "2025-01-16T00:00:00+00:00"
        )
        
        assert result == 0
    
    def test_notify_user_user_email_exception(self, mock_db):
        """Branch: exception getting user email (line 316->317)"""
        from backend.api.notifications import _notify_user_due_tasks
        
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Task",
            "due_date": "2025-01-15T14:30",
            "created_by": {"user_id": "user123"}
        }
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([Mock()])
                mock_tasks.where.return_value.where.return_value.stream.return_value = [mock_task]
                return mock_tasks
            elif name == "users":
                def raise_error(*args, **kwargs):
                    raise Exception("DB error")
                return Mock(document=Mock(return_value=Mock(get=Mock(side_effect=raise_error))))
            elif name == "notifications":
                mock_notifs = Mock()
                mock_notifs.where.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                mock_notifs.document.return_value = Mock(id="notif123")
                return mock_notifs
        
        mock_db.collection.side_effect = mock_collection
        
        with patch('backend.api.notifications.send_email_util', return_value=True):
            result = _notify_user_due_tasks(
                mock_db,
                "user123",
                "2025-01-15T00:00:00+00:00",
                "2025-01-16T00:00:00+00:00"
            )
        
        assert result == 1
    
    def test_notify_user_existing_notification_exists(self, mock_db):
        """Branch: existing notification found (line 324->325)"""
        from backend.api.notifications import _notify_user_due_tasks
        
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Task",
            "due_date": "2025-01-15T14:30",
            "created_by": {"user_id": "user123"}
        }
        
        mock_existing = Mock()
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.limit.return_value.stream.return_value = iter([Mock()])
                mock_tasks.where.return_value.where.return_value.stream.return_value = [mock_task]
                return mock_tasks
            elif name == "users":
                mock_user_doc = Mock()
                mock_user_doc.exists = True
                mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
                return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_user_doc))))
            elif name == "notifications":
                mock_notifs = Mock()
                mock_notifs.where.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = iter([mock_existing])
                return mock_notifs
        
        mock_db.collection.side_effect = mock_collection
        
        result = _notify_user_due_tasks(
            mock_db,
            "user123",
            "2025-01-15T00:00:00+00:00",
            "2025-01-16T00:00:00+00:00"
        )
        
        assert result == 0


class TestDueTodayBranches:
    """Test branches in due_today endpoint"""
    
    def test_due_today_no_viewer(self, client, mock_db):
        """Branch: no viewer provided (line 345->346)"""
        response = client.get("/api/notifications/due-today")
        
        assert response.status_code == 401
    
    def test_due_today_with_start_end_iso(self, client, mock_db):
        """Branch: start_iso and end_iso provided (line 349->skip 351-356)"""
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        response = client.get(
            "/api/notifications/due-today",
            headers={"X-User-Id": "user123"},
            query_string={
                "start_iso": "2025-01-01T00:00:00+00:00",
                "end_iso": "2025-01-02T00:00:00+00:00"
            }
        )
        
        assert response.status_code == 200
    
    def test_due_today_without_iso_params(self, client, mock_db):
        """Branch: no start_iso/end_iso, calculate today (line 349->351)"""
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        response = client.get(
            "/api/notifications/due-today",
            headers={"X-User-Id": "user123"}
        )
        
        assert response.status_code == 200
    
    def test_due_today_query_preview_exception(self, client, mock_db):
        """Branch: exception in query preview (line 362->363)"""
        call_count = [0]
        
        def raise_on_limit(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # First call to limit
                raise Exception("Query error")
            return Mock(stream=Mock(return_value=[]))
        
        mock_db.collection.return_value.where.return_value.where.return_value.limit.side_effect = raise_on_limit
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
        
        response = client.get(
            "/api/notifications/due-today",
            headers={"X-User-Id": "user123"}
        )
        
        assert response.status_code == 200
    
    def test_due_today_archived_task(self, client, mock_db):
        """Branch: task is archived (line 369->370)"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "archived": True,
            "title": "Archived Task"
        }
        
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = [mock_task]
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        response = client.get(
            "/api/notifications/due-today",
            headers={"X-User-Id": "user123"}
        )
        
        data = response.get_json()
        assert data["count"] == 0
    
    def test_due_today_creator_matches_viewer(self, client, mock_db):
        """Branch: creator matches viewer (line 376->377)"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "My Task",
            "due_date": "2025-01-15T14:30",
            "created_by": {"user_id": "user123"},
            "assigned_to": None,
            "project_id": None
        }
        
        def mock_collection(name):
            if name == "tasks":
                mock_where = Mock()
                mock_where.where.return_value.stream.return_value = [mock_task]
                mock_where.where.return_value.limit.return_value.stream.return_value = []
                return Mock(where=Mock(return_value=mock_where))
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.get(
            "/api/notifications/due-today",
            headers={"X-User-Id": "user123"}
        )
        
        data = response.get_json()
        assert data["count"] == 1
        assert data["tasks"][0]["task_id"] == "task123"
    
    def test_due_today_assignee_matches_viewer(self, client, mock_db):
        """Branch: assignee matches viewer (line 379->380)"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Assigned Task",
            "due_date": "2025-01-15T14:30",
            "created_by": None,
            "assigned_to": {"user_id": "user123"},
            "project_id": None
        }
        
        def mock_collection(name):
            if name == "tasks":
                mock_where = Mock()
                mock_where.where.return_value.stream.return_value = [mock_task]
                mock_where.where.return_value.limit.return_value.stream.return_value = []
                return Mock(where=Mock(return_value=mock_where))
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.get(
            "/api/notifications/due-today",
            headers={"X-User-Id": "user123"}
        )
        
        data = response.get_json()
        assert data["count"] == 1
        assert data["tasks"][0]["task_id"] == "task123"
    
    def test_due_today_not_involved_no_project(self, client, mock_db):
        """Branch: not involved, no project_id (line 382->skip 383-387)"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Other Task",
            "due_date": "2025-01-15T14:30",
            "created_by": {"user_id": "other_user"},
            "assigned_to": {"user_id": "another_user"}
        }
        
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = [mock_task]
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        response = client.get(
            "/api/notifications/due-today",
            headers={"X-User-Id": "user123"}
        )
        
        data = response.get_json()
        assert data["count"] == 0
    
    def test_due_today_project_member_exists(self, client, mock_db):
        """Branch: project_id exists and user is member (line 383->384->386)"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Project Task",
            "due_date": "2025-01-15T14:30",
            "created_by": {"user_id": "other_user"},
            "project_id": "proj123"
        }
        
        mock_membership_doc = Mock()
        mock_membership_doc.exists = True
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.where.return_value.where.return_value.stream.return_value = [mock_task]
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "memberships":
                return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_membership_doc))))
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.get(
            "/api/notifications/due-today",
            headers={"X-User-Id": "user123"}
        )
        
        data = response.get_json()
        assert data["count"] == 1
    
    def test_due_today_project_member_not_exists(self, client, mock_db):
        """Branch: project_id exists but user is not member (line 385->False)"""
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Project Task",
            "due_date": "2025-01-15T14:30",
            "created_by": {"user_id": "other_user"},
            "project_id": "proj123"
        }
        
        mock_membership_doc = Mock()
        mock_membership_doc.exists = False
        
        def mock_collection(name):
            if name == "tasks":
                mock_tasks = Mock()
                mock_tasks.where.return_value.where.return_value.stream.return_value = [mock_task]
                mock_tasks.where.return_value.where.return_value.limit.return_value.stream.return_value = []
                return mock_tasks
            elif name == "memberships":
                return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_membership_doc))))
        
        mock_db.collection.side_effect = mock_collection
        
        response = client.get(
            "/api/notifications/due-today",
            headers={"X-User-Id": "user123"}
        )
        
        data = response.get_json()
        assert data["count"] == 0
