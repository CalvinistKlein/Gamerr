# ROM Scraping and Metadata Collection Architecture

## 1. Overview

A unified pipeline for discovering ROM files, collecting metadata from multiple sources, and storing enriched game information. Built on existing components with improved integration and data quality.

## 2. Existing Components Analysis

### 2.1 ROM Detector (`services/rom_detector.py`)
- **Strengths**: File extension mapping, platform pattern detection
- **Limitations**: No hash calculation, limited metadata extraction
- **Improvements Needed**: Add CRC/MD5/SHA1 calculation, file header analysis

### 2.2 Libretro Importer (`services/libretro_importer.py`)
- **Strengths**: DAT file parsing, CRC matching, basic metadata
- **Limitations**: Limited to libretro database, no rich metadata
- **Improvements Needed**: Better error handling, incremental updates

### 2.3 IGDB Client (`services/igdb_client.py`)
- **Strengths**: Comprehensive API, rich metadata fields, rate limiting
- **Limitations**: Requires API key, rate limited, dependent on external service
- **Improvements Needed**: Caching, fallback strategies, batch operations

### 2.4 Error Handler (`services/error_handler.py`)
- **Strengths**: Rate limiting, retry logic, exponential backoff
- **Limitations**: Not integrated with scraping components
- **Improvements Needed**: Integration with all external API calls

## 3. New Scraping Architecture

### 3.1 Pipeline Stages

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Discovery     │───▶│   Enrichment    │───▶│   Storage       │
│   Phase         │    │   Phase         │    │   Phase         │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • File scanning │    │ • IGDB lookup   │    │ • Database      │
│ • Hash calc     │    │ • Image fetch   │    │   insertion     │
│ • Platform det  │    │ • Genre tagging │    │ • Cache update  │
│ • Basic metadata│    │ • Rating import │    │ • Search index  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Validation    │◀───│   Deduplication │◀───│   Normalization │
│   Phase         │    │   Phase         │    │   Phase         │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Data quality  │    │ • Duplicate     │    │ • Title cleanup │
│ • Completeness  │    │   detection     │    │ • Field mapping │
│ • Business rules│    │ • Merge logic   │    │ • Type conversion│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 3.2 Component Design

#### 3.2.1 Discovery Service
```python
class DiscoveryService:
    """Finds and analyzes ROM files"""
    
    def scan_directory(path: str) -> List[ROMFile]:
        """Recursively scan directory for ROM files"""
        
    def calculate_hashes(file_path: str) -> Dict[str, str]:
        """Calculate CRC32, MD5, SHA1 hashes"""
        
    def extract_basic_metadata(file_path: str) -> BasicMetadata:
        """Extract title, platform, region from filename"""
        
    def match_against_databases(hashes: Dict) -> Optional[DatMatch]:
        """Match hashes against No-Intro/Redump databases"""
```

#### 3.2.2 Enrichment Service
```python
class EnrichmentService:
    """Enhances basic metadata with external sources"""
    
    def enrich_from_igdb(basic_metadata: BasicMetadata) -> IGDBGame:
        """Fetch comprehensive metadata from IGDB"""
        
    def fetch_images(game: Game) -> ImageCollection:
        """Download cover art, screenshots, artwork"""
        
    def classify_genres(game: Game) -> List[Genre]:
        """AI/rule-based genre classification"""
        
    def calculate_ratings(game: Game) -> RatingSummary:
        """Aggregate ratings from multiple sources"""
```

#### 3.2.3 Storage Service
```python
class StorageService:
    """Manages data storage and retrieval"""
    
    def store_game(game: Game) -> GameRecord:
        """Store game in database with proper relationships"""
        
    def update_search_index(game: Game) -> None:
        """Update full-text search index"""
        
    def cache_metadata(game: Game) -> None:
        """Cache metadata for faster retrieval"""
        
    def backup_metadata(game: Game) -> None:
        """Create backup of metadata"""
```

## 4. Data Flow

### 4.1 Primary Flow
1. **File Discovery**: Scan filesystem for ROM files
2. **Hash Calculation**: Compute file hashes for identification
3. **Basic Metadata**: Extract from filename and headers
4. **Database Lookup**: Check if game already exists
5. **External Enrichment**: Fetch from IGDB and other sources
6. **Image Processing**: Download and optimize images
7. **Data Validation**: Ensure completeness and quality
8. **Storage**: Save to database with relationships
9. **Indexing**: Update search and cache layers

### 4.2 Fallback Flow
If primary source (IGDB) fails:
1. Try alternative APIs (RAWG, MobyGames)
2. Use libretro database as fallback
3. Use filename-based metadata as last resort
4. Flag for manual review

## 5. Integration Points

### 5.1 With Existing Database
- **Game Model**: Extend with hash fields, metadata relationships
- **Platform Model**: Standardize platform names across sources
- **Genre Model**: Unified genre taxonomy
- **Image Model**: Store and cache downloaded images

### 5.2 With External Services
- **IGDB API**: Primary metadata source
- **Libretro Database**: Platform-specific verification
- **No-Intro/Redump**: Hash verification
- **Image CDNs**: Cover art and screenshots

## 6. Implementation Priorities

### Phase 1: Core Discovery (Week 1)
1. Enhanced ROM detector with hash calculation
2. Directory scanning service
3. Basic metadata extraction from filenames
4. Integration with existing ROM detector

### Phase 2: Metadata Enrichment (Week 2)
1. IGDB client integration with caching
2. Image downloading service
3. Data normalization pipeline
4. Fallback strategy implementation

### Phase 3: Storage Integration (Week 3)
1. Database schema extensions for new metadata
2. Search index implementation
3. Cache layer for performance
4. Backup and recovery procedures

### Phase 4: Quality & Performance (Week 4)
1. Data quality validation
2. Performance optimization
3. Monitoring and alerting
4. Documentation and testing

## 7. Data Model Extensions

### New Fields Needed:
- **File Hashes**: CRC32, MD5, SHA1 for verification
- **Source Tracking**: Which service provided which metadata
- **Confidence Scores**: How reliable is this metadata
- **Image References**: URLs and local paths for images
- **External IDs**: IGDB ID, libretro ID, etc.

### New Tables Needed:
- `game_hashes`: Multiple hash types per game file
- `metadata_sources`: Track source of each metadata field
- `image_cache`: Downloaded and processed images
- `scraping_log`: Audit trail of scraping operations

## 8. Success Metrics

### Data Quality:
- >90% metadata completion for discovered ROMs
- <5% duplicate entries
- <2% data validation errors

### Performance:
- <30 seconds per ROM for full processing
- <100ms for database lookups
- <5% API failure rate

### Reliability:
- 99.9% successful processing of valid ROMs
- Graceful degradation when services are unavailable
- Comprehensive error logging and recovery

## 9. Next Steps

1. **Implement enhanced ROM detector** with hash calculation
2. **Create directory scanning service**
3. **Integrate IGDB client with rate limiting**
4. **Design database schema extensions**
5. **Build end-to-end scraping pipeline**

This architecture builds on existing strengths while addressing limitations through a unified, robust pipeline.