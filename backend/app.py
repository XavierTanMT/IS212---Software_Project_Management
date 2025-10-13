from flask import Flask
from flask_cors import CORS
from config.settings import Settings
from config.firebase_config import firebase_config
from middleware.error_middleware import register_error_handlers

def create_app():
    """Create and configure Flask application"""
    
    # Validate settings
    Settings.validate()
    
    app = Flask(__name__)
    app.config.from_object(Settings)
    
    # Initialize CORS with more permissive settings for development
    if Settings.FLASK_ENV == 'development':
        CORS(app, origins='*', supports_credentials=True)
    else:
        CORS(app, origins=Settings.CORS_ORIGINS, supports_credentials=True)
    
    # Initialize Firebase (this will happen when firebase_config is imported)
    try:
        firebase_config  # This triggers Firebase initialization
        print("✅ Firebase configuration loaded successfully")
    except Exception as e:
        print(f"❌ Firebase configuration failed: {e}")
        raise
    
    # Register blueprints
    from routes.auth_routes import auth_bp
    from routes.user_routes import user_bp
    from routes.task_routes import task_bp
    from routes.project_routes import project_bp
    from routes.config_routes import config_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(task_bp, url_prefix='/api/tasks')
    app.register_blueprint(project_bp, url_prefix='/api/projects')
    app.register_blueprint(config_bp, url_prefix='/api/config')
    
    # Register error handlers
    register_error_handlers(app)
    
    @app.route('/')
    def health_check():
        return {
            'status': 'healthy',
            'message': 'IS212 Task Management API',
            'version': '1.0.0'
        }
    
    @app.route('/api/health')
    def api_health():
        return {
            'status': 'healthy',
            'firebase_connected': True,
            'project_id': Settings.FIREBASE_PROJECT_ID
        }
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=Settings.DEBUG)
