from firebase_admin import auth as firebase_auth
from models.user_model import UserModel
from utils.validators import Validators, Helpers
from typing import Dict, Any, Optional
import json

class AuthService:
    """Authentication service using Firebase Auth"""
    
    def __init__(self):
        self.user_model = UserModel()
    
    def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new user with Firebase Auth and Firestore"""
        try:
            # Validate input data
            if not Validators.validate_user_id(user_data.get('user_id', '')):
                raise ValueError('Invalid user_id format')
            
            if not Validators.validate_email(user_data.get('email', '')):
                raise ValueError('Invalid email format')
            
            if not Validators.validate_name(user_data.get('name', '')):
                raise ValueError('Invalid name format')
            
            password = user_data.get('password', '')
            if len(password) < 6:
                raise ValueError('Password must be at least 6 characters')
            
            # Create Firebase Auth user
            firebase_user = firebase_auth.create_user(
                email=user_data['email'],
                password=password,
                display_name=user_data['name']
            )
            
            # Create user document in Firestore
            firestore_user_data = {
                'user_id': user_data['user_id'],
                'email': user_data['email'],
                'name': user_data['name'],
                'role': user_data.get('role', 'staff'),
                'manager_id': user_data.get('manager_id'),
                'firebase_uid': firebase_user.uid
            }
            
            created_user = self.user_model.create_user(firestore_user_data)
            
            # Set custom claims for role-based access
            self._set_user_claims(firebase_user.uid, created_user['role'])
            
            return {
                'user': created_user,
                'firebase_uid': firebase_user.uid,
                'message': 'User registered successfully'
            }
            
        except Exception as e:
            # Clean up Firebase user if Firestore creation fails
            try:
                if 'firebase_user' in locals():
                    firebase_auth.delete_user(firebase_user.uid)
            except:
                pass
            raise Exception(f"Registration failed: {str(e)}")
    
    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Login user (this would typically be handled by frontend Firebase SDK)"""
        try:
            # Get user from Firestore
            user_data = self.user_model.get_user_by_email(email)
            if not user_data:
                raise ValueError('User not found')
            
            # In a real implementation, the frontend would handle Firebase Auth
            # and send us the ID token for verification
            return {
                'user': user_data,
                'message': 'Login successful'
            }
            
        except Exception as e:
            raise Exception(f"Login failed: {str(e)}")
    
    def verify_token(self, id_token: str) -> Dict[str, Any]:
        """Verify Firebase ID token and return user data"""
        try:
            # Verify the token
            decoded_token = firebase_auth.verify_id_token(id_token)
            firebase_uid = decoded_token['uid']
            
            # Get user data from Firestore
            user_data = self.user_model.get_user_by_firebase_uid(firebase_uid)
            if not user_data:
                raise ValueError('User not found in database')
            
            return {
                'user': user_data,
                'firebase_uid': firebase_uid,
                'token_data': decoded_token
            }
            
        except Exception as e:
            raise Exception(f"Token verification failed: {str(e)}")
    
    def update_user_role(self, user_id: str, new_role: str) -> Dict[str, Any]:
        """Update user role (admin only)"""
        try:
            if not Validators.validate_role(new_role):
                raise ValueError('Invalid role')
            
            # Update user in Firestore
            updated_user = self.user_model.update_user(user_id, {'role': new_role})
            
            # Update Firebase custom claims
            firebase_uid = updated_user.get('firebase_uid')
            if firebase_uid:
                self._set_user_claims(firebase_uid, new_role)
            
            return {
                'user': updated_user,
                'message': 'User role updated successfully'
            }
            
        except Exception as e:
            raise Exception(f"Failed to update user role: {str(e)}")
    
    def reset_password(self, email: str) -> Dict[str, Any]:
        """Send password reset email"""
        try:
            if not Validators.validate_email(email):
                raise ValueError('Invalid email format')
            
            # Check if user exists
            user_data = self.user_model.get_user_by_email(email)
            if not user_data:
                raise ValueError('User not found')
            
            # Generate password reset link
            reset_link = firebase_auth.generate_password_reset_link(email)
            
            return {
                'message': 'Password reset email sent',
                'reset_link': reset_link  # In production, send this via email
            }
            
        except Exception as e:
            raise Exception(f"Password reset failed: {str(e)}")
    
    def delete_user_account(self, user_id: str) -> Dict[str, Any]:
        """Delete user account (admin only)"""
        try:
            # Get user data
            user_data = self.user_model.get_user(user_id)
            if not user_data:
                raise ValueError('User not found')
            
            # Delete from Firebase Auth
            firebase_uid = user_data.get('firebase_uid')
            if firebase_uid:
                firebase_auth.delete_user(firebase_uid)
            
            # Soft delete from Firestore
            self.user_model.delete_user(user_id)
            
            return {
                'message': 'User account deleted successfully'
            }
            
        except Exception as e:
            raise Exception(f"Failed to delete user account: {str(e)}")
    
    def _set_user_claims(self, firebase_uid: str, role: str) -> None:
        """Set custom claims for role-based access"""
        try:
            custom_claims = {
                'role': role,
                'user_id': firebase_uid  # You might want to store the actual user_id here
            }
            
            firebase_auth.set_custom_user_claims(firebase_uid, custom_claims)
            
        except Exception as e:
            print(f"Warning: Failed to set custom claims: {str(e)}")
    
    def get_user_by_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Get user data from ID token"""
        try:
            result = self.verify_token(id_token)
            return result['user']
        except:
            return None
