#!/usr/bin/env python3
"""
Database Manager for Romarr
===========================
This script manages the ROM database for the Romarr system.
It can:
1. Generate a comprehensive database from all sources
2. Export the database to a compressed file
3. Import a database file into the container's storage
"""

import os
import sys
import sqlite3
import argparse
import tempfile
import shutil
import gzip
import json
from pathlib import Path
from datetime import datetime

# Add the parent directory to the path so we can import the scraper
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def generate_database(output_path: str, sources: list = None, platforms: list = None):
    """
    Generate a comprehensive database by running the scraper.
    
    Args:
        output_path: Path to save the database file
        sources: List of sources to scrape (None = all)
        platforms: List of platforms to scrape (None = all)
    """
    print(f"Generating database at {output_path}")
    
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Import and run the scraper
    try:
        from scripts.scrape_comprehensive_database import main as scraper_main
        from scripts.scrape_comprehensive_database import ComprehensiveDatabaseScraper
        
        # Create scraper instance
        scraper = ComprehensiveDatabaseScraper(database_path=output_path)
        
        # Build command-line arguments
        import sys as sys_module
        original_argv = sys_module.argv
        
        # Set up command-line arguments for the scraper
        args = []
        if sources:
            args.extend(['--sources'] + sources)
        if platforms:
            args.extend(['--platforms'] + platforms)
        
        # Run the scraper
        print("Starting comprehensive database scrape...")
        scraper.run()
        
        # Verify the database was created
        if os.path.exists(output_path):
            # Get statistics
            conn = sqlite3.connect(output_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM rom_files")
            rom_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM platforms")
            platform_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT verification_source, COUNT(*) FROM rom_files GROUP BY verification_source")
            source_stats = cursor.fetchall()
            
            conn.close()
            
            print(f"\nDatabase generation complete!")
            print(f"  Total ROMs: {rom_count:,}")
            print(f"  Total platforms: {platform_count}")
            print(f"  File size: {os.path.getsize(output_path) / (1024*1024*1024):.2f} GB")
            print(f"  Source breakdown:")
            for source, count in source_stats:
                print(f"    - {source}: {count:,} ROMs")
            
            return True
        else:
            print(f"Error: Database file not created at {output_path}")
            return False
            
    except ImportError as e:
        print(f"Error importing scraper: {e}")
        print("Make sure you're running from the project root directory")
        return False
    except Exception as e:
        print(f"Error during database generation: {e}")
        import traceback
        traceback.print_exc()
        return False

def export_database(database_path: str, output_file: str, compress: bool = True):
    """
    Export a database to a .rommar file (compressed SQLite format).
    
    Args:
        database_path: Path to the SQLite database
        output_file: Path to save the exported file
        compress: Whether to compress with gzip (always True for .rommar)
    """
    if not os.path.exists(database_path):
        print(f"Error: Database file not found at {database_path}")
        return False
    
    print(f"Exporting database from {database_path}")
    
    try:
        # Ensure .rommar extension
        if not output_file.endswith('.rommar'):
            output_file = output_file.rsplit('.', 1)[0] + '.rommar'
        
        # Always compress for .rommar files
        print(f"Creating Romarr database archive: {output_file}")
        
        # Create a metadata file with database info
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM rom_files")
        rom_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM platforms")
        platform_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT verification_source, COUNT(*) FROM rom_files GROUP BY verification_source")
        source_stats = cursor.fetchall()
        
        conn.close()
        
        # Create metadata
        metadata = {
            "format": "romarr-database-v1",
            "created": datetime.now().isoformat(),
            "rom_count": rom_count,
            "platform_count": platform_count,
            "sources": {source: count for source, count in source_stats},
            "compression": "gzip",
            "schema_version": "1.0"
        }
        
        # Create a temporary directory for packaging
        with tempfile.TemporaryDirectory() as tmpdir:
            # Copy database
            db_copy = os.path.join(tmpdir, "database.db")
            shutil.copy2(database_path, db_copy)
            
            # Write metadata
            metadata_file = os.path.join(tmpdir, "metadata.json")
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Create archive
            print(f"Packaging database with {rom_count:,} ROMs and {platform_count} platforms...")
            
            # Create tar.gz archive
            import tarfile
            with tarfile.open(output_file, 'w:gz') as tar:
                tar.add(db_copy, arcname="database.db")
                tar.add(metadata_file, arcname="metadata.json")
            
            original_size = os.path.getsize(database_path)
            archive_size = os.path.getsize(output_file)
            compression_ratio = (1 - archive_size / original_size) * 100
            
            print(f"Export complete!")
            print(f"  Original size: {original_size / (1024*1024*1024):.2f} GB")
            print(f"  Archive size: {archive_size / (1024*1024*1024):.2f} GB")
            print(f"  Compression: {compression_ratio:.1f}%")
            print(f"  Format: Romarr Database Archive (.rommar)")
            print(f"  Contents: database.db + metadata.json")
        
        return True
        
    except Exception as e:
        print(f"Error during export: {e}")
        import traceback
        traceback.print_exc()
        return False

def import_database(database_file: str, target_path: str, progress_callback=None):
    """
    Import a database file (.rommar archive or .db/.db.gz) to the target path.
    
    Args:
        database_file: Path to the database file (.rommar, .db, or .db.gz)
        target_path: Path where the database should be placed
        progress_callback: Optional function(percentage, message)
    """
    def report(percent, msg):
        if progress_callback:
            progress_callback(percent, msg)
        print(f"[{percent}%] {msg}")

    if not os.path.exists(database_file):
        print(f"Error: Database file not found at {database_file}")
        return False
    
    report(0, f"Starting import of {os.path.basename(database_file)}")
    
    try:
        # Ensure target directory exists
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        
        # Use a temporary file for the import to avoid locking the main DB
        temp_target = target_path + '.tmp'
        if os.path.exists(temp_target):
            os.remove(temp_target)
            
        if database_file.endswith('.rommar'):
            report(10, "Opening Romarr database archive...")
            
            import tarfile
            with tarfile.open(database_file, 'r:gz') as tar:
                members = tar.getmembers()
                db_member = next((m for m in members if m.name == 'database.db'), None)
                
                if not db_member:
                    report(0, "Error: No database.db found in archive")
                    return False
                
                report(30, "Extracting database from archive...")
                tar.extract(db_member, path=os.path.dirname(target_path))
                
                # Move extracted to our temp target
                extracted_path = os.path.join(os.path.dirname(target_path), 'database.db')
                if os.path.exists(extracted_path):
                    if os.path.exists(temp_target): os.remove(temp_target)
                    shutil.move(extracted_path, temp_target)
        
        elif database_file.endswith('.gz'):
            report(10, "Decompressing gzipped database...")
            file_size = os.path.getsize(database_file)
            bytes_read = 0
            
            with gzip.open(database_file, 'rb') as f_in:
                with open(temp_target, 'wb') as f_out:
                    while True:
                        chunk = f_in.read(1024 * 1024) # 1MB chunks
                        if not chunk:
                            break
                        f_out.write(chunk)
                        bytes_read += len(chunk)
                        percent = min(95, int((bytes_read / (file_size * 2)) * 100)) 
                        report(percent, f"Decompressing... {bytes_read / (1024*1024):.1f} MB")
        
        else:
            report(20, "Copying database...")
            shutil.copy2(database_file, temp_target)
        
        # Verify the new database BEFORE swapping
        report(95, "Verifying imported database...")
        if os.path.exists(temp_target):
            try:
                conn = sqlite3.connect(temp_target)
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM rom_files")
                    rom_count = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM platforms")
                    platform_count = cursor.fetchone()[0]
                finally:
                    conn.close()
                
                # Atomic swap
                report(98, "Performing atomic swap...")
                os.replace(temp_target, target_path)
                
                report(100, f"Import complete! ({rom_count:,} ROMs, {platform_count} platforms)")
                return True
            except sqlite3.Error as e:
                report(0, f"Error: New database is invalid: {e}")
                if os.path.exists(temp_target): os.remove(temp_target)
                return False
        else:
            report(0, "Error: Temporary database file not found")
            return False
            
    except Exception as e:
        print(f"Error during import: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_database_info(database_path: str):
    """
    Get information about a database file.
    
    Args:
        database_path: Path to the SQLite database
    """
    if not os.path.exists(database_path):
        return None
    
    try:
        conn = sqlite3.connect(database_path)
        try:
            cursor = conn.cursor()
            
            # Get basic info
            cursor.execute("SELECT COUNT(*) FROM rom_files")
            rom_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM platforms")
            platform_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT verification_source, COUNT(*) FROM rom_files GROUP BY verification_source ORDER BY COUNT(*) DESC")
            source_stats = cursor.fetchall()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            file_size = os.path.getsize(database_path)
            
            return {
                "path": database_path,
                "filename": os.path.basename(database_path),
                "size_bytes": file_size,
                "size_gb": round(file_size / (1024*1024*1024), 2),
                "table_count": len(tables),
                "rom_count": rom_count,
                "platform_count": platform_count,
                "sources": {source: count for source, count in source_stats}
            }
        finally:
            conn.close()
        
    except sqlite3.Error as e:
        print(f"Error: Not a valid SQLite database: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Romarr Database Manager')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate a new database')
    generate_parser.add_argument('--output', '-o', default='instance/romarr.db',
                                help='Output database path (default: instance/romarr.db)')
    generate_parser.add_argument('--sources', nargs='+',
                                help='Sources to scrape (no-intro, mame, libretro)')
    generate_parser.add_argument('--platforms', nargs='+',
                                help='Platforms to scrape')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export database to file')
    export_parser.add_argument('--input', '-i', default='instance/romarr.db',
                              help='Input database path (default: instance/romarr.db)')
    export_parser.add_argument('--output', '-o', required=True,
                              help='Output file path')
    export_parser.add_argument('--no-compress', action='store_true',
                              help='Do not compress the output')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import database from file')
    import_parser.add_argument('--input', '-i', required=True,
                              help='Input database file path (.db or .db.gz)')
    import_parser.add_argument('--output', '-o', default='instance/romarr.db',
                              help='Output database path (default: instance/romarr.db)')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Get database information')
    info_parser.add_argument('--database', '-d', default='instance/romarr.db',
                            help='Database path (default: instance/romarr.db)')
    
    args = parser.parse_args()
    
    if args.command == 'generate':
        success = generate_database(args.output, args.sources, args.platforms)
        sys.exit(0 if success else 1)
    
    elif args.command == 'export':
        success = export_database(args.input, args.output, not args.no_compress)
        sys.exit(0 if success else 1)
    
    elif args.command == 'import':
        success = import_database(args.input, args.output)
        sys.exit(0 if success else 1)
    
    elif args.command == 'info':
        success = get_database_info(args.database)
        sys.exit(0 if success else 1)
    
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()