from datetime import datetime
from typing import Dict, Any, Optional
import re

class Validators:
    """Input validation utilities"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_user_id(user_id: str) -> bool:
        """Validate user ID format (3-20 chars, alphanumeric + underscore, or Firebase UID)"""
        # Allow Firebase UIDs (28 chars, alphanumeric)
        if len(user_id) == 28 and user_id.replace('-', '').replace('_', '').isalnum():
            return True
        
        # Allow custom user IDs (3-20 chars, alphanumeric + underscore)
        pattern = r'^[a-zA-Z0-9_]{3,20}$'
        return bool(re.match(pattern, user_id))
    
    @staticmethod
    def validate_name(name: str) -> bool:
        """Validate name format (2-100 chars, letters and spaces)"""
        pattern = r'^[a-zA-Z\s]{2,100}$'
        return bool(re.match(pattern, name))
    
    @staticmethod
    def validate_task_title(title: str) -> bool:
        """Validate task title (3-100 chars)"""
        return 3 <= len(title.strip()) <= 100
    
    @staticmethod
    def validate_task_description(description: str) -> bool:
        """Validate task description (10-500 chars)"""
        return 10 <= len(description.strip()) <= 500
    
    @staticmethod
    def validate_priority_bucket(priority: int) -> bool:
        """Validate priority bucket (1-10)"""
        return 1 <= priority <= 10
    
    @staticmethod
    def validate_role(role: str) -> bool:
        """Validate user role"""
        valid_roles = ['staff', 'manager', 'director', 'admin']
        return role in valid_roles
    
    @staticmethod
    def validate_status(status: str) -> bool:
        """Validate task status"""
        valid_statuses = ['todo', 'in_progress', 'done', 'review']
        return status in valid_statuses
    
    @staticmethod
    def validate_recurrence_frequency(frequency: str) -> bool:
        """Validate recurrence frequency"""
        valid_frequencies = ['daily', 'weekly', 'monthly']
        return frequency in valid_frequencies

class Helpers:
    """Utility helper functions"""
    
    @staticmethod
    def generate_id() -> str:
        """Generate a unique ID"""
        import uuid
        return str(uuid.uuid4())
    
    @staticmethod
    def get_current_timestamp() -> datetime:
        """Get current timestamp"""
        return datetime.utcnow()
    
    @staticmethod
    def format_timestamp(timestamp: datetime) -> str:
        """Format timestamp for API response"""
        return timestamp.isoformat() + 'Z'
    
    @staticmethod
    def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string to datetime"""
        try:
            # Handle both ISO format and other common formats
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1]
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def sanitize_string(text: str) -> str:
        """Sanitize string input"""
        if not text:
            return ""
        return text.strip()
    
    @staticmethod
    def calculate_next_occurrence(frequency: str, interval: int, current_date: datetime) -> datetime:
        """Calculate next occurrence for recurring tasks"""
        from datetime import timedelta
        
        if frequency == 'daily':
            return current_date + timedelta(days=interval)
        elif frequency == 'weekly':
            return current_date + timedelta(weeks=interval)
        elif frequency == 'monthly':
            # Simple monthly calculation (30 days)
            return current_date + timedelta(days=30 * interval)
        else:
            return current_date
    
    @staticmethod
    def is_overdue(due_date: datetime) -> bool:
        """Check if task is overdue"""
        return due_date < datetime.utcnow()
    
    @staticmethod
    def get_priority_color(priority: int) -> str:
        """Get color for priority bucket (1-10)"""
        if priority <= 3:
            return '#28a745'  # Green
        elif priority <= 6:
            return '#ffc107'  # Yellow
        else:
            return '#dc3545'  # Red
    
    @staticmethod
    def get_status_color(status: str) -> str:
        """Get color for task status"""
        colors = {
            'todo': '#2196f3',      # Blue
            'in_progress': '#ff9800',  # Orange
            'done': '#4caf50',      # Green
            'review': '#9c27b0'     # Purple
        }
        return colors.get(status, '#666666')
    
    @staticmethod
    def build_error_response(message: str, code: int = 400) -> Dict[str, Any]:
        """Build standardized error response"""
        return {
            'error': message,
            'code': code,
            'timestamp': Helpers.format_timestamp(Helpers.get_current_timestamp())
        }
    
    @staticmethod
    def build_success_response(data: Any = None, message: str = None) -> Dict[str, Any]:
        """Build standardized success response"""
        response = {
            'success': True,
            'timestamp': Helpers.format_timestamp(Helpers.get_current_timestamp())
        }
        
        if data is not None:
            response['data'] = data
        
        if message:
            response['message'] = message
        
        return response
