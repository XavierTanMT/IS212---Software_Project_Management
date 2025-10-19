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

fake_firestore = types.ModuleType("firebase_admin.firestore")
fake_firestore.client = Mock()
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
