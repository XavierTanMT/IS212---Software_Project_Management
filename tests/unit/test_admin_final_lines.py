"""
REMAINING LINES COVERAGE - Target the last 45 uncovered lines
Focus on successful execution paths for role changes, status changes, and cleanup
"""
import pytest
from unittest.mock import Mock, patch
import sys

fake_auth = sys.modules.get("firebase_admin.auth")


class TestSuccessfulRoleChanges:
    """Cover successful role change paths (lines 543-549)"""
    
    def test_lines_543_549_successful_role_change_to_manager(self, client, setup_firebase_mocks, mock_db):
        """Lines 543-549: Successful role change update and return"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"role": "staff", "is_active": True})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(
                            get=Mock(return_value=mock_user),
                            update=Mock()  # Should succeed
                        )
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        # Don't mock set_custom_user_claims - let it succeed
        fake_auth.set_custom_user_claims = Mock()
        
        response = client.put('/api/admin/users/user1/role?admin_id=admin1', json={"role": "manager"})
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        assert data['new_role'] == 'manager'
    
    def test_lines_543_549_successful_role_change_to_staff(self, client, setup_firebase_mocks, mock_db):
        """Lines 543-549: Successful role change from manager to staff"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"role": "manager", "is_active": True})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(
                            get=Mock(return_value=mock_user),
                            update=Mock()
                        )
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        fake_auth.set_custom_user_claims = Mock()
        
        response = client.put('/api/admin/users/user1/role?admin_id=admin1', json={"role": "staff"})
        assert response.status_code == 200


