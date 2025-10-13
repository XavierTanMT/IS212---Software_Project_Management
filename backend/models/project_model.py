from config.firebase_config import db
from utils.validators import Validators, Helpers
from typing import Dict, Any, Optional, List
from datetime import datetime

class ProjectModel:
    """Project data model for Firestore operations"""
    
    def __init__(self):
        self.collection = db.collection('projects')
    
    def create_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new project"""
        try:
            # Validate required fields
            if not project_data.get('name', '').strip():
                raise ValueError('Project name is required')
            
            if len(project_data.get('name', '').strip()) < 2:
                raise ValueError('Project name must be at least 2 characters')
            
            if len(project_data.get('name', '').strip()) > 100:
                raise ValueError('Project name must be less than 100 characters')
            
            # Generate project ID
            project_id = Helpers.generate_id()
            
            # Prepare project document
            project_doc = {
                'project_id': project_id,
                'name': Helpers.sanitize_string(project_data['name']),
                'description': Helpers.sanitize_string(project_data.get('description', '')),
                'created_by': project_data['created_by'],
                'members': project_data.get('members', []),  # List of user IDs
                'created_at': Helpers.get_current_timestamp(),
                'updated_at': Helpers.get_current_timestamp()
            }
            
            # Create document in Firestore
            doc_ref = self.collection.document(project_id)
            doc_ref.set(project_doc)
            
            # Return created project data
            return self.get_project(project_id)
            
        except Exception as e:
            raise Exception(f"Failed to create project: {str(e)}")
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by project_id"""
        try:
            doc_ref = self.collection.document(project_id)
            doc = doc_ref.get()
            
            if doc.exists:
                project_data = doc.to_dict()
                # Convert Firestore timestamps to ISO strings
                if 'created_at' in project_data:
                    project_data['created_at'] = Helpers.format_timestamp(project_data['created_at'])
                if 'updated_at' in project_data:
                    project_data['updated_at'] = Helpers.format_timestamp(project_data['updated_at'])
                return project_data
            return None
            
        except Exception as e:
            raise Exception(f"Failed to get project: {str(e)}")
    
    def update_project(self, project_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update project data"""
        try:
            # Check if project exists
            if not self.get_project(project_id):
                raise ValueError('Project not found')
            
            # Validate fields if provided
            if 'name' in update_data:
                name = update_data['name'].strip()
                if not name:
                    raise ValueError('Project name cannot be empty')
                if len(name) < 2:
                    raise ValueError('Project name must be at least 2 characters')
                if len(name) > 100:
                    raise ValueError('Project name must be less than 100 characters')
            
            # Prepare update data
            update_doc = {
                'updated_at': Helpers.get_current_timestamp()
            }
            
            # Add validated fields
            if 'name' in update_data:
                update_doc['name'] = Helpers.sanitize_string(update_data['name'])
            
            if 'description' in update_data:
                update_doc['description'] = Helpers.sanitize_string(update_data['description'])
            
            if 'members' in update_data:
                update_doc['members'] = update_data['members']
            
            # Update document
            doc_ref = self.collection.document(project_id)
            doc_ref.update(update_doc)
            
            return self.get_project(project_id)
            
        except Exception as e:
            raise Exception(f"Failed to update project: {str(e)}")
    
    def delete_project(self, project_id: str) -> bool:
        """Delete project"""
        try:
            if not self.get_project(project_id):
                raise ValueError('Project not found')
            
            # Delete document
            doc_ref = self.collection.document(project_id)
            doc_ref.delete()
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to delete project: {str(e)}")
    
    def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """Get projects for a specific user (created by or member)"""
        try:
            # Get projects created by user
            created_query = self.collection.where('created_by', '==', user_id)
            created_docs = created_query.get()
            
            # Get projects where user is a member
            member_query = self.collection.where('members', 'array_contains', user_id)
            member_docs = member_query.get()
            
            # Combine and deduplicate
            projects = []
            project_ids = set()
            
            for doc in list(created_docs) + list(member_docs):
                project_data = doc.to_dict()
                project_id = project_data['project_id']
                
                if project_id not in project_ids:
                    # Convert Firestore timestamps to ISO strings
                    if 'created_at' in project_data:
                        project_data['created_at'] = Helpers.format_timestamp(project_data['created_at'])
                    if 'updated_at' in project_data:
                        project_data['updated_at'] = Helpers.format_timestamp(project_data['updated_at'])
                    
                    projects.append(project_data)
                    project_ids.add(project_id)
            
            return projects
            
        except Exception as e:
            raise Exception(f"Failed to get user projects: {str(e)}")
    
    def add_member(self, project_id: str, user_id: str) -> Dict[str, Any]:
        """Add member to project"""
        try:
            project = self.get_project(project_id)
            if not project:
                raise ValueError('Project not found')
            
            # Check if user is already a member
            members = project.get('members', [])
            if user_id in members:
                raise ValueError('User is already a member of this project')
            
            # Add user to members list
            members.append(user_id)
            
            # Update project
            updated_project = self.update_project(project_id, {'members': members})
            
            return updated_project
            
        except Exception as e:
            raise Exception(f"Failed to add member: {str(e)}")
    
    def remove_member(self, project_id: str, user_id: str) -> Dict[str, Any]:
        """Remove member from project"""
        try:
            project = self.get_project(project_id)
            if not project:
                raise ValueError('Project not found')
            
            # Check if user is the creator
            if project.get('created_by') == user_id:
                raise ValueError('Cannot remove project creator')
            
            # Remove user from members list
            members = project.get('members', [])
            if user_id not in members:
                raise ValueError('User is not a member of this project')
            
            members.remove(user_id)
            
            # Update project
            updated_project = self.update_project(project_id, {'members': members})
            
            return updated_project
            
        except Exception as e:
            raise Exception(f"Failed to remove member: {str(e)}")
    
    def get_project_members(self, project_id: str) -> List[Dict[str, Any]]:
        """Get project members with their details"""
        try:
            project = self.get_project(project_id)
            if not project:
                raise ValueError('Project not found')
            
            # Get member details from user model
            from models.user_model import UserModel
            user_model = UserModel()
            
            members = []
            
            # Add creator
            creator = user_model.get_user(project.get('created_by'))
            if creator:
                creator['role_in_project'] = 'creator'
                members.append(creator)
            
            # Add other members
            for member_id in project.get('members', []):
                if member_id != project.get('created_by'):  # Don't duplicate creator
                    member = user_model.get_user(member_id)
                    if member:
                        member['role_in_project'] = 'member'
                        members.append(member)
            
            return members
            
        except Exception as e:
            raise Exception(f"Failed to get project members: {str(e)}")
    
    def get_project_statistics(self, project_id: str) -> Dict[str, Any]:
        """Get project statistics"""
        try:
            project = self.get_project(project_id)
            if not project:
                raise ValueError('Project not found')
            
            # Get tasks for this project
            from models.task_model import TaskModel
            task_model = TaskModel()
            
            tasks = task_model.get_project_tasks(project_id)
            
            # Calculate statistics
            total_tasks = len(tasks)
            status_breakdown = {'todo': 0, 'in_progress': 0, 'done': 0, 'review': 0}
            priority_breakdown = {str(i): 0 for i in range(1, 11)}
            
            overdue_count = 0
            current_time = Helpers.get_current_timestamp()
            
            for task in tasks:
                # Status breakdown
                status = task.get('status', 'todo')
                if status in status_breakdown:
                    status_breakdown[status] += 1
                
                # Priority breakdown
                priority = str(task.get('priority_bucket', 5))
                if priority in priority_breakdown:
                    priority_breakdown[priority] += 1
                
                # Overdue count
                if task.get('due_date') and task.get('status') != 'done':
                    due_date = Helpers.parse_timestamp(task['due_date'])
                    if due_date and due_date < current_time:
                        overdue_count += 1
            
            return {
                'project': project,
                'statistics': {
                    'total_tasks': total_tasks,
                    'status_breakdown': status_breakdown,
                    'priority_breakdown': priority_breakdown,
                    'overdue_count': overdue_count,
                    'member_count': len(project.get('members', [])) + 1  # +1 for creator
                }
            }
            
        except Exception as e:
            raise Exception(f"Failed to get project statistics: {str(e)}")
    
    def get_all_projects(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all projects (admin only)"""
        try:
            query = self.collection.limit(limit)
            docs = query.get()
            
            projects = []
            for doc in docs:
                project_data = doc.to_dict()
                # Convert Firestore timestamps to ISO strings
                if 'created_at' in project_data:
                    project_data['created_at'] = Helpers.format_timestamp(project_data['created_at'])
                if 'updated_at' in project_data:
                    project_data['updated_at'] = Helpers.format_timestamp(project_data['updated_at'])
                projects.append(project_data)
            
            return projects
            
        except Exception as e:
            raise Exception(f"Failed to get all projects: {str(e)}")
