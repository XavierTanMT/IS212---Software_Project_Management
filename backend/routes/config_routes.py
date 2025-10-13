from flask import Blueprint, jsonify
from config.settings import Settings
from utils.validators import Helpers

# Create blueprint
config_bp = Blueprint('config', __name__)

@config_bp.route('/firebase-config', methods=['GET'])
def get_firebase_config():
    """Get Firebase configuration for frontend"""
    try:
        # Return Firebase config from environment variables
        config = {
            'apiKey': Settings.FIREBASE_API_KEY,
            'authDomain': Settings.FIREBASE_AUTH_DOMAIN,
            'projectId': Settings.FIREBASE_PROJECT_ID,
            'storageBucket': Settings.FIREBASE_STORAGE_BUCKET,
            'messagingSenderId': Settings.FIREBASE_MESSAGING_SENDER_ID,
            'appId': Settings.FIREBASE_APP_ID,
            'measurementId': Settings.FIREBASE_MEASUREMENT_ID
        }
        
        return jsonify(Helpers.build_success_response(
            data=config,
            message='Firebase configuration retrieved successfully'
        )), 200
        
    except Exception as e:
        return jsonify(Helpers.build_error_response(f'Failed to get Firebase config: {str(e)}')), 500
