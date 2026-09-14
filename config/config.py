"""
Configuration settings for ROMarr
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'romarr.db')}"
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