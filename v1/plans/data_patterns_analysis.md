# Data Patterns and Requirements Analysis

## 1. ROM File Analysis Results

### 1.1 Test Results Summary
From testing the ROM scanner with sample filenames:

**Platform Detection:**
- `.nes` → NES (correct)
- `.n64` → N64 (correct)  
- `.gen` → Genesis (correct)
- `.smc` → SNES (correct)
- `.gb` → Game Boy (correct)
- `.gba` → Game Boy Advance (correct)
- `.zip` → Arcade (correct for MAME)
- `.iso` → Xbox One (INCORRECT - ambiguous mapping)

**Region Detection:**
- `(USA)` → USA (correct)
- `(Japan)` → Japan (correct)
- `(Europe)` → Europe (correct)
- `(World)` → World (correct)
- `(En)` → English language (correct)

**Title Extraction:**
- "Super Mario Bros. (USA).nes" → "Super Mario Bros." (correct)
- "The Legend of Zelda (Japan).nes" → "The Legend of Zelda" (correct)
- "Chrono Trigger (Japan) (En).smc" → "Chrono Trigger" (correct)

### 1.2 Issues Identified

#### Platform Detection Ambiguity:
- `.iso` extension maps to multiple platforms (GameCube, Saturn, PlayStation, Xbox, etc.)
- `.bin` extension also ambiguous (Saturn, PlayStation, etc.)
- Need better disambiguation using filename patterns or file headers

#### Hash Calculation:
- Empty files produce zero hashes (expected)
- Real ROMs will have meaningful hashes for verification

#### Metadata Completeness:
- Missing: Release year, publisher, developer, genre, description
- Missing: Player count, game modes, ratings
- Missing: Cover art, screenshots

## 2. Data Requirements from Existing System

### 2.1 Current Database Models Analysis

#### `models/game.py` (Simple Schema):
```python
# Fields: id, title, platform, region, release_year, file_path, file_size, 
# added_date, last_played, play_count, status
```
**Missing**: Hashes, detailed metadata, relationships

#### `models/metadata_db.py` (Complex Schema):
```python
# 10+ tables with comprehensive metadata:
# - metadata_games: Core game info
# - metadata_platforms: Platform details  
# - metadata_genres: Genre classification
# - metadata_companies: Developers/publishers
# - metadata_roms: ROM file info with hashes
# - metadata_release_dates: Release dates by region
# - Plus: themes, game_modes, player_perspectives, keywords, alternative_names
```
**Strengths**: Comprehensive, normalized, relationships
**Weaknesses**: Overly complex, not integrated with simple schema

#### `models/catalog.py` (Catalog Schema):
```python
# Fields: title, platform, region, release_year, publisher, developer, genre,
# description, players, rating, cover_image_url, screenshot_urls, source
```
**Strengths**: Good balance of metadata
**Weaknesses**: No hashes, denormalized

## 3. Data Patterns from Real ROM Collections

### 3.1 Common ROM Naming Conventions
Based on community standards (No-Intro, Redump):

1. **Standard Format**: `Game Title (Region) (Version).ext`
   - Example: `Super Mario Bros. (USA) (Rev A).nes`
   
2. **Multi-disc**: `Game Title (Region) (Disc X).ext`
   - Example: `Final Fantasy VII (USA) (Disc 1).bin`
   
3. **Multi-region**: `Game Title (Region1-Region2).ext`
   - Example: `Sonic the Hedgehog (USA-Europe).gen`
   
4. **Special Editions**: `Game Title - Special Edition (Region).ext`
   - Example: `The Legend of Zelda - Collector's Edition (USA).gcm`

### 3.2 Metadata Availability by Source

#### IGDB API (Primary Source):
- **Complete**: Title, description, release dates, platforms, genres, companies
- **Partial**: Ratings (user and critic), cover art, screenshots
- **Limited**: Exact ROM matching (needs manual mapping)

#### Libretro Database (Secondary Source):
- **Complete**: ROM hashes (CRC), basic title, publisher
- **Partial**: Region, platform mapping
- **Limited**: No rich metadata, no images

#### No-Intro/Redump (Verification Source):
- **Complete**: Exact file hashes, file sizes
- **Partial**: Standardized naming
- **Limited**: No descriptive metadata

