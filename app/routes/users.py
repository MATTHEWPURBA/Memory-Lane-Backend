from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.models.user import User
from app.utils.validators import (
    validate_username, validate_email_address, validate_pagination,
    validate_search_query, ValidationError
)
from app.utils.error_handlers import create_error_response, create_success_response

users_bp = Blueprint('users', __name__)

@users_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user's profile."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return create_error_response('User Not Found', 'User not found', 404)
        
        return create_success_response(
            data={'user': user.to_dict(include_private=True)},
            message='Profile retrieved successfully'
        )
        
    except Exception as e:
        return create_error_response('Profile Retrieval Failed', str(e), 500)

@users_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user's profile."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return create_error_response('User Not Found', 'User not found', 404)
        
        data = request.get_json()
        if not data:
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        # Update allowed fields
        if 'display_name' in data:
            display_name = data['display_name']
            if display_name and len(display_name.strip()) > 100:
                return create_error_response(
                    'Validation Error', 
                    'Display name must not exceed 100 characters', 
                    400
                )
            user.display_name = display_name.strip() if display_name else None
        
        if 'bio' in data:
            bio = data['bio']
            if bio and len(bio.strip()) > 500:
                return create_error_response(
                    'Validation Error', 
                    'Bio must not exceed 500 characters', 
                    400
                )
            user.bio = bio.strip() if bio else None
        
        if 'email' in data:
            new_email = validate_email_address(data['email'])
            # Check if email is already taken by another user
            existing_user = User.find_by_email(new_email)
            if existing_user and str(existing_user.user_id) != str(user.user_id):
                return create_error_response(
                    'Email Taken', 
                    'Email address already exists', 
                    409
                )
            user.email = new_email
        
        if 'default_memory_privacy' in data:
            privacy_level = data['default_memory_privacy']
            if privacy_level not in ['public', 'friends', 'private']:
                return create_error_response(
                    'Validation Error', 
                    'Default memory privacy must be public, friends, or private', 
                    400
                )
            user.default_memory_privacy = privacy_level
        
        db.session.commit()
        
        return create_success_response(
            data={'user': user.to_dict(include_private=True)},
            message='Profile updated successfully'
        )
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Profile Update Failed', str(e), 500)

@users_bp.route('/privacy-settings', methods=['PUT'])
@jwt_required()
def update_privacy_settings():
    """Update user's privacy settings."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return create_error_response('User Not Found', 'User not found', 404)
        
        data = request.get_json()
        if not data:
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        # Validate privacy settings
        valid_privacy_keys = [
            'profile_visibility', 'location_sharing', 'memory_discovery',
            'show_activity_status', 'allow_friend_requests'
        ]
        
        settings_to_update = {}
        
        for key, value in data.items():
            if key not in valid_privacy_keys:
                continue
            
            if key == 'profile_visibility':
                if value not in ['public', 'friends', 'private']:
                    return create_error_response(
                        'Validation Error', 
                        'Profile visibility must be public, friends, or private', 
                        400
                    )
            elif isinstance(value, bool):
                pass  # Boolean values are valid for other settings
            else:
                return create_error_response(
                    'Validation Error', 
                    f'{key} must be a boolean value', 
                    400
                )
            
            settings_to_update[key] = value
        
        # Update location sharing in separate field for easy access
        if 'location_sharing' in settings_to_update:
            user.location_sharing_enabled = settings_to_update['location_sharing']
        
        # Update privacy settings
        user.update_privacy_settings(settings_to_update)
        
        return create_success_response(
            data={'privacy_settings': user.privacy_settings},
            message='Privacy settings updated successfully'
        )
        
    except Exception as e:
        return create_error_response('Privacy Settings Update Failed', str(e), 500)

@users_bp.route('/<user_id>', methods=['GET'])
@jwt_required(optional=True)
def get_user_profile(user_id):
    """Get another user's public profile."""
    try:
        # Get viewer information
        viewer_user_id = get_jwt_identity()
        viewer_user = User.query.get(viewer_user_id) if viewer_user_id else None
        
        # Get target user
        user = User.query.get(user_id)
        if not user or not user.is_active:
            return create_error_response('User Not Found', 'User not found', 404)
        
        # Check if viewer can see this profile
        if not user.can_view_profile(viewer_user):
            return create_error_response(
                'Access Denied', 
                'You do not have permission to view this profile', 
                403
            )
        
        return create_success_response(
            data={'user': user.to_dict(viewer_user=viewer_user)},
            message='User profile retrieved successfully'
        )
        
    except Exception as e:
        return create_error_response('Profile Retrieval Failed', str(e), 500)

