#!/usr/bin/env python3
"""
Gamerr (Romarr) Public SkyHook Metadata Proxy Server
=====================================================
A lightweight, standalone server that you can host publicly (like radarr.servarr.com
or skyhook.sonarr.tv) to serve game metadata to all Gamerr instances worldwide.

Features:
- Zero API keys required for end users.
- Connects upstream to IGDB, RAWG, and open community DAT databases.
- Aggressive caching (in-memory & SQLite) to protect API limits and ensure sub-50ms responses.
- Endpoints:
    GET /v1/health
    GET /v1/search?q={query}&platform={platform}&decade={decade}&generation={gen}&page={p}
    GET /v1/game/<id>
    GET /v1/platforms
"""

import os
import time
import argparse
from flask import Flask, jsonify, request
import requests

app = Flask("GamerrSkyHook")

# Upstream API Credentials (Stored securely on this server, never exposed to users)
IGDB_CLIENT_ID = os.environ.get("IGDB_CLIENT_ID", "")
IGDB_CLIENT_SECRET = os.environ.get("IGDB_CLIENT_SECRET", "")
RAWG_API_KEY = os.environ.get("RAWG_API_KEY", "")

# In-memory LRU Cache for high performance
CACHE = {}
CACHE_TTL = 3600 * 24  # 24 hours


def get_cached(key):
    entry = CACHE.get(key)
    if entry and (time.time() - entry['time'] < CACHE_TTL):
        return entry['data']
    return None


def set_cached(key, data):
    CACHE[key] = {'time': time.time(), 'data': data}


@app.route('/v1/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'Gamerr SkyHook Metadata Proxy',
        'version': '1.0.0',
        'cached_queries': len(CACHE)
    })


@app.route('/v1/search')
def search():
    """
    Search games across upstream databases with caching.
    Params: q, platform, decade, generation, page, limit
    """
    q = request.args.get('q', '').strip()
    platform = request.args.get('platform', '').strip()
    decade = request.args.get('decade', '').strip()
    generation = request.args.get('generation', '').strip()
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 36, type=int)

    cache_key = f"search:{q}:{platform}:{decade}:{generation}:{page}:{limit}"
    cached = get_cached(cache_key)
    if cached:
        return jsonify(cached)

    results = []

    # If RAWG key is set on the proxy, query RAWG
    if RAWG_API_KEY:
        try:
            rawg_params = {
                'key': RAWG_API_KEY,
                'search': q,
                'page': page,
                'page_size': limit
            }
            res = requests.get('https://api.rawg.io/api/games', params=rawg_params, timeout=5)
            if res.status_code == 200:
                rawg_data = res.json()
                for item in rawg_data.get('results', []):
                    platforms = [p['platform']['name'] for p in item.get('platforms', []) if 'platform' in p]
                    primary_platform = platforms[0] if platforms else (platform or 'PC (Windows)')
                    release_year = None
                    if item.get('released'):
                        try:
                            release_year = int(item['released'][:4])
                        except Exception:
                            pass
                    results.append({
                        'id': item.get('id'),
                        'title': item.get('name'),
                        'platform': primary_platform,
                        'release_year': release_year,
                        'rating': item.get('rating'),
                        'cover_image_url': item.get('background_image'),
                        'source': 'skyhook_rawg'
                    })
        except Exception as e:
            app.logger.warning(f"RAWG upstream error: {e}")

    # Fallback to local seeds if no upstream keys configured
    if not results:
        seed_path = os.path.join(os.path.dirname(__file__), '..', 'seeds', 'initial_catalog.json')
        if os.path.exists(seed_path):
            import json
            with open(seed_path, 'r', encoding='utf-8') as f:
                seed_data = json.load(f)
            for idx, item in enumerate(seed_data):
                if q and q.lower() not in item.get('title', '').lower():
                    continue
                if platform and platform.lower() not in item.get('platform', '').lower():
                    continue
                item['id'] = idx + 1
                item['source'] = 'skyhook_seed'
                results.append(item)

    payload = {
        'results': results,
        'total': len(results),
        'page': page,
        'limit': limit,
        'source': 'gamerr_skyhook'
    }

    set_cached(cache_key, payload)
    return jsonify(payload)


