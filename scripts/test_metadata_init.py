#!/usr/bin/env python3
"""
Test metadata database initialization
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from models.metadata_db import db, MetadataGame, MetadataPlatform, MetadataROM

def main():
    """Test metadata database initialization"""
    print("Testing metadata database initialization...")
    
    # Create Flask app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/romarr.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize db with app
    db.init_app(app)
    
    with app.app_context():
        print("Creating metadata tables...")
        
        # Create all tables
        db.create_all()
        print("Tables created")
        
        # Check what tables exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        print(f"\nTotal tables in database: {len(tables)}")
        print("Tables:")
        for table in sorted(tables):
            print(f"  - {table}")
        
        # Check if metadata tables exist
        metadata_tables = [t for t in tables if t.startswith('metadata')]
        print(f"\nMetadata tables found: {len(metadata_tables)}")
        
        if metadata_tables:
            print("Metadata tables:")
            for table in metadata_tables:
                print(f"  - {table}")
        
        # Test inserting sample data
        print("\nTesting data insertion...")
        
        try:
            # Create a test platform
            platform = MetadataPlatform(
                name="Nintendo Entertainment System",
                short_name="NES",
                manufacturer="Nintendo",
                generation="3rd",
                release_year=1983
            )
            db.session.add(platform)
            db.session.flush()  # Get the ID
            
            # Create a test game
            game = MetadataGame(
                title="Super Mario Bros.",
                platform_id=platform.id,
                release_year=1985,
                publisher="Nintendo",
                developer="Nintendo R&D4",
                genre="Platformer",
                players=1
            )
            db.session.add(game)
            db.session.flush()
            
            # Create a test ROM
            rom = MetadataROM(
                game_id=game.id,
                filename="Super Mario Bros. (World).nes",
                size=40960,
                crc32="0x12345678",
                md5="d41d8cd98f00b204e9800998ecf8427e",
                sha1="da39a3ee5e6b4b0d3255bfef95601890afd80709",
                region="World"
            )
            db.session.add(rom)
            
            db.session.commit()
            print("Sample data inserted successfully")
            
            # Query the data back
            print("\nQuerying inserted data...")
            
            game_count = MetadataGame.query.count()
            platform_count = MetadataPlatform.query.count()
            rom_count = MetadataROM.query.count()
            
            print(f"Games: {game_count}")
            print(f"Platforms: {platform_count}")
            print(f"ROMs: {rom_count}")
            
            # Show the inserted game
            inserted_game = MetadataGame.query.first()
            if inserted_game:
                print(f"\nFirst game: {inserted_game.title} ({inserted_game.release_year})")
                
                # Get platform
                platform = MetadataPlatform.query.get(inserted_game.platform_id)
                if platform:
                    print(f"Platform: {platform.name} ({platform.short_name})")
                
                # Get ROMs
                roms = MetadataROM.query.filter_by(game_id=inserted_game.id).all()
                print(f"ROMs: {len(roms)}")
                for r in roms:
                    print(f"  - {r.filename} ({r.size} bytes)")
            
        except Exception as e:
            print(f"Error inserting test data: {e}")
            db.session.rollback()
        
        print("\nTest completed successfully!")

if __name__ == '__main__':
    main()