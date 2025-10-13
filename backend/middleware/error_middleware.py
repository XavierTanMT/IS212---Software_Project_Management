"""
Error Handling Middleware
Centralized error handling and logging
"""
import logging
import traceback
from flask import request, jsonify
from datetime import datetime
from utils.validators import Helpers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ErrorHandler:
    """Centralized error handling service"""
    
    @staticmethod
    def handle_validation_error(error_data: dict) -> tuple:
        """Handle validation errors"""
        logger.warning(f"Validation error: {error_data}")
        
        error_message = "Validation failed"
        if isinstance(error_data, dict) and 'errors' in error_data:
            error_message = "; ".join(error_data['errors'])
        elif isinstance(error_data, str):
            error_message = error_data
        
        return jsonify(Helpers.build_error_response(
            message=error_message,
            code="VALIDATION_ERROR",
            details=error_data
        )), 400
    
    @staticmethod
    def handle_authentication_error(error_message: str = "Authentication failed") -> tuple:
        """Handle authentication errors"""
        logger.warning(f"Authentication error: {error_message}")
        
        return jsonify(Helpers.build_error_response(
            message=error_message,
            code="AUTHENTICATION_ERROR"
        )), 401
    
    @staticmethod
    def handle_authorization_error(error_message: str = "Insufficient permissions") -> tuple:
        """Handle authorization errors"""
        logger.warning(f"Authorization error: {error_message}")
        
        return jsonify(Helpers.build_error_response(
            message=error_message,
            code="AUTHORIZATION_ERROR"
        )), 403
    
    @staticmethod
    def handle_not_found_error(resource: str = "Resource") -> tuple:
        """Handle not found errors"""
        logger.info(f"Not found error: {resource}")
        
        return jsonify(Helpers.build_error_response(
            message=f"{resource} not found",
            code="NOT_FOUND"
        )), 404
    
    @staticmethod
    def handle_database_error(error: Exception) -> tuple:
        """Handle database errors"""
        logger.error(f"Database error: {str(error)}")
        
        return jsonify(Helpers.build_error_response(
            message="Database operation failed",
            code="DATABASE_ERROR"
        )), 500
    
    @staticmethod
    def handle_firebase_error(error: Exception) -> tuple:
        """Handle Firebase errors"""
        logger.error(f"Firebase error: {str(error)}")
        
        return jsonify(Helpers.build_error_response(
            message="Firebase operation failed",
            code="FIREBASE_ERROR"
        )), 500
    
    @staticmethod
    def handle_generic_error(error: Exception) -> tuple:
        """Handle generic errors"""
        logger.error(f"Unexpected error: {str(error)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return jsonify(Helpers.build_error_response(
            message="An unexpected error occurred",
            code="INTERNAL_ERROR"
        )), 500
    
    @staticmethod
    def log_request_info():
        """Log request information for debugging"""
        logger.info(f"Request: {request.method} {request.path}")
        logger.info(f"Headers: {dict(request.headers)}")
        if request.is_json:
            logger.info(f"Body: {request.get_json()}")

def register_error_handlers(app):
    """Register error handlers with Flask app"""
    
    @app.errorhandler(400)
    def handle_bad_request(error):
        return ErrorHandler.handle_validation_error("Bad request")
    
    @app.errorhandler(401)
    def handle_unauthorized(error):
        return ErrorHandler.handle_authentication_error("Unauthorized")
    
    @app.errorhandler(403)
    def handle_forbidden(error):
        return ErrorHandler.handle_authorization_error("Forbidden")
    
    @app.errorhandler(404)
    def handle_not_found(error):
        return ErrorHandler.handle_not_found_error("Endpoint")
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify(Helpers.build_error_response(
            message="Method not allowed",
            code="METHOD_NOT_ALLOWED"
        )), 405
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        return ErrorHandler.handle_generic_error(error)
    
    @app.errorhandler(Exception)
    def handle_unhandled_exception(error):
        return ErrorHandler.handle_generic_error(error)
