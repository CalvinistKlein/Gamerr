"""
Notification model for tracking system notifications
"""

from datetime import datetime
from extensions import db


class Notification(db.Model):
    """Notification model for system notifications"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), default='info')  # 'info', 'success', 'warning', 'error'
    category = db.Column(db.String(50), default='system')  # 'system', 'download', 'search', 'import'
    
    # Associated entity
    entity_type = db.Column(db.String(50))  # 'game', 'download', 'wanted_game'
    entity_id = db.Column(db.Integer)
    
    # Status
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Notification {self.title}>'
    
    def to_dict(self):
        """Convert notification to dictionary for API responses"""
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'category': self.category,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'read': self.read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'time_ago': self.get_time_ago()
        }
    
    def get_time_ago(self):
        """Get human-readable time ago string"""
        if not self.created_at:
            return 'just now'
        
        delta = datetime.utcnow() - self.created_at
        
        if delta.days > 0:
            return f'{delta.days} day{"s" if delta.days != 1 else ""} ago'
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f'{hours} hour{"s" if hours != 1 else ""} ago'
        elif delta.seconds >= 60:
            minutes = delta.seconds // 60
            return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
        else:
            return 'just now'
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.read = True
        self.read_at = datetime.utcnow()
        db.session.commit()
    
    @classmethod
    def create(cls, title, message, type='info', category='system', entity_type=None, entity_id=None):
        """Create a new notification"""
        notification = cls(
            title=title,
            message=message,
            type=type,
            category=category,
            entity_type=entity_type,
            entity_id=entity_id
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @classmethod
    def get_unread_count(cls):
        """Get count of unread notifications"""
        return cls.query.filter_by(read=False).count()
    
    @classmethod
    def get_recent(cls, limit=10):
        """Get recent notifications"""
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def mark_all_as_read(cls):
        """Mark all notifications as read (single bulk UPDATE, not N commits)"""
        now = datetime.utcnow()
        count = cls.query.filter_by(read=False).update(
            {'read': True, 'read_at': now},
            synchronize_session='fetch'
        )
        db.session.commit()
        return count
    
    @classmethod
    def create_download_completed(cls, game_title, download_id):
        """Create a download completed notification"""
        return cls.create(
            title='Download Completed',
            message=f'{game_title} has finished downloading',
            type='success',
            category='download',
            entity_type='download',
            entity_id=download_id
        )
    
    @classmethod
    def create_search_found(cls, game_title, wanted_id):
        """Create a search found notification"""
        return cls.create(
            title='Game Found',
            message=f'{game_title} was found and added to downloads',
            type='success',
            category='search',
            entity_type='wanted_game',
            entity_id=wanted_id
        )
    
    @classmethod
    def create_import_completed(cls, game_title, game_id):
        """Create an import completed notification"""
        return cls.create(
            title='Import Completed',
            message=f'{game_title} has been imported to your library',
            type='success',
            category='import',
            entity_type='game',
            entity_id=game_id
        )