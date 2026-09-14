#!/bin/bash
set -e

echo "========================================="
echo "Gamerr - Video Game Collection Manager"
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
    TABLES_VERIFIED=$(sqlite3 /app/instance/romarr.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null)
    if [ -n "$TABLES_VERIFIED" ]; then
        TABLE_COUNT=$(sqlite3 /app/instance/romarr.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
        
        # Try to get game and platform count if tables exist
        TABLE_EXISTS=$(sqlite3 /app/instance/romarr.db "SELECT name FROM sqlite_master WHERE type='table' AND name='games';" 2>/dev/null)
        if [ -n "$TABLE_EXISTS" ]; then
            GAME_COUNT=$(sqlite3 /app/instance/romarr.db "SELECT COUNT(*) FROM games;" 2>/dev/null || echo "0")
            PLATFORM_COUNT=$(sqlite3 /app/instance/romarr.db "SELECT COUNT(*) FROM platforms;" 2>/dev/null || echo "0")
            CATALOG_COUNT=$(sqlite3 /app/instance/romarr.db "SELECT COUNT(*) FROM game_catalog;" 2>/dev/null || echo "0")
            echo "Database contains:"
            echo "  - $TABLE_COUNT tables"
            echo "  - $PLATFORM_COUNT platforms"
            echo "  - $GAME_COUNT library games"
            echo "  - $CATALOG_COUNT catalog titles"
        else
            echo "Database contains $TABLE_COUNT tables (seeding will occur during app startup)"
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
    
    echo "Empty database created. Core platforms and seed catalog will be loaded on startup."
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