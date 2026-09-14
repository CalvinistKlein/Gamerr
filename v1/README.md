# Gamerr - Comprehensive ROM Database Management System

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![SQLite](https://img.shields.io/badge/SQLite-3.x-green.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

A powerful, comprehensive ROM database management system that scrapes, organizes, and manages ROM metadata from multiple sources including No-Intro, MAME, and libretro databases. The system features a web interface for browsing, searching, and managing your ROM collection.

## 🚀 Features

- **Multi-Source Database Scraping**: Automatically scrape ROM metadata from:
  - **No-Intro** (342 DAT files, 315 platforms)
  - **MAME** (XML database, 1,954 platforms/categories)
  - **libretro** (30 platforms)
  - **Redump & TOSEC** (supported when databases become available)

- **Duplicate Detection**: Intelligent duplicate prevention across all databases using CRC32, MD5, and SHA1 checksums

- **Web Interface**: Modern Flask-based web UI for:
  - Browsing ROMs by platform, source, or category
  - Searching ROM metadata
  - Managing wanted lists
  - Tracking downloads
  - Importing custom DAT/XML files

- **Command-Line Tools**: Flexible scraping with options for:
  - Selective source scraping
  - Platform filtering
  - Dry-run mode
  - Custom database paths

## 📊 System Architecture

```
gamerr/
├── scripts/
│   └── scrape_comprehensive_database.py  # Main scraper
├── instance/
│   └── romarr.db                         # SQLite database
├── models/                               # Database models
├── routes/                               # Flask routes
├── templates/                            # HTML templates
├── static/                               # CSS/JS assets
└── services/                             # Business logic
```

## 🛠️ Installation

### Prerequisites
- **Docker** (recommended) or **Python 3.8+**
- **Docker Compose** (for Docker deployment)
- **Git**

### Quick Start (Docker - Recommended)
```bash
# Clone the repository
git clone <repository-url>
cd gamerr

# Start the self-contained Docker container
docker-compose up --build

# Access the web interface at http://localhost:5000
```

The Docker container includes:
- ✅ Pre-populated database with 3M+ ROMs
- ✅ Web interface ready to use
- ✅ No scraping required
- ✅ Production-ready configuration

### Manual Installation (Without Docker)
```bash
# Clone the repository
git clone <repository-url>
cd gamerr

# Install dependencies
pip install -r requirements.txt

# Set up environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Initialize the database (this will take several hours)
python scripts/scrape_comprehensive_database.py

# Start the web application
python app.py
```

### Docker Installation (Alternative)
```bash
# Build and run with Docker Compose (includes pre-populated database)
docker-compose up --build
```

## 📖 Usage

### 1. Database Scraping

Run the comprehensive scraper to populate your database:

```bash
# Scrape all available sources
python scripts/scrape_comprehensive_database.py

# Scrape specific sources only
python scripts/scrape_comprehensive_database.py --sources no-intro mame libretro

# Scrape with platform filtering
python scripts/scrape_comprehensive_database.py --platforms "Nintendo - Nintendo Entertainment System" "Sega - Mega Drive"

# Dry run (no database changes)
python scripts/scrape_comprehensive_database.py --dry-run

# View help
python scripts/scrape_comprehensive_database.py --help
```

### 2. Web Interface

Start the Flask web application:

```bash
# Development server
python app.py

# Production (with Gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Access the web interface at `http://localhost:5000`

### 3. Database Management

```bash
# Check database statistics
sqlite3 instance/romarr.db "SELECT source, COUNT(*) FROM roms GROUP BY source;"

# Export ROM list to CSV
sqlite3 instance/romarr.db ".headers on" ".mode csv" ".output roms.csv" "SELECT * FROM roms LIMIT 1000;"
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file based on `.env.example`:

```env
FLASK_APP=app.py
FLASK_ENV=development
DATABASE_URL=sqlite:///instance/romarr.db
SECRET_KEY=your-secret-key-here
```

### Database Sources Configuration
The scraper is configured in `scripts/scrape_comprehensive_database.py` with:

```python
self.sources = {
    'no-intro': {
        'name': 'No-Intro',
        'local_path': 'No-Intro Love Pack (Standard) (2026-03-09)',
        # ... platforms and URLs
    },
    'mame': {
        'name': 'MAME',
        'local_path': 'Mame_XML_Full_Lists_0.285_Arcade',
        # ... platforms
    },
    # ... other sources
}
```

## 📈 Performance & Statistics

The system has been tested with:
- **3,102,511 ROMs** processed across all databases
- **2,299 platforms** total (315 No-Intro + 1,954 MAME + 30 libretro)
- **23 errors** (0.0007% error rate) - all due to malformed XML in MAME files
- **Duplicate prevention**: Automatic detection using UNIQUE constraints on (crc32, md5, sha1, platform_id)

### Database Schema
```sql
-- Platforms table
CREATE TABLE platforms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    manufacturer TEXT,
    generation TEXT,
    release_year INTEGER,
    media_type TEXT,
    source TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ROMs table with duplicate prevention
CREATE TABLE roms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    size INTEGER,
    crc32 TEXT,
    md5 TEXT,
    sha1 TEXT,
    platform_id INTEGER,
    region TEXT,
    languages TEXT,
    version TEXT,
    serial TEXT,
    edition TEXT,
    source TEXT,
    dat_file TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (platform_id) REFERENCES platforms (id),
    UNIQUE(crc32, md5, sha1, platform_id)  -- Duplicate prevention
);
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/

