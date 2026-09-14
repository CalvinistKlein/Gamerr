#!/usr/bin/env python3
"""
Retro Gaming Metadata Scraper
Main script for automating collection of game titles and metadata from DAT files and IGDB API
"""

import os
import sys
import argparse
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import csv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.dat_parser import DATParser, parse_dat_directory, GameEntry
from services.one_game_one_rom import OneGameOneRomFilter, apply_1g1r_to_dat_files
from services.igdb_client import IGDBClient, create_igdb_client, IGDBGame
from models.metadata_db import (
    MetadataDatabaseManager, MetadataGame, MetadataPlatform, MetadataGenre,
    MetadataCompany, MetadataROM, MetadataReleaseDate
)
from extensions import db, create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('retro_metadata_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RetroMetadataScraper:
    """Main scraper class that orchestrates DAT parsing, 1G1R filtering, and IGDB API integration"""
    
    def __init__(self, database_path: str = None, igdb_client: IGDBClient = None):
        """
        Initialize scraper
        
        Args:
            database_path: Path to SQLite database (optional)
            igdb_client: IGDB client instance (optional)
        """
        # Create Flask app context for database operations
        self.app = create_app()
        
        # Initialize IGDB client
        self.igdb_client = igdb_client or create_igdb_client()
        if not self.igdb_client:
            logger.warning("IGDB client not available. Set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET environment variables.")
        
        # Statistics
        self.stats = {
            'dat_files_parsed': 0,
            'games_found': 0,
            'games_after_1g1r': 0,
            'igdb_matches': 0,
            'igdb_failures': 0,
            'database_entries': 0,
            'start_time': datetime.utcnow(),
            'end_time': None
        }
    
    def parse_dat_files(self, dat_path: str, recursive: bool = True) -> Dict[str, List[GameEntry]]:
        """
        Parse DAT files from directory
        
        Args:
            dat_path: Path to DAT file or directory
            recursive: Search directories recursively
            
        Returns:
            Dictionary mapping platform names to list of GameEntry objects
        """
        logger.info(f"Parsing DAT files from: {dat_path}")
        
        if os.path.isfile(dat_path):
            # Single file
            parser = DATParser()
            games = parser.parse_file(dat_path)
            platform = parser.platform or os.path.splitext(os.path.basename(dat_path))[0]
            results = {platform: games}
        else:
            # Directory
            results = parse_dat_directory(dat_path, recursive)
        
        # Update statistics
        total_games = sum(len(games) for games in results.values())
        self.stats['dat_files_parsed'] = len(results)
        self.stats['games_found'] = total_games
        
        logger.info(f"Parsed {total_games} games from {len(results)} platforms")
        return results
    
    def apply_1g1r_filtering(self, dat_results: Dict[str, List[GameEntry]], 
                            filter_options: Dict = None) -> Dict[str, List[GameEntry]]:
        """
        Apply 1G1R filtering to DAT results
        
        Args:
            dat_results: Dictionary mapping platform names to list of GameEntry objects
            filter_options: Optional dictionary of filter options
            
        Returns:
            Filtered dictionary with one version per game per platform
        """
        logger.info("Applying 1G1R filtering...")
        
        if filter_options is None:
            filter_options = {
                'prefer_usa': True,
                'prefer_english': True,
                'exclude_prototypes': True,
                'exclude_demos': True,
                'exclude_pirates': True
            }
        
        filtered_results = apply_1g1r_to_dat_files(dat_results, filter_options)
        
        # Update statistics
        total_filtered = sum(len(games) for games in filtered_results.values())
        self.stats['games_after_1g1r'] = total_filtered
        
        reduction = self.stats['games_found'] - total_filtered
        reduction_pct = (reduction / self.stats['games_found'] * 100) if self.stats['games_found'] > 0 else 0
        
        logger.info(f"1G1R filtering: {self.stats['games_found']} -> {total_filtered} games "
                   f"({reduction} removed, {reduction_pct:.1f}%)")
        
        return filtered_results
    
    def fetch_igdb_metadata(self, game: GameEntry, platform_name: str) -> Optional[IGDBGame]:
        """
        Fetch metadata from IGDB API for a game
        
        Args:
            game: GameEntry object
            platform_name: Platform name for filtering
            
        Returns:
            IGDBGame object or None if not found
        """
        if not self.igdb_client:
            logger.debug("IGDB client not available, skipping metadata fetch")
            return None
        
        try:
            # Clean title for better search
            clean_title = game.clean_title
            
            # Search IGDB
            igdb_games = self.igdb_client.fuzzy_search_game(
                title=clean_title,
                platform_name=platform_name,
                max_results=3
            )
            
            if not igdb_games:
                logger.debug(f"No IGDB matches found for: {clean_title}")
                self.stats['igdb_failures'] += 1
                return None
            
            # Use the best match (first result)
            igdb_game = igdb_games[0]
            
            logger.debug(f"Found IGDB match: {clean_title} -> {igdb_game.name}")
            self.stats['igdb_matches'] += 1
            
            return igdb_game
            
        except Exception as e:
            logger.error(f"Error fetching IGDB metadata for {game.clean_title}: {e}")
            self.stats['igdb_failures'] += 1
            return None
    
    def save_to_database(self, dat_results: Dict[str, List[GameEntry]], 
                        fetch_metadata: bool = True) -> int:
        """
        Save games to metadata database
        
        Args:
            dat_results: Dictionary mapping platform names to list of GameEntry objects
            fetch_metadata: Whether to fetch IGDB metadata
            
        Returns:
            Number of games saved to database
        """
        logger.info("Saving games to database...")
        
        saved_count = 0
        
        with self.app.app_context():
            # Initialize database if needed
            MetadataDatabaseManager.initialize_database()
            
            for platform_name, games in dat_results.items():
                logger.info(f"Processing {len(games)} games for {platform_name}")
                
                for game in games:
                    try:
                        # Check if game already exists
                        existing_game = MetadataGame.query.filter_by(
                            clean_title=game.clean_title,
                            source='dat_file'
                        ).first()
                        
                        if existing_game:
                            # Update existing game
                            self._update_existing_game(existing_game, game, platform_name)
                        else:
                            # Create new game
                            saved = self._create_new_game(game, platform_name, fetch_metadata)
                            if saved:
                                saved_count += 1
                        
                        # Commit periodically
                        if saved_count % 100 == 0:
                            db.session.commit()
                            logger.info(f"Committed {saved_count} games...")
                    
                    except Exception as e:
                        logger.error(f"Error saving game {game.clean_title}: {e}")
                        db.session.rollback()
                        continue
            
            # Final commit
            db.session.commit()
        
        self.stats['database_entries'] = saved_count
        logger.info(f"Saved {saved_count} games to database")
        return saved_count
    
    def _create_new_game(self, game: GameEntry, platform_name: str, 
                        fetch_metadata: bool) -> bool:
        """Create new game in database"""
        # Create base game record
        metadata_game = MetadataGame(
            title=game.name,
            clean_title=game.clean_title,
            source='dat_file',
            source_id=f"dat_{platform_name}_{game.clean_title}",
            last_updated=datetime.utcnow()
        )
        
        # Fetch IGDB metadata if requested
        igdb_game = None
        if fetch_metadata and self.igdb_client:
            igdb_game = self.fetch_igdb_metadata(game, platform_name)
        
        if igdb_game:
            # Update with IGDB metadata
            self._update_game_with_igdb(metadata_game, igdb_game)
        
        # Add platform
        platform = self._get_or_create_platform(platform_name)
        if platform:
            metadata_game.platforms.append(platform)
        
        # Add ROM information
        for rom in game.roms:
            metadata_rom = MetadataROM(
                filename=rom.name,
                size=rom.size,
                crc=rom.crc,
                md5=rom.md5,
                sha1=rom.sha1,
                region=game.extracted_region or game.region,
                source='no-intro',  # Assuming No-Intro DAT
                source_id=f"rom_{rom.crc}" if rom.crc else f"rom_{rom.name}",
                game=metadata_game
            )
            db.session.add(metadata_rom)
        
        db.session.add(metadata_game)
        return True
    
    def _update_existing_game(self, existing_game: MetadataGame, 
                             game: GameEntry, platform_name: str):
        """Update existing game with new information"""
        # Check if we need to update metadata
        needs_update = False
        
        # Add ROM if not already present
        for rom in game.roms:
            if rom.crc:
                existing_rom = MetadataROM.query.filter_by(
                    game_id=existing_game.id,
                    crc=rom.crc
                ).first()
                
                if not existing_rom:
                    # Add new ROM
                    metadata_rom = MetadataROM(
                        filename=rom.name,
                        size=rom.size,
                        crc=rom.crc,
                        md5=rom.md5,
                        sha1=rom.sha1,
                        region=game.extracted_region or game.region,
                        source='no-intro',
                        source_id=f"rom_{rom.crc}",
                        game=existing_game
                    )
                    db.session.add(metadata_rom)
                    needs_update = True
        
        # Update timestamp if changed
        if needs_update:
            existing_game.last_updated = datetime.utcnow()
    
    def _update_game_with_igdb(self, metadata_game: MetadataGame, igdb_game: IGDBGame):
        """Update game with IGDB metadata"""
        metadata_game.igdb_id = igdb_game.id
        metadata_game.slug = igdb_game.slug
        metadata_game.summary = igdb_game.summary
        metadata_game.storyline = igdb_game.storyline
        metadata_game.rating = igdb_game.rating
        metadata_game.rating_count = igdb_game.rating_count
        metadata_game.total_rating = igdb_game.total_rating
        metadata_game.total_rating_count = igdb_game.total_rating_count
        
        if igdb_game.first_release_date:
            metadata_game.first_release_date = datetime.fromtimestamp(igdb_game.first_release_date)
            metadata_game.release_year = metadata_game.first_release_date.year
        
        metadata_game.cover_url = igdb_game.cover_url
        
        # Store screenshot URLs as JSON
        if igdb_game.screenshot_urls:
            metadata_game.screenshot_urls = json.dumps(igdb_game.screenshot_urls)
        
        # Update source
        metadata_game.source = 'igdb'
    
    def _get_or_create_platform(self, platform_name: str) -> Optional[MetadataPlatform]:
        """Get or create platform record"""
        # Try to find existing platform
        platform = MetadataPlatform.query.filter_by(name=platform_name).first()
        
        if not platform:
            # Create new platform
            platform = MetadataPlatform(
                name=platform_name,
                slug=platform_name.lower().replace(' ', '-'),
                source='dat_file',
                source_id=f"platform_{platform_name}",
                last_updated=datetime.utcnow()
            )
            
            # Try to get IGDB platform ID
            if self.igdb_client:
                igdb_platform_id = self.igdb_client.map_platform_name(platform_name)
                if igdb_platform_id:
                    platform.igdb_id = igdb_platform_id
            
            db.session.add(platform)
        
        return platform
    
    def export_to_csv(self, output_path: str, include_metadata: bool = True):
        """
        Export database to CSV
        
        Args:
            output_path: Path to output CSV file
            include_metadata: Whether to include IGDB metadata
        """
        logger.info(f"Exporting to CSV: {output_path}")
        
        with self.app.app_context():
            games = MetadataGame.query.all()
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                if include_metadata:
                    fieldnames = [
                        'title', 'clean_title', 'platforms', 'release_year',
                        'rating', 'genres', 'developers', 'publishers',
                        'summary', 'cover_url', 'source'
                    ]
                else:
                    fieldnames = [
                        'title', 'clean_title', 'platforms', 'region',
                        'rom_filename', 'rom_size', 'rom_crc', 'source'
                    ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for game in games:
                    if include_metadata:
                        writer.writerow({
                            'title': game.title,
                            'clean_title': game.clean_title,
                            'platforms': ', '.join([p.name for p in game.platforms]),
                            'release_year': game.release_year,
                            'rating': game.rating,
                            'genres': ', '.join([g.name for g in game.genres]),
                            'developers': ', '.join([d.name for d in game.developers]),
                            'publishers': ', '.join([p.name for p in game.publishers]),
                            'summary': (game.summary or '')[:200] if game.summary else '',
                            'cover_url': game.cover_url or '',
                            'source': game.source
                        })
                    else:
                        # Basic export without metadata
                        for rom in game.roms:
                            writer.writerow({
                                'title': game.title,
                                'clean_title': game.clean_title,
                                'platforms': ', '.join([p.name for p in game.platforms]),
                                'region': rom.region or '',
                                'rom_filename': rom.filename,
                                'rom_size': rom.size,
                                'rom_crc': rom.crc or '',
                                'source': game.source
                            })
        
        logger.info(f"Exported {len(games)} games to {output_path}")
    
    def get_statistics(self) -> Dict:
        """Get scraping statistics"""
        self.stats['end_time'] = datetime.utcnow()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        self.stats['duration_seconds'] = duration
        
        # Add database statistics
        with self.app.app_context():
            db_stats = MetadataDatabaseManager.get_statistics()
            self.stats.update(db_stats)
        
        return self.stats
    
    def print_statistics(self):
        """Print statistics to console"""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("RETRO METADATA SCRAPER STATISTICS")
        print("="*60)
        
        print(f"\nDAT Files Processing:")
        print(f"  DAT files parsed: {stats['dat_files_parsed']}")
        print(f"  Games found: {stats['games_found']}")
        print(f"  Games after 1G1R: {stats['games_after_1g1r']}")
        
        if stats['games_found'] > 0:
            reduction = stats['games_found'] - stats['games_after_1g1r']
            reduction_pct = (reduction / stats['games_found'] * 100)
            print(f"  1G1R reduction: {reduction} games ({reduction_pct:.1f}%)")
        
        print(f"\nIGDB API Integration:")
        print(f"  Successful matches: {stats.get('igdb_matches', 0)}")
        print(f"  Failed matches: {stats.get('igdb_failures', 0)}")
        
        if stats.get('igdb_matches', 0) > 0:
            success_rate = stats['igdb_matches'] / (stats['igdb_matches'] + stats['igdb_failures']) * 100
            print(f"  Success rate: {success_rate:.1f}%")
        
        print(f"\nDatabase:")
        print(f"  Games in database: {stats.get('games', 0)}")
        print(f"  Platforms: {stats.get('platforms', 0)}")
        print(f"  Genres: {stats.get('genres', 0)}")
        print(f"  ROMs: {stats.get('roms', 0)}")
        
        print(f"\nPerformance:")
        print(f"  Duration: {stats.get('duration_seconds', 0):.1f} seconds")
        
        if stats.get('games', 0) > 0 and stats.get('duration_seconds', 0) > 0:
            games_per_second = stats['games'] / stats['duration_seconds']
            print(f"  Processing rate: {games_per_second:.2f} games/second")
        
        print("="*60)


def main():
    """Command-line interface for retro metadata scraper"""
    parser = argparse.ArgumentParser(
        description='Retro Gaming Metadata Scraper - Collect game metadata from DAT files and IGDB API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s parse --dat-path ./libretro-database/dat --output ./games.csv
  %(prog)s full --dat-path ./dat_files --database ./metadata.db --fetch-metadata
  %(prog)s export --database ./metadata.db --output ./export.csv --format csv
  
Environment Variables:
  IGDB_CLIENT_ID: Twitch Developer Application Client ID
  IGDB_CLIENT_SECRET: Twitch Developer Application Client Secret
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Parse command
    parse_parser = subparsers.add_parser('parse', help='Parse DAT files only')
    parse_parser.add_argument('--dat-path', required=True, help='Path to DAT file or directory')
    parse_parser.add_argument('--recursive', action='store_true', help='Search directories recursively')
    parse_parser.add_argument('--output', help='Output CSV file path')
    parse_parser.add_argument('--no-1g1r', action='store_true', help='Skip 1G1R filtering')
    
    # Full pipeline command
    full_parser = subparsers.add_parser('full', help='Run full pipeline (parse, filter, fetch metadata, save to DB)')
    full_parser.add_argument('--dat-path', required=True, help='Path to DAT file or directory')
    full_parser.add_argument('--database', default='metadata.db', help='SQLite database path')
    full_parser.add_argument('--recursive', action='store_true', help='Search directories recursively')
    full_parser.add_argument('--no-1g1r', action='store_true', help='Skip 1G1R filtering')
    full_parser.add_argument('--no-metadata', action='store_true', help='Skip IGDB metadata fetching')
    full_parser.add_argument('--export', help='Export to CSV after processing')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export database to CSV')
    export_parser.add_argument('--database', default='metadata.db', help='SQLite database path')
    export_parser.add_argument('--output', required=True, help='Output CSV file path')
    export_parser.add_argument('--format', choices=['csv', 'json'], default='csv', help='Output format')
    export_parser.add_argument('--include-metadata', action='store_true', help='Include IGDB metadata')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show database statistics')
    stats_parser.add_argument('--database', default='metadata.db', help='SQLite database path')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test IGDB API connection')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Set database path if specified
    if hasattr(args, 'database') and args.database:
        os.environ['DATABASE_URL'] = f'sqlite:///{args.database}'
    
    # Create scraper instance
    scraper = RetroMetadataScraper()
    
    try:
        if args.command == 'parse':
            # Parse DAT files only
            dat_results = scraper.parse_dat_files(args.dat_path, args.recursive)
            
            if not args.no_1g1r:
                dat_results = scraper.apply_1g1r_filtering(dat_results)
            
            # Export to CSV if requested
            if args.output:
                # Simple export without database
                total_games = sum(len(games) for games in dat_results.values())
                print(f"Parsed {total_games} games")
                
                # Create simple CSV export
                with open(args.output, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['platform', 'title', 'clean_title', 'region', 'rom_count']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for platform, games in dat_results.items():
                        for game in games:
                            writer.writerow({
                                'platform': platform,
                                'title': game.name,
                                'clean_title': game.clean_title,
                                'region': game.extracted_region or '',
                                'rom_count': len(game.roms)
                            })
                
                print(f"Exported to {args.output}")
            
            scraper.print_statistics()
        
        elif args.command == 'full':
            # Run full pipeline
            print("Starting full metadata scraping pipeline...")
            
            # 1. Parse DAT files
            dat_results = scraper.parse_dat_files(args.dat_path, args.recursive)
            
            # 2. Apply 1G1R filtering
            if not args.no_1g1r:
                dat_results = scraper.apply_1g1r_filtering(dat_results)
            
            # 3. Save to database (with optional metadata fetching)
            fetch_metadata = not args.no_metadata
            saved_count = scraper.save_to_database(dat_results, fetch_metadata)
            
            # 4. Export if requested
            if args.export:
                scraper.export_to_csv(args.export, include_metadata=fetch_metadata)
            
            print(f"\nPipeline completed. Saved {saved_count} games to database.")
            scraper.print_statistics()
        
        elif args.command == 'export':
            # Export database
            scraper.export_to_csv(args.output, include_metadata=args.include_metadata)
            print(f"Exported database to {args.output}")
        
        elif args.command == 'stats':
            # Show statistics
            stats = scraper.get_statistics()
            scraper.print_statistics()
        
        elif args.command == 'test':
            # Test IGDB connection
            if scraper.igdb_client:
                result = scraper.igdb_client.test_connection()
                if result['success']:
                    print(f"IGDB API connection successful!")
                    print(f"Sample game: {result.get('sample_game', 'N/A')}")
                else:
                    print(f"IGDB API connection failed: {result['message']}")
            else:
                print("IGDB client not configured. Set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET environment variables.")
        
        print("\nDone!")
        
    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()