"""
Settings model for storing application configuration
"""

from extensions import db

class Settings(db.Model):
    """Settings model for storing application configuration"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True)
    value = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='general')
    description = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    
    __table_args__ = (
        db.Index('idx_settings_category', 'category'),
    )
    
    @classmethod
    def get(cls, key, default=None):
        """Get a setting value by key"""
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @classmethod
    def set(cls, key, value, category='general'):
        """Set a setting value"""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
            setting.category = category
        else:
            setting = cls(key=key, value=str(value), category=category)
            db.session.add(setting)
        db.session.commit()
        return setting
    
    @classmethod
    def get_all(cls):
        """Get all settings as a dictionary"""
        settings = cls.query.all()
        return {s.key: s.value for s in settings}
    
    @classmethod
    def get_by_category(cls, category):
        """Get all settings in a category"""
        settings = cls.query.filter_by(category=category).all()
        return {s.key: s.value for s in settings}
    
    @classmethod
    def get_prowlarr_config(cls):
        """Get Prowlarr configuration"""
        return {
            'prowlarr_url': cls.get('prowlarr_url', 'http://localhost:9696'),
            'prowlarr_api_key': cls.get('prowlarr_api_key', ''),
            'enabled': cls.get('prowlarr_enabled', 'true') == 'true',
            # Legacy aliases kept for template compatibility
            'url': cls.get('prowlarr_url', 'http://localhost:9696'),
            'api_key': cls.get('prowlarr_api_key', ''),
        }
    
    @classmethod
    def get_qbittorrent_config(cls):
        """Get qBittorrent configuration"""
        return {
            'url': cls.get('qbittorrent_url', 'http://localhost:8080'),
            'username': cls.get('qbittorrent_username', 'admin'),
            'password': cls.get('qbittorrent_password', 'adminadmin'),
            'enabled': cls.get('qbittorrent_enabled', 'true') == 'true'
        }
    
    @classmethod
    def get_network_config(cls):
        """Get network hosting configuration"""
        return {
            'roms_path': cls.get('roms_path', '/data/roms'),
            'network_share_enabled': cls.get('network_share_enabled', 'true') == 'true',
            'network_share_path': cls.get('network_share_path', '/data/roms'),
            'network_share_type': cls.get('network_share_type', 'nfs'),  # nfs, smb, webdav
            'retropie_integration': cls.get('retropie_integration', 'true') == 'true',
            'retroarch_integration': cls.get('retroarch_integration', 'true') == 'true',
            'auto_refresh_library': cls.get('auto_refresh_library', 'true') == 'true'
        }
    
    @classmethod
    def get_download_config(cls):
        """Get download configuration"""
        return {
            'default_category': cls.get('download_default_category', 'romarr-roms'),
            'default_save_path': cls.get('download_default_save_path', '/data/roms'),
            'auto_import': cls.get('download_auto_import', 'true') == 'true',
            'auto_delete_torrents': cls.get('download_auto_delete_torrents', 'false') == 'true',
            'max_downloads': int(cls.get('download_max_downloads', '3')),
            'max_seeding_time': int(cls.get('download_max_seeding_time', '1440'))  # minutes
        }
    
    @classmethod
    def get_metadata_config(cls):
        """Get metadata source configuration (IGDB, RAWG, etc.)"""
        return {
            # IGDB (via Twitch API)
            'igdb_enabled': cls.get('igdb_enabled', 'false') == 'true',
            'igdb_client_id': cls.get('igdb_client_id', ''),
            'igdb_client_secret': cls.get('igdb_client_secret', ''),
            # RAWG
            'rawg_enabled': cls.get('rawg_enabled', 'false') == 'true',
            'rawg_api_key': cls.get('rawg_api_key', ''),
            # Priority order for sources (comma-separated)
            'source_priority': cls.get('metadata_source_priority', 'igdb,rawg,local'),
        }
    
    @classmethod
    def initialize_defaults(cls):
        """Initialize default settings if they don't exist"""
        defaults = [
            # Prowlarr settings
            ('prowlarr_url', 'http://localhost:9696', 'prowlarr'),
            ('prowlarr_api_key', '', 'prowlarr'),
            ('prowlarr_enabled', 'true', 'prowlarr'),
            
            # qBittorrent settings
            ('qbittorrent_url', 'http://localhost:8080', 'qbittorrent'),
            ('qbittorrent_username', 'admin', 'qbittorrent'),
            ('qbittorrent_password', 'adminadmin', 'qbittorrent'),
            ('qbittorrent_enabled', 'true', 'qbittorrent'),
            
            # Network hosting settings
            ('roms_path', '/data/roms', 'network'),
            ('network_share_enabled', 'true', 'network'),
            ('network_share_path', '/data/roms', 'network'),
            ('network_share_type', 'nfs', 'network'),
            ('retropie_integration', 'true', 'network'),
            ('retroarch_integration', 'true', 'network'),
            ('auto_refresh_library', 'true', 'network'),
            
            # Download settings
            ('download_default_category', 'romarr-roms', 'download'),
            ('download_default_save_path', '/data/roms', 'download'),
            ('download_auto_import', 'true', 'download'),
            ('download_auto_delete_torrents', 'false', 'download'),
            ('download_max_downloads', '3', 'download'),
            ('download_max_seeding_time', '1440', 'download'),
            
            # General settings
            ('theme', 'dark', 'general'),
            ('language', 'en', 'general'),
            ('timezone', 'UTC', 'general'),
            ('debug_mode', 'false', 'general'),
            ('log_level', 'info', 'general'),
            
            # Metadata source settings
            ('igdb_enabled', 'false', 'metadata'),
            ('igdb_client_id', '', 'metadata'),
            ('igdb_client_secret', '', 'metadata'),
            ('rawg_enabled', 'false', 'metadata'),
            ('rawg_api_key', '', 'metadata'),
            ('metadata_source_priority', 'igdb,rawg,local', 'metadata'),
        ]
        
        for key, value, category in defaults:
            if not cls.query.filter_by(key=key).first():
                cls.set(key, value, category)
        
        db.session.commit()