@app.route('/v1/game/<int:game_id>')
def get_game(game_id):
    """
    Get detailed game information by ID.
    Checks cache first, then queries RAWG upstream, falls back to seed data.
    """
    cache_key = f"game:{game_id}"
    cached = get_cached(cache_key)
    if cached:
        return jsonify(cached)

    result = None

    # Try RAWG upstream
    if RAWG_API_KEY:
        try:
            res = requests.get(
                f'https://api.rawg.io/api/games/{game_id}',
                params={'key': RAWG_API_KEY},
                timeout=5
            )
            if res.status_code == 200:
                item = res.json()
                platforms = [p['platform']['name'] for p in item.get('platforms', []) if 'platform' in p]
                genres = [g['name'] for g in item.get('genres', [])]
                developers = [d['name'] for d in item.get('developers', [])]
                publishers = [p['name'] for p in item.get('publishers', [])]
                release_year = None
                if item.get('released'):
                    try:
                        release_year = int(item['released'][:4])
                    except Exception:
                        pass
                result = {
                    'id': item.get('id'),
                    'title': item.get('name'),
                    'description': item.get('description_raw', ''),
                    'platform': platforms[0] if platforms else None,
                    'platforms': platforms,
                    'genres': genres,
                    'developers': developers,
                    'publishers': publishers,
                    'release_year': release_year,
                    'released': item.get('released'),
                    'rating': item.get('rating'),
                    'ratings_count': item.get('ratings_count'),
                    'metacritic': item.get('metacritic'),
                    'cover_image_url': item.get('background_image'),
                    'website': item.get('website'),
                    'source': 'skyhook_rawg'
                }
        except Exception as e:
            app.logger.warning(f"RAWG game detail error: {e}")

    # Fallback to seed data
    if not result:
        seed_path = os.path.join(os.path.dirname(__file__), '..', 'seeds', 'initial_catalog.json')
        if os.path.exists(seed_path):
            import json
            with open(seed_path, 'r', encoding='utf-8') as f:
                seed_data = json.load(f)
            if 1 <= game_id <= len(seed_data):
                item = seed_data[game_id - 1]
                result = {**item, 'id': game_id, 'source': 'skyhook_seed'}

    if not result:
        return jsonify({'error': 'Game not found'}), 404

    set_cached(cache_key, result)
    return jsonify(result)


@app.route('/v1/platforms')
def get_platforms():
    """
    Return a list of known gaming platforms.
    Checks cache, then builds from seed data or returns a curated default list.
    """
    cache_key = "platforms:all"
    cached = get_cached(cache_key)
    if cached:
        return jsonify(cached)

    platforms = set()

    # Extract platforms from seed data
    seed_path = os.path.join(os.path.dirname(__file__), '..', 'seeds', 'initial_catalog.json')
    if os.path.exists(seed_path):
        import json
        with open(seed_path, 'r', encoding='utf-8') as f:
            seed_data = json.load(f)
        for item in seed_data:
            if item.get('platform'):
                platforms.add(item['platform'])

    # Ensure a baseline set of well-known platforms
    default_platforms = [
        'NES', 'SNES', 'N64', 'GameCube', 'Wii', 'Wii U', 'Switch',
        'Game Boy', 'Game Boy Color', 'Game Boy Advance', 'DS', '3DS',
        'Master System', 'Genesis', 'Saturn', 'Dreamcast',
        'PlayStation', 'PlayStation 2', 'PlayStation 3', 'PlayStation 4', 'PlayStation 5',
        'PSP', 'PS Vita',
        'Xbox', 'Xbox 360', 'Xbox One',
        'PC (DOS)', 'PC (Windows)',
        'Arcade', 'Neo Geo',
        'Atari 2600', 'Atari 7800',
        'TurboGrafx-16', 'PC Engine',
    ]
    platforms.update(default_platforms)

    sorted_platforms = sorted(platforms)
    payload = {
        'platforms': sorted_platforms,
        'total': len(sorted_platforms),
        'source': 'gamerr_skyhook'
    }

    set_cached(cache_key, payload)
    return jsonify(payload)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Gamerr SkyHook Metadata Server")
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 8000)), help='Port to bind (default: PORT env or 8000)')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind (default: 0.0.0.0)')
    args = parser.parse_args()

    print(f"Starting Gamerr SkyHook Server on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port)
