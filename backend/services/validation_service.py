"""
Centralized Input Validation Service
Handles all input validation with proper error messages
"""
from typing import Dict, Any, List, Optional
import re
from datetime import datetime

class ValidationService:
    """Centralized validation service for all inputs"""
    
    # Constants
    MIN_PASSWORD_LENGTH = 6
    MAX_PASSWORD_LENGTH = 128
    MIN_USER_ID_LENGTH = 3
    MAX_USER_ID_LENGTH = 20
    MIN_NAME_LENGTH = 2
    MAX_NAME_LENGTH = 100
    MIN_TASK_TITLE_LENGTH = 3
    MAX_TASK_TITLE_LENGTH = 100
    MIN_TASK_DESCRIPTION_LENGTH = 10
    MAX_TASK_DESCRIPTION_LENGTH = 500
    MIN_PRIORITY = 1
    MAX_PRIORITY = 10
    
    VALID_ROLES = ['staff', 'manager', 'director', 'admin']
    VALID_STATUSES = ['todo', 'in_progress', 'done', 'review']
    VALID_RECURRENCE_FREQUENCIES = ['daily', 'weekly', 'monthly']
    
    @staticmethod
    def validate_email(email: str) -> Dict[str, Any]:
        """Validate email format with detailed error message"""
        if not email or not isinstance(email, str):
            return {'valid': False, 'error': 'Email is required'}
        
        email = email.strip().lower()
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(pattern, email):
            return {'valid': False, 'error': 'Invalid email format'}
        
        if len(email) > 254:  # RFC 5321 limit
            return {'valid': False, 'error': 'Email is too long'}
        
        return {'valid': True, 'value': email}
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """Validate password with security requirements"""
        if not password or not isinstance(password, str):
            return {'valid': False, 'error': 'Password is required'}
        
        if len(password) < ValidationService.MIN_PASSWORD_LENGTH:
            return {'valid': False, 'error': f'Password must be at least {ValidationService.MIN_PASSWORD_LENGTH} characters'}
        
        if len(password) > ValidationService.MAX_PASSWORD_LENGTH:
            return {'valid': False, 'error': f'Password must be less than {ValidationService.MAX_PASSWORD_LENGTH} characters'}
        
        # Check for basic password strength
        if not re.search(r'[A-Za-z]', password):
            return {'valid': False, 'error': 'Password must contain at least one letter'}
        
        if not re.search(r'[0-9]', password):
            return {'valid': False, 'error': 'Password must contain at least one number'}
        
        return {'valid': True, 'value': password}
    
    @staticmethod
    def validate_user_id(user_id: str) -> Dict[str, Any]:
        """Validate user ID format"""
        if not user_id or not isinstance(user_id, str):
            return {'valid': False, 'error': 'User ID is required'}
        
        user_id = user_id.strip()
        
        # Allow Firebase UIDs (28 chars, alphanumeric)
        if len(user_id) == 28 and user_id.replace('-', '').replace('_', '').isalnum():
            return {'valid': True, 'value': user_id}
        
        # Allow custom user IDs
        if len(user_id) < ValidationService.MIN_USER_ID_LENGTH:
            return {'valid': False, 'error': f'User ID must be at least {ValidationService.MIN_USER_ID_LENGTH} characters'}
        
        if len(user_id) > ValidationService.MAX_USER_ID_LENGTH:
            return {'valid': False, 'error': f'User ID must be less than {ValidationService.MAX_USER_ID_LENGTH} characters'}
        
        pattern = r'^[a-zA-Z0-9_]+$'
        if not re.match(pattern, user_id):
            return {'valid': False, 'error': 'User ID can only contain letters, numbers, and underscores'}
        
        return {'valid': True, 'value': user_id}
    
    @staticmethod
    def validate_name(name: str) -> Dict[str, Any]:
        """Validate name format"""
        if not name or not isinstance(name, str):
            return {'valid': False, 'error': 'Name is required'}
        
        name = name.strip()
        
        if len(name) < ValidationService.MIN_NAME_LENGTH:
            return {'valid': False, 'error': f'Name must be at least {ValidationService.MIN_NAME_LENGTH} characters'}
        
        if len(name) > ValidationService.MAX_NAME_LENGTH:
            return {'valid': False, 'error': f'Name must be less than {ValidationService.MAX_NAME_LENGTH} characters'}
        
        pattern = r'^[a-zA-Z\s]+$'
        if not re.match(pattern, name):
            return {'valid': False, 'error': 'Name can only contain letters and spaces'}
        
        return {'valid': True, 'value': name}
    
    @staticmethod
    def validate_task_title(title: str) -> Dict[str, Any]:
        """Validate task title"""
        if not title or not isinstance(title, str):
            return {'valid': False, 'error': 'Task title is required'}
        
        title = title.strip()
        
        if len(title) < ValidationService.MIN_TASK_TITLE_LENGTH:
            return {'valid': False, 'error': f'Task title must be at least {ValidationService.MIN_TASK_TITLE_LENGTH} characters'}
        
        if len(title) > ValidationService.MAX_TASK_TITLE_LENGTH:
            return {'valid': False, 'error': f'Task title must be less than {ValidationService.MAX_TASK_TITLE_LENGTH} characters'}
        
        return {'valid': True, 'value': title}
    
    @staticmethod
    def validate_task_description(description: str) -> Dict[str, Any]:
        """Validate task description"""
        if not description or not isinstance(description, str):
            return {'valid': False, 'error': 'Task description is required'}
        
        description = description.strip()
        
        if len(description) < ValidationService.MIN_TASK_DESCRIPTION_LENGTH:
            return {'valid': False, 'error': f'Task description must be at least {ValidationService.MIN_TASK_DESCRIPTION_LENGTH} characters'}
        
        if len(description) > ValidationService.MAX_TASK_DESCRIPTION_LENGTH:
            return {'valid': False, 'error': f'Task description must be less than {ValidationService.MAX_TASK_DESCRIPTION_LENGTH} characters'}
        
        return {'valid': True, 'value': description}
    
    @staticmethod
    def validate_priority_bucket(priority: Any) -> Dict[str, Any]:
        """Validate priority bucket (1-10)"""
        try:
            priority = int(priority)
        except (ValueError, TypeError):
            return {'valid': False, 'error': 'Priority must be a number'}
        
        if priority < ValidationService.MIN_PRIORITY:
            return {'valid': False, 'error': f'Priority must be at least {ValidationService.MIN_PRIORITY}'}
        
        if priority > ValidationService.MAX_PRIORITY:
            return {'valid': False, 'error': f'Priority must be at most {ValidationService.MAX_PRIORITY}'}
        
        return {'valid': True, 'value': priority}
    
    @staticmethod
    def validate_role(role: str) -> Dict[str, Any]:
        """Validate user role"""
        if not role or not isinstance(role, str):
            return {'valid': False, 'error': 'Role is required'}
        
        role = role.strip().lower()
        
        if role not in ValidationService.VALID_ROLES:
            return {'valid': False, 'error': f'Role must be one of: {", ".join(ValidationService.VALID_ROLES)}'}
        
        return {'valid': True, 'value': role}
    
    @staticmethod
    def validate_status(status: str) -> Dict[str, Any]:
        """Validate task status"""
        if not status or not isinstance(status, str):
            return {'valid': False, 'error': 'Status is required'}
        
        status = status.strip().lower()
        
        if status not in ValidationService.VALID_STATUSES:
            return {'valid': False, 'error': f'Status must be one of: {", ".join(ValidationService.VALID_STATUSES)}'}
        
        return {'valid': True, 'value': status}
    
    @staticmethod
    def validate_recurrence_frequency(frequency: str) -> Dict[str, Any]:
        """Validate recurrence frequency"""
        if not frequency or not isinstance(frequency, str):
            return {'valid': False, 'error': 'Recurrence frequency is required'}
        
        frequency = frequency.strip().lower()
        
        if frequency not in ValidationService.VALID_RECURRENCE_FREQUENCIES:
            return {'valid': False, 'error': f'Frequency must be one of: {", ".join(ValidationService.VALID_RECURRENCE_FREQUENCIES)}'}
        
        return {'valid': True, 'value': frequency}
    
    @staticmethod
    def validate_recurrence_interval(interval: Any) -> Dict[str, Any]:
        """Validate recurrence interval"""
        try:
            interval = int(interval)
        except (ValueError, TypeError):
            return {'valid': False, 'error': 'Recurrence interval must be a number'}
        
        if interval < 1:
            return {'valid': False, 'error': 'Recurrence interval must be at least 1'}
        
        if interval > 365:  # Reasonable upper limit
            return {'valid': False, 'error': 'Recurrence interval must be at most 365'}
        
        return {'valid': True, 'value': interval}
    
    @staticmethod
    def validate_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complete user data"""
        errors = []
        validated_data = {}
        
        # Validate required fields
        email_result = ValidationService.validate_email(user_data.get('email', ''))
        if not email_result['valid']:
            errors.append(email_result['error'])
        else:
            validated_data['email'] = email_result['value']
        
        password_result = ValidationService.validate_password(user_data.get('password', ''))
        if not password_result['valid']:
            errors.append(password_result['error'])
        else:
            validated_data['password'] = password_result['value']
        
        user_id_result = ValidationService.validate_user_id(user_data.get('user_id', ''))
        if not user_id_result['valid']:
            errors.append(user_id_result['error'])
        else:
            validated_data['user_id'] = user_id_result['value']
        
        name_result = ValidationService.validate_name(user_data.get('name', ''))
        if not name_result['valid']:
            errors.append(name_result['error'])
        else:
            validated_data['name'] = name_result['value']
        
        role_result = ValidationService.validate_role(user_data.get('role', 'staff'))
        if not role_result['valid']:
            errors.append(role_result['error'])
        else:
            validated_data['role'] = role_result['value']
        
        if errors:
            return {'valid': False, 'errors': errors}
        
        return {'valid': True, 'data': validated_data}
    
    @staticmethod
    def validate_task_data(task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complete task data"""
        errors = []
        validated_data = {}
        
        # Validate required fields
        title_result = ValidationService.validate_task_title(task_data.get('title', ''))
        if not title_result['valid']:
            errors.append(title_result['error'])
        else:
            validated_data['title'] = title_result['value']
        
        description_result = ValidationService.validate_task_description(task_data.get('description', ''))
        if not description_result['valid']:
            errors.append(description_result['error'])
        else:
            validated_data['description'] = description_result['value']
        
        priority_result = ValidationService.validate_priority_bucket(task_data.get('priority_bucket', 5))
        if not priority_result['valid']:
            errors.append(priority_result['error'])
        else:
            validated_data['priority_bucket'] = priority_result['value']
        
        status_result = ValidationService.validate_status(task_data.get('status', 'todo'))
        if not status_result['valid']:
            errors.append(status_result['error'])
        else:
            validated_data['status'] = status_result['value']
        
        # Validate optional fields
        if 'recurrence' in task_data and task_data['recurrence'].get('enabled'):
            recurrence = task_data['recurrence']
            
            frequency_result = ValidationService.validate_recurrence_frequency(recurrence.get('frequency', ''))
            if not frequency_result['valid']:
                errors.append(f"Recurrence: {frequency_result['error']}")
            else:
                validated_data.setdefault('recurrence', {})['frequency'] = frequency_result['value']
            
            interval_result = ValidationService.validate_recurrence_interval(recurrence.get('interval', 1))
            if not interval_result['valid']:
                errors.append(f"Recurrence: {interval_result['error']}")
            else:
                validated_data.setdefault('recurrence', {})['interval'] = interval_result['value']
        
        if errors:
            return {'valid': False, 'errors': errors}
        
        return {'valid': True, 'data': validated_data}
