"""Unit tests for auth.py module"""
import pytest
from unittest.mock import Mock, patch
import sys

# Get fake modules from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")
fake_auth = sys.modules.get("firebase_admin.auth")

# Get exception classes
EmailAlreadyExistsError = fake_auth.EmailAlreadyExistsError
UidAlreadyExistsError = fake_auth.UidAlreadyExistsError
InvalidIdTokenError = fake_auth.InvalidIdTokenError
ExpiredIdTokenError = fake_auth.ExpiredIdTokenError

from flask import Flask
from backend.api import users_bp


# app, client, and mock_db fixtures provided by conftest.py


class TestRegisterUser:
    """Test user registration endpoint"""
    
    def test_register_success(self, client, mock_db, monkeypatch):
        """Test successful user registration"""
        # Mock Firestore - user doesn't exist
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_doc_ref.set = Mock()
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        # Mock Firebase Auth
        mock_firebase_user = Mock()
        mock_firebase_user.uid = "test_user_123"
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "create_user", Mock(return_value=mock_firebase_user))
        monkeypatch.setattr(fake_auth, "create_custom_token", Mock(return_value=b"test_token"))
        
        payload = {
            "user_id": "test_user_123",
            "name": "Test User",
            "email": "test@example.com",
            "password": "password123"
        }
        
        response = client.post("/api/users/auth/register", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert "user" in data
        assert "firebaseToken" in data
        assert data["user"]["user_id"] == "test_user_123"
        assert data["user"]["email"] == "test@example.com"
    
    def test_register_missing_fields(self, client, mock_db, monkeypatch):
        """Test registration with missing required fields"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Missing user_id
        response = client.post("/api/users/auth/register", json={
            "name": "Test",
            "email": "test@example.com",
            "password": "password123"
        })
        assert response.status_code == 400
        assert "required" in response.get_json()["error"].lower()
        
        # Missing password
        response = client.post("/api/users/auth/register", json={
            "user_id": "test",
            "name": "Test",
            "email": "test@example.com"
        })
        assert response.status_code == 400
    
    def test_register_weak_password(self, client, mock_db, monkeypatch):
        """Test registration with weak password"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "user_id": "test_user",
            "name": "Test User",
            "email": "test@example.com",
            "password": "12345"  # Too short
        }
        
        response = client.post("/api/users/auth/register", json=payload)
        
        assert response.status_code == 400
        assert "6 characters" in response.get_json()["error"]
    
    def test_register_user_id_exists_firestore(self, client, mock_db, monkeypatch):
        """Test registration when user_id already exists in Firestore"""
        # Mock Firestore - user exists
        mock_doc = Mock()
        mock_doc.exists = True
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "user_id": "existing_user",
            "name": "Test User",
            "email": "test@example.com",
            "password": "password123"
        }
        
        response = client.post("/api/users/auth/register", json=payload)
        
        assert response.status_code == 409
        assert "User ID already exists" in response.get_json()["error"]
    
    def test_register_email_exists_firestore(self, client, mock_db, monkeypatch):
        """Test registration when email already exists in Firestore"""
        # Mock Firestore - user_id doesn't exist but email does
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        
        mock_existing_user = Mock()
        mock_existing_user.id = "other_user"
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [mock_existing_user]
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "user_id": "new_user",
            "name": "Test User",
            "email": "existing@example.com",
            "password": "password123"
        }
        
        response = client.post("/api/users/auth/register", json=payload)
        
        assert response.status_code == 409
        assert "Email already registered" in response.get_json()["error"]
    
    def test_register_email_exists_firebase(self, client, mock_db, monkeypatch):
        """Test registration when email already exists in Firebase"""
        # Mock Firestore - no conflicts
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        # Mock Firebase Auth - email exists
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "create_user", Mock(side_effect=EmailAlreadyExistsError("Email exists")))
        
        payload = {
            "user_id": "new_user",
            "name": "Test User",
            "email": "existing@example.com",
            "password": "password123"
        }
        
        response = client.post("/api/users/auth/register", json=payload)
        
        assert response.status_code == 409
        assert "Email already registered in Firebase" in response.get_json()["error"]
    
    def test_register_uid_exists_firebase(self, client, mock_db, monkeypatch):
        """Test registration when UID already exists in Firebase"""
        # Mock Firestore - no conflicts
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        # Mock Firebase Auth - UID exists
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "create_user", Mock(side_effect=UidAlreadyExistsError("UID exists")))
        
        payload = {
            "user_id": "existing_uid",
            "name": "Test User",
            "email": "test@example.com",
            "password": "password123"
        }
        
        response = client.post("/api/users/auth/register", json=payload)
        
        assert response.status_code == 409
        assert "User ID already exists in Firebase" in response.get_json()["error"]
    
    def test_register_invalid_input(self, client, mock_db, monkeypatch):
        """Test registration with invalid input"""
        # Mock Firestore - no conflicts
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        # Mock Firebase Auth - invalid input
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "create_user", Mock(side_effect=ValueError("Invalid email")))
        
        payload = {
            "user_id": "test_user",
            "name": "Test User",
            "email": "invalid-email",
            "password": "password123"
        }
        
        response = client.post("/api/users/auth/register", json=payload)
        
        assert response.status_code == 400
        assert "Invalid input" in response.get_json()["error"]
    
    def test_register_email_lowercase(self, client, mock_db, monkeypatch):
        """Test that email is converted to lowercase"""
        # Mock Firestore
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_doc_ref.set = Mock()
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        # Mock Firebase Auth
        mock_firebase_user = Mock()
        mock_firebase_user.uid = "test_user"
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "create_user", Mock(return_value=mock_firebase_user))
        monkeypatch.setattr(fake_auth, "create_custom_token", Mock(return_value=b"test_token"))
        
        payload = {
            "user_id": "test_user",
            "name": "Test User",
            "email": "Test@EXAMPLE.COM",  # Mixed case
            "password": "password123"
        }
        
        response = client.post("/api/users/auth/register", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["user"]["email"] == "test@example.com"  # Should be lowercase
    
    def test_register_exception_cleanup(self, client, mock_db, monkeypatch):
        """Test that Firebase user is cleaned up if Firestore creation fails"""
        # Mock Firestore - document set fails
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_doc_ref.set = Mock(side_effect=Exception("Firestore error"))
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        # Mock Firebase Auth
        mock_firebase_user = Mock()
        mock_firebase_user.uid = "test_user"
        
        mock_delete = Mock()
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "create_user", Mock(return_value=mock_firebase_user))
        monkeypatch.setattr(fake_auth, "delete_user", mock_delete)
        
        payload = {
            "user_id": "test_user",
            "name": "Test User",
            "email": "test@example.com",
            "password": "password123"
        }
        
        response = client.post("/api/users/auth/register", json=payload)
        
        assert response.status_code == 500
        assert "Registration failed" in response.get_json()["error"]
    
    def test_register_exception_cleanup_delete_fails(self, client, mock_db, monkeypatch):
        """Test exception cleanup when delete also fails"""
        # Mock Firestore - document set fails
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        mock_doc_ref.set = Mock(side_effect=Exception("Firestore error"))
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        # Mock Firebase Auth - both create and delete
        mock_firebase_user = Mock()
        mock_firebase_user.uid = "test_user"
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "create_user", Mock(return_value=mock_firebase_user))
        # Delete also fails, but should be caught silently
        monkeypatch.setattr(fake_auth, "delete_user", Mock(side_effect=Exception("Delete failed")))
        
        payload = {
            "user_id": "test_user",
            "name": "Test User",
            "email": "test@example.com",
            "password": "password123"
        }
        
        response = client.post("/api/users/auth/register", json=payload)
        
        assert response.status_code == 500
        assert "Registration failed" in response.get_json()["error"]


