"""Integration tests for project workflows using real Firebase."""
import pytest
import json
from datetime import datetime, timezone, timedelta
from google.cloud.firestore_v1.base_query import FieldFilter


class TestProjectCreationIntegration:
    """Test real project creation operations with Firebase."""
    
    def test_create_project_in_firestore(self, db, test_collection_prefix, cleanup_collections):
        """Test creating a project directly in Firestore."""
        collection_name = f"{test_collection_prefix}_projects"
        cleanup_collections.append(collection_name)
        
        project_id = f"integration_project_{datetime.now(timezone.utc).timestamp()}"
        project_data = {
            "project_id": project_id,
            "name": "Integration Test Project",
            "description": "A project for integration testing",
            "owner_id": "test_manager_123",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "Active"
        }
        
        # Create project in Firestore
        db.collection(collection_name).document(project_id).set(project_data)
        
        # Verify project was created
        doc = db.collection(collection_name).document(project_id).get()
        assert doc.exists
        assert doc.to_dict()["name"] == project_data["name"]
        assert doc.to_dict()["description"] == project_data["description"]
        assert doc.to_dict()["owner_id"] == project_data["owner_id"]
        
        # Cleanup
        db.collection(collection_name).document(project_id).delete()
    
    
    def test_update_project_in_firestore(self, db, test_project):
        """Test updating a project in Firestore."""
        collection = test_project["collection"]
        project_id = test_project["project_id"]
        
        # Update project
        db.collection(collection).document(project_id).update({
            "name": "Updated Project Name",
            "status": "Completed",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify update
        doc = db.collection(collection).document(project_id).get()
        assert doc.exists
        assert doc.to_dict()["name"] == "Updated Project Name"
        assert doc.to_dict()["status"] == "Completed"
        assert "updated_at" in doc.to_dict()


class TestProjectTaskRelationship:
    """Test project-task relationships with real Firebase."""
    
    def test_query_tasks_by_project(self, db, test_collection_prefix, cleanup_collections):
        """Test querying tasks belonging to a project."""
        projects_collection = f"{test_collection_prefix}_projects"
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.extend([projects_collection, tasks_collection])
        
        # Create project
        project_id = f"project_{datetime.now(timezone.utc).timestamp()}"
        db.collection(projects_collection).document(project_id).set({
            "project_id": project_id,
            "name": "Test Project"
        })
        
        # Create tasks for this project
        task_ids = []
        for i in range(3):
            task_id = f"task_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(tasks_collection).document(task_id).set({
                "task_id": task_id,
                "project_id": project_id,
                "title": f"Task {i}",
                "status": "In Progress"
            })
            task_ids.append(task_id)
        
        # Query tasks by project_id
        query = db.collection(tasks_collection).where(filter=FieldFilter("project_id", "==", project_id))
        tasks = [doc.to_dict() for doc in query.stream()]
        
        assert len(tasks) == 3
        for task in tasks:
            assert task["project_id"] == project_id
            assert task["task_id"] in task_ids
        
        # Cleanup
        db.collection(projects_collection).document(project_id).delete()
        for task_id in task_ids:
            db.collection(tasks_collection).document(task_id).delete()


class TestProjectMembership:
    """Test project membership relationships."""
    
    def test_add_members_to_project(self, db, test_collection_prefix, cleanup_collections):
        """Test adding members to a project via memberships collection."""
        projects_collection = f"{test_collection_prefix}_projects"
        memberships_collection = f"{test_collection_prefix}_memberships"
        cleanup_collections.extend([projects_collection, memberships_collection])
        
        # Create project
        project_id = f"project_{datetime.now(timezone.utc).timestamp()}"
        db.collection(projects_collection).document(project_id).set({
            "project_id": project_id,
            "name": "Team Project"
        })
        
        # Add memberships
        member_ids = ["user1", "user2", "user3"]
        membership_docs = []
        for user_id in member_ids:
            membership_id = f"{project_id}_{user_id}"
            db.collection(memberships_collection).document(membership_id).set({
                "project_id": project_id,
                "user_id": user_id,
                "role": "Member"
            })
            membership_docs.append(membership_id)
        
        # Query memberships for project
        query = db.collection(memberships_collection).where(filter=FieldFilter("project_id", "==", project_id))
        memberships = [doc.to_dict() for doc in query.stream()]
        
        assert len(memberships) == 3
        retrieved_user_ids = [m["user_id"] for m in memberships]
        for user_id in member_ids:
            assert user_id in retrieved_user_ids
        
        # Cleanup
        db.collection(projects_collection).document(project_id).delete()
        for membership_id in membership_docs:
            db.collection(memberships_collection).document(membership_id).delete()
    
    
    def test_query_user_projects(self, db, test_collection_prefix, cleanup_collections):
        """Test querying all projects a user is a member of."""
        memberships_collection = f"{test_collection_prefix}_memberships"
        cleanup_collections.append(memberships_collection)
        
        user_id = "test_user_123"
        project_ids = []
        membership_docs = []
        
        # Create memberships for user across multiple projects
        for i in range(3):
            project_id = f"project_{i}_{datetime.now(timezone.utc).timestamp()}"
            membership_id = f"{project_id}_{user_id}"
            db.collection(memberships_collection).document(membership_id).set({
                "project_id": project_id,
                "user_id": user_id,
                "role": "Member"
            })
            project_ids.append(project_id)
            membership_docs.append(membership_id)
        
        # Query all projects for this user
        query = db.collection(memberships_collection).where(filter=FieldFilter("user_id", "==", user_id))
        memberships = [doc.to_dict() for doc in query.stream()]
        
        assert len(memberships) == 3
        retrieved_project_ids = [m["project_id"] for m in memberships]
        for project_id in project_ids:
            assert project_id in retrieved_project_ids
        
        # Cleanup
        for membership_id in membership_docs:
            db.collection(memberships_collection).document(membership_id).delete()

