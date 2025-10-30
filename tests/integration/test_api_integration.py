"""API Integration tests - Testing Flask endpoints with real Firebase backend."""
import pytest
import json
from datetime import datetime, timezone, timedelta


class TestUserAPIIntegration:
    """Test user API endpoints with real Firebase."""
    
    def test_create_user_via_api(self, client, db, test_collection_prefix, cleanup_collections):
        """Test creating user through POST /api/users endpoint."""
        users_collection = f"{test_collection_prefix}_users"
        cleanup_collections.append(users_collection)
        
        user_id = f"api_user_{datetime.now(timezone.utc).timestamp()}"
        payload = {
            "user_id": user_id,
            "email": f"{user_id}@example.com",
            "name": "API Test User",
            "role": "Member"
        }
        
        # Call API endpoint
        response = client.post("/api/users", 
                             json=payload,
                             headers={"Content-Type": "application/json"})
        
        # Verify API response
        assert response.status_code == 201
        data = response.get_json()
        assert data["user"]["user_id"] == user_id
        assert data["user"]["email"] == payload["email"]
        
        # Verify data in Firebase
        doc = db.collection("users").document(user_id).get()
        assert doc.exists
        assert doc.to_dict()["email"] == payload["email"]
        
        # Cleanup
        db.collection("users").document(user_id).delete()
    
    
    def test_get_user_via_api(self, client, db):
        """Test retrieving user through GET /api/users/<user_id> endpoint."""
        # Create test user directly in Firebase
        user_id = f"get_user_{datetime.now(timezone.utc).timestamp()}"
        user_data = {
            "user_id": user_id,
            "email": f"{user_id}@example.com",
            "name": "Get Test User",
            "role": "Member"
        }
        db.collection("users").document(user_id).set(user_data)
        
        try:
            # Call API endpoint
            response = client.get(f"/api/users/{user_id}")
            
            # Verify response
            assert response.status_code == 200
            data = response.get_json()
            assert data["user_id"] == user_id
            assert data["email"] == user_data["email"]
        finally:
            # Cleanup
            db.collection("users").document(user_id).delete()
    
    
    def test_list_users_via_api(self, client, db):
        """Test listing users through GET /api/users endpoint."""
        # Create multiple test users
        user_ids = []
        for i in range(3):
            user_id = f"list_user_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection("users").document(user_id).set({
                "user_id": user_id,
                "email": f"{user_id}@example.com",
                "name": f"List User {i}"
            })
            user_ids.append(user_id)
        
        try:
            # Call API endpoint
            response = client.get("/api/users")
            
            # Verify response
            assert response.status_code == 200
            data = response.get_json()
            assert "users" in data
            assert len(data["users"]) >= 3
        finally:
            # Cleanup
            for user_id in user_ids:
                db.collection("users").document(user_id).delete()


