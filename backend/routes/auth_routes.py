from flask import Blueprint, request, jsonify
from services.auth_service import AuthService
from utils.validators import Helpers
from middleware.auth_middleware import AuthMiddleware

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# Initialize service
auth_service = AuthService()

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify(Helpers.build_error_response('No data provided')), 400
        
        # Required fields
        required_fields = ['user_id', 'email', 'password', 'name']
        for field in required_fields:
            if field not in data:
                return jsonify(Helpers.build_error_response(f'Missing required field: {field}')), 400
        
        # Register user
        result = auth_service.register_user(data)
        
        return jsonify(Helpers.build_success_response(
            data=result,
            message='User registered successfully'
        )), 201
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Registration failed: {str(e)}')), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user (frontend handles Firebase Auth, this verifies token)"""
    try:
        data = request.get_json()
        
        if not data or 'id_token' not in data:
            return jsonify(Helpers.build_error_response('ID token required')), 400
        
        # Verify token and get user data
        result = auth_service.verify_token(data['id_token'])
        
        return jsonify(Helpers.build_success_response(
            data=result,
            message='Login successful'
        )), 200
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Login failed: {str(e)}')), 500

@auth_bp.route('/verify', methods=['POST'])
def verify_token():
    """Verify Firebase ID token"""
    try:
        data = request.get_json()
        
        if not data or 'id_token' not in data:
            return jsonify(Helpers.build_error_response('ID token required')), 400
        
        # Verify token
        result = auth_service.verify_token(data['id_token'])
        
        return jsonify(Helpers.build_success_response(
            data=result,
            message='Token verified successfully'
        )), 200
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Token verification failed: {str(e)}')), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Send password reset email"""
    try:
        data = request.get_json()
        
        if not data or 'email' not in data:
            return jsonify(Helpers.build_error_response('Email required')), 400
        
        result = auth_service.reset_password(data['email'])
        
        return jsonify(Helpers.build_success_response(
            data=result,
            message='Password reset email sent'
        )), 200
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Password reset failed: {str(e)}')), 500

@auth_bp.route('/update-role', methods=['PUT'])
@AuthMiddleware.verify_token
def update_user_role():
    """Update user role (admin only)"""
    try:
        data = request.get_json()
        
        if not data or 'user_id' not in data or 'role' not in data:
            return jsonify(Helpers.build_error_response('user_id and role required')), 400
        
        result = auth_service.update_user_role(data['user_id'], data['role'])
        
        return jsonify(Helpers.build_success_response(
            data=result,
            message='User role updated successfully'
        )), 200
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Role update failed: {str(e)}')), 500

@auth_bp.route('/delete-account', methods=['DELETE'])
@AuthMiddleware.verify_token
def delete_user_account():
    """Delete user account (admin only)"""
    try:
        data = request.get_json()
        
        if not data or 'user_id' not in data:
            return jsonify(Helpers.build_error_response('user_id required')), 400
        
        result = auth_service.delete_user_account(data['user_id'])
        
        return jsonify(Helpers.build_success_response(
            data=result,
            message='User account deleted successfully'
        )), 200
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Account deletion failed: {str(e)}')), 500
