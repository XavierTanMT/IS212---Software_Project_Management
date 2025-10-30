"""Shared pytest configuration for integration tests."""
import sys
import os
import json
import pytest
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure repo root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# # CRITICAL: Clean up unit test mocks IMMEDIATELY at module load time
# # This must happen BEFORE any other imports in this file
# print("=" * 80)
# print("INTEGRATION TEST SETUP: Cleaning up unit test mocks...")
# print("=" * 80)

# for module_name in list(sys.modules.keys()):
#     if module_name.startswith('firebase_admin'):
#         module = sys.modules[module_name]
#         if not hasattr(module, '__file__'):
#             print(f"  Removing mock Firebase module: {module_name}")
#             del sys.modules[module_name]

# # Remove backend modules that may have imported mocked firebase
# backend_modules = [m for m in sys.modules.keys() if m.startswith('backend')]
# for module_name in backend_modules:
#     print(f"  Removing backend module: {module_name}")
#     del sys.modules[module_name]

# print("=" * 80)


# DO NOT import Firebase at module level - use lazy imports to avoid slowdown
# This makes test collection much faster

_firebase_initialized = False

def ensure_firebase_initialized():
    """Ensure Firebase is initialized exactly once. Uses lazy imports for speed."""
    global _firebase_initialized
    
    # Lazy import - only load when actually needed
    import firebase_admin
    from firebase_admin import credentials
    from backend.firebase_utils import get_firebase_credentials
    
    # Check if firebase_admin has any apps - this is the real indicator
    if firebase_admin._apps:
        _firebase_initialized = True
        return
    
    # If we thought we initialized but _apps is empty, we need to reinitialize
    # (This can happen when modules are cleaned up between test runs)
    if _firebase_initialized and not firebase_admin._apps:
        _firebase_initialized = False
    
    if not _firebase_initialized:
        try:
            firebase_creds = get_firebase_credentials()
            cred = credentials.Certificate(firebase_creds)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            print("✓ Firebase initialized successfully")
        except Exception as e:
            print(f"✗ Firebase initialization failed: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to initialize Firebase: {e}")


@pytest.fixture
def app():
    """Create Flask application for testing."""
    # Ensure Firebase is properly initialized before creating app
    ensure_firebase_initialized()
    
    # Import and create the app
    # The cleanup_unit_test_mocks fixture ensures we're using real Firebase
    from backend.app import create_app
    
    app = create_app()
    app.config['TESTING'] = True
    
    yield app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def db():
    """Get real Firestore database instance."""
    # Ensure Firebase is initialized before creating client
    ensure_firebase_initialized()
    
    # CRITICAL: Import firestore directly to avoid unit test mocks
    # The unit test conftest may have monkeypatched firebase_admin in sys.modules
    # We need to use the REAL firestore module we imported at the top of this file
    from firebase_admin import firestore as real_firestore
    
    # Get Firestore client from the real module
    client = real_firestore.client()
    
    # Validate that we have a proper Firestore client with required methods
    if not hasattr(client, 'collection'):
        raise RuntimeError(
            f"Firestore client is invalid (type: {type(client)}). "
            "Check Firebase initialization and credentials."
        )
    
    return client


@pytest.fixture
def test_collection_prefix():
    """Prefix for test collections to isolate test data."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"test_{timestamp}"


@pytest.fixture
def cleanup_collections(db, test_collection_prefix):
    """Cleanup test collections after tests."""
    collections_to_clean = []
    
    yield collections_to_clean
    
    # Cleanup after test
    for collection_name in collections_to_clean:
        try:
            docs = db.collection(collection_name).limit(100).stream()
            for doc in docs:
                doc.reference.delete()
        except Exception as e:
            print(f"Warning: Could not clean up {collection_name}: {e}")


@pytest.fixture
def test_user(db, test_collection_prefix, cleanup_collections):
    """Create a test user in Firebase."""
    user_id = f"test_user_{datetime.now(timezone.utc).timestamp()}"
    collection_name = f"{test_collection_prefix}_users"
    cleanup_collections.append(collection_name)
    
    user_data = {
        "user_id": user_id,
        "email": f"{user_id}@test.com",
        "name": "Test User",
        "role": "Member",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Create user in Firestore
    db.collection(collection_name).document(user_id).set(user_data)
    
    yield {**user_data, "collection": collection_name}
    
    # Cleanup
    try:
        db.collection(collection_name).document(user_id).delete()
    except:
        pass


@pytest.fixture
def test_admin(db, test_collection_prefix, cleanup_collections):
    """Create a test admin user in Firebase."""
    user_id = f"test_admin_{datetime.now(timezone.utc).timestamp()}"
    collection_name = f"{test_collection_prefix}_users"
    cleanup_collections.append(collection_name)
    
    admin_data = {
        "user_id": user_id,
        "email": f"{user_id}@test.com",
        "name": "Test Admin",
        "role": "Admin",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Create admin in Firestore
    db.collection(collection_name).document(user_id).set(admin_data)
    
    yield {**admin_data, "collection": collection_name}
    
    # Cleanup
    try:
        db.collection(collection_name).document(user_id).delete()
    except:
        pass


@pytest.fixture
def test_project(db, test_user, test_collection_prefix, cleanup_collections):
    """Create a test project in Firebase."""
    project_id = f"test_project_{datetime.now(timezone.utc).timestamp()}"
    collection_name = f"{test_collection_prefix}_projects"
    cleanup_collections.append(collection_name)
    
    project_data = {
        "project_id": project_id,
        "name": "Test Project",
        "description": "A test project for integration testing",
        "created_by": {"user_id": test_user["user_id"], "email": test_user["email"]},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active"
    }
    
    db.collection(collection_name).document(project_id).set(project_data)
    
    yield {**project_data, "collection": collection_name}
    
    # Cleanup
    try:
        db.collection(collection_name).document(project_id).delete()
    except:
        pass


@pytest.fixture
def test_task(db, test_user, test_project, test_collection_prefix, cleanup_collections):
    """Create a test task in Firebase."""
    task_id = f"test_task_{datetime.now(timezone.utc).timestamp()}"
    collection_name = f"{test_collection_prefix}_tasks"
    cleanup_collections.append(collection_name)
    
    task_data = {
        "task_id": task_id,
        "title": "Test Task",
        "description": "A test task for integration testing",
        "status": "To Do",
        "priority": 5,
        "project_id": test_project["project_id"],
        "created_by": {"user_id": test_user["user_id"], "email": test_user["email"]},
        "assigned_to": None,
        "due_date": (datetime.now(timezone.utc)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_recurring": False,
        "labels": []
    }
    
    db.collection(collection_name).document(task_id).set(task_data)
    
    yield {**task_data, "collection": collection_name}
    
    # Cleanup
    try:
        db.collection(collection_name).document(task_id).delete()
    except:
        pass


@pytest.fixture
def auth_token(test_user):
    """Generate authentication token for test user."""
    try:
        # Lazy import to avoid loading Firebase at module level
        from firebase_admin import auth as firebase_auth
        
        # Create custom token for test user
        token = firebase_auth.create_custom_token(test_user["user_id"])
        return token.decode('utf-8') if isinstance(token, bytes) else token
    except Exception as e:
        # Return mock token if Firebase Auth fails
        return f"Bearer test_token_{test_user['user_id']}"


@pytest.fixture
def auth_headers(auth_token):
    """Create authentication headers for requests."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
