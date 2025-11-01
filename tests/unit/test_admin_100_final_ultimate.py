"""
COMPLETE REMAINING COVERAGE - Lines 791-792, 798-801, 807-808, 826-907
Target 100% coverage by covering cleanup exceptions and recommendation helper
"""
import pytest
from unittest.mock import Mock, patch
import sys

fake_auth = sys.modules.get("firebase_admin.auth")


class TestCleanupExceptionPaths:
    """Cover cleanup endpoint exception handling (lines 791-792, 798-801, 807-808)"""
    
    def test_lines_791_792_firestore_delete_exception(self, client, setup_firebase_mocks, mock_db):
        """Lines 791-792: Exception when deleting from Firestore"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "test@test.com"})
        
        # Make Firestore delete raise exception
        mock_doc = Mock(
            get=Mock(return_value=mock_user),
            delete=Mock(side_effect=Exception("Firestore permission denied"))
        )
        mock_db.collection.return_value.document.return_value = mock_doc
        
        # Firebase Auth returns not found
        fake_auth.delete_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.delete('/api/admin/cleanup/user1?confirm=true')
        assert response.status_code in [200, 404]
        data = response.get_json()
        assert 'errors' in data
        assert any('Firestore deletion failed' in err for err in data.get('errors', []))
    
    def test_lines_798_801_firebase_auth_delete_exception(self, client, setup_firebase_mocks, mock_db):
        """Lines 798-801: General exception when deleting from Firebase Auth"""
        mock_user = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        # Firebase Auth raises general exception (not UserNotFoundError)
        fake_auth.delete_user = Mock(side_effect=Exception("Firebase network error"))
        
        response = client.delete('/api/admin/cleanup/user1?confirm=true')
        assert response.status_code in [200, 404]
        data = response.get_json()
        assert 'errors' in data
        assert any('Firebase Auth deletion failed' in err for err in data.get('errors', []))
    
    def test_lines_807_808_both_deletions_fail(self, client, setup_firebase_mocks, mock_db):
        """Lines 807-808: Both Firestore and Firebase Auth deletions fail"""
        mock_user = Mock(exists=True)
        
        # Firestore delete fails
        mock_doc = Mock(
            get=Mock(return_value=mock_user),
            delete=Mock(side_effect=Exception("Firestore error"))
        )
        mock_db.collection.return_value.document.return_value = mock_doc
        
        # Firebase Auth delete fails
        fake_auth.delete_user = Mock(side_effect=Exception("Firebase error"))
        
        response = client.delete('/api/admin/cleanup/user1?confirm=true')
        assert response.status_code in [200, 404]
        data = response.get_json()
        assert 'errors' in data
        # Should have both error messages
        assert len(data['errors']) >= 2


class TestRecommendationHelper:
    """Cover _get_recommendation helper function (lines 826-907)"""
    
    def test_recommendation_both_synced(self, client, setup_firebase_mocks, mock_db):
        """Lines 826-907: Recommendation when both systems have user"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "synced@test.com", "name": "Synced User"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(return_value=Mock(
            uid='synced_user',
            email='synced@test.com',
            display_name='Synced User',
            disabled=False,
            email_verified=True
        ))
        
        response = client.get('/api/admin/check/synced_user')
        assert response.status_code == 200
        data = response.get_json()
        assert data['synced'] == True
        assert data['in_firestore'] == True
        assert data['in_firebase_auth'] == True
        assert 'recommendation' in data
        assert 'properly synced' in data['recommendation'].lower()
    
    def test_recommendation_firestore_only(self, client, setup_firebase_mocks, mock_db):
        """Lines 826-907: Recommendation when user only in Firestore"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "orphan@test.com", "name": "Orphan"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.get('/api/admin/check/orphan_firestore')
        assert response.status_code == 200
        data = response.get_json()
        assert data['in_firestore'] == True
        assert data['in_firebase_auth'] == False
        assert 'recommendation' in data
        assert 'Orphaned Firestore' in data['recommendation'] or 'cleanup' in data['recommendation'].lower()
    
    def test_recommendation_firebase_only(self, client, setup_firebase_mocks, mock_db):
        """Lines 826-907: Recommendation when user only in Firebase Auth"""
        mock_user = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(return_value=Mock(
            uid='firebase_only',
            email='firebase@test.com',
            display_name='Firebase Only',
            disabled=False,
            email_verified=True
        ))
        
        response = client.get('/api/admin/check/firebase_only')
        assert response.status_code == 200
        data = response.get_json()
        assert data['in_firestore'] == False
        assert data['in_firebase_auth'] == True
        assert 'recommendation' in data
        assert 'Orphaned Firebase' in data['recommendation'] or 'sync' in data['recommendation'].lower()
    
    def test_recommendation_neither_exists(self, client, setup_firebase_mocks, mock_db):
        """Lines 826-907: Recommendation when user doesn't exist anywhere"""
        mock_user = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.get('/api/admin/check/nonexistent_user')
        assert response.status_code == 200
        data = response.get_json()
        assert data['in_firestore'] == False
        assert data['in_firebase_auth'] == False
        assert 'recommendation' in data
        assert "doesn't exist" in data['recommendation'].lower() or 'safe to register' in data['recommendation'].lower()


