from flask import Flask, request, jsonify
from flask_cors import CORS
from user import User, setup_database
from task import Task, Priority, Status, setup_tasks_table
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# ================================
# DATABASE RESET ON STARTUP
# ================================
def reset_database():
    """Delete existing database and recreate fresh tables"""
    db_path = 'task_manager.db'
    
    # Delete existing database file if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print("🗑️  Deleted existing database")
    
    # Recreate fresh database tables
    setup_database()
    setup_tasks_table()
    print("✅ Created fresh database tables")

# Reset database on startup
reset_database()


# ================================
# HOME & INFO ENDPOINTS
# ================================

@app.route('/')
def home():
    """Home endpoint to test if API is running"""
    return jsonify({
        'message': 'Task Manager API is running!',
        'version': '1.0.0',
        'endpoints': {
            'users': {
                'GET /api/users': 'Get all users',
                'POST /api/users': 'Create new user',
                'GET /api/users/<user_id>': 'Get specific user',
                'PUT /api/users/<user_id>': 'Update user',
                'DELETE /api/users/<user_id>': 'Delete user'
            },
            'tasks': {
                'GET /api/tasks': 'Get all tasks',
                'POST /api/tasks': 'Create new task',
                'GET /api/tasks/<task_id>': 'Get specific task',
                'PUT /api/tasks/<task_id>': 'Update task',
                'DELETE /api/tasks/<task_id>': 'Delete task'
            },
            'relationships': {
                'GET /api/users/<user_id>/tasks': 'Get tasks created by user',
                'GET /api/users/<user_id>/assigned-tasks': 'Get tasks assigned to user',
                'PUT /api/tasks/<task_id>/assign': 'Assign task to user'
            }
        }
    })

# ================================
# USER ENDPOINTS
# ================================