class TestTaskAPIIntegration:
    """Test task API endpoints with real Firebase."""
    
    def test_create_task_via_api(self, client, db):
        """Test creating task through POST /api/tasks endpoint."""
        task_id = f"api_task_{datetime.now(timezone.utc).timestamp()}"
        payload = {
            "task_id": task_id,
            "title": "API Task",
            "description": "Task created via API",
            "status": "To Do",
            "priority": 5,
            "created_by": {"user_id": "test_creator", "name": "Creator"}
        }
        
        # Call API endpoint
        response = client.post("/api/tasks",
                             json=payload,
                             headers={"X-User-Id": "test_creator"})
        
        try:
            # Verify API response
            assert response.status_code == 201
            data = response.get_json()
            assert data["task"]["task_id"] == task_id
            assert data["task"]["title"] == payload["title"]
            
            # Verify data in Firebase
            doc = db.collection("tasks").document(task_id).get()
            assert doc.exists
            assert doc.to_dict()["title"] == payload["title"]
        finally:
            # Cleanup
            db.collection("tasks").document(task_id).delete()
    
    
    def test_get_task_via_api(self, client, db):
        """Test retrieving task through GET /api/tasks/<task_id> endpoint."""
        # Create test task in Firebase
        task_id = f"get_task_{datetime.now(timezone.utc).timestamp()}"
        task_data = {
            "task_id": task_id,
            "title": "Get Test Task",
            "status": "To Do",
            "priority": 3
        }
        db.collection("tasks").document(task_id).set(task_data)
        
        try:
            # Call API endpoint
            response = client.get(f"/api/tasks/{task_id}",
                                headers={"X-User-Id": "test_user"})
            
            # Verify response
            assert response.status_code == 200
            data = response.get_json()
            assert data["task_id"] == task_id
            assert data["title"] == task_data["title"]
        finally:
            # Cleanup
            db.collection("tasks").document(task_id).delete()
    
    
    def test_update_task_via_api(self, client, db):
        """Test updating task through PATCH /api/tasks/<task_id> endpoint."""
        # Create test task
        task_id = f"update_task_{datetime.now(timezone.utc).timestamp()}"
        db.collection("tasks").document(task_id).set({
            "task_id": task_id,
            "title": "Original Title",
            "status": "To Do",
            "priority": 5
        })
        
        try:
            # Update via API
            update_payload = {
                "title": "Updated Title",
                "status": "In Progress",
                "priority": 10
            }
            response = client.patch(f"/api/tasks/{task_id}",
                                  json=update_payload,
                                  headers={"X-User-Id": "test_user"})
            
            # Verify API response
            assert response.status_code == 200
            data = response.get_json()
            assert data["task"]["title"] == "Updated Title"
            assert data["task"]["status"] == "In Progress"
            
            # Verify data in Firebase
            doc = db.collection("tasks").document(task_id).get()
            updated_data = doc.to_dict()
            assert updated_data["title"] == "Updated Title"
            assert updated_data["priority"] == 10
        finally:
            # Cleanup
            db.collection("tasks").document(task_id).delete()
    
    
    def test_delete_task_via_api(self, client, db):
        """Test deleting task through DELETE /api/tasks/<task_id> endpoint."""
        # Create test task
        task_id = f"delete_task_{datetime.now(timezone.utc).timestamp()}"
        db.collection("tasks").document(task_id).set({
            "task_id": task_id,
            "title": "Task to Delete",
            "status": "To Do"
        })
        
        # Verify task exists
        doc = db.collection("tasks").document(task_id).get()
        assert doc.exists
        
        # Delete via API
        response = client.delete(f"/api/tasks/{task_id}",
                               headers={"X-User-Id": "test_user"})
        
        # Verify API response
        assert response.status_code == 200
        
        # Verify task is deleted from Firebase
        doc = db.collection("tasks").document(task_id).get()
        assert not doc.exists


class TestProjectAPIIntegration:
    """Test project API endpoints with real Firebase."""
    
    def test_create_project_via_api(self, client, db):
        """Test creating project through POST /api/projects endpoint."""
        project_id = f"api_project_{datetime.now(timezone.utc).timestamp()}"
        payload = {
            "project_id": project_id,
            "name": "API Project",
            "description": "Project created via API"
        }
        
        response = client.post("/api/projects",
                             json=payload,
                             headers={"X-User-Id": "test_creator"})
        
        try:
            assert response.status_code == 201
            data = response.get_json()
            assert data["project"]["project_id"] == project_id
            
            # Verify in Firebase
            doc = db.collection("projects").document(project_id).get()
            assert doc.exists
        finally:
            db.collection("projects").document(project_id).delete()
    
    
    def test_list_projects_via_api(self, client, db):
        """Test listing projects through GET /api/projects endpoint."""
        # Create test projects
        project_ids = []
        for i in range(2):
            project_id = f"list_proj_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection("projects").document(project_id).set({
                "project_id": project_id,
                "name": f"Project {i}"
            })
            project_ids.append(project_id)
        
        try:
            response = client.get("/api/projects",
                                headers={"X-User-Id": "test_user"})
            
            assert response.status_code == 200
            data = response.get_json()
            assert "projects" in data
        finally:
            for project_id in project_ids:
                db.collection("projects").document(project_id).delete()


