"""
Enhanced Metadata Database Schema
Normalized schema for retro gaming metadata with comprehensive game information
"""

from datetime import datetime
from typing import Dict, List, Optional
from extensions import db
from sqlalchemy import ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import json


# Association tables for many-to-many relationships
game_genre_association = db.Table('game_genre_association',
    db.Column('game_id', db.Integer, ForeignKey('metadata_games.id'), primary_key=True),
    db.Column('genre_id', db.Integer, ForeignKey('metadata_genres.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

game_theme_association = db.Table('game_theme_association',
    db.Column('game_id', db.Integer, ForeignKey('metadata_games.id'), primary_key=True),
    db.Column('theme_id', db.Integer, ForeignKey('metadata_themes.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

game_game_mode_association = db.Table('game_game_mode_association',
    db.Column('game_id', db.Integer, ForeignKey('metadata_games.id'), primary_key=True),
    db.Column('game_mode_id', db.Integer, ForeignKey('metadata_game_modes.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

game_player_perspective_association = db.Table('game_player_perspective_association',
    db.Column('game_id', db.Integer, ForeignKey('metadata_games.id'), primary_key=True),
    db.Column('player_perspective_id', db.Integer, ForeignKey('metadata_player_perspectives.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

game_keyword_association = db.Table('game_keyword_association',
    db.Column('game_id', db.Integer, ForeignKey('metadata_games.id'), primary_key=True),
    db.Column('keyword_id', db.Integer, ForeignKey('metadata_keywords.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

game_alternative_name_association = db.Table('game_alternative_name_association',
    db.Column('game_id', db.Integer, ForeignKey('metadata_games.id'), primary_key=True),
    db.Column('alternative_name_id', db.Integer, ForeignKey('metadata_alternative_names.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

game_developer_association = db.Table('game_developer_association',
    db.Column('game_id', db.Integer, ForeignKey('metadata_games.id'), primary_key=True),
    db.Column('company_id', db.Integer, ForeignKey('metadata_companies.id'), primary_key=True),
    db.Column('role', db.String(20), default='developer'),  # developer, publisher, etc.
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

game_publisher_association = db.Table('game_publisher_association',
    db.Column('game_id', db.Integer, ForeignKey('metadata_games.id'), primary_key=True),
    db.Column('company_id', db.Integer, ForeignKey('metadata_companies.id'), primary_key=True),
    db.Column('role', db.String(20), default='publisher'),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

game_platform_association = db.Table('game_platform_association',
    db.Column('game_id', db.Integer, ForeignKey('metadata_games.id'), primary_key=True),
    db.Column('platform_id', db.Integer, ForeignKey('metadata_platforms.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)


class MetadataPlatform(db.Model):
    """Platform/console information"""
    __tablename__ = 'metadata_platforms'
    
    id = db.Column(db.Integer, primary_key=True)
    igdb_id = db.Column(db.Integer, unique=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, index=True)
    abbreviation = db.Column(db.String(20))
    platform_family = db.Column(db.String(50))
    generation = db.Column(db.Integer)
    
    # Platform details
    summary = db.Column(db.Text)
    manufacturer = db.Column(db.String(100))
    release_date = db.Column(db.Date)
    discontinued_date = db.Column(db.Date)
    units_sold = db.Column(db.BigInteger)
    
    # Media
    logo_url = db.Column(db.String(500))
    photo_url = db.Column(db.String(500))
    
    # Source tracking
    source = db.Column(db.String(50))  # 'igdb', 'manual', 'libretro'
    source_id = db.Column(db.String(100))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    games = relationship('MetadataGame', secondary=game_platform_association, back_populates='platforms')
    
    def __repr__(self):
        return f'<MetadataPlatform {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'igdb_id': self.igdb_id,
            'name': self.name,
            'slug': self.slug,
            'abbreviation': self.abbreviation,
            'platform_family': self.platform_family,
            'generation': self.generation,
            'release_date': self.release_date.isoformat() if self.release_date else None,
            'manufacturer': self.manufacturer,
            'logo_url': self.logo_url
        }


class MetadataGenre(db.Model):
    """Game genre classification"""
    __tablename__ = 'metadata_genres'
    
    id = db.Column(db.Integer, primary_key=True)
    igdb_id = db.Column(db.Integer, unique=True, index=True)
    name = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(50), unique=True, index=True)
    description = db.Column(db.Text)
    
    # Source tracking
    source = db.Column(db.String(50))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    games = relationship('MetadataGame', secondary=game_genre_association, back_populates='genres')
    
    def __repr__(self):
        return f'<MetadataGenre {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'igdb_id': self.igdb_id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description
        }


class MetadataTheme(db.Model):
    """Game theme"""
    __tablename__ = 'metadata_themes'
    
    id = db.Column(db.Integer, primary_key=True)
    igdb_id = db.Column(db.Integer, unique=True, index=True)
    name = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(50), unique=True, index=True)
    
    # Source tracking
    source = db.Column(db.String(50))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    games = relationship('MetadataGame', secondary=game_theme_association, back_populates='themes')
    
    def __repr__(self):
        return f'<MetadataTheme {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'igdb_id': self.igdb_id,
            'name': self.name,
            'slug': self.slug
        }


class MetadataGameMode(db.Model):
    """Game mode (single-player, multiplayer, etc.)"""
    __tablename__ = 'metadata_game_modes'
    
    id = db.Column(db.Integer, primary_key=True)
    igdb_id = db.Column(db.Integer, unique=True, index=True)
    name = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(50), unique=True, index=True)
    
    # Source tracking
    source = db.Column(db.String(50))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    games = relationship('MetadataGame', secondary=game_game_mode_association, back_populates='game_modes')
    
    def __repr__(self):
        return f'<MetadataGameMode {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'igdb_id': self.igdb_id,
            'name': self.name,
            'slug': self.slug
        }


class MetadataPlayerPerspective(db.Model):
    """Player perspective (first-person, third-person, etc.)"""
    __tablename__ = 'metadata_player_perspectives'
    
    id = db.Column(db.Integer, primary_key=True)
    igdb_id = db.Column(db.Integer, unique=True, index=True)
    name = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(50), unique=True, index=True)
    
    # Source tracking
    source = db.Column(db.String(50))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    games = relationship('MetadataGame', secondary=game_player_perspective_association, back_populates='player_perspectives')
    
    def __repr__(self):
        return f'<MetadataPlayerPerspective {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'igdb_id': self.igdb_id,
            'name': self.name,
            'slug': self.slug
        }


class MetadataKeyword(db.Model):
    """Game keywords/tags"""
    __tablename__ = 'metadata_keywords'
    
    id = db.Column(db.Integer, primary_key=True)
    igdb_id = db.Column(db.Integer, unique=True, index=True)
    name = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(50), unique=True, index=True)
    
    # Source tracking
    source = db.Column(db.String(50))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    games = relationship('MetadataGame', secondary=game_keyword_association, back_populates='keywords')
    
    def __repr__(self):
        return f'<MetadataKeyword {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'igdb_id': self.igdb_id,
            'name': self.name,
            'slug': self.slug
        }


class MetadataCompany(db.Model):
    """Company (developer, publisher)"""
    __tablename__ = 'metadata_companies'
    
    id = db.Column(db.Integer, primary_key=True)
    igdb_id = db.Column(db.Integer, unique=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, index=True)
    
    # Company details
    description = db.Column(db.Text)
    country = db.Column(db.Integer)  # IGDB country code
    country_name = db.Column(db.String(50))
    start_date = db.Column(db.Date)
    changed_company_id = db.Column(db.Integer)  # If company changed
    
    # Media
    logo_url = db.Column(db.String(500))
    
    # Source tracking
    source = db.Column(db.String(50))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    developed_games = relationship('MetadataGame', secondary=game_developer_association, back_populates='developers')
    published_games = relationship('MetadataGame', secondary=game_publisher_association, back_populates='publishers')
    
    def __repr__(self):
        return f'<MetadataCompany {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'igdb_id': self.igdb_id,
            'name': self.name,
            'slug': self.slug,
            'country_name': self.country_name,
            'description': self.description,
            'logo_url': self.logo_url
        }


class MetadataAlternativeName(db.Model):
    """Alternative names for games"""
    __tablename__ = 'metadata_alternative_names'
    
    id = db.Column(db.Integer, primary_key=True)
    igdb_id = db.Column(db.Integer, unique=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    comment = db.Column(db.String(200))  # e.g., "Acronym", "Japanese title"
    
    # Source tracking
    source = db.Column(db.String(50))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    games = relationship('MetadataGame', secondary=game_alternative_name_association, back_populates='alternative_names')
    
    def __repr__(self):
        return f'<MetadataAlternativeName {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'igdb_id': self.igdb_id,
            'name': self.name,
            'comment': self.comment
        }


class MetadataGame(db.Model):
    """Main game metadata table"""
    __tablename__ = 'metadata_games'
    
    id = db.Column(db.Integer, primary_key=True)
    igdb_id = db.Column(db.Integer, unique=True, index=True)
    
    # Basic information
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, index=True)
    clean_title = db.Column(db.String(200), index=True)  # For 1G1R matching
    
    # Descriptions
    summary = db.Column(db.Text)
    storyline = db.Column(db.Text)
    
    # Ratings
    rating = db.Column(db.Float)  # 0-100
    rating_count = db.Column(db.Integer)
    aggregated_rating = db.Column(db.Float)
    aggregated_rating_count = db.Column(db.Integer)
    total_rating = db.Column(db.Float)
    total_rating_count = db.Column(db.Integer)
    
    # Release information
    first_release_date = db.Column(db.Date)
    release_year = db.Column(db.Integer)
    
    # Game status
    status = db.Column(db.String(50))  # released, alpha, beta, etc.
    category = db.Column(db.String(50))  # main_game, expansion, bundle, etc.
    
    # Player information
    player_count_min = db.Column(db.Integer)
    player_count_max = db.Column(db.Integer)
    player_count_recommended = db.Column(db.Integer)
    
    # Time to beat (in minutes)
    time_to_beat_completionist = db.Column(db.Integer)
    time_to_beat_main = db.Column(db.Integer)
    time_to_beat_main_extra = db.Column(db.Integer)
    
    # Media
    cover_url = db.Column(db.String(500))
    screenshot_urls = db.Column(db.Text)  # JSON array
    artwork_urls = db.Column(db.Text)  # JSON array
    video_urls = db.Column(db.Text)  # JSON array
    
    # Websites
    websites = db.Column(db.Text)  # JSON array
    
    # Franchise/collection
    franchise_id = db.Column(db.Integer)
    collection_id = db.Column(db.Integer)
    
    # Game engine
    game_engine_id = db.Column(db.Integer)
    game_engine_name = db.Column(db.String(100))
    
    # Source tracking
    source = db.Column(db.String(50))  # 'igdb', 'manual', 'dat_file'
    source_id = db.Column(db.String(100))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    platforms = relationship('MetadataPlatform', secondary=game_platform_association, back_populates='games')
    genres = relationship('MetadataGenre', secondary=game_genre_association, back_populates='games')
    themes = relationship('MetadataTheme', secondary=game_theme_association, back_populates='games')
    game_modes = relationship('MetadataGameMode', secondary=game_game_mode_association, back_populates='games')
    player_perspectives = relationship('MetadataPlayerPerspective', secondary=game_player_perspective_association, back_populates='games')
    keywords = relationship('MetadataKeyword', secondary=game_keyword_association, back_populates='games')
    alternative_names = relationship('MetadataAlternativeName', secondary=game_alternative_name_association, back_populates='games')
    developers = relationship('MetadataCompany', secondary=game_developer_association, back_populates='developed_games')
    publishers = relationship('MetadataCompany', secondary=game_publisher_association, back_populates='published_games')
    
    # ROM information (one-to-many)
    roms = relationship('MetadataROM', back_populates='game', cascade='all, delete-orphan')
    
    # Release dates (one-to-many)
    release_dates = relationship('MetadataReleaseDate', back_populates='game', cascade='all, delete-orphan')
    
    # Indexes
    __table_args__ = (
        Index('idx_metadata_games_title', 'title'),
        Index('idx_metadata_games_release_year', 'release_year'),
        Index('idx_metadata_games_rating', 'rating'),
    )
    
    def __repr__(self):
        return f'<MetadataGame {self.title}>'
    
    def to_dict(self, include_relationships=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'igdb_id': self.igdb_id,
            'title': self.title,
            'slug': self.slug,
            'clean_title': self.clean_title,
            'summary': self.summary,
            'storyline': self.storyline,
            'rating': self.rating,
            'rating_count': self.rating_count,
            'aggregated_rating': self.aggregated_rating,
            'total_rating': self.total_rating,
            'first_release_date': self.first_release_date.isoformat() if self.first_release_date else None,
            'release_year': self.release_year,
            'status': self.status,
            'category': self.category,
            'cover_url': self.cover_url,
            'player_count_min': self.player_count_min,
            'player_count_max': self.player_count_max,
            'source': self.source,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
        
        if include_relationships:
            data['platforms'] = [p.to_dict() for p in self.platforms]
            data['genres'] = [g.to_dict() for g in self.genres]
            data['developers'] = [d.to_dict() for d in self.developers]
            data['publishers'] = [p.to_dict() for p in self.publishers]
            data['roms'] = [r.to_dict() for r in self.roms]
            
            # Parse JSON fields
            if self.screenshot_urls:
                try:
                    data['screenshot_urls'] = json.loads(self.screenshot_urls)
                except:
                    data['screenshot_urls'] = []
            else:
                data['screenshot_urls'] = []
            
            if self.websites:
                try:
                    data['websites'] = json.loads(self.websites)
                except:
                    data['websites'] = []
            else:
                data['websites'] = []
        
        return data


class MetadataROM(db.Model):
    """ROM file information from DAT files"""
    __tablename__ = 'metadata_roms'
    
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, ForeignKey('metadata_games.id'), nullable=False, index=True)
    
    # ROM identification
    filename = db.Column(db.String(500), nullable=False)
    size = db.Column(db.BigInteger)  # Size in bytes
    crc = db.Column(db.String(8))  # CRC32
    md5 = db.Column(db.String(32))
    sha1 = db.Column(db.String(40))
    sha256 = db.Column(db.String(64))
    
    # ROM metadata
    region = db.Column(db.String(50))
    version = db.Column(db.String(50))  # Rev 1, v1.0, etc.
    serial = db.Column(db.String(100))  # Disc serial number
    status = db.Column(db.String(20))  # verified, bad, alternate
    
    # Source information
    source = db.Column(db.String(50))  # 'no-intro', 'redump', 'libretro'
    source_id = db.Column(db.String(100))
    dat_file = db.Column(db.String(500))  # Original DAT file
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    game = relationship('MetadataGame', back_populates='roms')
    
    # Indexes
    __table_args__ = (
        Index('idx_metadata_roms_crc', 'crc'),
        Index('idx_metadata_roms_md5', 'md5'),
        Index('idx_metadata_roms_sha1', 'sha1'),
        UniqueConstraint('game_id', 'crc', 'md5', name='uq_game_rom_hash'),
    )
    
    def __repr__(self):
        return f'<MetadataROM {self.filename}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'game_id': self.game_id,
            'filename': self.filename,
            'size': self.size,
            'crc': self.crc,
            'md5': self.md5,
            'sha1': self.sha1,
            'region': self.region,
            'version': self.version,
            'serial': self.serial,
            'status': self.status,
            'source': self.source
        }


class MetadataReleaseDate(db.Model):
    """Release date information for games by region"""
    __tablename__ = 'metadata_release_dates'
    
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, ForeignKey('metadata_games.id'), nullable=False, index=True)
    platform_id = db.Column(db.Integer, ForeignKey('metadata_platforms.id'), index=True)
    
    # Release information
    region = db.Column(db.String(50))  # 1=Europe, 2=North America, 3=Australia, 4=New Zealand, 5=Japan, 6=China, 7=Asia, 8=Worldwide
    region_name = db.Column(db.String(50))  # Human-readable region name
    date = db.Column(db.Date)
    year = db.Column(db.Integer)
    human = db.Column(db.String(100))  # Human-readable date
    
    # Certification/rating
    certification = db.Column(db.String(50))  # ESRB, PEGI, etc.
    rating = db.Column(db.String(10))  # E, T, M, etc.
    
    # Source tracking
    source = db.Column(db.String(50))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    game = relationship('MetadataGame', back_populates='release_dates')
    platform = relationship('MetadataPlatform')
    
    def __repr__(self):
        return f'<MetadataReleaseDate {self.region_name} {self.date}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'game_id': self.game_id,
            'platform_id': self.platform_id,
            'region': self.region,
            'region_name': self.region_name,
            'date': self.date.isoformat() if self.date else None,
            'year': self.year,
            'human': self.human,
            'certification': self.certification,
            'rating': self.rating
        }


class MetadataDatabaseManager:
    """Manager for metadata database operations"""
    
    @classmethod
    def initialize_database(cls):
        """Initialize database tables"""
        try:
            db.create_all()
            logger.info("Metadata database tables created")
            return True
        except Exception as e:
            logger.error(f"Error creating metadata database tables: {e}")
            return False
    
    @classmethod
    def clear_database(cls):
        """Clear all metadata tables (for testing/reset)"""
        try:
            # Drop all tables in reverse order to avoid foreign key constraints
            db.session.query(MetadataROM).delete()
            db.session.query(MetadataReleaseDate).delete()
            db.session.query(MetadataGame).delete()
            db.session.query(MetadataPlatform).delete()
            db.session.query(MetadataGenre).delete()
            db.session.query(MetadataTheme).delete()
            db.session.query(MetadataGameMode).delete()
            db.session.query(MetadataPlayerPerspective).delete()
            db.session.query(MetadataKeyword).delete()
            db.session.query(MetadataCompany).delete()
            db.session.query(MetadataAlternativeName).delete()
            
            db.session.commit()
            logger.info("Metadata database cleared")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error clearing metadata database: {e}")
            return False
    
    @classmethod
    def get_statistics(cls) -> Dict:
        """Get database statistics"""
        stats = {
            'games': MetadataGame.query.count(),
            'platforms': MetadataPlatform.query.count(),
            'genres': MetadataGenre.query.count(),
            'companies': MetadataCompany.query.count(),
            'roms': MetadataROM.query.count(),
            'release_dates': MetadataReleaseDate.query.count()
        }
        
        # Count by source
        sources = db.session.query(MetadataGame.source, db.func.count(MetadataGame.id)).group_by(MetadataGame.source).all()
        stats['sources'] = dict(sources)
        
        return stats


# Import logger at the end to avoid circular imports
import logging
logger = logging.getLogger(__name__)