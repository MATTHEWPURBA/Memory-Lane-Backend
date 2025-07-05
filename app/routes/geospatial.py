from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db, limiter
from app.models.memory import Memory, PrivacyLevel
from app.models.user import User
from app.models.interaction import Interaction, InteractionType
from app.utils.validators import validate_coordinates, validate_search_radius
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from app.utils.error_handlers import create_error_response, create_success_response

geospatial_bp = Blueprint('geospatial', __name__)

@geospatial_bp.route('/discover', methods=['GET'])
@jwt_required()
@limiter.limit("100 per hour")
def discover_memories():
    """Discover memories near a specific location."""
    try:
        current_user_id = get_jwt_identity()
        
        # Get location parameters
        latitude = request.args.get('latitude', type=float)
        longitude = request.args.get('longitude', type=float)
        radius = request.args.get('radius', default=500, type=int)
        
        # Validate coordinates
        coord_error = validate_coordinates(latitude, longitude)
        if coord_error:
            return jsonify({'error': coord_error}), 400
        
        # Validate radius
        radius_error = validate_search_radius(radius)
        if radius_error:
            return jsonify({'error': radius_error}), 400
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        
        # Create a point from the provided coordinates
        user_location = func.ST_GeogFromText(f'POINT({longitude} {latitude})')
        
        # Base query for nearby memories
        query = Memory.query.filter(
            func.ST_DWithin(Memory.location, user_location, radius),
            Memory.is_active == True,
            Memory.privacy_level == PrivacyLevel.PUBLIC
        )
        
        # Filter out expired memories
        query = query.filter(
            or_(Memory.expiration_date.is_(None),
                Memory.expiration_date > datetime.utcnow())
        )
        
        # Optional filters
        content_type = request.args.get('content_type')
        if content_type:
            from app.models.memory import ContentType
            try:
                content_type_enum = ContentType(content_type)
                query = query.filter(Memory.content_type == content_type_enum)
            except ValueError:
                pass
        
        # Time filter
        time_filter = request.args.get('time_filter')
        if time_filter == 'today':
            today = datetime.utcnow().date()
            query = query.filter(Memory.created_at >= today)
        elif time_filter == 'week':
            week_ago = datetime.utcnow() - timedelta(days=7)
            query = query.filter(Memory.created_at >= week_ago)
        elif time_filter == 'month':
            month_ago = datetime.utcnow() - timedelta(days=30)
            query = query.filter(Memory.created_at >= month_ago)
        
        # Exclude user's own memories if requested
        if request.args.get('exclude_own', type=bool, default=False):
            query = query.filter(Memory.creator_id != current_user_id)
        
        # Order by distance
        query = query.order_by(func.ST_Distance(Memory.location, user_location))
        
        # Paginate
        memories_page = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        memories_data = []
        for memory in memories_page.items:
            memory_dict = memory.to_dict()
            
            # Calculate distance
            distance = db.session.query(
                func.ST_Distance(memory.location, user_location)
            ).scalar()
            memory_dict['distance_meters'] = round(distance, 2)
            
            # Add interaction counts
            interaction_counts = Interaction.get_interaction_counts(memory.memory_id)
            memory_dict.update(interaction_counts)
            
            # Check if current user has liked this memory
            has_liked = Interaction.has_user_interacted(
                current_user_id, memory.memory_id, InteractionType.LIKE
            )
            memory_dict['has_liked'] = has_liked
            
            memories_data.append(memory_dict)
        
        # Update user's discovery count if memories found
        if memories_data and current_user_id:
            user = User.query.get(current_user_id)
            if user:
                user.discoveries_count += len(memories_data)
                db.session.commit()
        
        return jsonify({
            'memories': memories_data,
            'search_location': {
                'latitude': latitude,
                'longitude': longitude,
                'radius_meters': radius
            },
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
        current_app.logger.error(f"Memory discovery error: {str(e)}")
        return jsonify({'error': 'Failed to discover memories'}), 500


@geospatial_bp.route('/heatmap', methods=['GET'])
@jwt_required()
def get_memory_heatmap():
    """Get memory density data for heatmap visualization."""
    try:
        # Get bounding box parameters
        north = request.args.get('north', type=float)
        south = request.args.get('south', type=float)
        east = request.args.get('east', type=float)
        west = request.args.get('west', type=float)
        
        # Validate bounding box
        if not all([north, south, east, west]):
            return jsonify({'error': 'Bounding box coordinates are required'}), 400
        
        if north <= south or east <= west:
            return jsonify({'error': 'Invalid bounding box'}), 400
        
        # Create bounding box polygon
        bbox = func.ST_MakeEnvelope(west, south, east, north, 4326)
        
        # Grid resolution (degrees)
        grid_size = request.args.get('grid_size', default=0.01, type=float)
        
        # Query memory count within bounding box grouped by grid cells
        grid_query = db.session.query(
            func.floor(Memory.longitude / grid_size) * grid_size,
            func.floor(Memory.latitude / grid_size) * grid_size,
            func.count(Memory.memory_id)
        ).filter(
            func.ST_Within(Memory.location, bbox),
            Memory.is_active == True,
            Memory.privacy_level == PrivacyLevel.PUBLIC,
            or_(Memory.expiration_date.is_(None),
                Memory.expiration_date > datetime.utcnow())
        ).group_by(
            func.floor(Memory.longitude / grid_size),
            func.floor(Memory.latitude / grid_size)
        ).all()
        
        heatmap_data = []
        for lon, lat, count in grid_query:
            heatmap_data.append({
                'latitude': float(lat),
                'longitude': float(lon),
                'intensity': int(count)
            })
        
        return jsonify({
            'heatmap_data': heatmap_data,
            'bounding_box': {
                'north': north,
                'south': south,
                'east': east,
                'west': west
            },
            'grid_size': grid_size
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Heatmap generation error: {str(e)}")
        return jsonify({'error': 'Failed to generate heatmap'}), 500


@geospatial_bp.route('/nearby-users', methods=['GET'])
@jwt_required()
def get_nearby_users():
    """Get users who have created memories near a location."""
    try:
        current_user_id = get_jwt_identity()
        
        # Get location parameters
        latitude = request.args.get('latitude', type=float)
        longitude = request.args.get('longitude', type=float)
        radius = request.args.get('radius', default=1000, type=int)
        
        # Validate coordinates
        coord_error = validate_coordinates(latitude, longitude)
        if coord_error:
            return jsonify({'error': coord_error}), 400
        
        # Validate radius (allow larger radius for user discovery)
        if radius < 50 or radius > 5000:
            return jsonify({'error': 'Radius must be between 50 and 5000 meters'}), 400
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)
        
        # Create a point from the provided coordinates
        user_location = func.ST_GeogFromText(f'POINT({longitude} {latitude})')
        
        # Query for users with memories in the area
        users_query = db.session.query(
            User,
            func.count(Memory.memory_id).label('memories_in_area'),
            func.min(func.ST_Distance(Memory.location, user_location)).label('closest_memory_distance')
        ).join(
            Memory, User.user_id == Memory.creator_id
        ).filter(
            func.ST_DWithin(Memory.location, user_location, radius),
            Memory.is_active == True,
            Memory.privacy_level == PrivacyLevel.PUBLIC,
            User.is_active == True,
            User.user_id != current_user_id,  # Exclude current user
            or_(Memory.expiration_date.is_(None),
                Memory.expiration_date > datetime.utcnow())
        ).group_by(User.user_id).order_by(
            func.min(func.ST_Distance(Memory.location, user_location))
        )
        
        users_page = users_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        users_data = []
        for user, memories_count, closest_distance in users_page.items:
            user_dict = {
                'user_id': user.user_id,
                'username': user.username,
                'profile_photo_url': user.profile_photo_url,
                'memories_in_area': memories_count,
                'closest_memory_distance': round(closest_distance, 2)
            }
            
            # Include additional info based on privacy settings
            if user.privacy_settings and user.privacy_settings.get('profile_visibility') == 'public':
                user_dict.update({
                    'full_name': user.full_name,
                    'bio': user.bio,
                    'memories_count': user.memories_count
                })
            
            users_data.append(user_dict)
        
        return jsonify({
            'users': users_data,
            'search_location': {
                'latitude': latitude,
                'longitude': longitude,
                'radius_meters': radius
            },
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': users_page.total,
                'pages': users_page.pages,
                'has_next': users_page.has_next,
                'has_prev': users_page.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Nearby users error: {str(e)}")
        return jsonify({'error': 'Failed to find nearby users'}), 500


@geospatial_bp.route('/areas/popular', methods=['GET'])
@jwt_required()
def get_popular_areas():
    """Get popular areas with high memory density."""
    try:
        # Clustering parameters
        radius_km = request.args.get('cluster_radius', default=1.0, type=float)
        min_memories = request.args.get('min_memories', default=5, type=int)
        
        # Grid size for clustering (in degrees, roughly 1km = 0.01 degrees)
        grid_size = radius_km * 0.01
        
        # Query to find areas with high memory density
        clusters_query = db.session.query(
            func.floor(Memory.longitude / grid_size) * grid_size,
            func.floor(Memory.latitude / grid_size) * grid_size,
            func.count(Memory.memory_id).label('memory_count'),
            func.avg(Memory.latitude).label('center_lat'),
            func.avg(Memory.longitude).label('center_lon')
        ).filter(
            Memory.is_active == True,
            Memory.privacy_level == PrivacyLevel.PUBLIC,
            or_(Memory.expiration_date.is_(None),
                Memory.expiration_date > datetime.utcnow())
        ).group_by(
            func.floor(Memory.longitude / grid_size),
            func.floor(Memory.latitude / grid_size)
        ).having(
            func.count(Memory.memory_id) >= min_memories
        ).order_by(
            func.count(Memory.memory_id).desc()
        ).limit(20).all()
        
        popular_areas = []
        for grid_lon, grid_lat, count, center_lat, center_lon in clusters_query:
            popular_areas.append({
                'center': {
                    'latitude': float(center_lat),
                    'longitude': float(center_lon)
                },
                'memory_count': int(count),
                'radius_km': radius_km
            })
        
        return jsonify({
            'popular_areas': popular_areas,
            'clustering_params': {
                'cluster_radius_km': radius_km,
                'min_memories': min_memories
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Popular areas error: {str(e)}")
        return jsonify({'error': 'Failed to find popular areas'}), 500


@geospatial_bp.route('/distance', methods=['GET'])
@jwt_required()
def calculate_distance():
    """Calculate distance between two coordinates."""
    try:
        # Source coordinates
        lat1 = request.args.get('lat1', type=float)
        lon1 = request.args.get('lon1', type=float)
        
        # Destination coordinates
        lat2 = request.args.get('lat2', type=float)
        lon2 = request.args.get('lon2', type=float)
        
        # Validate coordinates
        for lat, lon in [(lat1, lon1), (lat2, lon2)]:
            coord_error = validate_coordinates(lat, lon)
            if coord_error:
                return jsonify({'error': coord_error}), 400
        
        # Calculate distance using PostGIS
        point1 = func.ST_GeogFromText(f'POINT({lon1} {lat1})')
        point2 = func.ST_GeogFromText(f'POINT({lon2} {lat2})')
        
        distance = db.session.query(
            func.ST_Distance(point1, point2)
        ).scalar()
        
        return jsonify({
            'distance_meters': round(distance, 2),
            'distance_km': round(distance / 1000, 3),
            'source': {'latitude': lat1, 'longitude': lon1},
            'destination': {'latitude': lat2, 'longitude': lon2}
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Distance calculation error: {str(e)}")
        return jsonify({'error': 'Failed to calculate distance'}), 500

@geospatial_bp.route('/nearby-memories', methods=['GET'])
@jwt_required(optional=True)
def get_nearby_memories():
    """Get memories near a specific location."""
    try:
        viewer_user_id = get_jwt_identity()
        viewer_user = User.query.get(viewer_user_id) if viewer_user_id else None
        
        # Get location parameters
        latitude = request.args.get('latitude')
        longitude = request.args.get('longitude')
        radius = request.args.get('radius', 500)
        
        if not latitude or not longitude:
            return create_error_response(
                'Missing Location',
                'Latitude and longitude are required',
                400
            )
        
        # Validate parameters
        latitude, longitude = validate_coordinates(latitude, longitude)
        radius = validate_search_radius(radius)
        
        # Get pagination parameters
        limit = request.args.get('limit', 50)
        limit = min(int(limit), 100)
        
        # Find nearby memories
        nearby_memories = Memory.find_nearby(
            latitude, longitude, radius, limit=limit, user=viewer_user
        )
        
        return create_success_response(
            data={
                'memories': nearby_memories,
                'location': {'latitude': latitude, 'longitude': longitude},
                'radius': radius,
                'total': len(nearby_memories)
            },
            message='Nearby memories retrieved successfully'
        )
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Nearby Memories Retrieval Failed', str(e), 500)

@geospatial_bp.route('/memory-heatmap', methods=['GET'])
@jwt_required(optional=True)
def get_memory_heatmap_v2():
    """Get memory density heatmap data for a region."""
    try:
        viewer_user_id = get_jwt_identity()
        viewer_user = User.query.get(viewer_user_id) if viewer_user_id else None
        
        # Get bounding box parameters
        north = request.args.get('north')
        south = request.args.get('south')
        east = request.args.get('east')
        west = request.args.get('west')
        
        if not all([north, south, east, west]):
            return create_error_response(
                'Missing Bounds',
                'North, south, east, and west bounds are required',
                400
            )
        
        # Validate coordinates
        try:
            north = float(north)
            south = float(south)
            east = float(east)
            west = float(west)
        except ValueError:
            return create_error_response(
                'Invalid Coordinates',
                'All bounds must be valid numbers',
                400
            )
        
        # Validate bounds
        if not (-90 <= south <= north <= 90):
            return create_error_response(
                'Invalid Latitude Bounds',
                'Latitude bounds must be between -90 and 90, with south <= north',
                400
            )
        
        if not (-180 <= west <= east <= 180):
            return create_error_response(
                'Invalid Longitude Bounds',
                'Longitude bounds must be between -180 and 180, with west <= east',
                400
            )
        
        # Grid size for heatmap
        grid_size = int(request.args.get('grid_size', 20))
        grid_size = min(max(grid_size, 5), 50)  # Between 5 and 50
        
        # Calculate grid cell size
        lat_step = (north - south) / grid_size
        lng_step = (east - west) / grid_size
        
        # Generate heatmap data
        heatmap_data = []
        
        for i in range(grid_size):
            for j in range(grid_size):
                cell_south = south + (i * lat_step)
                cell_north = south + ((i + 1) * lat_step)
                cell_west = west + (j * lng_step)
                cell_east = west + ((j + 1) * lng_step)
                
                # Count memories in this cell
                cell_center_lat = (cell_south + cell_north) / 2
                cell_center_lng = (cell_west + cell_east) / 2
                
                # Use PostGIS to count memories in bounding box
                count_query = db.session.query(func.count(Memory.memory_id)).filter(
                    Memory.is_active == True,
                    Memory.privacy_level == 'public',
                    Memory.latitude >= cell_south,
                    Memory.latitude <= cell_north,
                    Memory.longitude >= cell_west,
                    Memory.longitude <= cell_east
                )
                
                memory_count = count_query.scalar() or 0
                
                if memory_count > 0:
                    heatmap_data.append({
                        'latitude': cell_center_lat,
                        'longitude': cell_center_lng,
                        'intensity': memory_count,
                        'bounds': {
                            'north': cell_north,
                            'south': cell_south,
                            'east': cell_east,
                            'west': cell_west
                        }
                    })
        
        return create_success_response(
            data={
                'heatmap': heatmap_data,
                'bounds': {
                    'north': north,
                    'south': south,
                    'east': east,
                    'west': west
                },
                'grid_size': grid_size,
                'total_cells': len(heatmap_data)
            },
            message='Memory heatmap generated successfully'
        )
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Heatmap Generation Failed', str(e), 500)

@geospatial_bp.route('/popular-areas', methods=['GET'])
@jwt_required(optional=True)
def get_popular_areas_v2():
    """Get popular memory areas based on engagement."""
    try:
        viewer_user_id = get_jwt_identity()
        viewer_user = User.query.get(viewer_user_id) if viewer_user_id else None
        
        # Get location parameters
        latitude = request.args.get('latitude')
        longitude = request.args.get('longitude')
        radius = request.args.get('radius', 5000)  # Default 5km
        
        if not latitude or not longitude:
            return create_error_response(
                'Missing Location',
                'Latitude and longitude are required',
                400
            )
        
        # Validate parameters
        latitude, longitude = validate_coordinates(latitude, longitude)
        radius = min(float(radius), 10000)  # Max 10km
        
        # Get limit
        limit = int(request.args.get('limit', 10))
        limit = min(limit, 50)
        
        # Find popular memories in area
        popular_memories = Memory.get_popular_in_area(
            latitude, longitude, radius, limit=limit * 3  # Get more to cluster
        )
        
        # Group memories by location clusters (simplified clustering)
        location_clusters = {}
        cluster_radius = 100  # 100m cluster radius
        
        for memory in popular_memories:
            if not memory.can_view(viewer_user):
                continue
                
            # Find existing cluster or create new one
            memory_lat = memory.latitude
            memory_lng = memory.longitude
            
            cluster_key = None
            for key, cluster in location_clusters.items():
                cluster_lat, cluster_lng = key
                # Simple distance check (approximate)
                lat_diff = abs(memory_lat - cluster_lat)
                lng_diff = abs(memory_lng - cluster_lng)
                
                if lat_diff < 0.001 and lng_diff < 0.001:  # ~100m
                    cluster_key = key
                    break
            
            if cluster_key:
                location_clusters[cluster_key]['memories'].append(memory)
                location_clusters[cluster_key]['total_engagement'] += (
                    memory.likes_count + memory.comments_count + memory.discoveries_count
                )
            else:
                location_clusters[(memory_lat, memory_lng)] = {
                    'center': {'latitude': memory_lat, 'longitude': memory_lng},
                    'memories': [memory],
                    'total_engagement': memory.likes_count + memory.comments_count + memory.discoveries_count
                }
        
        # Convert to response format and sort by engagement
        popular_areas = []
        for cluster in location_clusters.values():
            area_data = {
                'center': cluster['center'],
                'memory_count': len(cluster['memories']),
                'total_engagement': cluster['total_engagement'],
                'sample_memories': [
                    memory.to_dict(user=viewer_user) 
                    for memory in cluster['memories'][:3]
                ]
            }
            popular_areas.append(area_data)
        
        # Sort by engagement
        popular_areas.sort(key=lambda x: x['total_engagement'], reverse=True)
        popular_areas = popular_areas[:limit]
        
        return create_success_response(
            data={
                'popular_areas': popular_areas,
                'search_location': {'latitude': latitude, 'longitude': longitude},
                'search_radius': radius,
                'total_areas': len(popular_areas)
            },
            message='Popular areas retrieved successfully'
        )
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Popular Areas Retrieval Failed', str(e), 500)

@geospatial_bp.route('/nearby-users-v2', methods=['GET'])
@jwt_required()
def get_nearby_users_v2():
    """Get users who have created memories near a location."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return create_error_response('User Not Found', 'User not found', 404)
        
        # Get location parameters
        latitude = request.args.get('latitude')
        longitude = request.args.get('longitude')
        radius = request.args.get('radius', 1000)  # Default 1km
        
        if not latitude or not longitude:
            return create_error_response(
                'Missing Location',
                'Latitude and longitude are required',
                400
            )
        
        # Validate parameters
        latitude, longitude = validate_coordinates(latitude, longitude)
        radius = validate_search_radius(radius)
        
        # Get limit
        limit = int(request.args.get('limit', 20))
        limit = min(limit, 50)
        
        # Find users with memories in the area
        point = func.ST_GeomFromText(f'POINT({longitude} {latitude})', 4326)
        
        nearby_users_query = db.session.query(
            User,
            func.count(Memory.memory_id).label('memory_count'),
            func.min(func.ST_Distance(Memory.location, point)).label('closest_distance')
        ).join(
            Memory, User.user_id == Memory.creator_id
        ).filter(
            func.ST_DWithin(Memory.location, point, radius),
            Memory.is_active == True,
            Memory.privacy_level == 'public',
            User.is_active == True,
            User.user_id != user_id  # Exclude current user
        ).group_by(User.user_id).order_by(
            'closest_distance'
        ).limit(limit).all()
        
        nearby_users = []
        for user_obj, memory_count, closest_distance in nearby_users_query:
            # Check if user profile can be viewed
            if user_obj.can_view_profile(user):
                user_data = user_obj.to_dict(viewer_user=user)
                user_data.update({
                    'nearby_memory_count': memory_count,
                    'closest_memory_distance': round(closest_distance, 2)
                })
                nearby_users.append(user_data)
        
        return create_success_response(
            data={
                'nearby_users': nearby_users,
                'location': {'latitude': latitude, 'longitude': longitude},
                'radius': radius,
                'total': len(nearby_users)
            },
            message='Nearby users retrieved successfully'
        )
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Nearby Users Retrieval Failed', str(e), 500)

@geospatial_bp.route('/location-stats', methods=['GET'])
@jwt_required(optional=True)
def get_location_stats():
    """Get statistics for a specific location."""
    try:
        viewer_user_id = get_jwt_identity()
        viewer_user = User.query.get(viewer_user_id) if viewer_user_id else None
        
        # Get location parameters
        latitude = request.args.get('latitude')
        longitude = request.args.get('longitude')
        radius = request.args.get('radius', 500)
        
        if not latitude or not longitude:
            return create_error_response(
                'Missing Location',
                'Latitude and longitude are required',
                400
            )
        
        # Validate parameters
        latitude, longitude = validate_coordinates(latitude, longitude)
        radius = validate_search_radius(radius)
        
        # Get memories in area
        point = func.ST_GeomFromText(f'POINT({longitude} {latitude})', 4326)
        
        # Basic memory count
        total_memories = db.session.query(func.count(Memory.memory_id)).filter(
            func.ST_DWithin(Memory.location, point, radius),
            Memory.is_active == True,
            Memory.privacy_level == 'public'
        ).scalar() or 0
        
        # Content type distribution
        content_stats = db.session.query(
            Memory.content_type,
            func.count(Memory.memory_id).label('count')
        ).filter(
            func.ST_DWithin(Memory.location, point, radius),
            Memory.is_active == True,
            Memory.privacy_level == 'public'
        ).group_by(Memory.content_type).all()
        
        content_distribution = {content_type: count for content_type, count in content_stats}
        
        # Unique creators
        unique_creators = db.session.query(func.count(func.distinct(Memory.creator_id))).filter(
            func.ST_DWithin(Memory.location, point, radius),
            Memory.is_active == True,
            Memory.privacy_level == 'public'
        ).scalar() or 0
        
        # Total engagement
        engagement_stats = db.session.query(
            func.sum(Memory.likes_count).label('total_likes'),
            func.sum(Memory.comments_count).label('total_comments'),
            func.sum(Memory.views_count).label('total_views'),
            func.sum(Memory.discoveries_count).label('total_discoveries')
        ).filter(
            func.ST_DWithin(Memory.location, point, radius),
            Memory.is_active == True,
            Memory.privacy_level == 'public'
        ).first()
        
        stats = {
            'location': {'latitude': latitude, 'longitude': longitude},
            'radius': radius,
            'total_memories': total_memories,
            'unique_creators': unique_creators,
            'content_distribution': content_distribution,
            'engagement': {
                'total_likes': engagement_stats.total_likes or 0,
                'total_comments': engagement_stats.total_comments or 0,
                'total_views': engagement_stats.total_views or 0,
                'total_discoveries': engagement_stats.total_discoveries or 0
            }
        }
        
        # Most popular memory in area
        if total_memories > 0:
            popular_memory = db.session.query(Memory).filter(
                func.ST_DWithin(Memory.location, point, radius),
                Memory.is_active == True,
                Memory.privacy_level == 'public'
            ).order_by(
                (Memory.likes_count + Memory.comments_count + Memory.discoveries_count).desc()
            ).first()
            
            if popular_memory and popular_memory.can_view(viewer_user):
                stats['most_popular_memory'] = popular_memory.to_dict(user=viewer_user)
        
        return create_success_response(
            data={'stats': stats},
            message='Location statistics retrieved successfully'
        )
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Location Stats Retrieval Failed', str(e), 500)

@geospatial_bp.route('/discover-route', methods=['POST'])
@jwt_required()
def discover_route():
    """Get memories along a route for discovery."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return create_error_response('User Not Found', 'User not found', 404)
        
        if not user.can_discover_memories():
            return create_error_response(
                'Discovery Disabled',
                'Memory discovery is disabled in your privacy settings',
                403
            )
        
        data = request.get_json()
        if not data:
            return create_error_response('Invalid Request', 'Request body is required', 400)
        
        # Get route waypoints
        waypoints = data.get('waypoints', [])
        if len(waypoints) < 2:
            return create_error_response(
                'Invalid Route',
                'At least 2 waypoints are required',
                400
            )
        
        # Validate waypoints
        validated_waypoints = []
        for i, waypoint in enumerate(waypoints):
            if not isinstance(waypoint, dict) or 'latitude' not in waypoint or 'longitude' not in waypoint:
                return create_error_response(
                    'Invalid Waypoint',
                    f'Waypoint {i+1} must have latitude and longitude',
                    400
                )
            
            lat, lng = validate_coordinates(waypoint['latitude'], waypoint['longitude'])
            validated_waypoints.append({'latitude': lat, 'longitude': lng})
        
        route_radius = float(data.get('radius', 200))  # 200m default
        route_radius = min(route_radius, 500)  # Max 500m
        
        # Find memories along route
        route_memories = []
        
        for waypoint in validated_waypoints:
            nearby = Memory.find_nearby(
                waypoint['latitude'],
                waypoint['longitude'],
                route_radius,
                limit=10,
                user=user
            )
            
            # Add waypoint info and avoid duplicates
            for memory_data in nearby:
                memory_id = memory_data['memory_id']
                if not any(m['memory_id'] == memory_id for m in route_memories):
                    memory_data['discovered_at_waypoint'] = waypoint
                    route_memories.append(memory_data)
        
        # Sort by distance from route start
        if route_memories and validated_waypoints:
            start_point = validated_waypoints[0]
            for memory in route_memories:
                # Simple distance calculation
                lat_diff = memory['latitude'] - start_point['latitude']
                lng_diff = memory['longitude'] - start_point['longitude']
                memory['distance_from_start'] = (lat_diff**2 + lng_diff**2)**0.5
            
            route_memories.sort(key=lambda x: x['distance_from_start'])
        
        return create_success_response(
            data={
                'route_memories': route_memories[:20],  # Limit to 20
                'waypoints': validated_waypoints,
                'radius': route_radius,
                'total_discovered': len(route_memories)
            },
            message='Route discovery completed successfully'
        )
        
    except ValidationError as e:
        return create_error_response('Validation Error', str(e), 400)
    except Exception as e:
        return create_error_response('Route Discovery Failed', str(e), 500) 