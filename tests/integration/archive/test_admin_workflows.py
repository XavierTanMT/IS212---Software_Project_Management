"""Integration tests for admin workflows using real Firebase."""
import pytest
import json
from datetime import datetime, timezone, timedelta
from google.cloud.firestore_v1.base_query import FieldFilter


class TestAdminOperations:
    """Test admin-specific operations with real Firebase."""
    
    def test_create_admin_user(self, db, test_collection_prefix, cleanup_collections):
        """Test creating an admin user."""
        collection_name = f"{test_collection_prefix}_users"
        cleanup_collections.append(collection_name)
        
        admin_id = f"admin_{datetime.now(timezone.utc).timestamp()}"
        admin_data = {
            "user_id": admin_id,
            "email": f"{admin_id}@example.com",
            "name": "Admin User",
            "role": "Admin",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Create admin
        db.collection(collection_name).document(admin_id).set(admin_data)
        
        # Verify
        doc = db.collection(collection_name).document(admin_id).get()
        assert doc.exists
        assert doc.to_dict()["role"] == "Admin"
        
        # Cleanup
        db.collection(collection_name).document(admin_id).delete()
    
    
    def test_query_users_by_role(self, db, test_collection_prefix, cleanup_collections):
        """Test querying users filtered by role."""
        collection_name = f"{test_collection_prefix}_users"
        cleanup_collections.append(collection_name)
        
        # Create users with different roles
        admin_ids = []
        member_ids = []
        
        for i in range(2):
            admin_id = f"admin_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(collection_name).document(admin_id).set({
                "user_id": admin_id,
                "role": "Admin",
                "email": f"{admin_id}@example.com"
            })
            admin_ids.append(admin_id)
        
        for i in range(3):
            member_id = f"member_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(collection_name).document(member_id).set({
                "user_id": member_id,
                "role": "Member",
                "email": f"{member_id}@example.com"
            })
            member_ids.append(member_id)
        
        # Query admins
        admin_query = db.collection(collection_name).where(filter=FieldFilter("role", "==", "Admin"))
        admins = [doc.to_dict() for doc in admin_query.stream()]
        
        admin_user_ids = [a["user_id"] for a in admins]
        for admin_id in admin_ids:
            assert admin_id in admin_user_ids
        
        # Cleanup
        for user_id in admin_ids + member_ids:
            db.collection(collection_name).document(user_id).delete()


