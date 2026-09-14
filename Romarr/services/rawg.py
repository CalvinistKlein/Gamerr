import requests
import logging

logger = logging.getLogger(__name__)

class RAWGClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.rawg.io/api"

    def search_game(self, title, platform=None):
        """Finds the best game match by title and optionally platform."""
        if not self.api_key:
            return None
            
        params = {
            'key': self.api_key,
            'search': title,
            'page_size': 5
        }
        
        try:
            response = requests.get(f"{self.base_url}/games", params=params)
            response.raise_for_status()
            data = response.json()
            
            if data['results']:
                # For now, return the first result as the best match
                return data['results'][0]
        except Exception as e:
            logger.error(f"RAWG search failed for {title}: {e}")
            
        return None

    def get_game_details(self, rawg_id):
        """Fetches full details including descriptions and ratings."""
        if not self.api_key or not rawg_id:
            return None
            
        params = {
            'key': self.api_key
        }
        
        try:
            response = requests.get(f"{self.base_url}/games/{rawg_id}", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"RAWG details fetch failed for ID {rawg_id}: {e}")
            
        return None
