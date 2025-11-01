"""
FINAL 16 LINES - Surgical precision to reach 100%
Missing: 177, 182, 372, 418-419, 446, 473-474, 493-494, 521, 543-549, 574, 630, 669
"""
import pytest
from unittest.mock import Mock
import sys

fake_auth = sys.modules.get("firebase_admin.auth")


class TestExactLine177:
    """Line 177: if role_filter and user_data.get("role") != role_filter: continue"""
    
    def test_line_177_exact(self, client, setup_firebase_mocks, mock_db):
        """Execute exact line 177 condition"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create users where role != role_filter to trigger continue
        u1 = Mock(id='u1')
        u1.to_dict = lambda: {'role': 'manager', 'name': 'M1', 'is_active': True}
        u2 = Mock(id='u2')
        u2.to_dict = lambda: {'role': 'staff', 'name': 'S1', 'is_active': True}
        
        call_admin = [False]
        
        def coll_eff(name):
            if name == "users":
                if not call_admin[0]:
                    call_admin[0] = True
                    return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))))
                else:
                    return Mock(stream=Mock(return_value=[u1, u2]))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_eff)
        
        # role_filter=staff, so manager user triggers line 177 continue
        response = client.get('/api/admin/users?admin_id=a1&role=staff')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['users']) == 1
        assert data['users'][0]['role'] == 'staff'


class TestExactLine182:
    """Line 182: if status_filter == "active" and not is_active: continue"""
    
    def test_line_182_exact(self, client, setup_firebase_mocks, mock_db):
        """Execute exact line 182 condition"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create inactive user to trigger continue when filtering for active
        u1 = Mock(id='u1')
        u1.to_dict = lambda: {'role': 'staff', 'name': 'S1', 'is_active': False}
        u2 = Mock(id='u2')
        u2.to_dict = lambda: {'role': 'staff', 'name': 'S2', 'is_active': True}
        
        call_admin = [False]
        
        def coll_eff(name):
            if name == "users":
                if not call_admin[0]:
                    call_admin[0] = True
                    return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))))
                else:
                    return Mock(stream=Mock(return_value=[u1, u2]))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_eff)
        
        # status_filter=active, so inactive user triggers line 182 continue
        response = client.get('/api/admin/users?admin_id=a1&status=active')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['users']) == 1
        assert data['users'][0]['is_active'] == True


class TestExactLine372:
    """Line 372: return jsonify({"error": "Can only remove staff..."}), 400"""
    
    def test_line_372_exact(self, client, setup_firebase_mocks, mock_db):
        """Execute exact line 372"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_staff = Mock(exists=True, to_dict=lambda: {"role": "manager", "name": "M"})
        
        def coll_eff(name):
            if name == "users":
                def doc_eff(doc_id):
                    if doc_id == 'a1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_not_staff))
                return Mock(document=Mock(side_effect=doc_eff))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_eff)
        
        response = client.delete('/api/admin/staff/m1?admin_id=a1')
        assert response.status_code == 400


class TestExactLines418And419:
    """Lines 418-419: if not user_doc.exists: return ..., 404"""
    
    def test_lines_418_419_exact(self, client, setup_firebase_mocks, mock_db):
        """Execute exact lines 418-419"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_exist = Mock(exists=False)
        
        def coll_eff(name):
            if name == "users":
                def doc_eff(doc_id):
                    if doc_id == 'a1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_not_exist))
                return Mock(document=Mock(side_effect=doc_eff))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_eff)
        
        response = client.delete('/api/admin/managers/nonexist?admin_id=a1')
        assert response.status_code == 404


class TestExactLine446:
    """Line 446: return jsonify({"error": "Can only remove managers..."}), 400"""
    
    def test_line_446_exact(self, client, setup_firebase_mocks, mock_db):
        """Execute exact line 446"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_manager = Mock(exists=True, to_dict=lambda: {"role": "staff", "name": "S"})
        
        def coll_eff(name):
            if name == "users":
                def doc_eff(doc_id):
                    if doc_id == 'a1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_not_manager))
                return Mock(document=Mock(side_effect=doc_eff))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_eff)
        
        response = client.delete('/api/admin/managers/s1?admin_id=a1')
        assert response.status_code == 400


class TestExactLines473And474:
    """Lines 473-474: if not user_doc.exists: return ..., 404"""
    
    def test_lines_473_474_exact(self, client, setup_firebase_mocks, mock_db):
        """Execute exact lines 473-474"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_exist = Mock(exists=False)
        
        def coll_eff(name):
            if name == "users":
                def doc_eff(doc_id):
                    if doc_id == 'a1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_not_exist))
                return Mock(document=Mock(side_effect=doc_eff))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_eff)
        
        response = client.put('/api/admin/users/nonexist/role?admin_id=a1', json={'role': 'manager'})
        assert response.status_code == 404


