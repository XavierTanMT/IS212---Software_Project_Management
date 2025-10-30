"""
Integration tests for API endpoints using Flask test client.

These tests verify that API endpoints work correctly by making HTTP requests
and confirming both the API responses and Firebase data persistence.
"""

from datetime import datetime, timezone


class TestUserAPIIntegration:
    """Test user API endpoints with real Firebase."""
    
    def test_create_user_via_api(self, client, db):
        """Test POST /api/users - create user."""
        user_id = f"api_user_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        payload = {
            "user_id": user_id,
            "name": "API Test User",
            "email": f"{user_id}@example.com"
        }
        
        # Call API
        response = client.post("/api/users", json=payload)
        
        try:
            # Verify API response
            assert response.status_code == 201
            data = response.get_json()
            assert "user" in data
            assert data["user"]["user_id"] == user_id
            
            # Verify Firebase
            doc = db.collection("users").document(user_id).get()
            assert doc.exists
        finally:
            db.collection("users").document(user_id).delete()
    
    
    def test_get_user_via_api(self, client, db):
        """Test GET /api/users/<user_id> - get user."""
        user_id = f"get_user_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        user_data = {
            "user_id": user_id,
            "name": "Get Test",
            "email": f"{user_id}@example.com"
        }
        db.collection("users").document(user_id).set(user_data)
        
        try:
            response = client.get(f"/api/users/{user_id}")
            assert response.status_code == 200
            data = response.get_json()
            assert data["user_id"] == user_id
        finally:
            db.collection("users").document(user_id).delete()
    
    
    def test_get_user_role_via_api(self, client, db):
        """Test GET /api/users/<user_id>/role - get user role."""
        user_id = f"role_user_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        user_data = {
            "user_id": user_id,
            "name": "Role Test",
            "email": f"{user_id}@example.com",
            "role": "manager"
        }
        db.collection("users").document(user_id).set(user_data)
        
        try:
            response = client.get(f"/api/users/{user_id}/role")
            assert response.status_code == 200
            data = response.get_json()
            assert data["role"] == "manager"
        finally:
            db.collection("users").document(user_id).delete()


