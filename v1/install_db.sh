#!/bin/bash
# install_db.sh - Automates the creation of the Gamerr database

echo "Starting Gamerr Database Installation..."

# Move to the script's directory (the gamerr root)
cd "$(dirname "$0")"

# 1. Setup python virtual environment if not present
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# 2. Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# 3. Clean slate database
echo "Wiping existing local database for a fresh start..."
rm -f instance/romarr.db instance/test.db

# Ensure instance directory exists
mkdir -p instance

# 4. Generate Schema
echo "Creating database schema using setup_database.py..."
# Inject 'y' answers in case setup_database.py asks for backup overwrite confirmations
yes y | python scripts/setup_database.py

# 5. Populate the database
echo "Populating the database with scraped data..."
# Use database_manager.py to generate (this uses scrape_comprehensive_database.py under the hood)
python scripts/database_manager.py generate

# 6. Export to .rommar format
echo "Exporting the database to compressed .rommar format..."
DATE=$(date +%Y%m%d)
python scripts/database_manager.py export --output "instance/romarr_database_${DATE}.rommar"

echo "Done! The new structured database has been built."
