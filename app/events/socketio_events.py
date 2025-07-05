from flask_socketio import emit, join_room, leave_room, disconnect
from flask_jwt_extended import decode_token
from app import socketio, db
from app.models.user import User
from app.models.memory import Memory
from app.models.interaction import Interaction, InteractionType
from datetime import datetime
import json


# Store active connections
active_connections = {}


@socketio.on('connect')
def handle_connect(auth):
    """Handle client connection."""
    try:
        # Verify JWT token from auth
        if not auth or 'token' not in auth:
            disconnect()
            return False
        
        # Decode JWT token
        try:
            decoded_token = decode_token(auth['token'])
            user_id = decoded_token['sub']
        except:
            disconnect()
            return False
        
        # Verify user exists and is active
        user = User.query.get(user_id)
        if not user or not user.is_active:
            disconnect()
            return False
        
        # Store connection
        active_connections[request.sid] = {
            'user_id': user_id,
            'username': user.username,
            'connected_at': datetime.utcnow()
        }
        
        # Join user to their personal room
        join_room(f"user_{user_id}")
        
        # Emit connection confirmation
        emit('connected', {
            'message': 'Successfully connected to Memory Lane',
            'user_id': user_id,
            'username': user.username
        })
        
        # Update user's last seen
        user.last_seen = datetime.utcnow()
        db.session.commit()
        
        print(f"User {user.username} connected via Socket.IO")
        
    except Exception as e:
        print(f"Connection error: {str(e)}")
        disconnect()
        return False


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    try:
        connection_info = active_connections.pop(request.sid, None)
        if connection_info:
            user_id = connection_info['user_id']
            username = connection_info['username']
            
            # Leave all rooms
            leave_room(f"user_{user_id}")
            
            print(f"User {username} disconnected from Socket.IO")
        
    except Exception as e:
        print(f"Disconnection error: {str(e)}")


@socketio.on('join_location')
def handle_join_location(data):
    """Join a location-based room for proximity notifications."""
    try:
        connection_info = active_connections.get(request.sid)
        if not connection_info:
            return
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not latitude or not longitude:
            emit('error', {'message': 'Latitude and longitude are required'})
            return
        
        # Create location room identifier (grid-based)
        # Round to ~100m precision for grouping nearby users
        lat_grid = round(latitude, 3)  # ~111m precision
        lon_grid = round(longitude, 3)  # ~111m precision at equator
        
        location_room = f"location_{lat_grid}_{lon_grid}"
        
        # Leave any previous location room
        if 'location_room' in connection_info:
            leave_room(connection_info['location_room'])
        
        # Join new location room
        join_room(location_room)
        active_connections[request.sid]['location_room'] = location_room
        active_connections[request.sid]['current_location'] = {
            'latitude': latitude,
            'longitude': longitude
        }
        
        emit('location_joined', {
            'room': location_room,
            'latitude': lat_grid,
            'longitude': lon_grid
        })
        
    except Exception as e:
        emit('error', {'message': 'Failed to join location'})


@socketio.on('leave_location')
def handle_leave_location():
    """Leave current location room."""
    try:
        connection_info = active_connections.get(request.sid)
        if not connection_info:
            return
        
        if 'location_room' in connection_info:
            leave_room(connection_info['location_room'])
            del active_connections[request.sid]['location_room']
            del active_connections[request.sid]['current_location']
            
            emit('location_left', {'message': 'Left location room'})
        
    except Exception as e:
        emit('error', {'message': 'Failed to leave location'})


@socketio.on('memory_created')
def handle_memory_created(data):
    """Notify nearby users when a new memory is created."""
    try:
        connection_info = active_connections.get(request.sid)
        if not connection_info:
            return
        
        memory_id = data.get('memory_id')
        if not memory_id:
            return
        
        memory = Memory.query.get(memory_id)
        if not memory or not memory.is_active:
            return
        
        # Get memory location for room calculation
        lat_grid = round(memory.latitude, 3)
        lon_grid = round(memory.longitude, 3)
        location_room = f"location_{lat_grid}_{lon_grid}"
        
        # Notify users in the same location room
        socketio.emit('new_memory_nearby', {
            'memory_id': memory.memory_id,
            'title': memory.title,
            'content_type': memory.content_type.value,
            'creator_username': memory.creator.username,
            'latitude': memory.latitude,
            'longitude': memory.longitude,
            'created_at': memory.created_at.isoformat()
        }, room=location_room)
        
    except Exception as e:
        print(f"Memory creation notification error: {str(e)}")