class TestTaskAPIIntegration:
    """Test task API endpoints with real Firebase."""
    
    def test_create_task_via_api(self, client, db):
        """Test POST /api/tasks - create task."""
        # Create user first (required by API)
        user_id = f"task_creator_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        db.collection("users").document(user_id).set({
            "user_id": user_id,
            "name": "Task Creator",
            "email": f"{user_id}@example.com"
        })
        
        try:
            payload = {
                "title": "API Created Task",
                "description": "This is a task created via API test endpoint",
                "status": "To Do",
                "priority": "High",
                "created_by_id": user_id
            }
            
            response = client.post("/api/tasks", json=payload)
            
            # Verify response
            assert response.status_code == 201
            data = response.get_json()
            # API returns task object directly, not wrapped
            task_id = data["task_id"]
            
            # Verify in Firebase
            doc = db.collection("tasks").document(task_id).get()
            assert doc.exists
            
            # Cleanup task
            db.collection("tasks").document(task_id).delete()
        finally:
            db.collection("users").document(user_id).delete()
    
    
    def test_get_tasks_list_via_api(self, client, db):
        """Test GET /api/tasks - list tasks."""
        # Create a test user (required for X-User-Id header)
        user_id = f"viewer_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        db.collection("users").document(user_id).set({
            "user_id": user_id,
            "name": "Viewer",
            "email": f"{user_id}@example.com"
        })
        
        # Create a test task
        task_id = f"list_task_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        task_data = {
            "task_id": task_id,
            "title": "List Test Task",
            "description": "Task for testing GET endpoint",
            "status": "To Do",
            "priority": "Medium"
        }
        db.collection("tasks").document(task_id).set(task_data)
        
        try:
            # GET /api/tasks returns list of tasks (requires X-User-Id header)
            response = client.get("/api/tasks", headers={"X-User-Id": user_id})
            assert response.status_code == 200
            data = response.get_json()
            # Response is array of tasks
            assert isinstance(data, list)
        finally:
            db.collection("tasks").document(task_id).delete()
            db.collection("users").document(user_id).delete()
    
    
    def test_update_task_via_api(self, client, db):
        """Test PUT /api/tasks/<task_id> - update task."""
        task_id = f"update_task_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        user_id = f"updater_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        
        # Create user (updates require authentication)
        db.collection("users").document(user_id).set({
            "user_id": user_id,
            "name": "Updater",
            "email": f"{user_id}@example.com",
            "role": "admin"  # Give admin role to bypass permission checks
        })
        
        # Create task with the user as creator to allow updates
        db.collection("tasks").document(task_id).set({
            "task_id": task_id,
            "title": "Original Title",
            "description": "Original description for update testing",
            "status": "To Do",
            "priority": "Low",
            "created_by": {"user_id": user_id}  # User owns this task
        })
        
        try:
            update_payload = {
                "title": "Updated Title via API",
                "status": "In Progress"
            }
            # Include user ID in headers
            response = client.put(f"/api/tasks/{task_id}", 
                                json=update_payload,
                                headers={"X-User-Id": user_id})
            
            assert response.status_code == 200
            
            # Verify update in Firebase
            doc = db.collection("tasks").document(task_id).get()
            data = doc.to_dict()
            assert data["title"] == "Updated Title via API"
            assert data["status"] == "In Progress"
        finally:
            db.collection("tasks").document(task_id).delete()
            db.collection("users").document(user_id).delete()
    
    
    def test_reassign_task_via_api(self, client, db):
        """Test PATCH /api/tasks/<task_id>/reassign - reassign task."""
        task_id = f"reassign_task_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        user1_id = f"user1_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        user2_id = f"user2_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        manager_id = f"manager_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        
        # Create users
        for uid in [user1_id, user2_id]:
            db.collection("users").document(uid).set({
                "user_id": uid,
                "name": f"User {uid}",
                "email": f"{uid}@example.com"
            })
        
        # Create manager user (to perform reassignment)
        db.collection("users").document(manager_id).set({
            "user_id": manager_id,
            "name": "Manager",
            "email": f"{manager_id}@example.com",
            "role": "manager"
        })
        
        # Create task
        db.collection("tasks").document(task_id).set({
            "task_id": task_id,
            "title": "Task to Reassign",
            "description": "This task will be reassigned via API",
            "status": "To Do",
            "assigned_to": {"user_id": user1_id}
        })
        
        try:
            # Reassign via API (requires X-User-Id header)
            response = client.patch(f"/api/tasks/{task_id}/reassign",
                                   json={"new_assigned_to_id": user2_id},  # Correct field name
                                   headers={"X-User-Id": manager_id})
            assert response.status_code == 200
            
            # Verify reassignment
            doc = db.collection("tasks").document(task_id).get()
            data = doc.to_dict()
            assert data["assigned_to"]["user_id"] == user2_id
        finally:
            db.collection("tasks").document(task_id).delete()
            db.collection("users").document(user1_id).delete()
            db.collection("users").document(user2_id).delete()
            db.collection("users").document(manager_id).delete()


class TestProjectAPIIntegration:
    """Test project API endpoints with real Firebase."""
    
    def test_create_project_via_api(self, client, db):
        """Test POST /api/projects - create project."""
        # Create owner user first (required by API)
        owner_id = f"proj_owner_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        db.collection("users").document(owner_id).set({
            "user_id": owner_id,
            "name": "Project Owner",
            "email": f"{owner_id}@example.com"
        })
        
        try:
            payload = {
                "name": "API Test Project",
                "description": "Project created via API",
                "owner_id": owner_id  # Required by API
            }
            
            response = client.post("/api/projects", json=payload)
            
            assert response.status_code == 201
            data = response.get_json()
            assert "project_id" in data
            project_id = data["project_id"]
            
            # Verify in Firebase
            doc = db.collection("projects").document(project_id).get()
            assert doc.exists
            
            # Cleanup
            db.collection("projects").document(project_id).delete()
        finally:
            db.collection("users").document(owner_id).delete()
    
    
    def test_get_project_via_api(self, client, db):
        """Test GET /api/projects/<project_id> - get project."""
        project_id = f"get_proj_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        project_data = {
            "project_id": project_id,
            "name": "Get Test Project",
            "description": "Project for testing GET"
        }
        db.collection("projects").document(project_id).set(project_data)
        
        try:
            response = client.get(f"/api/projects/{project_id}")
            assert response.status_code == 200
            data = response.get_json()
            assert data["project_id"] == project_id
        finally:
            db.collection("projects").document(project_id).delete()