class TestHardDeletePaths:
    """Cover hard delete exception paths"""
    
    def test_lines_473_474_hard_delete_manager_with_exception(self, client, setup_firebase_mocks, mock_db):
        """Lines 473-474: Hard delete manager with Firebase Auth exception"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"role": "manager"})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(
                            get=Mock(return_value=mock_user),
                            delete=Mock()
                        )
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        # Firebase Auth delete raises exception
        fake_auth.delete_user = Mock(side_effect=Exception("Cannot delete from Firebase"))
        
        response = client.delete('/api/admin/managers/manager1?admin_id=admin1&hard_delete=true')
        assert response.status_code == 200
        data = response.get_json()
        assert data['deleted_type'] == 'hard_delete'


class TestCleanupErrorPaths:
    """Cover cleanup endpoint error paths (lines 790-808)"""
    
    def test_lines_790_792_cleanup_user_not_in_firestore(self, client, setup_firebase_mocks, mock_db):
        """Lines 790-792: Cleanup when user not in Firestore"""
        mock_user = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        # User exists in Firebase Auth but not Firestore
        fake_auth.get_user = Mock(return_value=Mock(uid='user1', email='test@test.com'))
        fake_auth.delete_user = Mock()
        
        response = client.delete('/api/admin/cleanup/user1?confirm=true')
        assert response.status_code == 200
        data = response.get_json()
        assert 'errors' in data
    
    def test_lines_798_801_cleanup_user_not_in_firebase_auth(self, client, setup_firebase_mocks, mock_db):
        """Lines 798-801: Cleanup when user not in Firebase Auth"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "test@test.com"})
        mock_db.collection.return_value.document.return_value = Mock(
            get=Mock(return_value=mock_user),
            delete=Mock()
        )
        
        # User not in Firebase Auth
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.delete('/api/admin/cleanup/user1?confirm=true')
        assert response.status_code == 200
        data = response.get_json()
        assert data['firestore_deleted'] == True
        assert 'firebase_auth_deleted' in data
    
    def test_lines_807_808_cleanup_exception_handling(self, client, setup_firebase_mocks, mock_db):
        """Lines 807-808: Exception during cleanup"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "test@test.com"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        # Firebase Auth get_user raises general exception
        fake_auth.get_user = Mock(side_effect=Exception("Network error"))
        
        response = client.delete('/api/admin/cleanup/user1?confirm=true')
        assert response.status_code == 200


class TestRecommendationHelperFunction:
    """Cover _get_recommendation helper function (lines 826-907)"""
    
    def test_lines_826_907_all_recommendation_cases(self, client, setup_firebase_mocks, mock_db):
        """Lines 826-907: Cover all 4 cases of recommendations"""
        # Case 1: Both True - Synced
        mock_user_synced = Mock(exists=True)
        mock_user_synced.to_dict = Mock(return_value={"email": "synced@test.com"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_synced
        
        # Return proper dict values, not Mock objects
        fake_auth.get_user = Mock(return_value=Mock(
            uid='synced',
            email='synced@test.com',
            display_name='Synced User',
            disabled=False,
            email_verified=True
        ))
        
        response = client.get('/api/admin/check/synced')
        assert response.status_code == 200
        data = response.get_json()
        assert data['synced'] == True
        assert 'recommendation' in data
        
        # Case 2: in_firestore=True, in_firebase_auth=False
        mock_user_orphan = Mock(exists=True)
        mock_user_orphan.to_dict = Mock(return_value={"email": "orphan@test.com"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_orphan
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.get('/api/admin/check/orphan')
        assert response.status_code == 200
        data = response.get_json()
        assert data['in_firestore'] == True
        assert data['in_firebase_auth'] == False
        assert 'recommendation' in data
        
        # Case 3: in_firestore=False, in_firebase_auth=True
        mock_user_ghost = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_ghost
        fake_auth.get_user = Mock(return_value=Mock(
            uid='ghost',
            email='ghost@test.com',
            display_name='Ghost User',
            disabled=False,
            email_verified=False
        ))
        
        response = client.get('/api/admin/check/ghost')
        assert response.status_code == 200
        data = response.get_json()
        assert data['in_firestore'] == False
        assert data['in_firebase_auth'] == True
        assert 'recommendation' in data
        
        # Case 4: Both False
        mock_user_none = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_none
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.get('/api/admin/check/nonexistent')
        assert response.status_code == 200
        data = response.get_json()
        assert data['in_firestore'] == False
        assert data['in_firebase_auth'] == False
        assert 'recommendation' in data
    
    def test_line_920_recommendation_default_case(self, client, setup_firebase_mocks, mock_db):
        """Line 920: Default recommendation case"""
        # This tests an edge case in the recommendation function
        mock_user = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.get('/api/admin/check/test_default')
        assert response.status_code == 200
        data = response.get_json()
        assert 'recommendation' in data


class TestInvalidAdminAccessPaths:
    """Cover error_response return paths for invalid admin"""
    
    def test_line_521_change_role_invalid_admin(self, client, setup_firebase_mocks, mock_db):
        """Line 521: Invalid admin in change_role endpoint"""
        mock_admin = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.put('/api/admin/users/user1/role?admin_id=fake', json={"new_role": "manager"})
        assert response.status_code in [401, 403, 404]
    
    def test_line_574_change_status_invalid_admin(self, client, setup_firebase_mocks, mock_db):
        """Line 574: Invalid admin in change_status endpoint"""
        mock_admin = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.put('/api/admin/users/user1/status?admin_id=fake', json={"is_active": False})
        assert response.status_code in [401, 403, 404]
    
    def test_line_630_get_projects_invalid_admin(self, client, setup_firebase_mocks, mock_db):
        """Line 630: Invalid admin in get_all_projects endpoint"""
        mock_admin = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.get('/api/admin/projects?admin_id=fake')
        assert response.status_code in [401, 403, 404]
    
    def test_line_669_get_tasks_invalid_admin(self, client, setup_firebase_mocks, mock_db):
        """Line 669: Invalid admin in get_all_tasks endpoint"""
        mock_admin = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.get('/api/admin/tasks?admin_id=fake')
        assert response.status_code in [401, 403, 404]
