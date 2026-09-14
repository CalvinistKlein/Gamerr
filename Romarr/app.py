import os
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
from routes.upload import upload_bp
from routes.settings import settings_bp
from routes.admin import admin_bp
from services.prowlarr import ProwlarrClient
from services.torrent_client import QBittorrentClient
from services.library_manager import LibraryManager

app = Flask(__name__, static_folder='frontend/dist', static_url_path='/')
CORS(app) # Enable CORS for frontend requests

app.config['DATABASE'] = 'romarr.db'
app.config['LIBRARY_PATH'] = os.path.join(os.getcwd(), 'Library')

# Initialize Managers
library_manager = LibraryManager(app.config['LIBRARY_PATH'])
app.register_blueprint(upload_bp, url_prefix='/api')
app.register_blueprint(settings_bp, url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/api')

# Global state for transient activity and logs (would be DB in larger app)
SYSTEM_ACTIVITIES = []
SYSTEM_LOGS = []

def add_system_log(message, level="INFO"):
    from datetime import datetime
    log_entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "level": level,
        "message": message
    }
    SYSTEM_LOGS.append(log_entry)
    if len(SYSTEM_LOGS) > 100:
        SYSTEM_LOGS.pop(0)
    print(f"[{level}] {message}")

def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            time TEXT NOT NULL,
            unread BOOLEAN DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def clean_title(title):
    """Remove common ROM tags like (USA), (Japan), [Beta], etc. for better matching."""
    import re
    # Remove anything in parentheses or brackets
    cleaned = re.sub(r'\([^)]*\)', '', title)
    cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
    # Remove extra whitespace
    return cleaned.strip()

@app.route('/')
def index():
    return app.send_static_file('index.html')

# Catch-all route to handle React Router in production
@app.errorhandler(404)
def not_found(e):
    if not request.path.startswith('/api'):
        return app.send_static_file('index.html')
    return jsonify({'error': 'Not found'}), 404

# --- Game Discovery APIs ---

@app.route('/api/games', methods=['GET'])
def get_games():
    """Retrieve games from the local database."""
    add_system_log(f"Game search requested: {request.args}")
    conn = get_db_connection()
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    offset = (page - 1) * limit
    
    # Optional filters
    platform_id = request.args.get('platform_id')
    query = request.args.get('query')

    base_sql = """
        SELECT g.id, g.title, g.release_year, p.name as platform_name, w.status as requested_status
        FROM games g 
        LEFT JOIN game_platform_association gpa ON g.id = gpa.game_id 
        LEFT JOIN platforms p ON gpa.platform_id = p.id 
        LEFT JOIN wanted_games w ON g.id = w.game_id
        WHERE 1=1
    """
    params = []

    if platform_id:
        base_sql += " AND p.id = ?"
        params.append(platform_id)
    if query:
        base_sql += " AND g.title LIKE ?"
        params.append(f"%{query}%")
    
    # Default behavior: If searching OR all=true, show all. If browsing, filter for library.
    if request.args.get('all') == 'true' or query:
        pass # Global search
    elif request.args.get('wanted') == 'true':
        base_sql += " AND w.id IS NOT NULL AND (w.status IS NULL OR w.status != 'completed')"
    else:
        # Strict library view
        base_sql += " AND (w.id IS NOT NULL OR EXISTS(SELECT 1 FROM downloads d WHERE d.game_id = g.id))"

    # Ensure unique results per game
    base_sql += " GROUP BY g.id"
    base_sql += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    add_system_log(f"Final SQL: {base_sql} | Params: {params}")
    games = conn.execute(base_sql, params).fetchall()
    conn.close()
    
    return jsonify([dict(ix) for ix in games])

@app.route('/api/games/<int:game_id>', methods=['GET'])
def get_game_details(game_id):
    conn = get_db_connection()
    game = conn.execute("""
        SELECT g.*, p.name as platform_name, w.status as requested_status
        FROM games g
        LEFT JOIN game_platform_association gpa ON g.id = gpa.game_id 
        LEFT JOIN platforms p ON gpa.platform_id = p.id 
        LEFT JOIN wanted_games w ON g.id = w.game_id
        WHERE g.id = ?
    """, (game_id,)).fetchone()
    
    if game is None:
        return jsonify({'error': 'Game not found'}), 404
        
    game_dict = dict(game)
    # Check if we have it in library (simplified check)
    downloads = conn.execute("SELECT id, status FROM downloads WHERE game_id = ?", (game_id,)).fetchall()
    game_dict['in_library'] = any(d['status'] == 'completed' for d in downloads)
    game_dict['active_downloads'] = [dict(d) for d in downloads if d['status'] != 'completed']

    conn.close()
    return jsonify(game_dict)

@app.route('/api/activity', methods=['GET'])
def get_activity():
    """Fetch real-time activity from torrent client and background jobs."""
    from services.config_manager import ConfigManager
    from services.torrent_client import QBittorrentClient
    
    config = ConfigManager().load_settings()
    dl = config.get('downloaders', {})
    
    activities = []
    
    # 1. Fetch from qBittorrent
    if dl.get('qbittorrent_url') and dl.get('qbittorrent_user'):
        client = QBittorrentClient(
            dl['qbittorrent_url'], 
            dl['qbittorrent_user'], 
            dl.get('qbittorrent_pass', '')
        )
        torrents = client.get_torrents()
        for t in torrents:
            activities.append({
                'id': f"torrent_{t['hash'][:8]}",
                'name': f"Downloading: {t['name']}",
                'progress': int(t['progress'] * 100),
                'status': t['state']
            })
            
    # 2. Add system jobs (live system activities)
    activities.extend(SYSTEM_ACTIVITIES)
    
    return jsonify(activities)

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Fetch recent system logs."""
    return jsonify(SYSTEM_LOGS)

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Fetch system notifications from DB."""
    conn = get_db_connection()
    notifications = conn.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return jsonify([dict(n) for n in notifications])

