"""
Search service for Romarr
==========================
Provides hybrid search across:
1. Local GameCatalog / games tables (instant, no API key needed)
2. IGDB API (live metadata enrichment on-the-fly when credentials are set)

Images are cached lazily — only downloaded for games that are actually searched.
"""

import logging
from typing import Dict, List, Optional

import requests

from config.config import Config
from models.settings import Settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prowlarr (torrent search — unchanged from original)
# ---------------------------------------------------------------------------

class SearchService:
    """Service for searching game torrents via Prowlarr"""

    @classmethod
    def _get_prowlarr_config(cls) -> Dict:
        return Settings.get_prowlarr_config()

    @classmethod
    def _make_prowlarr_request(cls, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make a request to Prowlarr API"""
        config = cls._get_prowlarr_config()
        url = config.get('prowlarr_url', '')
        api_key = config.get('prowlarr_api_key', '')

        if not url or not api_key:
            return None

        if not url.endswith('/'):
            url += '/'

        full_url = f"{url}api/v1/{endpoint}"
        headers = {
            'X-Api-Key': api_key,
            'Content-Type': 'application/json'
        }

        try:
            response = requests.get(full_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            try:
                return response.json()
            except ValueError as e:
                logger.warning(f"Prowlarr returned invalid JSON: {e}")
                return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Prowlarr request failed: {e}")
            return None

    @classmethod
    def search_games(cls, query: str, platform: str = None) -> List[Dict]:
        """Search for game torrents using Prowlarr"""
        search_query = query

        platform_terms = {
            'NES': 'nes', 'SNES': 'snes', 'N64': 'n64',
            'GameCube': 'gamecube', 'Wii': 'wii', 'Switch': 'switch',
            'Game Boy': 'gameboy', 'Game Boy Color': 'gameboy color',
            'Game Boy Advance': 'gameboy advance', 'DS': 'ds', '3DS': '3ds',
            'Genesis': 'genesis', 'PlayStation': 'playstation',
            'PlayStation 2': 'playstation 2', 'PlayStation 3': 'playstation 3',
            'PlayStation 4': 'playstation 4', 'Xbox': 'xbox',
            'Xbox 360': 'xbox 360', 'Arcade': 'arcade'
        }

        if platform and platform in platform_terms:
            search_query = f"{query} {platform_terms[platform]}"

        params = {
            'query': search_query,
            'categories': [1000, 1010],
            'type': 'search'
        }

        results = cls._make_prowlarr_request('search', params)
        if not results:
            return []

        formatted_results = []
        for result in results:
            if not cls._is_rom_result(result):
                continue

            formatted_result = {
                'title': result.get('title', ''),
                'size': result.get('size', 0),
                'seeders': result.get('seeders', 0),
                'leechers': result.get('leechers', 0),
                'download_url': result.get('downloadUrl', ''),
                'guid': result.get('guid', ''),
                'indexer': result.get('indexer', ''),
                'published_date': result.get('publishDate', ''),
                'category': result.get('categories', [])
            }

            platform_detected = cls._extract_platform_from_result(result)
            if platform_detected:
                formatted_result['platform'] = platform_detected

            formatted_results.append(formatted_result)

        return formatted_results

    @classmethod
    def _is_rom_result(cls, result: Dict) -> bool:
        title = result.get('title', '').lower()
        categories = result.get('categories', [])
        rom_categories = [1000, 1010, 1020]
        if any(cat in categories for cat in rom_categories):
            return True
        rom_extensions = ['.nes', '.smc', '.sfc', '.n64', '.z64', '.gcm', '.iso',
                          '.wbfs', '.wad', '.nsp', '.xci', '.gb', '.gbc', '.gba',
                          '.nds', '.3ds', '.cia', '.gen', '.md', '.smd', '.bin',
                          '.cue', '.pbp', '.pkg', '.xbe', '.xex', '.pce', '.ng',
                          '.zip', '.7z', '.chd']
        return any(ext in title for ext in rom_extensions)

    @classmethod
    def _extract_platform_from_result(cls, result: Dict) -> Optional[str]:
        import re
        title = result.get('title', '').lower()
        platform_patterns = {
            'NES': [r'\.nes', r'\(nes\)', r'\[nes\]', r'\bnes\b'],
            'SNES': [r'\.smc', r'\.sfc', r'\(snes\)', r'\[snes\]', r'\bsnes\b'],
            'N64': [r'\.n64', r'\.z64', r'\.v64', r'\(n64\)', r'\[n64\]', r'\bn64\b'],
            'GameCube': [r'\.gcm', r'\(gamecube\)', r'\(gc\)', r'\bgc\b'],
            'Wii': [r'\.wbfs', r'\.wad', r'\(wii\)', r'\bwii\b'],
            'Switch': [r'\.nsp', r'\.xci', r'\(switch\)', r'\bswitch\b'],
            'Game Boy': [r'\.gb', r'\(gb\)', r'\bgame ?boy\b'],
            'Game Boy Color': [r'\.gbc', r'\(gbc\)', r'\bgame ?boy ?color\b'],
            'Game Boy Advance': [r'\.gba', r'\(gba\)', r'\bgame ?boy ?advance\b'],
            'DS': [r'\.nds', r'\(ds\)', r'\bds\b', r'\bnintendo ?ds\b'],
            '3DS': [r'\.3ds', r'\.cia', r'\(3ds\)', r'\b3ds\b'],
            'Genesis': [r'\.gen', r'\.md', r'\.smd', r'\(genesis\)', r'\(megadrive\)', r'\bgenesis\b'],
            'PlayStation': [r'\.bin', r'\.cue', r'\(ps1\)', r'\(psx\)', r'\bplaystation\b'],
            'PlayStation 2': [r'\(ps2\)', r'\bplaystation ?2\b'],
            'PlayStation 3': [r'\.pkg', r'\(ps3\)', r'\bplaystation ?3\b'],
            'PlayStation 4': [r'\.pkg', r'\(ps4\)', r'\bplaystation ?4\b'],
            'Xbox': [r'\.xbe', r'\(xbox\)', r'\bxbox\b'],
            'Xbox 360': [r'\.xex', r'\(xbox ?360\)', r'\bxbox ?360\b'],
            'Arcade': [r'\.zip', r'\.7z', r'\.chd', r'\(arcade\)', r'\(mame\)', r'\barcade\b'],
        }
        for platform, patterns in platform_patterns.items():
            for pattern in patterns:
                if re.search(pattern, title, re.IGNORECASE):
                    return platform
        return None

    @classmethod
    def test_connection(cls) -> Dict:
        config = cls._get_prowlarr_config()
        url = config.get('prowlarr_url', '')
        api_key = config.get('prowlarr_api_key', '')

        if not url or not api_key:
            return {'success': False, 'message': 'Prowlarr URL or API key not configured'}

        if not url.endswith('/'):
            url += '/'

        test_url = f"{url}api/v1/system/status"
        headers = {'X-Api-Key': api_key}

        try:
            response = requests.get(test_url, headers=headers, timeout=5)
            if response.status_code == 200:
                try:
                    data = response.json()
                    return {
                        'success': True,
                        'message': 'Prowlarr connection successful',
                        'version': data.get('version', 'unknown'),
                        'appName': data.get('appName', 'Prowlarr')
                    }
                except ValueError as e:
                    return {'success': False, 'message': f'Prowlarr returned invalid JSON: {str(e)}'}
            else:
                return {'success': False, 'message': f'Prowlarr returned status code {response.status_code}'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'message': f'Failed to connect to Prowlarr: {str(e)}'}


# ---------------------------------------------------------------------------
# Metadata Search — local DB + IGDB on-the-fly with image caching
# ---------------------------------------------------------------------------

class MetadataSearchService:
    """
    Hybrid search service that queries the local database AND external APIs.
    Images are cached lazily: only downloaded when a game is actually searched/viewed.
    """

    LOCAL_LIMIT = 20
    EXTERNAL_LIMIT = 10

    @classmethod
    def search(cls, query: str, platform: str = None, page: int = 1,
               per_page: int = 20) -> dict:
        """
        Search both local catalog and metadata sources, merge results, cache cover images.
        """
        from models.settings import Settings
        import logging
        logger = logging.getLogger(__name__)
        
        local_results = cls._search_local(query, platform, page, per_page)
        
        config = Settings.get_metadata_config()
        igdb_results = []
        rawg_results = []
        
        if config['igdb_enabled'] and config['igdb_client_id'] and config['igdb_client_secret']:
            try:
                igdb_results = cls._search_igdb(query, platform, config['igdb_client_id'], config['igdb_client_secret'])
            except Exception as e:
                logger.warning(f"IGDB search failed: {e}")
                
        if config['rawg_enabled'] and config['rawg_api_key']:
            try:
                rawg_results = cls._search_rawg(query, platform, config['rawg_api_key'])
            except Exception as e:
                logger.warning(f"RAWG search failed: {e}")

        # Split priority
        priority = [s.strip().lower() for s in config.get('source_priority', 'igdb,rawg,local').split(',') if s.strip()]
        if not priority:
            priority = ['local', 'igdb', 'rawg']
            
        merged = cls._merge(local_results['items'], igdb_results, rawg_results, priority, query, platform)

        # Lazy-cache cover images for the first page of results only
        for item in merged[:per_page]:
            cover_url = item.get('cover_url') or item.get('cover_image_url')
            if cover_url and not cover_url.startswith('/static/cache'):
                try:
                    from services.image_cache import get_or_fetch
                    cached_url = get_or_fetch(
                        url=cover_url,
                        entity_type='game',
                        entity_id=item.get('catalog_id') or item.get('id') or 0,
                        image_type='cover'
                    )
                    if cached_url:
                        item['cached_cover_url'] = cached_url
                except Exception as e:
                    logger.debug(f"Image cache skip for {cover_url}: {e}")

        return {
            'results': merged,
            'total_local': local_results['total'],
            'igdb_available': bool(igdb_results),
            'rawg_available': bool(rawg_results),
            'query': query,
            'platform': platform,
            'page': page,
            'per_page': per_page,
        }

    @classmethod
    def _search_local(cls, query: str, platform: str, page: int, per_page: int) -> dict:
        """Search the local GameCatalog table with pagination."""
        from models.unified_schema import GameCatalog

        q = GameCatalog.query

        if query:
            q = q.filter(GameCatalog.title.ilike(f'%{query}%'))
        if platform:
            q = q.filter_by(platform=platform)

        total = q.count()
        items = q.order_by(GameCatalog.title)\
                  .offset((page - 1) * per_page)\
                  .limit(per_page)\
                  .all()

        return {
            'total': total,
            'items': [cls._format_local_game(g) for g in items]
        }

    @classmethod
    def _format_local_game(cls, game) -> dict:
        """Convert GameCatalog model to dict."""
        return {
            'source': 'local',
            'catalog_id': game.catalog_id,
            'title': game.title,
            'platform': game.platform,
            'description': game.description,
            'release_year': game.release_year,
            'rating': game.rating,
            'cover_image_url': game.cover_image_url,
            'cover_url': game.cover_image_url,
            'screenshot_urls': [],
            'enriched': False,
        }

    @classmethod
    def _search_igdb(cls, query: str, platform: str, client_id: str, client_secret: str) -> list:
        """Query IGDB for live metadata."""
        from services.igdb_client import IGDBClient
        client = IGDBClient(client_id, client_secret)

        games = client.fuzzy_search_game(
            title=query,
            platform_name=platform,
            max_results=cls.EXTERNAL_LIMIT
        )

        results = []
        for game in games:
            d = game.to_dict()
            d['source'] = 'igdb'
            d['cover_url'] = game.cover_url
            d['screenshot_urls'] = game.screenshot_urls
            d['platform'] = platform or ''
            results.append(d)

        return results

    @classmethod
    def _search_rawg(cls, query: str, platform: str, api_key: str) -> list:
        """Query RAWG for live metadata."""
        from services.rawg_client import RAWGClient
        client = RAWGClient(api_key)
        return client.search_game(title=query, max_results=cls.EXTERNAL_LIMIT)

    @classmethod
    def _merge(cls, local: list, igdb: list, rawg: list,
               priority: list, query: str, platform: str) -> list:
        """
        Merge local, IGDB, and RAWG results based on source priority.
        Enriches lower-priority entries with higher-priority metadata.
        """
        import difflib

        def key(title, plat):
            return (str(title).lower().strip(), (plat or '').lower().strip())

        master_list = []
        sources = {'local': local, 'igdb': igdb, 'rawg': rawg}
        ordered_sources = []
        
        for p in priority:
            if p in sources:
                ordered_sources.append(p)
                
        # Fallback for sources not in priority list
        for s in sources:
            if s not in ordered_sources:
                ordered_sources.append(s)

        # Build master list starting from the highest priority source
        for source_name in ordered_sources:
            items = sources[source_name]
            for item in items:
                item_key = key(item.get('title', ''), item.get('platform', ''))
                
                # Check fuzzy match against already merged master_list
                matched = None
                for master_item in master_list:
                    master_key = key(master_item.get('title', ''), master_item.get('platform', ''))
                    # Usually comparing identical platforms, but fuzzy title match is good enough
                    similarity = difflib.SequenceMatcher(None, item_key[0], master_key[0]).ratio()
                    if similarity >= 0.80 and (not item_key[1] or not master_key[1] or item_key[1] == master_key[1]):
                        matched = master_item
                        break
                        
                if matched:
                    # Enrich existing item if it lacks data
                    if not matched.get('description') and item.get('summary'):
                        matched['description'] = item['summary']
                    if not matched.get('cover_image_url') and item.get('cover_url'):
                        matched['cover_image_url'] = item['cover_url']
                        matched['cover_url'] = item['cover_url']
                    if not matched.get('rating') and item.get('rating'):
                        if source_name == 'igdb':
                            matched['rating'] = round(item['rating'] / 20, 1) # 0-100 -> 0-5
                        else:
                            matched['rating'] = item['rating']
                    if not matched.get('release_year') and item.get('release_year'):
                        matched['release_year'] = item['release_year']
                    if not matched.get('screenshot_urls') and item.get('screenshot_urls'):
                        matched['screenshot_urls'] = item['screenshot_urls']
                    matched['enriched'] = True
                    
                    # Preserve local catalog_id always
                    if source_name == 'local' and not matched.get('catalog_id'):
                        matched['catalog_id'] = item.get('catalog_id')
                        matched['source'] = 'local'  # Always treat as local if it's in the DB
                else:
                    # Add new item
                    if source_name == 'igdb' and item.get('rating'):
                        item['rating'] = round(item['rating'] / 20, 1)
                    if not item.get('cover_image_url') and item.get('cover_url'):
                        item['cover_image_url'] = item['cover_url']
                    if not item.get('platform'):
                        item['platform'] = platform or ''
                    master_list.append(item)

        # Ensure UI knows which items are in catalog
        for item in master_list:
            if item.get('catalog_id'):
                item['source'] = 'local'

        return master_list
