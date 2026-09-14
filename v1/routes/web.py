"""
Web routes for Romarr UI
"""

from flask import Blueprint, render_template, jsonify, request
import os
from models.unified_schema import Game
from models.unified_schema import WantedGame
from models.unified_schema import Download
from models.unified_schema import GameCatalog
from models.settings import Settings
from config.constants import COLORS, PLATFORMS

web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def index():
    """Dashboard page"""
    # Get stats for dashboard
    library_count = Game.get_library_count()
    wanted_count = WantedGame.get_active_count()
    active_downloads = Download.get_active()
    
    # Get recent activity
    recent_games = Game.query.order_by(Game.created_at.desc()).limit(5).all()
    recent_wanted = WantedGame.query.order_by(WantedGame.added_date.desc()).limit(5).all()
    
    # Get configuration for status display
    prowlarr_config = Settings.get_prowlarr_config()
    qbittorrent_config = Settings.get_qbittorrent_config()
    network_config = Settings.get_network_config()
    
    # Create recent activity list
    recent_activity = []
    
    # Add recent games as "add" activity
    for game in recent_games:
        recent_activity.append({
            'type': 'add',
            'message': f'Added {game.title} ({game.platform}) to library',
            'time': game.added_date.strftime('%Y-%m-%d %H:%M') if game.added_date else 'Recently'
        })
    
    # Add recent wanted games as "search" activity
    for wanted in recent_wanted:
        recent_activity.append({
            'type': 'search',
            'message': f'Added {wanted.game_title} ({wanted.platform}) to wanted list',
            'time': wanted.added_date.strftime('%Y-%m-%d %H:%M') if wanted.added_date else 'Recently'
        })
    
    # Sort by time (simplified - in reality you'd sort by actual timestamp)
    recent_activity = sorted(recent_activity, key=lambda x: x['time'], reverse=True)[:10]
    
    return render_template('index.html',
                         library_count=library_count,
                         wanted_count=wanted_count,
                         active_downloads=active_downloads,
                         recent_activity=recent_activity,
                         recent_wanted=recent_wanted,
                         prowlarr_config=prowlarr_config,
                         qbittorrent_config=qbittorrent_config,
                         network_config=network_config)

