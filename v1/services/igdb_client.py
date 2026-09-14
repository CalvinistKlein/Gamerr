"""
IGDB API Client for fetching game metadata
Uses IGDB API v4 with Twitch OAuth authentication
"""

import os
import time
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class IGDBGame:
    """Game data from IGDB API"""
    id: int
    name: str
    slug: str
    summary: Optional[str] = None
    storyline: Optional[str] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    aggregated_rating: Optional[float] = None
    aggregated_rating_count: Optional[int] = None
    total_rating: Optional[float] = None
    total_rating_count: Optional[int] = None
    first_release_date: Optional[int] = None
    release_dates: List[Dict] = None
    platforms: List[int] = None
    genres: List[int] = None
    themes: List[int] = None
    game_modes: List[int] = None
    player_perspectives: List[int] = None
    cover: Optional[int] = None
    cover_url: Optional[str] = None
    screenshots: List[int] = None
    screenshot_urls: List[str] = None
    artworks: List[int] = None
    artwork_urls: List[str] = None
    websites: List[Dict] = None
    involved_companies: List[int] = None
    developers: List[int] = None
    publishers: List[int] = None
    alternative_names: List[str] = None
    collection: Optional[int] = None
    franchise: Optional[int] = None
    game_engines: List[int] = None
    keywords: List[int] = None
    status: Optional[str] = None
    category: Optional[str] = None
    
    def __post_init__(self):
        if self.release_dates is None:
            self.release_dates = []
        if self.platforms is None:
            self.platforms = []
        if self.genres is None:
            self.genres = []
        if self.themes is None:
            self.themes = []
        if self.game_modes is None:
            self.game_modes = []
        if self.player_perspectives is None:
            self.player_perspectives = []
        if self.screenshots is None:
            self.screenshots = []
        if self.screenshot_urls is None:
            self.screenshot_urls = []
        if self.artworks is None:
            self.artworks = []
        if self.artwork_urls is None:
            self.artwork_urls = []
        if self.websites is None:
            self.websites = []
        if self.involved_companies is None:
            self.involved_companies = []
        if self.developers is None:
            self.developers = []
        if self.publishers is None:
            self.publishers = []
        if self.alternative_names is None:
            self.alternative_names = []
        if self.game_engines is None:
            self.game_engines = []
        if self.keywords is None:
            self.keywords = []
    
    @property
    def release_year(self) -> Optional[int]:
        """Extract release year from first release date"""
        if self.first_release_date:
            try:
                dt = datetime.fromtimestamp(self.first_release_date)
                return dt.year
            except (ValueError, OSError):
                return None
        return None
    
    @property
    def release_date_iso(self) -> Optional[str]:
        """Get release date in ISO format"""
        if self.first_release_date:
            try:
                dt = datetime.fromtimestamp(self.first_release_date)
                return dt.strftime('%Y-%m-%d')
            except (ValueError, OSError):
                return None
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'igdb_id': self.id,
            'title': self.name,
            'slug': self.slug,
            'summary': self.summary,
            'storyline': self.storyline,
            'rating': self.rating,
            'rating_count': self.rating_count,
            'aggregated_rating': self.aggregated_rating,
            'total_rating': self.total_rating,
            'release_date': self.release_date_iso,
            'release_year': self.release_year,
            'cover_url': self.cover_url,
            'platform_ids': self.platforms,
            'genre_ids': self.genres,
            'developer_ids': self.developers,
            'publisher_ids': self.publishers,
            'alternative_names': self.alternative_names,
            'status': self.status,
            'category': self.category
        }


