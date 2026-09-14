#!/bin/bash
# Setup script for Retro Gaming Metadata Scraper

set -e

echo "========================================="
echo "Retro Gaming Metadata Scraper Setup"
echo "========================================="

# Check Python version
echo "Checking Python version..."
python3 --version || { echo "Python 3 is required"; exit 1; }

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv || { echo "Failed to create virtual environment"; exit 1; }

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating directories..."
mkdir -p logs
mkdir -p exports
mkdir -p databases

# Check for IGDB credentials
echo ""
echo "========================================="
echo "IGDB API Setup (Optional)"
echo "========================================="
echo "To fetch game metadata from IGDB, you need:"
echo "1. A Twitch Developer account: https://dev.twitch.tv/"
echo "2. Register an application to get Client ID and Client Secret"
echo ""
echo "You can set credentials in several ways:"
echo ""
echo "A) Environment variables:"
echo "   export IGDB_CLIENT_ID='your_client_id'"
echo "   export IGDB_CLIENT_SECRET='your_client_secret'"
echo ""
echo "B) .env file (create .env in project root):"
echo "   IGDB_CLIENT_ID=your_client_id"
echo "   IGDB_CLIENT_SECRET=your_client_secret"
echo ""
echo "C) Command line (each time you run the script):"
echo "   IGDB_CLIENT_ID=your_client_id IGDB_CLIENT_SECRET=your_client_secret python scripts/retro_metadata_scraper.py ..."
echo ""
echo "Note: The scraper will work without IGDB credentials, but will only"
echo "      parse DAT files without fetching additional metadata."

# Create sample .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating sample .env file..."
    cat > .env.example << EOF
# IGDB API Credentials (from Twitch Developer Portal)
IGDB_CLIENT_ID=your_client_id_here
IGDB_CLIENT_SECRET=your_client_secret_here

# Database configuration (optional)
DATABASE_URL=sqlite:///databases/retro_games.db

# Logging configuration (optional)
LOG_LEVEL=INFO
LOG_FILE=logs/retro_metadata.log
EOF
    echo "Created .env.example. Copy to .env and edit with your credentials."
fi

# Test the installation
echo ""
echo "========================================="
echo "Testing Installation"
echo "========================================="
echo "Running basic tests..."
if python test_retro_metadata.py; then
    echo "✓ Tests passed!"
else
    echo "⚠ Some tests failed, but installation may still work."
    echo "  Check the error messages above for details."
fi

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Quick Start Examples:"
echo ""
echo "1. Parse a DAT file:"
echo "   python scripts/retro_metadata_scraper.py parse --dat-path /path/to/dat/file.dat"
echo ""
echo "2. Parse a directory of DAT files:"
echo "   python scripts/retro_metadata_scraper.py parse --dat-path /path/to/dat/files --recursive"
echo ""
echo "3. Run full pipeline (without IGDB metadata):"
echo "   python scripts/retro_metadata_scraper.py full --dat-path /path/to/dat/files --no-metadata"
echo ""
echo "4. Get help:"
echo "   python scripts/retro_metadata_scraper.py --help"
echo ""
echo "For detailed instructions, see RETRO_METADATA_README.md"
echo ""
echo "To activate the virtual environment in the future:"
echo "   source venv/bin/activate"
echo ""
echo "========================================="