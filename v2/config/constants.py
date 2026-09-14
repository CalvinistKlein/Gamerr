"""
Application constants for Romarr
"""

# Game statuses
GAME_STATUS_LIBRARY = 'library'
GAME_STATUS_WANTED = 'wanted'
GAME_STATUS_DOWNLOADING = 'downloading'
GAME_STATUS_FAILED = 'failed'

# Wanted list statuses
WANTED_STATUS_PENDING = 'pending'
WANTED_STATUS_SEARCHING = 'searching'
WANTED_STATUS_FOUND = 'found'
WANTED_STATUS_FAILED = 'failed'

# Download statuses
DOWNLOAD_STATUS_QUEUED = 'queued'
DOWNLOAD_STATUS_DOWNLOADING = 'downloading'
DOWNLOAD_STATUS_COMPLETED = 'completed'
DOWNLOAD_STATUS_FAILED = 'failed'

# Platform constants
PLATFORMS = [
    'NES', 'SNES', 'N64', 'GameCube', 'Wii', 'Wii U', 'Switch',
    'Game Boy', 'Game Boy Color', 'Game Boy Advance', 'DS', '3DS',
    'Master System', 'Genesis', 'Saturn', 'Dreamcast',
    'PlayStation', 'PlayStation 2', 'PlayStation 3', 'PlayStation 4',
    'Xbox', 'Xbox 360', 'Xbox One',
    'PC (DOS)', 'PC (Windows)', 'ScummVM', 'Commodore 64', 'Commodore Amiga',
    'PC Engine', 'Neo Geo', 'Arcade', 'MAME'
]

# Region constants
REGIONS = [
    'USA', 'Europe', 'Japan', 'Asia', 'Australia',
    'Brazil', 'Canada', 'China', 'France', 'Germany',
    'Italy', 'Korea', 'Spain', 'Taiwan', 'World'
]

# Color scheme for UI
COLORS = {
    'primary': '#3ecf6e',
    'secondary': '#6c63ff',
    'warning': '#e8871a',
    'error': '#ff4757',
    'info': '#2d8cf0',
    'success': '#3ecf6e',
    'dark': '#1a1a2e',
    'light': '#f8f9fa',
    'gray': '#6c757d'
}

# Automation intervals (in seconds)
AUTOMATION_INTERVAL = 300  # 5 minutes
DOWNLOAD_CHECK_INTERVAL = 60  # 1 minute
SEARCH_INTERVAL = 3600  # 1 hour
AUTOMATION_ENABLED = True
AUTOMATION_MAX_CONCURRENT_DOWNLOADS = 3