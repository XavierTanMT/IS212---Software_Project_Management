"""
FINAL BRANCH COVERAGE - Cover remaining branch and exception lines
Branch 71->74: role not in role_breakdown
Lines 493-494: Manager soft delete Firebase Auth exception
"""
import pytest
from unittest.mock import Mock
import sys

fake_auth = sys.modules.get("firebase_admin.auth")


class TestFinalBranchCoverage:
    """Cover the last missing branch and exception lines"""
    
    def test_branch_71_74_unknown_role_not_in_breakdown(self, client, setup_firebase_mocks, mock_db):
        """Branch 71->74: User with role not in role_breakdown dict"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin", "name": "Admin", "email": "admin@test.com", "is_active": True})
        
        # Create users with a role that's not in the initial role_breakdown keys
        # role_breakdown starts with: {"admin": 0, "manager": 0, "staff": 0}
        user1 = Mock(id='u1')
        user1.to_dict = Mock(return_value={
            'user_id': 'u1',
            'name': 'User 1',
            'role': 'director',  # This role is NOT in initial role_breakdown
            'is_active': True
        })
        
        user2 = Mock(id='u2')
        user2.to_dict = Mock(return_value={
            'user_id': 'u2',
            'name': 'User 2',
            'role': 'hr',  # This role is also NOT in initial role_breakdown
            'is_active': True
        })
        
        user3 = Mock(id='u3')
        user3.to_dict = Mock(return_value={
            'user_id': 'u3',
            'name': 'User 3',
            'role': 'unknown_role',  # Unknown role
            'is_active': False
        })
        
        def collection_mock(name):
            if name == "users":
                return Mock(
                    document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))),
                    stream=Mock(return_value=[user1, user2, user3])
                )
            elif name == "tasks":
                return Mock(stream=Mock(return_value=[]))
            elif name == "projects":
                return Mock(stream=Mock(return_value=[]))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.get('/api/admin/dashboard?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        
        # The branch 71->74 should be triggered when role NOT in role_breakdown
        # These users should still be counted in statistics
        assert data['statistics']['total_users'] == 3
        assert 'recent_users' in data
        assert len(data['recent_users']) == 3
        
    def test_lines_493_494_manager_soft_delete_firebase_exception(self, client, setup_firebase_mocks, mock_db):
        """Lines 493-494: Manager soft delete with Firebase Auth exception"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_manager = Mock(exists=True)
        mock_manager.to_dict = Mock(return_value={"role": "manager", "is_active": True})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(
                            get=Mock(return_value=mock_manager),
                            update=Mock()  # Firestore update succeeds
                        )
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        # Make Firebase Auth update_user raise exception (lines 493-494)
        fake_auth.update_user = Mock(side_effect=Exception("Firebase Auth service unavailable"))
        
        response = client.delete('/api/admin/managers/mgr1?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        assert data['deleted_type'] == 'soft_delete'
        # Even though Firebase Auth failed, Firestore update succeeded


class TestEdgeCaseRoles:
    """Test various edge cases for role handling"""
    
    def test_multiple_unknown_roles_in_dashboard(self, client, setup_firebase_mocks, mock_db):
        """Test dashboard with multiple users having roles not in breakdown"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        # Create users with various unknown roles
        users = []
        unknown_roles = ['director', 'hr', 'intern', 'contractor', 'consultant']
        for i, role in enumerate(unknown_roles):
            user = Mock(id=f'u{i}')
            user.to_dict = Mock(return_value={
                'user_id': f'u{i}',
                'name': f'User {i}',
                'role': role,
                'is_active': True
            })
            users.append(user)
        
        def collection_mock(name):
            if name == "users":
                return Mock(
                    document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))),
                    stream=Mock(return_value=users)
                )
            elif name == "tasks":
                return Mock(stream=Mock(return_value=[]))
            elif name == "projects":
                return Mock(stream=Mock(return_value=[]))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.get('/api/admin/dashboard?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        
        # All users should be counted even with unknown roles
        assert data['statistics']['total_users'] == 5
        # Statistics should still work
        assert 'statistics' in data
        assert 'recent_users' in data


class TestManagerDeleteAllPaths:
    """Ensure all manager delete paths are covered"""
    
    def test_manager_soft_delete_firebase_disabled_exception(self, client, setup_firebase_mocks, mock_db):
        """Soft delete manager - Firebase Auth disable fails"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_manager = Mock(exists=True)
        mock_manager.to_dict = Mock(return_value={"role": "manager", "is_active": True})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(
                            get=Mock(return_value=mock_manager),
                            update=Mock()
                        )
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        # Firebase Auth update_user fails with different exception
        fake_auth.update_user = Mock(side_effect=Exception("Network timeout"))
        
        response = client.delete('/api/admin/managers/manager_id?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Manager deactivated'
        
    def test_manager_soft_delete_firebase_permission_exception(self, client, setup_firebase_mocks, mock_db):
        """Soft delete manager - Firebase Auth permission denied"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_manager = Mock(exists=True)
        mock_manager.to_dict = Mock(return_value={"role": "manager", "is_active": True})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(
                            get=Mock(return_value=mock_manager),
                            update=Mock()
                        )
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        # Firebase Auth update_user fails with permission error
        fake_auth.update_user = Mock(side_effect=Exception("Permission denied"))
        
        response = client.delete('/api/admin/managers/mgr_id?admin_id=admin1')
        assert response.status_code == 200
