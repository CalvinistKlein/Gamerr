"""
Romarr: Automated ROM Management System
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
            
            # Check if catalog is empty
            catalog_count = GameCatalog.query.count()
            if catalog_count == 0:
                print("Initializing libretro catalog...")
                stats = LibretroImporter.initialize_catalog()
                print(f"Catalog initialized: {stats.get('imported_games', 0)} games imported")
            else:
                print(f"Catalog already has {catalog_count} games")
        except Exception as e:
            print(f"Note: Could not initialize catalog: {e}")
        
        # Start automation service in production mode
        if not app.config.get('DEBUG', False):
            try:
                from services.automation import automation_service
                automation_service.start()
                print("Automation service started")
            except Exception as e:
                print(f"Failed to start automation service: {e}")
    
    return app

# Create app instance for running directly
app = create_app()

if __name__ == '__main__':
    # Start automation service when running directly
    with app.app_context():
        try:
            from services.automation import automation_service
            automation_service.start()
            print("Automation service started")
        except Exception as e:
            print(f"Failed to start automation service: {e}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)