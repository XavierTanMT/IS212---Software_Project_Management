from flask import Blueprint, request, jsonify
from models.user_model import UserModel
from utils.validators import Helpers
from middleware.auth_middleware import AuthMiddleware, RoleMiddleware

# Create blueprint
user_bp = Blueprint('users', __name__)

# Initialize model
user_model = UserModel()

@user_bp.route('/', methods=['POST'])
def create_user():
    """Create a new user (admin only)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify(Helpers.build_error_response('No data provided')), 400
        
        # Create user
        user = user_model.create_user(data)
        
        return jsonify(Helpers.build_success_response(
            data={'user': user},
            message='User created successfully'
        )), 201
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'User creation failed: {str(e)}')), 500

@user_bp.route('/<user_id>', methods=['GET'])
@AuthMiddleware.verify_token
def get_user(user_id):
    """Get user by ID"""
    try:
        # Check permissions
        current_user_data = getattr(request, 'current_user_data', None)
        if not RoleMiddleware.can_manage_user(user_id):
            return jsonify(Helpers.build_error_response('Insufficient permissions')), 403
        
        user = user_model.get_user(user_id)
        
        if not user:
            return jsonify(Helpers.build_error_response('User not found')), 404
        
        return jsonify(Helpers.build_success_response(
            data={'user': user}
        )), 200
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to get user: {str(e)}')), 500

@user_bp.route('/<user_id>', methods=['PUT'])
@AuthMiddleware.verify_token
def update_user(user_id):
    """Update user data"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify(Helpers.build_error_response('No data provided')), 400
        
        # Check permissions
        current_user_data = getattr(request, 'current_user_data', None)
        if not RoleMiddleware.can_manage_user(user_id):
            return jsonify(Helpers.build_error_response('Insufficient permissions')), 403
        
        # Update user
        user = user_model.update_user(user_id, data)
        
        return jsonify(Helpers.build_success_response(
            data={'user': user},
            message='User updated successfully'
        )), 200
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'User update failed: {str(e)}')), 500

@user_bp.route('/<user_id>', methods=['DELETE'])
@AuthMiddleware.verify_token
@RoleMiddleware.require_admin()
def delete_user(user_id):
    """Delete user (admin only)"""
    try:
        # Check if user exists
        user = user_model.get_user(user_id)
        if not user:
            return jsonify(Helpers.build_error_response('User not found')), 404
        
        # Delete user
        success = user_model.delete_user(user_id)
        
        if success:
            return jsonify(Helpers.build_success_response(
                message='User deleted successfully'
            )), 200
        else:
            return jsonify(Helpers.build_error_response('Failed to delete user')), 500
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'User deletion failed: {str(e)}')), 500

@user_bp.route('/<user_id>/dashboard', methods=['GET'])
@AuthMiddleware.verify_token
def get_user_dashboard(user_id):
    """Get user dashboard data"""
    try:
        # Get current user from Firebase token
        current_user = getattr(request, 'current_user', None)
        if not current_user:
            return jsonify(Helpers.build_error_response('Authentication required')), 401
        
        # Allow users to access their own dashboard
        if current_user.get('uid') != user_id:
            return jsonify(Helpers.build_error_response('Can only access your own dashboard')), 403
        
        # Get user data from Firestore (create if doesn't exist)
        user = user_model.get_user(user_id)
        if not user:
            # Create user in Firestore if they don't exist
            user_data = {
                'user_id': user_id,
                'email': current_user.get('email', ''),
                'name': current_user.get('name', current_user.get('email', '').split('@')[0]),
                'role': 'staff'
            }
            user = user_model.create_user(user_data)
        
        # Import task model for dashboard data
        from models.task_model import TaskModel
        task_model = TaskModel()
        
        # Get dashboard statistics
        dashboard_data = task_model.get_user_dashboard_data(user_id)
        
        return jsonify(Helpers.build_success_response(
            data=dashboard_data
        )), 200
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to get dashboard data: {str(e)}')), 500

@user_bp.route('/role/<role>', methods=['GET'])
@AuthMiddleware.verify_token
@RoleMiddleware.require_manager_or_above()
def get_users_by_role(role):
    """Get users by role (manager and above)"""
    try:
        users = user_model.get_users_by_role(role)
        
        return jsonify(Helpers.build_success_response(
            data={'users': users}
        )), 200
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to get users by role: {str(e)}')), 500

@user_bp.route('/team/<manager_id>', methods=['GET'])
@AuthMiddleware.verify_token
def get_team_members(manager_id):
    """Get team members for a manager"""
    try:
        # Check permissions
        current_user_data = getattr(request, 'current_user_data', None)
        if not RoleMiddleware.can_manage_user(manager_id):
            return jsonify(Helpers.build_error_response('Insufficient permissions')), 403
        
        team_members = user_model.get_team_members(manager_id)
        
        return jsonify(Helpers.build_success_response(
            data={'team_members': team_members}
        )), 200
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to get team members: {str(e)}')), 500

@user_bp.route('/all', methods=['GET'])
@AuthMiddleware.verify_token
@RoleMiddleware.require_admin()
def get_all_users():
    """Get all users (admin only)"""
    try:
        limit = request.args.get('limit', 100, type=int)
        users = user_model.get_all_users(limit)
        
        return jsonify(Helpers.build_success_response(
            data={'users': users}
        )), 200
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to get all users: {str(e)}')), 500
