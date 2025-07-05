import re
from typing import Optional
from email_validator import validate_email, EmailNotValidError
from werkzeug.datastructures import FileStorage


class ValidationError(Exception):
    """Custom validation error exception."""
    pass


def validate_email_format(email: str) -> Optional[str]:
    """Validate email format."""
    if not email:
        return "Email is required"
    
    # Basic email regex pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        return "Invalid email format"
    
    if len(email) > 120:
        return "Email is too long (maximum 120 characters)"
    
    return None


def validate_username(username: str) -> Optional[str]:
    """Validate username format and constraints."""
    if not username:
        return "Username is required"
    
    if len(username) < 3:
        return "Username must be at least 3 characters long"
    
    if len(username) > 50:
        return "Username must not exceed 50 characters"
    
    # Allow letters, numbers, underscores, and hyphens
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return "Username can only contain letters, numbers, underscores, and hyphens"
    
    # Cannot start or end with special characters
    if username.startswith(('_', '-')) or username.endswith(('_', '-')):
        return "Username cannot start or end with underscores or hyphens"
    
    # Check for reserved usernames
    reserved_usernames = {
        'admin', 'administrator', 'root', 'moderator', 'mod',
        'api', 'www', 'mail', 'ftp', 'test', 'guest', 'user',
        'support', 'help', 'info', 'contact', 'about', 'terms',
        'privacy', 'security', 'login', 'register', 'signup',
        'signin', 'logout', 'profile', 'settings', 'account'
    }
    
    if username.lower() in reserved_usernames:
        return "This username is reserved and cannot be used"
    
    return None


def validate_password(password: str) -> Optional[str]:
    """Validate password strength."""
    if not password:
        return "Password is required"
    
    if len(password) < 8:
        return "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return "Password must not exceed 128 characters"
    
    # Check for at least one uppercase letter
    if not re.search(r'[A-Z]', password):
        return "Password must contain at least one uppercase letter"
    
    # Check for at least one lowercase letter
    if not re.search(r'[a-z]', password):
        return "Password must contain at least one lowercase letter"
    
    # Check for at least one digit
    if not re.search(r'\d', password):
        return "Password must contain at least one number"
    
    # Check for at least one special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return "Password must contain at least one special character"
    
    # Check for common weak passwords
    weak_passwords = {
        'password', '12345678', 'qwerty123', 'password123',
        'admin123', 'letmein123', 'welcome123', 'password1',
        '123456789', 'qwertyuiop'
    }
    
    if password.lower() in weak_passwords:
        return "This password is too common and cannot be used"
    
    return None


def validate_coordinates(latitude: float, longitude: float) -> Optional[str]:
    """Validate GPS coordinates."""
    if latitude is None or longitude is None:
        return "Latitude and longitude are required"
    
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (ValueError, TypeError):
        return "Invalid coordinate format"
    
    if not (-90 <= lat <= 90):
        return "Latitude must be between -90 and 90 degrees"
    
    if not (-180 <= lon <= 180):
        return "Longitude must be between -180 and 180 degrees"
    
    return None


def validate_content_type(content_type: str) -> Optional[str]:
    """Validate memory content type."""
    valid_types = {'photo', 'audio', 'video', 'text'}
    
    if not content_type:
        return "Content type is required"
    
    if content_type.lower() not in valid_types:
        return f"Invalid content type. Must be one of: {', '.join(valid_types)}"
    
    return None


def validate_privacy_level(privacy_level: str) -> Optional[str]:
    """Validate memory privacy level."""
    valid_levels = {'public', 'friends', 'private'}
    
    if not privacy_level:
        return "Privacy level is required"
    
    if privacy_level.lower() not in valid_levels:
        return f"Invalid privacy level. Must be one of: {', '.join(valid_levels)}"
    
    return None


def validate_search_radius(radius: int) -> Optional[str]:
    """Validate search radius for memory discovery."""
    if radius is None:
        return "Search radius is required"
    
    try:
        radius = int(radius)
    except (ValueError, TypeError):
        return "Search radius must be a number"
    
    if radius < 50:
        return "Search radius must be at least 50 meters"
    
    if radius > 1000:
        return "Search radius cannot exceed 1000 meters"
    
    return None


def validate_file_extension(filename: str, allowed_extensions: set) -> Optional[str]:
    """Validate file extension."""
    if not filename:
        return "Filename is required"
    
    if '.' not in filename:
        return "File must have an extension"
    
    extension = filename.rsplit('.', 1)[1].lower()
    
    if extension not in allowed_extensions:
        return f"File type not allowed. Allowed extensions: {', '.join(allowed_extensions)}"
    
    return None


def validate_memory_title(title: str) -> Optional[str]:
    """Validate memory title."""
    if not title:
        return "Memory title is required"
    
    title = title.strip()
    
    if len(title) < 3:
        return "Memory title must be at least 3 characters long"
    
    if len(title) > 200:
        return "Memory title must not exceed 200 characters"
    
    return None