## 4. Database Requirements Analysis

### 4.1 Core Requirements

#### 1. File Tracking:
- Multiple hash types (CRC32, MD5, SHA1)
- File paths and sizes
- Platform and region detection
- Import timestamps

#### 2. Game Metadata:
- Title (clean and original)
- Description and storyline
- Release dates and years
- Genres and themes
- Developers and publishers
- Ratings and review counts

#### 3. Media Assets:
- Cover art URLs and local cache
- Screenshot URLs and local cache
- Artwork and video URLs

#### 4. Relationships:
- Game to multiple ROM files (different regions/versions)
- Game to multiple platforms
- Game to multiple genres/themes
- Game to developers/publishers

### 4.2 Performance Requirements

#### Query Patterns:
1. **Library Browsing**: Filter by platform, genre, sort by title/rating
2. **Search**: Full-text search on titles and descriptions
3. **ROM Matching**: Hash-based lookup for file verification
4. **Statistics**: Counts by platform, genre, completion status

#### Volume Estimates:
- Small collection: 100-500 games
- Medium collection: 500-5,000 games  
- Large collection: 5,000-50,000 games
- Each game: 1-10 ROM files, 5-20 metadata relationships

### 4.3 Data Quality Requirements

#### Validation Rules:
1. **Required Fields**: Title, platform, at least one hash
2. **Unique Constraints**: Hash combinations, title+platform+region
3. **Data Types**: Proper enums for status, region, platform
4. **Relationships**: Foreign key constraints with cascade rules

#### Quality Metrics:
- >90% metadata completion for discovered ROMs
- <5% duplicate entries
- <2% data validation errors
- 100% referential integrity

## 5. Schema Design Implications

### 5.1 Lessons from Current Implementation

#### What Works:
- Simple `Game` model for basic library management
- Comprehensive `metadata_db` for rich metadata
- `Catalog` model as middle ground

#### What Doesn't Work:
- Dual schema without integration
- Missing hash storage for verification
- No transaction management
- Poor error handling

### 5.2 Recommended Approach

**Unified Schema with Modular Design**:
1. **Core Tables**: Game, Platform, Genre (essential for all use cases)
2. **File Tables**: ROMFile with hashes, GameFile relationship
3. **Metadata Tables**: Extended metadata (optional, can be lazy-loaded)
4. **Relationship Tables**: Many-to-many relationships

**Progressive Enhancement**:
- Start with essential fields
- Add extended metadata as needed
- Support partial data (games with only basic info)
- Allow enrichment over time

## 6. Next Steps for Database Design

### Phase 1: Essential Schema
1. **Game**: Core game information
2. **Platform**: Console/platform details  
3. **ROMFile**: File hashes and paths
4. **Genre**: Game genres

### Phase 2: Extended Metadata
5. **Company**: Developers and publishers
6. **Release**: Release dates by region
7. **Media**: Cover art and screenshots
8. **Rating**: User and critic ratings

### Phase 3: Advanced Features
9. **Collection**: Game series and collections
10. **PlayHistory**: User play statistics
11. **Wishlist**: Games to acquire
12. **Download**: Download tracking

## 7. Implementation Priorities

### High Priority (Week 1):
1. Unified Game table with essential fields
2. ROMFile table with hash storage
3. Platform and Genre reference tables
4. Basic API for CRUD operations

### Medium Priority (Week 2):
5. Extended metadata tables
6. Relationship management
7. Search functionality
8. Image caching

### Low Priority (Week 3+):
9. Advanced statistics
10. User preferences
11. Backup and migration
12. Performance optimization

## 8. Success Criteria

### Data Model Success:
- [ ] All test ROMs can be stored with basic metadata
- [ ] Hashes can be used for duplicate detection
- [ ] Platform and region detection works correctly
- [ ] Extended metadata can be added incrementally

### Performance Success:
- [ ] <100ms response for common queries
- [ ] <1s for full collection scan
- [ ] <5s for hash-based lookups
- [ ] Scalable to 50,000+ games

### Quality Success:
- [ ] >95% data integrity
- [ ] <1% duplicate entries
- [ ] Comprehensive error handling
- [ ] Graceful degradation when metadata unavailable

This analysis provides the foundation for designing a database schema that meets the actual needs of ROM management while being scalable and maintainable.