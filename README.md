# Gamerr (Romarr)

Gamerr (formerly Romarr) is an automated video game collection, retro ROM catalog, metadata scraper, and download management platform modeled after the familiar workflows and design language of Sonarr and Radarr (*arr ecosystem).

It provides an end-to-end management pipeline that integrates with indexers via Prowlarr, sends automated downloads to torrent clients like qBittorrent, organizes local ROM libraries, enriches game metadata, and detects ROM files using intelligent hash, serial, and filename identification.

---

## AI Collaboration and Acknowledgments

This project was built and evolved with AI assistance from:
- **Claude (Anthropic)**: Designed the initial core architecture, database schemas, API integration models, search-to-download pipeline specifications, and structural implementation plans.
- **Gemini (Google DeepMind)**: Extended the platform to v2, engineered the zero-key SkyHook metadata proxy, implemented DAT file parsing and catalog ingestion, added batch operations, direct ROM upload mechanisms, system activity/event logging APIs, and full automated test auditing.

---

## System Architecture Overview

Gamerr is structured into modular builds:
- **v2 (Current Active Architecture)**: Flask REST API, SQLAlchemy ORM, Sonarr/Radarr dark slate UI, zero-key SkyHook metadata client with local seed fallback, DAT file / MAME XML catalog ingestion, single/multi ROM web uploader, batch game management, 1G1R deduplication, and automated unit/integration audit suites.
- **Romarr / v1 (Legacy Foundation)**: Original prototype services, RAWG and IGDB client integrations, initial SQLite schema models, and web UI templates.

---

## Key Features

### Automated *arr Ecosystem Management
- Search-to-download automation matching retro and PC titles against torrent indexers using Prowlarr.
- qBittorrent integration for download queue tracking, progress monitoring, and automatic library import upon completion.
- Configurable region and quality preferences.

### Zero-Key Remote Metadata Proxy
- Centralized SkyHook metadata proxy integration (`api.gamerr.io`) eliminating the need for end users to configure developer API keys for IGDB or Twitch.
- Self-hosting metadata proxy server capabilities included (`scripts/metadata_server.py`).
- Automatic local seed catalog fallback ensuring search availability offline.

### Multi-Era and Cross-Platform Support
- Era classification covering Generation 3 (8-Bit), Generation 4 (16-Bit), Generation 5 (32/64-Bit), Generation 6 (128-Bit), Generation 7, Generation 8, and Modern PC systems.
- Supported platforms include NES, SNES, Genesis, Game Boy (GBA/GBC), Nintendo 64, PlayStation (PS1/PS2/PSP), GameCube, Dreamcast, Saturn, MS-DOS, ScummVM, Amiga, and PC Windows.
- Multi-format file support (.iso, .cue, .chd, .sfc, .nes, .gba, .bin, .d64, .adf, .dosbox, .exe, .zip, .7z, .rar).

### DAT File and MAME XML Catalog Ingestion
- Native parsing of No-Intro and LibRetro CLRMAMEPRO `.dat` files as well as `MAME XML` machine lists.
- Automatic extraction of CRC32, MD5, SHA1, and serial numbers to seed local catalog databases without bloat.
- REST API progress tracking for background catalog building tasks.

### Direct ROM Upload and Archive Extraction
- Multipart HTTP file upload (`/api/upload/rom`) supporting single ROMs or compressed archives (.zip, .7z, .rar).
- Auto-extraction of archives into designated platform library paths (`/data/roms/<platform>/`).
- Intelligent title and platform identification via ROMDetector matching uploaded files to Wanted list entries and automatically updating status to completed.

### One Game One ROM (1G1R) and Deduplication
- Automated 1G1R deduplication engine (`services/one_game_one_rom.py`).
- Filtering rules to retain the optimal version per game based on user-defined regional priorities (e.g. USA over Europe/Japan) and revision ranks.

### Batch Operations and Management
- Batch deletion API (`DELETE /api/games/batch`) for atomic cleanup of multiple game records, wanted entries, and associated download data.
- Per-game metadata refresh (`POST /api/games/<id>/refresh-metadata`) for forced re-indexing.
- Database backup export endpoint (`GET /api/database/export`) for full SQLite database retrieval.

### Real-Time System Activity and Event Logging
- Unified system activity stream (`GET /api/activity`) combining live qBittorrent download progress with background worker task statuses.
- System event log API (`GET /api/logs`) providing structured log history for troubleshooting.

---

## Quick Start (Docker Compose)

### 1. Run Stack
```bash
git clone https://github.com/CalvinistKlein/Gamerr.git
cd Gamerr/v2
docker compose up -d
```

### 2. Access Web Interface
- Gamerr UI: http://localhost:5000
- Prowlarr: http://localhost:9696
- qBittorrent: http://localhost:8080 (User: admin, Pass: adminadmin)

---

## Manual Bare-Metal Installation

### Requirements
- Python 3.11+
- SQLite 3

### Environment Setup
```bash
cd v2
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

---

## Running the Automated Test Suite

Verify system integrity with the audit test suite:
```bash
cd v2
PYTHONPATH=. python -m unittest discover tests
```

---

## License

MIT License. Open source and community-driven.
