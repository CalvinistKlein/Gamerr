"""
RAWG API Client for fetching game metadata
"""

import logging
from typing import Dict, List
import requests

logger = logging.getLogger(__name__)


class RAWGClient:
    """Client for interacting with the RAWG API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.rawg.io/api"
        
    def search_game(self, title: str, max_results: int = 10) -> List[Dict]:
        """Search for games by title"""
        try:
            url = f"{self.base_url}/games"
            params = {
                'key': self.api_key,
                'search': title,
                'page_size': max_results
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get('results', []):
                # Extract year from YYYY-MM-DD
                release_year = None
                if item.get('released'):
                    try:
                        release_year = int(item['released'][:4])
                    except (ValueError, TypeError):
                        pass
                        
                # Extract platforms
                platforms = []
                for p_info in item.get('platforms', []):
                    if 'platform' in p_info and 'name' in p_info['platform']:
                        platforms.append(p_info['platform']['name'])
                        
                # Extract screenshots
                screenshots = []
                for img in item.get('short_screenshots', []):
                    if 'image' in img:
                        screenshots.append(img['image'])
                        
                results.append({
                    'rawg_id': item.get('id'),
                    'title': item.get('name'),
                    'platform': ', '.join(platforms),
                    'release_year': release_year,
                    'rating': item.get('rating'),  # RAWG is natively 0-5
                    'cover_url': item.get('background_image'),
                    'screenshot_urls': screenshots,
                    'source': 'rawg',
                    'summary': None  # RAWG search endpoint doesn't return full description
                })
                
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"RAWG API Request Error: {e}")
            return []
        except Exception as e:
            logger.error(f"RAWG processing Error: {e}")
            return []
