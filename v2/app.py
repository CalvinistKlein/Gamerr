"""
Gamerr: Video Game Collection & Management System
Main Flask application entry point
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config.config import Config

from extensions import db, migrate

def create_app(config_class=Config):
    """Application factory function"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    from routes.web import web_bp
    from routes.api import api_bp
    
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Create database tables and initialize default settings
    with app.app_context():
        try:
            # Try to create tables - they might already exist
            db.create_all()
            print("Database tables created")
        except Exception as e:
            # Tables likely already exist, which is fine
            print(f"Note: Database tables may already exist: {e}")
        
        # Import here to avoid circular imports
        from models.settings import Settings
        Settings.initialize_defaults()
        
        # Initialize libretro catalog if empty
        try:
            from models.unified_schema import GameCatalog
            from services.libretro_importer import LibretroImporter
            
            # Seed or update catalog from seed files
            stats = LibretroImporter.initialize_catalog()
            catalog_count = GameCatalog.query.count()
            print(f"Catalog has {catalog_count} games ({stats.get('imported_games', 0)} newly imported)")
        except Exception as e:
            print(f"Note: Could not initialize catalog: {e}")
        
        # Start automation service in production mode (not testing or debugging)
        import sys
        if not app.config.get('DEBUG', False) and not app.config.get('TESTING', False) and 'unittest' not in sys.modules:
            try:
                from services.automation import automation_service
                automation_service.start(app)
            except Exception as e:
                print(f"Failed to start automation service: {e}")
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)