class TestSyncEndpointAllCases:
    """Cover sync endpoint to ensure recommendation helper is called (lines 826-907)"""
    
    def test_sync_firestore_only_without_password(self, client, setup_firebase_mocks, mock_db):
        """Sync when user in Firestore only - missing password"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "orphan@test.com", "name": "Orphan"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.post('/api/admin/sync/orphan_user', json={})
        assert response.status_code == 400
        data = response.get_json()
        assert 'Password required' in data.get('error', '')
    
    def test_sync_firestore_only_with_password(self, client, setup_firebase_mocks, mock_db):
        """Sync when user in Firestore only - with password"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "orphan@test.com", "name": "Orphan User"})
        
        mock_doc = Mock(
            get=Mock(return_value=mock_user),
            update=Mock()
        )
        mock_db.collection.return_value.document.return_value = mock_doc
        
        # First call: check if exists (should return UserNotFoundError)
        # Second call: after creation (should return user)
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        fake_auth.create_user = Mock(return_value=Mock(uid='new_firebase_uid'))
        
        response = client.post('/api/admin/sync/orphan_user', json={"password": "SecurePass123"})
        assert response.status_code == 201
        data = response.get_json()
        assert 'Created Firebase Auth user' in data.get('message', '')
    
    def test_sync_firebase_only(self, client, setup_firebase_mocks, mock_db):
        """Sync when user in Firebase Auth only"""
        mock_user = Mock(exists=False)
        
        # Mock the document to be set
        mock_doc = Mock(
            get=Mock(return_value=mock_user),
            set=Mock()
        )
        mock_db.collection.return_value.document.return_value = mock_doc
        
        fake_auth.get_user = Mock(return_value=Mock(
            uid='firebase_user',
            email='firebase@test.com',
            display_name='Firebase User'
        ))
        
        response = client.post('/api/admin/sync/firebase_user', json={})
        assert response.status_code == 201
        data = response.get_json()
        assert 'Created Firestore document' in data.get('message', '')
    
    def test_sync_already_synced(self, client, setup_firebase_mocks, mock_db):
        """Sync when user already in both systems"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "synced@test.com", "name": "Synced"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(return_value=Mock(uid='synced', email='synced@test.com'))
        
        response = client.post('/api/admin/sync/synced_user', json={})
        assert response.status_code == 200
        data = response.get_json()
        assert 'Already synced' in data.get('status', '')
    
    def test_sync_user_not_found_anywhere(self, client, setup_firebase_mocks, mock_db):
        """Sync when user doesn't exist anywhere"""
        mock_user = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.post('/api/admin/sync/nonexistent', json={})
        assert response.status_code == 404
        data = response.get_json()
        assert 'Not found' in data.get('status', '') or "doesn't exist" in data.get('message', '')
    
    def test_sync_create_firebase_user_exception(self, client, setup_firebase_mocks, mock_db):
        """Sync endpoint - Firebase user creation fails"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "orphan@test.com", "name": "Orphan"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        fake_auth.create_user = Mock(side_effect=Exception("Firebase creation failed"))
        
        response = client.post('/api/admin/sync/orphan_fail', json={"password": "Pass123"})
        assert response.status_code == 500
        data = response.get_json()
        assert 'Failed to create Firebase Auth user' in data.get('error', '')


class TestCleanupSuccessCases:
    """Test successful cleanup scenarios"""
    
    def test_cleanup_firestore_success_firebase_not_found(self, client, setup_firebase_mocks, mock_db):
        """Cleanup successfully deletes from Firestore, Firebase user not found"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "test@test.com"})
        
        mock_doc = Mock(
            get=Mock(return_value=mock_user),
            delete=Mock()  # Succeeds
        )
        mock_db.collection.return_value.document.return_value = mock_doc
        
        # Firebase user not found
        fake_auth.delete_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.delete('/api/admin/cleanup/user1?confirm=true')
        assert response.status_code == 200
        data = response.get_json()
        assert data['firestore_deleted'] == True
        assert 'Cleanup completed' in data['status']
    
    def test_cleanup_firebase_success_firestore_not_found(self, client, setup_firebase_mocks, mock_db):
        """Cleanup successfully deletes from Firebase, Firestore not found"""
        mock_user = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        # Firebase delete succeeds
        fake_auth.delete_user = Mock()
        
        response = client.delete('/api/admin/cleanup/user1?confirm=true')
        assert response.status_code == 200
        data = response.get_json()
        assert data['firebase_auth_deleted'] == True
        assert 'Cleanup completed' in data['status']
    
    def test_cleanup_both_succeed(self, client, setup_firebase_mocks, mock_db):
        """Cleanup successfully deletes from both systems"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "test@test.com"})
        
        mock_doc = Mock(
            get=Mock(return_value=mock_user),
            delete=Mock()
        )
        mock_db.collection.return_value.document.return_value = mock_doc
        
        fake_auth.delete_user = Mock()
        
        response = client.delete('/api/admin/cleanup/user1?confirm=true')
        assert response.status_code == 200
        data = response.get_json()
        assert data['firestore_deleted'] == True
        assert data['firebase_auth_deleted'] == True
        assert 'Cleanup completed' in data['status']
    
    def test_cleanup_nothing_to_cleanup(self, client, setup_firebase_mocks, mock_db):
        """Cleanup when user exists nowhere - lines 807-808"""
        mock_user = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.delete_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.delete('/api/admin/cleanup/nonexistent?confirm=true')
        assert response.status_code == 404
        data = response.get_json()
        assert 'Nothing to clean up' in data['status']
