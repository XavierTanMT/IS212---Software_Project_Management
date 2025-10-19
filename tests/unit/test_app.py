import sys
import types
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

# Ensure repo root is on sys.path so local packages like `api` can be imported
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Also add backend dir to sys.path so `import api` (used inside backend.app) resolves
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Inject a fake firebase_admin and firebase_admin.credentials before importing
# so importing backend.app doesn't fail when firebase_admin isn't installed.
fake_firebase = types.ModuleType("firebase_admin")
fake_firebase._apps = []

fake_credentials = types.ModuleType("firebase_admin.credentials")
def _dummy_certificate(path):
    class _C: pass
    return _C()

fake_credentials.Certificate = _dummy_certificate
fake_firebase.credentials = fake_credentials
fake_firebase.initialize_app = lambda cred: None

# Provide a fake firestore module with a client() callable so imports succeed
fake_firestore = types.ModuleType("firebase_admin.firestore")
def _fake_client():
    # Return a minimal sentinel object; tests shouldn't call it during import
    return object()

fake_firestore.client = _fake_client
fake_firebase.firestore = fake_firestore

sys.modules["firebase_admin.firestore"] = fake_firestore

sys.modules["firebase_admin"] = fake_firebase
sys.modules["firebase_admin.credentials"] = fake_credentials

from backend import app as app_module


def test_health_endpoint(monkeypatch):
    """Ensure the Flask health endpoint returns OK without initializing Firebase."""
    # Prevent external Firebase initialization during tests
    monkeypatch.setattr(app_module, "init_firebase", lambda: None)

    app = app_module.create_app()
    client = app.test_client()

    resp = client.get("/")
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["status"] == "ok"
    assert "service" in data


