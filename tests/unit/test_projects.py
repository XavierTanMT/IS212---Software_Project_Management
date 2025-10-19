import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
import sys

# Get fake_firestore from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")

from flask import Flask
from backend.api import projects_bp
from backend.api import projects as projects_module


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = Flask('test_projects_app')
    app.config['TESTING'] = True
    # Use try-except to handle blueprint already registered
    try:
        app.register_blueprint(projects_bp)
    except AssertionError:
        # Blueprint already registered, that's okay
        pass
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


class TestNowIso:
    """Test the now_iso helper function"""
    
    def test_now_iso_returns_iso_format(self):
        """Test that now_iso returns ISO formatted datetime string"""
        # Mock datetime to control the timestamp
        mock_dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        with patch('backend.api.projects.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_dt
            
            result = projects_module.now_iso()
            
            assert result == "2024-01-15T10:30:45+00:00"
            mock_datetime.now.assert_called_once_with(timezone.utc)


class TestCreateProject:
    """Test the create_project POST endpoint"""
    
    def test_create_project_success(self, client, mock_db, monkeypatch):
        """Test successfully creating a new project"""
        # Setup mocks
        mock_proj_ref = Mock()
        mock_proj_ref.id = "proj123"
        mock_mem_ref = Mock()
        
        # Mock collection().document() to return different refs
        def mock_document(doc_id=None):
            if doc_id is None:
                return mock_proj_ref
            elif doc_id.startswith("proj123_"):
                return mock_mem_ref
            return Mock()
        
        mock_db.collection.return_value.document = mock_document
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Make request
        payload = {
            "name": "Test Project",
            "key": "TP",
            "owner_id": "user123",
            "description": "A test project"
        }
        response = client.post("/api/projects", json=payload)
        
        # Assertions
        assert response.status_code == 201
        data = response.get_json()
        assert data["project_id"] == "proj123"
        assert data["name"] == "Test Project"
        assert data["key"] == "TP"
        assert data["owner_id"] == "user123"
        assert data["description"] == "A test project"
        assert data["archived"] == False
        assert "created_at" in data
        
        # Verify database calls
        assert mock_proj_ref.set.called
        assert mock_mem_ref.set.called
        
    def test_create_project_minimal_fields(self, client, mock_db, monkeypatch):
        """Test creating project with only required fields"""
        mock_proj_ref = Mock()
        mock_proj_ref.id = "proj456"
        mock_mem_ref = Mock()
        
        def mock_document(doc_id=None):
            if doc_id is None:
                return mock_proj_ref
            return mock_mem_ref
        
        mock_db.collection.return_value.document = mock_document
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "Minimal Project",
            "owner_id": "user123"
        }
        response = client.post("/api/projects", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Minimal Project"
        assert data["owner_id"] == "user123"
        assert data["key"] is None
        assert data["description"] is None
        
    def test_create_project_trims_whitespace(self, client, mock_db, monkeypatch):
        """Test that fields are trimmed"""
        mock_proj_ref = Mock()
        mock_proj_ref.id = "proj789"
        mock_mem_ref = Mock()
        
        def mock_document(doc_id=None):
            if doc_id is None:
                return mock_proj_ref
            return mock_mem_ref
        
        mock_db.collection.return_value.document = mock_document
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "  Test Project  ",
            "key": "  TP  ",
            "owner_id": "  user123  ",
            "description": "  A test  "
        }
        response = client.post("/api/projects", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Test Project"
        assert data["key"] == "TP"
        assert data["owner_id"] == "user123"
        assert data["description"] == "A test"
        
    def test_create_project_missing_name(self, client, mock_db, monkeypatch):
        """Test error when name is missing"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "owner_id": "user123"
        }
        response = client.post("/api/projects", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "name and owner_id are required" in data["error"]
        
    def test_create_project_missing_owner_id(self, client, mock_db, monkeypatch):
        """Test error when owner_id is missing"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "Test Project"
        }
        response = client.post("/api/projects", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "name and owner_id are required" in data["error"]
        
    def test_create_project_empty_name(self, client, mock_db, monkeypatch):
        """Test error when name is empty string"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "",
            "owner_id": "user123"
        }
        response = client.post("/api/projects", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        
    def test_create_project_empty_owner_id(self, client, mock_db, monkeypatch):
        """Test error when owner_id is empty string"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "Test Project",
            "owner_id": ""
        }
        response = client.post("/api/projects", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        
    def test_create_project_whitespace_only_fields(self, client, mock_db, monkeypatch):
        """Test error when fields are only whitespace"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "   ",
            "owner_id": "   "
        }
        response = client.post("/api/projects", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        
    def test_create_project_empty_payload(self, client, mock_db, monkeypatch):
        """Test error when payload is empty"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post("/api/projects", json={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        
    def test_create_project_creates_membership(self, client, mock_db, monkeypatch):
        """Test that creating project also creates owner membership"""
        mock_proj_ref = Mock()
        mock_proj_ref.id = "proj123"
        mock_mem_ref = Mock()
        
        membership_doc_id = None
        membership_data = None
        
        def mock_document(doc_id=None):
            nonlocal membership_doc_id
            if doc_id is None:
                return mock_proj_ref
            else:
                membership_doc_id = doc_id
                return mock_mem_ref
        
        def mock_mem_set(data):
            nonlocal membership_data
            membership_data = data
        
        mock_mem_ref.set = mock_mem_set
        mock_db.collection.return_value.document = mock_document
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "Test Project",
            "owner_id": "user123"
        }
        response = client.post("/api/projects", json=payload)
        
        assert response.status_code == 201
        # Verify membership was created
        assert membership_doc_id == "proj123_user123"
        assert membership_data is not None
        assert membership_data["project_id"] == "proj123"
        assert membership_data["user_id"] == "user123"
        assert membership_data["role"] == "owner"


