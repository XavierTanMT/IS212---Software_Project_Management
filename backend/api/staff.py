# app/routes/staff.py
from flask import request, jsonify
from firebase_admin import firestore
from . import staff_bp
from datetime import datetime, timezone

@staff_bp.route('/dashboard', methods=['GET'])
def get_staff_dashboard():
    """Staff dashboard - only their own tasks"""
    db = firestore.client()
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    
    # Verify user exists
    user_doc = db.collection('users').document(user_id).get()
    if not user_doc.exists:
        return jsonify({'error': 'User not found'}), 404
    
    current_user = user_doc.to_dict()
    current_user['user_id'] = user_id
    
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

@staff_bp.route('/tasks', methods=['GET'])
def get_my_tasks():
    """Get only this staff member's tasks"""
    db = firestore.client()
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    
    # Can only see own tasks
    tasks = []
    my_tasks = db.collection('tasks').where('created_by.user_id', '==', user_id).stream()
    
    for task_doc in my_tasks:
        task_data = task_doc.to_dict()
        task_data['task_id'] = task_doc.id
        tasks.append(task_data)
    
    return jsonify({'tasks': tasks}), 200

@staff_bp.route('/tasks', methods=['POST'])
def create_task():
    """Staff creates their own task"""
    db = firestore.client()
    data = request.get_json()
    
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    
    # Get user info
    user_doc = db.collection('users').document(user_id).get()
    if not user_doc.exists:
        return jsonify({'error': 'User not found'}), 404
    
    user_data = user_doc.to_dict()
    
    task_data = {
        'title': data.get('title'),
        'description': data.get('description', ''),
        'priority': data.get('priority', 5),
        'status': data.get('status', 'To Do'),
        'due_date': data.get('due_date'),
        'created_by': {
            'user_id': user_id,
            'name': user_data.get('name'),
            'email': user_data.get('email')
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