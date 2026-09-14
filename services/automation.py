"""
Automation service for automatic search and download workflow
"""

import time
import threading
import functools
import traceback
from datetime import datetime
from typing import Dict, List, Optional

from extensions import db
from models.unified_schema import WantedGame
from models.unified_schema import Game
from models.unified_schema import Download
from models.constants import (
    GAME_STATUS_DOWNLOADING, GAME_STATUS_LIBRARY,
    DOWNLOAD_STATUS_QUEUED, DOWNLOAD_STATUS_DOWNLOADING, DOWNLOAD_STATUS_COMPLETED
)
from services.search import SearchService
from services.download import DownloadService
from config.constants import (
    AUTOMATION_INTERVAL,
    AUTOMATION_ENABLED,
    AUTOMATION_MAX_CONCURRENT_DOWNLOADS
)

class AutomationService:
    """Service for automating the search and download workflow"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AutomationService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """Initialize automation service"""
        if self._initialized:
            return
        
        self._running = False
        self._thread = None
        self._last_run = None
        self._stats = {
            'total_searches': 0,
            'total_downloads_started': 0,
            'total_downloads_completed': 0,
            'last_error': None
        }
        
        self._initialized = True
    
    def start(self, app=None):
        """Start automation service"""
        if self._running:
            return
        
        self._app = app  # store app reference for thread context
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("Automation service started")
    
    def stop(self):
        """Stop automation service"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("Automation service stopped")
    
    def _run_loop(self):
        """Main automation loop"""
        if self._app is not None:
            app = self._app
        else:
            try:
                from flask import current_app
                if current_app:
                    app = current_app._get_current_object()
                else:
                    from app import app as flask_app
                    app = flask_app
            except Exception:
                from app import create_app
                app = create_app()
        
        while self._running:
            try:
                with app.app_context():
                    self._process_pending_wanted_games()
                    self._monitor_downloads()
                    self._process_completed_downloads()
                    
                    self._last_run = datetime.utcnow()
                    self._stats['last_error'] = None
                
            except Exception as e:
                self._stats['last_error'] = str(e)
                print(f"Error in automation loop: {e}")
                traceback.print_exc()
            
            # Sleep for configured interval
            time.sleep(AUTOMATION_INTERVAL)
    
    def _process_pending_wanted_games(self):
        """Process pending wanted games and start downloads"""
        try:
            # Get pending wanted games
            pending_games = WantedGame.query.filter_by(status='pending').all()
            
            for wanted_game in pending_games:
                # Check if we have too many concurrent downloads
                active_downloads = Download.query.filter(
                    Download.status.in_(['downloading', 'queued'])
                ).count()
                
                if active_downloads >= AUTOMATION_MAX_CONCURRENT_DOWNLOADS:
                    print(f"Too many active downloads ({active_downloads}), skipping for now")
                    break
                
                # Search for the game
                print(f"Searching for: {wanted_game.game_title} ({wanted_game.platform})")
                results = SearchService.search_games(
                    query=wanted_game.game_title,
                    platform=wanted_game.platform
                )
                
                self._stats['total_searches'] += 1
                
                if results:
                    # Select the best result
                    best_result = self._select_best_result(results, wanted_game)
                    
                    if best_result:
                        # Create download from result
                        download = self._create_download_from_result(best_result, wanted_game)
                        
                        if download:
                            # Update wanted game status
                            wanted_game.status = 'downloading'
                            wanted_game.download_id = download.id
                            wanted_game.last_searched = datetime.utcnow()
                            db.session.commit()
                            
                            self._stats['total_downloads_started'] += 1
                            print(f"Started download for: {wanted_game.game_title}")
                
                # Update last search date even if no results found
                wanted_game.last_searched = datetime.utcnow()
                db.session.commit()
                
        except Exception as e:
            print(f"Error processing pending wanted games: {e}")
            traceback.print_exc()
            db.session.rollback()
    
    def _select_best_result(self, results: List[Dict], wanted_game: WantedGame) -> Optional[Dict]:
        """Select the best result from search results"""
        if not results:
            return None
        
        # Simple scoring algorithm
        scored_results = []
        for result in results:
            score = 0
            
            # Title match (case-insensitive)
            result_title = result.get('title', '').lower()
            wanted_title = wanted_game.game_title.lower()
            
            if wanted_title in result_title:
                score += 10
            
            # Platform match
            result_platform = result.get('platform', '').lower()
            wanted_platform = (wanted_game.platform or '').lower()
            
            if wanted_platform in result_platform:
                score += 5
            
            # Region preference
            if wanted_game.region_preference:
                result_region = result.get('region', '').lower()
                wanted_region = (wanted_game.region_preference or '').lower()
                
                if wanted_region in result_region:
                    score += 3
            
            # Seeders/leechers (if available)
            seeders = result.get('seeders', 0)
            leechers = result.get('leechers', 0)
            
            if seeders > 0:
                score += min(seeders / 10, 5)  # Max 5 points for seeders
            
            # Size (prefer reasonable sizes)
            size_mb = result.get('size', 0) / (1024 * 1024)
            if 1 <= size_mb <= 500:  # Reasonable ROM size range
                score += 2
            
            scored_results.append((score, result))
        
        # Return result with highest score
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return scored_results[0][1] if scored_results else None
    
    def _create_download_from_result(self, result: Dict, wanted_game: WantedGame) -> Optional[Download]:
        """Create a download from search result"""
        try:
            # First, create or update the game record
            from models.unified_schema import Platform
            game = Game.query.filter(
                Game.title == wanted_game.game_title,
                Game.platforms.any((Platform.name.ilike(wanted_game.platform or '')) | (Platform.slug == (wanted_game.platform or '').lower()))
            ).first()
            
            if not game:
                game = Game(
                    title=wanted_game.game_title,
                    platform=wanted_game.platform,
                    region=wanted_game.region_preference,
                    status=GAME_STATUS_DOWNLOADING
                )
                db.session.add(game)
                db.session.flush()  # Get the game ID
            else:
                game.status = GAME_STATUS_DOWNLOADING
            
            # Create download record
            download = Download(
                game_id=game.id,
                torrent_hash=result.get('guid', ''),
                torrent_name=result.get('title', ''),
                download_path='',  # Will be set by qBittorrent
                size_bytes=result.get('size', 0),
                status=DOWNLOAD_STATUS_QUEUED
            )
            
            db.session.add(download)
            db.session.commit()
            
            # Try to add to qBittorrent
            download_url = result.get('download_url')
            if download_url:
                download_result = DownloadService.add_download(
                    torrent_url=download_url,
                    category="romarr-roms"
                )
                
                if download_result and download_result.get('success'):
                    download.torrent_hash = download_result.get('torrent_hash', download.torrent_hash)
                    download.status = DOWNLOAD_STATUS_DOWNLOADING
                    db.session.commit()
            
            return download
            
        except Exception as e:
            print(f"Error creating download: {e}")
            traceback.print_exc()
            db.session.rollback()
            return None
    
    def _monitor_downloads(self):
        """Monitor active downloads and update their status"""
        # Sync with qBittorrent
        DownloadService.sync_downloads_with_database()
    
    def _process_completed_downloads(self):
        """Process completed downloads and import them to library"""
        completed_downloads = Download.query.filter_by(status='completed').all()
        
        for download in completed_downloads:
            try:
                # Get the associated game
                game = Game.query.get(download.game_id)
                if not game:
                    continue
                
                # Update game status to library
                game.status = GAME_STATUS_LIBRARY
                game.file_path = download.download_path
                game.file_size = download.size_bytes
                game.added_date = datetime.utcnow()
                
                # Update wanted game if exists
                wanted_game = WantedGame.query.filter_by(download_id=download.id).first()
                if wanted_game:
                    wanted_game.status = 'completed'
                    wanted_game.completed_date = datetime.utcnow()
                
                db.session.commit()
                
                self._stats['total_downloads_completed'] += 1
                print(f"Completed download: {game.title}")
                
            except Exception as e:
                print(f"Error processing completed download {download.id}: {e}")
                traceback.print_exc()
                db.session.rollback()
    
    def trigger_immediate_search(self, wanted_game_id: int):
        """Trigger immediate search for a specific wanted game"""
        wanted_game = WantedGame.query.get(wanted_game_id)
        if not wanted_game:
            return False
        
        try:
            # Search for the game
            results = SearchService.search_games(
                query=wanted_game.game_title,
                platform=wanted_game.platform
            )
            
            if results:
                best_result = self._select_best_result(results, wanted_game)
                if best_result:
                    download = self._create_download_from_result(best_result, wanted_game)
                    if download:
                        wanted_game.status = 'downloading'
                        wanted_game.download_id = download.id
                        wanted_game.last_searched = datetime.utcnow()
                        db.session.commit()
                        return True
            
            return False
            
        except Exception as e:
            print(f"Error in immediate search: {e}")
            traceback.print_exc()
            return False
    
    def get_status(self) -> Dict:
        """Get automation service status"""
        return {
            'running': self._running,
            'last_run': self._last_run.isoformat() if self._last_run else None,
            'stats': self._stats,
            'active_downloads': Download.query.filter(
                Download.status.in_(['downloading', 'queued'])
            ).count(),
            'pending_wanted_games': WantedGame.query.filter_by(status='pending').count()
        }
# Export an instance for the app to use
automation_service = AutomationService()
