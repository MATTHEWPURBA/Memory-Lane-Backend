from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt, verify_jwt_in_request
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta
import logging
import traceback
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app import db, redis_client
from app.models.user import User
from app.utils.validators import (
    validate_username, validate_email_address, validate_email_for_check, validate_password,
    ValidationError
)
from app.utils.error_handlers import create_error_response, create_success_response

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['OPTIONS'])
@auth_bp.route('/login', methods=['OPTIONS'])
@auth_bp.route('/check-username', methods=['OPTIONS'])
@auth_bp.route('/check-email', methods=['OPTIONS'])
def handle_preflight():
    """Handle CORS preflight requests."""
    response = jsonify({'status': 'ok'})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
        # Log the incoming request
        current_app.logger.info(f"Registration attempt from {request.remote_addr}")
        
        data = request.get_json()
        
        if not data:
            current_app.logger.warning("Registration attempt with no JSON data")
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        # Validate required fields
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not all([username, email, password]):
            missing_fields = []
            if not username:
                missing_fields.append('username')
            if not email:
                missing_fields.append('email')
            if not password:
                missing_fields.append('password')
            
            current_app.logger.warning(f"Registration attempt with missing fields: {missing_fields}")
            return create_error_response(
                'Missing Fields', 
                f'Required fields missing: {", ".join(missing_fields)}', 
                400
            )
        
        # Validate input data
        try:
            username_error = validate_username(username)
            if username_error:
                current_app.logger.warning(f"Username validation error: {username_error}")
                return create_error_response('Validation Error', username_error, 400)
            
            email_error = validate_email_address(email)
            if email_error:
                current_app.logger.warning(f"Email validation error: {email_error}")
                return create_error_response('Validation Error', email_error, 400)
            
            password_error = validate_password(password)
            if password_error:
                current_app.logger.warning(f"Password validation error: {password_error}")
                return create_error_response('Validation Error', password_error, 400)
        except ValidationError as e:
            current_app.logger.warning(f"Registration validation error: {str(e)}")
            return create_error_response('Validation Error', str(e), 400)
        
        # Check if user already exists
        try:
            if User.find_by_username(username):
                current_app.logger.warning(f"Registration attempt with existing username: {username}")
                return create_error_response('Username Taken', 'Username already exists', 409)
            
            if User.find_by_email(email):
                current_app.logger.warning(f"Registration attempt with existing email: {email}")
                return create_error_response('Email Taken', 'Email address already exists', 409)
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error checking user existence: {str(e)}")
            return create_error_response('Database Error', 'Unable to check user availability', 500)
        
        # Create new user
        try:
            user = User(
                username=username,
                email=email,
                password=password,
                display_name=data.get('display_name'),
                bio=data.get('bio')
            )
            
            db.session.add(user)
            db.session.commit()
            
            current_app.logger.info(f"User registered successfully: {username}")
            
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Database integrity error during registration: {str(e)}")
            
            # Check for specific integrity errors
            error_str = str(e.orig).lower()
            if 'username' in error_str and 'unique' in error_str:
                return create_error_response('Username Taken', 'Username already exists', 409)
            elif 'email' in error_str and 'unique' in error_str:
                return create_error_response('Email Taken', 'Email address already exists', 409)
            else:
                return create_error_response('Registration Failed', 'User creation failed due to database constraints', 409)
                
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error during registration: {str(e)}")
            return create_error_response('Database Error', 'Unable to create user account', 500)
        
        # Create tokens
        try:
            access_token = create_access_token(identity=str(user.user_id))
            refresh_token = create_refresh_token(identity=str(user.user_id))
        except Exception as e:
            current_app.logger.error(f"Token creation error: {str(e)}")
            return create_error_response('Authentication Error', 'Unable to create authentication tokens', 500)
        
        return create_success_response(
            data={
                'user': user.to_dict(include_private=True),
                'access_token': access_token,
                'refresh_token': refresh_token
            },
            message='User registered successfully',
            status_code=201
        )
        
    except ValidationError as e:
        current_app.logger.warning(f"Validation error in registration: {str(e)}")
        return create_error_response('Validation Error', str(e), 400)
    except BadRequest as e:
        current_app.logger.warning(f"Bad request in registration: {str(e)}")
        return create_error_response('Bad Request', str(e), 400)
    except Exception as e:
        current_app.logger.error(f"Unexpected error in registration: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return create_error_response('Registration Failed', 'An unexpected error occurred during registration', 500)

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user and return tokens."""
    try:
        # Log the incoming request
        current_app.logger.info(f"Login attempt from {request.remote_addr}")
        
        data = request.get_json()
        
        if not data:
            current_app.logger.warning("Login attempt with no JSON data")
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        # Get credentials
        username_or_email = data.get('username') or data.get('email')
        password = data.get('password')
        
        if not all([username_or_email, password]):
            missing_fields = []
            if not username_or_email:
                missing_fields.append('username/email')
            if not password:
                missing_fields.append('password')
            
            current_app.logger.warning(f"Login attempt with missing credentials: {missing_fields}")
            return create_error_response(
                'Missing Credentials', 
                f'Required credentials missing: {", ".join(missing_fields)}', 
                400
            )
        
        # Find user by username or email
        user = None
        try:
            if '@' in username_or_email:
                user = User.find_by_email(username_or_email)
            else:
                user = User.find_by_username(username_or_email)
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error during login lookup: {str(e)}")
            return create_error_response('Database Error', 'Unable to verify credentials', 500)
        
        # Check credentials
        if not user:
            current_app.logger.warning(f"Login attempt with non-existent user: {username_or_email}")
            return create_error_response(
                'Invalid Credentials', 
                'Invalid username/email or password', 
                401
            )
        
        if not user.check_password(password):
            current_app.logger.warning(f"Login attempt with wrong password for user: {username_or_email}")
            return create_error_response(
                'Invalid Credentials', 
                'Invalid username/email or password', 
                401
            )
        
        if not user.is_active:
            current_app.logger.warning(f"Login attempt for deactivated account: {username_or_email}")
            return create_error_response(
                'Account Deactivated', 
                'Your account has been deactivated', 
                403
            )
        
        # Update last active
        try:
            user.update_last_active()
            db.session.commit()
        except SQLAlchemyError as e:
            current_app.logger.warning(f"Failed to update last active for user {user.username}: {str(e)}")
            # Don't fail the login for this error
        
        # Create tokens
        try:
            access_token = create_access_token(identity=str(user.user_id))
            refresh_token = create_refresh_token(identity=str(user.user_id))
        except Exception as e:
            current_app.logger.error(f"Token creation error during login: {str(e)}")
            return create_error_response('Authentication Error', 'Unable to create authentication tokens', 500)
        
        current_app.logger.info(f"User logged in successfully: {user.username}")
        
        return create_success_response(
            data={
                'user': user.to_dict(include_private=True),
                'access_token': access_token,
                'refresh_token': refresh_token
            },
            message='Login successful'
        )
        
    except BadRequest as e:
        current_app.logger.warning(f"Bad request in login: {str(e)}")
        return create_error_response('Bad Request', str(e), 400)
    except Exception as e:
        current_app.logger.error(f"Unexpected error in login: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return create_error_response('Login Failed', 'An unexpected error occurred during login', 500)

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token using refresh token."""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return create_error_response(
                'Invalid User', 
                'User not found or deactivated', 
                401
            )
        
        # Create new access token
        access_token = create_access_token(identity=current_user_id)
        
        return create_success_response(
            data={'access_token': access_token},
            message='Token refreshed successfully'
        )
        
    except Exception as e:
        return create_error_response('Token Refresh Failed', str(e), 500)

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user by blacklisting current token."""
    try:
        jti = get_jwt()['jti']
        user_id = get_jwt_identity()
        
        # Add token to blacklist (Redis)
        redis_client.set(jti, '', ex=timedelta(hours=24))
        
        return create_success_response(message='Logout successful')
        
    except Exception as e:
        return create_error_response('Logout Failed', str(e), 500)

@auth_bp.route('/logout-all', methods=['POST'])
@jwt_required()
def logout_all():
    """Logout user from all devices by blacklisting all tokens."""
    try:
        user_id = get_jwt_identity()
        
        # In a real implementation, you'd keep track of all user tokens
        # For now, just blacklist current token
        jti = get_jwt()['jti']
        redis_client.set(jti, '', ex=timedelta(hours=24))
        
        return create_success_response(message='Logged out from all devices')
        
    except Exception as e:
        return create_error_response('Logout Failed', str(e), 500)

@auth_bp.route('/verify-token', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify if current token is valid."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            return create_error_response(
                'Invalid Token', 
                'Token is valid but user not found or deactivated', 
                401
            )
        
        return create_success_response(
            data={'user': user.to_dict()},
            message='Token is valid'
        )
        
    except Exception as e:
        return create_error_response('Token Verification Failed', str(e), 500)

@auth_bp.route('/change-password', methods=['PUT'])
@jwt_required()
def change_password():
    """Change user password."""
    try:
        data = request.get_json()
        
        if not data:
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not all([current_password, new_password]):
            return create_error_response(
                'Missing Fields', 
                'Current password and new password are required', 
                400
            )
        
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return create_error_response('User Not Found', 'User not found', 404)
        
        # Verify current password
        if not user.check_password(current_password):
            return create_error_response(
                'Invalid Password', 
                'Current password is incorrect', 
                401
            )
        
        # Validate new password
        new_password = validate_password(new_password)
        
        # Check if new password is different from current
        if user.check_password(new_password):
            return create_error_response(
                'Same Password', 
                'New password must be different from current password', 
                400
            )
        
        # Update password
        user.set_password(new_password)
        db.session.commit()
        
        # Blacklist current token to force re-login
        jti = get_jwt()['jti']
        redis_client.set(jti, '', ex=timedelta(hours=24))
        
        return create_success_response(message='Password changed successfully')
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Password Change Failed', str(e), 500)

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset (placeholder - would implement email sending)."""
    try:
        data = request.get_json()
        
        if not data:
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        email = data.get('email')
        
        if not email:
            return create_error_response('Missing Email', 'Email address is required', 400)
        
        # Validate email
        email = validate_email_address(email)
        
        # Find user by email
        user = User.find_by_email(email)
        
        # Always return success for security (don't reveal if email exists)
        if user and user.is_active:
            # TODO: Implement email sending with reset token
            # For now, just log that a reset was requested
            pass
        
        return create_success_response(
            message='If an account with that email exists, a password reset link has been sent'
        )
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Password Reset Failed', str(e), 500)

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password using reset token (placeholder)."""
    try:
        data = request.get_json()
        
        if not data:
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        reset_token = data.get('reset_token')
        new_password = data.get('new_password')
        
        if not all([reset_token, new_password]):
            return create_error_response(
                'Missing Fields', 
                'Reset token and new password are required', 
                400
            )
        
        # TODO: Implement token validation and password reset
        # For now, return not implemented
        return create_error_response(
            'Not Implemented', 
            'Password reset functionality not yet implemented', 
            501
        )
        
    except Exception as e:
        return create_error_response('Password Reset Failed', str(e), 500)

@auth_bp.route('/check-username', methods=['POST'])
def check_username():
    """Check if username is available."""
    try:
        # Log the incoming request
        current_app.logger.debug(f"Username availability check from {request.remote_addr}")
        current_app.logger.debug(f"Request headers: {dict(request.headers)}")
        current_app.logger.debug(f"Request method: {request.method}")
        
        # Check if request has JSON content
        if not request.is_json:
            current_app.logger.warning("Request is not JSON")
            return create_error_response('Invalid Request', 'Content-Type must be application/json', 400)
        
        data = request.get_json()
        current_app.logger.debug(f"Request data: {data}")
        current_app.logger.debug(f"Request content type: {request.content_type}")
        current_app.logger.debug(f"Request body: {request.get_data(as_text=True)}")
        
        if not data:
            current_app.logger.warning("Username check attempt with no JSON data")
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        username = data.get('username')
        current_app.logger.debug(f"Extracted username: {username}")
        
        if not username:
            current_app.logger.warning("Username check attempt with no username")
            return create_error_response('Missing Username', 'Username is required', 400)
        
        # Validate username format
        try:
            username_error = validate_username(username)
            if username_error:
                current_app.logger.debug(f"Username validation error: {username_error}")
                return create_error_response('Validation Error', username_error, 400)
        except ValidationError as e:
            current_app.logger.debug(f"Username validation error: {str(e)}")
            return create_error_response('Validation Error', str(e), 400)
        
        # Check availability
        try:
            user_exists = User.find_by_username(username) is not None
            current_app.logger.debug(f"Username availability check for '{username}': {'taken' if user_exists else 'available'}")
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error during username check: {str(e)}")
            return create_error_response('Database Error', 'Unable to check username availability', 500)
        
        return create_success_response(
            data={
                'username': username,
                'available': not user_exists
            },
            message='Username checked successfully'
        )
        
    except ValidationError as e:
        current_app.logger.warning(f"Validation error in username check: {str(e)}")
        return create_error_response('Validation Error', str(e), 400)
    except BadRequest as e:
        current_app.logger.warning(f"Bad request in username check: {str(e)}")
        return create_error_response('Bad Request', str(e), 400)
    except Exception as e:
        current_app.logger.error(f"Unexpected error in username check: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return create_error_response('Username Check Failed', 'An unexpected error occurred while checking username availability', 500)

@auth_bp.route('/check-email', methods=['POST'])
def check_email():
    """Check if email is available."""
    try:
        # Log the incoming request
        current_app.logger.debug(f"Email availability check from {request.remote_addr}")
        
        data = request.get_json()
        
        if not data:
            current_app.logger.warning("Email check attempt with no JSON data")
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        email = data.get('email')
        
        if not email:
            current_app.logger.warning("Email check attempt with no email")
            return create_error_response('Missing Email', 'Email is required', 400)
        
        # Validate email format (more lenient for real-time checking)
        try:
            email_error = validate_email_for_check(email)
            if email_error:
                current_app.logger.debug(f"Email validation error: {email_error}")
                return create_error_response('Validation Error', email_error, 400)
        except ValidationError as e:
            current_app.logger.debug(f"Email validation error: {str(e)}")
            return create_error_response('Validation Error', str(e), 400)
        
        # Check availability
        try:
            user_exists = User.find_by_email(email) is not None
            current_app.logger.debug(f"Email availability check for '{email}': {'taken' if user_exists else 'available'}")
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error during email check: {str(e)}")
            return create_error_response('Database Error', 'Unable to check email availability', 500)
        
        return create_success_response(
            data={
                'email': email,
                'available': not user_exists
            },
            message='Email checked successfully'
        )
        
    except ValidationError as e:
        current_app.logger.warning(f"Validation error in email check: {str(e)}")
        return create_error_response('Validation Error', str(e), 400)
    except BadRequest as e:
        current_app.logger.warning(f"Bad request in email check: {str(e)}")
        return create_error_response('Bad Request', str(e), 400)
    except Exception as e:
        current_app.logger.error(f"Unexpected error in email check: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return create_error_response('Email Check Failed', 'An unexpected error occurred while checking email availability', 500) 