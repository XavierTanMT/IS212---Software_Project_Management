from models.task_model import TaskModel
from utils.validators import Helpers
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

class RecurrenceService:
    """Service for handling recurring tasks"""
    
    def __init__(self):
        self.task_model = TaskModel()
    
    def create_recurring_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a recurring task"""
        try:
            # Validate recurrence data
            recurrence = task_data.get('recurrence', {})
            if not recurrence.get('enabled', False):
                raise ValueError('Recurrence must be enabled')
            
            if not recurrence.get('frequency'):
                raise ValueError('Recurrence frequency is required')
            
            if not recurrence.get('interval', 0) > 0:
                raise ValueError('Recurrence interval must be greater than 0')
            
            # Create the initial task
            task = self.task_model.create_task(task_data)
            
            # Calculate next occurrence if task has due date
            if task.get('due_date'):
                next_occurrence = self._calculate_next_occurrence(
                    recurrence['frequency'],
                    recurrence['interval'],
                    Helpers.parse_timestamp(task['due_date'])
                )
                
                # Update task with next occurrence
                update_data = {
                    'recurrence.next_occurrence': next_occurrence
                }
                self.task_model.update_task(task['task_id'], update_data)
            
            return task
            
        except Exception as e:
            raise Exception(f"Failed to create recurring task: {str(e)}")
    
    def complete_recurring_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Complete a recurring task and generate next occurrence"""
        try:
            # Get the task
            task = self.task_model.get_task(task_id)
            if not task:
                raise ValueError('Task not found')
            
            # Check if task is recurring
            recurrence = task.get('recurrence', {})
            if not recurrence.get('enabled', False):
                # Just mark as completed, no recurrence
                self.task_model.update_task(task_id, {'status': 'done'})
                return None
            
            # Check if we should create next occurrence
            if not self._should_create_next_occurrence(recurrence):
                # Mark as completed, no more occurrences
                self.task_model.update_task(task_id, {'status': 'done'})
                return None
            
            # Calculate next occurrence
            current_due_date = Helpers.parse_timestamp(task.get('due_date'))
            if not current_due_date:
                # If no due date, use current time
                current_due_date = Helpers.get_current_timestamp()
            
            next_due_date = self._calculate_next_occurrence(
                recurrence['frequency'],
                recurrence['interval'],
                current_due_date
            )
            
            # Create next occurrence
            next_task_data = {
                'title': task['title'],
                'description': task['description'],
                'status': 'todo',
                'priority_bucket': task['priority_bucket'],
                'due_date': Helpers.format_timestamp(next_due_date),
                'created_by': task['created_by'],
                'assigned_to': task['assigned_to'],
                'project_id': task.get('project_id'),
                'parent_task_id': task.get('parent_task_id'),
                'tags': task.get('tags', []),
                'recurrence': recurrence  # Same recurrence settings
            }
            
            # Create the next task
            next_task = self.task_model.create_task(next_task_data)
            
            # Mark original task as completed
            self.task_model.update_task(task_id, {'status': 'done'})
            
            return next_task
            
        except Exception as e:
            raise Exception(f"Failed to complete recurring task: {str(e)}")
    
    def _calculate_next_occurrence(self, frequency: str, interval: int, current_date: datetime) -> datetime:
        """Calculate next occurrence date"""
        if frequency == 'daily':
            return current_date + timedelta(days=interval)
        elif frequency == 'weekly':
            return current_date + timedelta(weeks=interval)
        elif frequency == 'monthly':
            # Simple monthly calculation (30 days)
            return current_date + timedelta(days=30 * interval)
        else:
            raise ValueError(f"Invalid frequency: {frequency}")
    
    def _should_create_next_occurrence(self, recurrence: Dict[str, Any]) -> bool:
        """Check if we should create next occurrence"""
        # Check if there's an end date
        end_date = recurrence.get('end_date')
        if end_date:
            end_date_dt = Helpers.parse_timestamp(end_date)
            if end_date_dt and Helpers.get_current_timestamp() >= end_date_dt:
                return False
        
        # For now, always create next occurrence if no end date
        return True
    
    def get_recurring_tasks_due_soon(self, days_ahead: int = 7) -> list:
        """Get recurring tasks that are due soon"""
        try:
            # This would require a more complex query
            # For now, we'll get all recurring tasks and filter
            # In production, you might want to use a scheduled job
            
            # Get all tasks with recurrence enabled
            query = self.task_model.collection.where('recurrence.enabled', '==', True).where('is_archived', '==', False)
            docs = query.get()
            
            due_soon = []
            current_time = Helpers.get_current_timestamp()
            future_time = current_time + timedelta(days=days_ahead)
            
            for doc in docs:
                task_data = doc.to_dict()
                
                # Check if task is due soon
                due_date = task_data.get('due_date')
                if due_date and current_time <= due_date <= future_time:
                    # Convert Firestore timestamps to ISO strings
                    for field in ['created_at', 'updated_at', 'due_date', 'archived_at']:
                        if field in task_data and task_data[field]:
                            task_data[field] = Helpers.format_timestamp(task_data[field])
                    
                    # Handle recurrence end_date
                    if 'recurrence' in task_data and task_data['recurrence'].get('end_date'):
                        task_data['recurrence']['end_date'] = Helpers.format_timestamp(task_data['recurrence']['end_date'])
                    
                    due_soon.append(task_data)
            
            return due_soon
            
        except Exception as e:
            raise Exception(f"Failed to get recurring tasks due soon: {str(e)}")
    
    def update_recurrence_settings(self, task_id: str, recurrence_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update recurrence settings for a task"""
        try:
            # Validate recurrence data
            if recurrence_data.get('enabled', False):
                if not recurrence_data.get('frequency'):
                    raise ValueError('Recurrence frequency is required when enabled')
                
                if not recurrence_data.get('interval', 0) > 0:
                    raise ValueError('Recurrence interval must be greater than 0')
            
            # Update the task
            update_data = {'recurrence': recurrence_data}
            updated_task = self.task_model.update_task(task_id, update_data)
            
            return updated_task
            
        except Exception as e:
            raise Exception(f"Failed to update recurrence settings: {str(e)}")
    
    def pause_recurrence(self, task_id: str) -> Dict[str, Any]:
        """Pause recurrence for a task"""
        try:
            task = self.task_model.get_task(task_id)
            if not task:
                raise ValueError('Task not found')
            
            recurrence = task.get('recurrence', {})
            recurrence['enabled'] = False
            
            update_data = {'recurrence': recurrence}
            updated_task = self.task_model.update_task(task_id, update_data)
            
            return updated_task
            
        except Exception as e:
            raise Exception(f"Failed to pause recurrence: {str(e)}")
    
    def resume_recurrence(self, task_id: str) -> Dict[str, Any]:
        """Resume recurrence for a task"""
        try:
            task = self.task_model.get_task(task_id)
            if not task:
                raise ValueError('Task not found')
            
            recurrence = task.get('recurrence', {})
            if not recurrence.get('frequency'):
                raise ValueError('Cannot resume recurrence without frequency setting')
            
            recurrence['enabled'] = True
            
            update_data = {'recurrence': recurrence}
            updated_task = self.task_model.update_task(task_id, update_data)
            
            return updated_task
            
        except Exception as e:
            raise Exception(f"Failed to resume recurrence: {str(e)}")
