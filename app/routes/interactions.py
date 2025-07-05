from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db, limiter
from app.models.interaction import Interaction, InteractionType
from app.models.memory import Memory
from app.models.user import User
from app.utils.validators import sanitize_input, validate_comment_content, validate_report_reason, validate_pagination, ValidationError
from datetime import datetime
from app.utils.error_handlers import create_error_response, create_success_response

interactions_bp = Blueprint('interactions', __name__)

@interactions_bp.route('/like', methods=['POST'])
@jwt_required()
def like_memory():
    """Like a memory."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return create_error_response('User Not Found', 'User not found', 404)
        
        data = request.get_json()
        if not data:
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        memory_id = data.get('memory_id')
        if not memory_id:
            return create_error_response('Missing Memory ID', 'Memory ID is required', 400)
        
        memory = Memory.query.get(memory_id)
        if not memory:
            return create_error_response('Memory Not Found', 'Memory not found', 404)
        
        # Check if memory can be viewed
        if not memory.can_view(user):
            return create_error_response(
                'Access Denied',
                'You do not have permission to interact with this memory',
                403
            )
        
        # Check if user already liked this memory
        existing_like = Interaction.find_interaction(user_id, memory_id, 'like')
        if existing_like and existing_like.is_active:
            return create_error_response(
                'Already Liked',
                'You have already liked this memory',
                409
            )
        
        # Create like interaction
        like = Interaction.create_like(user_id, memory_id)
        
        # Update memory like count
        memory.increment_likes()
        
        # Update user statistics
        user.increment_likes_given_count()
        
        # Update memory creator statistics
        if str(memory.creator_id) != str(user_id):
            memory.creator.increment_likes_received_count()
        
        return create_success_response(
            data={
                'interaction': like.to_dict(user=user),
                'likes_count': memory.likes_count
            },
            message='Memory liked successfully'
        )
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Like Failed', str(e), 500)

@interactions_bp.route('/unlike', methods=['POST'])
@jwt_required()
def unlike_memory():
    """Unlike a memory."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return create_error_response('User Not Found', 'User not found', 404)
        
        data = request.get_json()
        if not data:
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        memory_id = data.get('memory_id')
        if not memory_id:
            return create_error_response('Missing Memory ID', 'Memory ID is required', 400)
        
        memory = Memory.query.get(memory_id)
        if not memory:
            return create_error_response('Memory Not Found', 'Memory not found', 404)
        
        # Remove like
        success = Interaction.remove_like(user_id, memory_id)
        
        if not success:
            return create_error_response(
                'Not Liked',
                'You have not liked this memory',
                400
            )
        
        # Update memory like count
        memory.decrement_likes()
        
        return create_success_response(
            data={'likes_count': memory.likes_count},
            message='Memory unliked successfully'
        )
        
    except Exception as e:
        return create_error_response('Unlike Failed', str(e), 500)

@interactions_bp.route('/comment', methods=['POST'])
@jwt_required()
def comment_on_memory():
    """Comment on a memory."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return create_error_response('User Not Found', 'User not found', 404)
        
        data = request.get_json()
        if not data:
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        memory_id = data.get('memory_id')
        content = data.get('content')
        
        if not memory_id or not content:
            return create_error_response(
                'Missing Fields',
                'Memory ID and content are required',
                400
            )
        
        memory = Memory.query.get(memory_id)
        if not memory:
            return create_error_response('Memory Not Found', 'Memory not found', 404)
        
        # Check if memory can be viewed
        if not memory.can_view(user):
            return create_error_response(
                'Access Denied',
                'You do not have permission to interact with this memory',
                403
            )
        
        # Validate comment content
        content = validate_comment_content(content)
        
        # Create comment interaction
        comment = Interaction.create_comment(user_id, memory_id, content)
        
        # Update memory comment count
        memory.increment_comments()
        
        return create_success_response(
            data={
                'interaction': comment.to_dict(user=user),
                'comments_count': memory.comments_count
            },
            message='Comment added successfully',
            status_code=201
        )
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Comment Failed', str(e), 500)

@interactions_bp.route('/comment/<interaction_id>', methods=['PUT'])
@jwt_required()
def update_comment(interaction_id):
    """Update a comment."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return create_error_response('User Not Found', 'User not found', 404)
        
        interaction = Interaction.query.get(interaction_id)
        if not interaction or interaction.interaction_type != 'comment':
            return create_error_response('Comment Not Found', 'Comment not found', 404)
        
        # Check if user can edit this comment
        if not interaction.can_edit(user):
            return create_error_response(
                'Access Denied',
                'You do not have permission to edit this comment',
                403
            )
        
        data = request.get_json()
        if not data:
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        content = data.get('content')
        if not content:
            return create_error_response('Missing Content', 'Content is required', 400)
        
        # Validate comment content
        content = validate_comment_content(content)
        
        # Update comment
        interaction.update_content(content)
        
        return create_success_response(
            data={'interaction': interaction.to_dict(user=user)},
            message='Comment updated successfully'
        )
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Comment Update Failed', str(e), 500)

