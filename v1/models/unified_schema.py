"""
Unified Database Schema for ROM Management
Combines the best of simple and complex schemas with proper relationships
"""

from datetime import datetime
from typing import List, Optional
from extensions import db
from sqlalchemy import ForeignKey, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.orm import relationship, validates
import json


# Association tables for many-to-many relationships
game_genre_association = db.Table('game_genre_association',
    db.Column('game_id', db.Integer, ForeignKey('games.id', ondelete='CASCADE'), primary_key=True),
    db.Column('genre_id', db.Integer, ForeignKey('genres.id', ondelete='CASCADE'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

game_platform_association = db.Table('game_platform_association',
    db.Column('game_id', db.Integer, ForeignKey('games.id', ondelete='CASCADE'), primary_key=True),
    db.Column('platform_id', db.Integer, ForeignKey('platforms.id', ondelete='CASCADE'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

game_developer_association = db.Table('game_developer_association',
    db.Column('game_id', db.Integer, ForeignKey('games.id', ondelete='CASCADE'), primary_key=True),
    db.Column('company_id', db.Integer, ForeignKey('companies.id', ondelete='CASCADE'), primary_key=True),
    db.Column('role', db.String(20), default='developer'),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

game_publisher_association = db.Table('game_publisher_association',
    db.Column('game_id', db.Integer, ForeignKey('games.id', ondelete='CASCADE'), primary_key=True),
    db.Column('company_id', db.Integer, ForeignKey('companies.id', ondelete='CASCADE'), primary_key=True),
    db.Column('role', db.String(20), default='publisher'),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)


class Game(db.Model):
    """
    Core game entity representing a video game title.
    A game can have multiple ROM files (different regions/versions).
    """
    __tablename__ = 'games'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Core identification
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, index=True)
    description = db.Column(db.Text)
    
    # Release information
    first_release_date = db.Column(db.Date)
    release_year = db.Column(db.Integer)
    
    # Ratings
    rating = db.Column(db.Float, CheckConstraint('rating >= 0 AND rating <= 100'))
    rating_count = db.Column(db.Integer, default=0)
    aggregated_rating = db.Column(db.Float, CheckConstraint('aggregated_rating >= 0 AND aggregated_rating <= 100'))
    aggregated_rating_count = db.Column(db.Integer, default=0)
    
    # Game details
    storyline = db.Column(db.Text)
    summary = db.Column(db.Text)
    players_min = db.Column(db.Integer, default=1)
    players_max = db.Column(db.Integer, default=1)
    time_to_beat_main = db.Column(db.Integer)  # in minutes
    time_to_beat_completionist = db.Column(db.Integer)  # in minutes
    
    # External references
    igdb_id = db.Column(db.Integer, unique=True, index=True)
    rawg_id = db.Column(db.Integer, unique=True, index=True)
    
    # Media
    cover_url = db.Column(db.String(500))
    screenshot_urls = db.Column(db.Text)  # JSON array
    artwork_urls = db.Column(db.Text)  # JSON array
    
    # Status tracking
    status = db.Column(db.String(20), default='active')  # active, archived, deleted
    metadata_completeness = db.Column(db.Float, default=0.0)  # 0.0 to 1.0
    last_metadata_update = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    rom_files = relationship('ROMFile', back_populates='game', cascade='all, delete-orphan')
    platforms = relationship('Platform', secondary=game_platform_association, back_populates='games')
    genres = relationship('Genre', secondary=game_genre_association, back_populates='games')
    developers = relationship('Company', secondary=game_developer_association, 
                            primaryjoin="Game.id==game_developer_association.c.game_id",
                            secondaryjoin="Company.id==game_developer_association.c.company_id",
                            backref='developed_games')
    publishers = relationship('Company', secondary=game_publisher_association,
                             primaryjoin="Game.id==game_publisher_association.c.game_id",
                             secondaryjoin="Company.id==game_publisher_association.c.company_id",
                             backref='published_games')
    releases = relationship('Release', back_populates='game', cascade='all, delete-orphan')
    downloads = relationship('Download', backref='game_ref', lazy=True)
    
    # Indexes
    __table_args__ = (
        Index('ix_games_title_platform', 'title'),
        Index('ix_games_release_year', 'release_year'),
        Index('ix_games_rating', 'rating'),
        Index('ix_games_metadata_completeness', 'metadata_completeness'),
    )
    
    @validates('rating', 'aggregated_rating')
    def validate_rating(self, key, value):
        """Validate rating values are within bounds"""
        if value is not None and (value < 0 or value > 100):
            raise ValueError(f"{key} must be between 0 and 100")
        return value
    
    @validates('metadata_completeness')
    def validate_completeness(self, key, value):
        """Validate completeness is between 0 and 1"""
        if value is not None and (value < 0 or value > 1):
            raise ValueError(f"{key} must be between 0 and 1")
        return value

    # Compatibility properties for old Game model API
    @property
    def platform(self):
        return self.platforms[0].name if self.platforms else "Unknown"

    @platform.setter
    def platform(self, value):
        from models.unified_schema import Platform, create_slug
        # Set a dummy platform. In reality this requires DB queries inside the setter, which isn't ideal but works for now.
        pass

    @property
    def region(self):
        return self.rom_files[0].region if self.rom_files else None

    @region.setter
    def region(self, value):
        pass

    @property
    def file_path(self):
        return self.rom_files[0].file_path if self.rom_files else None

    @file_path.setter
    def file_path(self, value):
        if self.rom_files:
            self.rom_files[0].file_path = value

    @property
    def file_size(self):
        return self.rom_files[0].file_size if self.rom_files else 0

    @file_size.setter
    def file_size(self, value):
        if self.rom_files:
            self.rom_files[0].file_size = value

    @property
    def added_date(self):
        return self.created_at

    @property
    def last_played(self):
        return None  # We can implement this later
        
    @property
    def play_count(self):
        return 0
    
    @classmethod
    def get_library_count(cls):
        """Get count of games in library"""
        return cls.query.filter_by(status='library').count()

    def to_dict(self, include_relationships=False):
        """Convert game to dictionary for API responses"""
        result = {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'description': self.description,
            'first_release_date': self.first_release_date.isoformat() if self.first_release_date else None,
            'release_year': self.release_year,
            'rating': self.rating,
            'rating_count': self.rating_count,
            'aggregated_rating': self.aggregated_rating,
            'aggregated_rating_count': self.aggregated_rating_count,
            'players_min': self.players_min,
            'players_max': self.players_max,
            'cover_url': self.cover_url,
            'status': self.status,
            'metadata_completeness': self.metadata_completeness,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # Backwards compatibility output
            'platform': self.platform,
            'region': self.region,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'added_date': self.created_at.isoformat() if self.created_at else None,
            'last_played': None,
            'play_count': 0
        }
        
        if include_relationships:
            result['platforms'] = [p.to_dict() for p in self.platforms]
            result['genres'] = [g.to_dict() for g in self.genres]
            result['rom_files'] = [r.to_dict() for r in self.rom_files]
            result['developers'] = [c.to_dict() for c in self.developers]
            result['publishers'] = [c.to_dict() for c in self.publishers]
        
        return result
    
    def __repr__(self):
        return f'<Game {self.title}>'


class ROMFile(db.Model):
    """
    ROM file entity representing a specific file on disk.
    Multiple ROM files can belong to one game (different regions/versions).
    """
    __tablename__ = 'rom_files'
    
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, ForeignKey('games.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # File information
    file_path = db.Column(db.String(500), nullable=False)
    file_name = db.Column(db.String(200), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    file_extension = db.Column(db.String(10), nullable=False)
    
    # Hashes for verification
    crc32 = db.Column(db.String(8), index=True)
    md5 = db.Column(db.String(32), index=True)
    sha1 = db.Column(db.String(40), index=True)
    
    # ROM-specific metadata
    region = db.Column(db.String(50))
    version = db.Column(db.String(50))
    language = db.Column(db.String(50))
    
    # Detection information
    detected_platform = db.Column(db.String(50))
    detection_confidence = db.Column(db.Float, default=0.0)
    detection_method = db.Column(db.String(50))
    
    # Verification status
    is_verified = db.Column(db.Boolean, default=False)
    verification_source = db.Column(db.String(50))  # 'no-intro', 'redump', 'libretro'
    verification_date = db.Column(db.DateTime)
    
    # Import tracking
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_scanned = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    game = relationship('Game', back_populates='rom_files')
    
    # Indexes
    __table_args__ = (
        UniqueConstraint('crc32', 'md5', 'sha1', name='uq_romfile_hashes'),
        Index('ix_romfiles_hashes_composite', 'crc32', 'md5', 'sha1'),
        Index('ix_romfiles_region', 'region'),
        Index('ix_romfiles_is_verified', 'is_verified'),
    )
    
    @validates('detection_confidence')
    def validate_confidence(self, key, value):
        """Validate confidence is between 0 and 1"""
        if value is not None and (value < 0 or value > 1):
            raise ValueError(f"{key} must be between 0 and 1")
        return value
    
    def to_dict(self):
        """Convert ROM file to dictionary"""
        return {
            'id': self.id,
            'game_id': self.game_id,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_extension': self.file_extension,
            'crc32': self.crc32,
            'md5': self.md5,
            'sha1': self.sha1,
            'region': self.region,
            'version': self.version,
            'language': self.language,
            'detected_platform': self.detected_platform,
            'detection_confidence': self.detection_confidence,
            'is_verified': self.is_verified,
            'verification_source': self.verification_source,
            'imported_at': self.imported_at.isoformat() if self.imported_at else None,
        }
    
    def __repr__(self):
        return f'<ROMFile {self.file_name}>'


class Platform(db.Model):
    """
    Gaming platform/console entity.
    """
    __tablename__ = 'platforms'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Core identification
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(100), nullable=False, unique=True, index=True)
    abbreviation = db.Column(db.String(20))
    
    # Platform details
    manufacturer = db.Column(db.String(100))
    generation = db.Column(db.Integer)
    release_date = db.Column(db.Date)
    discontinued_date = db.Column(db.Date)
    units_sold = db.Column(db.BigInteger)
    
    # Technical details
    cpu = db.Column(db.String(200))
    memory = db.Column(db.String(100))
    storage = db.Column(db.String(100))
    
    # Media
    logo_url = db.Column(db.String(500))
    photo_url = db.Column(db.String(500))
    
    # External references
    igdb_id = db.Column(db.Integer, unique=True, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    games = relationship('Game', secondary=game_platform_association, back_populates='platforms')
    
    def to_dict(self):
        """Convert platform to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'abbreviation': self.abbreviation,
            'manufacturer': self.manufacturer,
            'generation': self.generation,
            'release_date': self.release_date.isoformat() if self.release_date else None,
            'logo_url': self.logo_url,
            'igdb_id': self.igdb_id,
        }
    
    def __repr__(self):
        return f'<Platform {self.name}>'


class Genre(db.Model):
    """
    Game genre classification.
    """
    __tablename__ = 'genres'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Core identification
    name = db.Column(db.String(50), nullable=False, unique=True)
    slug = db.Column(db.String(50), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)
    
    # External references
    igdb_id = db.Column(db.Integer, unique=True, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    games = relationship('Game', secondary=game_genre_association, back_populates='genres')
    
    def to_dict(self):
        """Convert genre to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'igdb_id': self.igdb_id,
        }
    
    def __repr__(self):
        return f'<Genre {self.name}>'


class Company(db.Model):
    """
    Company entity (developer, publisher).
    """
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Core identification
    name = db.Column(db.String(200), nullable=False, unique=True)
    slug = db.Column(db.String(200), nullable=False, unique=True, index=True)
    
    # Company details
    description = db.Column(db.Text)
    country = db.Column(db.String(50))
    country_code = db.Column(db.String(2))
    founded_date = db.Column(db.Date)
    
    # Media
    logo_url = db.Column(db.String(500))
    
    # External references
    igdb_id = db.Column(db.Integer, unique=True, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert company to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'country': self.country,
            'logo_url': self.logo_url,
            'igdb_id': self.igdb_id,
        }
    
    def __repr__(self):
        return f'<Company {self.name}>'


class Release(db.Model):
    """
    Release information for a game in a specific region.
    """
    __tablename__ = 'releases'
    
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, ForeignKey('games.id', ondelete='CASCADE'), nullable=False, index=True)
    platform_id = db.Column(db.Integer, ForeignKey('platforms.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Release details
    region = db.Column(db.String(50), nullable=False)
    release_date = db.Column(db.Date)
    certification = db.Column(db.String(50))  # ESRB, PEGI, etc.
    
    # External references
    igdb_release_id = db.Column(db.Integer, unique=True, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    game = relationship('Game', back_populates='releases')
    platform = relationship('Platform')
    
    # Indexes
    __table_args__ = (
        UniqueConstraint('game_id', 'platform_id', 'region', name='uq_release_game_platform_region'),
        Index('ix_releases_region', 'region'),
        Index('ix_releases_release_date', 'release_date'),
    )
    
    def to_dict(self):
        """Convert release to dictionary"""
        return {
            'id': self.id,
            'game_id': self.game_id,
            'platform_id': self.platform_id,
            'region': self.region,
            'release_date': self.release_date.isoformat() if self.release_date else None,
            'certification': self.certification,
        }
    
    def __repr__(self):
        return f'<Release {self.game_id} - {self.platform_id} - {self.region}>'

class ImageCache(db.Model):
    """
    Cache for downloaded images to avoid repeated downloads.
    """
    __tablename__ = 'image_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Image identification
    url = db.Column(db.String(500), nullable=False, unique=True, index=True)
    image_type = db.Column(db.String(20), nullable=False)  # 'cover', 'screenshot', 'artwork', 'logo'
    entity_type = db.Column(db.String(20), nullable=False)  # 'game', 'platform', 'company'
    entity_id = db.Column(db.Integer, nullable=False, index=True)
    
    # Image data
    local_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    format = db.Column(db.String(10))  # 'jpg', 'png', 'webp'
    
    # Download tracking
    downloaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    access_count = db.Column(db.Integer, default=0)
    
    # Status
    is_valid = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    
    # Indexes
    __table_args__ = (
        Index('ix_image_cache_entity', 'entity_type', 'entity_id'),
        Index('ix_image_cache_type', 'image_type'),
        Index('ix_image_cache_last_accessed', 'last_accessed'),
    )
    
    def to_dict(self):
        """Convert image cache to dictionary"""
        return {
            'id': self.id,
            'url': self.url,
            'image_type': self.image_type,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'local_path': self.local_path,
            'file_size': self.file_size,
            'width': self.width,
            'height': self.height,
            'format': self.format,
            'downloaded_at': self.downloaded_at.isoformat() if self.downloaded_at else None,
            'access_count': self.access_count,
            'is_valid': self.is_valid,
        }
    
    def __repr__(self):
        return f'<ImageCache {self.image_type} for {self.entity_type} {self.entity_id}>'


class ScrapingLog(db.Model):
    """
    Audit log for scraping operations.
    """
    __tablename__ = 'scraping_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Operation details
    operation_type = db.Column(db.String(50), nullable=False)  # 'scan', 'enrich', 'verify', 'download'
    entity_type = db.Column(db.String(20))  # 'game', 'rom_file', 'image'
    entity_id = db.Column(db.Integer)
    
    # Source information
    source = db.Column(db.String(50))  # 'igdb', 'libretro', 'no-intro', 'filesystem'
    source_id = db.Column(db.String(100))
    
    # Operation results
    status = db.Column(db.String(20), nullable=False)  # 'success', 'failure', 'partial'
    items_processed = db.Column(db.Integer, default=0)
    items_succeeded = db.Column(db.Integer, default=0)
    items_failed = db.Column(db.Integer, default=0)
    
    # Performance metrics
    duration_seconds = db.Column(db.Float)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    
    # Error tracking
    error_message = db.Column(db.Text)
    stack_trace = db.Column(db.Text)
    
    # Additional data
    log_metadata = db.Column(db.Text)  # JSON data
    
    # Indexes
    __table_args__ = (
        Index('ix_scraping_logs_operation', 'operation_type'),
        Index('ix_scraping_logs_status', 'status'),
        Index('ix_scraping_logs_start_time', 'start_time'),
        Index('ix_scraping_logs_entity', 'entity_type', 'entity_id'),
    )
    
    def to_dict(self):
        """Convert scraping log to dictionary"""
        return {
            'id': self.id,
            'operation_type': self.operation_type,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'source': self.source,
            'source_id': self.source_id,
            'status': self.status,
            'items_processed': self.items_processed,
            'items_succeeded': self.items_succeeded,
            'items_failed': self.items_failed,
            'duration_seconds': self.duration_seconds,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'error_message': self.error_message,
            'log_metadata': self.log_metadata,
        }
    
    def __repr__(self):
        return f'<ScrapingLog {self.operation_type} - {self.status}>'


# Helper functions for the unified schema
def calculate_metadata_completeness(game: Game) -> float:
    """
    Calculate metadata completeness score for a game (0.0 to 1.0).
    
    Weights:
    - Title: 0.1
    - Description: 0.15
    - Release year: 0.1
    - Cover art: 0.1
    - Genres: 0.1
    - Platforms: 0.1
    - Developers: 0.1
    - Publishers: 0.1
    - Rating: 0.05
    - ROM files: 0.1
    """
    weights = {
        'title': 0.1,
        'description': 0.15,
        'release_year': 0.1,
        'cover_url': 0.1,
        'genres': 0.1,
        'platforms': 0.1,
        'developers': 0.1,
        'publishers': 0.1,
        'rating': 0.05,
        'rom_files': 0.1,
    }
    
    score = 0.0
    
    # Check each field
    if game.title:
        score += weights['title']
    
    if game.description:
        score += weights['description']
    
    if game.release_year:
        score += weights['release_year']
    
    if game.cover_url:
        score += weights['cover_url']
    
    if game.genres and len(game.genres) > 0:
        score += weights['genres']
    
    if game.platforms and len(game.platforms) > 0:
        score += weights['platforms']
    
    if game.developers and len(game.developers) > 0:
        score += weights['developers']
    
    if game.publishers and len(game.publishers) > 0:
        score += weights['publishers']
    
    if game.rating is not None:
        score += weights['rating']
    
    if game.rom_files and len(game.rom_files) > 0:
        score += weights['rom_files']
    
    return round(score, 2)


def update_game_metadata_completeness(game: Game):
    """Update the metadata completeness score for a game."""
    game.metadata_completeness = calculate_metadata_completeness(game)
    game.last_metadata_update = datetime.utcnow()


def find_game_by_hash(crc32: str = None, md5: str = None, sha1: str = None) -> Optional[Game]:
    """
    Find a game by one or more hash values.
    
    Args:
        crc32: CRC32 hash (optional)
        md5: MD5 hash (optional)
        sha1: SHA1 hash (optional)
        
    Returns:
        Game object if found, None otherwise
    """
    if not any([crc32, md5, sha1]):
        return None
    
    query = ROMFile.query
    
    if crc32:
        query = query.filter_by(crc32=crc32)
    if md5:
        query = query.filter_by(md5=md5)
    if sha1:
        query = query.filter_by(sha1=sha1)
    
    rom_file = query.first()
    if rom_file:
        return rom_file.game
    
    return None


def create_game_from_rom_file(rom_file_data: dict) -> Game:
    """
    Create a new game from ROM file data.
    
    Args:
        rom_file_data: Dictionary with ROM file information
        
    Returns:
        Newly created Game object
    """
    # Extract title from filename if not provided
    title = rom_file_data.get('title')
    if not title and 'file_name' in rom_file_data:
        # Simple title extraction (remove extension and common patterns)
        import re
        filename = rom_file_data['file_name']
        title = re.sub(r'\.[^.]*$', '', filename)  # Remove extension
        title = re.sub(r'\([^)]*\)', '', title)  # Remove parentheses content
        title = re.sub(r'\[[^\]]*\]', '', title)  # Remove bracket content
        title = re.sub(r'\s+', ' ', title).strip()  # Clean whitespace
    
    # Create game
    game = Game(
        title=title or 'Unknown Game',
        slug=create_slug(title) if title else 'unknown-game',
        status='active'
    )
    
    db.session.add(game)
    
    # Create ROM file
    rom_file = ROMFile(
        game=game,
        file_path=rom_file_data.get('file_path', ''),
        file_name=rom_file_data.get('file_name', ''),
        file_size=rom_file_data.get('file_size', 0),
        file_extension=rom_file_data.get('file_extension', ''),
        crc32=rom_file_data.get('crc32'),
        md5=rom_file_data.get('md5'),
        sha1=rom_file_data.get('sha1'),
        region=rom_file_data.get('region'),
        version=rom_file_data.get('version'),
        language=rom_file_data.get('language'),
        detected_platform=rom_file_data.get('detected_platform'),
        detection_confidence=rom_file_data.get('detection_confidence', 0.0),
        detection_method=rom_file_data.get('detection_method', 'unknown'),
    )
    
    db.session.add(rom_file)
    db.session.commit()
    
    # Update completeness score
    update_game_metadata_completeness(game)
    db.session.commit()
    
    return game


def create_slug(text: str) -> str:
    """
    Create a URL-friendly slug from text.
    
    Args:
        text: Input text
        
    Returns:
        URL-friendly slug
    """
    import re
    import unicodedata
    
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)
    
    # Convert to lowercase and remove special characters
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    text = text.strip('-')
    
    return text


# Initialize default data
def initialize_default_data():
    """Initialize default platforms and genres."""
    from sqlalchemy import exists
    
    # Default platforms
    default_platforms = [
        {'name': 'NES', 'slug': 'nes', 'manufacturer': 'Nintendo', 'generation': 3},
        {'name': 'SNES', 'slug': 'snes', 'manufacturer': 'Nintendo', 'generation': 4},
        {'name': 'Nintendo 64', 'slug': 'n64', 'manufacturer': 'Nintendo', 'generation': 5},
        {'name': 'GameCube', 'slug': 'gamecube', 'manufacturer': 'Nintendo', 'generation': 6},
        {'name': 'Wii', 'slug': 'wii', 'manufacturer': 'Nintendo', 'generation': 7},
        {'name': 'Game Boy', 'slug': 'game-boy', 'manufacturer': 'Nintendo', 'generation': 4},
        {'name': 'Game Boy Color', 'slug': 'game-boy-color', 'manufacturer': 'Nintendo', 'generation': 5},
        {'name': 'Game Boy Advance', 'slug': 'game-boy-advance', 'manufacturer': 'Nintendo', 'generation': 6},
        {'name': 'Genesis', 'slug': 'genesis', 'manufacturer': 'Sega', 'generation': 4},
        {'name': 'PlayStation', 'slug': 'playstation', 'manufacturer': 'Sony', 'generation': 5},
        {'name': 'PlayStation 2', 'slug': 'playstation-2', 'manufacturer': 'Sony', 'generation': 6},
        {'name': 'Xbox', 'slug': 'xbox', 'manufacturer': 'Microsoft', 'generation': 6},
        {'name': 'Arcade', 'slug': 'arcade', 'manufacturer': 'Various', 'generation': 1},
    ]
    
    for platform_data in default_platforms:
        if not db.session.query(exists().where(Platform.slug == platform_data['slug'])).scalar():
            platform = Platform(**platform_data)
            db.session.add(platform)
    
    # Default genres
    default_genres = [
        {'name': 'Action', 'slug': 'action', 'description': 'Fast-paced games focusing on physical challenges'},
        {'name': 'Adventure', 'slug': 'adventure', 'description': 'Story-driven games with exploration and puzzle-solving'},
        {'name': 'Role-Playing', 'slug': 'role-playing', 'description': 'Games where players assume roles of characters'},
        {'name': 'Strategy', 'slug': 'strategy', 'description': 'Games requiring careful planning and resource management'},
        {'name': 'Simulation', 'slug': 'simulation', 'description': 'Games that simulate real-world activities'},
        {'name': 'Sports', 'slug': 'sports', 'description': 'Games based on real-world sports'},
        {'name': 'Racing', 'slug': 'racing', 'description': 'Games focused on vehicle racing'},
        {'name': 'Fighting', 'slug': 'fighting', 'description': 'Games focused on combat between characters'},
        {'name': 'Shooter', 'slug': 'shooter', 'description': 'Games focused on shooting enemies'},
        {'name': 'Platformer', 'slug': 'platformer', 'description': 'Games focused on jumping between platforms'},
        {'name': 'Puzzle', 'slug': 'puzzle', 'description': 'Games focused on solving puzzles'},
    ]
    
    for genre_data in default_genres:
        if not db.session.query(exists().where(Genre.slug == genre_data['slug'])).scalar():
            genre = Genre(**genre_data)
            db.session.add(genre)
    
    db.session.commit()
    print("Default platforms and genres initialized")
    

class WantedGame(db.Model):
    """Wanted game model for tracking games to be searched and downloaded"""
    __tablename__ = 'wanted_games'
    
    id = db.Column(db.Integer, primary_key=True)
    game_title = db.Column(db.String(200), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    region_preference = db.Column(db.String(50))
    quality_preference = db.Column(db.String(50))
    added_date = db.Column(db.DateTime, default=datetime.utcnow)
    priority = db.Column(db.Integer, default=1)  # 1-5, higher is more important
    status = db.Column(db.String(20), default='pending')
    
    # Search tracking
    last_searched = db.Column(db.DateTime)
    search_count = db.Column(db.Integer, default=0)
    
    # Found result
    found_torrent_hash = db.Column(db.String(100))
    found_torrent_name = db.Column(db.String(500))
    found_size = db.Column(db.BigInteger)
    found_seeders = db.Column(db.Integer)
    
    # The download this wanted game is tied to
    download_id = db.Column(db.Integer, db.ForeignKey('downloads.id'), nullable=True)
    completed_date = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<WantedGame {self.game_title} ({self.platform}) - {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'game_title': self.game_title,
            'platform': self.platform,
            'region_preference': self.region_preference,
            'quality_preference': self.quality_preference,
            'added_date': self.added_date.isoformat() if self.added_date else None,
            'priority': self.priority,
            'status': self.status,
            'last_searched': self.last_searched.isoformat() if self.last_searched else None,
            'search_count': self.search_count
        }

    @classmethod
    def get_active_count(cls):
        """Get count of wanted games that are not completed or failed"""
        return cls.query.filter(~cls.status.in_(['completed', 'failed'])).count()

class Download(db.Model):
    """Download model for tracking torrent downloads"""
    __tablename__ = 'downloads'
    
    id = db.Column(db.Integer, primary_key=True)
    # Important connection to unified games table
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=True)
    torrent_hash = db.Column(db.String(100))
    torrent_name = db.Column(db.String(500))
    download_path = db.Column(db.String(500))
    size_bytes = db.Column(db.BigInteger)
    progress = db.Column(db.Float, default=0.0)  # 0.0 to 1.0
    status = db.Column(db.String(20), default='queued')
    added_date = db.Column(db.DateTime, default=datetime.utcnow)
    completed_date = db.Column(db.DateTime)
    
    # Download tracking
    download_speed = db.Column(db.BigInteger)  # bytes per second
    eta = db.Column(db.Integer)  # seconds
    seeds = db.Column(db.Integer)
    peers = db.Column(db.Integer)
    
    # Relationship to wanted games
    wanted_games = relationship('WantedGame', backref='download', lazy=True)
    
    def __repr__(self):
        return f'<Download {self.torrent_name} - {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'game_id': self.game_id,
            'torrent_hash': self.torrent_hash,
            'torrent_name': self.torrent_name,
            'download_path': self.download_path,
            'size_bytes': self.size_bytes,
            'progress': self.progress,
            'status': self.status,
            'added_date': self.added_date.isoformat() if self.added_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'download_speed': self.download_speed,
            'eta': self.eta,
            'seeds': self.seeds,
            'peers': self.peers
        }
    
    @classmethod
    def get_active(cls):
        return cls.query.filter(cls.status.in_(['queued', 'downloading'])).all()

class GameCatalog(db.Model):
    """Game catalog model representing games available for download"""
    __tablename__ = 'game_catalog'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    region = db.Column(db.String(50))
    release_year = db.Column(db.Integer)
    publisher = db.Column(db.String(100))
    developer = db.Column(db.String(100))
    genre = db.Column(db.String(100))
    
    # Game details
    description = db.Column(db.Text)
    players = db.Column(db.Integer)
    rating = db.Column(db.Float)  # User rating 0-5
    cover_image_url = db.Column(db.String(500))
    screenshot_urls = db.Column(db.Text)  # JSON array of URLs
    
    # Source information
    source = db.Column(db.String(50))  # 'vimm', 'retropie', 'igdb', etc.
    source_id = db.Column(db.String(100))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Download metrics
    download_count = db.Column(db.Integer, default=0)
    popularity_score = db.Column(db.Float, default=0.0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'platform': self.platform,
            'region': self.region,
            'release_year': self.release_year,
            'publisher': self.publisher,
            'developer': self.developer,
            'genre': self.genre,
            'description': self.description,
            'players': self.players,
            'rating': self.rating,
            'cover_image_url': self.cover_image_url,
            'source': self.source,
            'download_count': self.download_count,
            'popularity_score': self.popularity_score
        }
