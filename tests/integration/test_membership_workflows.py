"""Integration tests for membership workflows using real Firebase."""
import pytest
from datetime import datetime, timezone
from google.cloud.firestore_v1.base_query import FieldFilter


class TestMembershipOperations:
    """Test basic membership CRUD operations with real Firebase."""
    
    def test_add_member_to_project(self, db, test_collection_prefix, cleanup_collections):
        """Test adding a member to a project."""
        projects_collection = f"{test_collection_prefix}_projects"
        users_collection = f"{test_collection_prefix}_users"
        memberships_collection = f"{test_collection_prefix}_memberships"
        cleanup_collections.extend([projects_collection, users_collection, memberships_collection])
        
        # Create project
        project_id = f"project_{datetime.now(timezone.utc).timestamp()}"
        db.collection(projects_collection).document(project_id).set({
            "project_id": project_id,
            "name": "Test Project",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Create user
        user_id = f"user_{datetime.now(timezone.utc).timestamp()}"
        db.collection(users_collection).document(user_id).set({
            "user_id": user_id,
            "name": "Test User",
            "email": "test@example.com",
            "role": "Member"
        })
        
        # Add membership
        membership_id = f"{project_id}_{user_id}"
        db.collection(memberships_collection).document(membership_id).set({
            "project_id": project_id,
            "user_id": user_id,
            "role": "Member",
            "joined_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify membership exists
        doc = db.collection(memberships_collection).document(membership_id).get()
        assert doc.exists
        
        membership_data = doc.to_dict()
        assert membership_data["project_id"] == project_id
        assert membership_data["user_id"] == user_id
        assert membership_data["role"] == "Member"
        
        # Cleanup
        db.collection(projects_collection).document(project_id).delete()
        db.collection(users_collection).document(user_id).delete()
        db.collection(memberships_collection).document(membership_id).delete()
    
    
    def test_remove_member_from_project(self, db, test_collection_prefix, cleanup_collections):
        """Test removing a member from a project."""
        memberships_collection = f"{test_collection_prefix}_memberships"
        cleanup_collections.append(memberships_collection)
        
        project_id = f"project_{datetime.now(timezone.utc).timestamp()}"
        user_id = f"user_{datetime.now(timezone.utc).timestamp()}"
        membership_id = f"{project_id}_{user_id}"
        
        # Create membership
        db.collection(memberships_collection).document(membership_id).set({
            "project_id": project_id,
            "user_id": user_id,
            "role": "Member",
            "joined_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify creation
        doc = db.collection(memberships_collection).document(membership_id).get()
        assert doc.exists
        
        # Remove membership
        db.collection(memberships_collection).document(membership_id).delete()
        
        # Verify removal
        doc = db.collection(memberships_collection).document(membership_id).get()
        assert not doc.exists
    
    
    def test_update_member_role(self, db, test_collection_prefix, cleanup_collections):
        """Test updating a member's role in a project."""
        memberships_collection = f"{test_collection_prefix}_memberships"
        cleanup_collections.append(memberships_collection)
        
        project_id = f"project_{datetime.now(timezone.utc).timestamp()}"
        user_id = f"user_{datetime.now(timezone.utc).timestamp()}"
        membership_id = f"{project_id}_{user_id}"
        
        # Create membership with Member role
        db.collection(memberships_collection).document(membership_id).set({
            "project_id": project_id,
            "user_id": user_id,
            "role": "Member",
            "joined_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Update role to Manager
        db.collection(memberships_collection).document(membership_id).update({
            "role": "Manager",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify update
        doc = db.collection(memberships_collection).document(membership_id).get()
        membership_data = doc.to_dict()
        
        assert membership_data["role"] == "Manager"
        assert "updated_at" in membership_data
        
        # Cleanup
        db.collection(memberships_collection).document(membership_id).delete()


class TestMembershipQueries:
    """Test querying memberships with various filters."""
    
    def test_list_all_project_members(self, db, test_collection_prefix, cleanup_collections):
        """Test listing all members of a specific project."""
        memberships_collection = f"{test_collection_prefix}_memberships"
        cleanup_collections.append(memberships_collection)
        
        project_id = f"project_{datetime.now(timezone.utc).timestamp()}"
        membership_ids = []
        
        # Add multiple members to project
        for i in range(5):
            user_id = f"user_{i}_{datetime.now(timezone.utc).timestamp()}"
            membership_id = f"{project_id}_{user_id}"
            db.collection(memberships_collection).document(membership_id).set({
                "project_id": project_id,
                "user_id": user_id,
                "role": "Member" if i > 0 else "Manager",  # First user is Manager
                "joined_at": datetime.now(timezone.utc).isoformat()
            })
            membership_ids.append(membership_id)
        
        # Query all members of this project
        query = db.collection(memberships_collection).where(filter=FieldFilter("project_id", "==", project_id))
        members = [doc.to_dict() for doc in query.stream()]
        
        assert len(members) >= 5
        
        # Verify one manager and multiple members
        roles = [m["role"] for m in members]
        assert "Manager" in roles
        assert roles.count("Member") >= 4
        
        # Cleanup
        for membership_id in membership_ids:
            db.collection(memberships_collection).document(membership_id).delete()
    
    
    def test_list_user_projects(self, db, test_collection_prefix, cleanup_collections):
        """Test listing all projects a user is a member of."""
        memberships_collection = f"{test_collection_prefix}_memberships"
        cleanup_collections.append(memberships_collection)
        
        user_id = f"user_{datetime.now(timezone.utc).timestamp()}"
        membership_ids = []
        project_ids = []
        
        # Add user to multiple projects
        for i in range(4):
            project_id = f"project_{i}_{datetime.now(timezone.utc).timestamp()}"
            membership_id = f"{project_id}_{user_id}"
            db.collection(memberships_collection).document(membership_id).set({
                "project_id": project_id,
                "user_id": user_id,
                "role": "Member",
                "joined_at": datetime.now(timezone.utc).isoformat()
            })
            membership_ids.append(membership_id)
            project_ids.append(project_id)
        
        # Query all projects for this user
        query = db.collection(memberships_collection).where(filter=FieldFilter("user_id", "==", user_id))
        user_memberships = [doc.to_dict() for doc in query.stream()]
        
        assert len(user_memberships) >= 4
        
        # Verify all expected projects are present
        retrieved_project_ids = [m["project_id"] for m in user_memberships]
        for project_id in project_ids:
            assert project_id in retrieved_project_ids
        
        # Cleanup
        for membership_id in membership_ids:
            db.collection(memberships_collection).document(membership_id).delete()
    
    
    def test_query_members_by_role(self, db, test_collection_prefix, cleanup_collections):
        """Test querying members by their role."""
        memberships_collection = f"{test_collection_prefix}_memberships"
        cleanup_collections.append(memberships_collection)
        
        project_id = f"project_{datetime.now(timezone.utc).timestamp()}"
        membership_ids = []
        
        # Create members with different roles
        roles_to_create = ["Manager", "Manager", "Member", "Member", "Member", "Viewer"]
        
        for i, role in enumerate(roles_to_create):
            user_id = f"user_{i}_{datetime.now(timezone.utc).timestamp()}"
            membership_id = f"{project_id}_{user_id}"
            db.collection(memberships_collection).document(membership_id).set({
                "project_id": project_id,
                "user_id": user_id,
                "role": role,
                "joined_at": datetime.now(timezone.utc).isoformat()
            })
            membership_ids.append(membership_id)
        
        # Query for managers only
        query = (db.collection(memberships_collection)
                .where(filter=FieldFilter("project_id", "==", project_id))
                .where(filter=FieldFilter("role", "==", "Manager")))
        managers = [doc.to_dict() for doc in query.stream()]
        
        assert len(managers) >= 2
        for manager in managers:
            assert manager["role"] == "Manager"
        
        # Cleanup
        for membership_id in membership_ids:
            db.collection(memberships_collection).document(membership_id).delete()


class TestMembershipRoles:
    """Test different membership role scenarios."""
    
    def test_manager_permissions(self, db, test_collection_prefix, cleanup_collections):
        """Test manager role membership."""
        memberships_collection = f"{test_collection_prefix}_memberships"
        cleanup_collections.append(memberships_collection)
        
        project_id = f"project_{datetime.now(timezone.utc).timestamp()}"
        user_id = f"user_{datetime.now(timezone.utc).timestamp()}"
        membership_id = f"{project_id}_{user_id}"
        
        # Create manager membership
        db.collection(memberships_collection).document(membership_id).set({
            "project_id": project_id,
            "user_id": user_id,
            "role": "Manager",
            "permissions": ["read", "write", "delete", "manage_members"],
            "joined_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify manager has extended permissions
        doc = db.collection(memberships_collection).document(membership_id).get()
        membership_data = doc.to_dict()
        
        assert membership_data["role"] == "Manager"
        assert "manage_members" in membership_data["permissions"]
        
        # Cleanup
        db.collection(memberships_collection).document(membership_id).delete()
    
    
    def test_viewer_permissions(self, db, test_collection_prefix, cleanup_collections):
        """Test viewer role membership with limited permissions."""
        memberships_collection = f"{test_collection_prefix}_memberships"
        cleanup_collections.append(memberships_collection)
        
        project_id = f"project_{datetime.now(timezone.utc).timestamp()}"
        user_id = f"user_{datetime.now(timezone.utc).timestamp()}"
        membership_id = f"{project_id}_{user_id}"
        
        # Create viewer membership
        db.collection(memberships_collection).document(membership_id).set({
            "project_id": project_id,
            "user_id": user_id,
            "role": "Viewer",
            "permissions": ["read"],
            "joined_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify viewer has limited permissions
        doc = db.collection(memberships_collection).document(membership_id).get()
        membership_data = doc.to_dict()
        
        assert membership_data["role"] == "Viewer"
        assert membership_data["permissions"] == ["read"]
        
        # Cleanup
        db.collection(memberships_collection).document(membership_id).delete()


class TestMembershipEdgeCases:
    """Test edge cases and complex membership scenarios."""
    
    def test_user_membership_in_multiple_projects(self, db, test_collection_prefix, cleanup_collections):
        """Test a single user being a member of multiple projects with different roles."""
        memberships_collection = f"{test_collection_prefix}_memberships"
        cleanup_collections.append(memberships_collection)
        
        user_id = f"user_{datetime.now(timezone.utc).timestamp()}"
        membership_ids = []
        
        # Add user to projects with different roles
        roles = ["Manager", "Member", "Viewer", "Member"]
        for i, role in enumerate(roles):
            project_id = f"project_{i}_{datetime.now(timezone.utc).timestamp()}"
            membership_id = f"{project_id}_{user_id}"
            db.collection(memberships_collection).document(membership_id).set({
                "project_id": project_id,
                "user_id": user_id,
                "role": role,
                "joined_at": datetime.now(timezone.utc).isoformat()
            })
            membership_ids.append(membership_id)
        
        # Query user's memberships
        query = db.collection(memberships_collection).where(filter=FieldFilter("user_id", "==", user_id))
        memberships = [doc.to_dict() for doc in query.stream()]
        
        assert len(memberships) >= 4
        
        # Verify different roles
        member_roles = [m["role"] for m in memberships]
        assert "Manager" in member_roles
        assert "Viewer" in member_roles
        assert member_roles.count("Member") >= 2
        
        # Cleanup
        for membership_id in membership_ids:
            db.collection(memberships_collection).document(membership_id).delete()
    
    
    def test_prevent_duplicate_membership(self, db, test_collection_prefix, cleanup_collections):
        """Test that duplicate memberships use the same document ID."""
        memberships_collection = f"{test_collection_prefix}_memberships"
        cleanup_collections.append(memberships_collection)
        
        project_id = f"project_{datetime.now(timezone.utc).timestamp()}"
        user_id = f"user_{datetime.now(timezone.utc).timestamp()}"
        membership_id = f"{project_id}_{user_id}"
        
        # Create first membership
        db.collection(memberships_collection).document(membership_id).set({
            "project_id": project_id,
            "user_id": user_id,
            "role": "Member",
            "joined_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Attempt to create duplicate (should overwrite)
        db.collection(memberships_collection).document(membership_id).set({
            "project_id": project_id,
            "user_id": user_id,
            "role": "Manager",  # Different role
            "joined_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Query memberships - should only have one
        query = (db.collection(memberships_collection)
                .where(filter=FieldFilter("project_id", "==", project_id))
                .where(filter=FieldFilter("user_id", "==", user_id)))
        memberships = [doc.to_dict() for doc in query.stream()]
        
        assert len(memberships) == 1
        assert memberships[0]["role"] == "Manager"  # Should be updated
        
        # Cleanup
        db.collection(memberships_collection).document(membership_id).delete()
    
    
    def test_membership_count_per_project(self, db, test_collection_prefix, cleanup_collections):
        """Test counting the number of members in a project."""
        memberships_collection = f"{test_collection_prefix}_memberships"
        cleanup_collections.append(memberships_collection)
        
        project_id = f"project_{datetime.now(timezone.utc).timestamp()}"
        expected_member_count = 8
        membership_ids = []
        
        # Add specific number of members
        for i in range(expected_member_count):
            user_id = f"user_{i}_{datetime.now(timezone.utc).timestamp()}"
            membership_id = f"{project_id}_{user_id}"
            db.collection(memberships_collection).document(membership_id).set({
                "project_id": project_id,
                "user_id": user_id,
                "role": "Member",
                "joined_at": datetime.now(timezone.utc).isoformat()
            })
            membership_ids.append(membership_id)
        
        # Count members
        query = db.collection(memberships_collection).where(filter=FieldFilter("project_id", "==", project_id))
        member_count = len([doc for doc in query.stream()])
        
        assert member_count == expected_member_count
        
        # Cleanup
        for membership_id in membership_ids:
            db.collection(memberships_collection).document(membership_id).delete()
    
    
    def test_empty_project_no_members(self, db, test_collection_prefix, cleanup_collections):
        """Test that a project with no members returns empty list."""
        memberships_collection = f"{test_collection_prefix}_memberships"
        cleanup_collections.append(memberships_collection)
        
        project_id = f"empty_project_{datetime.now(timezone.utc).timestamp()}"
        
        # Query members for project with none
        query = db.collection(memberships_collection).where(filter=FieldFilter("project_id", "==", project_id))
        members = [doc.to_dict() for doc in query.stream()]
        
        assert len(members) == 0
