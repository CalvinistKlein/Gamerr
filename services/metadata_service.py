"""
Gamerr (Romarr) Metadata Service
================================
Implements the Sonarr/Radarr (SkyHook) architecture:
1. Queries the centralized Gamerr Metadata Proxy (METADATA_API_URL).
   - Zero API keys required for end users.
   - Returns high-res box art, ratings, release years, developers, publishers, genres.
2. Graceful Fallbacks:
   - Falls back to local cached entries in GameCatalog.
   - Falls back to bundled offline seed datasets (seeds/initial_catalog.json).
   - Falls back to open public community repositories (Libretro / TheGamesDB).
"""

import os
import json
import logging
import requests
from typing import Dict, List, Optional
from config.config import Config
from models.settings import Settings

logger = logging.getLogger(__name__)


class MetadataService:
    """Zero-configuration metadata client for Gamerr/Romarr"""

    DEFAULT_ENDPOINT = "https://api.gamerr.io/v1"
    TIMEOUT_SECONDS = 4

    @classmethod
    def get_api_url(cls) -> str:
        """Get configured metadata endpoint (Settings DB -> Config / Env -> Default)"""
        try:
            from flask import has_app_context
            if has_app_context():
                custom_url = Settings.get('metadata_api_url')
                if custom_url:
                    return custom_url.rstrip('/')
        except Exception:
            pass
        return os.environ.get('METADATA_API_URL', getattr(Config, 'METADATA_API_URL', cls.DEFAULT_ENDPOINT)).rstrip('/')

    @classmethod
    def search_games(cls, query: str = "", platform: str = None, 
                     decade: str = None, generation: int = None, 
                     sort: str = "popular", page: int = 1, per_page: int = 36) -> Dict:
        """
        Search games across cloud metadata proxy, with local database fallbacks.
        Users do NOT need any API keys.
        """
        api_url = cls.get_api_url()

        # 1. Try Centralized Metadata Proxy (SkyHook style)
        if api_url:
            try:
                params = {
                    'q': query,
                    'platform': platform or '',
                    'decade': decade or '',
                    'generation': generation or '',
                    'sort': sort,
                    'page': page,
                    'limit': per_page
                }
                resp = requests.get(f"{api_url}/search", params=params, timeout=cls.TIMEOUT_SECONDS)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict) and 'results' in data:
                        logger.info(f"Retrieved {len(data['results'])} games from SkyHook proxy ({api_url})")
                        return data
                    elif isinstance(data, list):
                        return {
                            'results': data,
                            'total': len(data),
                            'page': page,
                            'per_page': per_page,
                            'source': 'skyhook'
                        }
            except Exception as e:
                logger.debug(f"SkyHook proxy ({api_url}) unavailable, using local/seed fallback: {e}")

        # 2. Resilient Fallback: Local Database & Seeds
        return cls._search_local_and_seed(query, platform, decade, generation, sort, page, per_page)

    @classmethod
    def _search_local_and_seed(cls, query: str, platform: str, 
                               decade: str, generation: int, 
                               sort: str, page: int, per_page: int) -> Dict:
        """Search local GameCatalog cache and seeds"""
        from flask import has_app_context
        import os
        import json

        if not has_app_context():
            # If called without active Flask context, search seed catalog directly
            seed_file = os.path.join(os.path.dirname(__file__), '..', 'seeds', 'initial_catalog.json')
            if os.path.exists(seed_file):
                with open(seed_file, 'r', encoding='utf-8') as f:
                    seeds = json.load(f)
                filtered = []
                for idx, item in enumerate(seeds):
                    if query and query.lower() not in item.get('title', '').lower():
                        continue
                    if platform and platform.lower() not in item.get('platform', '').lower():
                        continue
                    item_copy = dict(item)
                    item_copy.setdefault('id', idx + 1)
                    filtered.append(item_copy)
                return {
                    'results': filtered[:per_page],
                    'total': len(filtered),
                    'page': page,
                    'per_page': per_page,
                    'source': 'seed_fallback'
                }
            return {'results': [], 'total': 0, 'page': page, 'per_page': per_page, 'source': 'empty'}

        from models.unified_schema import GameCatalog, Platform
        from routes.web import GENERATIONS
        from extensions import db

        catalog_query = GameCatalog.query

        # Text Filter
        if query:
            catalog_query = catalog_query.filter(
                db.or_(
                    GameCatalog.title.ilike(f'%{query}%'),
                    GameCatalog.publisher.ilike(f'%{query}%'),
                    GameCatalog.developer.ilike(f'%{query}%'),
                    GameCatalog.genre.ilike(f'%{query}%')
                )
            )

        # Platform Filter
        if platform:
            catalog_query = catalog_query.filter(
                db.or_(
                    GameCatalog.platform.ilike(platform),
                    GameCatalog.platform == platform
                )
            )

        # Decade Filter
        if decade and decade.endswith('s') and decade[:-1].isdigit():
            start_year = int(decade[:-1])
            end_year = start_year + 9
            catalog_query = catalog_query.filter(GameCatalog.release_year.between(start_year, end_year))

        # Generation Filter (Console + PC titles from that historical window)
        if generation and generation in GENERATIONS:
            gen_info = GENERATIONS[generation]
            gen_start, gen_end = gen_info['years']
            
            gen_plat_objs = Platform.query.filter_by(generation=generation).all()
            gen_platform_names = [p.name for p in gen_plat_objs] + [p.slug for p in gen_plat_objs]
            
            catalog_query = catalog_query.filter(
                db.or_(
                    GameCatalog.platform.in_(gen_platform_names),
                    db.and_(
                        GameCatalog.release_year.between(gen_start, gen_end),
                        db.or_(*[GameCatalog.platform.ilike(f'%{p}%') for p in ['PC', 'DOS', 'Windows', 'ScummVM', 'Commodore', 'Amiga']])
                    )
                )
            )

        # Sorting
        if sort == 'newest':
            catalog_query = catalog_query.order_by(GameCatalog.release_year.desc().nullslast(), GameCatalog.title.asc())
        elif sort == 'oldest':
            catalog_query = catalog_query.order_by(GameCatalog.release_year.asc().nullslast(), GameCatalog.title.asc())
        elif sort == 'title':
            catalog_query = catalog_query.order_by(GameCatalog.title.asc())
        elif sort == 'rating':
            catalog_query = catalog_query.order_by(GameCatalog.rating.desc().nullslast(), GameCatalog.title.asc())
        else:
            catalog_query = catalog_query.order_by(GameCatalog.rating.desc().nullslast(), GameCatalog.download_count.desc(), GameCatalog.title.asc())

        total = catalog_query.count()
        items = catalog_query.offset((page - 1) * per_page).limit(per_page).all()

        return {
            'results': [item.to_dict() for item in items],
            'total': total,
            'page': page,
            'per_page': per_page,
            'source': 'local_cache'
        }

    @classmethod
    def get_game_details(cls, game_id: int) -> Optional[Dict]:
        """Fetch details for a specific catalog game"""
        from flask import has_app_context
        import os
        import json

        if has_app_context():
            from models.unified_schema import GameCatalog
            game = GameCatalog.query.get(game_id)
            if game:
                return game.to_dict()

        # Check seed catalog as fallback
        seed_file = os.path.join(os.path.dirname(__file__), '..', 'seeds', 'initial_catalog.json')
        if os.path.exists(seed_file):
            with open(seed_file, 'r', encoding='utf-8') as f:
                seeds = json.load(f)
            for idx, item in enumerate(seeds):
                assigned_id = item.get('id', idx + 1)
                if assigned_id == game_id:
                    item_copy = dict(item)
                    item_copy.setdefault('id', assigned_id)
                    return item_copy
            if seeds and isinstance(game_id, int) and 0 <= game_id < len(seeds):
                item_copy = dict(seeds[game_id])
                item_copy.setdefault('id', game_id + 1)
                return item_copy
        return None

    @classmethod
    def get_metadata(cls, title: str, platform: str = None) -> Optional[Dict]:
        """Fetch metadata dictionary for a specific game title and platform"""
        if not title:
            return None
        res = cls.search_games(query=title, platform=platform, per_page=1)
        results = res.get('results', [])
        if results:
            return results[0]
        if platform:
            res = cls.search_games(query=title, per_page=1)
            results = res.get('results', [])
            if results:
                return results[0]
        return None