# Run specific test module
python -m pytest tests/test_rom_detector.py

# Run with coverage
python -m pytest --cov=scripts tests/
```

## 🔄 Data Sources

### Currently Supported
1. **No-Intro Love Pack (Standard) (2026-03-09)**
   - 342 DAT files covering 315 platforms
   - Includes official, unofficial, and source code DATs
   - XML format with comprehensive checksums

2. **MAME XML Full Lists 0.285 Arcade**
   - 1,954 XML files organized by genre, manufacturer, year, etc.
   - Arcade game metadata without checksums (generated placeholders)

3. **libretro-database**
   - 30 DAT files for various platforms
   - Simple text format with CRC32 values

### Planned Support
- **Redump**: CD-based game verification database
- **TOSEC**: The Old School Emulation Center database
- **Custom DAT/XML**: User-uploaded database files

## 🚨 Error Handling

The system includes comprehensive error handling:

1. **XML Parsing Errors**: Malformed XML files are logged and skipped
2. **Database Constraints**: Duplicate ROMs are automatically ignored
3. **Missing Files**: Sources without local files are skipped with clear logging
4. **Network Issues**: Download failures are caught and retried

All errors are logged to `comprehensive_scraper.log` with timestamps and context.

## 📱 Web Interface Features

### Main Pages
- **Library**: Browse all ROMs with filtering and pagination
- **Catalog**: View ROMs organized by platform and source
- **Wanted**: Manage your wanted ROM list
- **Downloads**: Track download progress and status
- **Import**: Upload custom DAT/XML files

### Search & Filter
- Full-text search across ROM names and descriptions
- Filter by platform, source, region, and language
- Sort by name, size, or last updated

### Management Features
- Add/remove ROMs from wanted list
- Mark ROMs as downloaded
- Import custom database files
- Export ROM lists to CSV

## 🐳 Docker Deployment (Two-Pronged Approach)

Romarr uses a **two-pronged approach** to handle the large ROM database (1.8GB+):
1. **Lightweight Docker Container**: Contains only the web application
2. **External Database Management**: Generate/import the database separately

This approach avoids shipping massive Docker images while providing flexibility.

### Key Features:
- **Lightweight Container**: Small image size, fast deployment
- **Flexible Database Management**: Generate locally or import pre-built databases
- **Persistent Storage**: Database and ROMs stored in Docker volumes
- **Production-Ready**: Gunicorn server, health checks, proper user permissions

### Using Docker Compose
```yaml
version: '3.8'
services:
  romarr:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./config:/app/config  # Optional: custom configuration
      - romarr_data:/app/instance  # Database storage
      - roms_data:/data/roms  # ROM file storage
    environment:
      - DATABASE_URL=sqlite:////app/instance/romarr.db
      - ROMS_PATH=/data/roms
      - SECRET_KEY=your-secret-key-here
    restart: unless-stopped

volumes:
  romarr_data:
  roms_data:
```

### Quick Start with Docker Compose
```bash
# Clone and run
git clone <repository-url>
cd gamerr
docker-compose up --build

# The container will start with an empty database
# Access the web interface at http://localhost:5000
```

### Database Setup Options

#### Option 1: Generate Database Locally (Recommended)
Generate the database on your local machine, then import it:

```bash
# Step 1: Generate the database (takes several hours)
python scripts/database_manager.py generate --output instance/romarr.db