class TestLoginUser:
    """Test user login endpoint"""
    
    def test_login_with_firebase_rest_api_success(self, client, mock_db, monkeypatch):
        """Test successful login using Firebase REST API"""
        # Mock Firestore - configure mock_db's collection method
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "user_id": "test_user",
            "name": "Test User",
            "email": "test@example.com"
        }

        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        
        # Create a mock collection that returns our configured document
        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        
        # Override the collection method to return our mock
        mock_db.collection = Mock(return_value=mock_collection)        # Mock requests.post for Firebase REST API
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "idToken": "test_id_token",
            "localId": "test_user"
        }
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('requests.post', return_value=mock_response):
            payload = {
                "email": "test@example.com",
                "password": "password123"
            }
            
            response = client.post("/api/users/auth/login", json=payload)
        
        assert response.status_code == 200
        data = response.get_json()
        assert "user" in data
        assert "firebaseToken" in data
        assert data["firebaseToken"] == "test_id_token"
    
    def test_login_missing_credentials(self, client, mock_db, monkeypatch):
        """Test login with missing email or password"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Missing password
        response = client.post("/api/users/auth/login", json={
            "email": "test@example.com"
        })
        assert response.status_code == 400
        assert "required" in response.get_json()["error"].lower()
        
        # Missing email
        response = client.post("/api/users/auth/login", json={
            "password": "password123"
        })
        assert response.status_code == 400
    
    def test_login_email_not_found(self, client, mock_db, monkeypatch):
        """Test login with email not found"""
        # Mock Firebase REST API - email not found
        mock_response = Mock()
        mock_response.ok = False
        mock_response.json.return_value = {
            "error": {"message": "EMAIL_NOT_FOUND"}
        }
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('requests.post', return_value=mock_response):
            payload = {
                "email": "nonexistent@example.com",
                "password": "password123"
            }
            
            response = client.post("/api/users/auth/login", json=payload)
        
        assert response.status_code == 401
        assert "No account found" in response.get_json()["error"]
    
    def test_login_invalid_password(self, client, mock_db, monkeypatch):
        """Test login with incorrect password"""
        # Mock Firebase REST API - invalid password
        mock_response = Mock()
        mock_response.ok = False
        mock_response.json.return_value = {
            "error": {"message": "INVALID_PASSWORD"}
        }
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('requests.post', return_value=mock_response):
            payload = {
                "email": "test@example.com",
                "password": "wrongpassword"
            }
            
            response = client.post("/api/users/auth/login", json=payload)
        
        assert response.status_code == 401
        assert "Incorrect password" in response.get_json()["error"]
    
    def test_login_user_disabled(self, client, mock_db, monkeypatch):
        """Test login with disabled account"""
        # Mock Firebase REST API - user disabled
        mock_response = Mock()
        mock_response.ok = False
        mock_response.json.return_value = {
            "error": {"message": "USER_DISABLED"}
        }
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('requests.post', return_value=mock_response):
            payload = {
                "email": "disabled@example.com",
                "password": "password123"
            }
            
            response = client.post("/api/users/auth/login", json=payload)
        
        assert response.status_code == 401
        assert "disabled" in response.get_json()["error"].lower()
    
    def test_login_generic_error(self, client, mock_db, monkeypatch):
        """Test login with generic Firebase error"""
        # Mock Firebase REST API - generic error
        mock_response = Mock()
        mock_response.ok = False
        mock_response.json.return_value = {
            "error": {"message": "UNKNOWN_ERROR"}
        }
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('requests.post', return_value=mock_response):
            payload = {
                "email": "test@example.com",
                "password": "password123"
            }
            
            response = client.post("/api/users/auth/login", json=payload)
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.get_json()["error"]
    
    def test_login_user_not_in_firestore(self, client, mock_db, monkeypatch):
        """Test login when user exists in Firebase but not in Firestore"""
        # Mock Firestore - user not found
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase REST API - login successful
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "idToken": "test_token",
            "localId": "test_user"
        }
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('requests.post', return_value=mock_response):
            payload = {
                "email": "test@example.com",
                "password": "password123"
            }
            
            response = client.post("/api/users/auth/login", json=payload)
        
        assert response.status_code == 404
        assert "User profile not found" in response.get_json()["error"]
    
    def test_login_with_firebase_token(self, client, mock_db, monkeypatch):
        """Test login with firebase_token (old flow)"""
        # Mock Firestore
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "user_id": "test_user",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth verify_id_token
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "verify_id_token", Mock(return_value={"uid": "test_user"}))
        
        payload = {
            "firebase_token": "valid_token"
        }
        
        response = client.post("/api/users/auth/login", json=payload)
        
        assert response.status_code == 200
        data = response.get_json()
        assert "user" in data
    
    def test_login_with_invalid_firebase_token(self, client, mock_db, monkeypatch):
        """Test login with invalid firebase_token"""
        # Mock Firebase Auth - invalid token
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "verify_id_token", Mock(side_effect=InvalidIdTokenError("Invalid")))
        
        payload = {
            "firebase_token": "invalid_token"
        }
        
        response = client.post("/api/users/auth/login", json=payload)
        
        assert response.status_code == 401
        assert "Invalid Firebase token" in response.get_json()["error"]
    
    def test_login_with_expired_firebase_token(self, client, mock_db, monkeypatch):
        """Test login with expired firebase_token"""
        # Mock Firebase Auth - expired token
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "verify_id_token", Mock(side_effect=ExpiredIdTokenError("Expired")))
        
        payload = {
            "firebase_token": "expired_token"
        }
        
        response = client.post("/api/users/auth/login", json=payload)
        
        assert response.status_code == 401
        assert "expired" in response.get_json()["error"].lower()
    
    def test_login_firebase_token_no_uid(self, client, mock_db, monkeypatch):
        """Test login with firebase_token that has no uid"""
        # Mock Firebase Auth - token without uid
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "verify_id_token", Mock(return_value={}))
        
        payload = {
            "firebase_token": "token_without_uid"
        }
        
        response = client.post("/api/users/auth/login", json=payload)
        
        assert response.status_code == 401
        assert "Invalid token" in response.get_json()["error"]
    
    def test_login_firebase_token_user_not_found(self, client, mock_db, monkeypatch):
        """Test login with firebase_token when user not in Firestore"""
        # Mock Firestore - user not found
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "verify_id_token", Mock(return_value={"uid": "test_user"}))
        
        payload = {
            "firebase_token": "valid_token"
        }
        
        response = client.post("/api/users/auth/login", json=payload)
        
        assert response.status_code == 404
        assert "User profile not found" in response.get_json()["error"]
    
    def test_login_requests_exception(self, client, mock_db, monkeypatch):
        """Test login when requests library raises exception"""
        import requests
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('requests.post', side_effect=requests.RequestException("Network error")):
            payload = {
                "email": "test@example.com",
                "password": "password123"
            }
            
            response = client.post("/api/users/auth/login", json=payload)
        
        assert response.status_code == 500
        assert "Authentication service error" in response.get_json()["error"]
    
    def test_login_firebase_token_generic_exception(self, client, mock_db, monkeypatch):
        """Test login with firebase_token when generic exception occurs"""
        # Mock Firestore - raises exception
        mock_db.collection.side_effect = Exception("Database error")
        
        # Mock Firebase Auth - valid token
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "verify_id_token", Mock(return_value={"uid": "test_user"}))
        
        payload = {
            "firebase_token": "valid_token"
        }
        
        response = client.post("/api/users/auth/login", json=payload)
        
        assert response.status_code == 500
        assert "Login failed" in response.get_json()["error"]
    
    def test_login_generic_exception(self, client, mock_db, monkeypatch):
        """Test login when generic exception occurs in main flow"""
        # Mock Firebase REST API to succeed first, then Firestore fails
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "idToken": "test_token",
            "localId": "test_user"
        }
        
        # Mock Firestore to raise exception when getting user
        mock_doc_ref = Mock()
        mock_doc_ref.get.side_effect = Exception("Unexpected database error")
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('requests.post', return_value=mock_response):
            payload = {
                "email": "test@example.com",
                "password": "password123"
            }
            
            response = client.post("/api/users/auth/login", json=payload)
        
        assert response.status_code == 500
        assert "Login failed" in response.get_json()["error"]

    def test_login_fallback_no_api_key_success(self, client, mock_db, monkeypatch):
        """Test login fallback path when FIREBASE_WEB_API_KEY is not set"""
        # Import auth module to patch its FIREBASE_WEB_API_KEY
        from backend.api import auth as auth_module
        
        # Mock no API key (fallback path)
        monkeypatch.setattr(auth_module, "FIREBASE_WEB_API_KEY", None)
        
        # Mock Firestore - user exists
        mock_user_doc = Mock()
        mock_user_doc.id = "user_123"
        mock_user_doc.to_dict.return_value = {
            "name": "Test User",
            "email": "test@example.com"
        }
        
        # Mock the where().limit().stream() chain
        mock_stream = [mock_user_doc]
        mock_query = Mock()
        mock_query.stream.return_value = mock_stream
        mock_limit = Mock(return_value=mock_query)
        mock_where = Mock(return_value=Mock(limit=mock_limit))
        mock_collection = Mock(where=mock_where)
        
        # Mock document retrieval
        mock_doc_snapshot = Mock()
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = {
            "name": "Test User",
            "email": "test@example.com"
        }
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc_snapshot
        
        # Set up mock_db
        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth to create custom token
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "create_custom_token", Mock(return_value=b"custom_token_123"))
        
        payload = {
            "email": "test@example.com",
            "password": "password123"
        }
        
        response = client.post("/api/users/auth/login", json=payload)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["user"]["email"] == "test@example.com"
        assert data["user"]["name"] == "Test User"
        assert "firebaseToken" in data
    
    def test_login_fallback_no_api_key_user_not_found(self, client, mock_db, monkeypatch):
        """Test login fallback path when user doesn't exist in Firestore"""
        # Import auth module to patch its FIREBASE_WEB_API_KEY
        from backend.api import auth as auth_module
        
        # Mock no API key (fallback path)
        monkeypatch.setattr(auth_module, "FIREBASE_WEB_API_KEY", None)
        
        # Mock Firestore - user not found
        mock_query = Mock()
        mock_query.stream.return_value = []
        mock_limit = Mock(return_value=mock_query)
        mock_where = Mock(return_value=Mock(limit=mock_limit))
        mock_collection = Mock(where=mock_where)
        
        mock_db.collection.return_value = mock_collection
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "email": "nonexistent@example.com",
            "password": "password123"
        }
        
        response = client.post("/api/users/auth/login", json=payload)
        
        assert response.status_code == 404
        assert "User not found" in response.get_json()["error"]