@interactions_bp.route('/comment/<interaction_id>', methods=['DELETE'])
@jwt_required()
def delete_comment(interaction_id):
    """Delete a comment."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return create_error_response('User Not Found', 'User not found', 404)
        
        interaction = Interaction.query.get(interaction_id)
        if not interaction or interaction.interaction_type != 'comment':
            return create_error_response('Comment Not Found', 'Comment not found', 404)
        
        # Check if user can delete this comment (owner or memory creator)
        memory = Memory.query.get(interaction.memory_id)
        can_delete = (
            interaction.can_edit(user) or  # Comment owner
            (memory and memory.can_edit(user))  # Memory owner
        )
        
        if not can_delete:
            return create_error_response(
                'Access Denied',
                'You do not have permission to delete this comment',
                403
            )
        
        # Soft delete comment
        interaction.deactivate()
        
        # Update memory comment count
        if memory:
            memory.comments_count = max(0, memory.comments_count - 1)
            db.session.commit()
        
        return create_success_response(message='Comment deleted successfully')
        
    except Exception as e:
        return create_error_response('Comment Deletion Failed', str(e), 500)

@interactions_bp.route('/share', methods=['POST'])
@jwt_required()
def share_memory():
    """Share a memory."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return create_error_response('User Not Found', 'User not found', 404)
        
        data = request.get_json()
        if not data:
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        memory_id = data.get('memory_id')
        if not memory_id:
            return create_error_response('Missing Memory ID', 'Memory ID is required', 400)
        
        memory = Memory.query.get(memory_id)
        if not memory:
            return create_error_response('Memory Not Found', 'Memory not found', 404)
        
        # Check if memory can be viewed
        if not memory.can_view(user):
            return create_error_response(
                'Access Denied',
                'You do not have permission to share this memory',
                403
            )
        
        # Get share metadata
        platform = data.get('platform', 'app')  # app, facebook, twitter, etc.
        message = data.get('message', '')
        
        metadata = {
            'platform': platform,
            'message': message
        }
        
        # Create share interaction
        share = Interaction.create_share(user_id, memory_id, metadata)
        
        return create_success_response(
            data={'interaction': share.to_dict(user=user)},
            message='Memory shared successfully'
        )
        
    except Exception as e:
        return create_error_response('Share Failed', str(e), 500)