@web_bp.route('/library')
def library():
    """Game library page — paginated to avoid loading all rows at once"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    query_str = request.args.get('q', '')
    platform = request.args.get('platform', '')

    q = Game.query
    if query_str:
        q = q.filter(Game.title.ilike(f'%{query_str}%'))
    if platform:
        q = q.filter(Game.platform == platform)

    total = q.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    games = q.order_by(Game.title).offset((page - 1) * per_page).limit(per_page).all()

    return render_template('library.html', games=games,
                           page=page, total_pages=total_pages,
                           query=query_str, platform=platform,
                           platforms=PLATFORMS)

@web_bp.route('/wanted')
def wanted():
    """Wanted games page"""
    wanted_games = WantedGame.query.order_by(WantedGame.priority.desc(), WantedGame.added_date.desc()).all()
    return render_template('wanted.html', wanted_games=wanted_games)

@web_bp.route('/downloads')
def downloads():
    """Downloads page — paginated to avoid loading all rows at once"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    status_filter = request.args.get('status', '')

    q = Download.query
    if status_filter:
        q = q.filter(Download.status == status_filter)

    total = q.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    downloads_list = q.order_by(Download.added_date.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return render_template('downloads.html', downloads=downloads_list,
                           page=page, total_pages=total_pages,
                           status_filter=status_filter)

@web_bp.route('/catalog')
def catalog():
    """Game catalog page"""
    query = request.args.get('q', '')
    platform = request.args.get('platform', '')
    page = request.args.get('page', 1, type=int)
    per_page = 24
    
    from models.unified_schema import GameCatalog
    catalog_query = GameCatalog.query
    
    if query:
        catalog_query = catalog_query.filter(GameCatalog.title.ilike(f'%{query}%'))
    
    if platform:
        catalog_query = catalog_query.filter_by(platform=platform)
    
    # Simple pagination
    total_count = catalog_query.count()
    total_pages = (total_count + per_page - 1) // per_page
    
    games = catalog_query.order_by(GameCatalog.title).offset((page - 1) * per_page).limit(per_page).all()
    
    return render_template('catalog.html', 
                         games=games, 
                         colors=COLORS,
                         query=query,
                         platforms=PLATFORMS,
                         current_platform=platform,
                         page=page,
                         total_pages=total_pages)

@web_bp.route('/catalog/<int:catalog_id>')
def catalog_game(catalog_id):
    """Individual catalog game page"""
    from models.unified_schema import GameCatalog
    game = GameCatalog.query.get_or_404(catalog_id)
    return render_template('catalog_game.html', game=game, colors=COLORS)

@web_bp.route('/import')
def import_roms():
    """Import ROMs page"""
    return render_template('import.html')

@web_bp.route('/settings')
def settings():
    """Settings page"""
    from models.settings import Settings
    from scripts.database_manager import get_database_info
    
    prowlarr_config = Settings.get_prowlarr_config()
    qbittorrent_config = Settings.get_qbittorrent_config()
    network_config = Settings.get_network_config()
    download_config = Settings.get_download_config()
    metadata_config = Settings.get_metadata_config()

    
    # Get database info
    instance_path = os.path.join(os.getcwd(), 'instance', 'romarr.db')
    try:
        db_info = get_database_info(instance_path)
    except Exception as e:
        print(f"Error fetching database info for settings: {e}")
        db_info = None
    
    # Get general config
    general_config = {
        'theme': Settings.get('theme', 'dark'),
        'language': Settings.get('language', 'en'),
        'timezone': Settings.get('timezone', 'UTC'),
        'notifications_enabled': Settings.get('notifications_enabled', 'true') == 'true'
    }
    
    import socket
    try:
        hostname = socket.gethostname()
    except:
        hostname = 'localhost'
        
    return render_template('settings.html', 
                         prowlarr_config=prowlarr_config,
                         qbittorrent_config=qbittorrent_config,
                         network_config=network_config,
                         download_config=download_config,
                         general_config=general_config,
                         metadata_config=metadata_config,
                         db_info=db_info,
                         hostname=hostname)

@web_bp.route('/api/stats')
def get_stats():
    """Get system statistics for dashboard widgets"""
    library_count = Game.get_library_count()
    wanted_count = WantedGame.get_active_count()
    active_downloads_count = len(Download.get_active())
    
    # Get catalog stats
    catalog_count = GameCatalog.query.count()
    
    # Get download stats
    completed_downloads = Download.query.filter_by(status='completed').count()
    failed_downloads = Download.query.filter_by(status='failed').count()
    
    return jsonify({
        'library': library_count,
        'wanted': wanted_count,
        'active_downloads': active_downloads_count,
        'catalog': catalog_count,
        'completed_downloads': completed_downloads,
        'failed_downloads': failed_downloads
    })

@web_bp.route('/api/library/search')
def search_library():
    """Search library games"""
    query = request.args.get('q', '')
    platform = request.args.get('platform', '')
    
    games_query = Game.query
    
    if query:
        games_query = games_query.filter(Game.title.ilike(f'%{query}%'))
    
    if platform:
        games_query = games_query.filter_by(platform=platform)
    
    games = games_query.order_by(Game.title).all()
    
    return jsonify([{
        'id': game.id,
        'title': game.title,
        'platform': game.platform,
        'region': game.region,
        'release_year': game.release_year,
        'file_path': game.file_path,
        'status': game.status
    } for game in games])

@web_bp.route('/api/wanted/search')
def search_wanted():
    """Search wanted games"""
    query = request.args.get('q', '')
    platform = request.args.get('platform', '')
    
    wanted_query = WantedGame.query
    
    if query:
        wanted_query = wanted_query.filter(WantedGame.game_title.ilike(f'%{query}%'))
    
    if platform:
        wanted_query = wanted_query.filter_by(platform=platform)
    
    wanted_games = wanted_query.order_by(WantedGame.priority.desc(), WantedGame.added_date.desc()).all()
    
    return jsonify([{
        'id': game.id,
        'game_title': game.game_title,
        'platform': game.platform,
        'region_preference': game.region_preference,
        'quality_preference': game.quality_preference,
        'priority': game.priority,
        'status': game.status,
        'added_date': game.added_date.isoformat() if game.added_date else None
    } for game in wanted_games])

@web_bp.route('/api/catalog/search')
def search_catalog():
    """Search catalog games"""
    query = request.args.get('q', '')
    platform = request.args.get('platform', '')
    
    catalog_query = GameCatalog.query
    
    if query:
        catalog_query = catalog_query.filter(GameCatalog.title.ilike(f'%{query}%'))
    
    if platform:
        catalog_query = catalog_query.filter_by(platform=platform)
    
    catalog_games = catalog_query.order_by(GameCatalog.title).all()
    
    return jsonify([{
        'id': game.id,
        'title': game.title,
        'platform': game.platform,
        'region': game.region,
        'release_year': game.release_year,
        'description': game.description,
        'genre': game.genre,
        'developer': game.developer,
        'publisher': game.publisher,
        'players': game.players,
        'rating': game.rating
    } for game in catalog_games])

@web_bp.route('/api/platforms')
def get_platforms_list():
    """Get list of platforms for dropdowns"""
    return jsonify(PLATFORMS)

@web_bp.route('/api/colors')
def get_colors():
    """Get color scheme for UI"""
    return jsonify(COLORS)

@web_bp.route('/api/import/scan', methods=['POST'])
def scan_for_roms():
    """Scan directory for ROMs"""
    data = request.get_json()
    directory = data.get('directory', '')
    
    if not directory or not os.path.isdir(directory):
        return jsonify({
            'success': False,
            'message': 'Invalid directory',
            'found_roms': []
        })
    
    # Import here to avoid circular imports
    from services.rom_scanner import ROMScanner
    
    try:
        scanner = ROMScanner(directory)
        found_roms = scanner.scan()
        
        return jsonify({
            'success': True,
            'message': f'Found {len(found_roms)} ROMs',
            'found_roms': found_roms
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error scanning directory: {str(e)}',
            'found_roms': []
        })

@web_bp.route('/api/import/process', methods=['POST'])
def process_roms():
    """Process found ROMs and add to library"""
    data = request.get_json()
    roms_to_import = data.get('roms', [])
    
    if not roms_to_import:
        return jsonify({
            'success': False,
            'message': 'No ROMs to import',
            'imported_count': 0
        })
    
    # Import here to avoid circular imports
    from services.rom_importer import ROMImporter
    
    try:
        importer = ROMImporter()
        results = importer.import_roms(roms_to_import)
        
        return jsonify({
            'success': True,
            'message': f'Imported {results["imported"]} ROMs',
            'imported_count': results['imported'],
            'skipped_count': results['skipped'],
            'failed_count': results['failed'],
            'details': results['details']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error importing ROMs: {str(e)}',
            'imported_count': 0
        })

@web_bp.route('/api/downloads/status')
def get_downloads_status():
    """Get current downloads status"""
    downloads = Download.query.order_by(Download.added_date.desc()).all()
    
    return jsonify([{
        'id': download.id,
        'game_id': download.game_id,
        'torrent_name': download.torrent_name,
        'download_path': download.download_path,
        'size_bytes': download.size_bytes,
        'downloaded_bytes': download.downloaded_bytes,
        'progress': download.progress,
        'status': download.status,
        'added_date': download.added_date.isoformat() if download.added_date else None,
        'completed_date': download.completed_date.isoformat() if download.completed_date else None
    } for download in downloads])