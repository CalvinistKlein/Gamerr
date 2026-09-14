"""
API routes for Romarr
"""

from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

from models.unified_schema import Game
from models.unified_schema import WantedGame
from models.unified_schema import Download
from models.settings import Settings
from models.notification import Notification
from models.constants import (
    GAME_STATUS_WANTED, WANTED_STATUS_PENDING,
    DOWNLOAD_STATUS_QUEUED
)
from config.constants import PLATFORMS, REGIONS

import os
import shutil
api_bp = Blueprint('api', __name__)

# Games API
@api_bp.route('/games', methods=['GET'])
def get_games():
    """Get all games"""
    games = Game.query.all()
    return jsonify([game.to_dict() for game in games])

@api_bp.route('/games/<int:game_id>', methods=['GET'])
def get_game(game_id):
    """Get a specific game"""
    game = Game.query.get_or_404(game_id)
    return jsonify(game.to_dict())

@api_bp.route('/games', methods=['POST'])
def create_game():
    """Create a new game"""
    data = request.get_json()
    
    game = Game(
        title=data.get('title'),
        platform=data.get('platform'),
        region=data.get('region'),
        release_year=data.get('release_year'),
        file_path=data.get('file_path'),
        file_size=data.get('file_size'),
        status=data.get('status', 'library')
    )
    
    from extensions import db
    db.session.add(game)
    db.session.commit()
    
    return jsonify(game.to_dict()), 201

@api_bp.route('/games/<int:game_id>', methods=['PUT'])
def update_game(game_id):
    """Update a game"""
    game = Game.query.get_or_404(game_id)
    data = request.get_json()
    
    for key, value in data.items():
        if hasattr(game, key):
            setattr(game, key, value)
    
    from extensions import db
    db.session.commit()
    return jsonify(game.to_dict())

@api_bp.route('/games/<int:game_id>', methods=['DELETE'])
def delete_game(game_id):
    """Delete a game"""
    game = Game.query.get_or_404(game_id)
    from extensions import db
    db.session.delete(game)
    db.session.commit()
    return jsonify({'message': 'Game deleted'})

# Wanted Games API
@api_bp.route('/wanted', methods=['GET'])
def get_wanted_games():
    """Get all wanted games"""
    wanted_games = WantedGame.query.all()
    return jsonify([game.to_dict() for game in wanted_games])

@api_bp.route('/wanted', methods=['POST'])
def create_wanted_game():
    """Add a game to wanted list"""
    data = request.get_json()
    
    # Also create a game entry with wanted status
    game = Game(
        title=data.get('game_title'),
        platform=data.get('platform'),
        region=data.get('region_preference'),
        status=GAME_STATUS_WANTED
    )
    from extensions import db
    db.session.add(game)
    db.session.flush()  # Get the game ID
    
    wanted_game = WantedGame(
        game_title=data.get('game_title'),
        platform=data.get('platform'),
        region_preference=data.get('region_preference'),
        quality_preference=data.get('quality_preference'),
        priority=data.get('priority', 1)
    )
    
    db.session.add(wanted_game)
    db.session.commit()
    
    return jsonify(wanted_game.to_dict()), 201

@api_bp.route('/wanted/<int:wanted_id>', methods=['DELETE'])
def delete_wanted_game(wanted_id):
    """Remove a game from wanted list"""
    wanted_game = WantedGame.query.get_or_404(wanted_id)
    from extensions import db
    db.session.delete(wanted_game)
    db.session.commit()
    return jsonify({'message': 'Wanted game removed'})

# Downloads API
@api_bp.route('/downloads', methods=['GET'])
def get_downloads():
    """Get all downloads"""
    downloads = Download.query.all()
    return jsonify([download.to_dict() for download in downloads])

@api_bp.route('/downloads/active', methods=['GET'])
def get_active_downloads():
    """Get active downloads"""
    downloads = Download.get_active()
    return jsonify([download.to_dict() for download in downloads])

