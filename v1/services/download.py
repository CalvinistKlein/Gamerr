"""
Download service for qBittorrent integration
"""

import time
from typing import Dict, List, Optional
from config.config import Config
from models.settings import Settings
from models.unified_schema import Download
from extensions import db


class DownloadService:
    """Service for managing downloads via qBittorrent"""
    
    @classmethod
    def _get_qbittorrent_client(cls) -> Optional['Client']:
        """Get qBittorrent client instance"""
        try:
            from qbittorrent import Client  # lazy import — missing package won't crash the app
        except ImportError:
            return None

        config = Settings.get_qbittorrent_config()
        url = config.get('qbittorrent_url', '') or config.get('url', '')
        username = config.get('qbittorrent_username', '') or config.get('username', '')
        password = config.get('qbittorrent_password', '') or config.get('password', '')
        
        if not url:
            return None
        
        try:
            qb = Client(url)
            if username and password:
                qb.login(username, password)
            else:
                qb.login()  # Try without credentials
            return qb
        except Exception as e:
            print(f"Failed to connect to qBittorrent: {e}")
            return None
    
    @classmethod
    def add_download(cls, torrent_url: str, category: str = "roms") -> Optional[Dict]:
        """
        Add a torrent to qBittorrent
        
        Args:
            torrent_url: Magnet link or torrent file URL
            category: Category to assign the download
            
        Returns:
            Dictionary with download info or None if failed
        """
        qb = cls._get_qbittorrent_client()
        if not qb:
            return None
        
        try:
            # Add torrent to qBittorrent
            qb.download_from_link(torrent_url, category=category)
            
            # Get the torrent hash from the URL (simplified)
            # In a real implementation, you'd parse the magnet link
            import hashlib
            torrent_hash = hashlib.md5(torrent_url.encode()).hexdigest()[:20]
            
            return {
                'success': True,
                'torrent_hash': torrent_hash,
                'message': 'Torrent added to qBittorrent'
            }
        except Exception as e:
            print(f"Failed to add download: {e}")
            return None
    
    @classmethod
    def get_active_downloads(cls) -> List[Dict]:
        """Get list of active downloads from qBittorrent"""
        qb = cls._get_qbittorrent_client()
        if not qb:
            return []
        
        try:
            torrents = qb.torrents()
            active_downloads = []
            
            for torrent in torrents:
                # Only include downloading torrents
                if torrent['state'] in ['downloading', 'stalledDL', 'queuedDL', 'checkingDL', 'pausedDL']:
                    download_info = {
                        'name': torrent['name'],
                        'hash': torrent['hash'],
                        'size': torrent['size'],
                        'progress': torrent['progress'],
                        'download_speed': torrent['dlspeed'],
                        'upload_speed': torrent['upspeed'],
                        'eta': torrent['eta'],
                        'state': torrent['state'],
                        'category': torrent.get('category', ''),
                        'save_path': torrent['save_path']
                    }
                    active_downloads.append(download_info)
            
            return active_downloads
        except Exception as e:
            print(f"Failed to get active downloads: {e}")
            return []
    
    @classmethod
    def get_completed_downloads(cls) -> List[Dict]:
        """Get list of completed downloads from qBittorrent"""
        qb = cls._get_qbittorrent_client()
        if not qb:
            return []
        
        try:
            torrents = qb.torrents()
            completed_downloads = []
            
            for torrent in torrents:
                # Only include completed torrents
                if torrent['progress'] == 1:
                    download_info = {
                        'name': torrent['name'],
                        'hash': torrent['hash'],
                        'size': torrent['size'],
                        'progress': torrent['progress'],
                        'state': torrent['state'],
                        'category': torrent.get('category', ''),
                        'save_path': torrent['save_path'],
                        'completion_date': torrent.get('completion_date', 0)
                    }
                    completed_downloads.append(download_info)
            
            return completed_downloads
        except Exception as e:
            print(f"Failed to get completed downloads: {e}")
            return []
    
    @classmethod
    def sync_downloads_with_database(cls):
        """Sync qBittorrent downloads with database"""
        qb = cls._get_qbittorrent_client()
        if not qb:
            return
        
        try:
            torrents = qb.torrents()
            
            for torrent in torrents:
                torrent_hash = torrent['hash']
                
                # Check if download already exists in database
                existing_download = Download.query.filter_by(torrent_hash=torrent_hash).first()
                
                if not existing_download:
                    # Create new download record
                    download = Download(
                        torrent_hash=torrent_hash,
                        torrent_name=torrent['name'],
                        download_path=torrent['save_path'],
                        size_bytes=torrent['size'],
                        progress=torrent['progress'] * 100,  # Convert to percentage
                        status=cls._map_qb_state_to_status(torrent['state'])
                    )
                    db.session.add(download)
                else:
                    # Update existing download
                    existing_download.torrent_name = torrent['name']
                    existing_download.progress = torrent['progress'] * 100
                    existing_download.status = cls._map_qb_state_to_status(torrent['state'])
                    
                    # Mark as completed if progress is 100%
                    if torrent['progress'] == 1 and existing_download.status != 'completed':
                        existing_download.status = 'completed'
            
            db.session.commit()
        except Exception as e:
            print(f"Failed to sync downloads: {e}")
            db.session.rollback()
    
    @classmethod
    def _map_qb_state_to_status(cls, qb_state: str) -> str:
        """Map qBittorrent state to download status"""
        state_mapping = {
            'downloading': 'downloading',
            'stalledDL': 'downloading',
            'queuedDL': 'queued',
            'checkingDL': 'downloading',
            'pausedDL': 'paused',
            'uploading': 'seeding',
            'stalledUP': 'seeding',
            'queuedUP': 'seeding',
            'checkingUP': 'seeding',
            'pausedUP': 'paused',
            'error': 'failed',
            'missingFiles': 'failed'
        }
        
        return state_mapping.get(qb_state, 'unknown')
    
    @classmethod
    def test_connection(cls) -> Dict:
        """Test qBittorrent connection"""
        qb = cls._get_qbittorrent_client()
        
        if not qb:
            return {
                'success': False,
                'message': 'Failed to connect to qBittorrent'
            }
        
        try:
            # Try to get version info
            version = qb.qbittorrent_version
            return {
                'success': True,
                'message': 'qBittorrent connection successful',
                'version': version
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to communicate with qBittorrent: {str(e)}'
            }
    
    @classmethod
    def monitor_downloads(cls):
        """Monitor and update download status (to be run periodically)"""
        cls.sync_downloads_with_database()
        
        # Check for completed downloads that need processing
        completed_downloads = Download.query.filter_by(status='completed').all()
        
        for download in completed_downloads:
            # Here you would add logic to:
            # 1. Import the downloaded ROM
            # 2. Update game status
            # 3. Move files to library
            # 4. Clean up torrent if desired
            pass