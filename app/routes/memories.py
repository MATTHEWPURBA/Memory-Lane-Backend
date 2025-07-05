from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db, limiter
from app.models.memory import Memory, ContentType, PrivacyLevel
from app.models.user import User
from app.models.interaction import Interaction, InteractionType
from app.utils.validators import (
    validate_coordinates, validate_content_type, validate_privacy_level,
    validate_memory_title, validate_memory_description, sanitize_input,
    validate_tags, validate_pagination, validate_search_query, ValidationError
)
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from app.utils.error_handlers import create_error_response, create_success_response

memories_bp = Blueprint('memories', __name__)

@memories_bp.route('/', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def create_memory():
    """Create a new memory."""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['latitude', 'longitude', 'content_type', 'title']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate coordinates
        coord_error = validate_coordinates(data['latitude'], data['longitude'])
        if coord_error:
            return jsonify({'error': coord_error}), 400
        
        # Validate content type
        content_type_error = validate_content_type(data['content_type'])
        if content_type_error:
            return jsonify({'error': content_type_error}), 400
        
        # Validate title
        title_error = validate_memory_title(data['title'])
        if title_error:
            return jsonify({'error': title_error}), 400
        
        # Validate description if provided
        if 'description' in data:
            desc_error = validate_memory_description(data['description'])
            if desc_error:
                return jsonify({'error': desc_error}), 400
        
        # Validate privacy level if provided
        privacy_level = data.get('privacy_level', 'public')
        privacy_error = validate_privacy_level(privacy_level)
        if privacy_error:
            return jsonify({'error': privacy_error}), 400
        
        # Sanitize input
        title = sanitize_input(data['title'])
        description = sanitize_input(data.get('description', ''))
        
        # Create memory
        memory = Memory(
            creator_id=current_user_id,
            latitude=float(data['latitude']),
            longitude=float(data['longitude']),
            content_type=data['content_type'],
            title=title,
            description=description,
            privacy_level=privacy_level,
            altitude=data.get('altitude'),
            location_accuracy=data.get('location_accuracy'),
            content_url=data.get('content_url'),
            content_size=data.get('content_size'),
            content_duration=data.get('content_duration'),
            category_tags=data.get('category_tags', []),
            weather_data=data.get('weather_data'),
            device_info=data.get('device_info')
        )
        
        # Set expiration date if provided
        if 'expiration_hours' in data:
            try:
                hours = int(data['expiration_hours'])
                if 1 <= hours <= 8760:  # Max 1 year
                    memory.expiration_date = datetime.utcnow() + timedelta(hours=hours)
            except ValueError:
                pass
        
        db.session.add(memory)
        
        # Update user's memory count
        user = User.query.get(current_user_id)
        if user:
            user.memories_count += 1
        
        db.session.commit()
        
        return jsonify({
            'message': 'Memory created successfully',
            'memory': memory.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Memory creation error: {str(e)}")
        return jsonify({'error': 'Failed to create memory'}), 500


@memories_bp.route('/<memory_id>', methods=['GET'])
@jwt_required(optional=True)
def get_memory(memory_id):
    """Get a specific memory by ID."""
    try:
        current_user_id = get_jwt_identity()
        viewer_user = User.query.get(current_user_id) if current_user_id else None
        
        memory = Memory.query.get(memory_id)
        if not memory or not memory.is_active:
            return jsonify({'error': 'Memory not found'}), 404
        
        # Check if memory is expired
        if memory.is_expired():
            return jsonify({'error': 'Memory has expired'}), 410
        
        # Check privacy permissions
        if not memory.can_view(viewer_user):
            return jsonify({'error': 'Access denied'}), 403
        
        # Increment view count (if not the creator)
        if memory.creator_id != current_user_id:
            memory.increment_view_count()
            
            # Create view interaction
            if not Interaction.has_user_interacted(current_user_id, memory_id, InteractionType.VIEW):
                view_interaction = Interaction(
                    user_id=current_user_id,
                    memory_id=memory_id,
                    interaction_type=InteractionType.VIEW
                )
                db.session.add(view_interaction)
                db.session.commit()
        
        # Get interaction counts
        interaction_counts = Interaction.get_interaction_counts(memory_id)
        
        memory_data = memory.to_dict(user=viewer_user)
        memory_data.update(interaction_counts)
        
        # Check if current user has liked this memory
        has_liked = Interaction.has_user_interacted(current_user_id, memory_id, InteractionType.LIKE)
        memory_data['has_liked'] = has_liked
        
        return jsonify(memory_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Memory retrieval error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve memory'}), 500


@memories_bp.route('/<memory_id>', methods=['PUT'])
@jwt_required()
def update_memory(memory_id):
    """Update a memory (only by creator)."""
    try:
        current_user_id = get_jwt_identity()
        
        memory = Memory.query.get(memory_id)
        if not memory or not memory.is_active:
            return jsonify({'error': 'Memory not found'}), 404
        
        # Check if user is the creator
        if memory.creator_id != current_user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        # Update allowed fields
        if 'title' in data:
            title_error = validate_memory_title(data['title'])
            if title_error:
                return jsonify({'error': title_error}), 400
            memory.title = sanitize_input(data['title'])
        
        if 'description' in data:
            desc_error = validate_memory_description(data['description'])
            if desc_error:
                return jsonify({'error': desc_error}), 400
            memory.description = sanitize_input(data['description'])
        
        if 'privacy_level' in data:
            privacy_error = validate_privacy_level(data['privacy_level'])
            if privacy_error:
                return jsonify({'error': privacy_error}), 400
            memory.privacy_level = PrivacyLevel(data['privacy_level'])
        
        if 'category_tags' in data:
            memory.category_tags = data['category_tags']
        
        if 'expiration_hours' in data:
            try:
                hours = int(data['expiration_hours'])
                if hours == 0:
                    memory.expiration_date = None
                elif 1 <= hours <= 8760:
                    memory.expiration_date = datetime.utcnow() + timedelta(hours=hours)
            except ValueError:
                pass
        
        memory.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Memory updated successfully',
            'memory': memory.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Memory update error: {str(e)}")
        return jsonify({'error': 'Failed to update memory'}), 500


@memories_bp.route('/<memory_id>', methods=['DELETE'])
@jwt_required()
def delete_memory(memory_id):
    """Delete a memory (only by creator)."""
    try:
        current_user_id = get_jwt_identity()
        
        memory = Memory.query.get(memory_id)
        if not memory or not memory.is_active:
            return jsonify({'error': 'Memory not found'}), 404
        
        # Check if user is the creator
        if memory.creator_id != current_user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Soft delete
        memory.is_active = False
        
        # Update user's memory count
        user = User.query.get(current_user_id)
        if user and user.memories_count > 0:
            user.memories_count -= 1
        
        db.session.commit()
        
        return jsonify({
            'message': 'Memory deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Memory deletion error: {str(e)}")
        return jsonify({'error': 'Failed to delete memory'}), 500


@memories_bp.route('/user/<user_id>', methods=['GET'])
@jwt_required(optional=True)
def get_user_memories(user_id):
    """Get memories created by a specific user."""
    try:
        current_user_id = get_jwt_identity()
        viewer_user = User.query.get(current_user_id) if current_user_id else None
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)
        
        # Base query
        query = Memory.query.filter(
            Memory.creator_id == user_id,
            Memory.is_active == True
        )
        
        # Privacy filtering
        if user_id != current_user_id:
            query = query.filter(Memory.privacy_level == PrivacyLevel.PUBLIC)
        
        # Filter out expired memories
        query = query.filter(
            or_(Memory.expiration_date.is_(None),
                Memory.expiration_date > datetime.utcnow())
        )
        
        # Order by creation date
        query = query.order_by(Memory.created_at.desc())
        
        # Paginate
        memories_page = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        memories_data = []
        for memory in memories_page.items:
            memory_dict = memory.to_dict(user=viewer_user)
            # Add interaction counts
            interaction_counts = Interaction.get_interaction_counts(memory.memory_id)
            memory_dict.update(interaction_counts)
            memories_data.append(memory_dict)
        
        return jsonify({
            'memories': memories_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': memories_page.total,
                'pages': memories_page.pages,
                'has_next': memories_page.has_next,
                'has_prev': memories_page.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"User memories retrieval error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve memories'}), 500


@memories_bp.route('/feed', methods=['GET'])
@jwt_required(optional=True)
def get_memory_feed():
    """Get a personalized feed of recent memories."""
    try:
        current_user_id = get_jwt_identity()
        viewer_user = User.query.get(current_user_id) if current_user_id else None
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)
        
        # Base query for public memories
        query = Memory.query.filter(
            Memory.is_active == True,
            Memory.privacy_level == PrivacyLevel.PUBLIC
        )
        
        # Filter out expired memories
        query = query.filter(
            or_(Memory.expiration_date.is_(None),
                Memory.expiration_date > datetime.utcnow())
        )
        
        # Filter by content type if specified
        content_type = request.args.get('content_type')
        if content_type:
            try:
                content_type_enum = ContentType(content_type)
                query = query.filter(Memory.content_type == content_type_enum)
            except ValueError:
                pass
        
        # Filter by time range
        time_filter = request.args.get('time_filter', 'all')
        if time_filter == 'today':
            today = datetime.utcnow().date()
            query = query.filter(Memory.created_at >= today)
        elif time_filter == 'week':
            week_ago = datetime.utcnow() - timedelta(days=7)
            query = query.filter(Memory.created_at >= week_ago)
        elif time_filter == 'month':
            month_ago = datetime.utcnow() - timedelta(days=30)
            query = query.filter(Memory.created_at >= month_ago)
        
        # Order by creation date or popularity
        sort_by = request.args.get('sort_by', 'recent')
        if sort_by == 'popular':
            query = query.order_by(Memory.likes_count.desc(), Memory.created_at.desc())
        elif sort_by == 'featured':
            query = query.filter(Memory.is_featured == True).order_by(Memory.created_at.desc())
        else:  # recent
            query = query.order_by(Memory.created_at.desc())
        
        # Paginate
        memories_page = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        memories_data = []
        for memory in memories_page.items:
            memory_dict = memory.to_dict(user=viewer_user)
            # Add interaction counts
            interaction_counts = Interaction.get_interaction_counts(memory.memory_id)
            memory_dict.update(interaction_counts)
            
            # Check if current user has liked this memory
            has_liked = Interaction.has_user_interacted(current_user_id, memory.memory_id, InteractionType.LIKE)
            memory_dict['has_liked'] = has_liked
            
            memories_data.append(memory_dict)
        
        return jsonify({
            'memories': memories_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': memories_page.total,
                'pages': memories_page.pages,
                'has_next': memories_page.has_next,
                'has_prev': memories_page.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Memory feed error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve memory feed'}), 500


@memories_bp.route('/search', methods=['GET'])
@jwt_required(optional=True)
def search_memories():
    """Search memories by text query."""
    try:
        current_user_id = get_jwt_identity()
        viewer_user = User.query.get(current_user_id) if current_user_id else None
        
        query_text = request.args.get('q', '').strip()
        if not query_text:
            return jsonify({'error': 'Search query is required'}), 400
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)
        
        # Search in title, description, and tags
        search_query = Memory.query.filter(
            Memory.is_active == True,
            Memory.privacy_level == PrivacyLevel.PUBLIC,
            or_(
                Memory.title.ilike(f'%{query_text}%'),
                Memory.description.ilike(f'%{query_text}%'),
                func.json_extract_path_text(Memory.category_tags, '%').ilike(f'%{query_text}%')
            )
        )
        
        # Filter out expired memories
        search_query = search_query.filter(
            or_(Memory.expiration_date.is_(None),
                Memory.expiration_date > datetime.utcnow())
        )
        
        # Order by relevance (for now, just by creation date)
        search_query = search_query.order_by(Memory.created_at.desc())
        
        # Paginate
        memories_page = search_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        memories_data = []
        for memory in memories_page.items:
            memory_dict = memory.to_dict(user=viewer_user)
            interaction_counts = Interaction.get_interaction_counts(memory.memory_id)
            memory_dict.update(interaction_counts)
            memories_data.append(memory_dict)
        
        return jsonify({
            'memories': memories_data,
            'query': query_text,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': memories_page.total,
                'pages': memories_page.pages,
                'has_next': memories_page.has_next,
                'has_prev': memories_page.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Memory search error: {str(e)}")
        return jsonify({'error': 'Failed to search memories'}), 500

@memories_bp.route('/nearby', methods=['GET'])
@jwt_required(optional=True)
def get_nearby_memories():
    """Get memories near a specific location."""
    try:
        current_user_id = get_jwt_identity()
        viewer_user = User.query.get(current_user_id) if current_user_id else None
        
        # Get location parameters
        latitude = request.args.get('latitude')
        longitude = request.args.get('longitude')
        radius = request.args.get('radius', 500)
        
        if not latitude or not longitude:
            return jsonify({'error': 'Missing Location', 'message': 'Latitude and longitude are required'}), 400
        
        # Validate parameters
        latitude, longitude = validate_coordinates(latitude, longitude)
        radius = float(radius)
        
        if radius > 5000:  # 5km max
            radius = 5000
        
        # Get pagination parameters
        limit = request.args.get('limit', 50)
        limit = min(int(limit), 100)
        
        # Find nearby memories
        nearby_memories = Memory.find_nearby(
            latitude, longitude, radius, limit=limit, user=viewer_user
        )
        
        return jsonify({
            'memories': nearby_memories,
            'location': {'latitude': latitude, 'longitude': longitude},
            'radius': radius,
            'total': len(nearby_memories)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Nearby memories retrieval error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve nearby memories'}), 500

@memories_bp.route('/discover', methods=['POST'])
@jwt_required()
def discover_memories():
    """Discover memories at current location (for AR/discovery mode)."""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User Not Found', 'message': 'User not found'}), 404
        
        if not user.can_discover_memories():
            return jsonify({'error': 'Discovery Disabled', 'message': 'Memory discovery is disabled in your privacy settings'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid Request', 'message': 'Request body is required'}), 400
        
        # Get location
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        radius = data.get('radius', 100)  # Default 100m for discovery
        
        if not latitude or not longitude:
            return jsonify({'error': 'Missing Location', 'message': 'Latitude and longitude are required'}), 400
        
        # Validate parameters
        latitude, longitude = validate_coordinates(latitude, longitude)
        radius = min(float(radius), 500)  # Max 500m for discovery
        
        # Find memories to discover
        discovered_memories = Memory.find_nearby(
            latitude, longitude, radius, limit=20, user=user
        )
        
        # Filter out memories already discovered by this user
        # TODO: Implement discovery tracking
        
        # Update user discovery count
        if discovered_memories:
            user.increment_discoveries_count()
        
        return jsonify({
            'memories': discovered_memories,
            'location': {'latitude': latitude, 'longitude': longitude},
            'radius': radius,
            'discovered_count': len(discovered_memories)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Memory discovery error: {str(e)}")
        return jsonify({'error': 'Failed to discover memories'}), 500

@memories_bp.route('/<memory_id>/add-tags', methods=['POST'])
@jwt_required()
def add_memory_tags(memory_id):
    """Add tags to a memory."""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User Not Found', 'message': 'User not found'}), 404
        
        memory = Memory.query.get(memory_id)
        if not memory:
            return jsonify({'error': 'Memory Not Found', 'message': 'Memory not found'}), 404
        
        # Check if user can edit this memory
        if not memory.can_edit(user):
            return jsonify({'error': 'Access Denied', 'message': 'You do not have permission to edit this memory'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid Request', 'message': 'Request body is required'}), 400
        
        # Validate tags
        tags = validate_tags(data.get('tags', []))
        tag_type = data.get('type', 'category')  # category or ai
        
        if tag_type == 'category':
            memory.add_tags(tags)
        elif tag_type == 'ai':
            memory.add_ai_tags(tags)
        else:
            return jsonify({'error': 'Invalid Tag Type', 'message': 'Tag type must be category or ai'}), 400
        
        return jsonify({
            'message': 'Tags added successfully',
            'memory': memory.to_dict(user=user)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Tag addition error: {str(e)}")
        return jsonify({'error': 'Failed to add tags'}), 500 