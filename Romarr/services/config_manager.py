import os
import json

class ConfigManager:
    def __init__(self, config_dir='config', config_file='settings.json'):
        self.config_dir = config_dir
        self.config_file = os.path.join(self.config_dir, config_file)
        self.default_settings = {
            "ui": {
                "language": "en-US",
                "date_format": "YYYY-MM-DD",
                "time_format": "HH:mm",
                "first_day_of_week": 1
            },
            "media": {
                "naming_convention": "{Platform}/{Title} ({Year})",
                "rescan_frequency": 60,
                "recycle_bin": False,
                "chmod": "0644",
                "chown": ""
            },
            "security": {
                "api_key": "",
                "auth_enabled": False
            },
            "indexers": {
                "prowlarr_url": "http://localhost:9696",
                "prowlarr_api_key": ""
            },
            "downloaders": {
                "qbittorrent_url": "http://localhost:8080",
                "qbittorrent_user": "admin",
                "qbittorrent_pass": "adminadmin"
            },
            "metadata": {
                "rawg_api_key": "",
                "prefer_external_data": True
            }
        }
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        
        if not os.path.exists(self.config_file):
            self.save_settings(self.default_settings)

    def load_settings(self):
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.default_settings

    def save_settings(self, settings):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(settings, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def update_setting(self, category, key, value):
        settings = self.load_settings()
        if category in settings:
            settings[category][key] = value
            return self.save_settings(settings)
        return False
