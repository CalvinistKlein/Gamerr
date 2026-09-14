import os
import shutil
import sqlite3
import zipfile
import re
import xml.etree.ElementTree as ET
import requests
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename

admin_bp = Blueprint('admin', __name__)
DB_PATH = 'romarr.db'
BACKUP_DIR = 'backups'
TEMP_DIR = 'temp_extract'

if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# Global progress tracking for ingestion
INGESTION_PROGRESS = {"status": "idle", "progress": 0, "message": ""}

def update_progress(progress, message, status="busy"):
    global INGESTION_PROGRESS
    INGESTION_PROGRESS["progress"] = progress
    INGESTION_PROGRESS["message"] = message
    INGESTION_PROGRESS["status"] = status

def is_sqlite(file_path):
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)
            return header == b'SQLite format 3\x00'
    except:
        return False

def detect_dat_platform(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(1000)
            if 'clrmamepro (' in content:
                match = re.search(r'name\s+"([^"]+)"', content)
                return match.group(1) if match else "Unknown DAT"
    except:
        pass
    return None

def is_mame_xml(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(500)
            return '<mame' in content.lower() or '<machine' in content.lower()
    except:
        return False

@admin_bp.route('/admin/backup/analyze', methods=['POST'])
def analyze_upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(BACKUP_DIR, filename)
    file.save(filepath)

    result = {
        "filename": filename,
        "type": "Unknown",
        "platform": None,
        "details": "",
        "temp_path": filepath
    }

    try:
        # 1. Check if it's a zip and peek inside
        if filename.endswith('.zip'):
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                for name in zip_ref.namelist()[:10]: # Check first 10 files
                    if name.endswith('.db'):
                        result["type"] = "Romarr Backup (Zipped)"
                        break
                    if name.endswith('.dat'):
                        # Extract temporarily to check platform
                        zip_ref.extract(name, TEMP_DIR)
                        platform = detect_dat_platform(os.path.join(TEMP_DIR, name))
                        result["type"] = "LibRetro/No-Intro DAT (Zipped)"
                        result["platform"] = platform
                        break
        
        # 2. Direct file checks
        elif is_sqlite(filepath):
            result["type"] = "Romarr Backup (Direct)"
        elif detect_dat_platform(filepath):
            result["type"] = "LibRetro/No-Intro DAT"
            result["platform"] = detect_dat_platform(filepath)
        elif is_mame_xml(filepath):
            result["type"] = "MAME XML"
            result["platform"] = "Arcade"

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/admin/backup/apply', methods=['POST'])
def apply_upload():
    data = request.json
    temp_path = data.get('temp_path')
    file_type = data.get('type', '')
    platform = data.get('platform')
    
    if not temp_path or not os.path.exists(temp_path):
        return jsonify({"error": "Invalid or missing file reference"}), 400

    from services.database_builder import DatabaseBuilder
    builder = DatabaseBuilder()

    try:
        # Handle Romarr Backups (SQLite)
        if "Backup" in file_type:
            if temp_path.endswith('.zip'):
                with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                    for name in zip_ref.namelist():
                        if name.endswith('.db'):
                            zip_ref.extract(name, TEMP_DIR)
                            os.replace(os.path.join(TEMP_DIR, name), DB_PATH)
                            break
            else:
                shutil.copy2(temp_path, DB_PATH)
            return jsonify({"message": "Database restored successfully"}), 200
        
        # Handle LibRetro/No-Intro DATs
        elif "DAT" in file_type:
            target_file = temp_path
            if temp_path.endswith('.zip'):
                with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                    for name in zip_ref.namelist():
                        if name.endswith('.dat'):
                            zip_ref.extract(name, TEMP_DIR)
                            target_file = os.path.join(TEMP_DIR, name)
                            break
            
            update_progress(10, f"Starting import for {platform}...")
            # Note: DatabaseBuilder would ideally be updated to call update_progress but for now we simulate
            success = builder.parse_nointro_dat(target_file, platform or "Unknown")
            update_progress(100, "Import complete", "idle")
            if success:
                return jsonify({"message": f"Successfully imported {platform} database"}), 200
            else:
                return jsonify({"error": "Failed to parse DAT file"}), 500

        # Handle MAME XML
        elif "MAME" in file_type:
            target_file = temp_path
            if temp_path.endswith('.zip'):
                with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                    for name in zip_ref.namelist():
                        if name.endswith('.xml'):
                            zip_ref.extract(name, TEMP_DIR)
                            target_file = os.path.join(TEMP_DIR, name)
                            break
            
            update_progress(10, "Starting MAME XML import...")
            success = builder.parse_mame_xml(target_file)
            update_progress(100, "Import complete", "idle")
            if success:
                return jsonify({"message": "Successfully imported MAME database"}), 200
            else:
                return jsonify({"error": "Failed to parse MAME XML"}), 500

        return jsonify({"error": "Unsupported file type for import"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(TEMP_DIR):
            for f in os.listdir(TEMP_DIR):
                os.remove(os.path.join(TEMP_DIR, f))

@admin_bp.route('/admin/rebuild', methods=['POST'])
def rebuild_db():
    data = request.json
    rebuild_type = data.get('type')
    print(f"Triggering {rebuild_type} rebuild...")
    return jsonify({"message": f"{rebuild_type} rebuild triggered in background"}), 202

@admin_bp.route('/admin/backup/download', methods=['GET'])
def download_backup():
    if not os.path.exists(DB_PATH):
        return jsonify({"error": "Database not found"}), 404
    return send_file(DB_PATH, as_attachment=True, download_name='romarr_backup.db')

@admin_bp.route('/admin/test/prowlarr', methods=['POST'])
def test_prowlarr():
    data = request.json
    url = data.get('url', '').rstrip('/')
    api_key = data.get('api_key')
    
    if not url or not api_key:
        return jsonify({"success": False, "message": "Missing URL or API Key"}), 400
        
    try:
        # Prowlarr system status endpoint
        test_url = f"{url}/api/v1/system/status"
        response = requests.get(test_url, params={"apikey": api_key}, timeout=10)
        
        if response.status_code == 200:
            return jsonify({"success": True, "message": "Successfully connected to Prowlarr"}), 200
        elif response.status_code == 401:
            return jsonify({"success": False, "message": "Authentication failed: Invalid API Key"}), 401
        else:
            return jsonify({"success": False, "message": f"Prowlarr returned status: {response.status_code}"}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Connection failed: {str(e)}"}), 500

@admin_bp.route('/admin/test/qbittorrent', methods=['POST'])
def test_qbittorrent():
    data = request.json
    url = data.get('url', '').rstrip('/')
    user = data.get('user')
    password = data.get('pass')
    
    if not url:
        return jsonify({"success": False, "message": "Missing URL"}), 400
        
    try:
        # qBittorrent login endpoint
        login_url = f"{url}/api/v2/auth/login"
        payload = {'username': user, 'password': password}
        response = requests.post(login_url, data=payload, timeout=10)
        
        if response.status_code == 200:
            if "Ok" in response.text:
                return jsonify({"success": True, "message": "Successfully authenticated with qBittorrent"}), 200
            else:
                return jsonify({"success": False, "message": "Login failed: check credentials"}), 401
        else:
            return jsonify({"success": False, "message": f"qBittorrent returned status: {response.status_code}"}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Connection failed: {str(e)}"}), 500

@admin_bp.route('/admin/test/rawg', methods=['POST'])
def test_rawg():
    data = request.json
    api_key = data.get('api_key')
    
    if not api_key:
        return jsonify({"success": False, "message": "Missing API Key"}), 400
        
    try:
        # RAWG test endpoint
        test_url = "https://api.rawg.io/api/games"
        response = requests.get(test_url, params={"key": api_key, "page_size": 1}, timeout=10)
        
        if response.status_code == 200:
            return jsonify({"success": True, "message": "Successfully connected to RAWG"}), 200
        elif response.status_code == 401:
            return jsonify({"success": False, "message": "Invalid API Key"}), 401
        else:
            return jsonify({"success": False, "message": f"RAWG returned status: {response.status_code}"}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Connection failed: {str(e)}"}), 500

@admin_bp.route('/admin/progress', methods=['GET'])
def get_progress():
    return jsonify(INGESTION_PROGRESS)

@admin_bp.route('/admin/reset_db', methods=['POST'])
def reset_db():
    """Wipe all games and platforms from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Use a list of tables to clear
        tables = ['games', 'platforms', 'game_platform_association', 'wanted_games', 'downloads']
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
        conn.commit()
        conn.close()
        return jsonify({'message': 'Database wiped successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
