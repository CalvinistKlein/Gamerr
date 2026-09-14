#!/bin/bash
# Setup script for ROM Management System
# Creates virtual environment, installs dependencies, and sets up database

set -e  # Exit on error

echo "========================================="
echo "ROM Management System - Environment Setup"
echo "========================================="

# Check Python version
echo "Checking Python version..."
python3 --version || { echo "Python 3 is required"; exit 1; }

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if additional dependencies are needed
echo "Checking for additional system dependencies..."
if command -v apt-get &> /dev/null; then
    echo "Detected Debian-based system"
    # Install system dependencies for Python packages
    sudo apt-get update
    sudo apt-get install -y python3-dev build-essential libssl-dev libffi-dev
fi

# Setup database
echo "Setting up database..."
if [ -f "scripts/setup_database.py" ]; then
    python scripts/setup_database.py
else
    echo "Database setup script not found, creating basic database..."
    python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Database tables created')
"
fi

# Create .env file if it doesn't exist
echo "Setting up environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Created .env file from example"
        echo "Please edit .env file to configure your settings"
    else
        echo "No .env.example found, creating basic .env..."
        cat > .env << EOF
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///instance/romarr.db

# External Services
PROWLARR_URL=http://localhost:9696
PROWLARR_API_KEY=

QBITTORRENT_URL=http://localhost:8080
QBITTORRENT_USERNAME=admin
QBITTORRENT_PASSWORD=adminadmin

# Paths
ROMS_PATH=/data/roms
EOF
        echo "Created basic .env file"
    fi
else
    echo ".env file already exists"
fi

echo ""
echo "========================================="
echo "Setup completed successfully!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Configure .env file with your settings"
echo "3. Import ROMs: python services/rom_importer.py /path/to/your/roms"
echo "4. Run the application: python app.py"
echo "5. Access web interface at http://localhost:5000"
echo ""
echo "For Docker deployment: docker-compose up -d"
echo "========================================="