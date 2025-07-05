from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt, verify_jwt_in_request
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta

from app import db, redis_client
from app.models.user import User
from app.utils.validators import (
    validate_username, validate_email_address, validate_password,
    ValidationError
)
from app.utils.error_handlers import create_error_response, create_success_response

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
        data = request.get_json()
        
        if not data:
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        # Validate required fields
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not all([username, email, password]):
            return create_error_response(
                'Missing Fields', 
                'Username, email, and password are required', 
                400
            )
        
        # Validate input data
        username = validate_username(username)
        email = validate_email_address(email)
        password = validate_password(password)
        
        # Check if user already exists
        if User.find_by_username(username):
            return create_error_response('Username Taken', 'Username already exists', 409)
        
        if User.find_by_email(email):
            return create_error_response('Email Taken', 'Email address already exists', 409)
        
        # Create new user
        user = User(
            username=username,
            email=email,
            password=password,
            display_name=data.get('display_name'),
            bio=data.get('bio')
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Create tokens
        access_token = create_access_token(identity=str(user.user_id))
        refresh_token = create_refresh_token(identity=str(user.user_id))
        
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
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Registration Failed', str(e), 500)

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user and return tokens."""
    try:
        data = request.get_json()
        
        if not data:
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        # Get credentials
        username_or_email = data.get('username') or data.get('email')
        password = data.get('password')
        
        if not all([username_or_email, password]):
            return create_error_response(
                'Missing Credentials', 
                'Username/email and password are required', 
                400
            )
        
        # Find user by username or email
        user = None
        if '@' in username_or_email:
            user = User.find_by_email(username_or_email)
        else:
            user = User.find_by_username(username_or_email)
        
        if not user or not user.check_password(password):
            return create_error_response(
                'Invalid Credentials', 
                'Invalid username/email or password', 
                401
            )
        
        if not user.is_active:
            return create_error_response(
                'Account Deactivated', 
                'Your account has been deactivated', 
                403
            )
        
        # Update last active
        user.update_last_active()
        
        # Create tokens
        access_token = create_access_token(identity=str(user.user_id))
        refresh_token = create_refresh_token(identity=str(user.user_id))
        
        return create_success_response(
            data={
                'user': user.to_dict(include_private=True),
                'access_token': access_token,
                'refresh_token': refresh_token
            },
            message='Login successful'
        )
        
    except Exception as e:
        return create_error_response('Login Failed', str(e), 500)

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
        data = request.get_json()
        
        if not data:
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        username = data.get('username')
        
        if not username:
            return create_error_response('Missing Username', 'Username is required', 400)
        
        # Validate username format
        username = validate_username(username)
        
        # Check availability
        user_exists = User.find_by_username(username) is not None
        
        return create_success_response(
            data={
                'username': username,
                'available': not user_exists
            },
            message='Username checked successfully'
        )
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Username Check Failed', str(e), 500)

@auth_bp.route('/check-email', methods=['POST'])
def check_email():
    """Check if email is available."""
    try:
        data = request.get_json()
        
        if not data:
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        email = data.get('email')
        
        if not email:
            return create_error_response('Missing Email', 'Email is required', 400)
        
        # Validate email format
        email = validate_email_address(email)
        
        # Check availability
        user_exists = User.find_by_email(email) is not None
        
        return create_success_response(
            data={
                'email': email,
                'available': not user_exists
            },
            message='Email checked successfully'
        )
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Email Check Failed', str(e), 500) 