@api_bp.route('/downloads', methods=['POST'])
def create_download():
    """Add a new download"""
    data = request.get_json()
    
    download = Download(
        game_id=data.get('game_id'),
        torrent_hash=data.get('torrent_hash'),
        torrent_name=data.get('torrent_name'),
        download_path=data.get('download_path'),
        size_bytes=data.get('size_bytes'),
        status=DOWNLOAD_STATUS_QUEUED
    )
    
    from extensions import db
    db.session.add(download)
    db.session.commit()
    
    return jsonify(download.to_dict()), 201

# Utility endpoints
@api_bp.route('/platforms', methods=['GET'])
def get_platforms():
    """Get list of supported platforms"""
    return jsonify(PLATFORMS)

@api_bp.route('/regions', methods=['GET'])
def get_regions():
    """Get list of supported regions"""
    return jsonify(REGIONS)

@api_bp.route('/search', methods=['POST'])
def search_games():
    """
    Hybrid game search: local DB catalog + live IGDB metadata + Prowlarr torrents.
    Cover images for results are lazily cached on first search.
    """
    data = request.get_json()
    query = data.get('query', '')
    platform = data.get('platform', '')
    page = data.get('page', 1)
    per_page = data.get('per_page', 20)

    if not query:
        return jsonify({'error': 'Query parameter is required', 'results': []}), 400

    from services.search import MetadataSearchService, SearchService

    # 1. Hybrid metadata search (local catalog + IGDB enrichment)
    metadata = MetadataSearchService.search(
        query=query,
        platform=platform or None,
        page=page,
        per_page=per_page
    )

    # 2. Prowlarr torrent search — non-fatal if offline/unconfigured
    torrent_results = []
    try:
        torrent_results = SearchService.search_games(query, platform)
    except Exception:
        pass

    return jsonify({
        'results': metadata['results'],
        'torrent_results': torrent_results,
        'query': query,
        'platform': platform,
        'page': page,
        'per_page': per_page,
        'total_local': metadata['total_local'],
        'igdb_available': metadata['igdb_available'],
        'rawg_available': metadata['rawg_available'],
        'count': len(metadata['results'])
    })


@api_bp.route('/search/catalog', methods=['GET'])
def search_catalog_api():
    """
    Paginated catalog search (local DB only). Hard-capped at 100 rows per page
    to prevent loading millions of rows at once (Bug 7 fix).
    """
    query = request.args.get('q', '')
    platform = request.args.get('platform', '')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 24, type=int), 100)

    from models.unified_schema import GameCatalog
    q = GameCatalog.query
    if query:
        q = q.filter(GameCatalog.title.ilike(f'%{query}%'))
    if platform:
        q = q.filter_by(platform=platform)

    total = q.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    items = q.order_by(GameCatalog.title) \
              .offset((page - 1) * per_page) \
              .limit(per_page) \
              .all()

    return jsonify({
        'results': [g.to_dict() for g in items],
        'query': query,
        'platform': platform,
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages
    })


@api_bp.route('/image-cache/<entity_type>/<int:entity_id>', methods=['GET'])
def get_cached_image(entity_type, entity_id):
    """
    Serve a cached cover/screenshot image for any entity.
    If ?url=<remote_url> is provided, download and cache it first.
    ?image_type= defaults to 'cover'.
    """
    from flask import redirect
    from services.image_cache import get_or_fetch, get_cached_url

    image_type = request.args.get('image_type', 'cover')
    remote_url = request.args.get('url', '')

    if remote_url:
        local_url = get_or_fetch(
            url=remote_url,
            entity_type=entity_type,
            entity_id=entity_id,
            image_type=image_type
        )
        if local_url:
            return redirect(local_url)
        return jsonify({'error': 'Failed to cache image'}), 502

    cached = get_cached_url(entity_type, entity_id, image_type)
    if cached:
        return redirect(cached)

    return jsonify({'error': 'No cached image found'}), 404

