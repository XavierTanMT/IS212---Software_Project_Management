"""
Authentication endpoints for Firebase Auth integration.
This module handles user registration and login with Firebase Authentication.
"""
from datetime import datetime, timezone
from flask import request, jsonify
from . import users_bp
from firebase_admin import auth, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import requests
import os

def now_iso():
    return datetime.now(timezone.utc).isoformat()

# Get Firebase Web API Key from environment variable
# You can get this from Firebase Console → Project Settings → General → Web API Key
FIREBASE_WEB_API_KEY = os.environ.get('FIREBASE_WEB_API_KEY', 'AIzaSyBRwjLY_7EstOCQa8aIhRFEp-gEA_IgqvI')

@users_bp.post("/auth/register")
def register_user():
    """
    Register a new user with Firebase Authentication and create user profile in Firestore.
    Expected payload: {email, password, name, user_id}
    Returns: {user: {...}, firebaseToken: "..."}
    """
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    
    user_id = (payload.get("user_id") or "").strip()
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = (payload.get("password") or "").strip()
    
    # Validate required fields
    if not user_id or not name or not email or not password:
        return jsonify({"error": "user_id, name, email, and password are required"}), 400
    
    # Validate password strength
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    
    try:
        # Check if user_id already exists in Firestore
        user_ref = db.collection("users").document(user_id)
        if user_ref.get().exists:
            return jsonify({"error": "User ID already exists"}), 409
        
        # Check if email already exists in Firestore
        existing_user = db.collection("users").where(filter=FieldFilter("email", "==", email)).limit(1).stream()
        if list(existing_user):
            return jsonify({"error": "Email already registered"}), 409
        
        # Create Firebase Auth user
        try:
            firebase_user = auth.create_user(
                uid=user_id,  # Use our custom user_id as Firebase UID
                email=email,
                password=password,
                display_name=name
            )
        except auth.EmailAlreadyExistsError:
            return jsonify({"error": "Email already registered in Firebase"}), 409
        except auth.UidAlreadyExistsError:
            return jsonify({"error": "User ID already exists in Firebase"}), 409
        except ValueError as e:
            return jsonify({"error": f"Invalid input: {str(e)}"}), 400
        
        # Create user profile in Firestore
        user_doc = {
            "user_id": user_id,
            "name": name,
            "email": email,
            "created_at": now_iso(),
            "firebase_uid": firebase_user.uid
        }
        user_ref.set(user_doc)
        
        # Generate custom token for client
        custom_token = auth.create_custom_token(user_id)
        
        return jsonify({
            "user": user_doc,
            "firebaseToken": custom_token.decode('utf-8')
        }), 201
        
    except Exception as e:
        # Cleanup: if Firestore creation fails but Firebase user was created, delete the Firebase user
        try:
            if 'firebase_user' in locals():
                auth.delete_user(user_id)
        except:
            pass
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

@users_bp.post("/auth/login")
def login_user():
    """
    Login with email and password (BACKEND-ONLY MODE).
    Backend verifies credentials with Firebase Auth REST API and returns JWT token.
    
    Expected payload: {email: "...", password: "..."}
    Returns: {user: {...}, firebaseToken: "..."}
    """
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    
    email = (payload.get("email") or "").strip().lower()
    password = (payload.get("password") or "").strip()
    
    # Check if this is the old client-SDK flow (firebase_token provided)
    firebase_token = payload.get("firebase_token", "").strip()
    if firebase_token:
        # Old flow: verify token and return user data
        try:
            decoded_token = auth.verify_id_token(firebase_token)
            user_id = decoded_token.get('uid')
            
            if not user_id:
                return jsonify({"error": "Invalid token"}), 401
            
            user_ref = db.collection("users").document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                return jsonify({"error": "User profile not found"}), 404
            
            user_data = user_doc.to_dict()
            return jsonify({"user": user_data}), 200
            
        except auth.InvalidIdTokenError:
            return jsonify({"error": "Invalid Firebase token"}), 401
        except auth.ExpiredIdTokenError:
            return jsonify({"error": "Firebase token expired"}), 401
        except Exception as e:
            return jsonify({"error": f"Login failed: {str(e)}"}), 500
    
    # New flow: email/password login (backend-only mode)
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    try:
        # Step 1: Verify password using Firebase Auth REST API
        if FIREBASE_WEB_API_KEY:
            # Use Firebase REST API to verify email/password
            firebase_rest_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
            
            rest_response = requests.post(firebase_rest_url, json={
                "email": email,
                "password": password,
                "returnSecureToken": True
            })
            
            if not rest_response.ok:
                error_data = rest_response.json()
                error_message = error_data.get('error', {}).get('message', 'Invalid credentials')
                
                # Map Firebase errors to user-friendly messages
                if 'EMAIL_NOT_FOUND' in error_message:
                    return jsonify({"error": "No account found with this email"}), 401
                elif 'INVALID_PASSWORD' in error_message:
                    return jsonify({"error": "Incorrect password"}), 401
                elif 'USER_DISABLED' in error_message:
                    return jsonify({"error": "This account has been disabled"}), 401
                else:
                    return jsonify({"error": "Invalid credentials"}), 401
            
            # Password verified successfully
            firebase_data = rest_response.json()
            id_token = firebase_data.get('idToken')
            user_id = firebase_data.get('localId')
            
        else:
            # Fallback: If no Web API Key, find user by email and create custom token
            # WARNING: This doesn't verify password! Only use if you trust the source
            users_query = db.collection("users").where(filter=FieldFilter("email", "==", email)).limit(1).stream()
            users_list = list(users_query)
            
            if not users_list:
                return jsonify({"error": "User not found with this email"}), 404
            
            user_doc = users_list[0]
            user_id = user_doc.id
            
            # Create custom token (WARNING: password not verified in this fallback!)
            id_token = auth.create_custom_token(user_id).decode('utf-8')
        
        # Step 2: Get user profile from Firestore
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({"error": "User profile not found in database"}), 404
        
        user_data = user_doc.to_dict()
        
        return jsonify({
            "user": user_data,
            "firebaseToken": id_token
        }), 200
            
    except requests.RequestException as e:
        return jsonify({"error": f"Authentication service error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 500

@users_bp.post("/auth/verify")
def verify_token():
    """
    Verify a Firebase token and return user data.
    Used for session validation.
    
    Expected payload: {firebase_token: "..."}
    Returns: {user: {...}, valid: true}
    """
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    
    firebase_token = payload.get("firebase_token", "").strip()
    
    if not firebase_token:
        return jsonify({"error": "Firebase token is required", "valid": False}), 400
    
    try:
        # Verify the Firebase ID token
        decoded_token = auth.verify_id_token(firebase_token)
        user_id = decoded_token.get('uid')
        
        # Get user profile from Firestore
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({"error": "User not found", "valid": False}), 404
        
        user_data = user_doc.to_dict()
        return jsonify({"user": user_data, "valid": True}), 200
        
    except (auth.InvalidIdTokenError, auth.ExpiredIdTokenError):
        return jsonify({"error": "Invalid or expired token", "valid": False}), 401
    except Exception as e:
        return jsonify({"error": str(e), "valid": False}), 500
