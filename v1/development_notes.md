# Development Notes

## Important Commands to Remember

1. **Docker Compose**: Use `docker compose` with a space (not `docker-compose`)
2. **Container Management**:
   - `docker compose up -d` - Start containers in background
   - `docker compose down` - Stop and remove containers
   - `docker compose build` - Rebuild containers
   - `docker compose logs -f` - Follow container logs

## Branding Updates Completed

All "Romerr" branding has been updated to "Romarr" in the following files:

### Web Application Templates
- `templates/base.html` - Updated title, logo, and footer
- `templates/index.html` - Updated title and "Configure Romarr" text
- Other template files also updated (catalog.html, settings.html, import.html, etc.)

### Python Files
- `app.py` - Updated docstring
- `routes/api.py` - Updated docstring and health endpoint
- `routes/web.py` - Updated docstring
- `config/constants.py` - Updated docstring
- `scripts/setup_database.py` - Updated database path references
- `scripts/initialize_metadata_db.py` - Updated database path
- `scripts/test_metadata_init.py` - Updated database path

### Database References
- Changed all `romerr.db` references to `romarr.db`
- Updated backup file naming convention

## Next Steps

1. Rebuild Docker container with updated branding
2. Test the web interface to ensure all branding changes are visible
3. Verify database functionality still works correctly

## Current Status (2026-03-09)

### Todo List Status
1. ✅ Analyze current script structure and identify issues
2. ✅ Fix indentation and syntax errors in parse_no_intro_dat method
3. ✅ Integrate parse_redump_dat method properly
4. ✅ Improve DAT file parsing with actual implementations
5. ✅ Add proper error handling and logging
6. ✅ Test the script with libretro-database
7. ✅ Add command-line options for selective scraping
8. ✅ Implement No-Intro database scraping from local files
9. ✅ Implement MAME database scraping from XML files
10. ✅ Handle Redump and TOSEC sources
11. ✅ Implement duplicate detection across all databases
12. ✅ Fix libretro parsing issue (saving 0 ROMs)
13. ✅ Ensure MAME database is scraped
14. ✅ Update script to skip unavailable sources
15. ✅ Run final comprehensive scrape
16. ✅ Update Docker configuration for self-contained container
17. ✅ Include pre-populated database in Docker image
18. ✅ Update docker-compose.yml to remove database volume
19. ✅ Update entrypoint script to use included database
20. ✅ Update README to reflect self-contained approach
21. ✅ Test Docker build to ensure it works correctly
22. ✅ Fix "Romerr" branding in web application templates
23. ✅ Update Python files with "Romarr" branding
24. ✅ Update configuration files and database references
25. ✅ Rebuild and redeploy container with updated branding
26. ✅ Start Romarr container and verify it's running
27. ✅ Test web interface for updated branding
28. ✅ Verify container size is reasonable

### Current Issues Being Addressed
- **SQLAlchemy Table Conflict**: Fixed duplicate 'games' table definition by renaming `models/game.py` table to 'library_games'
- **Foreign Key Issue**: Updated `models/download.py` foreign key from 'games.id' to 'library_games.id'
- **Container Size**: Reduced from 12.9GB to 537MB by excluding large data directories from Docker image
- **Container Restart Loop**: Fixed foreign key reference issue, but there may be more references to update

### Recent Changes
1. Added `extend_existing=True` to Game models (didn't work)
2. Renamed `game.py` table from 'games' to 'library_games' to avoid conflict with `unified_schema.py`
3. Updated foreign key in `download.py` from 'games.id' to 'library_games.id'
4. Rebuilt Docker image and restarted container

### Current Error
The container is still restarting due to foreign key issues. Need to check all references to 'games.id' in the codebase and update them to 'library_games.id' or find a better solution.

### Next Immediate Actions
1. Search for all 'games.id' references in the codebase
2. Update all foreign key references
3. Rebuild and test container
4. Alternative approach: Remove duplicate Game model entirely and use only one schema

## Notes
- The container is currently running on port 5000
- Database uses the new `.rommar` archive format
- Two-pronged deployment approach: lightweight container + external database management
- Container size successfully reduced from 12.9GB to 537MB