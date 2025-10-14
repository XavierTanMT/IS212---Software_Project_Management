import os
from flask import Flask, jsonify
from flask_cors import CORS

import firebase_admin
from firebase_admin import credentials

from api import (
    users_bp, tasks_bp, dashboard_bp,
    projects_bp, comments_bp, labels_bp, memberships_bp, attachments_bp
)

def init_firebase():
    cred_path = os.getenv("FIREBASE_CREDENTIALS_JSON") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path or not os.path.isfile(cred_path):
        raise RuntimeError("Missing Firebase credentials. Set FIREBASE_CREDENTIALS_JSON (or GOOGLE_APPLICATION_CREDENTIALS).")
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)

def create_app():
    init_firebase()
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    @app.get("/")
    def health():
        return jsonify({"status": "ok", "service": "task-manager-api"}), 200

    # Register all blueprints
    app.register_blueprint(users_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(comments_bp)
    app.register_blueprint(labels_bp)
    app.register_blueprint(memberships_bp)
    app.register_blueprint(attachments_bp)
    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)