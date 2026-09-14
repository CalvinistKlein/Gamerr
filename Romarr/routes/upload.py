import os
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from services.database_builder import DatabaseBuilder

upload_bp = Blueprint('upload', __name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allow common ROM and image extensions
ALLOWED_EXTENSIONS = {'zip', '7z', 'rar', 'iso', 'bin', 'cue', 'md', 'sfc', 'nes', 'gba', 'xml', 'dat'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route('/upload/rom', methods=['POST'])
def upload_rom():
    """Endpoint for uploading multiple ROM files."""
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files part'}), 400
    
    files = request.files.getlist('files[]')
    
    if not files or files[0].filename == '':
        return jsonify({'error': 'No selected files'}), 400

    uploaded_files = []
    from app import library_manager, add_system_log, get_db_connection
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            # Identify title (removing extension)
            base_name, _ = os.path.splitext(filename)
            add_system_log(f"ROM uploaded: {filename}. Testing match...")
            
            # Simple organization: move to 'Unsorted'
            success, dest = library_manager.import_rom(filepath, "Unsorted", base_name)
            if success:
                uploaded_files.append(filename)
                add_system_log(f"ROM organized to: {dest}", "SUCCESS")
                
                # Match against DB
                conn = get_db_connection()
                try:
                    # Look for exact or fuzzy match
                    game = conn.execute("SELECT id FROM games WHERE title = ?", (base_name,)).fetchone()
                    if not game:
                        game = conn.execute("SELECT id FROM games WHERE title LIKE ?", (f"%{base_name}%",)).fetchone()
                    
                    if game:
                        game_id = game['id']
                        # Mark as completed in wanted_games
                        conn.execute("INSERT OR REPLACE INTO wanted_games (game_id, status) VALUES (?, 'completed')", (game_id,))
                        conn.commit()
                        add_system_log(f"Linked {filename} to game ID {game_id}", "SUCCESS")
                except Exception as db_err:
                    add_system_log(f"DB match failed: {db_err}", "WARNING")
                finally:
                    conn.close()
            else:
                add_system_log(f"Failed to organize {filename}: {dest}", "WARNING")

    return jsonify({
        'message': 'Files successfully uploaded',
        'files': uploaded_files
    }), 201

@upload_bp.route('/admin/rebuild_db', methods=['POST'])
def rebuild_database():
    """Endpoint to trigger a localized rebuild of romarr.db"""
    data = request.json
    source_type = data.get('type')
    filepath = data.get('filepath')
    platform = data.get('platform')

    if not source_type or not filepath:
        return jsonify({'error': 'Missing type or filepath'}), 400

    if not os.path.exists(filepath):
        return jsonify({'error': f'File not found: {filepath}'}), 404

    builder = DatabaseBuilder()
    success = False

    if source_type == 'mame':
        success = builder.parse_mame_xml(filepath)
    elif source_type == 'nointro':
        if not platform:
            return jsonify({'error': 'Platform required for No-Intro DATs'}), 400
        success = builder.parse_nointro_dat(filepath, platform)
    else:
        return jsonify({'error': 'Invalid source type. Use "mame" or "nointro"'}), 400

    if success:
        return jsonify({'message': f'Successfully rebuilt DB using {source_type}'}), 200
    else:
        return jsonify({'error': 'Database rebuild failed'}), 500