class TestDashboardAPIIntegration:
    """Test dashboard API endpoints with real Firebase."""
    
    def test_get_user_dashboard_via_api(self, client, db):
        """Test GET /api/users/<user_id>/dashboard - get user dashboard."""
        user_id = f"dash_user_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        db.collection("users").document(user_id).set({
            "user_id": user_id,
            "name": "Dashboard User",
            "email": f"{user_id}@example.com"
        })
        
        try:
            response = client.get(f"/api/users/{user_id}/dashboard")
            assert response.status_code == 200
            data = response.get_json()
            # Dashboard returns multiple sections
            assert "recent_created_tasks" in data or "recent_assigned_tasks" in data
        finally:
            db.collection("users").document(user_id).delete()


class TestLabelAPIIntegration:
    """Test label API endpoints with real Firebase."""
    
    def test_create_label_via_api(self, client, db):
        """Test POST /api/labels - create label."""
        payload = {
            "name": "API Label",
            "color": "blue"
        }
        
        response = client.post("/api/labels", json=payload)
        
        try:
            assert response.status_code == 201
            data = response.get_json()
            assert "label_id" in data
            label_id = data["label_id"]
            
            # Verify in Firebase
            doc = db.collection("labels").document(label_id).get()
            assert doc.exists
            
            # Cleanup
            db.collection("labels").document(label_id).delete()
        except AssertionError:
            # Cleanup on failure
            if response.status_code == 201:
                label_id = response.get_json().get("label_id")
                if label_id:
                    db.collection("labels").document(label_id).delete()
            raise
    
    
    def test_assign_label_to_task_via_api(self, client, db):
        """Test POST /api/labels/assign - assign label to task."""
        # Create label and task
        label_id = f"label_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        task_id = f"task_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        
        db.collection("labels").document(label_id).set({
            "label_id": label_id,
            "name": "Test Label",
            "color": "red"
        })
        
        db.collection("tasks").document(task_id).set({
            "task_id": task_id,
            "title": "Test Task for Label",
            "description": "Task for testing label assignment",
            "labels": []
        })
        
        try:
            # Note: endpoint is /api/labels/assign (not /api/labels/<id>/assign)
            payload = {
                "label_id": label_id,
                "task_id": task_id
            }
            response = client.post("/api/labels/assign", json=payload)
            
            assert response.status_code == 200
            
            # Verify label was assigned
            task_doc = db.collection("tasks").document(task_id).get()
            task_data = task_doc.to_dict()
            assert label_id in task_data.get("labels", [])
        finally:
            db.collection("labels").document(label_id).delete()
            db.collection("tasks").document(task_id).delete()


class TestNotesAPIIntegration:
    """Test notes/comments API endpoints with real Firebase."""
    
    def test_add_note_via_api(self, client, db):
        """Test POST /api/notes - add note/comment."""
        user_id = f"note_author_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        task_id = f"note_task_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        
        db.collection("users").document(user_id).set({
            "user_id": user_id,
            "name": "Note Author",
            "email": f"{user_id}@example.com"
        })
        
        db.collection("tasks").document(task_id).set({
            "task_id": task_id,
            "title": "Task with Note",
            "description": "Task for testing notes"
        })
        
        try:
            payload = {
                "task_id": task_id,
                "author_id": user_id,
                "body": "This is a test comment via API"
            }
            
            response = client.post("/api/notes", json=payload)
            
            assert response.status_code == 201
            data = response.get_json()
            # API returns note object directly with note_id
            assert "note_id" in data
            note_id = data["note_id"]
            
            # Verify in Firebase
            doc = db.collection("notes").document(note_id).get()
            assert doc.exists
            
            # Cleanup
            db.collection("notes").document(note_id).delete()
        finally:
            db.collection("users").document(user_id).delete()
            db.collection("tasks").document(task_id).delete()
    
    
    def test_get_task_notes_via_api(self, client, db):
        """Test GET /api/notes/by-task/<task_id> - get notes for task."""
        task_id = f"notes_task_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        
        # Create notes in Firebase
        note_ids = []
        for i in range(2):
            note_id = f"note_{i}_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
            db.collection("notes").document(note_id).set({
                "note_id": note_id,
                "task_id": task_id,
                "author_id": "test_author",
                "body": f"Comment {i}",
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            note_ids.append(note_id)
        
        try:
            # Note: endpoint is /api/notes/by-task/<task_id>
            response = client.get(f"/api/notes/by-task/{task_id}")
            
            assert response.status_code == 200
            data = response.get_json()
            # API returns array of notes directly (not wrapped)
            assert isinstance(data, list)
            assert len(data) == 2
        finally:
            for note_id in note_ids:
                db.collection("notes").document(note_id).delete()
