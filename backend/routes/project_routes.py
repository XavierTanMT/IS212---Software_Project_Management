from flask import Blueprint, request, jsonify
from models.project_model import ProjectModel
from utils.validators import Helpers
from middleware.auth_middleware import AuthMiddleware, RoleMiddleware

# Create blueprint
project_bp = Blueprint('projects', __name__)

# Initialize model
project_model = ProjectModel()

@project_bp.route('/', methods=['GET'])
@AuthMiddleware.verify_token
def get_projects():
    """Get projects for current user"""
    try:
        current_user_data = getattr(request, 'current_user_data', None)
        user_id = current_user_data.get('user_id')
        
        # Get user's projects
        projects = project_model.get_user_projects(user_id)
        
        return jsonify(Helpers.build_success_response(
            data={'projects': projects}
        )), 200
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to get projects: {str(e)}')), 500

@project_bp.route('/', methods=['POST'])
@AuthMiddleware.verify_token
def create_project():
    """Create a new project"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify(Helpers.build_error_response('No data provided')), 400
        
        # Get current user
        current_user_data = getattr(request, 'current_user_data', None)
        user_id = current_user_data.get('user_id')
        
        # Add created_by to project data
        data['created_by'] = user_id
        
        # Create project
        project = project_model.create_project(data)
        
        return jsonify(Helpers.build_success_response(
            data={'project': project},
            message='Project created successfully'
        )), 201
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Project creation failed: {str(e)}')), 500

@project_bp.route('/<project_id>', methods=['GET'])
@AuthMiddleware.verify_token
def get_project(project_id):
    """Get specific project"""
    try:
        project = project_model.get_project(project_id)
        
        if not project:
            return jsonify(Helpers.build_error_response('Project not found')), 404
        
        # Check if user has access to project
        current_user_data = getattr(request, 'current_user_data', None)
        user_id = current_user_data.get('user_id')
        
        if (project.get('created_by') != user_id and 
            user_id not in project.get('members', [])):
            return jsonify(Helpers.build_error_response('Insufficient permissions')), 403
        
        return jsonify(Helpers.build_success_response(
            data={'project': project}
        )), 200
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to get project: {str(e)}')), 500

@project_bp.route('/<project_id>', methods=['PUT'])
@AuthMiddleware.verify_token
def update_project(project_id):
    """Update project"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify(Helpers.build_error_response('No data provided')), 400
        
        # Check if project exists and user can manage it
        project = project_model.get_project(project_id)
        if not project:
            return jsonify(Helpers.build_error_response('Project not found')), 404
        
        # Check permissions (only creator can update)
        current_user_data = getattr(request, 'current_user_data', None)
        user_id = current_user_data.get('user_id')
        
        if project.get('created_by') != user_id:
            return jsonify(Helpers.build_error_response('Only project creator can update project')), 403
        
        # Update project
        updated_project = project_model.update_project(project_id, data)
        
        return jsonify(Helpers.build_success_response(
            data={'project': updated_project},
            message='Project updated successfully'
        )), 200
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Project update failed: {str(e)}')), 500

@project_bp.route('/<project_id>', methods=['DELETE'])
@AuthMiddleware.verify_token
def delete_project(project_id):
    """Delete project"""
    try:
        # Check if project exists and user can manage it
        project = project_model.get_project(project_id)
        if not project:
            return jsonify(Helpers.build_error_response('Project not found')), 404
        
        # Check permissions (only creator can delete)
        current_user_data = getattr(request, 'current_user_data', None)
        user_id = current_user_data.get('user_id')
        
        if project.get('created_by') != user_id:
            return jsonify(Helpers.build_error_response('Only project creator can delete project')), 403
        
        # Delete project
        success = project_model.delete_project(project_id)
        
        if success:
            return jsonify(Helpers.build_success_response(
                message='Project deleted successfully'
            )), 200
        else:
            return jsonify(Helpers.build_error_response('Failed to delete project')), 500
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Project deletion failed: {str(e)}')), 500

@project_bp.route('/<project_id>/members', methods=['POST'])
@AuthMiddleware.verify_token
def add_member(project_id):
    """Add member to project"""
    try:
        data = request.get_json()
        
        if not data or 'user_id' not in data:
            return jsonify(Helpers.build_error_response('user_id required')), 400
        
        # Check if project exists and user can manage it
        project = project_model.get_project(project_id)
        if not project:
            return jsonify(Helpers.build_error_response('Project not found')), 404
        
        # Check permissions (only creator can add members)
        current_user_data = getattr(request, 'current_user_data', None)
        user_id = current_user_data.get('user_id')
        
        if project.get('created_by') != user_id:
            return jsonify(Helpers.build_error_response('Only project creator can add members')), 403
        
        # Add member
        updated_project = project_model.add_member(project_id, data['user_id'])
        
        return jsonify(Helpers.build_success_response(
            data={'project': updated_project},
            message='Member added successfully'
        )), 200
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to add member: {str(e)}')), 500

