from flask import jsonify, current_app, request
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask_jwt_extended.exceptions import JWTExtendedException
from app.utils.validators import ValidationError
import traceback
import logging


def register_error_handlers(app):
    """Register error handlers for the Flask application."""
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        """Handle custom validation errors."""
        return jsonify({
            'error': 'Validation Error',
            'message': str(error),
            'status_code': 400
        }), 400
    
    @app.errorhandler(400)
    def handle_bad_request(error):
        """Handle bad request errors."""
        return jsonify({
            'error': 'Bad Request',
            'message': 'The request could not be understood or was missing required parameters',
            'status_code': 400
        }), 400
    
    @app.errorhandler(401)
    def handle_unauthorized(error):
        """Handle unauthorized errors."""
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication is required to access this resource',
            'status_code': 401
        }), 401
    
    @app.errorhandler(403)
    def handle_forbidden(error):
        """Handle forbidden errors."""
        return jsonify({
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource',
            'status_code': 403
        }), 403
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle not found errors."""
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found',
            'status_code': 404
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle method not allowed errors."""
        return jsonify({
            'error': 'Method Not Allowed',
            'message': f'The {request.method} method is not allowed for this endpoint',
            'status_code': 405
        }), 405
    
    @app.errorhandler(409)
    def handle_conflict(error):
        """Handle conflict errors."""
        return jsonify({
            'error': 'Conflict',
            'message': 'The request conflicts with the current state of the server',
            'status_code': 409
        }), 409
    
    @app.errorhandler(413)
    def handle_payload_too_large(error):
        """Handle payload too large errors."""
        return jsonify({
            'error': 'Payload Too Large',
            'message': 'The uploaded file is too large',
            'status_code': 413
        }), 413
    
    @app.errorhandler(422)
    def handle_unprocessable_entity(error):
        """Handle unprocessable entity errors."""
        return jsonify({
            'error': 'Unprocessable Entity',
            'message': 'The request was well-formed but was unable to be followed due to semantic errors',
            'status_code': 422
        }), 422
    
    @app.errorhandler(429)
    def handle_rate_limit_exceeded(error):
        """Handle rate limit exceeded errors."""
        return jsonify({
            'error': 'Rate Limit Exceeded',
            'message': 'Too many requests. Please try again later',
            'status_code': 429,
            'retry_after': getattr(error, 'retry_after', None)
        }), 429
    
    @app.errorhandler(500)
    def handle_internal_server_error(error):
        """Handle internal server errors."""
        app.logger.error(f'Internal Server Error: {error}')
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An internal server error occurred',
            'status_code': 500
        }), 500
    
    @app.errorhandler(502)
    def handle_bad_gateway(error):
        """Handle bad gateway errors."""
        return jsonify({
            'error': 'Bad Gateway',
            'message': 'The server received an invalid response from an upstream server',
            'status_code': 502
        }), 502
    
    @app.errorhandler(503)
    def handle_service_unavailable(error):
        """Handle service unavailable errors."""
        return jsonify({
            'error': 'Service Unavailable',
            'message': 'The server is temporarily unavailable',
            'status_code': 503
        }), 503
    
    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        """Handle database integrity errors."""
        app.logger.error(f'Database Integrity Error: {error}')
        
        # Common integrity error messages
        error_message = str(error.orig)
        
        if 'duplicate key value' in error_message.lower():
            if 'username' in error_message.lower():
                message = 'Username already exists'
            elif 'email' in error_message.lower():
                message = 'Email address already exists'
            else:
                message = 'A record with this information already exists'
        elif 'foreign key constraint' in error_message.lower():
            message = 'Referenced record does not exist'
        elif 'check constraint' in error_message.lower():
            message = 'Data violates database constraints'
        else:
            message = 'Database constraint violation'
        
        return jsonify({
            'error': 'Database Constraint Violation',
            'message': message,
            'status_code': 409
        }), 409
    
    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error):
        """Handle general database errors."""
        app.logger.error(f'Database Error: {error}')
        return jsonify({
            'error': 'Database Error',
            'message': 'A database error occurred',
            'status_code': 500
        }), 500
    
    @app.errorhandler(JWTExtendedException)
    def handle_jwt_exceptions(error):
        """Handle JWT related exceptions."""
        app.logger.warning(f'JWT Error: {error}')
        
        error_type = type(error).__name__
        
        if 'ExpiredSignature' in error_type:
            message = 'Token has expired'
        elif 'InvalidToken' in error_type:
            message = 'Invalid token'
        elif 'DecodeError' in error_type:
            message = 'Token decode error'
        elif 'RevokedToken' in error_type:
            message = 'Token has been revoked'
        elif 'NoAuthorization' in error_type:
            message = 'Authorization token is required'
        elif 'InvalidHeader' in error_type:
            message = 'Invalid authorization header'
        else:
            message = 'Authentication error'
        
        return jsonify({
            'error': 'Authentication Error',
            'message': message,
            'status_code': 401
        }), 401
    
    @app.errorhandler(FileNotFoundError)
    def handle_file_not_found(error):
        """Handle file not found errors."""
        app.logger.error(f'File Not Found: {error}')
        return jsonify({
            'error': 'File Not Found',
            'message': 'The requested file was not found',
            'status_code': 404
        }), 404
    
    @app.errorhandler(PermissionError)
    def handle_permission_error(error):
        """Handle permission errors."""
        app.logger.error(f'Permission Error: {error}')
        return jsonify({
            'error': 'Permission Error',
            'message': 'Insufficient permissions to perform this operation',
            'status_code': 403
        }), 403
    
    @app.errorhandler(ConnectionError)
    def handle_connection_error(error):
        """Handle connection errors."""
        app.logger.error(f'Connection Error: {error}')
        return jsonify({
            'error': 'Connection Error',
            'message': 'Unable to connect to external service',
            'status_code': 503
        }), 503
    
    @app.errorhandler(TimeoutError)
    def handle_timeout_error(error):
        """Handle timeout errors."""
        app.logger.error(f'Timeout Error: {error}')
        return jsonify({
            'error': 'Timeout Error',
            'message': 'Request timed out',
            'status_code': 504
        }), 504
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle generic HTTP exceptions."""
        return jsonify({
            'error': error.name,
            'message': error.description,
            'status_code': error.code
        }), error.code
    
    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        """Handle any unhandled exceptions."""
        app.logger.error(f'Unhandled Exception: {error}', exc_info=True)
        
        # Don't expose internal errors in production
        if app.config.get('DEBUG'):
            message = str(error)
        else:
            message = 'An unexpected error occurred'
        
        return jsonify({
            'error': 'Internal Server Error',
            'message': message,
            'status_code': 500
        }), 500

def create_error_response(error_type, message, status_code=400, **kwargs):
    """Create a standardized error response."""
    response = {
        'error': error_type,
        'message': message,
        'status_code': status_code
    }
    response.update(kwargs)
    return jsonify(response), status_code

def create_validation_error_response(errors):
    """Create a validation error response with multiple errors."""
    return jsonify({
        'error': 'Validation Error',
        'message': 'Request validation failed',
        'errors': errors,
        'status_code': 400
    }), 400

def create_success_response(data=None, message=None, status_code=200, **kwargs):
    """Create a standardized success response."""
    response = {
        'success': True,
        'status_code': status_code
    }
    
    if message:
        response['message'] = message
    
    if data is not None:
        response['data'] = data
    
    response.update(kwargs)
    return jsonify(response), status_code 