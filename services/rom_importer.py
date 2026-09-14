"""
ROM Importer Service
Integrates ROM scanning with database storage using the unified schema
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from extensions import db
from services.rom_scanner import ROMScanner, ROMFile as ScannedROMFile
from models.unified_schema import Game, ROMFile, Platform, Genre, find_game_by_hash, create_game_from_rom_file

# Configure logging
logger = logging.getLogger(__name__)


class ROMImporter:
    """Service for importing ROM files into the database"""
    
    @classmethod
    def import_directory(cls, directory_path: str, recursive: bool = True) -> Dict:
        """
        Import all ROM files from a directory into the database
        
        Args:
            directory_path: Path to scan for ROM files
            recursive: Whether to scan subdirectories
            
        Returns:
            Dictionary with import statistics
        """
        logger.info(f"Starting import of directory: {directory_path}")
        start_time = datetime.now()
        
        # Scan directory for ROM files
        scanner = ROMScanner()
        scanned_files = scanner.scan_directory(directory_path, recursive)
        
        logger.info(f"Found {len(scanned_files)} ROM files to process")
        
        # Statistics
        stats = {
            'total_files': len(scanned_files),
            'new_games': 0,
            'existing_games': 0,
            'new_rom_files': 0,
            'existing_rom_files': 0,
            'errors': 0,
            'processing_time': 0,
            'games': [],
        }
        
        # Process each file
        for scanned_file in scanned_files:
            try:
                result = cls._process_rom_file(scanned_file)
                
                if result['status'] == 'new_game':
                    stats['new_games'] += 1
                    stats['new_rom_files'] += 1
                elif result['status'] == 'existing_game_new_rom':
                    stats['existing_games'] += 1
                    stats['new_rom_files'] += 1
                elif result['status'] == 'existing_rom':
                    stats['existing_games'] += 1
                    stats['existing_rom_files'] += 1
                
                stats['games'].append(result)
                
            except Exception as e:
                logger.error(f"Error processing file {scanned_file.filename}: {e}")
                stats['errors'] += 1
        
        # Commit all changes
        try:
            db.session.commit()
            logger.info(f"Database changes committed successfully")
        except Exception as e:
            logger.error(f"Error committing database changes: {e}")
            db.session.rollback()
            stats['errors'] += len(scanned_files)  # All changes failed
        
        # Calculate processing time
        end_time = datetime.now()
        stats['processing_time'] = (end_time - start_time).total_seconds()
        
        logger.info(f"Import completed: {stats}")
        return stats
    
    @classmethod
    def _process_rom_file(cls, scanned_file: ScannedROMFile) -> Dict:
        """
        Process a single ROM file and store it in the database
        
        Args:
            scanned_file: Scanned ROM file object
            
        Returns:
            Dictionary with processing results
        """
        # Check if ROM file already exists by hash
        existing_game = None
        
        if scanned_file.crc32:
            existing_game = find_game_by_hash(crc32=scanned_file.crc32)
        
        if not existing_game and scanned_file.md5:
            existing_game = find_game_by_hash(md5=scanned_file.md5)
        
        if not existing_game and scanned_file.sha1:
            existing_game = find_game_by_hash(sha1=scanned_file.sha1)
        
        if existing_game:
            # Check if this specific ROM file already exists for the game
            existing_rom = cls._find_existing_rom_file(existing_game, scanned_file)
            
            if existing_rom:
                # Update last scanned timestamp
                existing_rom.last_scanned = datetime.utcnow()
                return {
                    'status': 'existing_rom',
                    'game_id': existing_game.id,
                    'game_title': existing_game.title,
                    'rom_file_id': existing_rom.id,
                    'filename': scanned_file.filename,
                    'message': 'ROM file already exists in database'
                }
            else:
                # Add new ROM file to existing game
                new_rom = cls._create_rom_file_object(scanned_file, existing_game.id)
                db.session.add(new_rom)
                
                return {
                    'status': 'existing_game_new_rom',
                    'game_id': existing_game.id,
                    'game_title': existing_game.title,
                    'rom_file_id': new_rom.id,
                    'filename': scanned_file.filename,
                    'message': 'Added new ROM file to existing game'
                }
        else:
            # Create new game from ROM file
            rom_file_data = {
                'file_path': scanned_file.path,
                'file_name': scanned_file.filename,
                'file_size': scanned_file.size,
                'file_extension': scanned_file.extension,
                'crc32': scanned_file.crc32,
                'md5': scanned_file.md5,
                'sha1': scanned_file.sha1,
                'region': scanned_file.region,
                'version': scanned_file.version,
                'language': scanned_file.language,
                'detected_platform': scanned_file.platform,
                'detection_confidence': scanned_file.confidence,
                'detection_method': scanned_file.detection_method,
                'title': scanned_file.title,
            }
            
            new_game = create_game_from_rom_file(rom_file_data)
            
            # Try to find and associate platform
            if scanned_file.platform:
                platform = cls._find_or_create_platform(scanned_file.platform)
                if platform and platform not in new_game.platforms:
                    new_game.platforms.append(platform)
            
            return {
                'status': 'new_game',
                'game_id': new_game.id,
                'game_title': new_game.title,
                'rom_file_id': new_game.rom_files[0].id if new_game.rom_files else None,
                'filename': scanned_file.filename,
                'message': 'Created new game from ROM file'
            }
    
    @classmethod
    def _find_existing_rom_file(cls, game: Game, scanned_file: ScannedROMFile) -> Optional[ROMFile]:
        """
        Find if a ROM file already exists for a game
        
        Args:
            game: Game object
            scanned_file: Scanned ROM file
            
        Returns:
            Existing ROMFile object or None
        """
        # Check by file path first (most reliable)
        for rom_file in game.rom_files:
            if rom_file.file_path == scanned_file.path:
                return rom_file
        
        # Check by hashes
        for rom_file in game.rom_files:
            if scanned_file.crc32 and rom_file.crc32 == scanned_file.crc32:
                return rom_file
            if scanned_file.md5 and rom_file.md5 == scanned_file.md5:
                return rom_file
            if scanned_file.sha1 and rom_file.sha1 == scanned_file.sha1:
                return rom_file
        
        return None
    
    @classmethod
    def _create_rom_file_object(cls, scanned_file: ScannedROMFile, game_id: int) -> ROMFile:
        """
        Create a ROMFile database object from scanned file
        
        Args:
            scanned_file: Scanned ROM file
            game_id: ID of the parent game
            
        Returns:
            ROMFile object
        """
        return ROMFile(
            game_id=game_id,
            file_path=scanned_file.path,
            file_name=scanned_file.filename,
            file_size=scanned_file.size,
            file_extension=scanned_file.extension,
            crc32=scanned_file.crc32,
            md5=scanned_file.md5,
            sha1=scanned_file.sha1,
            region=scanned_file.region,
            version=scanned_file.version,
            language=scanned_file.language,
            detected_platform=scanned_file.platform,
            detection_confidence=scanned_file.confidence,
            detection_method=scanned_file.detection_method,
            imported_at=datetime.utcnow(),
            last_scanned=datetime.utcnow(),
        )
    
    @classmethod
    def _find_or_create_platform(cls, platform_name: str) -> Optional[Platform]:
        """
        Find or create a platform by name
        
        Args:
            platform_name: Name of the platform
            
        Returns:
            Platform object or None
        """
        # Try to find by exact name
        platform = Platform.query.filter_by(name=platform_name).first()
        if platform:
            return platform
        
        # Try to find by slug
        from models.unified_schema import create_slug
        slug = create_slug(platform_name)
        platform = Platform.query.filter_by(slug=slug).first()
        if platform:
            return platform
        
        # Create new platform
        try:
            platform = Platform(
                name=platform_name,
                slug=slug,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.session.add(platform)
            return platform
        except Exception as e:
            logger.error(f"Error creating platform {platform_name}: {e}")
            return None
    
    @classmethod
    def get_import_statistics(cls) -> Dict:
        """
        Get overall import statistics from database
        
        Returns:
            Dictionary with statistics
        """
        total_games = Game.query.count()
        total_rom_files = ROMFile.query.count()
        total_platforms = Platform.query.count()
        total_genres = Genre.query.count()
        
        # Games by platform
        from sqlalchemy import func
        from sqlalchemy.orm import aliased
        
        # This is a simplified query - in production you'd want a proper join
        games_by_platform = {}
        for platform in Platform.query.all():
            # Count games associated with this platform
            count = db.session.query(func.count(Game.id)).join(
                Game.platforms
            ).filter(Platform.id == platform.id).scalar()
            if count > 0:
                games_by_platform[platform.name] = count
        
        # ROM files by verification status
        verified_count = ROMFile.query.filter_by(is_verified=True).count()
        unverified_count = total_rom_files - verified_count
        
        return {
            'total_games': total_games,
            'total_rom_files': total_rom_files,
            'total_platforms': total_platforms,
            'total_genres': total_genres,
            'games_by_platform': games_by_platform,
            'verified_rom_files': verified_count,
            'unverified_rom_files': unverified_count,
            'metadata_completeness_avg': db.session.query(func.avg(Game.metadata_completeness)).scalar() or 0,
        }

    @classmethod
    def import_rom_entries(cls, rom_entries: List[Dict]) -> Dict:
        """
        Import a list of ROM entry dictionaries (e.g. from web UI or API).
        """
        stats = {
            'total': len(rom_entries),
            'imported': 0,
            'skipped': 0,
            'failed': 0,
            'errors': [],
            'details': []
        }
        
        for item in rom_entries:
            try:
                path = item.get('file_path') or item.get('path') or ''
                filename = item.get('filename') or (os.path.basename(path) if path else 'unknown')
                platform = item.get('detected_platform') or item.get('platform') or 'Unknown'
                title = item.get('detected_title') or item.get('title') or filename
                region = item.get('detected_region') or item.get('region')
                size = item.get('file_size') or (os.path.getsize(path) if (path and os.path.exists(path)) else 0)
                ext = Path(filename).suffix if filename else ''
                
                scanned_file = ScannedROMFile(
                    path=path,
                    filename=filename,
                    size=size,
                    modified_time=datetime.utcnow(),
                    platform=platform,
                    extension=ext,
                    crc32=item.get('crc32'),
                    md5=item.get('md5'),
                    sha1=item.get('sha1'),
                    title=title,
                    region=region,
                    version=item.get('version'),
                    language=item.get('language'),
                    confidence=1.0 if item.get('confidence') == 'high' else 0.5,
                    detection_method='web_import',
                    raw_filename=filename
                )
                
                result = cls._process_rom_file(scanned_file)
                if result.get('status') in ('new_game', 'existing_game_new_rom'):
                    stats['imported'] += 1
                elif result.get('status') == 'existing_rom':
                    stats['skipped'] += 1
                else:
                    stats['imported'] += 1
                stats['details'].append(result)
            except Exception as e:
                logger.error(f"Error importing item {item}: {e}")
                stats['failed'] += 1
                stats['errors'].append(f"{item.get('filename', 'Unknown file')}: {str(e)}")
                
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to commit imported entries: {e}")
            db.session.rollback()
            stats['failed'] += stats['imported']
            stats['imported'] = 0
            stats['errors'].append(f"Database commit error: {str(e)}")
            
        return stats


# Command-line interface
if __name__ == "__main__":
    import argparse
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='Import ROM files into database')
    parser.add_argument('directory', help='Directory to scan for ROM files')
    parser.add_argument('--recursive', '-r', action='store_true', help='Scan subdirectories recursively')
    parser.add_argument('--stats', '-s', action='store_true', help='Show database statistics')
    
    args = parser.parse_args()
    
    if args.stats:
        # Show statistics
        from app import create_app
        app = create_app()
        with app.app_context():
            stats = ROMImporter.get_import_statistics()
            print("\n=== Database Statistics ===")
            print(f"Total games: {stats['total_games']}")
            print(f"Total ROM files: {stats['total_rom_files']}")
            print(f"Total platforms: {stats['total_platforms']}")
            print(f"Verified ROM files: {stats['verified_rom_files']}")
            print(f"Unverified ROM files: {stats['unverified_rom_files']}")
            print(f"Average metadata completeness: {stats['metadata_completeness_avg']:.2%}")
            print("\nGames by platform:")
            for platform, count in stats['games_by_platform'].items():
                print(f"  {platform}: {count}")
    else:
        # Import directory
        if not os.path.exists(args.directory):
            print(f"Error: Directory '{args.directory}' does not exist")
            sys.exit(1)
        
        from app import create_app
        app = create_app()
        with app.app_context():
            print(f"Importing ROM files from '{args.directory}' (recursive: {args.recursive})")
            stats = ROMImporter.import_directory(args.directory, args.recursive)
            
            print("\n=== Import Results ===")
            print(f"Total files scanned: {stats['total_files']}")
            print(f"New games created: {stats['new_games']}")
            print(f"Existing games updated: {stats['existing_games']}")
            print(f"New ROM files added: {stats['new_rom_files']}")
            print(f"Existing ROM files skipped: {stats['existing_rom_files']}")
            print(f"Errors: {stats['errors']}")
            print(f"Processing time: {stats['processing_time']:.2f} seconds")
            
            if stats['errors'] > 0:
                print("\nNote: Some files had errors. Check the logs for details.")
            
            print("\nSample of processed games:")
            for i, game in enumerate(stats['games'][:5], 1):
                print(f"  {i}. {game['filename']} - {game['message']}")