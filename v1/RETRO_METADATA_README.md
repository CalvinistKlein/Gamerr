# Retro Gaming Metadata Scraper

A comprehensive Python script for automating the collection of retro gaming metadata from DAT files and IGDB API, with 1G1R (One Game One ROM) filtering and SQLite database storage.

## Features

- **DAT File Parsing**: Parse No-Intro and Redump DAT files (XML and ClrMamePro formats)
- **IGDB API Integration**: Fetch comprehensive game metadata from IGDB (Internet Game Database)
- **1G1R Filtering**: Intelligent filtering to select the best version of each game
- **Normalized Database**: SQLite database with normalized schema for games, platforms, genres, companies
- **Robust Error Handling**: Rate limiting, retry logic, and comprehensive logging
- **Multiple Export Formats**: Export to CSV or JSON for use in other applications
- **CLI Interface**: Easy-to-use command-line interface for all operations

## Requirements

- Python 3.8+
- IGDB API credentials (Twitch Developer account)

## Installation

1. Clone the repository or copy the script files to your project
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up IGDB API credentials (optional, for metadata fetching):

```bash
export IGDB_CLIENT_ID="your_client_id"
export IGDB_CLIENT_SECRET="your_client_secret"
```

Or create a `.env` file:
```
IGDB_CLIENT_ID=your_client_id
IGDB_CLIENT_SECRET=your_client_secret
```

## Project Structure

```
gamerr/
├── scripts/
│   └── retro_metadata_scraper.py    # Main CLI script
├── services/
│   ├── dat_parser.py                # DAT file parser
│   ├── igdb_client.py               # IGDB API client
│   ├── one_game_one_rom.py          # 1G1R filtering logic
│   └── error_handler.py             # Error handling utilities
├── models/
│   ├── metadata_db.py               # Enhanced database schema
│   └── (existing models)
├── test_retro_metadata.py           # Test suite
├── requirements.txt                  # Python dependencies
└── RETRO_METADATA_README.md         # This file
```

## Usage Examples

### 1. Parse DAT files only

```bash
# Parse a single DAT file
python scripts/retro_metadata_scraper.py parse --dat-path ./libretro-database/dat/Nintendo\ -\ Nintendo\ Entertainment\ System.dat

# Parse a directory of DAT files
python scripts/retro_metadata_scraper.py parse --dat-path ./libretro-database/dat --recursive --output ./games.csv
```

### 2. Run full pipeline (without IGDB metadata)

```bash
python scripts/retro_metadata_scraper.py full \
  --dat-path ./libretro-database/dat \
  --database ./retro_games.db \
  --no-metadata \
  --export ./games_export.csv
```

### 3. Run full pipeline with IGDB metadata

```bash
# Set IGDB credentials first
export IGDB_CLIENT_ID="your_client_id"
export IGDB_CLIENT_SECRET="your_client_secret"

python scripts/retro_metadata_scraper.py full \
  --dat-path ./libretro-database/dat \
  --database ./retro_games.db \
  --export ./games_with_metadata.csv
```

### 4. Export existing database

```bash
python scripts/retro_metadata_scraper.py export \
  --database ./retro_games.db \
  --output ./export.csv \
  --include-metadata
```

### 5. Show database statistics

```bash
python scripts/retro_metadata_scraper.py stats --database ./retro_games.db
```

### 6. Test IGDB connection

```bash
python scripts/retro_metadata_scraper.py test
```

## Command Reference

### Parse Command
```
python scripts/retro_metadata_scraper.py parse --dat-path PATH [--recursive] [--output FILE] [--no-1g1r]
```

- `--dat-path`: Path to DAT file or directory
- `--recursive`: Search directories recursively (for directories)
- `--output`: Output CSV file path
- `--no-1g1r`: Skip 1G1R filtering

### Full Command
```
python scripts/retro_metadata_scraper.py full --dat-path PATH [--database FILE] [--recursive] [--no-1g1r] [--no-metadata] [--export FILE]
```

- `--dat-path`: Path to DAT file or directory
- `--database`: SQLite database path (default: metadata.db)
- `--recursive`: Search directories recursively
- `--no-1g1r`: Skip 1G1R filtering
- `--no-metadata`: Skip IGDB metadata fetching
- `--export`: Export to CSV after processing

### Export Command
```
python scripts/retro_metadata_scraper.py export --database FILE --output FILE [--format csv|json] [--include-metadata]
```

- `--database`: SQLite database path
- `--output`: Output file path
- `--format`: Output format (csv or json)
- `--include-metadata`: Include IGDB metadata in export

