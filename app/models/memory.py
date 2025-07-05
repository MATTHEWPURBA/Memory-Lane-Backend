from app import db
from datetime import datetime, timedelta
from uuid import uuid4
from geoalchemy2 import Geography, Geometry
from sqlalchemy import func, text
import enum
from sqlalchemy.dialects.postgresql import UUID, ARRAY


class ContentType(enum.Enum):
    """Enum for memory content types."""
    PHOTO = 'photo'
    AUDIO = 'audio'
    VIDEO = 'video'
    TEXT = 'text'


class PrivacyLevel(enum.Enum):
    """Enum for memory privacy levels."""
    PUBLIC = 'public'
    FRIENDS = 'friends'
    PRIVATE = 'private'


class Memory(db.Model):
    """Memory model for storing location-based memories with geospatial data."""
    
    __tablename__ = 'memories'
    
    # Primary fields
    memory_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    creator_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    
    # Location data (PostGIS)
    location = db.Column(Geometry('POINT', srid=4326), nullable=False, index=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    location_name = db.Column(db.String(255), nullable=True)  # Human-readable location
    
    # Content information
    content_type = db.Column(db.String(20), nullable=False)  # text, image, audio, video
    content_url = db.Column(db.String(500), nullable=True)  # File URL for media
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    content_text = db.Column(db.Text, nullable=True)  # For text-based memories
    
    # Privacy and visibility
    privacy_level = db.Column(db.String(20), default='public', nullable=False)  # public, friends, private
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_reported = db.Column(db.Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expiration_date = db.Column(db.DateTime, nullable=True)  # Optional expiry
    
    # Engagement metrics
    likes_count = db.Column(db.Integer, default=0, nullable=False)
    comments_count = db.Column(db.Integer, default=0, nullable=False)
    views_count = db.Column(db.Integer, default=0, nullable=False)
    discoveries_count = db.Column(db.Integer, default=0, nullable=False)
    
    # Classification and metadata
    category_tags = db.Column(ARRAY(db.String), default=list, nullable=False)
    ai_generated_tags = db.Column(ARRAY(db.String), default=list, nullable=False)
    mood = db.Column(db.String(50), nullable=True)  # happy, sad, nostalgic, etc.
    
    # Media metadata
    media_duration = db.Column(db.Float, nullable=True)  # For audio/video content
    media_size = db.Column(db.Integer, nullable=True)  # File size in bytes
    media_format = db.Column(db.String(20), nullable=True)  # File format
    thumbnail_url = db.Column(db.String(500), nullable=True)  # Thumbnail for videos
    
    # Relationships
    creator = db.relationship('User', back_populates='created_memories')
    interactions = db.relationship('Interaction', back_populates='memory', lazy='dynamic')
    
    def __init__(self, creator_id, latitude, longitude, title, content_type, **kwargs):
        """Initialize memory with required fields."""
        self.creator_id = creator_id
        self.latitude = latitude
        self.longitude = longitude
        self.title = title
        self.content_type = content_type
        
        # Create PostGIS point from coordinates
        self.location = func.ST_GeomFromText(f'POINT({longitude} {latitude})', 4326)
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @property
    def is_expired(self):
        """Check if memory has expired."""
        if self.expiration_date:
            return datetime.utcnow() > self.expiration_date
        return False
    
    @property
    def coordinates(self):
        """Get coordinates as tuple."""
        return (self.latitude, self.longitude)
    
    def update_location(self, latitude, longitude):
        """Update memory location."""
        self.latitude = latitude
        self.longitude = longitude
        self.location = func.ST_GeomFromText(f'POINT({longitude} {latitude})', 4326)
        db.session.commit()
    
    def add_tags(self, tags):
        """Add category tags."""
        if self.category_tags is None:
            self.category_tags = []
        self.category_tags.extend([tag for tag in tags if tag not in self.category_tags])
        db.session.commit()
    
    def add_ai_tags(self, tags):
        """Add AI-generated tags."""
        if self.ai_generated_tags is None:
            self.ai_generated_tags = []
        self.ai_generated_tags.extend([tag for tag in tags if tag not in self.ai_generated_tags])
        db.session.commit()
    
    def increment_likes(self):
        """Increment likes count."""
        self.likes_count += 1
        db.session.commit()
    
    def decrement_likes(self):
        """Decrement likes count."""
        if self.likes_count > 0:
            self.likes_count -= 1
        db.session.commit()
    
    def increment_comments(self):
        """Increment comments count."""
        self.comments_count += 1
        db.session.commit()
    
    def increment_views(self):
        """Increment views count."""
        self.views_count += 1
        db.session.commit()
    
    def increment_discoveries(self):
        """Increment discoveries count."""
        self.discoveries_count += 1
        db.session.commit()
    
    def report(self):
        """Mark memory as reported."""
        self.is_reported = True
        db.session.commit()
    
    def deactivate(self):
        """Deactivate memory."""
        self.is_active = False
        db.session.commit()
    
    def set_expiration(self, days=None, hours=None):
        """Set expiration date."""
        if days:
            self.expiration_date = datetime.utcnow() + timedelta(days=days)
        elif hours:
            self.expiration_date = datetime.utcnow() + timedelta(hours=hours)
        db.session.commit()
    
    def can_view(self, user=None):
        """Check if user can view this memory."""
        # Expired or inactive memories can't be viewed
        if not self.is_active or self.is_expired:
            return False
        
        # Creator can always view
        if user and str(user.user_id) == str(self.creator_id):
            return True
        
        # Check privacy level
        if self.privacy_level == 'public':
            return True
        elif self.privacy_level == 'private':
            return False
        elif self.privacy_level == 'friends':
            # TODO: Implement friend system
            return False
        
        return False
    
    def can_edit(self, user):
        """Check if user can edit this memory."""
        return user and str(user.user_id) == str(self.creator_id)
    
    def to_dict(self, include_location=True, user=None):
        """Convert memory to dictionary."""
        if not self.can_view(user):
            return None
        
        data = {
            'memory_id': str(self.memory_id),
            'creator_id': str(self.creator_id),
            'title': self.title,
            'description': self.description,
            'content_type': self.content_type,
            'content_url': self.content_url,
            'content_text': self.content_text,
            'privacy_level': self.privacy_level,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'likes_count': self.likes_count,
            'comments_count': self.comments_count,
            'views_count': self.views_count,
            'discoveries_count': self.discoveries_count,
            'category_tags': self.category_tags or [],
            'ai_generated_tags': self.ai_generated_tags or [],
            'mood': self.mood,
            'location_name': self.location_name,
            'is_expired': self.is_expired
        }
        
        if include_location:
            data.update({
                'latitude': self.latitude,
                'longitude': self.longitude,
                'coordinates': self.coordinates
            })
        
        if self.content_type in ['audio', 'video']:
            data.update({
                'media_duration': self.media_duration,
                'media_size': self.media_size,
                'media_format': self.media_format,
                'thumbnail_url': self.thumbnail_url
            })
        
        if self.expiration_date:
            data['expiration_date'] = self.expiration_date.isoformat()
        
        # Include creator info if available
        if self.creator:
            data['creator'] = {
                'username': self.creator.username,
                'display_name': self.creator.display_name or self.creator.username,
                'profile_photo_url': self.creator.profile_photo_url
            }
        
        return data
    
    @classmethod
    def find_nearby(cls, latitude, longitude, radius_meters=500, limit=50, user=None):
        """Find memories within radius of given coordinates."""
        point = func.ST_GeomFromText(f'POINT({longitude} {latitude})', 4326)
        
        query = cls.query.filter(
            func.ST_DWithin(cls.location, point, radius_meters),
            cls.is_active == True
        )
        
        # Filter by privacy if user is provided
        if user:
            query = query.filter(
                db.or_(
                    cls.privacy_level == 'public',
                    cls.creator_id == user.user_id
                )
            )
        else:
            query = query.filter(cls.privacy_level == 'public')
        
        # Add distance calculation and order by distance
        query = query.add_columns(
            func.ST_Distance(cls.location, point).label('distance')
        ).order_by('distance').limit(limit)
        
        results = []
        for memory, distance in query.all():
            memory_dict = memory.to_dict(user=user)
            if memory_dict:
                memory_dict['distance'] = distance
                results.append(memory_dict)
        
        return results
    
    @classmethod
    def find_by_creator(cls, creator_id, limit=50):
        """Find memories by creator."""
        return cls.query.filter_by(
            creator_id=creator_id,
            is_active=True
        ).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def search_by_content(cls, search_term, limit=50):
        """Search memories by title, description, or tags."""
        search_pattern = f"%{search_term}%"
        return cls.query.filter(
            db.or_(
                cls.title.ilike(search_pattern),
                cls.description.ilike(search_pattern),
                cls.content_text.ilike(search_pattern),
                cls.category_tags.any(search_term),
                cls.ai_generated_tags.any(search_term)
            ),
            cls.is_active == True,
            cls.privacy_level == 'public'
        ).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_popular_in_area(cls, latitude, longitude, radius_meters=1000, limit=20):
        """Get popular memories in area based on engagement."""
        point = func.ST_GeomFromText(f'POINT({longitude} {latitude})', 4326)
        
        return cls.query.filter(
            func.ST_DWithin(cls.location, point, radius_meters),
            cls.is_active == True,
            cls.privacy_level == 'public'
        ).order_by(
            (cls.likes_count + cls.comments_count + cls.discoveries_count).desc()
        ).limit(limit).all()
    
    @classmethod
    def get_recent_feed(cls, limit=50):
        """Get recent public memories for feed."""
        return cls.query.filter(
            cls.is_active == True,
            cls.privacy_level == 'public'
        ).order_by(cls.created_at.desc()).limit(limit).all()
    
    def __repr__(self):
        return f'<Memory {self.title} by {self.creator_id}>' 