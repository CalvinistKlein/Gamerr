# Gamerr (Romarr) v2

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3+-lightgrey.svg)
![SQLite](https://img.shields.io/badge/SQLite-3.x-green.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**Gamerr (Romarr) v2** is an automated video game collection, metadata, and download management system built with the familiar design language and workflow of Sonarr and Radarr (*arr ecosystem).

It automatically monitors your desired retro and PC games, searches indexers via Prowlarr, sends downloads to qBittorrent, organizes your library, and identifies ROM files using intelligent hash and filename detection.

---

## ⚡ Key Highlights in v2

* **Sonarr / Radarr Design Language**: Sleek dark slate theme (`#0f1317` / `#171c22` / Sonarr Cyan `#06b6d4`), responsive 2:3 poster cover grid with status ribbons and progress indicators, overview table view, and Radarr-style game detail backdrops.
* **Zero-Key Remote Metadata (SkyHook Model)**: End users never need to sign up for developer accounts or configure IGDB/Twitch API keys. Metadata is queried from the central Gamerr SkyHook proxy (`api.gamerr.io`) with automatic seed catalog fallback.
* **PC & Retro Era/Generation Cross-Mapping**: Dedicated support for PC (MS-DOS, Windows, ScummVM, Commodore 64, Commodore Amiga). Games dynamically match historical hardware generations (Gen 3 through Gen 8) and decades (1970s through 2020s).
* **Decoupled Lightweight Architecture**: The local SQLite database (`romarr.db`) manages strictly your monitored games, downloads, and scanned library, preventing multi-gigabyte database bloat.
* **Full *arr Ecosystem Orchestration**: Ready-to-go `docker-compose.yml` coordinating Gamerr, Prowlarr (indexers), and qBittorrent (client) with isolated networking.
* **Robust Automated Test Suite**: 100% test pass rate across unit tests, route integration tests, and full-system audit tests.

---

## 🚀 Quick Start (Docker Compose)

### 1. Launch the Stack
```bash
git clone https://github.com/calvink/gamerr.git
cd gamerr/v2

# Start Gamerr, Prowlarr, and qBittorrent
docker compose up -d
```

### 2. Access Web Interfaces
* **Gamerr UI**: [http://localhost:5000](http://localhost:5000)
* **Prowlarr (Indexers)**: [http://localhost:9696](http://localhost:9696)
* **qBittorrent (Downloads)**: [http://localhost:8080](http://localhost:8080) *(User: admin, Pass: adminadmin)*

---

## 💻 Manual Installation (Bare Metal)

### 1. Requirements
* Python 3.11+
* SQLite 3

### 2. Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run Development Server
```bash
python app.py
```
The application will automatically initialize the database schema and seed the initial catalog of iconic retro and PC titles.

---

## 🌐 Zero-Key SkyHook Metadata Proxy

Gamerr v2 queries metadata without requiring individual API keys from users:
* **Default Endpoint**: Configured to `https://api.gamerr.io/v1` via `METADATA_API_URL`.
* **Self-Hosting the Proxy**: You can run your own metadata proxy using the included `scripts/metadata_server.py` microservice:
  ```bash
  # Standalone
  python scripts/metadata_server.py --port 5001

  # Or via Docker Compose profile
  docker compose --profile metadata up -d metadata-server
  ```

---

## 🎮 Supported Platforms

| Category | Platforms | Supported Formats |
| :--- | :--- | :--- |
| **8-Bit (Gen 3)** | NES, Famicom, Master System, Commodore 64 | `.nes`, `.fds`, `.sms`, `.d64`, `.t64` |
| **16-Bit (Gen 4)** | SNES, Sega Genesis, Mega Drive, Game Boy, Amiga, ScummVM | `.sfc`, `.smc`, `.md`, `.bin`, `.gb`, `.adf`, `.svm` |
| **32/64-Bit (Gen 5)** | PlayStation, Nintendo 64, Saturn, DOS VGA | `.iso`, `.cue`, `.chd`, `.n64`, `.z64`, `.dosbox`, `.conf` |
| **128-Bit (Gen 6)** | PlayStation 2, GameCube, Xbox, Dreamcast, GBA | `.iso`, `.gcm`, `.cso`, `.chd`, `.gba` |
| **Modern & PC** | PC (DOS), PC (Windows), PS3, Xbox 360, Wii, Switch | `.exe`, `.msi`, `.wbfs`, `.nsp`, `.xci`, `.zip`, `.7z` |

---

## 🧪 Testing & Verification

Run the comprehensive 23-test suite:
```bash
PYTHONPATH=. python -m unittest discover tests
```

Tests verify:
1. `test_rom_detector.py`: ROM file identification, extensions, release years, and title normalization.
2. `test_integration.py`: Database schema relationships, import pipeline, and routes.
3. `test_audit.py`: All web views, all JSON API endpoints, wanted lifecycle, and metadata fallback.

---

## 📄 License
MIT License. Open source and community-driven.