## 1G1R (One Game One ROM) Filtering

The 1G1R filtering logic prioritizes the best version of each game when multiple versions exist:

### Priority Rules
1. **Region Priority**: USA > World > Europe > Japan > Other regions
2. **Version Type**: Retail > Revision > Enhanced > Translation > Hack > Demo > Beta > Prototype > Pirate
3. **Language**: English versions preferred (if `prefer_english=True`)
4. **Exclusions**: Prototypes, demos, and pirate versions can be excluded

### Configuration Options
- `--no-1g1r`: Disable 1G1R filtering entirely
- Custom filtering options available in `OneGameOneRomFilter` class

## Database Schema

The normalized database schema includes:

### Core Tables
- `metadata_games`: Main game information
- `metadata_platforms`: Console/platform information
- `metadata_genres`: Game genres
- `metadata_companies`: Developers and publishers
- `metadata_roms`: ROM file information (hashes, sizes)
- `metadata_release_dates`: Release dates by region

### Association Tables
- Game-Platform (many-to-many)
- Game-Genre (many-to-many)
- Game-Developer (many-to-many)
- Game-Publisher (many-to-many)

## IGDB API Integration

### Required Credentials
1. Create a Twitch Developer account at https://dev.twitch.tv/
2. Register an application to get Client ID and Client Secret
3. Set environment variables:
   - `IGDB_CLIENT_ID`: Your Twitch application Client ID
   - `IGDB_CLIENT_SECRET`: Your Twitch application Client Secret

### Rate Limiting
- Default: 4 requests per second (IGDB rate limit is 4 requests/second)
- Automatic retry with exponential backoff
- Request queuing to avoid rate limit errors

## Error Handling and Logging

### Logging
- Console output with colored levels
- File logging to `retro_metadata_scraper.log`
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)

### Error Recovery
- Automatic retry for failed API calls (3 retries by default)
- Exponential backoff between retries
- Graceful degradation when IGDB API is unavailable
- Database transaction rollback on errors

### Progress Tracking
- Real-time progress updates
- ETA calculation for long operations
- Memory usage monitoring (with psutil)

## Testing

Run the test suite:

```bash
python test_retro_metadata.py
```

The test suite includes:
- DAT file parser tests
- 1G1R filtering tests
- Database schema tests
- Error handler tests
- Main script structure tests

## Performance Considerations

### Memory Usage
- Processes games in batches to control memory usage
- Optional memory monitoring with psutil
- Database commits every 100 games to balance performance and memory

### Processing Speed
- Parallel processing not implemented (to avoid IGDB rate limiting)
- Typical speed: 2-5 games/second with IGDB metadata fetching
- Much faster without IGDB API calls (100+ games/second)

### Database Optimization
- Indexes on frequently queried columns
- Batch inserts for better performance
- SQLite WAL mode for concurrent access

## Integration with Existing Project

This scraper is designed to integrate with the existing Romerr project:

### Compatibility
- Uses existing Flask-SQLAlchemy configuration
- Shares database connection with main application
- Can run alongside existing services

### Extending the Catalog
The scraper populates the enhanced `metadata_games` table, which can be:
1. Used as a reference for the existing `GameCatalog` model
2. Integrated with the ROM detector service for automatic identification
3. Used to enhance search functionality in the web interface

## Troubleshooting

### Common Issues

1. **IGDB API errors**: Check your credentials and rate limits
2. **DAT file parsing errors**: Ensure DAT files are in correct format
3. **Database errors**: Check file permissions and disk space
4. **Memory errors**: Process fewer games at once or increase batch size

### Log Files
- Check `retro_metadata_scraper.log` for detailed error information
- Enable DEBUG logging for troubleshooting: `export LOG_LEVEL=DEBUG`

## Future Enhancements

### Planned Features
1. **ScreenScraper.fr integration**: Alternative metadata source
2. **Parallel processing**: For faster DAT file parsing
3. **Incremental updates**: Update only changed games
4. **Web interface**: For managing the metadata database
5. **ROM matching**: Match existing ROM files to database entries

### Community Contributions
- Additional DAT file format support
- More platform mappings
- Enhanced fuzzy matching algorithms
- Export to additional formats (XML, SQL dumps)

## License

This project is part of the Romerr/Gamerr ecosystem. See the main project LICENSE for details.

## Acknowledgments

- **No-Intro** and **Redump** for DAT files
- **IGDB** for comprehensive game metadata
- **RetroArch** for libretro-database
- The retro gaming preservation community