class TestVerifyToken:
    """Test token verification endpoint"""
    
    def test_verify_token_success(self, client, mock_db, monkeypatch):
        """Test successful token verification"""
        # Mock Firestore
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "user_id": "test_user",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "verify_id_token", Mock(return_value={"uid": "test_user"}))
        
        payload = {
            "firebase_token": "valid_token"
        }
        
        response = client.post("/api/users/auth/verify", json=payload)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] == True
        assert "user" in data
    
    def test_verify_token_missing_token(self, client, mock_db, monkeypatch):
        """Test verification with missing token"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post("/api/users/auth/verify", json={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] == False
        assert "required" in data["error"].lower()
    
    def test_verify_token_invalid(self, client, mock_db, monkeypatch):
        """Test verification with invalid token"""
        # Mock Firebase Auth - invalid token
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "verify_id_token", Mock(side_effect=InvalidIdTokenError("Invalid")))
        
        payload = {
            "firebase_token": "invalid_token"
        }
        
        response = client.post("/api/users/auth/verify", json=payload)
        
        assert response.status_code == 401
        data = response.get_json()
        assert data["valid"] == False
        assert "Invalid or expired" in data["error"]
    
    def test_verify_token_expired(self, client, mock_db, monkeypatch):
        """Test verification with expired token"""
        # Mock Firebase Auth - expired token
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "verify_id_token", Mock(side_effect=ExpiredIdTokenError("Expired")))
        
        payload = {
            "firebase_token": "expired_token"
        }
        
        response = client.post("/api/users/auth/verify", json=payload)
        
        assert response.status_code == 401
        data = response.get_json()
        assert data["valid"] == False
    
    def test_verify_token_user_not_found(self, client, mock_db, monkeypatch):
        """Test verification when user not in Firestore"""
        # Mock Firestore - user not found
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_doc
        
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Mock Firebase Auth - valid token
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "verify_id_token", Mock(return_value={"uid": "test_user"}))
        
        payload = {
            "firebase_token": "valid_token"
        }
        
        response = client.post("/api/users/auth/verify", json=payload)
        
        assert response.status_code == 404
        data = response.get_json()
        assert data["valid"] == False
        assert "User not found" in data["error"]
    
    def test_verify_token_exception(self, client, mock_db, monkeypatch):
        """Test verification with generic exception"""
        # Mock Firestore - raises exception
        mock_db.collection.side_effect = Exception("Database error")
        
        # Mock Firebase Auth - valid token
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        monkeypatch.setattr(fake_auth, "verify_id_token", Mock(return_value={"uid": "test_user"}))
        
        payload = {
            "firebase_token": "valid_token"
        }
        
        response = client.post("/api/users/auth/verify", json=payload)
        
        assert response.status_code == 500
        data = response.get_json()
        assert data["valid"] == False
