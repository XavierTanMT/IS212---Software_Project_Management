import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import firebase_admin
from firebase_admin import credentials
from datetime import datetime as _dt, timedelta as _td, timezone as _tz
from urllib.parse import quote_plus
import atexit

from api import (
    users_bp, tasks_bp, dashboard_bp, manager_bp,
    projects_bp, notes_bp, labels_bp, memberships_bp, attachments_bp, admin_bp
)
from api import notifications_bp
from firebase_utils import get_firebase_credentials

# Check if running in test/development mode without Firebase
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

def init_firebase():
    """Initialize Firebase, but allow app to run without it in dev mode."""
    if DEV_MODE:
        print("🔧 Running in DEV_MODE - Firebase disabled (will use mock data)")
        return False
    
    # Check if Firebase emulators are configured
    firestore_emulator = os.getenv("FIRESTORE_EMULATOR_HOST")
    auth_emulator = os.getenv("FIREBASE_AUTH_EMULATOR_HOST")
    
    if firestore_emulator or auth_emulator:
        print("🔥 Firebase Emulator Mode Detected")
        if firestore_emulator:
            print(f"   ✓ Firestore Emulator: {firestore_emulator}")
        if auth_emulator:
            print(f"   ✓ Auth Emulator: {auth_emulator}")
        
        # When using emulators, we need minimal credentials
        # Set GCLOUD_PROJECT if not already set
        if not os.getenv("GCLOUD_PROJECT"):
            os.environ["GCLOUD_PROJECT"] = "demo-no-project"
            print(f"   ✓ Set GCLOUD_PROJECT=demo-no-project")
        
        # For emulators, we need a dummy credentials file
        # Check if GOOGLE_APPLICATION_CREDENTIALS points to a valid file
        dummy_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not dummy_creds or not os.path.exists(dummy_creds):
            # Try to find the integration test dummy credentials
            import sys
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dummy_creds_path = os.path.join(repo_root, "tests", "integration", "dummy-credentials.json")
            if os.path.exists(dummy_creds_path):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = dummy_creds_path
                print(f"   ✓ Using dummy credentials for emulator")
        
        try:
            if not firebase_admin._apps:
                # Initialize with minimal options for emulator
                firebase_admin.initialize_app(options={'projectId': os.getenv("GCLOUD_PROJECT", "demo-no-project")})
                print("   ✓ Firebase initialized for EMULATOR use")
                print("   ⚠️  Using emulators - NO CLOUD QUOTA USED")
                return True
            return True
        except Exception as e:
            print(f"   ❌ Emulator initialization failed: {e}")
            return False
    
    # Normal cloud Firebase initialization
    try:
        # Use the unified credential loading function
        firebase_creds = get_firebase_credentials()
        
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_creds)
            firebase_admin.initialize_app(cred)
            print("✓ Firebase initialized successfully (CLOUD MODE)")
            print("⚠️  WARNING: Using cloud Firebase - may consume quota")
            return True
        return True
    except ValueError as e:
        print(f"⚠️  WARNING: {e}")
        print("   To use emulators instead, set FIRESTORE_EMULATOR_HOST=localhost:8080")
        print("   Or run with DEV_MODE=true for testing")
        return False
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        return False