# --- Request APIs ---

@app.route('/api/request', methods=['POST'])
def request_game():
    data = request.json
    game_id = data.get('game_id')
    
    if not game_id:
        return jsonify({'error': 'Game ID is required'}), 400

    conn = get_db_connection()
    game = conn.execute("""
        SELECT g.title, p.name as platform_name 
        FROM games g
        LEFT JOIN game_platform_association gpa ON g.id = gpa.game_id 
        LEFT JOIN platforms p ON gpa.platform_id = p.id 
        WHERE g.id = ?
    """, (game_id,)).fetchone()
    
    if not game:
        conn.close()
        return jsonify({'error': 'Game not found in DB'}), 404

    # Add to wanted list
    cursor = conn.cursor()
    from datetime import datetime
    cursor.execute('''
        INSERT INTO wanted_games (game_id, game_title, platform, status, added_date) 
        VALUES (?, ?, ?, ?, ?)
    ''', (game_id, game['title'], game['platform_name'], 'searching', datetime.now()))
    conn.commit()
    conn.close()

    # Trigger Prowlarr search
    prowlarr_url = os.environ.get('PROWLARR_URL', 'http://localhost:9696')
    prowlarr_api_key = os.environ.get('PROWLARR_API_KEY', '')
    
    if prowlarr_api_key:
        from services.prowlarr import ProwlarrClient
        prowlarr = ProwlarrClient(prowlarr_url, prowlarr_api_key)
        add_system_log(f"Starting Prowlarr search for: {game['title']}")
        results = prowlarr.search(game['title'])
        add_system_log(f"Prowlarr search for {game['title']} found {len(results)} results")

    # Enrich metadata in background (simplified for now, ideally async)
    enrich_game_metadata(game_id, game['title'], game['platform_name'])

    # Add notification
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO notifications (text, time) VALUES (?, ?)", 
                     (f"Requested ROM: {game['title']}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except:
        pass

    return jsonify({'message': f"Request added for {game['title']}", 'status': 'searching'})

def enrich_game_metadata(game_id, title, platform_name):
    """Internal helper to fetch metadata from RAWG and update DB."""
    from services.config_manager import ConfigManager
    from services.rawg import RAWGClient
    
    config = ConfigManager().load_settings()
    api_key = config.get('metadata', {}).get('rawg_api_key')
    
    if not api_key:
        return False
        
    client = RAWGClient(api_key)
    search_title = clean_title(title)
    add_system_log(f"Enriching metadata for: {title} (Searching as: {search_title})")
    rawg_game = client.search_game(search_title, platform_name)
    
    if rawg_game:
        add_system_log(f"Found match on RAWG: {rawg_game['name']} (ID: {rawg_game['id']})")
        details = client.get_game_details(rawg_game['id'])
        if details:
            conn = sqlite3.connect('romarr.db')
            # Update games table with RAWG data
            conn.execute("""
                UPDATE games 
                SET cover_url = ?, 
                    summary = ?, 
                    rating = ?, 
                    release_year = COALESCE(release_year, ?)
                WHERE id = ?
            """, (
                details.get('background_image'), 
                details.get('description_raw'), 
                details.get('rating'),
                details.get('released', '')[:4] if details.get('released') else None,
                game_id
            ))
            conn.commit()
            conn.close()
            add_system_log(f"Successfully enriched metadata for {title}", "SUCCESS")
            return True
    
    add_system_log(f"Failed to find metadata match for: {title}", "WARNING")
    return False

@app.route('/api/games/<int:game_id>/refresh-metadata', methods=['POST'])
def refresh_metadata(game_id):
    conn = get_db_connection()
    game = conn.execute("SELECT title, p.name as platform_name FROM games g LEFT JOIN game_platform_association gpa ON g.id = gpa.game_id LEFT JOIN platforms p ON gpa.platform_id = p.id WHERE g.id = ?", (game_id,)).fetchone()
    conn.close()
    
    if not game:
        return jsonify({'error': 'Game not found'}), 404
        
    success = enrich_game_metadata(game_id, game['title'], game['platform_name'])
    if success:
        return jsonify({'message': 'Metadata refreshed successfully'}), 200
    return jsonify({'error': 'Failed to enrich metadata. Check API key or game match.'}), 500

@app.route('/api/games/batch', methods=['DELETE'])
def delete_games_batch():
    data = request.json
    game_ids = data.get('game_ids', [])
    
    if not game_ids:
        return jsonify({'error': 'No game IDs provided'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        placeholders = ','.join(['?'] * len(game_ids))
        
        # 1. Delete from games
        cursor.execute(f"DELETE FROM games WHERE id IN ({placeholders})", game_ids)
        
        # 2. Delete from associations
        cursor.execute(f"DELETE FROM game_platform_association WHERE game_id IN ({placeholders})", game_ids)
        
        # 3. Delete from wanted_games
        cursor.execute(f"DELETE FROM wanted_games WHERE game_id IN ({placeholders})", game_ids)
        
        # 4. Delete from downloads (if applicable)
        cursor.execute(f"DELETE FROM downloads WHERE game_id IN ({placeholders})", game_ids)

        conn.commit()
        return jsonify({'message': f'Successfully deleted {len(game_ids)} games'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(debug=True, port=8000, host='0.0.0.0')