@socketio.on('memory_liked')
def handle_memory_liked(data):
    """Notify memory creator when their memory is liked."""
    try:
        connection_info = active_connections.get(request.sid)
        if not connection_info:
            return
        
        memory_id = data.get('memory_id')
        if not memory_id:
            return
        
        memory = Memory.query.get(memory_id)
        if not memory or not memory.is_active:
            return
        
        # Don't notify if user liked their own memory
        if memory.creator_id == connection_info['user_id']:
            return
        
        # Notify memory creator
        socketio.emit('memory_interaction', {
            'type': 'like',
            'memory_id': memory.memory_id,
            'memory_title': memory.title,
            'from_user': connection_info['username'],
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"user_{memory.creator_id}")
        
    except Exception as e:
        print(f"Memory like notification error: {str(e)}")


@socketio.on('memory_commented')
def handle_memory_commented(data):
    """Notify memory creator when someone comments on their memory."""
    try:
        connection_info = active_connections.get(request.sid)
        if not connection_info:
            return
        
        memory_id = data.get('memory_id')
        comment_content = data.get('comment_content', '')
        
        if not memory_id:
            return
        
        memory = Memory.query.get(memory_id)
        if not memory or not memory.is_active:
            return
        
        # Don't notify if user commented on their own memory
        if memory.creator_id == connection_info['user_id']:
            return
        
        # Notify memory creator
        socketio.emit('memory_interaction', {
            'type': 'comment',
            'memory_id': memory.memory_id,
            'memory_title': memory.title,
            'from_user': connection_info['username'],
            'comment_preview': comment_content[:100] + '...' if len(comment_content) > 100 else comment_content,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"user_{memory.creator_id}")
        
    except Exception as e:
        print(f"Memory comment notification error: {str(e)}")


@socketio.on('get_nearby_users')
def handle_get_nearby_users():
    """Get list of users currently in the same location room."""
    try:
        connection_info = active_connections.get(request.sid)
        if not connection_info or 'location_room' not in connection_info:
            emit('nearby_users', {'users': []})
            return
        
        location_room = connection_info['location_room']
        nearby_users = []
        
        for sid, conn_info in active_connections.items():
            if (conn_info.get('location_room') == location_room and 
                conn_info['user_id'] != connection_info['user_id']):
                
                nearby_users.append({
                    'user_id': conn_info['user_id'],
                    'username': conn_info['username'],
                    'location': conn_info.get('current_location')
                })
        
        emit('nearby_users', {'users': nearby_users})
        
    except Exception as e:
        emit('error', {'message': 'Failed to get nearby users'})


@socketio.on('ping')
def handle_ping():
    """Handle ping for connection health check."""
    emit('pong', {'timestamp': datetime.utcnow().isoformat()})


@socketio.on('user_status')
def handle_user_status():
    """Get current user status and connection info."""
    try:
        connection_info = active_connections.get(request.sid)
        if not connection_info:
            emit('status', {'connected': False})
            return
        
        emit('status', {
            'connected': True,
            'user_id': connection_info['user_id'],
            'username': connection_info['username'],
            'connected_at': connection_info['connected_at'].isoformat(),
            'current_location': connection_info.get('current_location'),
            'location_room': connection_info.get('location_room')
        })
        
    except Exception as e:
        emit('error', {'message': 'Failed to get user status'})


# Helper function to send notifications to specific users
def notify_user(user_id, event_name, data):
    """Send a notification to a specific user."""
    try:
        socketio.emit(event_name, data, room=f"user_{user_id}")
    except Exception as e:
        print(f"Failed to notify user {user_id}: {str(e)}")


# Helper function to notify users in a location
def notify_location(latitude, longitude, event_name, data, exclude_user_id=None):
    """Send a notification to users in a specific location."""
    try:
        lat_grid = round(latitude, 3)
        lon_grid = round(longitude, 3)
        location_room = f"location_{lat_grid}_{lon_grid}"
        
        if exclude_user_id:
            # Filter out the excluded user
            for sid, conn_info in active_connections.items():
                if (conn_info.get('location_room') == location_room and 
                    conn_info['user_id'] != exclude_user_id):
                    socketio.emit(event_name, data, room=sid)
        else:
            socketio.emit(event_name, data, room=location_room)
            
    except Exception as e:
        print(f"Failed to notify location: {str(e)}")


# Export helper functions for use in other modules
__all__ = ['notify_user', 'notify_location'] 