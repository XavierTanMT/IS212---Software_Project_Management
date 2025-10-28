# app/routes/staff.py
from flask import Blueprint, request, jsonify
from firebase_admin import firestore
from .auth import firebase_required, staff_only
from datetime import datetime, timezone

bp = Blueprint('staff', __name__)

@bp.route('/dashboard', methods=['GET'])
@firebase_required
def get_staff_dashboard(current_user):
    """Staff dashboard - only their own tasks"""
    db = firestore.client()
    user_id = current_user['user_id']
    
    # Get tasks created by this staff member
    my_tasks_query = db.collection('tasks').where('created_by.user_id', '==', user_id).stream()
    my_tasks = []
    for task_doc in my_tasks_query:
        task_data = task_doc.to_dict()
        task_data['task_id'] = task_doc.id
        my_tasks.append(task_data)
    
    # Get tasks assigned to this staff member
    assigned_tasks_query = db.collection('tasks').where('assigned_to.user_id', '==', user_id).stream()
    assigned_tasks = []
    for task_doc in assigned_tasks_query:
        task_data = task_doc.to_dict()
        task_data['task_id'] = task_doc.id
        assigned_tasks.append(task_data)
    
    # Get projects this staff is part of
    memberships = db.collection('memberships').where('user_id', '==', user_id).stream()
    project_ids = [mem.to_dict().get('project_id') for mem in memberships]
    
    projects = []
    for project_id in project_ids:
        project_doc = db.collection('projects').document(project_id).get()
        if project_doc.exists:
            project_data = project_doc.to_dict()
            project_data['project_id'] = project_id
            projects.append(project_data)
    
    return jsonify({
        'view': 'staff',
        'user': current_user,
        'my_tasks': my_tasks,
        'assigned_tasks': assigned_tasks,
        'projects': projects,
        'statistics': {
            'total_tasks': len(my_tasks) + len(assigned_tasks),
            'my_tasks_count': len(my_tasks),
            'assigned_tasks_count': len(assigned_tasks),
            'projects_count': len(projects)
        }
    }), 200

@bp.route('/tasks', methods=['GET'])
@firebase_required
def get_my_tasks(current_user):
    """Get only this staff member's tasks"""
    db = firestore.client()
    user_id = current_user['user_id']
    
    # Can only see own tasks
    tasks = []
    my_tasks = db.collection('tasks').where('created_by.user_id', '==', user_id).stream()
    
    for task_doc in my_tasks:
        task_data = task_doc.to_dict()
        task_data['task_id'] = task_doc.id
        tasks.append(task_data)
    
    return jsonify({'tasks': tasks}), 200

@bp.route('/tasks', methods=['POST'])
@firebase_required
def create_task(current_user):
    """Staff creates their own task"""
    db = firestore.client()
    data = request.get_json()
    
    task_data = {
        'title': data.get('title'),
        'description': data.get('description', ''),
        'priority': data.get('priority', 5),
        'status': data.get('status', 'To Do'),
        'due_date': data.get('due_date'),
        'created_by': {
            'user_id': current_user['user_id'],
            'name': current_user['name'],
            'email': current_user['email']
        },
        'assigned_to': data.get('assigned_to', {}),
        'project_id': data.get('project_id'),
        'labels': data.get('labels', []),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    
    task_ref = db.collection('tasks').add(task_data)
    
    return jsonify({
        'success': True,
        'task_id': task_ref[1].id,
        'message': 'Task created successfully'
    }), 201