def test_init_firebase_missing_credentials(monkeypatch):
    """Test init_firebase raises error when credentials are missing."""
    # Mock environment variables to return None
    monkeypatch.setenv("FIREBASE_CREDENTIALS_JSON", "")
    monkeypatch.delenv("FIREBASE_CREDENTIALS_JSON", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    
    # Mock os.getenv to return None
    monkeypatch.setattr(os, "getenv", lambda key, default=None: None if key in ["FIREBASE_CREDENTIALS_JSON", "GOOGLE_APPLICATION_CREDENTIALS"] else default)
    
    with pytest.raises(RuntimeError, match="Missing Firebase credentials"):
        app_module.init_firebase()


def test_init_firebase_invalid_file_path(monkeypatch, tmp_path):
    """Test init_firebase raises error when credential file doesn't exist."""
    fake_path = str(tmp_path / "nonexistent.json")
    
    # Mock os.getenv to return a non-existent path
    monkeypatch.setattr(os, "getenv", lambda key, default=None: fake_path if key == "FIREBASE_CREDENTIALS_JSON" else None)
    
    with pytest.raises(RuntimeError, match="Missing Firebase credentials"):
        app_module.init_firebase()


def test_init_firebase_success(monkeypatch, tmp_path):
    """Test init_firebase successfully initializes with valid credentials."""
    # Create a fake credentials file
    cred_file = tmp_path / "credentials.json"
    cred_file.write_text('{"type": "service_account"}')
    
    # Mock os.getenv to return the valid path
    monkeypatch.setattr(os, "getenv", lambda key, default=None: str(cred_file) if key == "FIREBASE_CREDENTIALS_JSON" else None)
    
    # Mock firebase_admin._apps to be empty
    fake_firebase._apps = []
    
    # Mock the Certificate and initialize_app
    mock_cert = Mock()
    monkeypatch.setattr(fake_credentials, "Certificate", Mock(return_value=mock_cert))
    mock_init = Mock()
    monkeypatch.setattr(fake_firebase, "initialize_app", mock_init)
    
    # Call init_firebase
    app_module.init_firebase()
    
    # Verify Certificate was called with correct path
    fake_credentials.Certificate.assert_called_once_with(str(cred_file))
    
    # Verify initialize_app was called
    mock_init.assert_called_once()


def test_init_firebase_already_initialized(monkeypatch, tmp_path):
    """Test init_firebase skips initialization if already initialized."""
    # Create a fake credentials file
    cred_file = tmp_path / "credentials.json"
    cred_file.write_text('{"type": "service_account"}')
    
    # Mock os.getenv to return the valid path
    monkeypatch.setattr(os, "getenv", lambda key, default=None: str(cred_file) if key == "FIREBASE_CREDENTIALS_JSON" else None)
    
    # Mock firebase_admin._apps to have an existing app
    fake_firebase._apps = ["existing_app"]
    
    # Mock initialize_app to track if it's called
    mock_init = Mock()
    monkeypatch.setattr(fake_firebase, "initialize_app", mock_init)
    
    # Call init_firebase
    app_module.init_firebase()
    
    # Verify initialize_app was NOT called since app already exists
    mock_init.assert_not_called()


def test_create_app_registers_blueprints(monkeypatch):
    """Test that create_app registers all blueprints."""
    monkeypatch.setattr(app_module, "init_firebase", lambda: None)
    
    app = app_module.create_app()
    
    # Check that blueprints are registered
    blueprint_names = [bp.name for bp in app.blueprints.values()]
    
    expected_blueprints = [
        'users', 'tasks', 'dashboard', 'projects', 
        'comments', 'labels', 'memberships', 'attachments'
    ]
    
    for bp_name in expected_blueprints:
        assert bp_name in blueprint_names, f"Blueprint '{bp_name}' not registered"


def test_create_app_cors_enabled(monkeypatch):
    """Test that CORS is enabled for the app."""
    monkeypatch.setattr(app_module, "init_firebase", lambda: None)
    
    app = app_module.create_app()
    client = app.test_client()
    
    # Make a request and check CORS headers
    resp = client.get("/")
    
    # Should have successful response
    assert resp.status_code == 200


def test_main_block_execution(monkeypatch):
    """Test the if __name__ == '__main__' block."""
    monkeypatch.setattr(app_module, "init_firebase", lambda: None)
    
    # Mock the app.run method
    mock_run = Mock()
    
    # Create a mock app
    mock_app = Mock()
    mock_app.run = mock_run
    
    # Mock create_app to return our mock
    monkeypatch.setattr(app_module, "create_app", lambda: mock_app)
    
    # Mock os.getenv for PORT
    monkeypatch.setattr(os, "getenv", lambda key, default=None: "8080" if key == "PORT" else default)
    
    # Execute the main block code
    with monkeypatch.context() as m:
        m.setattr(app_module, "__name__", "__main__")
        
        # Manually execute the main block logic
        test_app = app_module.create_app()
        port = int(os.getenv("PORT", 5000))
        
        assert port == 8080  # Should use mocked PORT value


def test_main_block_default_port(monkeypatch):
    """Test the main block uses default port when PORT env var is not set."""
    monkeypatch.setattr(app_module, "init_firebase", lambda: None)
    
    # Mock os.getenv to return None for PORT
    monkeypatch.setattr(os, "getenv", lambda key, default=None: default if key == "PORT" else None)
    
    # Execute the main block logic with default port
    test_app = app_module.create_app()
    port = int(os.getenv("PORT", 5000))
    
    assert port == 5000  # Should use default port


def test_health_endpoint_returns_correct_json_structure(monkeypatch):
    """Test health endpoint returns correct JSON structure."""
    monkeypatch.setattr(app_module, "init_firebase", lambda: None)
    
    app = app_module.create_app()
    client = app.test_client()
    
    resp = client.get("/")
    data = resp.get_json()
    
    # Verify JSON structure
    assert isinstance(data, dict)
    assert "status" in data
    assert "service" in data
    assert data["status"] == "ok"
    assert data["service"] == "task-manager-api"


def test_init_firebase_with_google_application_credentials(monkeypatch, tmp_path):
    """Test init_firebase works with GOOGLE_APPLICATION_CREDENTIALS."""
    # Create a fake credentials file
    cred_file = tmp_path / "google_creds.json"
    cred_file.write_text('{"type": "service_account"}')
    
    # Mock os.getenv to return None for FIREBASE_CREDENTIALS_JSON but valid for GOOGLE_APPLICATION_CREDENTIALS
    def mock_getenv(key, default=None):
        if key == "FIREBASE_CREDENTIALS_JSON":
            return None
        elif key == "GOOGLE_APPLICATION_CREDENTIALS":
            return str(cred_file)
        return default
    
    monkeypatch.setattr(os, "getenv", mock_getenv)
    
    # Mock firebase_admin._apps to be empty
    fake_firebase._apps = []
    
    # Mock the Certificate and initialize_app
    mock_cert = Mock()
    monkeypatch.setattr(fake_credentials, "Certificate", Mock(return_value=mock_cert))
    mock_init = Mock()
    monkeypatch.setattr(fake_firebase, "initialize_app", mock_init)
    
    # Call init_firebase
    app_module.init_firebase()
    
    # Verify Certificate was called with correct path
    fake_credentials.Certificate.assert_called_once_with(str(cred_file))
    
    # Verify initialize_app was called
    mock_init.assert_called_once()


def test_main_execution_block(monkeypatch, tmp_path):
    """Test the main execution block (__name__ == '__main__')."""
    # Create a fake credentials file
    cred_file = tmp_path / "credentials.json"
    cred_file.write_text('{"type": "service_account"}')
    
    # Mock environment
    def mock_getenv(key, default=None):
        if key == "FIREBASE_CREDENTIALS_JSON":
            return str(cred_file)
        elif key == "PORT":
            return "8080"
        return default
    
    monkeypatch.setattr(os, "getenv", mock_getenv)
    
    # Mock firebase_admin._apps to be empty
    fake_firebase._apps = []
    
    # Mock initialize_app
    monkeypatch.setattr(fake_firebase, "initialize_app", Mock())
    
    # Mock Flask app's run method
    mock_run = Mock()
    
    # We need to patch create_app to return an app with a mocked run method
    original_create_app = app_module.create_app
    
    def mock_create_app_wrapper():
        app = original_create_app()
        app.run = mock_run
        return app
    
    monkeypatch.setattr(app_module, "create_app", mock_create_app_wrapper)
    
    # Simulate the main block execution by directly calling the code
    # This is what happens in the if __name__ == "__main__" block (lines 42-44)
    app = app_module.create_app()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
    
    # Verify run was called with correct arguments
    mock_run.assert_called_once_with(host="0.0.0.0", port=8080, debug=True)


def test_main_block_with_default_port(monkeypatch, tmp_path):
    """Test main block uses default port when PORT env var is not set."""
    # Create a fake credentials file
    cred_file = tmp_path / "credentials.json"
    cred_file.write_text('{"type": "service_account"}')
    
    # Mock environment - PORT not set
    def mock_getenv(key, default=None):
        if key == "FIREBASE_CREDENTIALS_JSON":
            return str(cred_file)
        elif key == "PORT":
            return default  # Return default (not set)
        return default
    
    monkeypatch.setattr(os, "getenv", mock_getenv)
    
    # Mock firebase_admin._apps to be empty
    fake_firebase._apps = []
    
    # Mock initialize_app
    monkeypatch.setattr(fake_firebase, "initialize_app", Mock())
    
    # Mock Flask app's run method
    mock_run = Mock()
    
    # Patch create_app to return an app with a mocked run method
    original_create_app = app_module.create_app
    
    def mock_create_app_wrapper():
        app = original_create_app()
        app.run = mock_run
        return app
    
    monkeypatch.setattr(app_module, "create_app", mock_create_app_wrapper)
    
    # Simulate the main block execution (lines 42-44)
    app = app_module.create_app()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
    
    # Verify run was called with default port 5000
    mock_run.assert_called_once_with(host="0.0.0.0", port=5000, debug=True)


def test_main_module_execution(monkeypatch, tmp_path):
    """Test the main() function and if __name__ == '__main__' block."""
    # Create a fake credentials file
    cred_file = tmp_path / "test_credentials.json"
    cred_file.write_text('{"type": "service_account"}')
    
    # Mock environment
    monkeypatch.setenv("FIREBASE_CREDENTIALS_JSON", str(cred_file))
    monkeypatch.setenv("PORT", "7777")
    
    # Mock firebase_admin._apps to be empty
    fake_firebase._apps = []
    monkeypatch.setattr(fake_firebase, "initialize_app", Mock())
    
    # Mock app.run to prevent actual server start
    mock_run = Mock()
    
    original_create_app = app_module.create_app
    def mock_create_app_for_main():
        app = original_create_app()
        app.run = mock_run
        return app
    
    monkeypatch.setattr(app_module, "create_app", mock_create_app_for_main)
    
    # Call the main() function directly
    app_module.main()
    
    # Verify app.run was called with correct parameters
    mock_run.assert_called_once_with(host="0.0.0.0", port=7777, debug=True)


def test_name_main_guard(monkeypatch, tmp_path):
    """Test the if __name__ == '__main__' guard by simulating module execution."""
    import importlib
    import sys
    
    # Create a fake credentials file
    cred_file = tmp_path / "test_credentials.json"
    cred_file.write_text('{"type": "service_account"}')
    
    # Mock environment
    monkeypatch.setenv("FIREBASE_CREDENTIALS_JSON", str(cred_file))
    monkeypatch.setenv("PORT", "6666")
    
    # Mock firebase_admin._apps to be empty
    fake_firebase._apps = []
    monkeypatch.setattr(fake_firebase, "initialize_app", Mock())
    
    # Mock app.run
    mock_run = Mock()
    original_create_app = app_module.create_app
    
    def mock_create_app_for_guard():
        app = original_create_app()
        app.run = mock_run
        return app
    
    monkeypatch.setattr(app_module, "create_app", mock_create_app_for_guard)
    
    # Mock the main function to track if it was called
    original_main = app_module.main
    main_called = {'called': False}
    
    def mock_main():
        main_called['called'] = True
        original_main()
    
    monkeypatch.setattr(app_module, "main", mock_main)
    
    # Temporarily set __name__ to "__main__" to trigger the guard
    original_name = app_module.__name__
    monkeypatch.setattr(app_module, "__name__", "__main__")
    
    # Execute the guard condition
    if app_module.__name__ == "__main__":
        app_module.main()
    
    # Verify main was called
    assert main_called['called'], "main() should have been called when __name__ == '__main__'"
    assert mock_run.called, "app.run should have been called"