@interactions_bp.route('/report', methods=['POST'])
@jwt_required()
def report_memory():
    """Report a memory."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return create_error_response('User Not Found', 'User not found', 404)
        
        data = request.get_json()
        if not data:
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        memory_id = data.get('memory_id')
        reason = data.get('reason')
        
        if not memory_id or not reason:
            return create_error_response(
                'Missing Fields',
                'Memory ID and reason are required',
                400
            )
        
        memory = Memory.query.get(memory_id)
        if not memory:
            return create_error_response('Memory Not Found', 'Memory not found', 404)
        
        # Validate report reason
        reason = validate_report_reason(reason)
        
        # Get optional description
        description = data.get('description', '')
        
        # Create report interaction
        report = Interaction.create_report(user_id, memory_id, reason, description)
        
        # Mark memory as reported if multiple reports
        report_count = Interaction.query.filter_by(
            memory_id=memory_id,
            interaction_type='report',
            is_active=True
        ).count()
        
        if report_count >= 3:  # Threshold for automatic flagging
            memory.report()
        
        return create_success_response(
            message='Memory reported successfully. Thank you for helping keep our community safe.'
        )
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Report Failed', str(e), 500)

@interactions_bp.route('/memory/<memory_id>/comments', methods=['GET'])
@jwt_required(optional=True)
def get_memory_comments(memory_id):
    """Get comments for a memory."""
    try:
        viewer_user_id = get_jwt_identity()
        viewer_user = User.query.get(viewer_user_id) if viewer_user_id else None
        
        memory = Memory.query.get(memory_id)
        if not memory:
            return create_error_response('Memory Not Found', 'Memory not found', 404)
        
        # Check if memory can be viewed
        if not memory.can_view(viewer_user):
            return create_error_response(
                'Access Denied',
                'You do not have permission to view this memory',
                403
            )
        
        # Get pagination parameters
        page = request.args.get('page', 1)
        per_page = request.args.get('per_page', 50)
        page, per_page = validate_pagination(page, per_page)
        
        # Get comments
        comments = Interaction.get_comments_for_memory(memory_id, limit=per_page)
        
        # Convert to dict format
        comments_data = []
        for comment in comments:
            comment_dict = comment.to_dict(user=viewer_user)
            if comment_dict:
                comments_data.append(comment_dict)
        
        return create_success_response(
            data={
                'comments': comments_data,
                'memory_id': memory_id,
                'total': len(comments_data)
            },
            message='Comments retrieved successfully'
        )
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Comments Retrieval Failed', str(e), 500)

@interactions_bp.route('/memory/<memory_id>/likes', methods=['GET'])
@jwt_required(optional=True)
def get_memory_likes(memory_id):
    """Get likes for a memory."""
    try:
        viewer_user_id = get_jwt_identity()
        viewer_user = User.query.get(viewer_user_id) if viewer_user_id else None
        
        memory = Memory.query.get(memory_id)
        if not memory:
            return create_error_response('Memory Not Found', 'Memory not found', 404)
        
        # Check if memory can be viewed
        if not memory.can_view(viewer_user):
            return create_error_response(
                'Access Denied',
                'You do not have permission to view this memory',
                403
            )
        
        # Get likes
        likes = Interaction.get_likes_for_memory(memory_id)
        
        # Convert to dict format (user info only)
        likes_data = []
        for like in likes:
            if like.user:
                likes_data.append({
                    'user_id': str(like.user_id),
                    'username': like.user.username,
                    'display_name': like.user.display_name or like.user.username,
                    'profile_photo_url': like.user.profile_photo_url,
                    'liked_at': like.created_at.isoformat()
                })
        
        return create_success_response(
            data={
                'likes': likes_data,
                'memory_id': memory_id,
                'total': len(likes_data)
            },
            message='Likes retrieved successfully'
        )
        
    except Exception as e:
        return create_error_response('Likes Retrieval Failed', str(e), 500)

@interactions_bp.route('/user/<user_id>/interactions', methods=['GET'])
@jwt_required()
def get_user_interactions(user_id):
    """Get interactions by a user."""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user:
            return create_error_response('User Not Found', 'User not found', 404)
        
        # Only allow users to view their own interactions
        if str(current_user_id) != str(user_id):
            return create_error_response(
                'Access Denied',
                'You can only view your own interactions',
                403
            )
        
        # Get query parameters
        interaction_type = request.args.get('type')  # like, comment, share
        page = request.args.get('page', 1)
        per_page = request.args.get('per_page', 20)
        page, per_page = validate_pagination(page, per_page)
        
        # Get interactions
        interactions = Interaction.get_user_interactions(
            user_id, interaction_type=interaction_type, limit=per_page
        )
        
        # Convert to dict format
        interactions_data = []
        for interaction in interactions:
            interaction_dict = interaction.to_dict(user=current_user)
            if interaction_dict:
                interactions_data.append(interaction_dict)
        
        return create_success_response(
            data={
                'interactions': interactions_data,
                'user_id': user_id,
                'interaction_type': interaction_type,
                'total': len(interactions_data),
                'page': page,
                'per_page': per_page
            },
            message='User interactions retrieved successfully'
        )
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Interactions Retrieval Failed', str(e), 500)

@interactions_bp.route('/memory/<memory_id>/check-like', methods=['GET'])
@jwt_required()
def check_user_like(memory_id):
    """Check if current user has liked a memory."""
    try:
        user_id = get_jwt_identity()
        
        has_liked = Interaction.user_has_liked(user_id, memory_id)
        
        return create_success_response(
            data={
                'memory_id': memory_id,
                'has_liked': has_liked
            },
            message='Like status checked successfully'
        )
        
    except Exception as e:
        return create_error_response('Like Check Failed', str(e), 500) 