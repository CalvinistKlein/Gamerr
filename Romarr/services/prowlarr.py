import requests

class ProwlarrClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {'X-Api-Key': self.api_key}

    def test_connection(self):
        """Test connection to Prowlarr."""
        try:
            response = requests.get(f"{self.base_url}/api/v1/system/status", headers=self.headers, timeout=5)
            response.raise_for_status()
            return True, "Connection successful"
        except requests.exceptions.RequestException as e:
            return False, str(e)

    def search(self, query, categories=None):
        """Search Prowlarr for a query."""
        params = {'query': query, 'type': 'search'}
        if categories:
            params['categories'] = categories
            
        try:
            response = requests.get(f"{self.base_url}/api/v1/search", headers=self.headers, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Prowlarr search error: {e}")
            return []

    def get_indexers(self):
        """Get configured indexers."""
        try:
            response = requests.get(f"{self.base_url}/api/v1/indexer", headers=self.headers, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Prowlarr get_indexers error: {e}")
            return []
