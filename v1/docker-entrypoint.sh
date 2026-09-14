#!/bin/bash
set -e

echo "========================================="
echo "Romarr - ROM Database Management System"
echo "========================================="
echo "Version: 1.0.0 | Database Format: .rommar"
echo "Sources: No-Intro, MAME, libretro-database"
echo "========================================="

# Wait for database to be ready (if using external database)
if [ -n "$DATABASE_HOST" ] && [ -n "$DATABASE_PORT" ]; then
    echo "Waiting for database at $DATABASE_HOST:$DATABASE_PORT..."
    while ! nc -z $DATABASE_HOST $DATABASE_PORT; do
        sleep 1
    done
    echo "Database is ready!"
fi

# Check if database exists
if [ -f "/app/instance/romarr.db" ]; then
    echo "Found existing database at /app/instance/romarr.db"
    echo "Database size: $(du -h /app/instance/romarr.db | cut -f1)"
    
    # Verify database is accessible
    if sqlite3 /app/instance/romarr.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" >/dev/null 2>&1; then
        TABLE_COUNT=$(sqlite3 /app/instance/romarr.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
        
        # Try to get ROM count if tables exist
        if sqlite3 /app/instance/romarr.db "SELECT name FROM sqlite_master WHERE type='table' AND name='roms';" >/dev/null 2>&1; then
            ROM_COUNT=$(sqlite3 /app/instance/romarr.db "SELECT COUNT(*) FROM roms;" 2>/dev/null || echo "0")
            PLATFORM_COUNT=$(sqlite3 /app/instance/romarr.db "SELECT COUNT(*) FROM platforms;" 2>/dev/null || echo "0")
            echo "Database contains:"
            echo "  - $TABLE_COUNT tables"
            echo "  - $PLATFORM_COUNT platforms"
            echo "  - $ROM_COUNT ROM entries"
        else
            echo "Database contains $TABLE_COUNT tables (no ROM data yet)"
            echo "Use the database manager to import ROM data:"
            echo "  python scripts/database_manager.py import --input /path/to/romarr.db.gz --output /app/instance/romarr.db"
        fi
    else
        echo "Warning: Database verification failed, creating new database..."
        # Initialize empty database
        python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Basic database schema created')
"
    fi
else
    echo "No database found at /app/instance/romarr.db"
    echo "Creating empty database with basic schema..."
    
    # Create directory if it doesn't exist
    mkdir -p /app/instance
    
    # Initialize empty database
    python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Basic database schema created')
"
    
    echo "Empty database created."
    echo "To populate with ROM data, use one of these options:"
    echo "1. Run the scraper inside the container:"
    echo "   docker exec -it <container_name> python scripts/scrape_comprehensive_database.py"
    echo "2. Import a pre-generated database:"
    echo "   python scripts/database_manager.py import --input /path/to/romarr.db.gz --output /app/instance/romarr.db"
fi

# Run database migrations if Alembic is configured
if [ -f "/app/migrations/alembic.ini" ]; then
    echo "Running database migrations..."
    flask db upgrade
fi

# Initialize default data (settings, etc.)
echo "Initializing default data..."
python -c "
import traceback
try:
    from app import create_app
    from models.unified_schema import initialize_default_data
    app = create_app()
    with app.app_context():
        try:
            initialize_default_data()
            print('Default data initialized')
        except Exception as e:
            print(f'Note: Default data initialization issue (may be already initialized): {e}')
except ImportError as e:
    print(f'Import error during initialization (some modules may not be available): {e}')
except Exception as e:
    print(f'Unexpected error during initialization: {e}')
    traceback.print_exc()
"

# Set up ROMs directory if it doesn't exist
if [ ! -d "/data/roms" ]; then
    echo "Creating ROMs directory..."
    mkdir -p /data/roms
    chmod 755 /data/roms
fi

# Import ROMs from environment variable if set
if [ -n "$INITIAL_ROM_IMPORT_PATH" ] && [ -d "$INITIAL_ROM_IMPORT_PATH" ]; then
    echo "Importing ROMs from $INITIAL_ROM_IMPORT_PATH..."
    python services/rom_importer.py "$INITIAL_ROM_IMPORT_PATH" --recursive || {
        echo "ROM import failed, continuing without initial import"
    }
fi

echo "========================================="
echo "Starting ROM Management System..."
echo "========================================="

# Execute the command passed to docker run
exec "$@"