class TestDashboardAPIIntegration:
    """Test dashboard API endpoints with real Firebase."""
    
    def test_get_user_dashboard_via_api(self, client, db):
        """Test GET /api/users/<user_id>/dashboard endpoint."""
        # Create test user
        user_id = f"dashboard_user_{datetime.now(timezone.utc).timestamp()}"
        db.collection("users").document(user_id).set({
            "user_id": user_id,
            "email": f"{user_id}@example.com",
            "name": "Dashboard User"
        })
        
        # Create tasks for user
        task_ids = []
        for i in range(2):
            task_id = f"dashboard_task_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection("tasks").document(task_id).set({
                "task_id": task_id,
                "title": f"Dashboard Task {i}",
                "status": "To Do",
                "created_by": {"user_id": user_id},
                "priority": 5
            })
            task_ids.append(task_id)
        
        try:
            # Call dashboard API
            response = client.get(f"/api/users/{user_id}/dashboard")
            
            assert response.status_code == 200
            data = response.get_json()
            assert "tasks" in data
            assert "statistics" in data
        finally:
            # Cleanup
            db.collection("users").document(user_id).delete()
            for task_id in task_ids:
                db.collection("tasks").document(task_id).delete()


class TestLabelAPIIntegration:
    """Test label API endpoints with real Firebase."""
    
    def test_create_label_via_api(self, client, db):
        """Test creating label through POST /api/labels endpoint."""
        label_id = f"api_label_{datetime.now(timezone.utc).timestamp()}"
        payload = {
            "label_id": label_id,
            "name": "API Label",
            "color": "blue"
        }
        
        response = client.post("/api/labels", json=payload)
        
        try:
            assert response.status_code == 201
            data = response.get_json()
            assert data["label_id"] == label_id
            
            # Verify in Firebase
            doc = db.collection("labels").document(label_id).get()
            assert doc.exists
        finally:
            db.collection("labels").document(label_id).delete()
    
    
    def test_assign_label_to_task_via_api(self, client, db):
        """Test POST /api/labels/<label_id>/assign endpoint."""
        # Create label and task
        label_id = f"assign_label_{datetime.now(timezone.utc).timestamp()}"
        task_id = f"assign_task_{datetime.now(timezone.utc).timestamp()}"
        
        db.collection("labels").document(label_id).set({
            "label_id": label_id,
            "name": "Test Label",
            "color": "red"
        })
        
        db.collection("tasks").document(task_id).set({
            "task_id": task_id,
            "title": "Test Task",
            "labels": []
        })
        
        try:
            # Assign label via API
            response = client.post(f"/api/labels/{label_id}/assign",
                                 json={"task_id": task_id})
            
            assert response.status_code == 200
            
            # Verify task has label
            doc = db.collection("tasks").document(task_id).get()
            task_data = doc.to_dict()
            assert label_id in task_data.get("labels", [])
        finally:
            db.collection("labels").document(label_id).delete()
            db.collection("tasks").document(task_id).delete()


class TestNotesAPIIntegration:
    """Test notes/comments API endpoints with real Firebase."""
    
    def test_add_comment_via_api(self, client, db):
        """Test adding comment through POST /api/notes endpoint."""
        task_id = "test_task_for_comment"
        comment_payload = {
            "task_id": task_id,
            "author_id": "test_author",
            "body": "This is a test comment via API"
        }
        
        response = client.post("/api/notes", json=comment_payload)
        
        try:
            assert response.status_code == 201
            data = response.get_json()
            note_id = data["note_id"]
            assert data["body"] == comment_payload["body"]
            
            # Verify in Firebase
            doc = db.collection("notes").document(note_id).get()
            assert doc.exists
            
            # Cleanup
            db.collection("notes").document(note_id).delete()
        except:
            pass
    
    
    def test_list_task_comments_via_api(self, client, db):
        """Test listing comments through GET /api/tasks/<task_id>/notes endpoint."""
        task_id = f"task_with_notes_{datetime.now(timezone.utc).timestamp()}"
        
        # Create comments in Firebase
        note_ids = []
        for i in range(2):
            note_id = f"note_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection("notes").document(note_id).set({
                "note_id": note_id,
                "task_id": task_id,
                "author_id": "test_author",
                "body": f"Comment {i}",
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            note_ids.append(note_id)
        
        try:
            # Get comments via API
            response = client.get(f"/api/tasks/{task_id}/notes")
            
            assert response.status_code == 200
            data = response.get_json()
            assert "notes" in data
        finally:
            for note_id in note_ids:
                db.collection("notes").document(note_id).delete()
