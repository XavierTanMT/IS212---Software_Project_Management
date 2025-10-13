from functools import wraps
from flask import request, jsonify
from firebase_admin import auth as firebase_auth
from utils.validators import Helpers

class AuthMiddleware:
    """Authentication middleware for Firebase JWT tokens"""
    
    @staticmethod
    def verify_token(f):
        """Decorator to verify Firebase JWT token"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = None
            
            # Get token from Authorization header
            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                try:
                    token = auth_header.split(" ")[1]  # Bearer <token>
                except IndexError:
                    return jsonify(Helpers.build_error_response('Invalid token format', 401)), 401
            
            if not token:
                return jsonify(Helpers.build_error_response('Token is missing', 401)), 401
            
            try:
                # Verify Firebase token
                decoded_token = firebase_auth.verify_id_token(token)
                request.current_user = decoded_token
                
                # Fetch user data from Firestore
                from models.user_model import UserModel
                user_model = UserModel()
                try:
                    user_data = user_model.get_user(decoded_token['uid'])
                    request.current_user_data = user_data
                except:
                    # User not found in Firestore, create temporary data
                    request.current_user_data = {
                        'user_id': decoded_token['uid'],
                        'email': decoded_token.get('email', ''),
                        'name': decoded_token.get('name', decoded_token.get('email', '').split('@')[0]),
                        'role': 'staff'  # Default role
                    }
                
                return f(*args, **kwargs)
            except Exception as e:
                return jsonify(Helpers.build_error_response('Invalid token', 401)), 401
        
        return decorated_function
    
    @staticmethod
    def get_current_user():
        """Get current user from request"""
        return getattr(request, 'current_user', None)

class RoleMiddleware:
    """Role-based access control middleware"""
    
    ROLE_HIERARCHY = {
        'staff': 1,
        'manager': 2,
        'director': 3,
        'admin': 4
    }
    
    @staticmethod
    def require_role(required_role: str):
        """Decorator to require specific role or higher"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                current_user = AuthMiddleware.get_current_user()
                
                if not current_user:
                    return jsonify(Helpers.build_error_response('Authentication required', 401)), 401
                
                # Get user role from Firestore
                from models.user_model import UserModel
                user_model = UserModel()
                
                try:
                    user_data = user_model.get_user_by_firebase_uid(current_user['uid'])
                    if not user_data:
                        return jsonify(Helpers.build_error_response('User not found', 404)), 404
                    
                    user_role = user_data.get('role', 'staff')
                    required_level = RoleMiddleware.ROLE_HIERARCHY.get(required_role, 0)
                    user_level = RoleMiddleware.ROLE_HIERARCHY.get(user_role, 0)
                    
                    if user_level < required_level:
                        return jsonify(Helpers.build_error_response('Insufficient permissions', 403)), 403
                    
                    request.current_user_data = user_data
                    return f(*args, **kwargs)
                    
                except Exception as e:
                    return jsonify(Helpers.build_error_response('Role verification failed', 500)), 500
            
            return decorated_function
        return decorator
    
    @staticmethod
    def require_manager_or_above():
        """Require manager role or higher"""
        return RoleMiddleware.require_role('manager')
    
    @staticmethod
    def require_admin():
        """Require admin role"""
        return RoleMiddleware.require_role('admin')
    
    @staticmethod
    def can_manage_user(target_user_id: str):
        """Check if current user can manage target user"""
        current_user_data = getattr(request, 'current_user_data', None)
        
        if not current_user_data:
            # Fallback to Firebase token data
            current_user = getattr(request, 'current_user', None)
            if not current_user:
                return False
            
            # Allow users to access their own dashboard
            if current_user.get('uid') == target_user_id:
                return True
            
            return False
        
        current_role = current_user_data.get('role', 'staff')
        current_user_id = current_user_data.get('user_id')
        
        # Users can always access their own dashboard
        if current_user_id == target_user_id:
            return True
        
        # Admin can manage anyone
        if current_role == 'admin':
            return True
        
        # Manager can manage staff
        if current_role == 'manager':
            # Get target user data to check their role
            from models.user_model import UserModel
            user_model = UserModel()
            try:
                target_user = user_model.get_user(target_user_id)
                if target_user and target_user.get('role') == 'staff':
                    return True
            except:
                pass
        
        # Users can manage themselves
        return current_user_id == target_user_id
    
    @staticmethod
    def can_manage_task(task_data: dict):
        """Check if current user can manage task"""
        current_user_data = getattr(request, 'current_user_data', None)
        
        if not current_user_data:
            return False
        
        current_role = current_user_data.get('role', 'staff')
        current_user_id = current_user_data.get('user_id')
        
        # Admin can manage any task
        if current_role == 'admin':
            return True
        
        # Manager can manage tasks in their projects
        if current_role in ['manager', 'director']:
            # Check if user is project owner or member
            project_id = task_data.get('project_id')
            if project_id:
                from models.project_model import ProjectModel
                project_model = ProjectModel()
                try:
                    project = project_model.get_project(project_id)
                    if project:
                        created_by = project.get('created_by')
                        members = project.get('members', [])
                        return created_by == current_user_id or current_user_id in members
                except:
                    pass
        
        # Users can manage their own tasks
        created_by = task_data.get('created_by')
        assigned_to = task_data.get('assigned_to', [])
        
        return created_by == current_user_id or current_user_id in assigned_to