@users_bp.route('/search', methods=['GET'])
@jwt_required(optional=True)
def search_users():
    """Search for users by username or display name."""
    try:
        query = request.args.get('q')
        if not query:
            return create_error_response('Missing Query', 'Search query is required', 400)
        
        # Validate and get pagination parameters
        page = request.args.get('page', 1)
        per_page = request.args.get('per_page', 20)
        page, per_page = validate_pagination(page, per_page)
        
        # Validate search query
        query = validate_search_query(query)
        
        # Search users
        users = User.search_users(query, limit=per_page)
        
        # Get viewer information for privacy filtering
        viewer_user_id = get_jwt_identity()
        viewer_user = User.query.get(viewer_user_id) if viewer_user_id else None
        
        # Filter results based on privacy settings
        filtered_users = []
        for user in users:
            if user.can_view_profile(viewer_user):
                filtered_users.append(user.to_dict(viewer_user=viewer_user))
        
        return create_success_response(
            data={
                'users': filtered_users,
                'total': len(filtered_users),
                'page': page,
                'per_page': per_page
            },
            message='User search completed successfully'
        )
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('User Search Failed', str(e), 500)

@users_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_user_stats():
    """Get current user's statistics."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return create_error_response('User Not Found', 'User not found', 404)
        
        stats = user.get_stats()
        
        return create_success_response(
            data={'stats': stats},
            message='User statistics retrieved successfully'
        )
        
    except Exception as e:
        return create_error_response('Statistics Retrieval Failed', str(e), 500)

@users_bp.route('/deactivate', methods=['POST'])
@jwt_required()
def deactivate_account():
    """Deactivate user account."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return create_error_response('User Not Found', 'User not found', 404)
        
        data = request.get_json()
        if not data:
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        # Require password confirmation
        password = data.get('password')
        if not password:
            return create_error_response(
                'Password Required', 
                'Password is required to deactivate account', 
                400
            )
        
        if not user.check_password(password):
            return create_error_response(
                'Invalid Password', 
                'Password is incorrect', 
                401
            )
        
        # Deactivate account
        user.deactivate()
        
        return create_success_response(message='Account deactivated successfully')
        
    except Exception as e:
        return create_error_response('Account Deactivation Failed', str(e), 500)

@users_bp.route('/reactivate', methods=['POST'])
def reactivate_account():
    """Reactivate user account."""
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
        
        # Find user by username or email (including inactive users)
        user = None
        if '@' in username_or_email:
            user = User.query.filter_by(email=username_or_email.lower()).first()
        else:
            user = User.query.filter_by(username=username_or_email.lower()).first()
        
        if not user or not user.check_password(password):
            return create_error_response(
                'Invalid Credentials', 
                'Invalid username/email or password', 
                401
            )
        
        if user.is_active:
            return create_error_response(
                'Account Active', 
                'Account is already active', 
                400
            )
        
        # Reactivate account
        user.reactivate()
        
        return create_success_response(message='Account reactivated successfully')
        
    except Exception as e:
        return create_error_response('Account Reactivation Failed', str(e), 500)

@users_bp.route('/activity', methods=['GET'])
@jwt_required()
def get_user_activity():
    """Get user's recent activity summary."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return create_error_response('User Not Found', 'User not found', 404)
        
        # Get recent memories
        recent_memories = user.created_memories.order_by(
            user.created_memories.expression.created_at.desc()
        ).limit(5).all()
        
        # Get recent interactions
        recent_interactions = user.interactions.order_by(
            user.interactions.expression.created_at.desc()
        ).limit(10).all()
        
        activity = {
            'recent_memories': [memory.to_dict(user=user) for memory in recent_memories],
            'recent_interactions': [
                interaction.to_dict(include_user_info=False, user=user) 
                for interaction in recent_interactions
            ],
            'stats': user.get_stats()
        }
        
        return create_success_response(
            data={'activity': activity},
            message='User activity retrieved successfully'
        )
        
    except Exception as e:
        return create_error_response('Activity Retrieval Failed', str(e), 500) 