@project_bp.route('/<project_id>/members/<member_id>', methods=['DELETE'])
@AuthMiddleware.verify_token
def remove_member(project_id, member_id):
    """Remove member from project"""
    try:
        # Check if project exists and user can manage it
        project = project_model.get_project(project_id)
        if not project:
            return jsonify(Helpers.build_error_response('Project not found')), 404
        
        # Check permissions (only creator can remove members)
        current_user_data = getattr(request, 'current_user_data', None)
        user_id = current_user_data.get('user_id')
        
        if project.get('created_by') != user_id:
            return jsonify(Helpers.build_error_response('Only project creator can remove members')), 403
        
        # Remove member
        updated_project = project_model.remove_member(project_id, member_id)
        
        return jsonify(Helpers.build_success_response(
            data={'project': updated_project},
            message='Member removed successfully'
        )), 200
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to remove member: {str(e)}')), 500

@project_bp.route('/<project_id>/members', methods=['GET'])
@AuthMiddleware.verify_token
def get_project_members(project_id):
    """Get project members"""
    try:
        # Check if project exists and user has access
        project = project_model.get_project(project_id)
        if not project:
            return jsonify(Helpers.build_error_response('Project not found')), 404
        
        # Check if user has access to project
        current_user_data = getattr(request, 'current_user_data', None)
        user_id = current_user_data.get('user_id')
        
        if (project.get('created_by') != user_id and 
            user_id not in project.get('members', [])):
            return jsonify(Helpers.build_error_response('Insufficient permissions')), 403
        
        # Get members
        members = project_model.get_project_members(project_id)
        
        return jsonify(Helpers.build_success_response(
            data={'members': members}
        )), 200
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to get project members: {str(e)}')), 500

@project_bp.route('/<project_id>/statistics', methods=['GET'])
@AuthMiddleware.verify_token
def get_project_statistics(project_id):
    """Get project statistics"""
    try:
        # Check if project exists and user has access
        project = project_model.get_project(project_id)
        if not project:
            return jsonify(Helpers.build_error_response('Project not found')), 404
        
        # Check if user has access to project
        current_user_data = getattr(request, 'current_user_data', None)
        user_id = current_user_data.get('user_id')
        
        if (project.get('created_by') != user_id and 
            user_id not in project.get('members', [])):
            return jsonify(Helpers.build_error_response('Insufficient permissions')), 403
        
        # Get statistics
        statistics = project_model.get_project_statistics(project_id)
        
        return jsonify(Helpers.build_success_response(
            data=statistics
        )), 200
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to get project statistics: {str(e)}')), 500

@project_bp.route('/<project_id>/tasks', methods=['GET'])
@AuthMiddleware.verify_token
def get_project_tasks(project_id):
    """Get tasks for a project"""
    try:
        # Check if project exists and user has access
        project = project_model.get_project(project_id)
        if not project:
            return jsonify(Helpers.build_error_response('Project not found')), 404
        
        # Check if user has access to project
        current_user_data = getattr(request, 'current_user_data', None)
        user_id = current_user_data.get('user_id')
        
        if (project.get('created_by') != user_id and 
            user_id not in project.get('members', [])):
            return jsonify(Helpers.build_error_response('Insufficient permissions')), 403
        
        # Get tasks
        from models.task_model import TaskModel
        task_model = TaskModel()
        
        include_archived = request.args.get('include_archived', 'false').lower() == 'true'
        tasks = task_model.get_project_tasks(project_id, include_archived)
        
        return jsonify(Helpers.build_success_response(
            data={'tasks': tasks}
        )), 200
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to get project tasks: {str(e)}')), 500

@project_bp.route('/all', methods=['GET'])
@AuthMiddleware.verify_token
@RoleMiddleware.require_admin()
def get_all_projects():
    """Get all projects (admin only)"""
    try:
        limit = request.args.get('limit', 100, type=int)
        projects = project_model.get_all_projects(limit)
        
        return jsonify(Helpers.build_success_response(
            data={'projects': projects}
        )), 200
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to get all projects: {str(e)}')), 500
