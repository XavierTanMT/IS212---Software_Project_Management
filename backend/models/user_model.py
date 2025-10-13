from config.firebase_config import db
from utils.validators import Validators, Helpers
from typing import Dict, Any, Optional, List
from datetime import datetime

class UserModel:
    """User data model for Firestore operations"""
    
    def __init__(self):
        self.collection = db.collection('users')
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user"""
        try:
            # Validate required fields
            if not Validators.validate_user_id(user_data.get('user_id', '')):
                raise ValueError('Invalid user_id format')
            
            if not Validators.validate_email(user_data.get('email', '')):
                raise ValueError('Invalid email format')
            
            if not Validators.validate_name(user_data.get('name', '')):
                raise ValueError('Invalid name format')
            
            if not Validators.validate_role(user_data.get('role', '')):
                raise ValueError('Invalid role')
            
            # Check if user already exists
            if self.get_user(user_data['user_id']):
                raise ValueError('User already exists')
            
            # Check if email already exists
            if self.get_user_by_email(user_data['email']):
                raise ValueError('Email already registered')
            
            # Prepare user document
            user_doc = {
                'user_id': user_data['user_id'],
                'email': user_data['email'].lower().strip(),
                'name': Helpers.sanitize_string(user_data['name']),
                'role': user_data['role'],
                'manager_id': user_data.get('manager_id'),  # Optional
                'created_at': Helpers.get_current_timestamp(),
                'updated_at': Helpers.get_current_timestamp()
            }
            
            # Create document in Firestore
            doc_ref = self.collection.document(user_data['user_id'])
            doc_ref.set(user_doc)
            
            # Return created user data
            return self.get_user(user_data['user_id'])
            
        except Exception as e:
            raise Exception(f"Failed to create user: {str(e)}")
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by user_id"""
        try:
            doc_ref = self.collection.document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                user_data = doc.to_dict()
                # Convert Firestore timestamps to ISO strings
                if 'created_at' in user_data:
                    user_data['created_at'] = Helpers.format_timestamp(user_data['created_at'])
                if 'updated_at' in user_data:
                    user_data['updated_at'] = Helpers.format_timestamp(user_data['updated_at'])
                return user_data
            return None
            
        except Exception as e:
            raise Exception(f"Failed to get user: {str(e)}")
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            query = self.collection.where('email', '==', email.lower().strip()).limit(1)
            docs = query.get()
            
            if docs:
                user_data = docs[0].to_dict()
                # Convert Firestore timestamps to ISO strings
                if 'created_at' in user_data:
                    user_data['created_at'] = Helpers.format_timestamp(user_data['created_at'])
                if 'updated_at' in user_data:
                    user_data['updated_at'] = Helpers.format_timestamp(user_data['updated_at'])
                return user_data
            return None
            
        except Exception as e:
            raise Exception(f"Failed to get user by email: {str(e)}")
    
    def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[Dict[str, Any]]:
        """Get user by Firebase UID (stored in custom claims or separate field)"""
        try:
            # For now, we'll use email from Firebase token to find user
            # In a more robust implementation, you'd store firebase_uid in user document
            from firebase_admin import auth as firebase_auth
            firebase_user = firebase_auth.get_user(firebase_uid)
            return self.get_user_by_email(firebase_user.email)
            
        except Exception as e:
            raise Exception(f"Failed to get user by Firebase UID: {str(e)}")
    
    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user data"""
        try:
            # Validate fields if provided
            if 'email' in update_data and not Validators.validate_email(update_data['email']):
                raise ValueError('Invalid email format')
            
            if 'name' in update_data and not Validators.validate_name(update_data['name']):
                raise ValueError('Invalid name format')
            
            if 'role' in update_data and not Validators.validate_role(update_data['role']):
                raise ValueError('Invalid role')
            
            # Check if user exists
            if not self.get_user(user_id):
                raise ValueError('User not found')
            
            # Prepare update data
            update_doc = {
                'updated_at': Helpers.get_current_timestamp()
            }
            
            # Add validated fields
            if 'email' in update_data:
                update_doc['email'] = update_data['email'].lower().strip()
            
            if 'name' in update_data:
                update_doc['name'] = Helpers.sanitize_string(update_data['name'])
            
            if 'role' in update_data:
                update_doc['role'] = update_data['role']
            
            if 'manager_id' in update_data:
                update_doc['manager_id'] = update_data['manager_id']
            
            # Update document
            doc_ref = self.collection.document(user_id)
            doc_ref.update(update_doc)
            
            return self.get_user(user_id)
            
        except Exception as e:
            raise Exception(f"Failed to update user: {str(e)}")
    
    def delete_user(self, user_id: str) -> bool:
        """Delete user (soft delete by updating role)"""
        try:
            if not self.get_user(user_id):
                raise ValueError('User not found')
            
            # Soft delete by updating role to 'deleted'
            self.update_user(user_id, {'role': 'deleted'})
            return True
            
        except Exception as e:
            raise Exception(f"Failed to delete user: {str(e)}")
    
    def get_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        """Get all users with specific role"""
        try:
            if not Validators.validate_role(role):
                raise ValueError('Invalid role')
            
            query = self.collection.where('role', '==', role)
            docs = query.get()
            
            users = []
            for doc in docs:
                user_data = doc.to_dict()
                # Convert Firestore timestamps to ISO strings
                if 'created_at' in user_data:
                    user_data['created_at'] = Helpers.format_timestamp(user_data['created_at'])
                if 'updated_at' in user_data:
                    user_data['updated_at'] = Helpers.format_timestamp(user_data['updated_at'])
                users.append(user_data)
            
            return users
            
        except Exception as e:
            raise Exception(f"Failed to get users by role: {str(e)}")
    
    def get_team_members(self, manager_id: str) -> List[Dict[str, Any]]:
        """Get team members for a manager"""
        try:
            query = self.collection.where('manager_id', '==', manager_id)
            docs = query.get()
            
            team_members = []
            for doc in docs:
                user_data = doc.to_dict()
                # Convert Firestore timestamps to ISO strings
                if 'created_at' in user_data:
                    user_data['created_at'] = Helpers.format_timestamp(user_data['created_at'])
                if 'updated_at' in user_data:
                    user_data['updated_at'] = Helpers.format_timestamp(user_data['updated_at'])
                team_members.append(user_data)
            
            return team_members
            
        except Exception as e:
            raise Exception(f"Failed to get team members: {str(e)}")
    
    def get_all_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all users (for admin)"""
        try:
            query = self.collection.limit(limit)
            docs = query.get()
            
            users = []
            for doc in docs:
                user_data = doc.to_dict()
                # Convert Firestore timestamps to ISO strings
                if 'created_at' in user_data:
                    user_data['created_at'] = Helpers.format_timestamp(user_data['created_at'])
                if 'updated_at' in user_data:
                    user_data['updated_at'] = Helpers.format_timestamp(user_data['updated_at'])
                users.append(user_data)
            
            return users
            
        except Exception as e:
            raise Exception(f"Failed to get all users: {str(e)}")