class TestExactLines493And494:
    """Lines 493-494: if new_role not in ["staff", "manager", "admin"]: return ..., 400"""
    
    def test_lines_493_494_exact(self, client, setup_firebase_mocks, mock_db):
        """Execute exact lines 493-494"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=True, to_dict=lambda: {"role": "staff", "name": "U"})
        
        def coll_eff(name):
            if name == "users":
                def doc_eff(doc_id):
                    if doc_id == 'a1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_user))
                return Mock(document=Mock(side_effect=doc_eff))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_eff)
        
        response = client.put('/api/admin/users/u1/role?admin_id=a1', json={'role': 'invalid'})
        assert response.status_code == 400


class TestExactLine521:
    """Line 521: return jsonify({"error": "Cannot change your own role"}), 400"""
    
    def test_line_521_exact(self, client, setup_firebase_mocks, mock_db):
        """Execute exact line 521"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin", "name": "A"})
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.put('/api/admin/users/a1/role?admin_id=a1', json={'role': 'staff'})
        assert response.status_code == 400


class TestExactLines543To549:
    """Lines 543-549: if not user_doc.exists: return ..., 404"""
    
    def test_lines_543_to_549_exact(self, client, setup_firebase_mocks, mock_db):
        """Execute exact lines 543-549"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_exist = Mock(exists=False)
        
        def coll_eff(name):
            if name == "users":
                def doc_eff(doc_id):
                    if doc_id == 'a1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_not_exist))
                return Mock(document=Mock(side_effect=doc_eff))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_eff)
        
        response = client.put('/api/admin/users/nonexist/status?admin_id=a1', json={'is_active': False})
        assert response.status_code == 404


class TestExactLine574:
    """Line 574: return jsonify({"error": "is_active must be true or false"}), 400"""
    
    def test_line_574_exact(self, client, setup_firebase_mocks, mock_db):
        """Execute exact line 574"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=True, to_dict=lambda: {"role": "staff", "name": "U"})
        
        def coll_eff(name):
            if name == "users":
                def doc_eff(doc_id):
                    if doc_id == 'a1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_user))
                return Mock(document=Mock(side_effect=doc_eff))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_eff)
        
        # Send non-boolean value
        response = client.put('/api/admin/users/u1/status?admin_id=a1', json={'is_active': 'yes'})
        assert response.status_code == 400


class TestExactLine630:
    """Line 630: for project_doc in projects_query:"""
    
    def test_line_630_exact(self, client, setup_firebase_mocks, mock_db):
        """Execute exact line 630"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create multiple projects to iterate
        projs = []
        for i in range(5):
            p = Mock(id=f'p{i}')
            p.to_dict = lambda i=i: {'name': f'P{i}'}
            projs.append(p)
        
        def coll_eff(name):
            if name == "users":
                return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))))
            elif name == "projects":
                return Mock(stream=Mock(return_value=projs))
            elif name == "memberships":
                return Mock(where=Mock(return_value=Mock(stream=Mock(return_value=[Mock(), Mock()]))))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_eff)
        
        response = client.get('/api/admin/projects?admin_id=a1')
        assert response.status_code == 200
        assert len(response.get_json()['projects']) == 5


class TestExactLine669:
    """Line 669: for task_doc in tasks_query:"""
    
    def test_line_669_exact(self, client, setup_firebase_mocks, mock_db):
        """Execute exact line 669"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create multiple tasks to iterate
        tasks = []
        for i in range(7):
            t = Mock(id=f't{i}')
            t.to_dict = lambda i=i: {'title': f'T{i}', 'status': 'pending', 'priority': 'high'}
            tasks.append(t)
        
        def coll_eff(name):
            if name == "users":
                return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))))
            elif name == "tasks":
                return Mock(stream=Mock(return_value=tasks))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_eff)
        
        response = client.get('/api/admin/tasks?admin_id=a1')
        assert response.status_code == 200
        assert len(response.get_json()['tasks']) == 7
