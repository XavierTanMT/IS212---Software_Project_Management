from flask import Blueprint, request, jsonify
from models.task_model import TaskModel
from services.recurrence_service import RecurrenceService
from utils.validators import Helpers
from middleware.auth_middleware import AuthMiddleware, RoleMiddleware

# Create blueprint
task_bp = Blueprint('tasks', __name__)

# Initialize models and services
task_model = TaskModel()
recurrence_service = RecurrenceService()

@task_bp.route('/', methods=['GET'])
@AuthMiddleware.verify_token
def get_tasks():
    """Get tasks for current user"""
    try:
        current_user_data = getattr(request, 'current_user_data', None)
        user_id = current_user_data.get('user_id')
        
        # Get query parameters
        task_type = request.args.get('type', 'all')  # all, created, assigned, project
        project_id = request.args.get('project_id')
        include_archived = request.args.get('include_archived', 'false').lower() == 'true'
        
        tasks = []
        
        if task_type == 'created':
            tasks = task_model.get_user_tasks(user_id, include_archived)
        elif task_type == 'assigned':
            tasks = task_model.get_assigned_tasks(user_id, include_archived)
        elif task_type == 'project' and project_id:
            tasks = task_model.get_project_tasks(project_id, include_archived)
        else:
            # Get both created and assigned tasks
            created_tasks = task_model.get_user_tasks(user_id, include_archived)
            assigned_tasks = task_model.get_assigned_tasks(user_id, include_archived)
            
            # Combine and deduplicate
            task_ids = set()
            for task in created_tasks + assigned_tasks:
                if task['task_id'] not in task_ids:
                    tasks.append(task)
                    task_ids.add(task['task_id'])
        
        return jsonify(Helpers.build_success_response(
            data={'tasks': tasks}
        )), 200
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to get tasks: {str(e)}')), 500

@task_bp.route('/', methods=['POST'])
@AuthMiddleware.verify_token
def create_task():
    """Create a new task"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify(Helpers.build_error_response('No data provided')), 400
        
        # Get current user
        current_user_data = getattr(request, 'current_user_data', None)
        user_id = current_user_data.get('user_id')
        
        # Add created_by to task data
        data['created_by'] = user_id
        
        # Create task
        if data.get('recurrence', {}).get('enabled', False):
            # Create recurring task
            task = recurrence_service.create_recurring_task(data)
        else:
            # Create regular task
            task = task_model.create_task(data)
        
        return jsonify(Helpers.build_success_response(
            data={'task': task},
            message='Task created successfully'
        )), 201
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Task creation failed: {str(e)}')), 500

@task_bp.route('/<task_id>', methods=['GET'])
@AuthMiddleware.verify_token
def get_task(task_id):
    """Get specific task"""
    try:
        task = task_model.get_task(task_id)
        
        if not task:
            return jsonify(Helpers.build_error_response('Task not found')), 404
        
        # Check permissions
        if not RoleMiddleware.can_manage_task(task):
            return jsonify(Helpers.build_error_response('Insufficient permissions')), 403
        
        return jsonify(Helpers.build_success_response(
            data={'task': task}
        )), 200
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to get task: {str(e)}')), 500

@task_bp.route('/<task_id>', methods=['PUT'])
@AuthMiddleware.verify_token
def update_task(task_id):
    """Update task"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify(Helpers.build_error_response('No data provided')), 400
        
        # Check if task exists and user can manage it
        task = task_model.get_task(task_id)
        if not task:
            return jsonify(Helpers.build_error_response('Task not found')), 404
        
        if not RoleMiddleware.can_manage_task(task):
            return jsonify(Helpers.build_error_response('Insufficient permissions')), 403
        
        # Update task
        updated_task = task_model.update_task(task_id, data)
        
        return jsonify(Helpers.build_success_response(
            data={'task': updated_task},
            message='Task updated successfully'
        )), 200
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Task update failed: {str(e)}')), 500

@task_bp.route('/<task_id>', methods=['DELETE'])
@AuthMiddleware.verify_token
def delete_task(task_id):
    """Delete task (soft delete)"""
    try:
        # Check if task exists and user can manage it
        task = task_model.get_task(task_id)
        if not task:
            return jsonify(Helpers.build_error_response('Task not found')), 404
        
        if not RoleMiddleware.can_manage_task(task):
            return jsonify(Helpers.build_error_response('Insufficient permissions')), 403
        
        # Delete task
        success = task_model.delete_task(task_id)
        
        if success:
            return jsonify(Helpers.build_success_response(
                message='Task deleted successfully'
            )), 200
        else:
            return jsonify(Helpers.build_error_response('Failed to delete task')), 500
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Task deletion failed: {str(e)}')), 500