def create_app(run_startup_checks: bool = False):
    """Create and configure the Flask application.

    Args:
        run_startup_checks: If True, run one-time startup checks that may
            perform internal requests (used by the real application startup).
            Defaults to False so tests and normal imports don't execute
            internal requests. The real server can enable these checks by
            calling `create_app(run_startup_checks=True)`.
    """
    app = Flask(__name__)
    
    # Configure CORS - MUST be before routes
    # Allow all origins for development (restrict in production)
    CORS(app, 
         resources={r"/*": {"origins": "*"}},
         allow_headers=["Content-Type", "X-User-Id", "Authorization"],
         methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
         supports_credentials=True)
    
    # Initialize Firebase (allow app to start even if Firebase fails)
    firebase_initialized = init_firebase()
    
    @app.get("/")
    def health():
        return jsonify({
            "status": "ok", 
            "service": "task-manager-api",
            "firebase": "connected" if firebase_initialized else "not configured"
        }), 200
    
    @app.errorhandler(500)
    def handle_500_error(e):
        """Handle 500 errors with CORS headers"""
        print(f"500 Error: {e}")
        response = jsonify({
            "error": "Internal server error",
            "message": str(e)
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-User-Id, Authorization')
        return response, 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle all uncaught exceptions with CORS headers"""
        print(f"Uncaught exception: {e}")
        import traceback
        traceback.print_exc()
        response = jsonify({
            "error": "Internal server error",
            "message": str(e),
            "type": type(e).__name__
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-User-Id, Authorization')
        return response, 500

    # Register all blueprints
    app.register_blueprint(users_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(manager_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(labels_bp)
    app.register_blueprint(memberships_bp)
    app.register_blueprint(attachments_bp)
    app.register_blueprint(admin_bp)  # ✅ ADD THIS LINE
    app.register_blueprint(notifications_bp)
    # Add OPTIONS handler for CORS preflight (register before any requests)
    @app.route('/<path:path>', methods=['OPTIONS'])
    def handle_options(path):
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-User-Id, Authorization')
        return response, 200

    # Optionally run one-time startup check for deadlines. This block issues
    # internal requests using the test client and therefore must be disabled
    # during tests to avoid locking the app from further setup calls. Only
    # run when explicitly requested by the caller (e.g. main()).
    if run_startup_checks:
        try:
            # Late import of notifications module
            from api import notifications as notifications_module

            # Compute today's UTC start/end to match the `due_today` behaviour
            now = _dt.now(_tz.utc)
            start = _dt(now.year, now.month, now.day, 0, 0, 0, tzinfo=_tz.utc)
            end = start + _td(days=1, microseconds=-1)
            start_iso = start.isoformat()
            end_iso = end.isoformat()

            # Run inside app and use the test client to POST to the endpoint so
            # we get a proper Flask Response object (avoids calling view
            # functions directly).
            with app.app_context():
                with app.test_client() as client:
                    try:
                        resp = client.post('/api/notifications/check-deadlines', query_string={"start_iso": start_iso, "end_iso": end_iso})
                    except Exception as e:
                        print(f"[startup] check_deadlines view raised: {e}")

                # If the initial UTC-day pass found nothing, attempt a retry
                try:
                    parsed = None
                    try:
                        if isinstance(resp, tuple) and hasattr(resp[0], 'get_json'):
                            print("hello world")
                            parsed = resp[0].get_json()
                            print("hello world 2")
                            print(f"[startup] check_deadlines response: {parsed}")
                        elif hasattr(resp, 'get_json'):
                            parsed = resp.get_json()
                            print(f"[startup] check_deadlines response: {parsed}")
                    except Exception:
                        parsed = None

                    if not parsed or parsed.get('checked', 0) == 0:
                        local_now = _dt.now().astimezone()
                        local_start = _dt(local_now.year, local_now.month, local_now.day, 0, 0, 0, tzinfo=local_now.tzinfo)
                        local_end = local_start + _td(days=1, microseconds=-1)
                        alt_start_iso = local_start.astimezone(_tz.utc).isoformat()
                        alt_end_iso = local_end.astimezone(_tz.utc).isoformat()
                        with app.test_client() as client:
                            try:
                                alt_resp = client.post('/api/notifications/check-deadlines', query_string={"start_iso": alt_start_iso, "end_iso": alt_end_iso})
                            except Exception as e:
                                print(f"[startup] alternate check_deadlines view raised: {e}")
                except Exception as e:
                    print(f"[startup] failed alternate local-day check: {e}")
        except Exception as e:
            print(f"[startup] failed to run check_deadlines: {e}")
    
    # NOTE: CORS OPTIONS handler registered earlier before startup requests
    
    return app

def main():
    """Main entry point for running the application."""
    # When running the real server, enable one-time startup checks. Call
    # `create_app(run_startup_checks=True)` when the function supports the
    # parameter. If a test has monkeypatched `create_app` with a zero-arg
    # replacement, temporarily set the env var for the call and restore it
    # afterwards to avoid persistent process-wide side-effects that break
    # subsequent tests.
    import inspect
    sig = inspect.signature(create_app)
    if 'run_startup_checks' in sig.parameters:
        app = create_app(run_startup_checks=True)
    else:
        # Temporarily set env var and restore after the call
        old = os.environ.get("RUN_STARTUP_CHECKS")
        os.environ["RUN_STARTUP_CHECKS"] = "true"
        try:
            app = create_app()
        finally:
            if old is None:
                os.environ.pop("RUN_STARTUP_CHECKS", None)
            else:
                os.environ["RUN_STARTUP_CHECKS"] = old
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

if __name__ == "__main__":  # pragma: no cover
    main()