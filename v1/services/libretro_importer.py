"""
Libretro Database Importer Service
Parses libretro-database DAT files and imports game metadata into GameCatalog
"""

import os
import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from extensions import db
from models.unified_schema import GameCatalog


class LibretroImporter:
    """Service for importing libretro-database metadata"""
    
    # Platform mapping from libretro DAT filenames to our platform names
    PLATFORM_MAPPING = {
        'Nintendo - Super Nintendo Entertainment System': 'snes',
        'Nintendo - Nintendo Entertainment System': 'nes',
        'Nintendo - Game Boy': 'gb',
        'Nintendo - Game Boy Color': 'gbc',
        'Nintendo - Game Boy Advance': 'gba',
        'Nintendo - Nintendo 64': 'n64',
        'Nintendo - Nintendo 64DD': 'n64dd',
        'Nintendo - Virtual Boy': 'virtualboy',
        'Sega - Genesis': 'genesis',
        'Sega - Mega Drive': 'megadrive',
        'Sega - Game Gear': 'gamegear',
        'Sega - Master System': 'mastersystem',
        'Sega - Saturn': 'saturn',
        'Sega - Dreamcast': 'dreamcast',
        'Sony - PlayStation': 'ps1',
        'Sony - PlayStation 2': 'ps2',
        'Sony - PlayStation Portable': 'psp',
        'Microsoft - Xbox': 'xbox',
        'NEC - PC Engine - TurboGrafx 16': 'pcengine',
        'NEC - PC Engine CD - TurboGrafx-CD': 'pcenginecd',
        'SNK - Neo Geo Pocket': 'ngp',
        'SNK - Neo Geo Pocket Color': 'ngpc',
        'Atari - 2600': 'atari2600',
        'Atari - 7800': 'atari7800',
        'Atari - Lynx': 'atarilynx',
        'Bandai - WonderSwan': 'wonderswan',
        'Bandai - WonderSwan Color': 'wonderswancolor',
    }
    
    @classmethod
    def parse_dat_file(cls, filepath: str) -> List[Dict]:
        """Parse a libretro DAT file and extract game information"""
        games = []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract platform from filename
            filename = os.path.basename(filepath)
            platform_name = filename.replace('.dat', '')
            platform = cls.PLATFORM_MAPPING.get(platform_name, platform_name.lower())
            
            # Parse game entries using regex
            # Format: game ( comment "Game Title (Region)" publisher "Publisher" rom ( crc XXXXXXXX ) )
            game_pattern = r'game\s*\(\s*comment\s+"([^"]+)"\s+publisher\s+"([^"]*)"'
            
            for match in re.finditer(game_pattern, content, re.DOTALL):
                comment = match.group(1)
                publisher = match.group(2) if match.group(2) else None
                
                # Parse game title and region from comment
                title, region = cls._parse_game_comment(comment)
                
                # Extract CRC if available
                crc_match = re.search(r'rom\s*\(\s*crc\s+([0-9A-F]+)\s*\)', match.group(0))
                crc = crc_match.group(1) if crc_match else None
                
                game_data = {
                    'title': title,
                    'platform': platform,
                    'region': region,
                    'publisher': publisher,
                    'crc': crc,
                    'source': 'libretro',
                    'source_id': f"{platform}_{crc}" if crc else f"{platform}_{title}",
                    'raw_comment': comment
                }
                
                games.append(game_data)
                
        except Exception as e:
            print(f"Error parsing DAT file {filepath}: {e}")
        
        return games
    
    @classmethod
    def _parse_game_comment(cls, comment: str) -> Tuple[str, Optional[str]]:
        """Parse game comment to extract title and region"""
        # Common patterns: "Title (Region)" or "Title (Region) (Other Info)"
        title = comment
        region = None
        
        # Extract region from parentheses
        region_match = re.search(r'\(([^)]+)\)', comment)
        if region_match:
            region_text = region_match.group(1)
            
            # Common region abbreviations
            region_abbr = {
                'USA': 'us',
                'Europe': 'eu',
                'Japan': 'jp',
                'Germany': 'de',
                'France': 'fr',
                'Spain': 'es',
                'Italy': 'it',
                'Australia': 'au',
                'Brazil': 'br',
                'Korea': 'kr',
                'Asia': 'asia',
                'World': 'world'
            }
            
            # Check if region text matches known regions
            for full_name, abbr in region_abbr.items():
                if full_name in region_text:
                    region = abbr
                    break
            
            # If no match, use the text as-is (might be demo, prototype, etc.)
            if not region:
                # Check for common patterns
                if 'Demo' in region_text or 'Sample' in region_text:
                    region = 'demo'
                elif 'Beta' in region_text or 'Prototype' in region_text:
                    region = 'beta'
                elif 'Rev' in region_text or 'Revision' in region_text:
                    region = 'rev'
                else:
                    region = region_text.lower()
        
        # Clean title - remove region info from parentheses
        title = re.sub(r'\s*\([^)]+\)\s*$', '', comment).strip()
        
        return title, region
    
    @classmethod
    def import_dat_directory(cls, directory_path: str, limit_per_platform: int = 100) -> Dict:
        """Import all DAT files from a directory"""
        stats = {
            'total_files': 0,
            'total_games': 0,
            'imported_games': 0,
            'skipped_games': 0,
            'platforms': {}
        }
        
        try:
            # Find all DAT files
            dat_files = []
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    if file.endswith('.dat'):
                        dat_files.append(os.path.join(root, file))
            
            stats['total_files'] = len(dat_files)
            
            for dat_file in dat_files:
                platform_name = os.path.basename(dat_file).replace('.dat', '')
                print(f"Processing {platform_name}...")
                
                # Parse games from DAT file
                games = cls.parse_dat_file(dat_file)
                
                if not games:
                    continue
                
                platform_stats = {
                    'parsed': len(games),
                    'imported': 0,
                    'skipped': 0
                }
                
                # Limit games per platform to avoid overwhelming the database
                games_to_import = games[:limit_per_platform] if limit_per_platform else games
                
                for game_data in games_to_import:
                    try:
                        # Check if game already exists
                        existing = GameCatalog.query.filter_by(
                            title=game_data['title'],
                            platform=game_data['platform'],
                            source='libretro'
                        ).first()
                        
                        if existing:
                            # Update existing entry
                            existing.region = game_data['region']
                            existing.publisher = game_data['publisher']
                            existing.last_updated = datetime.utcnow()
                            platform_stats['skipped'] += 1
                            stats['skipped_games'] += 1
                        else:
                            # Create new entry
                            game = GameCatalog(
                                title=game_data['title'],
                                platform=game_data['platform'],
                                region=game_data['region'],
                                publisher=game_data['publisher'],
                                source='libretro',
                                source_id=game_data['source_id'],
                                last_updated=datetime.utcnow()
                            )
                            db.session.add(game)
                            platform_stats['imported'] += 1
                            stats['imported_games'] += 1
                        
                        stats['total_games'] += 1
                        
                    except Exception as e:
                        print(f"Error importing game {game_data['title']}: {e}")
                        platform_stats['skipped'] += 1
                        stats['skipped_games'] += 1
                
                # Commit after each platform
                db.session.commit()
                
                stats['platforms'][platform_name] = platform_stats
                print(f"  Imported {platform_stats['imported']} games, skipped {platform_stats['skipped']}")
            
            print(f"Import complete: {stats['imported_games']} games imported, {stats['skipped_games']} skipped")
            
        except Exception as e:
            print(f"Error importing DAT directory: {e}")
            db.session.rollback()
        
        return stats
    
    @classmethod
    def search_games(cls, query: str, platform: str = None, limit: int = 50) -> List[Dict]:
        """Search games in the catalog"""
        search_query = GameCatalog.query
        
        if query:
            search_query = search_query.filter(GameCatalog.title.ilike(f'%{query}%'))
        
        if platform:
            search_query = search_query.filter_by(platform=platform)
        
        games = search_query.order_by(GameCatalog.title).limit(limit).all()
        
        return [game.to_dict() for game in games]
    
    @classmethod
    def get_platforms(cls) -> List[str]:
        """Get list of available platforms in the catalog"""
        platforms = db.session.query(GameCatalog.platform).distinct().all()
        return [p[0] for p in platforms if p[0]]
    
    @classmethod
    def get_game_by_crc(cls, crc: str) -> Optional[GameCatalog]:
        """Find game by CRC hash"""
        # Note: We need to store CRC in the database first
        # For now, search by title patterns
        return None
    
    @classmethod
    def initialize_catalog(cls, dat_path: str = None) -> Dict:
        """Initialize the game catalog with libretro database"""
        if not dat_path:
            # Default path relative to project
            dat_path = os.path.join(os.path.dirname(__file__), '..', 'libretro-database', 'metadat', 'publisher')
        
        if not os.path.exists(dat_path):
            return {'error': f'DAT path not found: {dat_path}'}
        
        print(f"Initializing catalog from {dat_path}")
        return cls.import_dat_directory(dat_path, limit_per_platform=50)  # Limit for initial import
