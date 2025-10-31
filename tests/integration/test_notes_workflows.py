"""Integration tests for notes/comments workflows using real Firebase."""
import pytest
from datetime import datetime, timezone, timedelta
from google.cloud.firestore_v1.base_query import FieldFilter


class TestNoteOperations:
    """Test basic note/comment CRUD operations with real Firebase."""
    
    def test_add_comment_to_task(self, db, test_collection_prefix, cleanup_collections):
        """Test adding a comment/note to a task."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        notes_collection = f"{test_collection_prefix}_notes"
        cleanup_collections.extend([tasks_collection, notes_collection])
        
        # Create task
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}"
        db.collection(tasks_collection).document(task_id).set({
            "task_id": task_id,
            "title": "Task for Comments",
            "status": "In Progress"
        })
        
        # Add comment
        note_id = f"note_{datetime.now(timezone.utc).timestamp()}"
        note_data = {
            "note_id": note_id,
            "task_id": task_id,
            "content": "This is a test comment",
            "created_by": {
                "user_id": "user123",
                "name": "Test User",
                "email": "test@example.com"
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        db.collection(notes_collection).document(note_id).set(note_data)
        
        # Verify comment exists
        doc = db.collection(notes_collection).document(note_id).get()
        assert doc.exists
        
        retrieved_note = doc.to_dict()
        assert retrieved_note["content"] == "This is a test comment"
        assert retrieved_note["task_id"] == task_id
        
        # Cleanup
        db.collection(tasks_collection).document(task_id).delete()
        db.collection(notes_collection).document(note_id).delete()
    
    
    def test_list_comments_for_task(self, db, test_collection_prefix, cleanup_collections):
        """Test listing all comments for a specific task."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        notes_collection = f"{test_collection_prefix}_notes"
        cleanup_collections.extend([tasks_collection, notes_collection])
        
        # Create task
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}"
        db.collection(tasks_collection).document(task_id).set({
            "task_id": task_id,
            "title": "Task with Multiple Comments",
            "status": "To Do"
        })
        
        # Add multiple comments
        note_ids = []
        for i in range(3):
            note_id = f"note_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(notes_collection).document(note_id).set({
                "note_id": note_id,
                "task_id": task_id,
                "content": f"Comment {i}",
                "created_by": {
                    "user_id": f"user{i}",
                    "name": f"User {i}"
                },
                "created_at": (datetime.now(timezone.utc) + timedelta(minutes=i)).isoformat()
            })
            note_ids.append(note_id)
        
        # Query comments for this task
        query = db.collection(notes_collection).where(filter=FieldFilter("task_id", "==", task_id))
        comments = [doc.to_dict() for doc in query.stream()]
        
        assert len(comments) >= 3
        comment_contents = [c["content"] for c in comments]
        assert "Comment 0" in comment_contents
        assert "Comment 1" in comment_contents
        assert "Comment 2" in comment_contents
        
        # Cleanup
        db.collection(tasks_collection).document(task_id).delete()
        for note_id in note_ids:
            db.collection(notes_collection).document(note_id).delete()
    
    
    def test_update_comment(self, db, test_collection_prefix, cleanup_collections):
        """Test updating a comment's content."""
        notes_collection = f"{test_collection_prefix}_notes"
        cleanup_collections.append(notes_collection)
        
        # Create comment
        note_id = f"note_{datetime.now(timezone.utc).timestamp()}"
        original_content = "Original comment"
        db.collection(notes_collection).document(note_id).set({
            "note_id": note_id,
            "task_id": "task123",
            "content": original_content,
            "created_by": {"user_id": "user1"},
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Update comment
        updated_content = "Updated comment content"
        db.collection(notes_collection).document(note_id).update({
            "content": updated_content,
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify update
        doc = db.collection(notes_collection).document(note_id).get()
        note_data = doc.to_dict()
        
        assert note_data["content"] == updated_content
        assert "updated_at" in note_data
        
        # Cleanup
        db.collection(notes_collection).document(note_id).delete()
    
    
    def test_delete_comment(self, db, test_collection_prefix, cleanup_collections):
        """Test deleting a comment."""
        notes_collection = f"{test_collection_prefix}_notes"
        cleanup_collections.append(notes_collection)
        
        # Create comment
        note_id = f"note_{datetime.now(timezone.utc).timestamp()}"
        db.collection(notes_collection).document(note_id).set({
            "note_id": note_id,
            "task_id": "task456",
            "content": "Comment to be deleted",
            "created_by": {"user_id": "user1"},
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify creation
        doc = db.collection(notes_collection).document(note_id).get()
        assert doc.exists
        
        # Delete comment
        db.collection(notes_collection).document(note_id).delete()
        
        # Verify deletion
        doc = db.collection(notes_collection).document(note_id).get()
        assert not doc.exists


class TestCommentThreading:
    """Test comment threading and conversation features."""
    
    def test_chronological_comment_order(self, db, test_collection_prefix, cleanup_collections):
        """Test that comments can be retrieved in chronological order."""
        notes_collection = f"{test_collection_prefix}_notes"
        cleanup_collections.append(notes_collection)
        
        task_id = f"task_thread_{datetime.now(timezone.utc).timestamp()}"
        note_ids = []
        timestamps = []
        
        # Create comments with different timestamps
        for i in range(5):
            note_id = f"note_{i}_{datetime.now(timezone.utc).timestamp()}"
            timestamp = datetime.now(timezone.utc) + timedelta(seconds=i)
            db.collection(notes_collection).document(note_id).set({
                "note_id": note_id,
                "task_id": task_id,
                "content": f"Comment at time {i}",
                "created_by": {"user_id": "user1"},
                "created_at": timestamp.isoformat()
            })
            note_ids.append(note_id)
            timestamps.append(timestamp.isoformat())
        
        # Query comments (without order_by to avoid composite index requirement)
        query = db.collection(notes_collection).where(filter=FieldFilter("task_id", "==", task_id))
        comments = [doc.to_dict() for doc in query.stream()]
        
        # Sort client-side by created_at
        comments_sorted = sorted(comments, key=lambda x: x["created_at"])
        
        # Verify chronological order and all comments present
        assert len(comments_sorted) >= 5
        for i in range(len(comments_sorted) - 1):
            assert comments_sorted[i]["created_at"] <= comments_sorted[i + 1]["created_at"]
        
        # Verify timestamps are in expected order
        retrieved_timestamps = [c["created_at"] for c in comments_sorted]
        for expected_ts in timestamps:
            assert expected_ts in retrieved_timestamps
        
        # Cleanup
        for note_id in note_ids:
            db.collection(notes_collection).document(note_id).delete()
    
    
    def test_multiple_users_commenting(self, db, test_collection_prefix, cleanup_collections):
        """Test multiple users adding comments to the same task."""
        notes_collection = f"{test_collection_prefix}_notes"
        cleanup_collections.append(notes_collection)
        
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}"
        users = [
            {"user_id": "user1", "name": "Alice"},
            {"user_id": "user2", "name": "Bob"},
            {"user_id": "user3", "name": "Charlie"}
        ]
        
        note_ids = []
        for user in users:
            note_id = f"note_{user['user_id']}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(notes_collection).document(note_id).set({
                "note_id": note_id,
                "task_id": task_id,
                "content": f"Comment from {user['name']}",
                "created_by": user,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            note_ids.append(note_id)
        
        # Query comments
        query = db.collection(notes_collection).where(filter=FieldFilter("task_id", "==", task_id))
        comments = [doc.to_dict() for doc in query.stream()]
        
        assert len(comments) >= 3
        comment_authors = [c["created_by"]["name"] for c in comments]
        assert "Alice" in comment_authors
        assert "Bob" in comment_authors
        assert "Charlie" in comment_authors
        
        # Cleanup
        for note_id in note_ids:
            db.collection(notes_collection).document(note_id).delete()


class TestCommentEdgeCases:
    """Test edge cases and complex comment scenarios."""
    
    def test_long_comment_content(self, db, test_collection_prefix, cleanup_collections):
        """Test adding a very long comment."""
        notes_collection = f"{test_collection_prefix}_notes"
        cleanup_collections.append(notes_collection)
        
        note_id = f"note_{datetime.now(timezone.utc).timestamp()}"
        long_content = "A" * 5000  # 5000 character comment
        
        db.collection(notes_collection).document(note_id).set({
            "note_id": note_id,
            "task_id": "task123",
            "content": long_content,
            "created_by": {"user_id": "user1"},
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify storage and retrieval
        doc = db.collection(notes_collection).document(note_id).get()
        assert doc.exists
        assert len(doc.to_dict()["content"]) == 5000
        
        # Cleanup
        db.collection(notes_collection).document(note_id).delete()
    
    
    def test_comment_with_special_characters(self, db, test_collection_prefix, cleanup_collections):
        """Test comment with special characters and emoji."""
        notes_collection = f"{test_collection_prefix}_notes"
        cleanup_collections.append(notes_collection)
        
        note_id = f"note_{datetime.now(timezone.utc).timestamp()}"
        special_content = "This comment has special chars: @#$%^&*() and emoji 🎉🚀✨"
        
        db.collection(notes_collection).document(note_id).set({
            "note_id": note_id,
            "task_id": "task456",
            "content": special_content,
            "created_by": {"user_id": "user1"},
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify content preserved
        doc = db.collection(notes_collection).document(note_id).get()
        assert doc.to_dict()["content"] == special_content
        
        # Cleanup
        db.collection(notes_collection).document(note_id).delete()
    
    
    def test_empty_task_has_no_comments(self, db, test_collection_prefix, cleanup_collections):
        """Test that a task with no comments returns empty list."""
        notes_collection = f"{test_collection_prefix}_notes"
        cleanup_collections.append(notes_collection)
        
        task_id = f"empty_task_{datetime.now(timezone.utc).timestamp()}"
        
        # Query comments for non-existent task
        query = db.collection(notes_collection).where(filter=FieldFilter("task_id", "==", task_id))
        comments = [doc.to_dict() for doc in query.stream()]
        
        assert len(comments) == 0
    
    
    def test_comment_count_for_task(self, db, test_collection_prefix, cleanup_collections):
        """Test counting the number of comments on a task."""
        notes_collection = f"{test_collection_prefix}_notes"
        cleanup_collections.append(notes_collection)
        
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}"
        expected_count = 7
        note_ids = []
        
        # Add specific number of comments
        for i in range(expected_count):
            note_id = f"note_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(notes_collection).document(note_id).set({
                "note_id": note_id,
                "task_id": task_id,
                "content": f"Comment {i}",
                "created_by": {"user_id": "user1"},
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            note_ids.append(note_id)
        
        # Count comments
        query = db.collection(notes_collection).where(filter=FieldFilter("task_id", "==", task_id))
        comment_count = len([doc for doc in query.stream()])
        
        assert comment_count == expected_count
        
        # Cleanup
        for note_id in note_ids:
            db.collection(notes_collection).document(note_id).delete()