class TestListProjects:
    """Test the list_projects GET endpoint"""
    
    def test_list_projects_success(self, client, mock_db, monkeypatch):
        """Test successfully listing projects"""
        # Setup mock documents
        mock_doc1 = Mock()
        mock_doc1.id = "proj1"
        mock_doc1.to_dict.return_value = {
            "name": "Project 1",
            "owner_id": "user1",
            "created_at": "2024-01-01T00:00:00+00:00",
            "archived": False
        }
        mock_doc2 = Mock()
        mock_doc2.id = "proj2"
        mock_doc2.to_dict.return_value = {
            "name": "Project 2",
            "owner_id": "user2",
            "created_at": "2024-01-02T00:00:00+00:00",
            "archived": False
        }
        
        # Mock the query chain
        mock_query = Mock()
        mock_query.limit.return_value.stream.return_value = [mock_doc1, mock_doc2]
        mock_db.collection.return_value.order_by.return_value = mock_query
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Need to set Query.DESCENDING on fake_firestore
        fake_firestore.Query = Mock()
        fake_firestore.Query.DESCENDING = "DESCENDING"
        
        response = client.get("/api/projects")
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        assert data[0]["project_id"] == "proj1"
        assert data[0]["name"] == "Project 1"
        assert data[1]["project_id"] == "proj2"
        assert data[1]["name"] == "Project 2"
        
    def test_list_projects_empty_result(self, client, mock_db, monkeypatch):
        """Test listing projects when there are none"""
        mock_query = Mock()
        mock_query.limit.return_value.stream.return_value = []
        mock_db.collection.return_value.order_by.return_value = mock_query
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        fake_firestore.Query = Mock()
        fake_firestore.Query.DESCENDING = "DESCENDING"
        
        response = client.get("/api/projects")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data == []