@app.route('/api/users', methods=['GET'])
def get_all_users():
    """Get all users"""
    try:
        users = User.find_all()
        return jsonify({
            'users': [user.to_dict() for user in users],
            'count': len(users)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get specific user by ID"""
    try:
        user = User.find_by_id(user_id)
        if user:
            return jsonify(user.to_dict()), 200
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user"""
    try:
        # Get JSON data from request
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['user_id', 'name', 'email']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if user already exists
        existing_user = User.find_by_id(data['user_id'])
        if existing_user:
            return jsonify({'error': 'User already exists'}), 409
        
        # Create new user
        user = User(
            user_id=data['user_id'],
            name=data['name'],
            email=data['email']
        )
        
        # Save to database
        user.save()
        
        return jsonify({
            'message': 'User created successfully',
            'user': user.to_dict()
        }), 201
        
    except sqlite3.IntegrityError as e:
        if 'UNIQUE constraint failed: users.email' in str(e):
            return jsonify({'error': 'Email already exists'}), 409
        return jsonify({'error': 'Database integrity error'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    """Update an existing user"""
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Find existing user
        user = User.find_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update fields if provided
        if 'name' in data:
            user.update_name(data['name'])
        
        if 'email' in data:
            user.update_email(data['email'])
        
        # Save changes
        user.save()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
        
    except sqlite3.IntegrityError as e:
        if 'UNIQUE constraint failed: users.email' in str(e):
            return jsonify({'error': 'Email already exists'}), 409
        return jsonify({'error': 'Database integrity error'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user"""
    try:
        # Find user first
        user = User.find_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Delete from database
        user.delete()
        
        return jsonify({
            'message': 'User deleted successfully',
            'deleted_user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================================
# TASK ENDPOINTS
# ================================

@app.route('/api/tasks', methods=['GET'])
def get_all_tasks():
    """Get all tasks"""
    try:
        tasks = Task.find_all()
        return jsonify({
            'tasks': [task.to_dict() for task in tasks],
            'count': len(tasks)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """Get specific task by ID"""
    try:
        task = Task.find_by_id(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        return jsonify(task.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    try:
        # Get JSON data from request
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['title', 'description', 'created_by_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Get creator user
        creator = User.find_by_id(data['created_by_id'])
        if not creator:
            return jsonify({'error': 'Creator user not found'}), 404
        
        # Get assigned user if specified
        assigned_to = None
        if data.get('assigned_to_id'):
            assigned_to = User.find_by_id(data['assigned_to_id'])
            if not assigned_to:
                return jsonify({'error': 'Assigned user not found'}), 404
        
        # Parse due_date if provided
        due_date = None
        if data.get('due_date'):
            try:
                due_date = datetime.fromisoformat(data['due_date'])
            except ValueError:
                return jsonify({'error': 'Invalid due_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
        
        # Create task
        task = Task(
            title=data['title'],
            description=data['description'],
            created_by=creator,
            priority=Priority(data.get('priority', 'Medium')),
            due_date=due_date,
            assigned_to=assigned_to,
            status=Status(data.get('status', 'To Do'))
        )
        
        # Save to database
        task.save()
        
        return jsonify({
            'message': 'Task created successfully',
            'task': task.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    """Update an existing task"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        task = Task.find_by_id(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Update fields if provided
        if 'title' in data:
            task.update_title(data['title'])
        
        if 'description' in data:
            task.update_description(data['description'])
        
        if 'priority' in data:
            task.update_priority(Priority(data['priority']))
        
        if 'status' in data:
            task.update_status(Status(data['status']))
        
        if 'due_date' in data:
            if data['due_date']:
                try:
                    task.update_due_date(datetime.fromisoformat(data['due_date']))
                except ValueError:
                    return jsonify({'error': 'Invalid due_date format'}), 400
            else:
                task.due_date = None
                task.updated_at = datetime.now()
        
        if 'notes' in data:
            task.add_note(data['notes'])
        
        # Handle assignment change
        if 'assigned_to_id' in data:
            if data['assigned_to_id']:
                assigned_user = User.find_by_id(data['assigned_to_id'])
                if not assigned_user:
                    return jsonify({'error': 'Assigned user not found'}), 404
                task.assign_to_user(assigned_user)
            else:
                task.assigned_to = None
                task.updated_at = datetime.now()
        
        # Save changes
        task.save()
        
        return jsonify({
            'message': 'Task updated successfully',
            'task': task.to_dict()
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task"""
    try:
        task = Task.find_by_id(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        task.delete()
        
        return jsonify({
            'message': 'Task deleted successfully',
            'deleted_task': task.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================================
# RELATIONSHIP ENDPOINTS
# ================================

@app.route('/api/users/<user_id>/tasks', methods=['GET'])
def get_user_created_tasks(user_id):
    """Get all tasks created by a user"""
    try:
        # Check if user exists
        user = User.find_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        tasks = Task.find_by_creator(user_id)
        return jsonify({
            'user': user.to_dict(),
            'created_tasks': [task.to_dict() for task in tasks],
            'count': len(tasks)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<user_id>/assigned-tasks', methods=['GET'])
def get_user_assigned_tasks(user_id):
    """Get all tasks assigned to a user"""
    try:
        # Check if user exists
        user = User.find_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        tasks = Task.find_by_assignee(user_id)
        return jsonify({
            'user': user.to_dict(),
            'assigned_tasks': [task.to_dict() for task in tasks],
            'count': len(tasks)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<task_id>/assign', methods=['PUT'])
def assign_task(task_id):
    """Assign or reassign a task to a user"""
    try:
        data = request.get_json()
        if not data or 'user_id' not in data:
            return jsonify({'error': 'user_id required'}), 400
        
        # Get task
        task = Task.find_by_id(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Get user to assign to
        user = User.find_by_id(data['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Assign task
        task.assign_to_user(user)
        task.save()
        
        return jsonify({
            'message': f'Task assigned to {user.name}',
            'task': task.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<task_id>/unassign', methods=['PUT'])
def unassign_task(task_id):
    """Remove assignment from a task"""
    try:
        task = Task.find_by_id(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        task.assigned_to = None
        task.updated_at = datetime.now()
        task.save()
        
        return jsonify({
            'message': 'Task unassigned',
            'task': task.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================================
# FILTERING ENDPOINTS
# ================================

@app.route('/api/tasks/filter', methods=['GET'])
def filter_tasks():
    """Filter tasks by status, priority, etc."""
    try:
        status = request.args.get('status')
        priority = request.args.get('priority')
        
        if status:
            tasks = Task.find_by_status(Status(status))
        elif priority:
            tasks = Task.find_by_priority(Priority(priority))
        else:
            tasks = Task.find_all()
        
        return jsonify({
            'tasks': [task.to_dict() for task in tasks],
            'count': len(tasks),
            'filters': {
                'status': status,
                'priority': priority
            }
        }), 200
        
    except ValueError as e:
        return jsonify({'error': f'Invalid filter value: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================================
# DASHBOARD ENDPOINT
# ================================

@app.route('/api/users/<user_id>/dashboard', methods=['GET'])
def get_user_dashboard(user_id):
    """Get comprehensive dashboard data for a user"""
    try:
        user = User.find_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get user's tasks
        created_tasks = Task.find_by_creator(user_id)
        assigned_tasks = Task.find_by_assignee(user_id)
        
        # Calculate statistics
        total_created = len(created_tasks)
        total_assigned = len(assigned_tasks)
        
        # Status breakdown for assigned tasks
        status_counts = {}
        for status in Status:
            status_counts[status.value] = len([t for t in assigned_tasks if t.status == status])
        
        # Priority breakdown for assigned tasks
        priority_counts = {}
        for priority in Priority:
            priority_counts[priority.value] = len([t for t in assigned_tasks if t.priority == priority])
        
        # Overdue tasks
        now = datetime.now()
        overdue_tasks = [t for t in assigned_tasks if t.due_date and t.due_date < now and t.status != Status.COMPLETED]
        
        return jsonify({
            'user': user.to_dict(),
            'statistics': {
                'total_created': total_created,
                'total_assigned': total_assigned,
                'overdue_count': len(overdue_tasks),
                'status_breakdown': status_counts,
                'priority_breakdown': priority_counts
            },
            'recent_created_tasks': [t.to_dict() for t in created_tasks[:5]],
            'recent_assigned_tasks': [t.to_dict() for t in assigned_tasks[:5]],
            'overdue_tasks': [t.to_dict() for t in overdue_tasks]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================================
# ERROR HANDLERS
# ================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ================================
# MAIN
# ================================

if __name__ == '__main__':
    print("🚀 Starting Task Manager API...")
    print("📍 Server running at: http://localhost:5000")
    print("📖 API documentation at: http://localhost:5000")
    print("💾 Database: task_manager.db")
    app.run(debug=True, host='0.0.0.0', port=5000)