@task_bp.route('/<task_id>/subtasks', methods=['POST'])
@AuthMiddleware.verify_token
def create_subtask(task_id):
    """Create subtask"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify(Helpers.build_error_response('No data provided')), 400
        
        # Check if parent task exists and user can manage it
        parent_task = task_model.get_task(task_id)
        if not parent_task:
            return jsonify(Helpers.build_error_response('Parent task not found')), 404
        
        if not RoleMiddleware.can_manage_task(parent_task):
            return jsonify(Helpers.build_error_response('Insufficient permissions')), 403
        
        # Get current user
        current_user_data = getattr(request, 'current_user_data', None)
        user_id = current_user_data.get('user_id')
        
        # Add parent task ID and created_by
        data['parent_task_id'] = task_id
        data['created_by'] = user_id
        
        # Create subtask
        subtask = task_model.create_task(data)
        
        return jsonify(Helpers.build_success_response(
            data={'subtask': subtask},
            message='Subtask created successfully'
        )), 201
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Subtask creation failed: {str(e)}')), 500

@task_bp.route('/<task_id>/subtasks', methods=['GET'])
@AuthMiddleware.verify_token
def get_subtasks(task_id):
    """Get subtasks for a task"""
    try:
        # Check if parent task exists and user can manage it
        parent_task = task_model.get_task(task_id)
        if not parent_task:
            return jsonify(Helpers.build_error_response('Parent task not found')), 404
        
        if not RoleMiddleware.can_manage_task(parent_task):
            return jsonify(Helpers.build_error_response('Insufficient permissions')), 403
        
        # Get subtasks
        subtasks = task_model.get_subtasks(task_id)
        
        return jsonify(Helpers.build_success_response(
            data={'subtasks': subtasks}
        )), 200
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to get subtasks: {str(e)}')), 500

@task_bp.route('/<task_id>/assign', methods=['PUT'])
@AuthMiddleware.verify_token
@RoleMiddleware.require_manager_or_above()
def assign_task(task_id):
    """Assign task to users (manager and above)"""
    try:
        data = request.get_json()
        
        if not data or 'assigned_to' not in data:
            return jsonify(Helpers.build_error_response('assigned_to field required')), 400
        
        # Check if task exists
        task = task_model.get_task(task_id)
        if not task:
            return jsonify(Helpers.build_error_response('Task not found')), 404
        
        # Update assigned users
        updated_task = task_model.update_task(task_id, {'assigned_to': data['assigned_to']})
        
        return jsonify(Helpers.build_success_response(
            data={'task': updated_task},
            message='Task assigned successfully'
        )), 200
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Task assignment failed: {str(e)}')), 500

@task_bp.route('/<task_id>/complete', methods=['PUT'])
@AuthMiddleware.verify_token
def complete_task(task_id):
    """Complete task (handles recurring tasks)"""
    try:
        # Check if task exists and user can manage it
        task = task_model.get_task(task_id)
        if not task:
            return jsonify(Helpers.build_error_response('Task not found')), 404
        
        if not RoleMiddleware.can_manage_task(task):
            return jsonify(Helpers.build_error_response('Insufficient permissions')), 403
        
        # Check if task is recurring
        recurrence = task.get('recurrence', {})
        if recurrence.get('enabled', False):
            # Complete recurring task and create next occurrence
            next_task = recurrence_service.complete_recurring_task(task_id)
            
            response_data = {
                'completed_task': task_model.get_task(task_id),
                'message': 'Recurring task completed'
            }
            
            if next_task:
                response_data['next_task'] = next_task
                response_data['message'] += ' and next occurrence created'
            
            return jsonify(Helpers.build_success_response(
                data=response_data,
                message=response_data['message']
            )), 200
        else:
            # Complete regular task
            updated_task = task_model.update_task(task_id, {'status': 'done'})
            
            return jsonify(Helpers.build_success_response(
                data={'task': updated_task},
                message='Task completed successfully'
            )), 200
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Task completion failed: {str(e)}')), 500

@task_bp.route('/overdue', methods=['GET'])
@AuthMiddleware.verify_token
def get_overdue_tasks():
    """Get overdue tasks"""
    try:
        current_user_data = getattr(request, 'current_user_data', None)
        user_id = current_user_data.get('user_id')
        
        # Get overdue tasks for current user
        overdue_tasks = task_model.get_overdue_tasks(user_id)
        
        return jsonify(Helpers.build_success_response(
            data={'overdue_tasks': overdue_tasks}
        )), 200
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to get overdue tasks: {str(e)}')), 500

@task_bp.route('/<task_id>/recurrence', methods=['PUT'])
@AuthMiddleware.verify_token
def update_recurrence(task_id):
    """Update recurrence settings"""
    try:
        data = request.get_json()
        
        if not data or 'recurrence' not in data:
            return jsonify(Helpers.build_error_response('recurrence data required')), 400
        
        # Check if task exists and user can manage it
        task = task_model.get_task(task_id)
        if not task:
            return jsonify(Helpers.build_error_response('Task not found')), 404
        
        if not RoleMiddleware.can_manage_task(task):
            return jsonify(Helpers.build_error_response('Insufficient permissions')), 403
        
        # Update recurrence settings
        updated_task = recurrence_service.update_recurrence_settings(task_id, data['recurrence'])
        
        return jsonify(Helpers.build_success_response(
            data={'task': updated_task},
            message='Recurrence settings updated successfully'
        )), 200
        
    except ValueError as e:
        return jsonify(Helpers.build_error_response(str(e))), 400
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Recurrence update failed: {str(e)}')), 500
