from app import db
from datetime import datetime
from uuid import uuid4
import enum
from sqlalchemy.dialects.postgresql import UUID
import uuid


class InteractionType(enum.Enum):
    """Enum for interaction types."""
    LIKE = 'like'
    COMMENT = 'comment'
    REPORT = 'report'
    SHARE = 'share'
    VIEW = 'view'


class Interaction(db.Model):
    """Interaction model for user interactions with memories (likes, comments, shares, reports)."""
    
    __tablename__ = 'interactions'
    
    # Primary fields
    interaction_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    memory_id = db.Column(UUID(as_uuid=True), db.ForeignKey('memories.memory_id'), nullable=False)
    
    # Interaction details
    interaction_type = db.Column(db.String(20), nullable=False)  # like, comment, share, report, view
    content = db.Column(db.Text, nullable=True)  # For comments or report reasons
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional metadata
    interaction_metadata = db.Column(db.JSON, nullable=True)  # For storing additional interaction data
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    user = db.relationship('User', back_populates='interactions')
    memory = db.relationship('Memory', back_populates='interactions')
    
    # Index for faster queries on user-memory-type combinations
    __table_args__ = (
        db.Index('idx_user_memory_type', 'user_id', 'memory_id', 'interaction_type'),
    )
    
    def __init__(self, user_id, memory_id, interaction_type, content=None, **kwargs):
        """Initialize interaction."""
        self.user_id = user_id
        self.memory_id = memory_id
        self.interaction_type = interaction_type
        self.content = content
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def deactivate(self):
        """Deactivate interaction (soft delete)."""
        self.is_active = False
        db.session.commit()
    
    def update_content(self, new_content):
        """Update interaction content (for comments)."""
        if self.interaction_type == 'comment':
            self.content = new_content
            self.updated_at = datetime.utcnow()
            db.session.commit()
    
    def add_metadata(self, key, value):
        """Add metadata to interaction."""
        if self.interaction_metadata is None:
            self.interaction_metadata = {}
        self.interaction_metadata[key] = value
        db.session.commit()
    
    def can_edit(self, user):
        """Check if user can edit this interaction."""
        return user and str(user.user_id) == str(self.user_id)
    
    def can_view(self, user=None):
        """Check if user can view this interaction."""
        # All interactions are viewable except private reports
        if self.interaction_type == 'report':
            return user and (
                str(user.user_id) == str(self.user_id) or 
                user.is_admin  # Assuming admin role exists
            )
        return self.is_active
    
    def to_dict(self, include_user_info=True, user=None):
        """Convert interaction to dictionary."""
        if not self.can_view(user):
            return None
        
        data = {
            'interaction_id': str(self.interaction_id),
            'user_id': str(self.user_id),
            'memory_id': str(self.memory_id),
            'interaction_type': self.interaction_type,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.interaction_metadata
        }
        
        # Include user info if available and requested
        if include_user_info and self.user:
            data['user'] = {
                'username': self.user.username,
                'display_name': self.user.display_name or self.user.username,
                'profile_photo_url': self.user.profile_photo_url
            }
        
        return data
    
    @classmethod
    def create_like(cls, user_id, memory_id):
        """Create a like interaction."""
        # Check if like already exists
        existing_like = cls.find_interaction(user_id, memory_id, 'like')
        if existing_like and existing_like.is_active:
            return existing_like
        
        like = cls(user_id=user_id, memory_id=memory_id, interaction_type='like')
        db.session.add(like)
        db.session.commit()
        return like
    
    @classmethod
    def remove_like(cls, user_id, memory_id):
        """Remove a like interaction."""
        like = cls.find_interaction(user_id, memory_id, 'like')
        if like and like.is_active:
            like.deactivate()
            return True
        return False
    
    @classmethod
    def create_comment(cls, user_id, memory_id, content):
        """Create a comment interaction."""
        comment = cls(
            user_id=user_id, 
            memory_id=memory_id, 
            interaction_type='comment',
            content=content
        )
        db.session.add(comment)
        db.session.commit()
        return comment
    
    @classmethod
    def create_share(cls, user_id, memory_id, metadata=None):
        """Create a share interaction."""
        share = cls(
            user_id=user_id,
            memory_id=memory_id,
            interaction_type='share',
            interaction_metadata=metadata
        )
        db.session.add(share)
        db.session.commit()
        return share
    
    @classmethod
    def create_report(cls, user_id, memory_id, reason, content=None):
        """Create a report interaction."""
        report = cls(
            user_id=user_id,
            memory_id=memory_id,
            interaction_type='report',
            content=content,
            interaction_metadata={'reason': reason}
        )
        db.session.add(report)
        db.session.commit()
        return report
    
    @classmethod
    def create_view(cls, user_id, memory_id, metadata=None):
        """Create a view interaction."""
        # Check if view already exists today (to avoid spam)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        existing_view = cls.query.filter(
            cls.user_id == user_id,
            cls.memory_id == memory_id,
            cls.interaction_type == 'view',
            cls.created_at >= today_start,
            cls.is_active == True
        ).first()
        
        if existing_view:
            return existing_view
        
        view = cls(
            user_id=user_id,
            memory_id=memory_id,
            interaction_type='view',
            interaction_metadata=metadata
        )
        db.session.add(view)
        db.session.commit()
        return view
    
    @classmethod
    def find_interaction(cls, user_id, memory_id, interaction_type):
        """Find a specific interaction."""
        return cls.query.filter_by(
            user_id=user_id,
            memory_id=memory_id,
            interaction_type=interaction_type,
            is_active=True
        ).first()
    
    @classmethod
    def get_memory_interactions(cls, memory_id, interaction_type=None, limit=50):
        """Get interactions for a specific memory."""
        query = cls.query.filter_by(memory_id=memory_id, is_active=True)
        
        if interaction_type:
            query = query.filter_by(interaction_type=interaction_type)
        
        return query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_user_interactions(cls, user_id, interaction_type=None, limit=50):
        """Get interactions by a specific user."""
        query = cls.query.filter_by(user_id=user_id, is_active=True)
        
        if interaction_type:
            query = query.filter_by(interaction_type=interaction_type)
        
        return query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_likes_for_memory(cls, memory_id):
        """Get all likes for a memory."""
        return cls.query.filter_by(
            memory_id=memory_id,
            interaction_type='like',
            is_active=True
        ).all()
    
    @classmethod
    def get_comments_for_memory(cls, memory_id, limit=100):
        """Get comments for a memory."""
        return cls.query.filter_by(
            memory_id=memory_id,
            interaction_type='comment',
            is_active=True
        ).order_by(cls.created_at.asc()).limit(limit).all()
    
    @classmethod
    def user_has_liked(cls, user_id, memory_id):
        """Check if user has liked a memory."""
        like = cls.find_interaction(user_id, memory_id, 'like')
        return like is not None and like.is_active
    
    @classmethod
    def get_interaction_counts(cls, memory_id):
        """Get interaction counts for a memory."""
        counts = {}
        
        # Get counts for each interaction type
        for interaction_type in ['like', 'comment', 'share', 'view']:
            count = cls.query.filter_by(
                memory_id=memory_id,
                interaction_type=interaction_type,
                is_active=True
            ).count()
            counts[f'{interaction_type}s_count'] = count
        
        return counts
    
    @classmethod
    def get_popular_memories(cls, days=7, limit=20):
        """Get popular memories based on recent interactions."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Count interactions per memory in the last N days
        popular_memories = db.session.query(
            cls.memory_id,
            func.count(cls.interaction_id).label('interaction_count')
        ).filter(
            cls.created_at >= cutoff_date,
            cls.is_active == True,
            cls.interaction_type.in_(['like', 'comment', 'share'])
        ).group_by(cls.memory_id).order_by(
            func.count(cls.interaction_id).desc()
        ).limit(limit).all()
        
        return [memory_id for memory_id, _ in popular_memories]
    
    def __repr__(self):
        return f'<Interaction {self.interaction_type} by {self.user_id} on {self.memory_id}>' 