"""
Configuration settings for Gamerr
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    _base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _db_path = os.path.join(_base_dir, 'instance', 'gamerr.db')
    if not os.path.exists(_db_path) and os.path.exists(os.path.join(_base_dir, 'instance', 'romarr.db')):
        _db_path = os.path.join(_base_dir, 'instance', 'romarr.db')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{_db_path}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Prowlarr configuration
    PROWLARR_URL = os.environ.get('PROWLARR_URL', 'http://localhost:9696')
    PROWLARR_API_KEY = os.environ.get('PROWLARR_API_KEY', '')
    
    # qBittorrent configuration
    QBITTORRENT_URL = os.environ.get('QBITTORRENT_URL', 'http://localhost:8080')
    QBITTORRENT_USERNAME = os.environ.get('QBITTORRENT_USERNAME', 'admin')
    QBITTORRENT_PASSWORD = os.environ.get('QBITTORRENT_PASSWORD', 'adminadmin')
    
    # ROMs path
    ROMS_PATH = os.environ.get('ROMS_PATH', '/data/roms')
    
    # Gamerr SkyHook Metadata Proxy (Radarr/Sonarr style, zero user API keys)
    METADATA_API_URL = os.environ.get('METADATA_API_URL', 'https://api.gamerr.io/v1')
    
    # Application settings
    DEBUG = os.environ.get('FLASK_ENV') == 'development'