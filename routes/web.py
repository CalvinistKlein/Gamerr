"""
Web routes for Romarr UI
"""

from flask import Blueprint, render_template, jsonify, request
import os
from models.unified_schema import Game, WantedGame, Download, GameCatalog, Platform
from models.settings import Settings
from config.constants import COLORS, PLATFORMS

web_bp = Blueprint('web', __name__)

# Generation and Decade mapping
GENERATIONS = {
    1: {'id': 1, 'label': 'Gen 1 (1972–1977)', 'years': (1972, 1977), 'era': 'Early Arcades & Pong'},
    2: {'id': 2, 'label': 'Gen 2 (1976–1983)', 'years': (1976, 1983), 'era': 'Atari 2600 & Early PC'},
    3: {'id': 3, 'label': 'Gen 3 (1983–1990)', 'years': (1983, 1990), 'era': '8-Bit (NES, C64, Early DOS)'},
    4: {'id': 4, 'label': 'Gen 4 (1987–1996)', 'years': (1987, 1996), 'era': '16-Bit (SNES, Genesis, DOS VGA, Amiga)'},
    5: {'id': 5, 'label': 'Gen 5 (1993–2002)', 'years': (1993, 2002), 'era': '32/64-Bit 3D (PS1, N64, Win95/98)'},
    6: {'id': 6, 'label': 'Gen 6 (1998–2006)', 'years': (1998, 2006), 'era': '128-Bit / DVD (PS2, Xbox, WinXP)'},
    7: {'id': 7, 'label': 'Gen 7 (2005–2013)', 'years': (2005, 2013), 'era': 'HD Era (X360, PS3, Wii, Steam)'},
    8: {'id': 8, 'label': 'Gen 8 (2012–2020)', 'years': (2012, 2020), 'era': 'Connected Era (PS4, XOne, Switch)'},
    9: {'id': 9, 'label': 'Gen 9 (2020–Present)', 'years': (2020, 2030), 'era': 'Modern 4K / Raytracing'},
}

DECADES = ['1970s', '1980s', '1990s', '2000s', '2010s', '2020s']

@web_bp.context_processor
def inject_globals():
    return {
        'colors': COLORS,
        'platforms': PLATFORMS,
        'generations': GENERATIONS,
        'decades': DECADES
    }

@web_bp.route('/')
def index():
    """Dashboard page"""
    # Get stats for dashboard
    library_count = Game.get_library_count()
    wanted_count = WantedGame.get_active_count()
    active_downloads = Download.get_active()
    
    # Get recent activity
    recent_games = Game.query.order_by(Game.created_at.desc()).limit(5).all()
    recent_wanted = WantedGame.query.order_by(WantedGame.added_date.desc()).limit(5).all()
    
    # Get configuration for status display
    prowlarr_config = Settings.get_prowlarr_config()
    qbittorrent_config = Settings.get_qbittorrent_config()
    network_config = Settings.get_network_config()
    
    # Create recent activity list
    recent_activity = []
    
    # Add recent games as "add" activity
    for game in recent_games:
        recent_activity.append({
            'type': 'add',
            'message': f'Added {game.title} ({game.platform}) to library',
            'time': game.added_date.strftime('%Y-%m-%d %H:%M') if game.added_date else 'Recently'
        })
    
    # Add recent wanted games as "search" activity
    for wanted in recent_wanted:
        recent_activity.append({
            'type': 'search',
            'message': f'Added {wanted.game_title} ({wanted.platform}) to wanted list',
            'time': wanted.added_date.strftime('%Y-%m-%d %H:%M') if wanted.added_date else 'Recently'
        })
    
    # Sort by time (simplified - in reality you'd sort by actual timestamp)
    recent_activity = sorted(recent_activity, key=lambda x: x['time'], reverse=True)[:10]
    
    return render_template('index.html',
                         library_count=library_count,
                         wanted_count=wanted_count,
                         active_downloads=active_downloads,
                         recent_activity=recent_activity,
                         recent_wanted=recent_wanted,
                         prowlarr_config=prowlarr_config,
                         qbittorrent_config=qbittorrent_config,
                         network_config=network_config)

