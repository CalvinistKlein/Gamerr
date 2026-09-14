#!/usr/bin/env python3
"""
Initialize metadata database tables
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from models.metadata_db import MetadataDatabaseManager, db

def main():
    """Initialize metadata database tables"""
    print("Initializing metadata database...")
    
    # Create Flask app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/romarr.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        # Initialize database tables
        MetadataDatabaseManager.initialize_database()
        print("Database tables created successfully")
        
        # Check what tables were created
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        print(f"\nTotal tables in database: {len(tables)}")
        print("Tables:")
        for table in sorted(tables):
            print(f"  - {table}")
        
        # Count records in metadata tables
        metadata_tables = [t for t in tables if t.startswith('metadata')]
        print(f"\nMetadata tables: {len(metadata_tables)}")
        
        for table in metadata_tables:
            try:
                result = db.session.execute(f"SELECT COUNT(*) FROM {table}")
                count = result.scalar()
                print(f"  - {table}: {count} records")
            except Exception as e:
                print(f"  - {table}: Error counting - {e}")

if __name__ == '__main__':
    main()