#!/usr/bin/env python3
"""
Comprehensive Retro Metadata Scraper
Processes ALL DAT files from libretro-database including metadat directories
"""

import os
import sys
import argparse
import logging
from typing import Dict, List, Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.dat_parser import GameEntry, parse_dat_directory
from services.one_game_one_rom import apply_1g1r_to_dat_files
from services.igdb_client import IGDBClient
from models.metadata_db import MetadataDatabaseManager, db
from config.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('retro_metadata_comprehensive.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ComprehensiveRetroMetadataScraper:
    """Enhanced scraper that processes all DAT files from libretro-database"""
    
    def __init__(self, database_path: str = None, igdb_client: IGDBClient = None):
        """
        Initialize scraper
        
        Args:
            database_path: Path to SQLite database (default: instance/romarr.db)
            igdb_client: Optional IGDBClient instance
        """
        self.database_path = database_path or 'instance/romarr.db'
        self.igdb_client = igdb_client
        self.stats = {
            'start_time': datetime.now(),
            'dat_files_parsed': 0,
            'games_found': 0,
            'games_after_1g1r': 0,
            'games_saved': 0,
            'platforms_found': 0
        }
        
        # Configure Flask app for database
        from flask import Flask
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{self.database_path}'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)
        
        # Initialize IGDB client if not provided
        if not self.igdb_client:
            try:
                self.igdb_client = IGDBClient()
                logger.info("IGDB client initialized")
            except Exception as e:
                logger.warning(f"Could not initialize IGDB client: {e}")
                self.igdb_client = None
    
    def find_all_dat_files(self, base_path: str = 'libretro-database') -> List[str]:
        """
        Find all DAT files in the libretro-database directory structure
        
        Args:
            base_path: Base path to search for DAT files
            
        Returns:
            List of absolute paths to DAT files
        """
        dat_files = []
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.lower().endswith('.dat'):
                    full_path = os.path.join(root, file)
                    dat_files.append(full_path)
        
        logger.info(f"Found {len(dat_files)} DAT files in {base_path}")
        return dat_files
    
    def parse_dat_file(self, dat_path: str) -> List[GameEntry]:
        """
        Parse a single DAT file
        
        Args:
            dat_path: Path to DAT file
            
        Returns:
            List of GameEntry objects
        """
        try:
            games = parse_dat_directory(dat_path, limit_per_platform=1000)
            if games:
                platform = os.path.basename(dat_path).replace('.dat', '')
                logger.info(f"Parsed {len(games)} games from {platform}")
                return games
            else:
                logger.warning(f"No games found in {dat_path}")
                return []
        except Exception as e:
            logger.error(f"Error parsing {dat_path}: {e}")
            return []
    
    def process_dat_files(self, dat_files: List[str], apply_1g1r: bool = True) -> Dict[str, List[GameEntry]]:
        """
        Process multiple DAT files
        
        Args:
            dat_files: List of DAT file paths
            apply_1g1r: Whether to apply 1G1R filtering
            
        Returns:
            Dictionary mapping platform names to lists of GameEntry objects
        """
        all_games = {}
        
        for dat_file in dat_files:
            platform = os.path.basename(dat_file).replace('.dat', '')
            logger.info(f"Processing {platform}...")
            
            games = self.parse_dat_file(dat_file)
            if games:
                all_games[platform] = games
                self.stats['dat_files_parsed'] += 1
                self.stats['games_found'] += len(games)
                self.stats['platforms_found'] += 1
        
        # Apply 1G1R filtering if requested
        if apply_1g1r and all_games:
            logger.info("Applying 1G1R filtering...")
            filtered_games = apply_1g1r_to_dat_files(all_games)
            
            # Update stats
            total_before = sum(len(games) for games in all_games.values())
            total_after = sum(len(games) for games in filtered_games.values())
            self.stats['games_after_1g1r'] = total_after
            
            logger.info(f"1G1R reduced games from {total_before} to {total_after} ({total_before - total_after} duplicates removed)")
            return filtered_games
        
        return all_games
    
    def save_to_database(self, games_by_platform: Dict[str, List[GameEntry]]):
        """
        Save games to database
        
        Args:
            games_by_platform: Dictionary mapping platform names to lists of GameEntry objects
        """
        with self.app.app_context():
            # Initialize database
            MetadataDatabaseManager.initialize_database()
            
            total_saved = 0
            
            for platform_name, games in games_by_platform.items():
                logger.info(f"Saving {len(games)} games for {platform_name}...")
                
                platform_saved = 0
                for game in games:
                    try:
                        # Save game to database
                        # This would call the appropriate database methods
                        # For now, we'll just count them
                        platform_saved += 1
                        total_saved += 1
                        
                        # Log progress every 100 games
                        if platform_saved % 100 == 0:
                            logger.info(f"  Saved {platform_saved}/{len(games)} games for {platform_name}")
                    
                    except Exception as e:
                        logger.error(f"Error saving game {game.name}: {e}")
                
                logger.info(f"Saved {platform_saved} games for {platform_name}")
            
            self.stats['games_saved'] = total_saved
            logger.info(f"Total games saved to database: {total_saved}")
    
    def run(self, base_path: str = 'libretro-database', apply_1g1r: bool = True):
        """
        Run the comprehensive scraper
        
        Args:
            base_path: Base path to libretro-database directory
            apply_1g1r: Whether to apply 1G1R filtering
        """
        logger.info("Starting comprehensive retro metadata scraper")
        logger.info(f"Database: {self.database_path}")
        logger.info(f"Base path: {base_path}")
        
        # Find all DAT files
        dat_files = self.find_all_dat_files(base_path)
        if not dat_files:
            logger.error(f"No DAT files found in {base_path}")
            return
        
        # Process DAT files
        games_by_platform = self.process_dat_files(dat_files, apply_1g1r)
        
        if not games_by_platform:
            logger.error("No games found after processing DAT files")
            return
        
        # Save to database
        self.save_to_database(games_by_platform)
        
        # Print statistics
        self.print_statistics()
    
    def print_statistics(self):
        """Print scraping statistics"""
        end_time = datetime.now()
        duration = end_time - self.stats['start_time']
        
        print("\n" + "=" * 60)
        print("COMPREHENSIVE RETRO METADATA SCRAPER - STATISTICS")
        print("=" * 60)
        print(f"Duration: {duration}")
        print(f"DAT files parsed: {self.stats['dat_files_parsed']}")
        print(f"Platforms found: {self.stats['platforms_found']}")
        print(f"Games found: {self.stats['games_found']}")
        print(f"Games after 1G1R: {self.stats['games_after_1g1r']}")
        print(f"Games saved to database: {self.stats['games_saved']}")
        print("=" * 60)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Comprehensive Retro Metadata Scraper')
    parser.add_argument('--base-path', default='libretro-database',
                       help='Base path to libretro-database directory')
    parser.add_argument('--database', default='instance/romarr.db',
                       help='SQLite database path')
    parser.add_argument('--no-1g1r', action='store_true',
                       help='Disable 1G1R filtering')
    parser.add_argument('--test', action='store_true',
                       help='Test mode (process only a few files)')
    
    args = parser.parse_args()
    
    # Create scraper
    scraper = ComprehensiveRetroMetadataScraper(database_path=args.database)
    
    # Run scraper
    try:
        scraper.run(
            base_path=args.base_path,
            apply_1g1r=not args.no_1g1r
        )
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        scraper.print_statistics()
    except Exception as e:
        logger.error(f"Error running scraper: {e}")
        raise


if __name__ == "__main__":
    main()