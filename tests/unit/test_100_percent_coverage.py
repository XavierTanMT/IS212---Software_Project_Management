"""Tests to achieve 100% branch coverage for manager.py and projects.py"""
import pytest
from unittest.mock import Mock, patch
from conftest import fake_firestore


class TestManagerBranchCoverage:
    """Tests to cover the remaining partial branches in manager.py"""
    
    def test_team_tasks_invalid_filter_by(self, client, mock_db, monkeypatch):
        """Test filter_by with INVALID value to make line 277 elif FALSE (not visual_status)"""
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
                mock_collection_obj.document.return_value.get.return_value.exists = False
            elif collection_name == "memberships":
                def mock_where(field=None, op=None, value=None, filter=None):
                    if filter is not None:
                        field = getattr(filter, "field_path", field)
                    mock_query = Mock()
                    mock_query.stream.return_value = [mock_membership] if field == "user_id" else [mock_team_membership]
                    return mock_query
                mock_collection_obj.where = mock_where
            elif collection_name == "tasks":
                def mock_where(field=None, op=None, value=None, filter=None):
                    mock_query = Mock()
                    mock_query.stream.return_value = [mock_task]
                    return mock_query
                mock_collection_obj.where = mock_where
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        # Use filter_by="INVALID" - this will NOT match any of the if/elif conditions
        # So ALL elif branches (lines 272, 274, 275, 277) will be FALSE
        # This covers the FALSE branch of line 277
        response = client.get("/api/manager/team-tasks?filter_by=INVALID&filter_value=something",
                            headers={"X-User-Id": "manager1"})
        
        assert response.status_code == 200
    
    def test_team_tasks_invalid_sort_by(self, client, mock_db, monkeypatch):
        """Test sort_by with INVALID value to make line 285 elif FALSE (not project)"""
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
        
        mock_task = Mock()
        mock_task.id = "task1"
        mock_task.to_dict.return_value = {
            "title": "Task",
            "status": "To Do",
            "priority": 3,
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
                mock_collection_obj.document.return_value.get.return_value.exists = False
            elif collection_name == "memberships":
                def mock_where(field=None, op=None, value=None, filter=None):
                    if filter is not None:
                        field = getattr(filter, "field_path", field)
                    mock_query = Mock()
                    mock_query.stream.return_value = [mock_membership] if field == "user_id" else [mock_team_membership]
                    return mock_query
                mock_collection_obj.where = mock_where
            elif collection_name == "tasks":
                def mock_where(field=None, op=None, value=None, filter=None):
                    mock_query = Mock()
                    mock_query.stream.return_value = [mock_task]
                    return mock_query
                mock_collection_obj.where = mock_where
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        # Use sort_by="INVALID" - this will NOT match any of the if/elif conditions
        # So ALL elif branches (lines 281, 283, 285) will be FALSE
        # This covers the FALSE branch of line 285
        response = client.get("/api/manager/team-tasks?sort_by=INVALID",
                            headers={"X-User-Id": "manager1"})
        
        assert response.status_code == 200
    
    def test_team_tasks_member_not_exists(self, client, mock_db, monkeypatch):
        """Test with team member that doesn't exist - covers line 292 FALSE branch (292->290)"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_manager_doc = Mock()
        mock_manager_doc.exists = True
        mock_manager_doc.to_dict.return_value = {"role": "manager"}
        
        mock_team_member_doc = Mock()
        mock_team_member_doc.exists = False  # Member document doesn't exist
        
        mock_membership = Mock()
        mock_membership.to_dict.return_value = {"project_id": "proj1", "user_id": "manager1"}
        
        mock_team_membership = Mock()
        mock_team_membership.to_dict.return_value = {"project_id": "proj1", "user_id": "member1"}
        
        def mock_collection(collection_name):
            mock_collection_obj = Mock()
            if collection_name == "users":
                def mock_document(doc_id):
                    mock_doc_ref = Mock()
                    if doc_id == "manager1":
                        mock_doc_ref.get.return_value = mock_manager_doc
                    elif doc_id == "member1":
                        # Member document doesn't exist - FALSE branch of line 292
                        mock_doc_ref.get.return_value = mock_team_member_doc
                    else:
                        mock_doc_ref.get.return_value.exists = False
                    return mock_doc_ref
                mock_collection_obj.document = mock_document
            elif collection_name == "memberships":
                def mock_where(field=None, op=None, value=None, filter=None):
                    mock_query = Mock()
                    if filter is not None:
                        field = getattr(filter, "field_path", field)
                    if field == "user_id":
                        mock_query.stream.return_value = [mock_membership]
                    elif field == "project_id":
                        # Return one team member so the loop executes
                        mock_query.stream.return_value = [mock_team_membership]
                    else:
                        mock_query.stream.return_value = []
                    return mock_query
                mock_collection_obj.where = mock_where
            elif collection_name == "tasks":
                mock_collection_obj.where.return_value.stream.return_value = []
            elif collection_name == "projects":
                mock_collection_obj.document.return_value.get.return_value.exists = False
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        # Loop executes for member1 but member_doc.exists is FALSE (line 292)
        # So it skips the append and loops back to line 290
        response = client.get("/api/manager/team-tasks",
                            headers={"X-User-Id": "manager1"})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["team_members"] == []  # No members added because document doesn't exist


class TestProjectsBranchCoverage:
    """Tests to cover the remaining partial branch in projects.py"""
    
    def test_create_project_email_query_no_match(self, client, mock_db, monkeypatch):
        """Test email query that completes without finding a match (line 37 loop completes)"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {
            "user_id": "user1",
            "name": "User One",
            "email": "user1@test.com",
            "role": "member"
        }
        
        # Mock for the created project
        mock_project_ref = Mock()
        mock_project_ref.id = "new_project_id"
        mock_project_ref.set = Mock()
        
        # Mock for membership
        mock_membership_ref = Mock()
        mock_membership_ref.set = Mock()
        
        def mock_collection(collection_name):
            mock_collection_obj = Mock()
            if collection_name == "users":
                def mock_document(doc_id):
                    mock_doc_ref = Mock()
                    mock_doc_ref.get.return_value = mock_user_doc if doc_id == "user1" else Mock(exists=False)
                    return mock_doc_ref
                mock_collection_obj.document.side_effect = mock_document
                
                # Mock the where queries for owner resolution
                def mock_where(field=None, op=None, value=None, filter=None):
                    mock_query = Mock()
                    mock_limit = Mock()
                    
                    # First query by handle - no match
                    # Second query by email - EMPTY (no match, loop completes without break)
                    # This covers line 37 loop completion
                    empty_stream = iter([])  # Empty iterator - loop completes without breaking
                    mock_limit.stream.return_value = empty_stream
                    mock_query.limit.return_value = mock_limit
                    return mock_query
                
                mock_collection_obj.where.side_effect = mock_where
                
            elif collection_name == "projects":
                # Return mock project reference when document() is called
                mock_collection_obj.document.return_value = mock_project_ref
            
            elif collection_name == "memberships":
                # Return mock membership reference
                mock_collection_obj.document.return_value = mock_membership_ref
            
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        # Use an email-like owner_id that won't be found
        # This will make the email query (line 35-39) execute
        # The q2 iterator will be empty, so the loop at line 37 completes without breaking
        payload = {
            "name": "Test Project",
            "description": "A test project",
            "owner_id": "nonexistent@test.com",  # Email format but won't be found
            "status": "active"
        }
        
        response = client.post("/api/projects",
                              json=payload,
                              headers={"X-User-Id": "user1"})
        
        # Should still succeed even though owner wasn't resolved
        assert response.status_code == 201
        data = response.get_json()
        assert data["project_id"] == "new_project_id"

    def test_create_project_email_query_finds_match(self, client, mock_db, monkeypatch):
        """Test email query that FINDS a match - covers lines 42-43 (if resolved: resolve_id = resolved)"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {
            "user_id": "user1",
            "name": "User One",
            "email": "user1@test.com",
            "role": "member"
        }
        
        # Mock for the owner found by email
        mock_owner_by_email = Mock()
        mock_owner_by_email.id = "found_owner_id"
        
        # Mock for the created project
        mock_project_ref = Mock()
        mock_project_ref.id = "new_project_id"
        mock_project_ref.set = Mock()
        
        # Mock for membership
        mock_membership_ref = Mock()
        mock_membership_ref.set = Mock()
        
        def mock_collection(collection_name):
            mock_collection_obj = Mock()
            if collection_name == "users":
                def mock_document(doc_id):
                    mock_doc_ref = Mock()
                    mock_doc_ref.get.return_value = mock_user_doc if doc_id == "user1" else Mock(exists=False)
                    return mock_doc_ref
                mock_collection_obj.document.side_effect = mock_document
                
                # Mock the where queries for owner resolution
                # Track call count to distinguish between handle and email queries
                where_call_count = {"count": 0}
                
                def mock_where(field=None, op=None, value=None, filter=None):
                    mock_query = Mock()
                    mock_limit = Mock()
                    
                    where_call_count["count"] += 1
                    
                    # First call is handle query (no match)
                    # Second call is email query (finds match)
                    if where_call_count["count"] == 1:
                        # Handle query - no match
                        empty_stream = iter([])
                        mock_limit.stream.return_value = empty_stream
                    elif where_call_count["count"] == 2:
                        # Email query - FINDS A MATCH
                        # This makes resolved = d.id at line 39, then lines 42-43 execute
                        match_stream = iter([mock_owner_by_email])
                        mock_limit.stream.return_value = match_stream
                    else:
                        empty_stream = iter([])
                        mock_limit.stream.return_value = empty_stream
                    
                    mock_query.limit.return_value = mock_limit
                    return mock_query
                
                mock_collection_obj.where.side_effect = mock_where
                
            elif collection_name == "projects":
                mock_collection_obj.document.return_value = mock_project_ref
            
            elif collection_name == "memberships":
                mock_collection_obj.document.return_value = mock_membership_ref
            
            return mock_collection_obj
        
        mock_db.collection.side_effect = mock_collection
        
        # Use an email-like owner_id (contains @)
        # This will:
        # 1. Fail document lookup (line 25)
        # 2. Fail handle query (line 29-33)
        # 3. Execute email query (line 35-39) and FIND a match
        # 4. Set resolved = "found_owner_id"
        # 5. Execute lines 42-43: if resolved: resolve_id = resolved
        payload = {
            "name": "Test Project",
            "description": "A test project",
            "owner_id": "owner@example.com",  # Email that will be found
            "status": "active"
        }
        
        response = client.post("/api/projects",
                              json=payload,
                              headers={"X-User-Id": "user1"})
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["project_id"] == "new_project_id"
        # The owner_id should have been resolved to the found user
        # (though we can't easily check this in the response without more complex mocking)
