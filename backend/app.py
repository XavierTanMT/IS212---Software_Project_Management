import os
from flask import Flask, jsonify
from flask_cors import CORS

import firebase_admin
from firebase_admin import credentials

from api import (
    users_bp, tasks_bp, dashboard_bp,
    projects_bp, notes_bp, labels_bp, memberships_bp, attachments_bp
)

# Check if running in test/development mode without Firebase
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

def init_firebase():
    """Initialize Firebase, but allow app to run without it in dev mode."""
    if DEV_MODE:
        print("🔧 Running in DEV_MODE - Firebase disabled (will use mock data)")
        return False
    
    cred_path = os.getenv("FIREBASE_CREDENTIALS_JSON") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path:
        print("⚠️  WARNING: No Firebase credentials environment variable set.")
        print("   Set FIREBASE_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS")
        print("   Or run with DEV_MODE=true for testing")
        return False
    
    if not os.path.isfile(cred_path):
        print(f"⚠️  WARNING: Firebase credentials file not found: {cred_path}")
        return False
    
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("✓ Firebase initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Firebase initialization failed: {e}")
            return False
    return True

def create_app():
    app = Flask(__name__)
    
    # Configure CORS - MUST be before routes
    # Allow all origins for development (restrict in production)
    CORS(app, 
         resources={r"/*": {"origins": "*"}},
         allow_headers=["Content-Type", "X-User-Id"],
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
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-User-Id')
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
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-User-Id')
        return response, 500

    # Register all blueprints
    app.register_blueprint(users_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(labels_bp)
    app.register_blueprint(memberships_bp)
    app.register_blueprint(attachments_bp)
    
    # Add OPTIONS handler for CORS preflight
    @app.route('/<path:path>', methods=['OPTIONS'])
    def handle_options(path):
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-User-Id')
        return response, 200
    
    return app

def main():
    """Main entry point for running the application."""
    app = create_app()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

if __name__ == "__main__":  # pragma: no cover
    main()