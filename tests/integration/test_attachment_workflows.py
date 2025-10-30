"""Integration tests for attachment workflows using real Firebase."""
import pytest
from datetime import datetime, timezone
from google.cloud.firestore_v1.base_query import FieldFilter


class TestAttachmentOperations:
    """Test basic attachment CRUD operations with real Firebase."""
    
    def test_add_attachment_to_task(self, db, test_collection_prefix, cleanup_collections):
        """Test adding an attachment to a task."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        attachments_collection = f"{test_collection_prefix}_attachments"
        cleanup_collections.extend([tasks_collection, attachments_collection])
        
        # Create task
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}"
        db.collection(tasks_collection).document(task_id).set({
            "task_id": task_id,
            "title": "Task with Attachment",
            "status": "In Progress"
        })
        
        # Add attachment
        attachment_id = f"attachment_{datetime.now(timezone.utc).timestamp()}"
        attachment_data = {
            "attachment_id": attachment_id,
            "task_id": task_id,
            "filename": "document.pdf",
            "file_url": "https://example.com/files/document.pdf",
            "file_size": 1024576,  # 1MB in bytes
            "mime_type": "application/pdf",
            "uploaded_by": {
                "user_id": "user123",
                "name": "Test User",
                "email": "test@example.com"
            },
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }
        
        db.collection(attachments_collection).document(attachment_id).set(attachment_data)
        
        # Verify attachment exists
        doc = db.collection(attachments_collection).document(attachment_id).get()
        assert doc.exists
        
        retrieved_attachment = doc.to_dict()
        assert retrieved_attachment["filename"] == "document.pdf"
        assert retrieved_attachment["task_id"] == task_id
        assert retrieved_attachment["file_size"] == 1024576
        
        # Cleanup
        db.collection(tasks_collection).document(task_id).delete()
        db.collection(attachments_collection).document(attachment_id).delete()
    
    
    def test_list_attachments_for_task(self, db, test_collection_prefix, cleanup_collections):
        """Test listing all attachments for a specific task."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        attachments_collection = f"{test_collection_prefix}_attachments"
        cleanup_collections.extend([tasks_collection, attachments_collection])
        
        # Create task
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}"
        db.collection(tasks_collection).document(task_id).set({
            "task_id": task_id,
            "title": "Task with Multiple Attachments",
            "status": "To Do"
        })
        
        # Add multiple attachments
        attachment_ids = []
        filenames = ["report.pdf", "screenshot.png", "data.xlsx"]
        
        for i, filename in enumerate(filenames):
            attachment_id = f"attachment_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(attachments_collection).document(attachment_id).set({
                "attachment_id": attachment_id,
                "task_id": task_id,
                "filename": filename,
                "file_url": f"https://example.com/files/{filename}",
                "file_size": (i + 1) * 100000,
                "uploaded_by": {"user_id": f"user{i}"},
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            })
            attachment_ids.append(attachment_id)
        
        # Query attachments for this task
        query = db.collection(attachments_collection).where(filter=FieldFilter("task_id", "==", task_id))
        attachments = [doc.to_dict() for doc in query.stream()]
        
        assert len(attachments) >= 3
        attachment_filenames = [a["filename"] for a in attachments]
        assert "report.pdf" in attachment_filenames
        assert "screenshot.png" in attachment_filenames
        assert "data.xlsx" in attachment_filenames
        
        # Cleanup
        db.collection(tasks_collection).document(task_id).delete()
        for attachment_id in attachment_ids:
            db.collection(attachments_collection).document(attachment_id).delete()
    
    
    def test_delete_attachment(self, db, test_collection_prefix, cleanup_collections):
        """Test deleting an attachment."""
        attachments_collection = f"{test_collection_prefix}_attachments"
        cleanup_collections.append(attachments_collection)
        
        # Create attachment
        attachment_id = f"attachment_{datetime.now(timezone.utc).timestamp()}"
        db.collection(attachments_collection).document(attachment_id).set({
            "attachment_id": attachment_id,
            "task_id": "task456",
            "filename": "to_delete.txt",
            "file_url": "https://example.com/files/to_delete.txt",
            "uploaded_by": {"user_id": "user1"},
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify creation
        doc = db.collection(attachments_collection).document(attachment_id).get()
        assert doc.exists
        
        # Delete attachment
        db.collection(attachments_collection).document(attachment_id).delete()
        
        # Verify deletion
        doc = db.collection(attachments_collection).document(attachment_id).get()
        assert not doc.exists
    
    
    def test_update_attachment_metadata(self, db, test_collection_prefix, cleanup_collections):
        """Test updating attachment metadata."""
        attachments_collection = f"{test_collection_prefix}_attachments"
        cleanup_collections.append(attachments_collection)
        
        # Create attachment
        attachment_id = f"attachment_{datetime.now(timezone.utc).timestamp()}"
        db.collection(attachments_collection).document(attachment_id).set({
            "attachment_id": attachment_id,
            "task_id": "task789",
            "filename": "old_name.txt",
            "file_url": "https://example.com/files/old_name.txt",
            "uploaded_by": {"user_id": "user1"},
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Update filename
        new_filename = "renamed_file.txt"
        db.collection(attachments_collection).document(attachment_id).update({
            "filename": new_filename
        })
        
        # Verify update
        doc = db.collection(attachments_collection).document(attachment_id).get()
        assert doc.to_dict()["filename"] == new_filename
        
        # Cleanup
        db.collection(attachments_collection).document(attachment_id).delete()


class TestAttachmentFileTypes:
    """Test handling different file types and formats."""
    
    def test_various_file_types(self, db, test_collection_prefix, cleanup_collections):
        """Test attachments with various file types."""
        attachments_collection = f"{test_collection_prefix}_attachments"
        cleanup_collections.append(attachments_collection)
        
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}"
        
        # Test different file types
        file_types = [
            ("document.pdf", "application/pdf"),
            ("image.png", "image/png"),
            ("image.jpg", "image/jpeg"),
            ("video.mp4", "video/mp4"),
            ("archive.zip", "application/zip"),
            ("spreadsheet.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("code.py", "text/x-python"),
        ]
        
        attachment_ids = []
        for filename, mime_type in file_types:
            attachment_id = f"attachment_{filename}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(attachments_collection).document(attachment_id).set({
                "attachment_id": attachment_id,
                "task_id": task_id,
                "filename": filename,
                "file_url": f"https://example.com/files/{filename}",
                "mime_type": mime_type,
                "uploaded_by": {"user_id": "user1"},
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            })
            attachment_ids.append(attachment_id)
        
        # Query all attachments for this task
        query = db.collection(attachments_collection).where(filter=FieldFilter("task_id", "==", task_id))
        attachments = [doc.to_dict() for doc in query.stream()]
        
        assert len(attachments) >= len(file_types)
        
        # Verify each file type was stored
        stored_mime_types = [a["mime_type"] for a in attachments]
        for _, mime_type in file_types:
            assert mime_type in stored_mime_types
        
        # Cleanup
        for attachment_id in attachment_ids:
            db.collection(attachments_collection).document(attachment_id).delete()
    
    
    def test_large_file_metadata(self, db, test_collection_prefix, cleanup_collections):
        """Test attachment metadata for large files."""
        attachments_collection = f"{test_collection_prefix}_attachments"
        cleanup_collections.append(attachments_collection)
        
        attachment_id = f"attachment_{datetime.now(timezone.utc).timestamp()}"
        large_file_size = 100 * 1024 * 1024  # 100 MB
        
        db.collection(attachments_collection).document(attachment_id).set({
            "attachment_id": attachment_id,
            "task_id": "task123",
            "filename": "large_video.mp4",
            "file_url": "https://example.com/files/large_video.mp4",
            "file_size": large_file_size,
            "mime_type": "video/mp4",
            "uploaded_by": {"user_id": "user1"},
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify large file size is stored correctly
        doc = db.collection(attachments_collection).document(attachment_id).get()
        assert doc.to_dict()["file_size"] == large_file_size
        
        # Cleanup
        db.collection(attachments_collection).document(attachment_id).delete()


class TestAttachmentEdgeCases:
    """Test edge cases and complex attachment scenarios."""
    
    def test_task_with_no_attachments(self, db, test_collection_prefix, cleanup_collections):
        """Test that a task with no attachments returns empty list."""
        attachments_collection = f"{test_collection_prefix}_attachments"
        cleanup_collections.append(attachments_collection)
        
        task_id = f"empty_task_{datetime.now(timezone.utc).timestamp()}"
        
        # Query attachments for task with none
        query = db.collection(attachments_collection).where(filter=FieldFilter("task_id", "==", task_id))
        attachments = [doc.to_dict() for doc in query.stream()]
        
        assert len(attachments) == 0
    
    
    def test_attachment_with_special_filename(self, db, test_collection_prefix, cleanup_collections):
        """Test attachment with special characters in filename."""
        attachments_collection = f"{test_collection_prefix}_attachments"
        cleanup_collections.append(attachments_collection)
        
        attachment_id = f"attachment_{datetime.now(timezone.utc).timestamp()}"
        special_filename = "Report (Final) - 2024-01-15 [DRAFT] v2.0.pdf"
        
        db.collection(attachments_collection).document(attachment_id).set({
            "attachment_id": attachment_id,
            "task_id": "task123",
            "filename": special_filename,
            "file_url": "https://example.com/files/encoded_filename.pdf",
            "uploaded_by": {"user_id": "user1"},
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify filename is preserved
        doc = db.collection(attachments_collection).document(attachment_id).get()
        assert doc.to_dict()["filename"] == special_filename
        
        # Cleanup
        db.collection(attachments_collection).document(attachment_id).delete()
    
    
    def test_multiple_users_uploading_attachments(self, db, test_collection_prefix, cleanup_collections):
        """Test multiple users uploading attachments to same task."""
        attachments_collection = f"{test_collection_prefix}_attachments"
        cleanup_collections.append(attachments_collection)
        
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}"
        users = [
            {"user_id": "user1", "name": "Alice"},
            {"user_id": "user2", "name": "Bob"},
            {"user_id": "user3", "name": "Charlie"}
        ]
        
        attachment_ids = []
        for i, user in enumerate(users):
            attachment_id = f"attachment_{user['user_id']}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(attachments_collection).document(attachment_id).set({
                "attachment_id": attachment_id,
                "task_id": task_id,
                "filename": f"file_from_{user['name']}.pdf",
                "file_url": f"https://example.com/files/file_{i}.pdf",
                "uploaded_by": user,
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            })
            attachment_ids.append(attachment_id)
        
        # Query attachments
        query = db.collection(attachments_collection).where(filter=FieldFilter("task_id", "==", task_id))
        attachments = [doc.to_dict() for doc in query.stream()]
        
        assert len(attachments) >= 3
        uploaders = [a["uploaded_by"]["name"] for a in attachments]
        assert "Alice" in uploaders
        assert "Bob" in uploaders
        assert "Charlie" in uploaders
        
        # Cleanup
        for attachment_id in attachment_ids:
            db.collection(attachments_collection).document(attachment_id).delete()
    
    
    def test_attachment_count_for_task(self, db, test_collection_prefix, cleanup_collections):
        """Test counting attachments for a task."""
        attachments_collection = f"{test_collection_prefix}_attachments"
        cleanup_collections.append(attachments_collection)
        
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}"
        expected_count = 5
        attachment_ids = []
        
        # Add specific number of attachments
        for i in range(expected_count):
            attachment_id = f"attachment_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(attachments_collection).document(attachment_id).set({
                "attachment_id": attachment_id,
                "task_id": task_id,
                "filename": f"file_{i}.txt",
                "file_url": f"https://example.com/files/file_{i}.txt",
                "uploaded_by": {"user_id": "user1"},
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            })
            attachment_ids.append(attachment_id)
        
        # Count attachments
        query = db.collection(attachments_collection).where(filter=FieldFilter("task_id", "==", task_id))
        attachment_count = len([doc for doc in query.stream()])
        
        assert attachment_count == expected_count
        
        # Cleanup
        for attachment_id in attachment_ids:
            db.collection(attachments_collection).document(attachment_id).delete()