@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    from models.unified_schema import Game, WantedGame, Download
    
    try:
        # Get storage info
        roms_path = os.environ.get('ROMS_PATH', '/data/roms')
        dir_size_gb = 0
        if os.path.exists(roms_path):
            dir_size = 0
            for dirpath, dirnames, filenames in os.walk(roms_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        dir_size += os.path.getsize(fp)
            dir_size_gb = round(dir_size / (1024**3), 2)

        return jsonify({
            'library_count': Game.get_library_count() if hasattr(Game, 'get_library_count') else Game.query.count(),
            'wanted_count': WantedGame.get_active_count() if hasattr(WantedGame, 'get_active_count') else WantedGame.query.count(),
            'active_downloads_count': len(Download.get_active()) if hasattr(Download, 'get_active') else Download.query.count(),
            'storage_used': f"{dir_size_gb} GB",
            'storage_gb': dir_size_gb
        })
    except Exception as e:
        print(f"Error in /api/stats: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'romarr',
        'version': '0.1.0',
        'timestamp': datetime.utcnow().isoformat()
    })

@api_bp.route('/system/storage', methods=['GET'])
def get_storage_info():
    """Get disk usage info for the ROMs directory"""
    roms_path = os.environ.get('ROMS_PATH', '/data/roms')
    
    try:
        # Get total/used/free for the volume
        total, used, free = shutil.disk_usage(roms_path)
        
        # Get actual size of the roms directory specifically
        dir_size = 0
        if os.path.exists(roms_path):
            for dirpath, dirnames, filenames in os.walk(roms_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        dir_size += os.path.getsize(fp)
        
        return jsonify({
            'total': total,
            'used': used,
            'free': free,
            'roms_dir_size': dir_size,
            'total_gb': round(total / (1024**3), 2),
            'used_gb': round(used / (1024**3), 2),
            'free_gb': round(free / (1024**3), 2),
            'roms_gb': round(dir_size / (1024**3), 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Settings API
@api_bp.route('/settings', methods=['GET'])
def get_settings():
    """Get all settings"""
    settings = Settings.get_all()
    return jsonify(settings)

@api_bp.route('/settings', methods=['POST'])
def save_settings():
    """Save multiple settings"""
    data = request.get_json()
    settings = data.get('settings', {})
    category = data.get('category', 'general')
    
    for key, value in settings.items():
        Settings.set(key, value, category)
    
    return jsonify({
        'success': True,
        'message': 'Settings saved successfully',
        'saved_count': len(settings)
    })

@api_bp.route('/settings/test/prowlarr', methods=['POST'])
def test_prowlarr_connection():
    """Test Prowlarr connection"""
    data = request.get_json()
    url = data.get('prowlarr_url', '')
    api_key = data.get('prowlarr_api_key', '')

    import requests
    try:
        test_url = f"{url}/api/v1/system/status"
        headers = {'X-Api-Key': api_key} if api_key else {}
        response = requests.get(test_url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': 'Prowlarr connection successful',
                'version': response.json().get('version', 'unknown')
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Prowlarr returned status code {response.status_code}'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to connect to Prowlarr: {str(e)}'
        })

@api_bp.route('/settings/test/qbittorrent', methods=['POST'])
def test_qbittorrent_connection():
    """Test qBittorrent connection"""
    data = request.get_json()
    url = data.get('qbittorrent_url', '')
    username = data.get('qbittorrent_username', '')
    password = data.get('qbittorrent_password', '')

    try:
        from qbittorrent import Client
        qb = Client(url)
        qb.login(username, password)
        
        # Try to get version info
        version = qb.qbittorrent_version
        return jsonify({
            'success': True,
            'message': 'qBittorrent connection successful',
            'version': version
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to connect to qBittorrent: {str(e)}'
        })

@api_bp.route('/settings/test/igdb', methods=['POST'])
def test_igdb_connection():
    """Test IGDB connection"""
    data = request.get_json()
    client_id = data.get('igdb_client_id', '')
    client_secret = data.get('igdb_client_secret', '')
    
    if not client_id or not client_secret:
        return jsonify({'success': False, 'message': 'Client ID and Secret are required'})
        
    try:
        from services.igdb_client import IGDBClient
        client = IGDBClient(client_id, client_secret)
        # Just getting the token handles the test
        token = client._get_token()
        if token:
            return jsonify({'success': True, 'message': 'IGDB connected successfully'})
        return jsonify({'success': False, 'message': 'Failed to get IGDB token'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'IGDB connection failed: {str(e)}'})

@api_bp.route('/settings/test/rawg', methods=['POST'])
def test_rawg_connection():
    """Test RAWG connection"""
    data = request.get_json()
    api_key = data.get('rawg_api_key', '')
    
    if not api_key:
        return jsonify({'success': False, 'message': 'API Key is required'})
        
    try:
        from services.rawg_client import RAWGClient
        client = RAWGClient(api_key)
        # Search for something simple to test
        results = client.search_game("test", max_results=1)
        if isinstance(results, list):
            return jsonify({'success': True, 'message': 'RAWG connected successfully'})
        return jsonify({'success': False, 'message': 'RAWG returned invalid data'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'RAWG connection failed: {str(e)}'})

@api_bp.route('/catalog/<int:catalog_id>/add-to-wanted', methods=['POST'])
def add_catalog_to_wanted(catalog_id):
    """Add a catalog game to wanted list"""
    from models.unified_schema import GameCatalog
    from models.unified_schema import WantedGame
    from models.constants import WANTED_STATUS_PENDING
    
    # Get the catalog game
    catalog_game = GameCatalog.query.get_or_404(catalog_id)
    
    # Check if already in wanted list
    existing_wanted = WantedGame.query.filter_by(
        game_title=catalog_game.title,
        platform=catalog_game.platform
    ).first()
    
    if existing_wanted:
        return jsonify({
            'success': False,
            'message': 'Game is already in wanted list',
            'wanted_id': existing_wanted.id
        }), 409
    
    # Add to wanted list
    wanted_game = WantedGame(
        game_title=catalog_game.title,
        platform=catalog_game.platform,
        region_preference=catalog_game.region,
        quality_preference='preferred',  # Default quality
        priority=1,
        status=WANTED_STATUS_PENDING
    )
    
    from extensions import db
    db.session.add(wanted_game)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Added {catalog_game.title} to wanted list',
        'wanted_id': wanted_game.id,
        'game': wanted_game.to_dict()
    }), 201

@api_bp.route('/settings/network/share-url', methods=['GET'])
def get_network_share_url():
    """Get network share URL based on current settings"""
    network_config = Settings.get_network_config()
    share_type = network_config.get('network_share_type', 'nfs')
    share_path = network_config.get('network_share_path', '/data/roms')
    
    # This would be the actual server hostname/IP
    import socket
    hostname = socket.gethostname()
    
    share_url = ''
    if share_type == 'nfs':
        share_url = f'nfs://{hostname}:2049{share_path}'
    elif share_type == 'smb':
        share_url = f'smb://{hostname}/roms'
    elif share_type == 'webdav':
        share_url = f'http://{hostname}:5000/webdav{share_path}'
    
    return jsonify({
        'share_url': share_url,
        'share_type': share_type,
        'hostname': hostname
    })


# Notifications API
@api_bp.route('/notifications', methods=['GET'])
def get_notifications():
    """Get recent notifications"""
    limit = request.args.get('limit', 10, type=int)
    notifications = Notification.get_recent(limit=limit)
    return jsonify([n.to_dict() for n in notifications])


@api_bp.route('/notifications/unread/count', methods=['GET'])
def get_unread_notification_count():
    """Get count of unread notifications"""
    count = Notification.get_unread_count()
    return jsonify({'count': count})


@api_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
def mark_notification_as_read(notification_id):
    """Mark a notification as read"""
    notification = Notification.query.get_or_404(notification_id)
    notification.mark_as_read()
    return jsonify({'success': True})


@api_bp.route('/notifications/read/all', methods=['POST'])
def mark_all_notifications_as_read():
    """Mark all notifications as read"""
    count = Notification.mark_all_as_read()
    return jsonify({'success': True, 'count': count})
# Database Management Tasks
import threading
import uuid
from datetime import datetime

# Global dictionary to store task status
import_tasks = {}
import_tasks_lock = threading.Lock()

def cleanup_old_tasks():
    """Remove completed or failed tasks older than 1 hour"""
    now = datetime.now()
    with import_tasks_lock:
        to_delete = []
        for tid, task in import_tasks.items():
            if task['status'] in ['completed', 'failed']:
                start_time = datetime.fromisoformat(task['start_time'])
                if (now - start_time).total_seconds() > 3600:
                    to_delete.append(tid)
        for tid in to_delete:
            del import_tasks[tid]

@api_bp.route('/database/import', methods=['POST'])
def import_database_endpoint():
    """Import a new database file (.db, .db.gz, or .rommar)"""
    cleanup_old_tasks()
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part in the request'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected for uploading'}), 400
        
    if not (file.filename.endswith('.db') or file.filename.endswith('.db.gz') or file.filename.endswith('.rommar')):
        return jsonify({'success': False, 'message': 'Invalid file format. Must be .db, .db.gz, or .rommar'}), 400

    import os
    import tempfile
    
    # Save the file to a temporary location
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, file.filename)
    file.save(temp_path)
    
    task_id = str(uuid.uuid4())
    with import_tasks_lock:
        import_tasks[task_id] = {
            'status': 'starting',
            'progress': 0,
            'message': 'Preparing import...',
            'filename': file.filename,
            'start_time': datetime.now().isoformat()
        }
    
    # Capture the current app object to use in the background thread
    # (avoids calling create_app() again which re-runs all startup side-effects)
    app = current_app._get_current_object()

    def run_import(tid, path, app_instance):
        from services.automation import automation_service
        from scripts.database_manager import import_database
        from extensions import db
        
        try:
            with app_instance.app_context():
                with import_tasks_lock:
                    import_tasks[tid]['status'] = 'installing'
                
                def progress_callback(percent, msg):
                    with import_tasks_lock:
                        if tid in import_tasks:
                            import_tasks[tid]['progress'] = percent
                            import_tasks[tid]['message'] = msg
                
                # Pause automation service and close active DB sessions to release locks
                automation_service.stop()
                db.session.remove()
                
                target_db_path = os.path.join(os.getcwd(), 'instance', 'romarr.db')
                
                # Import it using the manager script's function
                success = import_database(path, target_db_path, progress_callback=progress_callback)
                
                with import_tasks_lock:
                    if success:
                        import_tasks[tid]['status'] = 'completed'
                        import_tasks[tid]['progress'] = 100
                        import_tasks[tid]['message'] = 'Database imported successfully'
                    else:
                        import_tasks[tid]['status'] = 'failed'
                        import_tasks[tid]['message'] = 'Failed to import the database file'
        except Exception as e:
            with import_tasks_lock:
                if tid in import_tasks:
                    import_tasks[tid]['status'] = 'failed'
                    import_tasks[tid]['message'] = f'System error: {str(e)}'
            print(f"Import task {tid} failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up the temp file and restart the services
            if os.path.exists(path):
                os.remove(path)
            automation_service.start()

    thread = threading.Thread(target=run_import, args=(task_id, temp_path, app))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True, 
        'message': 'Upload successful, import started',
        'task_id': task_id
    }), 202

@api_bp.route('/database/import/status/<task_id>', methods=['GET'])
def get_import_status(task_id):
    """Get the status of a database import task"""
    with import_tasks_lock:
        task = import_tasks.get(task_id)
        if not task:
            return jsonify({'success': False, 'message': 'Task not found'}), 404
        return jsonify(task)

@api_bp.route('/database/delete', methods=['DELETE'])
def delete_database_endpoint():
    """Wipe the database and reset to a clean state"""
    from services.automation import automation_service
    from models.settings import Settings
    
    try:
        from extensions import db
        # Pause background tasks to drop the database safely
        automation_service.stop()
        db.session.remove()
        
        # Drop and recreate tables
        db.drop_all()
        db.create_all()
        
        # Re-initialize basic metadata
        Settings.initialize_defaults()
        
        return jsonify({'success': True, 'message': 'Database wiped and re-initialized successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to wipe database: {str(e)}'}), 500
    finally:
        automation_service.start()