class TestAdminUserManagement:
    """Test admin user management capabilities."""
    
    def test_update_user_role(self, db, test_collection_prefix, cleanup_collections):
        """Test admin updating user role."""
        collection_name = f"{test_collection_prefix}_users"
        cleanup_collections.append(collection_name)
        
        user_id = f"user_{datetime.now(timezone.utc).timestamp()}"
        
        # Create user with Member role
        db.collection(collection_name).document(user_id).set({
            "user_id": user_id,
            "email": f"{user_id}@example.com",
            "name": "Test User",
            "role": "Member"
        })
        
        # Verify initial role
        doc = db.collection(collection_name).document(user_id).get()
        assert doc.to_dict()["role"] == "Member"
        
        # Update to Manager
        db.collection(collection_name).document(user_id).update({
            "role": "Manager",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify update
        doc = db.collection(collection_name).document(user_id).get()
        assert doc.to_dict()["role"] == "Manager"
        
        # Cleanup
        db.collection(collection_name).document(user_id).delete()
    
    
    def test_deactivate_user(self, db, test_collection_prefix, cleanup_collections):
        """Test admin deactivating a user account."""
        collection_name = f"{test_collection_prefix}_users"
        cleanup_collections.append(collection_name)
        
        user_id = f"user_{datetime.now(timezone.utc).timestamp()}"
        
        # Create active user
        db.collection(collection_name).document(user_id).set({
            "user_id": user_id,
            "email": f"{user_id}@example.com",
            "name": "Active User",
            "active": True
        })
        
        # Verify active
        doc = db.collection(collection_name).document(user_id).get()
        assert doc.to_dict()["active"] is True
        
        # Deactivate user
        db.collection(collection_name).document(user_id).update({
            "active": False,
            "deactivated_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify deactivation
        doc = db.collection(collection_name).document(user_id).get()
        user_data = doc.to_dict()
        assert user_data["active"] is False
        assert "deactivated_at" in user_data
        
        # Cleanup
        db.collection(collection_name).document(user_id).delete()
    
    
    def test_bulk_user_creation(self, db, test_collection_prefix, cleanup_collections):
        """Test creating multiple users in bulk."""
        collection_name = f"{test_collection_prefix}_users"
        cleanup_collections.append(collection_name)
        
        user_count = 5
        user_ids = []
        
        # Create multiple users
        for i in range(user_count):
            user_id = f"bulk_user_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(collection_name).document(user_id).set({
                "user_id": user_id,
                "email": f"user{i}@example.com",
                "name": f"User {i}",
                "role": "Member"
            })
            user_ids.append(user_id)
        
        # Verify all created
        for user_id in user_ids:
            doc = db.collection(collection_name).document(user_id).get()
            assert doc.exists
        
        # Cleanup
        for user_id in user_ids:
            db.collection(collection_name).document(user_id).delete()


class TestAdminProjectManagement:
    """Test admin project management capabilities."""
    
    def test_view_all_projects(self, db, test_collection_prefix, cleanup_collections):
        """Test admin viewing all projects in system."""
        projects_collection = f"{test_collection_prefix}_projects"
        cleanup_collections.append(projects_collection)
        
        project_count = 3
        project_ids = []
        
        # Create multiple projects
        for i in range(project_count):
            project_id = f"admin_project_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(projects_collection).document(project_id).set({
                "project_id": project_id,
                "name": f"Project {i}",
                "description": f"Admin test project {i}",
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            project_ids.append(project_id)
        
        # Query all projects
        all_projects = db.collection(projects_collection).stream()
        retrieved_ids = [doc.to_dict()["project_id"] for doc in all_projects]
        
        # Verify all projects are visible
        for project_id in project_ids:
            assert project_id in retrieved_ids
        
        # Cleanup
        for project_id in project_ids:
            db.collection(projects_collection).document(project_id).delete()
    
    
    def test_archive_project(self, db, test_collection_prefix, cleanup_collections):
        """Test admin archiving a project."""
        projects_collection = f"{test_collection_prefix}_projects"
        cleanup_collections.append(projects_collection)
        
        project_id = f"archive_project_{datetime.now(timezone.utc).timestamp()}"
        
        # Create project
        db.collection(projects_collection).document(project_id).set({
            "project_id": project_id,
            "name": "Project to Archive",
            "archived": False
        })
        
        # Verify not archived
        doc = db.collection(projects_collection).document(project_id).get()
        assert doc.to_dict()["archived"] is False
        
        # Archive project
        db.collection(projects_collection).document(project_id).update({
            "archived": True,
            "archived_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify archived
        doc = db.collection(projects_collection).document(project_id).get()
        project_data = doc.to_dict()
        assert project_data["archived"] is True
        assert "archived_at" in project_data
        
        # Cleanup
        db.collection(projects_collection).document(project_id).delete()


class TestAdminTaskMonitoring:
    """Test admin monitoring all tasks."""
    
    def test_view_all_tasks_across_projects(self, db, test_collection_prefix, cleanup_collections):
        """Test admin viewing all tasks regardless of project."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        # Create tasks for different projects
        task_data = [
            {"task_id": "admin_task_1", "project_id": "project_1", "title": "Task 1"},
            {"task_id": "admin_task_2", "project_id": "project_2", "title": "Task 2"},
            {"task_id": "admin_task_3", "project_id": "project_3", "title": "Task 3"},
        ]
        
        for task in task_data:
            task["status"] = "To Do"
            task["created_at"] = datetime.now(timezone.utc).isoformat()
            db.collection(tasks_collection).document(task["task_id"]).set(task)
        
        # Query all tasks
        all_tasks = db.collection(tasks_collection).stream()
        retrieved_ids = [doc.to_dict()["task_id"] for doc in all_tasks]
        
        # Verify all tasks visible
        for task in task_data:
            assert task["task_id"] in retrieved_ids
        
        # Cleanup
        for task in task_data:
            db.collection(tasks_collection).document(task["task_id"]).delete()
    
    
    def test_query_overdue_tasks_system_wide(self, db, test_collection_prefix, cleanup_collections):
        """Test admin querying all overdue tasks in system."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        now = datetime.now(timezone.utc)
        
        # Create overdue and current tasks
        overdue_id = f"overdue_{now.timestamp()}"
        current_id = f"current_{now.timestamp()}"
        
        db.collection(tasks_collection).document(overdue_id).set({
            "task_id": overdue_id,
            "title": "Overdue Task",
            "status": "To Do",
            "due_date": (now - timedelta(days=5)).isoformat()
        })
        
        db.collection(tasks_collection).document(current_id).set({
            "task_id": current_id,
            "title": "Current Task",
            "status": "To Do",
            "due_date": (now + timedelta(days=5)).isoformat()
        })
        
        # Query and filter overdue tasks
        all_tasks = db.collection(tasks_collection).stream()
        overdue_tasks = []
        
        for doc in all_tasks:
            task = doc.to_dict()
            if task.get("due_date") and task.get("status") != "Done":
                due_dt = datetime.fromisoformat(task["due_date"].replace('Z', '+00:00'))
                if due_dt < now:
                    overdue_tasks.append(task)
        
        # Verify overdue detection
        overdue_ids = [t["task_id"] for t in overdue_tasks]
        assert overdue_id in overdue_ids
        assert current_id not in overdue_ids
        
        # Cleanup
        db.collection(tasks_collection).document(overdue_id).delete()
        db.collection(tasks_collection).document(current_id).delete()


class TestAdminAnalytics:
    """Test admin analytics and reporting."""
    
    def test_count_users_by_role(self, db, test_collection_prefix, cleanup_collections):
        """Test counting users grouped by role."""
        users_collection = f"{test_collection_prefix}_users"
        cleanup_collections.append(users_collection)
        
        roles = ["Admin", "Manager", "Member", "Member", "Member"]
        user_ids = []
        
        for i, role in enumerate(roles):
            user_id = f"analytics_user_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(users_collection).document(user_id).set({
                "user_id": user_id,
                "email": f"user{i}@example.com",
                "role": role
            })
            user_ids.append(user_id)
        
        # Count by role
        all_users = db.collection(users_collection).stream()
        role_counts = {}
        
        for doc in all_users:
            user = doc.to_dict()
            role = user.get("role", "Unknown")
            role_counts[role] = role_counts.get(role, 0) + 1
        
        # Verify counts
        assert role_counts.get("Admin", 0) >= 1
        assert role_counts.get("Manager", 0) >= 1
        assert role_counts.get("Member", 0) >= 3
        
        # Cleanup
        for user_id in user_ids:
            db.collection(users_collection).document(user_id).delete()
    
    
    def test_count_tasks_by_status(self, db, test_collection_prefix, cleanup_collections):
        """Test counting tasks grouped by status."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        statuses = ["To Do", "To Do", "In Progress", "In Progress", "In Progress", "Done"]
        task_ids = []
        
        for i, status in enumerate(statuses):
            task_id = f"analytics_task_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(tasks_collection).document(task_id).set({
                "task_id": task_id,
                "title": f"Task {i}",
                "status": status
            })
            task_ids.append(task_id)
        
        # Count by status
        all_tasks = db.collection(tasks_collection).stream()
        status_counts = {}
        
        for doc in all_tasks:
            task = doc.to_dict()
            status = task.get("status", "Unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Verify counts
        assert status_counts.get("To Do", 0) >= 2
        assert status_counts.get("In Progress", 0) >= 3
        assert status_counts.get("Done", 0) >= 1
        
        # Cleanup
        for task_id in task_ids:
            db.collection(tasks_collection).document(task_id).delete()


class TestAdminPermissions:
    """Test admin permission scenarios."""
    
    def test_admin_role_hierarchy(self, db, test_collection_prefix, cleanup_collections):
        """Test that admin role has higher privileges than other roles."""
        users_collection = f"{test_collection_prefix}_users"
        cleanup_collections.append(users_collection)
        
        # Create users with different roles
        roles = ["Admin", "Manager", "Member", "Viewer"]
        role_hierarchy = {"Admin": 4, "Manager": 3, "Member": 2, "Viewer": 1}
        user_ids = []
        
        for role in roles:
            user_id = f"hierarchy_{role.lower()}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(users_collection).document(user_id).set({
                "user_id": user_id,
                "email": f"{user_id}@example.com",
                "role": role,
                "permission_level": role_hierarchy[role]
            })
            user_ids.append(user_id)
        
        # Query admin
        admin_query = db.collection(users_collection).where(
            filter=FieldFilter("role", "==", "Admin")
        )
        admins = [doc.to_dict() for doc in admin_query.stream()]
        
        # Verify admin has highest permission level
        assert len(admins) >= 1
        for admin in admins:
            assert admin["permission_level"] == 4
        
        # Cleanup
        for user_id in user_ids:
            db.collection(users_collection).document(user_id).delete()
    
    
    def test_admin_can_modify_any_project(self, db, test_collection_prefix, cleanup_collections):
        """Test that admin can modify projects created by other users."""
        projects_collection = f"{test_collection_prefix}_projects"
        cleanup_collections.append(projects_collection)
        
        # Create project owned by regular user
        project_id = f"user_project_{datetime.now(timezone.utc).timestamp()}"
        db.collection(projects_collection).document(project_id).set({
            "project_id": project_id,
            "name": "User Project",
            "owner": "regular_user_123",
            "description": "Original description"
        })
        
        # Admin modifies project
        db.collection(projects_collection).document(project_id).update({
            "description": "Modified by admin",
            "modified_by": "admin_user_456",
            "modified_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify modification
        doc = db.collection(projects_collection).document(project_id).get()
        project_data = doc.to_dict()
        assert project_data["description"] == "Modified by admin"
        assert project_data["modified_by"] == "admin_user_456"
        
        # Cleanup
        db.collection(projects_collection).document(project_id).delete()