@web_bp.route('/library')
def library():
    """Game library page — paginated with Sonarr/Radarr filtering by Platform, Decade, Generation, and View"""
    from extensions import db
    page = request.args.get('page', 1, type=int)
    if page is None:
        page = 1
    page = max(1, page)
    view_mode = request.args.get('view', 'table').strip()
    per_page = 36 if view_mode == 'posters' else 50
    query_str = request.args.get('q', '').strip()
    platform = request.args.get('platform', '').strip()
    decade = request.args.get('decade', '').strip()
    generation = request.args.get('generation', type=int)
    sort_by = request.args.get('sort', 'title').strip()

    q = Game.query
    if query_str:
        q = q.filter(Game.title.ilike(f'%{query_str}%'))
    if platform:
        q = q.join(Game.platforms).filter(
            (Platform.slug == platform.lower()) | (Platform.name.ilike(platform))
        )
    if decade and decade.endswith('s') and decade[:-1].isdigit():
        start_year = int(decade[:-1])
        end_year = start_year + 9
        q = q.filter(Game.release_year.between(start_year, end_year))
    if generation and generation in GENERATIONS:
        gen_info = GENERATIONS[generation]
        gen_start, gen_end = gen_info['years']
        q = q.filter(
            db.or_(
                Game.platforms.any(Platform.generation == generation),
                db.and_(
                    Game.release_year.between(gen_start, gen_end),
                    Game.platforms.any(Platform.slug.in_(['dos', 'windows', 'scummvm', 'c64', 'amiga']))
                )
            )
        )

    if sort_by == 'newest':
        q = q.order_by(Game.release_year.desc().nullslast(), Game.title.asc())
    elif sort_by == 'oldest':
        q = q.order_by(Game.release_year.asc().nullslast(), Game.title.asc())
    elif sort_by == 'rating':
        q = q.order_by(Game.rating.desc().nullslast(), Game.title.asc())
    else:
        q = q.order_by(Game.title.asc())

    total = q.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    games = q.offset((page - 1) * per_page).limit(per_page).all()

    return render_template('library.html',
                           games=games,
                           page=page,
                           total_pages=total_pages,
                           total_games=total,
                           query=query_str,
                           platform=platform,
                           decade=decade,
                           generation=generation,
                           sort=sort_by,
                           view=view_mode,
                           platforms=PLATFORMS,
                           colors=COLORS)

@web_bp.route('/wanted')
def wanted():
    """Wanted games page"""
    wanted_games = WantedGame.query.order_by(WantedGame.priority.desc(), WantedGame.added_date.desc()).all()
    return render_template('wanted.html', wanted_games=wanted_games)