def validate_memory_description(description: str) -> Optional[str]:
    """Validate memory description."""
    if description and len(description) > 2000:
        return "Description is too long (maximum 2000 characters)"
    
    return None


def sanitize_input(text: str) -> str:
    """Sanitize user input by removing dangerous characters."""
    if not text:
        return ""
    
    # Remove null bytes and other control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def validate_email_address(email):
    """Validate email format."""
    if not email:
        raise ValidationError("Email is required")
    
    try:
        # Use email-validator library for robust validation
        valid = validate_email(email)
        return valid.email.lower()
    except EmailNotValidError as e:
        raise ValidationError(f"Invalid email address: {str(e)}")


def validate_radius(radius):
    """Validate search radius."""
    try:
        radius = float(radius)
    except (ValueError, TypeError):
        raise ValidationError("Radius must be a valid number")
    
    if radius < 10:
        raise ValidationError("Radius must be at least 10 meters")
    
    if radius > 5000:  # 5km max
        raise ValidationError("Radius must not exceed 5000 meters")
    
    return radius


def validate_file_upload(file):
    """Validate uploaded file."""
    if not isinstance(file, FileStorage):
        raise ValidationError("Invalid file upload")
    
    if not file.filename:
        raise ValidationError("No file selected")
    
    # Check file extension
    allowed_extensions = {
        'jpg', 'jpeg', 'png', 'gif', 'webp',  # Images
        'mp4', 'avi', 'mov', 'webm',  # Videos
        'mp3', 'wav', 'ogg', 'm4a',  # Audio
        'txt', 'md'  # Text files
    }
    
    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    if file_ext not in allowed_extensions:
        raise ValidationError(f"File type .{file_ext} not allowed. Allowed types: {', '.join(allowed_extensions)}")
    
    # Check file size (will be handled by Flask's MAX_CONTENT_LENGTH)
    return file


def validate_tags(tags):
    """Validate tags list."""
    if not tags:
        return []
    
    if not isinstance(tags, list):
        raise ValidationError("Tags must be a list")
    
    if len(tags) > 10:
        raise ValidationError("Cannot have more than 10 tags")
    
    validated_tags = []
    for tag in tags:
        if not isinstance(tag, str):
            raise ValidationError("Each tag must be a string")
        
        tag = tag.strip().lower()
        
        if len(tag) < 2:
            raise ValidationError("Each tag must be at least 2 characters long")
        
        if len(tag) > 30:
            raise ValidationError("Each tag must not exceed 30 characters")
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', tag):
            raise ValidationError("Tags can only contain letters, numbers, underscores, and hyphens")
        
        if tag not in validated_tags:  # Avoid duplicates
            validated_tags.append(tag)
    
    return validated_tags


def validate_comment_content(content):
    """Validate comment content."""
    if not content:
        raise ValidationError("Comment content is required")
    
    content = content.strip()
    
    if len(content) < 1:
        raise ValidationError("Comment cannot be empty")
    
    if len(content) > 1000:
        raise ValidationError("Comment must not exceed 1000 characters")
    
    return content


def validate_report_reason(reason):
    """Validate report reason."""
    valid_reasons = [
        'inappropriate_content',
        'spam',
        'harassment',
        'copyright_violation',
        'false_information',
        'other'
    ]
    
    if reason not in valid_reasons:
        raise ValidationError(f"Report reason must be one of: {', '.join(valid_reasons)}")
    
    return reason


def validate_search_query(query):
    """Validate search query."""
    if not query:
        raise ValidationError("Search query is required")
    
    query = query.strip()
    
    if len(query) < 2:
        raise ValidationError("Search query must be at least 2 characters long")
    
    if len(query) > 100:
        raise ValidationError("Search query must not exceed 100 characters")
    
    return query


def validate_pagination(page, per_page):
    """Validate pagination parameters."""
    try:
        page = int(page) if page else 1
        per_page = int(per_page) if per_page else 20
    except (ValueError, TypeError):
        raise ValidationError("Page and per_page must be valid integers")
    
    if page < 1:
        raise ValidationError("Page must be at least 1")
    
    if per_page < 1:
        raise ValidationError("Per page must be at least 1")
    
    if per_page > 100:
        raise ValidationError("Per page must not exceed 100")
    
    return page, per_page


def validate_uuid(uuid_string):
    """Validate UUID format."""
    if not uuid_string:
        raise ValidationError("UUID is required")
    
    # Basic UUID format validation
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    
    if not re.match(uuid_pattern, str(uuid_string).lower()):
        raise ValidationError("Invalid UUID format")
    
    return str(uuid_string).lower()


def sanitize_filename(filename):
    """Sanitize filename for safe storage."""
    if not filename:
        return None
    
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Replace special characters with underscores
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Remove multiple consecutive underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_length = 255 - len(ext) - 1 if ext else 255
        filename = name[:max_name_length] + ('.' + ext if ext else '')
    
    return filename 