class TestGetProject:
    """Test the get_project GET endpoint"""
    
    def test_get_project_success(self, client, mock_db, monkeypatch):
        """Test successfully retrieving a project"""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.id = "proj123"
        mock_doc.to_dict.return_value = {
            "name": "Test Project",
            "key": "TP",
            "owner_id": "user123",
            "description": "A test project",
            "created_at": "2024-01-01T00:00:00+00:00",
            "archived": False
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/projects/proj123")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["project_id"] == "proj123"
        assert data["name"] == "Test Project"
        assert data["key"] == "TP"
        
    def test_get_project_not_found(self, client, mock_db, monkeypatch):
        """Test error when project doesn't exist"""
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/projects/nonexistent")
        
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "Project not found" in data["error"]


class TestPatchProject:
    """Test the patch_project PATCH endpoint"""
    
    def test_patch_project_success(self, client, mock_db, monkeypatch):
        """Test successfully updating a project"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = True
        
        # First get() call checks existence, second get() returns updated data
        updated_data = {
            "name": "Updated Project",
            "key": "UP",
            "description": "Updated description",
            "archived": False,
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-02T00:00:00+00:00"
        }
        mock_get_result.to_dict.return_value = updated_data
        mock_ref.get.return_value = mock_get_result
        
        mock_db.collection.return_value.document.return_value = mock_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "Updated Project",
            "description": "Updated description"
        }
        response = client.patch("/api/projects/proj123", json=payload)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["project_id"] == "proj123"
        assert data["name"] == "Updated Project"
        
        # Verify update was called
        mock_ref.update.assert_called_once()
        
    def test_patch_project_update_name(self, client, mock_db, monkeypatch):
        """Test updating only the name"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = True
        mock_get_result.to_dict.return_value = {
            "name": "New Name",
            "key": "TP",
            "owner_id": "user123",
            "archived": False
        }
        mock_ref.get.return_value = mock_get_result
        
        mock_db.collection.return_value.document.return_value = mock_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {"name": "New Name"}
        response = client.patch("/api/projects/proj123", json=payload)
        
        assert response.status_code == 200
        
    def test_patch_project_update_key(self, client, mock_db, monkeypatch):
        """Test updating only the key"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = True
        mock_get_result.to_dict.return_value = {
            "name": "Project",
            "key": "NEW",
            "owner_id": "user123",
            "archived": False
        }
        mock_ref.get.return_value = mock_get_result
        
        mock_db.collection.return_value.document.return_value = mock_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {"key": "NEW"}
        response = client.patch("/api/projects/proj123", json=payload)
        
        assert response.status_code == 200
        
    def test_patch_project_update_description(self, client, mock_db, monkeypatch):
        """Test updating only the description"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = True
        mock_get_result.to_dict.return_value = {
            "name": "Project",
            "description": "New description",
            "owner_id": "user123",
            "archived": False
        }
        mock_ref.get.return_value = mock_get_result
        
        mock_db.collection.return_value.document.return_value = mock_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {"description": "New description"}
        response = client.patch("/api/projects/proj123", json=payload)
        
        assert response.status_code == 200
        
    def test_patch_project_archive(self, client, mock_db, monkeypatch):
        """Test archiving a project"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = True
        mock_get_result.to_dict.return_value = {
            "name": "Project",
            "owner_id": "user123",
            "archived": True
        }
        mock_ref.get.return_value = mock_get_result
        
        mock_db.collection.return_value.document.return_value = mock_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {"archived": True}
        response = client.patch("/api/projects/proj123", json=payload)
        
        assert response.status_code == 200
        
    def test_patch_project_not_found(self, client, mock_db, monkeypatch):
        """Test error when project doesn't exist"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = False
        mock_ref.get.return_value = mock_get_result
        
        mock_db.collection.return_value.document.return_value = mock_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {"name": "Updated Name"}
        response = client.patch("/api/projects/nonexistent", json=payload)
        
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "Project not found" in data["error"]
        
    def test_patch_project_no_valid_fields(self, client, mock_db, monkeypatch):
        """Test error when no valid fields to update"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = True
        mock_ref.get.return_value = mock_get_result
        
        mock_db.collection.return_value.document.return_value = mock_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {"invalid_field": "value"}
        response = client.patch("/api/projects/proj123", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "No fields to update" in data["error"]
        
    def test_patch_project_empty_payload(self, client, mock_db, monkeypatch):
        """Test error when payload is empty"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = True
        mock_ref.get.return_value = mock_get_result
        
        mock_db.collection.return_value.document.return_value = mock_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.patch("/api/projects/proj123", json={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data


class TestDeleteProject:
    """Test the delete_project DELETE endpoint"""
    
    def test_delete_project_success(self, client, mock_db, monkeypatch):
        """Test successfully deleting a project"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = True
        mock_ref.get.return_value = mock_get_result
        
        # Mock memberships query
        mock_mem1 = Mock()
        mock_mem1.id = "mem1"
        mock_mem2 = Mock()
        mock_mem2.id = "mem2"
        
        mock_db.collection.return_value.document.return_value = mock_ref
        
        # Setup collection mocking for both projects and memberships
        def mock_collection(name):
            if name == "projects":
                projects_collection = Mock()
                projects_collection.document.return_value = mock_ref
                return projects_collection
            elif name == "memberships":
                memberships_collection = Mock()
                memberships_collection.where.return_value.stream.return_value = [mock_mem1, mock_mem2]
                memberships_collection.document = Mock(return_value=Mock())
                return memberships_collection
            return Mock()
        
        mock_db.collection = mock_collection
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete("/api/projects/proj123")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] == True
        assert data["project_id"] == "proj123"
        
        # Verify delete was called
        mock_ref.delete.assert_called_once()
        
    def test_delete_project_not_found(self, client, mock_db, monkeypatch):
        """Test error when project doesn't exist"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = False
        mock_ref.get.return_value = mock_get_result
        
        mock_db.collection.return_value.document.return_value = mock_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete("/api/projects/nonexistent")
        
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "Project not found" in data["error"]
        
    def test_delete_project_cleans_up_memberships(self, client, mock_db, monkeypatch):
        """Test that deleting project also deletes associated memberships"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = True
        mock_ref.get.return_value = mock_get_result
        
        # Mock memberships
        mock_mem1 = Mock()
        mock_mem1.id = "mem1"
        mock_mem2 = Mock()
        mock_mem2.id = "mem2"
        
        deleted_memberships = []
        
        def mock_collection(name):
            if name == "projects":
                projects_collection = Mock()
                projects_collection.document.return_value = mock_ref
                return projects_collection
            elif name == "memberships":
                memberships_collection = Mock()
                memberships_collection.where.return_value.stream.return_value = [mock_mem1, mock_mem2]
                
                def mock_mem_document(mem_id):
                    mem_doc = Mock()
                    def delete_mem():
                        deleted_memberships.append(mem_id)
                    mem_doc.delete = delete_mem
                    return mem_doc
                
                memberships_collection.document = mock_mem_document
                return memberships_collection
            return Mock()
        
        mock_db.collection = mock_collection
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete("/api/projects/proj123")
        
        assert response.status_code == 200
        # Verify memberships were deleted
        assert "mem1" in deleted_memberships
        assert "mem2" in deleted_memberships


class TestBlueprintRegistration:
    """Test blueprint is properly registered"""
    
    def test_blueprint_registered(self, client, mock_db, monkeypatch):
        """Test that projects blueprint is registered with correct prefix"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Test POST endpoint
        response = client.post("/api/projects", json={})
        assert response.status_code == 400  # validation error, not 404
        
        # Test GET list endpoint
        mock_query = Mock()
        mock_query.limit.return_value.stream.return_value = []
        mock_db.collection.return_value.order_by.return_value = mock_query
        fake_firestore.Query = Mock()
        fake_firestore.Query.DESCENDING = "DESCENDING"
        
        response = client.get("/api/projects")
        assert response.status_code == 200  # success, not 404


class TestEdgeCases:
    """Test edge cases and integration scenarios"""
    
    def test_create_project_with_special_characters(self, client, mock_db, monkeypatch):
        """Test creating project with special characters in name"""
        mock_proj_ref = Mock()
        mock_proj_ref.id = "proj123"
        mock_mem_ref = Mock()
        
        def mock_document(doc_id=None):
            if doc_id is None:
                return mock_proj_ref
            return mock_mem_ref
        
        mock_db.collection.return_value.document = mock_document
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "Project: Test & Development (2024)",
            "owner_id": "user123"
        }
        response = client.post("/api/projects", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Project: Test & Development (2024)"
        
    def test_patch_project_multiple_fields(self, client, mock_db, monkeypatch):
        """Test updating multiple fields at once"""
        mock_ref = Mock()
        mock_get_result = Mock()
        mock_get_result.exists = True
        mock_get_result.to_dict.return_value = {
            "name": "New Name",
            "key": "NEW",
            "description": "New Desc",
            "archived": True
        }
        mock_ref.get.return_value = mock_get_result
        
        mock_db.collection.return_value.document.return_value = mock_ref
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "New Name",
            "key": "NEW",
            "description": "New Desc",
            "archived": True
        }
        response = client.patch("/api/projects/proj123", json=payload)
        
        assert response.status_code == 200
