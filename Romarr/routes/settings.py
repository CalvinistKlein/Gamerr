from flask import Blueprint, request, jsonify
from services.config_manager import ConfigManager

settings_bp = Blueprint('settings', __name__)
config_manager = ConfigManager()

@settings_bp.route('/settings', methods=['GET'])
def get_settings():
    return jsonify(config_manager.load_settings())

@settings_bp.route('/settings', methods=['POST'])
def update_settings():
    data = request.json
    if config_manager.save_settings(data):
        return jsonify({"message": "Settings saved successfully"}), 200
    return jsonify({"error": "Failed to save settings"}), 500

@settings_bp.route('/settings/<category>/<key>', methods=['PATCH'])
def update_setting_item(category, key):
    value = request.json.get('value')
    if config_manager.update_setting(category, key, value):
        return jsonify({"message": "Setting updated"}), 200
    return jsonify({"error": "Invalid category or failed update"}), 400
