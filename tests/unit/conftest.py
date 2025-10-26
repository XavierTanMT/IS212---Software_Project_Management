"""Shared pytest configuration for unit tests."""
import sys
import os
import types
from unittest.mock import Mock
import pytest

# Ensure repo root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# Mock firebase_admin at module level BEFORE any other imports
fake_firebase = types.ModuleType("firebase_admin")
fake_firebase._apps = []

fake_credentials = types.ModuleType("firebase_admin.credentials")
def _dummy_certificate(path):
    class _C: pass
    return _C()

fake_credentials.Certificate = _dummy_certificate
fake_firebase.credentials = fake_credentials
fake_firebase.initialize_app = lambda cred: None

# Create fake_auth module for Firebase Auth
fake_auth = types.ModuleType("firebase_admin.auth")

# Add exception classes
class UserNotFoundError(Exception):
    """Firebase Auth UserNotFoundError exception"""
    pass

class EmailAlreadyExistsError(Exception):
    """Firebase Auth EmailAlreadyExistsError exception"""
    pass

class UidAlreadyExistsError(Exception):
    """Firebase Auth UidAlreadyExistsError exception"""
    pass

class InvalidIdTokenError(Exception):
    """Firebase Auth InvalidIdTokenError exception"""
    pass

class ExpiredIdTokenError(Exception):
    """Firebase Auth ExpiredIdTokenError exception"""
    pass

fake_auth.UserNotFoundError = UserNotFoundError
fake_auth.EmailAlreadyExistsError = EmailAlreadyExistsError
fake_auth.UidAlreadyExistsError = UidAlreadyExistsError
fake_auth.InvalidIdTokenError = InvalidIdTokenError
fake_auth.ExpiredIdTokenError = ExpiredIdTokenError
fake_auth.create_user = Mock(return_value=Mock(uid="mock_uid"))
fake_auth.get_user = Mock()
fake_auth.get_user_by_email = Mock()
fake_auth.update_user = Mock()
fake_auth.delete_user = Mock()
fake_auth.create_custom_token = Mock(return_value=b"mock_custom_token")
fake_auth.verify_id_token = Mock(return_value={"uid": "mock_uid"})
fake_firebase.auth = fake_auth

# Create fake_firestore with __getattr__ to dynamically provide missing attributes
fake_firestore = types.ModuleType("firebase_admin.firestore")
fake_firestore.client = Mock()

# Create callable mocks for ArrayUnion and ArrayRemove
_array_union_mock = Mock(side_effect=lambda x: x)
_array_remove_mock = Mock(side_effect=lambda x: x)

# Create Query class with constants
class QueryMock:
    DESCENDING = "DESCENDING"
    ASCENDING = "ASCENDING"

# Use __getattr__ to handle attribute access
def _firestore_getattr(name):
    if name == "ArrayUnion":
        return _array_union_mock
    elif name == "ArrayRemove":
        return _array_remove_mock
    elif name == "Query":
        return QueryMock
    raise AttributeError(f"module 'firebase_admin.firestore' has no attribute '{name}'")

fake_firestore.__getattr__ = _firestore_getattr

# Also set them directly for direct attribute access
fake_firestore.ArrayUnion = _array_union_mock
fake_firestore.ArrayRemove = _array_remove_mock
fake_firestore.Query = QueryMock

fake_firebase.firestore = fake_firestore

sys.modules["firebase_admin"] = fake_firebase
sys.modules["firebase_admin.credentials"] = fake_credentials
sys.modules["firebase_admin.auth"] = fake_auth
sys.modules["firebase_admin.firestore"] = fake_firestore


@pytest.fixture(scope="session", autouse=True)
def setup_firebase_mocks():
    """Provide Firebase mocks to tests."""
    yield {
        "firebase": fake_firebase,
        "credentials": fake_credentials,
        "firestore": fake_firestore
    }


