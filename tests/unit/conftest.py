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

# Create fake_firestore with __getattr__ to dynamically provide missing attributes
fake_firestore = types.ModuleType("firebase_admin.firestore")
fake_firestore.client = Mock()

# Create callable mocks for ArrayUnion and ArrayRemove
_array_union_mock = Mock(side_effect=lambda x: x)
_array_remove_mock = Mock(side_effect=lambda x: x)

# Use __getattr__ to handle attribute access
def _firestore_getattr(name):
    if name == "ArrayUnion":
        return _array_union_mock
    elif name == "ArrayRemove":
        return _array_remove_mock
    raise AttributeError(f"module 'firebase_admin.firestore' has no attribute '{name}'")

fake_firestore.__getattr__ = _firestore_getattr

# Also set them directly for direct attribute access
fake_firestore.ArrayUnion = _array_union_mock
fake_firestore.ArrayRemove = _array_remove_mock

fake_firebase.firestore = fake_firestore

sys.modules["firebase_admin"] = fake_firebase
sys.modules["firebase_admin.credentials"] = fake_credentials
sys.modules["firebase_admin.firestore"] = fake_firestore


@pytest.fixture(scope="session", autouse=True)
def setup_firebase_mocks():
    """Provide Firebase mocks to tests."""
    yield {
        "firebase": fake_firebase,
        "credentials": fake_credentials,
        "firestore": fake_firestore
    }


@pytest.fixture
def mock_db():
    """Create a fresh mock Firestore database for each test."""
    mock_db = Mock()
    mock_collection = Mock()
    mock_db.collection = Mock(return_value=mock_collection)
    return mock_db