# Step 2: Export and compress the database
python scripts/database_manager.py export --input instance/romarr.db --output romarr.db.gz

# Step 3: Import into the container
python scripts/database_manager.py import --input romarr.db.gz --output instance/romarr.db

# Or copy directly to the Docker volume
docker cp instance/romarr.db gamerr-romarr-1:/app/instance/romarr.db
```

#### Option 2: Run Scraper Inside Container
Run the scraper directly in the running container:

```bash
# Execute the scraper inside the container
docker exec -it gamerr-romarr-1 python scripts/scrape_comprehensive_database.py

# This will take several hours but populate the database directly
```

#### Option 3: Use Pre-Built Database
If you have a pre-built database file:

```bash
# Import the database file
python scripts/database_manager.py import --input /path/to/romarr.db.gz --output instance/romarr.db
```

### Database Manager Tool
The `scripts/database_manager.py` tool provides comprehensive database management:

```bash
# Generate a new database
python scripts/database_manager.py generate --output instance/romarr.db --sources no-intro mame libretro

# Export database (compressed by default)
python scripts/database_manager.py export --input instance/romarr.db --output romarr.db.gz

# Import database
python scripts/database_manager.py import --input romarr.db.gz --output instance/romarr.db

# Get database information
python scripts/database_manager.py info --database instance/romarr.db
```

### What's Included in the Container:
1. **Web Application**:
   - Flask-based web interface for browsing ROMs
   - Gunicorn production server
   - Health checks and monitoring

2. **Database Tools**:
   - Comprehensive scraper for No-Intro, MAME, and libretro databases
   - Database schema with duplicate prevention
   - Import/export functionality

3. **Entrypoint Script**:
   - Automatic database initialization (creates empty database if needed)
   - ROM directory setup
   - Error handling and logging

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:////app/instance/romarr.db` | Database connection URL |
| `ROMS_PATH` | `/data/roms` | Path for ROM file storage |
| `SECRET_KEY` | (required) | Flask secret key for sessions |
| `INITIAL_ROM_IMPORT_PATH` | (optional) | Path to import ROMs on startup |
| `FORCE_DB_INIT` | `false` | Force database reinitialization |

### Performance Notes
- **Database Generation**: Takes 2-4 hours depending on system
- **Database Size**: ~1.8GB uncompressed, ~1.2GB compressed
- **Memory Usage**: Scraper uses ~2GB RAM during generation
- **Web Interface**: Fast response times with indexed database

## 🔍 Troubleshooting

### Common Issues

1. **"Database is locked" errors**
   ```bash
   # Check for other processes using the database
   fuser instance/romarr.db
   
   # Or simply delete and recreate
   rm instance/romarr.db
   python scripts/scrape_comprehensive_database.py
   ```

2. **Missing database files**
   - Ensure the database directories exist in the project root
   - Check file permissions: `chmod -R 755 instance/`

3. **XML parsing errors in MAME files**
   - These are data issues, not code issues
   - The system logs and skips malformed files
   - Consider cleaning the XML files or reporting to MAME maintainers

4. **Web interface not loading**
   ```bash
   # Check Flask is running
   curl http://localhost:5000/health
   
   # Check logs
   tail -f scraper_output.log
   ```

### Log Files
- `comprehensive_scraper.log`: Scraper execution logs
- `scraper_output.log`: Web interface and general application logs
- Flask debug logs in development mode

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Write tests for new features
- Update documentation
- Use meaningful commit messages

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/gamerr/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/gamerr/discussions)
- **Email**: support@example.com

## 🎯 Roadmap

### Short Term
- [ ] Add Redump database support
- [ ] Add TOSEC database support  
- [ ] Implement advanced search filters
- [ ] Add bulk operations in web interface

### Medium Term
- [ ] REST API for external integration
- [ ] User authentication and permissions
- [ ] ROM file detection and matching
- [ ] Cloud synchronization

### Long Term
- [ ] Distributed scraping architecture
- [ ] Machine learning for ROM categorization
- [ ] Mobile application
- [ ] Plugin system for custom sources

---

## 🏆 Acknowledgments

- **No-Intro** for their comprehensive DAT files
- **MAME** team for the arcade game database
- **libretro** community for their database efforts
- All contributors and testers of the Gamerr system

---

*Last updated: March 2026 | Version: 1.0.0*