@pytest.fixture(autouse=True)
def reset_mocks(mock_db):
    """Reset all Firebase mocks before each test to prevent state pollution."""
    # Reset auth mocks
    fake_auth.create_user.reset_mock()
    fake_auth.get_user.reset_mock()
    fake_auth.get_user_by_email.reset_mock()
    fake_auth.update_user.reset_mock()
    fake_auth.delete_user.reset_mock()
    fake_auth.create_custom_token.reset_mock()
    fake_auth.verify_id_token.reset_mock()
    
    # Set default return values
    fake_auth.create_user.return_value = Mock(uid="mock_uid")
    fake_auth.verify_id_token.return_value = {"uid": "mock_uid"}
    
    # Reset firestore client mock and configure it to return our fresh mock_db
    fake_firestore.client.reset_mock()
    fake_firestore.client.return_value = mock_db
    
    yield
    
    # Clean up after test
    fake_auth.create_user.reset_mock()
    fake_auth.get_user.reset_mock()
    fake_auth.get_user_by_email.reset_mock()
    fake_auth.update_user.reset_mock()
    fake_auth.delete_user.reset_mock()
    fake_auth.create_custom_token.reset_mock()
    fake_auth.verify_id_token.reset_mock()
    fake_firestore.client.reset_mock()


@pytest.fixture
def mock_db():
    """Create a fresh mock Firestore database for each test.
    
    This mock is designed to be easily configurable by tests.
    Tests can override specific behaviors by setting return values directly.
    
    Example usage in tests:
        # Simple override
        mock_db.collection.return_value.document.return_value.get.return_value.exists = True
        
        # Or with more control
        mock_collection = Mock()
        mock_collection.document.return_value.get.return_value.exists = True
        mock_db.collection = Mock(return_value=mock_collection)
    """
    mock_db = Mock()
    
    # Create default collection mock with common methods
    mock_collection = Mock()
    mock_doc_ref = Mock()
    
    # Mock document reference with proper methods
    mock_doc_ref.set = Mock()
    mock_doc_ref.update = Mock()
    mock_doc_ref.delete = Mock()
    
    # Mock get() to return a document snapshot
    mock_snapshot = Mock()
    mock_snapshot.exists = False  # Default to not existing
    mock_snapshot.to_dict = Mock(return_value={})
    mock_snapshot.id = "mock_doc_id"
    mock_doc_ref.get = Mock(return_value=mock_snapshot)
    
    # Mock document() method
    mock_collection.document = Mock(return_value=mock_doc_ref)
    mock_collection.add = Mock(return_value=(None, mock_doc_ref))
    
    # Mock stream() and get() to return empty list by default
    mock_collection.stream = Mock(return_value=[])
    mock_collection.get = Mock(return_value=[])
    
    # Mock where(), order_by(), and limit() for query chaining
    # These return the collection itself to allow chaining
    mock_collection.where = Mock(return_value=mock_collection)
    mock_collection.order_by = Mock(return_value=mock_collection)
    mock_collection.limit = Mock(return_value=mock_collection)
    
    # Set up collection() to return the default collection
    # Tests can override this with mock_db.collection = Mock(return_value=custom_collection)
    mock_db.collection = Mock(return_value=mock_collection)
    
    return mock_db


# Store registered blueprints to avoid re-registration
_registered_blueprints = set()


@pytest.fixture
def app():
    """Create a Flask app for testing with all blueprints registered once."""
    from flask import Flask
    
    # Import all blueprints
    from backend.api import (
        users_bp, projects_bp, tasks_bp,
        labels_bp, notes_bp, attachments_bp, memberships_bp, dashboard_bp, manager_bp
    )
    
    # Create a fresh app each time
    test_app = Flask('test_app')
    test_app.config['TESTING'] = True
    
    # Register all blueprints to ensure all endpoints are available
    blueprints = [
        users_bp, projects_bp, tasks_bp, labels_bp,
        notes_bp, attachments_bp, memberships_bp, dashboard_bp, manager_bp
    ]
    
    for bp in blueprints:
        # Check if already registered on THIS app instance
        if bp.name not in [b.name for b in test_app.blueprints.values()]:
            test_app.register_blueprint(bp)
    
    return test_app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()

# =====================================================
# Chainable Firestore mock helper for chained where().where().stream()
# =====================================================
from unittest.mock import Mock

class _ChainableQuery:
    """Allows Firestore-like chaining in tests."""
    def __init__(self, results):
        self._results = results

    def where(self, *args, **kwargs):
        # Return self to allow chaining
        return self

    def stream(self):
        return self._results

def make_tasks_collection(created_results, assigned_results):
    """Return a mock 'tasks' collection with chainable where() for tests."""
    tasks_collection = Mock()

    def first_where(field, op, value):
        if isinstance(field, str) and field.startswith("created_by."):
            return _ChainableQuery(created_results)
        if isinstance(field, str) and field.startswith("assigned_to."):
            return _ChainableQuery(assigned_results)
        return _ChainableQuery([])

    tasks_collection.where = Mock(side_effect=first_where)
    return tasks_collection
