from app import db
from datetime import datetime
from uuid import uuid4
from werkzeug.security import generate_password_hash, check_password_hash
import json
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text
import uuid


class User(db.Model):
    """User model for authentication and profile management."""
    
    __tablename__ = 'users'
    
    # Primary fields
    user_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile information
    profile_photo_url = db.Column(db.String(255), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    display_name = db.Column(db.String(100), nullable=True)
    
    # Account status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Privacy settings
    privacy_settings = db.Column(db.JSON, default=lambda: {
        'profile_visibility': 'public',  # public, friends, private
        'location_sharing': True,
        'memory_discovery': True,
        'show_activity_status': True,
        'allow_friend_requests': True
    })
    
    # Location settings
    location_sharing_enabled = db.Column(db.Boolean, default=True, nullable=False)
    default_memory_privacy = db.Column(db.String(20), default='public', nullable=False)
    
    # Statistics (computed fields)
    memories_count = db.Column(db.Integer, default=0, nullable=False)
    discoveries_count = db.Column(db.Integer, default=0, nullable=False)
    likes_given_count = db.Column(db.Integer, default=0, nullable=False)
    likes_received_count = db.Column(db.Integer, default=0, nullable=False)
    
    # Relationships
    created_memories = db.relationship('Memory', back_populates='creator', lazy='dynamic')
    interactions = db.relationship('Interaction', back_populates='user', lazy='dynamic')
    
    def __init__(self, username, email, password, **kwargs):
        """Initialize user with required fields."""
        self.username = username
        self.email = email.lower()
        self.set_password(password)
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash."""
        return check_password_hash(self.password_hash, password)
    
    def update_last_active(self):
        """Update last active timestamp."""
        self.last_active = datetime.utcnow()
        db.session.commit()
    
    def deactivate(self):
        """Deactivate user account."""
        self.is_active = False
        db.session.commit()
    
    def reactivate(self):
        """Reactivate user account."""
        self.is_active = True
        self.last_active = datetime.utcnow()
        db.session.commit()
    
    def update_privacy_settings(self, settings):
        """Update privacy settings."""
        if self.privacy_settings is None:
            self.privacy_settings = {}
        self.privacy_settings.update(settings)
        db.session.commit()
    
    def get_privacy_setting(self, key):
        """Get specific privacy setting."""
        if self.privacy_settings is None:
            return None
        return self.privacy_settings.get(key)
    
    def can_view_profile(self, viewer_user=None):
        """Check if viewer can see this user's profile."""
        profile_visibility = self.get_privacy_setting('profile_visibility')
        
        if profile_visibility == 'public':
            return True
        elif profile_visibility == 'private':
            return viewer_user and viewer_user.user_id == self.user_id
        elif profile_visibility == 'friends':
            # TODO: Implement friend system
            return viewer_user and viewer_user.user_id == self.user_id
        
        return False
    
    def can_discover_memories(self):
        """Check if user allows memory discovery."""
        return self.get_privacy_setting('memory_discovery') and self.location_sharing_enabled
    
    def increment_memories_count(self):
        """Increment memories count."""
        self.memories_count += 1
        db.session.commit()
    
    def increment_discoveries_count(self):
        """Increment discoveries count."""
        self.discoveries_count += 1
        db.session.commit()
    
    def increment_likes_given_count(self):
        """Increment likes given count."""
        self.likes_given_count += 1
        db.session.commit()
    
    def increment_likes_received_count(self):
        """Increment likes received count."""
        self.likes_received_count += 1
        db.session.commit()
    
    def get_stats(self):
        """Get user statistics."""
        return {
            'memories_created': self.memories_count,
            'memories_discovered': self.discoveries_count,
            'likes_given': self.likes_given_count,
            'likes_received': self.likes_received_count,
            'member_since': self.created_at.isoformat(),
            'last_active': self.last_active.isoformat() if self.last_active else None
        }
    
    def to_dict(self, include_private=False, viewer_user=None):
        """Convert user to dictionary."""
        can_view_full = include_private or self.can_view_profile(viewer_user)
        
        basic_info = {
            'user_id': str(self.user_id),
            'username': self.username,
            'display_name': self.display_name or self.username,
            'profile_photo_url': self.profile_photo_url,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active
        }
        
        if can_view_full:
            basic_info.update({
                'email': self.email,
                'bio': self.bio,
                'last_active': self.last_active.isoformat() if self.last_active else None,
                'stats': self.get_stats()
            })
        
        if include_private:
            basic_info.update({
                'privacy_settings': self.privacy_settings,
                'location_sharing_enabled': self.location_sharing_enabled,
                'default_memory_privacy': self.default_memory_privacy,
                'is_verified': self.is_verified
            })
        
        return basic_info
    
    @classmethod
    def find_by_username(cls, username):
        """Find user by username."""
        return cls.query.filter_by(username=username, is_active=True).first()
    
    @classmethod
    def find_by_email(cls, email):
        """Find user by email."""
        return cls.query.filter_by(email=email.lower(), is_active=True).first()
    
    @classmethod
    def search_users(cls, query, limit=20):
        """Search users by username or display name."""
        search_term = f"%{query}%"
        return cls.query.filter(
            db.or_(
                cls.username.ilike(search_term),
                cls.display_name.ilike(search_term)
            ),
            cls.is_active == True
        ).limit(limit).all()
    
    def __repr__(self):
        return f'<User {self.username}>' 