@web_bp.route('/downloads')
def downloads():
    """Downloads page — paginated to avoid loading all rows at once"""
    page = request.args.get('page', 1, type=int)
    if page is None:
        page = 1
    page = max(1, page)
    per_page = 50
    status_filter = request.args.get('status', '')

    q = Download.query
    if status_filter:
        q = q.filter(Download.status == status_filter)

    total = q.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    downloads_list = q.order_by(Download.added_date.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return render_template('downloads.html', downloads=downloads_list,
                           page=page, total_pages=total_pages,
                           status_filter=status_filter)

@web_bp.route('/catalog')
def catalog():
    """Game catalog page with Sonarr/Radarr filtering by Platform, Decade, Generation, and View"""
    from extensions import db
    query = request.args.get('q', '').strip()
    platform = request.args.get('platform', '').strip()
    decade = request.args.get('decade', '').strip()
    generation = request.args.get('generation', type=int)
    sort_by = request.args.get('sort', 'popular').strip()
    view_mode = request.args.get('view', 'posters').strip()
    page = request.args.get('page', 1, type=int)
    if page is None:
        page = 1
    page = max(1, page)
    per_page = 36 if view_mode == 'posters' else 50
    
    catalog_query = GameCatalog.query
    
    # Text Search
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
    
    # Generation Filter (Console Gen + PC Titles from that Era)
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
    if sort_by == 'newest':
        catalog_query = catalog_query.order_by(GameCatalog.release_year.desc().nullslast(), GameCatalog.title.asc())
    elif sort_by == 'oldest':
        catalog_query = catalog_query.order_by(GameCatalog.release_year.asc().nullslast(), GameCatalog.title.asc())
    elif sort_by == 'title':
        catalog_query = catalog_query.order_by(GameCatalog.title.asc())
    elif sort_by == 'rating':
        catalog_query = catalog_query.order_by(GameCatalog.rating.desc().nullslast(), GameCatalog.title.asc())
    else:  # 'popular'
        catalog_query = catalog_query.order_by(GameCatalog.rating.desc().nullslast(), GameCatalog.download_count.desc(), GameCatalog.title.asc())
    
    total_count = catalog_query.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    games = catalog_query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Get all platforms in catalog
    db_platforms = [p[0] for p in db.session.query(GameCatalog.platform).distinct().order_by(GameCatalog.platform).all() if p[0]]
    all_platforms = sorted(list(set(PLATFORMS + db_platforms)))
    
    # Get set of wanted / library game titles for quick monitored status lookup
    monitored_titles = set(w.game_title.lower() for w in WantedGame.query.all())
    library_titles = set(g.title.lower() for g in Game.query.all())
    
    return render_template('catalog.html', 
                         games=games, 
                         colors=COLORS,
                         query=query,
                         platforms=all_platforms,
                         current_platform=platform,
                         decade=decade,
                         generation=generation,
                         sort=sort_by,
                         view=view_mode,
                         monitored_titles=monitored_titles,
                         library_titles=library_titles,
                         page=page,
                         total_pages=total_pages,
                         total_count=total_count)

@web_bp.route('/catalog/<int:game_id>')
def catalog_game(game_id):
    """Individual catalog game page"""
    from models.unified_schema import GameCatalog
    game = GameCatalog.query.get_or_404(game_id)
    return render_template('catalog_game.html', game=game, colors=COLORS)

@web_bp.route('/import')
def import_roms():
    """Import ROMs page"""
    return render_template('import.html')

@web_bp.route('/settings')
def settings():
    """Settings page"""
    from models.settings import Settings
    from scripts.database_manager import get_database_info
    
    prowlarr_config = Settings.get_prowlarr_config()
    qbittorrent_config = Settings.get_qbittorrent_config()
    network_config = Settings.get_network_config()
    download_config = Settings.get_download_config()
    metadata_config = Settings.get_metadata_config()

    
    # Get database info
    instance_path = os.path.join(os.getcwd(), 'instance', 'romarr.db')
    try:
        db_info = get_database_info(instance_path)
    except Exception as e:
        print(f"Error fetching database info for settings: {e}")
        db_info = None
    
    # Get general config
    general_config = {
        'theme': Settings.get('theme', 'dark'),
        'language': Settings.get('language', 'en'),
        'timezone': Settings.get('timezone', 'UTC'),
        'notifications_enabled': Settings.get('notifications_enabled', 'true') == 'true'
    }
    
    import socket
    try:
        hostname = socket.gethostname()
    except:
        hostname = 'localhost'
        
    return render_template('settings.html', 
                         prowlarr_config=prowlarr_config,
                         qbittorrent_config=qbittorrent_config,
                         network_config=network_config,
                         download_config=download_config,
                         general_config=general_config,
                         metadata_config=metadata_config,
                         db_info=db_info,
                         hostname=hostname)

## /api/stats route moved to api_bp to avoid blueprint route collision

