from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db, limiter
from app.utils.validators import validate_file_extension
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime

uploads_bp = Blueprint('uploads', __name__)

def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def generate_unique_filename(original_filename):
    """Generate a unique filename while preserving the extension."""
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    name, ext = os.path.splitext(secure_filename(original_filename))
    return f"{timestamp}_{unique_id}_{name}{ext}"

@uploads_bp.route('/image', methods=['POST'])
@jwt_required()
@limiter.limit("20 per hour")
def upload_image():
    """Upload an image file for memories."""
    try:
        current_user_id = get_jwt_identity()
        
        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file extension
        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
        if not allowed_file(file.filename, allowed_extensions):
            return jsonify({
                'error': f'File type not allowed. Allowed extensions: {", ".join(allowed_extensions)}'
            }), 400
        
        # Check file size (16MB limit)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        max_size = current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
        if file_size > max_size:
            return jsonify({
                'error': f'File too large. Maximum size: {max_size // (1024*1024)}MB'
            }), 400
        
        # Generate unique filename
        filename = generate_unique_filename(file.filename)
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(current_app.root_path, '..', 'uploads', 'images')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Generate URL (in production, this would be a CDN URL)
        file_url = f"/uploads/images/{filename}"
        
        return jsonify({
            'message': 'Image uploaded successfully',
            'file_url': file_url,
            'filename': filename,
            'file_size': file_size,
            'content_type': 'photo'
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Image upload error: {str(e)}")
        return jsonify({'error': 'Failed to upload image'}), 500


@uploads_bp.route('/audio', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def upload_audio():
    """Upload an audio file for memories."""
    try:
        current_user_id = get_jwt_identity()
        
        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file extension
        allowed_extensions = {'mp3', 'wav', 'aac', 'm4a', 'ogg'}
        if not allowed_file(file.filename, allowed_extensions):
            return jsonify({
                'error': f'File type not allowed. Allowed extensions: {", ".join(allowed_extensions)}'
            }), 400
        
        # Check file size (32MB limit for audio)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        max_size = 32 * 1024 * 1024  # 32MB
        if file_size > max_size:
            return jsonify({
                'error': f'File too large. Maximum size: {max_size // (1024*1024)}MB'
            }), 400
        
        # Generate unique filename
        filename = generate_unique_filename(file.filename)
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(current_app.root_path, '..', 'uploads', 'audio')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Generate URL
        file_url = f"/uploads/audio/{filename}"
        
        # Try to get audio duration (optional - requires additional libraries)
        duration = None
        try:
            # This would require a library like mutagen or pydub
            # For now, we'll leave it as None
            pass
        except:
            pass
        
        return jsonify({
            'message': 'Audio uploaded successfully',
            'file_url': file_url,
            'filename': filename,
            'file_size': file_size,
            'duration': duration,
            'content_type': 'audio'
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Audio upload error: {str(e)}")
        return jsonify({'error': 'Failed to upload audio'}), 500


@uploads_bp.route('/video', methods=['POST'])
@jwt_required()
@limiter.limit("5 per hour")
def upload_video():
    """Upload a video file for memories."""
    try:
        current_user_id = get_jwt_identity()
        
        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file extension
        allowed_extensions = {'mp4', 'mov', 'avi', 'webm', 'mkv'}
        if not allowed_file(file.filename, allowed_extensions):
            return jsonify({
                'error': f'File type not allowed. Allowed extensions: {", ".join(allowed_extensions)}'
            }), 400
        
        # Check file size (100MB limit for video)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        max_size = 100 * 1024 * 1024  # 100MB
        if file_size > max_size:
            return jsonify({
                'error': f'File too large. Maximum size: {max_size // (1024*1024)}MB'
            }), 400
        
        # Generate unique filename
        filename = generate_unique_filename(file.filename)
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(current_app.root_path, '..', 'uploads', 'videos')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Generate URL
        file_url = f"/uploads/videos/{filename}"
        
        # Try to get video duration and dimensions (optional)
        duration = None
        dimensions = None
        try:
            # This would require a library like opencv-python or moviepy
            # For now, we'll leave them as None
            pass
        except:
            pass
        
        return jsonify({
            'message': 'Video uploaded successfully',
            'file_url': file_url,
            'filename': filename,
            'file_size': file_size,
            'duration': duration,
            'dimensions': dimensions,
            'content_type': 'video'
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Video upload error: {str(e)}")
        return jsonify({'error': 'Failed to upload video'}), 500


@uploads_bp.route('/profile-image', methods=['POST'])
@jwt_required()
@limiter.limit("5 per hour")
def upload_profile_image():
    """Upload a profile image for user."""
    try:
        current_user_id = get_jwt_identity()
        
        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file extension
        allowed_extensions = {'jpg', 'jpeg', 'png', 'webp'}
        if not allowed_file(file.filename, allowed_extensions):
            return jsonify({
                'error': f'File type not allowed. Allowed extensions: {", ".join(allowed_extensions)}'
            }), 400
        
        # Check file size (5MB limit for profile images)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        max_size = 5 * 1024 * 1024  # 5MB
        if file_size > max_size:
            return jsonify({
                'error': f'File too large. Maximum size: {max_size // (1024*1024)}MB'
            }), 400
        
        # Generate unique filename
        filename = f"profile_{current_user_id}_{generate_unique_filename(file.filename)}"
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(current_app.root_path, '..', 'uploads', 'profiles')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Generate URL
        file_url = f"/uploads/profiles/{filename}"
        
        # Update user's profile photo URL
        from app.models.user import User
        user = User.query.get(current_user_id)
        if user:
            user.profile_photo_url = file_url
            db.session.commit()
        
        return jsonify({
            'message': 'Profile image uploaded successfully',
            'file_url': file_url,
            'filename': filename,
            'file_size': file_size
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Profile image upload error: {str(e)}")
        return jsonify({'error': 'Failed to upload profile image'}), 500


@uploads_bp.route('/delete/<path:file_path>', methods=['DELETE'])
@jwt_required()
def delete_file(file_path):
    """Delete an uploaded file."""
    try:
        current_user_id = get_jwt_identity()
        
        # Security check - ensure the file path is safe
        if '..' in file_path or file_path.startswith('/'):
            return jsonify({'error': 'Invalid file path'}), 400
        
        # Construct full file path
        full_path = os.path.join(current_app.root_path, '..', 'uploads', file_path)
        
        # Check if file exists
        if not os.path.exists(full_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Additional security check - verify user owns the file
        # This would require tracking file ownership in the database
        # For now, we'll allow deletion (in production, add proper checks)
        
        try:
            os.remove(full_path)
            return jsonify({
                'message': 'File deleted successfully'
            }), 200
        except OSError as e:
            current_app.logger.error(f"File deletion error: {str(e)}")
            return jsonify({'error': 'Failed to delete file'}), 500
        
    except Exception as e:
        current_app.logger.error(f"File deletion error: {str(e)}")
        return jsonify({'error': 'Failed to delete file'}), 500


@uploads_bp.route('/info', methods=['GET'])
@jwt_required()
def get_upload_info():
    """Get upload configuration and limits."""
    try:
        upload_config = {
            'max_file_sizes': {
                'image': '16MB',
                'audio': '32MB',
                'video': '100MB',
                'profile_image': '5MB'
            },
            'allowed_extensions': {
                'image': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
                'audio': ['mp3', 'wav', 'aac', 'm4a', 'ogg'],
                'video': ['mp4', 'mov', 'avi', 'webm', 'mkv'],
                'profile_image': ['jpg', 'jpeg', 'png', 'webp']
            },
            'rate_limits': {
                'image': '20 per hour',
                'audio': '10 per hour',
                'video': '5 per hour',
                'profile_image': '5 per hour'
            }
        }
        
        return jsonify(upload_config), 200
        
    except Exception as e:
        current_app.logger.error(f"Upload info error: {str(e)}")
        return jsonify({'error': 'Failed to get upload info'}), 500 