class IGDBClient:
    """Client for IGDB API"""
    
    BASE_URL = "https://api.igdb.com/v4"
    
    # Platform mapping from RetroArch/No-Intro names to IGDB platform IDs
    PLATFORM_MAPPING = {
        # Nintendo
        'Nintendo Entertainment System': 18,  # NES
        'NES': 18,
        'Super Nintendo Entertainment System': 19,  # SNES
        'SNES': 19,
        'Nintendo 64': 4,
        'N64': 4,
        'GameCube': 21,
        'Wii': 5,
        'Wii U': 41,
        'Switch': 130,
        'Game Boy': 33,
        'GB': 33,
        'Game Boy Color': 22,
        'GBC': 22,
        'Game Boy Advance': 24,
        'GBA': 24,
        'Nintendo DS': 20,
        'DS': 20,
        'Nintendo 3DS': 37,
        '3DS': 37,
        'Virtual Boy': 87,
        'Pokemon Mini': 115,
        
        # Sega
        'Master System': 64,
        'Sega Genesis': 29,
        'Genesis': 29,
        'Mega Drive': 29,
        'Sega CD': 78,
        'Sega 32X': 30,
        'Saturn': 32,
        'Dreamcast': 23,
        'Game Gear': 35,
        'SG-1000': 107,
        
        # Sony
        'PlayStation': 7,
        'PS1': 7,
        'PlayStation 2': 8,
        'PS2': 8,
        'PlayStation 3': 9,
        'PS3': 9,
        'PlayStation 4': 48,
        'PS4': 48,
        'PlayStation 5': 167,
        'PS5': 167,
        'PlayStation Portable': 38,
        'PSP': 38,
        'PlayStation Vita': 46,
        'PS Vita': 46,
        
        # Microsoft
        'Xbox': 11,
        'Xbox 360': 12,
        'Xbox One': 49,
        'Xbox Series X|S': 169,
        
        # Other consoles
        'Atari 2600': 59,
        'Atari 7800': 60,
        'Atari Lynx': 61,
        'Neo Geo': 80,
        'Neo Geo Pocket': 120,
        'Neo Geo Pocket Color': 119,
        'PC Engine': 86,
        'TurboGrafx-16': 86,
        'PC Engine CD': 150,
        'TurboGrafx-CD': 150,
        'WonderSwan': 123,
        'WonderSwan Color': 57,
        'Commodore 64': 15,
        'Amiga': 16,
        'ZX Spectrum': 26,
        'MSX': 27,
        '3DO': 111,
        'Jaguar': 62,
        'CD-i': 117,
        'Philips CD-i': 117,
        
        # Arcade
        'Arcade': 52,
        'MAME': 52,
    }
    
    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize IGDB client
        
        Args:
            client_id: Twitch Developer Application Client ID
            client_secret: Twitch Developer Application Client Secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires_at = 0
        
        # Configure session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
    
    def _get_access_token(self) -> Optional[str]:
        """Get OAuth access token from Twitch"""
        if self.access_token and time.time() < self.token_expires_at - 60:
            return self.access_token
        
        try:
            token_url = "https://id.twitch.tv/oauth2/token"
            params = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials'
            }
            
            response = self.session.post(token_url, params=params, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = time.time() + expires_in
            
            logger.info("Successfully obtained IGDB access token")
            return self.access_token
            
        except Exception as e:
            logger.error(f"Failed to get IGDB access token: {e}")
            return None
    
    def _make_request(self, endpoint: str, query: str) -> Optional[List[Dict]]:
        """
        Make a request to IGDB API
        
        Args:
            endpoint: API endpoint (games, platforms, etc.)
            query: IGDB query string
            
        Returns:
            List of results or None if error
        """
        token = self._get_access_token()
        if not token:
            return None
        
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {
            'Client-ID': self.client_id,
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }
        
        try:
            response = self.session.post(url, headers=headers, data=query, timeout=30)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self._make_request(endpoint, query)  # Retry
            
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"IGDB API request failed: {e}")
            return None
    
    def search_games(self, query: str, platform_id: Optional[int] = None, limit: int = 10) -> List[IGDBGame]:
        """
        Search for games by title
        
        Args:
            query: Game title to search for
            platform_id: Optional platform ID to filter by
            limit: Maximum number of results
            
        Returns:
            List of IGDBGame objects
        """
        # Build search query
        search_query = f'search "{query}";'
        
        # Fields to retrieve — use dot-expansion for cover and screenshots
        # so all data comes back in ONE request instead of N+1 calls
        fields = [
            'id', 'name', 'slug', 'summary', 'storyline',
            'rating', 'rating_count', 'aggregated_rating', 'aggregated_rating_count',
            'total_rating', 'total_rating_count', 'first_release_date',
            'cover.url',
            'screenshots.url',
            'artworks.url',
            'websites',
            'involved_companies',
            'alternative_names',
            'collection', 'franchise',
            'game_engines', 'keywords', 'status', 'category',
            'platforms', 'genres', 'themes', 'game_modes'
        ]
        
        # Add platform filter if specified
        if platform_id:
            search_query += f' where platforms = {platform_id};'
        
        search_query += f' limit {limit};'
        
        # Make request
        results = self._make_request('games', f'fields {",".join(fields)}; {search_query}')
        
        if not results:
            return []
        
        # Process results
        games = []
        for result in results:
            game = self._parse_game_result(result)
            if game:
                games.append(game)
        
        return games
    
    def get_game_by_id(self, game_id: int) -> Optional[IGDBGame]:
        """Get game by IGDB ID"""
        query = f'fields *; where id = {game_id};'
        
        results = self._make_request('games', query)
        if not results or len(results) == 0:
            return None
        
        return self._parse_game_result(results[0])
    
    def get_platforms(self, platform_ids: List[int]) -> List[Dict]:
        """Get platform information by IDs"""
        if not platform_ids:
            return []
        
        id_list = ','.join(str(id) for id in platform_ids)
        query = f'fields id,name,slug,abbreviation,platform_family; where id = ({id_list});'
        
        results = self._make_request('platforms', query)
        return results or []
    
    def get_genres(self, genre_ids: List[int]) -> List[Dict]:
        """Get genre information by IDs"""
        if not genre_ids:
            return []
        
        id_list = ','.join(str(id) for id in genre_ids)
        query = f'fields id,name,slug; where id = ({id_list});'
        
        results = self._make_request('genres', query)
        return results or []
    
    def get_companies(self, company_ids: List[int]) -> List[Dict]:
        """Get company information by IDs"""
        if not company_ids:
            return []
        
        id_list = ','.join(str(id) for id in company_ids)
        query = f'fields id,name,slug,description,country,start_date; where id = ({id_list});'
        
        results = self._make_request('companies', query)
        return results or []
    
    def get_involved_companies(self, game_id: int) -> List[Dict]:
        """Get involved companies for a game"""
        query = f'fields *,company.*,publisher,developer; where game = {game_id};'
        
        results = self._make_request('involved_companies', query)
        return results or []
    
    def get_release_dates(self, game_id: int) -> List[Dict]:
        """Get release dates for a game"""
        query = f'fields *,platform.*,region; where game = {game_id};'
        
        results = self._make_request('release_dates', query)
        return results or []
    
    def get_cover_url(self, cover_id: int, size: str = "cover_big") -> Optional[str]:
        """Get cover image URL"""
        if not cover_id:
            return None
        
        query = f'fields url; where id = {cover_id};'
        
        results = self._make_request('covers', query)
        if not results or len(results) == 0:
            return None
        
        url = results[0].get('url', '')
        if url:
            # Convert to specific size
            url = url.replace('t_thumb', f't_{size}')
            return f"https:{url}"
        
        return None
    
    def get_screenshot_urls(self, screenshot_ids: List[int], size: str = "screenshot_big") -> List[str]:
        """Get screenshot URLs"""
        if not screenshot_ids:
            return []
        
        id_list = ','.join(str(id) for id in screenshot_ids)
        query = f'fields url; where id = ({id_list});'
        
        results = self._make_request('screenshots', query)
        if not results:
            return []
        
        urls = []
        for result in results:
            url = result.get('url', '')
            if url:
                url = url.replace('t_thumb', f't_{size}')
                urls.append(f"https:{url}")
        
        return urls
    
    def _parse_game_result(self, result: Dict) -> Optional['IGDBGame']:
        """Parse raw API result into IGDBGame object"""
        # Extract basic fields
        game_id = result.get('id')
        if not game_id:
            return None
        
        # Get cover URL from pre-expanded cover field (no extra API call)
        cover_url = None
        cover_data = result.get('cover')
        if isinstance(cover_data, dict):
            raw_url = cover_data.get('url', '')
            if raw_url:
                cover_url = f"https:{raw_url.replace('t_thumb', 't_cover_big')}"
        
        # Get screenshot URLs from pre-expanded screenshots (no extra API call)
        screenshot_urls = []
        screenshots_data = result.get('screenshots', [])
        if screenshots_data and isinstance(screenshots_data, list):
            for s in screenshots_data[:5]:  # Limit to 5
                if isinstance(s, dict):
                    raw_url = s.get('url', '')
                    if raw_url:
                        screenshot_urls.append(f"https:{raw_url.replace('t_thumb', 't_screenshot_big')}")
        
        return IGDBGame(
            id=game_id,
            name=result.get('name', ''),
            slug=result.get('slug', ''),
            summary=result.get('summary'),
            storyline=result.get('storyline'),
            rating=result.get('rating'),
            rating_count=result.get('rating_count'),
            aggregated_rating=result.get('aggregated_rating'),
            aggregated_rating_count=result.get('aggregated_rating_count'),
            total_rating=result.get('total_rating'),
            total_rating_count=result.get('total_rating_count'),
            first_release_date=result.get('first_release_date'),
            release_dates=result.get('release_dates', []),
            platforms=result.get('platforms', []),
            genres=result.get('genres', []),
            themes=result.get('themes', []),
            game_modes=result.get('game_modes', []),
            player_perspectives=result.get('player_perspectives', []),
            cover=cover_data.get('id') if isinstance(cover_data, dict) else cover_data,
            cover_url=cover_url,
            screenshots=[s.get('id') for s in screenshots_data if isinstance(s, dict)],
            screenshot_urls=screenshot_urls,
            artworks=[],
            artwork_urls=[],
            websites=result.get('websites', []),
            involved_companies=result.get('involved_companies', []),
            developers=result.get('developers', []),
            publishers=result.get('publishers', []),
            alternative_names=result.get('alternative_names', []),
            collection=result.get('collection'),
            franchise=result.get('franchise'),
            game_engines=result.get('game_engines', []),
            keywords=result.get('keywords', []),
            status=result.get('status'),
            category=result.get('category')
        )
    
    def map_platform_name(self, platform_name: str) -> Optional[int]:
        """
        Map platform name to IGDB platform ID
        
        Args:
            platform_name: Platform name from DAT file
            
        Returns:
            IGDB platform ID or None if not found
        """
        # Clean platform name
        platform_name = platform_name.strip()
        
        # Try exact match first
        if platform_name in self.PLATFORM_MAPPING:
            return self.PLATFORM_MAPPING[platform_name]
        
        # Try case-insensitive match
        platform_lower = platform_name.lower()
        for key, value in self.PLATFORM_MAPPING.items():
            if key.lower() == platform_lower:
                return value
        
        # Try partial match
        for key, value in self.PLATFORM_MAPPING.items():
            if platform_lower in key.lower() or key.lower() in platform_lower:
                return value
        
        logger.warning(f"No IGDB platform mapping found for: {platform_name}")
        return None
    
    def fuzzy_search_game(self, title: str, platform_name: str = None, max_results: int = 5) -> List[IGDBGame]:
        """
        Fuzzy search for game by title with platform filtering
        
        Args:
            title: Game title to search for
            platform_name: Optional platform name for filtering
            max_results: Maximum number of results
            
        Returns:
            List of matching IGDBGame objects
        """
        # Clean title for better search
        clean_title = self._clean_search_title(title)
        
        # Map platform if specified
        platform_id = None
        if platform_name:
            platform_id = self.map_platform_name(platform_name)
        
        # Search games
        games = self.search_games(clean_title, platform_id, limit=max_results * 2)
        
        if not games:
            return []
        
        # Score and rank results
        scored_games = []
        for game in games:
            score = self._calculate_title_similarity(clean_title, game.name)
            scored_games.append((score, game))
        
        # Sort by score (descending)
        scored_games.sort(key=lambda x: x[0], reverse=True)
        
        # Return top results
        return [game for _, game in scored_games[:max_results]]
    
    def _clean_search_title(self, title: str) -> str:
        """Clean title for better search results"""
        # Remove region info, version numbers, etc.
        import re
        
        # Remove content in parentheses
        title = re.sub(r'\s*\([^)]*\)', '', title)
        
        # Remove common suffixes
        suffixes = [' - ', ' : ', ' :', ' -']
        for suffix in suffixes:
            if suffix in title:
                title = title.split(suffix)[0]
        
        # Remove extra spaces
        title = ' '.join(title.split())
        
        return title.strip()
    
    def _calculate_title_similarity(self, search_title: str, result_title: str) -> float:
        """Calculate similarity between search title and result title"""
        import difflib
        
        search_lower = search_title.lower()
        result_lower = result_title.lower()
        
        # Use SequenceMatcher for similarity
        similarity = difflib.SequenceMatcher(None, search_lower, result_lower).ratio()
        
        # Bonus for exact match at start
        if result_lower.startswith(search_lower):
            similarity += 0.2
        
        # Penalty for "demo", "beta", etc. in result when not in search
        demo_terms = ['demo', 'beta', 'prototype', 'sample', 'kiosk']
        search_has_demo = any(term in search_lower for term in demo_terms)
        result_has_demo = any(term in result_lower for term in demo_terms)
        
        if result_has_demo and not search_has_demo:
            similarity -= 0.3
        
        return max(0.0, min(1.0, similarity))
    
    def test_connection(self) -> Dict:
        """Test IGDB API connection"""
        try:
            # Try to fetch a known game
            results = self.search_games("Super Mario Bros", limit=1)
            
            if results:
                return {
                    'success': True,
                    'message': 'IGDB API connection successful',
                    'sample_game': results[0].name
                }
            else:
                return {
                    'success': False,
                    'message': 'IGDB API returned no results'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'IGDB API connection failed: {str(e)}'
            }


def load_igdb_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Load IGDB credentials from environment variables"""
    client_id = os.environ.get('IGDB_CLIENT_ID')
    client_secret = os.environ.get('IGDB_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        logger.warning("IGDB credentials not found in environment variables")
        logger.warning("Set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET environment variables")
    
    return client_id, client_secret


def create_igdb_client() -> Optional[IGDBClient]:
    """Create IGDB client using environment variables"""
    client_id, client_secret = load_igdb_credentials()
    
    if not client_id or not client_secret:
        return None
    
    return IGDBClient(client_id, client_secret)