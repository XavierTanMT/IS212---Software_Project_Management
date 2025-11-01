"""
EXACT LINE COVERAGE - Targeting specific line numbers from coverage report
Lines to cover: 177, 182, 372, 418-419, 446, 473-474, 493-494, 521, 543-549, 574, 630, 669
"""
import pytest
from unittest.mock import Mock
import sys

fake_auth = sys.modules.get("firebase_admin.auth")


class TestExactLines:
    """Target exact line numbers from coverage report"""
    
    def test_line_177_get_users_no_admin_id(self, client, setup_firebase_mocks, mock_db):
        """Line 177: return error when no admin_id in get_users"""
        # Call get_users WITHOUT admin_id parameter or header
        response = client.get('/api/admin/users')
        assert response.status_code == 401
        assert b'admin_id required' in response.data
    
    def test_line_182_get_users_invalid_admin(self, client, setup_firebase_mocks, mock_db):
        """Line 182: return error_response from _verify_admin_access"""
        # Mock admin that doesn't exist or is not admin
        mock_not_found = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_not_found
        
        response = client.get('/api/admin/users?admin_id=invalid')
        # Should return error from _verify_admin_access
        assert response.status_code in [401, 403, 404]
    
    def test_line_372_staff_removal_not_staff_role(self, client, setup_firebase_mocks, mock_db):
        """Line 372: Can only remove staff... error"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_staff = Mock(exists=True, to_dict=lambda: {"role": "manager", "name": "Mgr"})
        
        def coll_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_not_staff))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_mock)
        
        response = client.delete('/api/admin/staff/mgr1?admin_id=admin1')
        assert response.status_code == 400
        assert b'staff only' in response.data
    
    def test_lines_418_419_manager_removal_not_found(self, client, setup_firebase_mocks, mock_db):
        """Lines 418-419: return 404 when manager not found"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_found = Mock(exists=False)
        
        def coll_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_not_found))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_mock)
        
        response = client.delete('/api/admin/managers/notfound?admin_id=admin1')
        assert response.status_code == 404
        assert b'not found' in response.data.lower()
    
    def test_line_446_manager_removal_not_manager_role(self, client, setup_firebase_mocks, mock_db):
        """Line 446: Can only remove managers... error"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_manager = Mock(exists=True, to_dict=lambda: {"role": "staff", "name": "Staff"})
        
        def coll_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_not_manager))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_mock)
        
        response = client.delete('/api/admin/managers/staff1?admin_id=admin1')
        assert response.status_code == 400
        assert b'managers only' in response.data
    
    def test_lines_473_474_role_change_user_not_found(self, client, setup_firebase_mocks, mock_db):
        """Lines 473-474: return 404 when user not found for role change"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_found = Mock(exists=False)
        
        def coll_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_not_found))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_mock)
        
        response = client.put('/api/admin/users/notfound/role?admin_id=admin1', 
                            json={'role': 'manager'})
        assert response.status_code == 404
    
    def test_lines_493_494_role_change_invalid_role(self, client, setup_firebase_mocks, mock_db):
        """Lines 493-494: Invalid role value"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=True, to_dict=lambda: {"role": "staff", "name": "User"})
        
        def coll_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_user))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_mock)
        
        response = client.put('/api/admin/users/user1/role?admin_id=admin1', 
                            json={'role': 'invalidrole'})
        assert response.status_code == 400
        assert b'Invalid role' in response.data
    
    def test_line_521_self_role_change_prevention(self, client, setup_firebase_mocks, mock_db):
        """Line 521: Cannot change your own role"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin", "name": "Admin"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.put('/api/admin/users/admin1/role?admin_id=admin1', 
                            json={'role': 'staff'})
        assert response.status_code == 400
        assert b'Cannot change your own role' in response.data
    
    def test_lines_543_to_549_status_change_user_not_found(self, client, setup_firebase_mocks, mock_db):
        """Lines 543-549: User not found for status change"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_found = Mock(exists=False)
        
        def coll_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_not_found))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_mock)
        
        response = client.put('/api/admin/users/notfound/status?admin_id=admin1', 
                            json={'is_active': False})
        assert response.status_code == 404
    
    def test_line_574_status_change_non_boolean(self, client, setup_firebase_mocks, mock_db):
        """Line 574: is_active must be true or false"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=True, to_dict=lambda: {"role": "staff", "name": "User"})
        
        def coll_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_user))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_mock)
        
        # Send string instead of boolean
        response = client.put('/api/admin/users/user1/status?admin_id=admin1', 
                            json={'is_active': 'yes'})
        assert response.status_code == 400
        assert b'must be true or false' in response.data
    
    def test_line_630_projects_endpoint_no_admin_id(self, client, setup_firebase_mocks, mock_db):
        """Line 630: error return in get_all_projects when no admin_id"""
        # Line 630 is likely the error return in get_all_projects
        response = client.get('/api/admin/projects')
        assert response.status_code == 401
    
    def test_line_669_tasks_endpoint_no_admin_id(self, client, setup_firebase_mocks, mock_db):
        """Line 669: error return in get_all_tasks when no admin_id"""
        # Line 669 is likely the error return in get_all_tasks
        response = client.get('/api/admin/tasks')
        assert response.status_code == 401


class TestRemainingEndpointErrors:
    """Test error paths for all endpoints"""
    
    def test_all_endpoints_without_admin_id(self, client, setup_firebase_mocks):
        """Test that all endpoints require admin_id"""
        endpoints = [
            ('GET', '/api/admin/dashboard'),
            ('GET', '/api/admin/statistics'),
            ('GET', '/api/admin/users'),
            ('POST', '/api/admin/staff'),
            ('POST', '/api/admin/managers'),
            ('DELETE', '/api/admin/staff/user1'),
            ('DELETE', '/api/admin/managers/user1'),
            ('PUT', '/api/admin/users/user1/role'),
            ('PUT', '/api/admin/users/user1/status'),
            ('GET', '/api/admin/projects'),
            ('GET', '/api/admin/tasks'),
            # Skip cleanup endpoints - different HTTP methods
        ]
        
        for method, endpoint in endpoints:
            if method == 'GET':
                response = client.get(endpoint)
            elif method == 'POST':
                response = client.post(endpoint, json={})
            elif method == 'PUT':
                response = client.put(endpoint, json={})
            elif method == 'DELETE':
                response = client.delete(endpoint)
            
            assert response.status_code in [401, 404], f"Failed for {method} {endpoint}: got {response.status_code}"
    
    def test_all_endpoints_with_non_admin_user(self, client, setup_firebase_mocks, mock_db):
        """Test that all endpoints reject non-admin users"""
        # Mock a staff user (not admin)
        mock_staff = Mock(exists=True, to_dict=lambda: {"role": "staff", "name": "Staff"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_staff
        
        endpoints = [
            ('GET', '/api/admin/dashboard?admin_id=staff1'),
            ('GET', '/api/admin/statistics?admin_id=staff1'),
            ('GET', '/api/admin/users?admin_id=staff1'),
        ]
        
        for method, endpoint in endpoints:
            if method == 'GET':
                response = client.get(endpoint)
            
            assert response.status_code in [401, 403], f"Failed for {method} {endpoint}"
