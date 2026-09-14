import requests

class QBittorrentClient:
    def __init__(self, host, username, password):
        self.host = host.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.authenticated = False

    def authenticate(self):
        """Login to qBittorrent Web UI."""
        try:
            response = self.session.post(
                f"{self.host}/api/v2/auth/login",
                data={'username': self.username, 'password': self.password},
                timeout=5
            )
            # qBittorrent returns 'Ok.' on successful login
            if response.text == 'Ok.':
                self.authenticated = True
                return True, "Authenticated"
            return False, f"Login failed: {response.text}"
        except requests.exceptions.RequestException as e:
            return False, str(e)

    def add_torrent(self, torrent_url, save_path=None, category=None):
        """Add a torrent by URL."""
        if not self.authenticated:
            success, _ = self.authenticate()
            if not success:
                return False, "Not authenticated"

        data = {'urls': torrent_url}
        if save_path:
            data['savepath'] = save_path
        if category:
            data['category'] = category

        try:
            response = self.session.post(
                f"{self.host}/api/v2/torrents/add",
                data=data,
                timeout=5
            )
            if response.text == 'Ok.':
                return True, "Torrent added successfully"
            return False, f"Failed to add torrent: {response.text}"
        except requests.exceptions.RequestException as e:
            return False, str(e)

    def get_torrents(self, category=None, filter_status=None):
        """Get a list of torrents, optionally filtered."""
        if not self.authenticated:
            success, _ = self.authenticate()
            if not success:
                return []

        params = {}
        if category:
            params['category'] = category
        if filter_status:
            params['filter'] = filter_status

        try:
            response = self.session.get(
                f"{self.host}/api/v2/torrents/info",
                params=params,
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting torrents: {e}")
            return []
