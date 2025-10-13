from config.firebase_config import db
from utils.validators import Validators, Helpers
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

class TaskModel:
    """Task data model for Firestore operations"""
    
    def __init__(self):
        self.collection = db.collection('tasks')
    
    def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task"""
        try:
            # Validate required fields
            if not Validators.validate_task_title(task_data.get('title', '')):
                raise ValueError('Invalid task title (3-100 characters required)')
            
            if not Validators.validate_task_description(task_data.get('description', '')):
                raise ValueError('Invalid task description (10-500 characters required)')
            
            if not Validators.validate_priority_bucket(task_data.get('priority_bucket', 5)):
                raise ValueError('Invalid priority bucket (1-10 required)')
            
            if not Validators.validate_status(task_data.get('status', 'todo')):
                raise ValueError('Invalid status')
            
            # Generate task ID
            task_id = Helpers.generate_id()
            
            # Prepare task document
            task_doc = {
                'task_id': task_id,
                'title': Helpers.sanitize_string(task_data['title']),
                'description': Helpers.sanitize_string(task_data['description']),
                'status': task_data.get('status', 'todo'),
                'priority_bucket': task_data.get('priority_bucket', 5),
                'due_date': Helpers.parse_timestamp(task_data.get('due_date')) if task_data.get('due_date') else None,
                'created_by': task_data['created_by'],
                'assigned_to': task_data.get('assigned_to', []),
                'project_id': task_data.get('project_id'),
                'parent_task_id': task_data.get('parent_task_id'),  # For subtasks
                'tags': task_data.get('tags', []),
                'is_archived': False,
                'archived_at': None,
                'archived_by_id': None,
                'created_at': Helpers.get_current_timestamp(),
                'updated_at': Helpers.get_current_timestamp()
            }
            
            # Handle recurrence (NEW requirement)
            if task_data.get('recurrence', {}).get('enabled', False):
                recurrence_data = task_data['recurrence']
                if not Validators.validate_recurrence_frequency(recurrence_data.get('frequency', '')):
                    raise ValueError('Invalid recurrence frequency')
                
                task_doc['recurrence'] = {
                    'enabled': True,
                    'frequency': recurrence_data['frequency'],
                    'interval': recurrence_data.get('interval', 1),
                    'end_date': Helpers.parse_timestamp(recurrence_data.get('end_date')) if recurrence_data.get('end_date') else None,
                    'next_occurrence': None  # Will be calculated when task is completed
                }
            else:
                task_doc['recurrence'] = {
                    'enabled': False,
                    'frequency': None,
                    'interval': None,
                    'end_date': None,
                    'next_occurrence': None
                }
            
            # Create document in Firestore
            doc_ref = self.collection.document(task_id)
            doc_ref.set(task_doc)
            
            # Return created task data
            return self.get_task(task_id)
            
        except Exception as e:
            raise Exception(f"Failed to create task: {str(e)}")
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by task_id"""
        try:
            doc_ref = self.collection.document(task_id)
            doc = doc_ref.get()
            
            if doc.exists:
                task_data = doc.to_dict()
                # Convert Firestore timestamps to ISO strings
                for field in ['created_at', 'updated_at', 'due_date', 'archived_at']:
                    if field in task_data and task_data[field]:
                        task_data[field] = Helpers.format_timestamp(task_data[field])
                
                # Handle recurrence end_date
                if 'recurrence' in task_data and task_data['recurrence'].get('end_date'):
                    task_data['recurrence']['end_date'] = Helpers.format_timestamp(task_data['recurrence']['end_date'])
                
                return task_data
            return None
            
        except Exception as e:
            raise Exception(f"Failed to get task: {str(e)}")
    
    def update_task(self, task_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update task data"""
        try:
            # Check if task exists
            if not self.get_task(task_id):
                raise ValueError('Task not found')
            
            # Validate fields if provided
            if 'title' in update_data and not Validators.validate_task_title(update_data['title']):
                raise ValueError('Invalid task title (3-100 characters required)')
            
            if 'description' in update_data and not Validators.validate_task_description(update_data['description']):
                raise ValueError('Invalid task description (10-500 characters required)')
            
            if 'priority_bucket' in update_data and not Validators.validate_priority_bucket(update_data['priority_bucket']):
                raise ValueError('Invalid priority bucket (1-10 required)')
            
            if 'status' in update_data and not Validators.validate_status(update_data['status']):
                raise ValueError('Invalid status')
            
            # Prepare update data
            update_doc = {
                'updated_at': Helpers.get_current_timestamp()
            }
            
            # Add validated fields
            if 'title' in update_data:
                update_doc['title'] = Helpers.sanitize_string(update_data['title'])
            
            if 'description' in update_data:
                update_doc['description'] = Helpers.sanitize_string(update_data['description'])
            
            if 'status' in update_data:
                update_doc['status'] = update_data['status']
            
            if 'priority_bucket' in update_data:
                update_doc['priority_bucket'] = update_data['priority_bucket']
            
            if 'due_date' in update_data:
                update_doc['due_date'] = Helpers.parse_timestamp(update_data['due_date']) if update_data['due_date'] else None
            
            if 'assigned_to' in update_data:
                update_doc['assigned_to'] = update_data['assigned_to']
            
            if 'project_id' in update_data:
                update_doc['project_id'] = update_data['project_id']
            
            if 'tags' in update_data:
                update_doc['tags'] = update_data['tags']
            
            # Handle recurrence updates
            if 'recurrence' in update_data:
                recurrence_data = update_data['recurrence']
                if recurrence_data.get('enabled', False):
                    if not Validators.validate_recurrence_frequency(recurrence_data.get('frequency', '')):
                        raise ValueError('Invalid recurrence frequency')
                    
                    update_doc['recurrence'] = {
                        'enabled': True,
                        'frequency': recurrence_data['frequency'],
                        'interval': recurrence_data.get('interval', 1),
                        'end_date': Helpers.parse_timestamp(recurrence_data.get('end_date')) if recurrence_data.get('end_date') else None,
                        'next_occurrence': None
                    }
                else:
                    update_doc['recurrence'] = {
                        'enabled': False,
                        'frequency': None,
                        'interval': None,
                        'end_date': None,
                        'next_occurrence': None
                    }
            
            # Update document
            doc_ref = self.collection.document(task_id)
            doc_ref.update(update_doc)
            
            return self.get_task(task_id)
            
        except Exception as e:
            raise Exception(f"Failed to update task: {str(e)}")
    
    def delete_task(self, task_id: str) -> bool:
        """Delete task (soft delete by archiving)"""
        try:
            task_data = self.get_task(task_id)
            if not task_data:
                raise ValueError('Task not found')
            
            # Soft delete by archiving
            update_data = {
                'is_archived': True,
                'archived_at': Helpers.get_current_timestamp(),
                'archived_by_id': task_data.get('created_by')  # You might want to get this from current user
            }
            
            self.update_task(task_id, update_data)
            return True
            
        except Exception as e:
            raise Exception(f"Failed to delete task: {str(e)}")
    
    def get_user_tasks(self, user_id: str, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Get tasks for a specific user"""
        try:
            query = self.collection.where('created_by', '==', user_id)
            
            if not include_archived:
                query = query.where('is_archived', '==', False)
            
            docs = query.get()
            
            tasks = []
            for doc in docs:
                task_data = doc.to_dict()
                # Convert Firestore timestamps to ISO strings
                for field in ['created_at', 'updated_at', 'due_date', 'archived_at']:
                    if field in task_data and task_data[field]:
                        task_data[field] = Helpers.format_timestamp(task_data[field])
                
                # Handle recurrence end_date
                if 'recurrence' in task_data and task_data['recurrence'].get('end_date'):
                    task_data['recurrence']['end_date'] = Helpers.format_timestamp(task_data['recurrence']['end_date'])
                
                tasks.append(task_data)
            
            return tasks
            
        except Exception as e:
            raise Exception(f"Failed to get user tasks: {str(e)}")
    
    def get_assigned_tasks(self, user_id: str, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Get tasks assigned to a specific user"""
        try:
            query = self.collection.where('assigned_to', 'array_contains', user_id)
            
            if not include_archived:
                query = query.where('is_archived', '==', False)
            
            docs = query.get()
            
            tasks = []
            for doc in docs:
                task_data = doc.to_dict()
                # Convert Firestore timestamps to ISO strings
                for field in ['created_at', 'updated_at', 'due_date', 'archived_at']:
                    if field in task_data and task_data[field]:
                        task_data[field] = Helpers.format_timestamp(task_data[field])
                
                # Handle recurrence end_date
                if 'recurrence' in task_data and task_data['recurrence'].get('end_date'):
                    task_data['recurrence']['end_date'] = Helpers.format_timestamp(task_data['recurrence']['end_date'])
                
                tasks.append(task_data)
            
            return tasks
            
        except Exception as e:
            raise Exception(f"Failed to get assigned tasks: {str(e)}")
    
    def get_project_tasks(self, project_id: str, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Get tasks for a specific project"""
        try:
            query = self.collection.where('project_id', '==', project_id)
            
            if not include_archived:
                query = query.where('is_archived', '==', False)
            
            docs = query.get()
            
            tasks = []
            for doc in docs:
                task_data = doc.to_dict()
                # Convert Firestore timestamps to ISO strings
                for field in ['created_at', 'updated_at', 'due_date', 'archived_at']:
                    if field in task_data and task_data[field]:
                        task_data[field] = Helpers.format_timestamp(task_data[field])
                
                # Handle recurrence end_date
                if 'recurrence' in task_data and task_data['recurrence'].get('end_date'):
                    task_data['recurrence']['end_date'] = Helpers.format_timestamp(task_data['recurrence']['end_date'])
                
                tasks.append(task_data)
            
            return tasks
            
        except Exception as e:
            raise Exception(f"Failed to get project tasks: {str(e)}")
    
    def get_subtasks(self, parent_task_id: str) -> List[Dict[str, Any]]:
        """Get subtasks for a parent task"""
        try:
            query = self.collection.where('parent_task_id', '==', parent_task_id).where('is_archived', '==', False)
            docs = query.get()
            
            subtasks = []
            for doc in docs:
                task_data = doc.to_dict()
                # Convert Firestore timestamps to ISO strings
                for field in ['created_at', 'updated_at', 'due_date', 'archived_at']:
                    if field in task_data and task_data[field]:
                        task_data[field] = Helpers.format_timestamp(task_data[field])
                
                # Handle recurrence end_date
                if 'recurrence' in task_data and task_data['recurrence'].get('end_date'):
                    task_data['recurrence']['end_date'] = Helpers.format_timestamp(task_data['recurrence']['end_date'])
                
                subtasks.append(task_data)
            
            return subtasks
            
        except Exception as e:
            raise Exception(f"Failed to get subtasks: {str(e)}")
    
    def get_user_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """Get dashboard data for a user"""
        try:
            # Get user's created tasks
            created_tasks = self.get_user_tasks(user_id)
            
            # Get user's assigned tasks
            assigned_tasks = self.get_assigned_tasks(user_id)
            
            # Calculate statistics
            total_created = len(created_tasks)
            total_assigned = len(assigned_tasks)
            
            # Status breakdown
            status_breakdown = {'todo': 0, 'in_progress': 0, 'done': 0, 'review': 0}
            priority_breakdown = {str(i): 0 for i in range(1, 11)}
            
            all_tasks = created_tasks + assigned_tasks
            
            for task in all_tasks:
                status = task.get('status', 'todo')
                priority = str(task.get('priority_bucket', 5))
                
                if status in status_breakdown:
                    status_breakdown[status] += 1
                
                if priority in priority_breakdown:
                    priority_breakdown[priority] += 1
            
            # Overdue count
            overdue_count = 0
            current_time = Helpers.get_current_timestamp()
            
            for task in all_tasks:
                if task.get('due_date') and task.get('status') != 'done':
                    due_date = Helpers.parse_timestamp(task['due_date'])
                    if due_date and due_date < current_time:
                        overdue_count += 1
            
            # Recent tasks (last 5)
            recent_created = sorted(created_tasks, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
            recent_assigned = sorted(assigned_tasks, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
            
            return {
                'statistics': {
                    'total_created': total_created,
                    'total_assigned': total_assigned,
                    'status_breakdown': status_breakdown,
                    'priority_breakdown': priority_breakdown,
                    'overdue_count': overdue_count
                },
                'recent_created_tasks': recent_created,
                'recent_assigned_tasks': recent_assigned
            }
            
        except Exception as e:
            raise Exception(f"Failed to get dashboard data: {str(e)}")
    
    def get_overdue_tasks(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Get overdue tasks"""
        try:
            query = self.collection.where('is_archived', '==', False).where('status', '!=', 'done')
            
            if user_id:
                # Get tasks created by or assigned to user
                created_query = query.where('created_by', '==', user_id)
                assigned_query = query.where('assigned_to', 'array_contains', user_id)
                
                created_docs = created_query.get()
                assigned_docs = assigned_query.get()
                
                all_docs = list(created_docs) + list(assigned_docs)
            else:
                all_docs = query.get()
            
            overdue_tasks = []
            current_time = Helpers.get_current_timestamp()
            
            for doc in all_docs:
                task_data = doc.to_dict()
                
                if task_data.get('due_date'):
                    due_date = task_data['due_date']
                    if due_date < current_time:
                        # Convert Firestore timestamps to ISO strings
                        for field in ['created_at', 'updated_at', 'due_date', 'archived_at']:
                            if field in task_data and task_data[field]:
                                task_data[field] = Helpers.format_timestamp(task_data[field])
                        
                        # Handle recurrence end_date
                        if 'recurrence' in task_data and task_data['recurrence'].get('end_date'):
                            task_data['recurrence']['end_date'] = Helpers.format_timestamp(task_data['recurrence']['end_date'])
                        
                        overdue_tasks.append(task_data)
            
            return overdue_tasks
            
        except Exception as e:
            raise Exception(f"Failed to get overdue tasks: {str(e)}")
