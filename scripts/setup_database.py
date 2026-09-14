#!/usr/bin/env python3
"""
Database Setup Script
Clears existing database and sets up new unified schema
"""

import os
import sys
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.unified_schema import initialize_default_data


def backup_existing_database():
    """Backup existing database file if it exists"""
    db_path = Path("instance/romarr.db")
    if db_path.exists():
        backup_path = Path(f"instance/romarr.db.backup.{os.path.getmtime(db_path)}")
        try:
            shutil.copy2(db_path, backup_path)
            print(f"Backed up existing database to {backup_path}")
            return True
        except Exception as e:
            print(f"Warning: Could not backup database: {e}")
            return False
    return True


def clear_database():
    """Clear all database tables"""
    print("Dropping all existing tables...")
    try:
        # Drop all tables
        db.drop_all()
        print("All tables dropped successfully")
        return True
    except Exception as e:
        print(f"Error dropping tables: {e}")
        return False


def create_new_schema():
    """Create new unified schema"""
    print("Creating new unified schema...")
    try:
        # Create all tables
        db.create_all()
        print("New schema created successfully")
        return True
    except Exception as e:
        print(f"Error creating schema: {e}")
        return False


def initialize_data():
    """Initialize default data"""
    print("Initializing default data...")
    try:
        initialize_default_data()
        print("Default data initialized successfully")
        return True
    except Exception as e:
        print(f"Error initializing data: {e}")
        return False


def verify_schema():
    """Verify the schema was created correctly"""
    print("Verifying schema...")
    try:
        # Check if tables exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            'games', 'rom_files', 'platforms', 'genres', 
            'companies', 'releases', 'image_cache', 'scraping_logs',
            'game_genre_association', 'game_platform_association',
            'game_developer_association', 'game_publisher_association'
        ]
        
        missing_tables = [t for t in expected_tables if t not in tables]
        
        if missing_tables:
            print(f"Warning: Missing tables: {missing_tables}")
            return False
        
        print(f"Schema verified: {len(tables)} tables created")
        return True
    except Exception as e:
        print(f"Error verifying schema: {e}")
        return False


def main():
    """Main function"""
    print("=" * 60)
    print("DATABASE SETUP: Unified Schema Migration")
    print("=" * 60)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Step 1: Backup existing database
        print("\n1. Backing up existing database...")
        if not backup_existing_database():
            response = input("Continue without backup? (y/N): ")
            if response.lower() != 'y':
                print("Aborted by user")
                return False
        
        # Step 2: Clear existing database
        print("\n2. Clearing existing database...")
        if not clear_database():
            response = input("Continue despite errors? (y/N): ")
            if response.lower() != 'y':
                print("Aborted by user")
                return False
        
        # Step 3: Create new schema
        print("\n3. Creating new unified schema...")
        if not create_new_schema():
            print("Failed to create schema")
            return False
        
        # Step 4: Initialize default data
        print("\n4. Initializing default data...")
        if not initialize_data():
            print("Failed to initialize data")
            return False
        
        # Step 5: Verify schema
        print("\n5. Verifying schema...")
        if not verify_schema():
            print("Schema verification failed")
            return False
        
        print("\n" + "=" * 60)
        print("DATABASE SETUP COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Run ROM scanner: python services/rom_importer.py /path/to/roms")
        print("2. Start the application: python app.py")
        print("3. Access the web interface at http://localhost:5000")
        
        return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)