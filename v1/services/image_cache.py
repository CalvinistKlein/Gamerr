"""
Image Cache Service for Romarr
================================
Provides lazy, on-demand image caching.
- Images are ONLY downloaded when a game is actually searched or viewed.
- Cached images are served from static/cache/images/ via Flask.
- The ImageCache DB table tracks what has been cached and when it was last accessed.
"""

import os
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

# Where cached images are stored (relative to app root, served as static files)
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          'static', 'cache', 'images')


def _ensure_cache_dir():
    """Make sure the cache directory exists."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def _url_to_filename(url: str, image_type: str, entity_type: str, entity_id: int) -> str:
    """
    Convert a remote URL to a stable local filename.
    Uses a hash of the URL so we avoid filesystem path issues.
    """
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    ext = os.path.splitext(urlparse(url).path)[1] or '.jpg'
    return f"{entity_type}_{entity_id}_{image_type}_{url_hash}{ext}"


def get_or_fetch(url: str,
                 entity_type: str,
                 entity_id: int,
                 image_type: str,
                 timeout: int = 10) -> Optional[str]:
    """
    Return the Flask-accessible URL for a cached image.
    If the image isn't cached yet, download it now and store it.

    Args:
        url:         Remote image URL (e.g. from IGDB)
        entity_type: 'game', 'platform', or 'company'
        entity_id:   ID of the entity this image belongs to
        image_type:  'cover', 'screenshot', 'artwork', or 'logo'
        timeout:     HTTP timeout in seconds

    Returns:
        Flask URL path '/static/cache/images/<filename>' on success, or None.
    """
    if not url:
        return None

    from extensions import db
    from models.unified_schema import ImageCache

    # 1. Check if already cached in DB
    cached = ImageCache.query.filter_by(url=url).first()
    if cached and cached.is_valid and os.path.exists(cached.local_path):
        # Update access tracking
        cached.last_accessed = datetime.utcnow()
        cached.access_count = (cached.access_count or 0) + 1
        db.session.commit()
        # Return as a Flask static URL
        relative = os.path.relpath(cached.local_path,
                                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return '/' + relative.replace(os.sep, '/')

    # 2. Download the image
    _ensure_cache_dir()
    filename = _url_to_filename(url, image_type, entity_type, entity_id)
    local_path = os.path.join(CACHE_DIR, filename)

    try:
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        file_size = 0
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                file_size += len(chunk)

        # Detect format from content-type or extension
        content_type = response.headers.get('Content-Type', '')
        if 'jpeg' in content_type or 'jpg' in content_type:
            fmt = 'jpg'
        elif 'png' in content_type:
            fmt = 'png'
        elif 'webp' in content_type:
            fmt = 'webp'
        else:
            fmt = os.path.splitext(filename)[1].lstrip('.') or 'jpg'

        # 3. Record in DB (upsert)
        if cached:
            cached.local_path = local_path
            cached.file_size = file_size
            cached.format = fmt
            cached.is_valid = True
            cached.error_message = None
            cached.downloaded_at = datetime.utcnow()
            cached.last_accessed = datetime.utcnow()
            cached.access_count = (cached.access_count or 0) + 1
        else:
            cached = ImageCache(
                url=url,
                image_type=image_type,
                entity_type=entity_type,
                entity_id=entity_id,
                local_path=local_path,
                file_size=file_size,
                format=fmt,
                downloaded_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                access_count=1,
                is_valid=True,
            )
            db.session.add(cached)

        db.session.commit()
        relative = os.path.relpath(local_path,
                                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return '/' + relative.replace(os.sep, '/')

    except Exception as e:
        logger.warning(f"Failed to cache image {url}: {e}")
        # Mark as invalid in DB so we don't retry on every request this session
        if cached:
            cached.is_valid = False
            cached.error_message = str(e)
            db.session.commit()
        return None


def get_cached_url(entity_type: str, entity_id: int, image_type: str) -> Optional[str]:
    """
    Return the Flask URL for an already-cached image without downloading.
    Returns None if not yet cached.
    """
    from models.unified_schema import ImageCache

    cached = ImageCache.query.filter_by(
        entity_type=entity_type,
        entity_id=entity_id,
        image_type=image_type,
        is_valid=True
    ).first()

    if cached and os.path.exists(cached.local_path):
        relative = os.path.relpath(cached.local_path,
                                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return '/' + relative.replace(os.sep, '/')
    return None


def cleanup_old_cache(days: int = 30) -> int:
    """
    Remove cached images that haven't been accessed in `days` days.
    Returns the number of entries removed.

    Call this from a scheduled maintenance task, not on every request.
    """
    from extensions import db
    from models.unified_schema import ImageCache

    cutoff = datetime.utcnow() - timedelta(days=days)
    old_entries = ImageCache.query.filter(ImageCache.last_accessed < cutoff).all()

    removed = 0
    for entry in old_entries:
        try:
            if os.path.exists(entry.local_path):
                os.remove(entry.local_path)
            db.session.delete(entry)
            removed += 1
        except Exception as e:
            logger.warning(f"Failed to remove cached image {entry.local_path}: {e}")

    db.session.commit()
    logger.info(f"Image cache cleanup: removed {removed} entries older than {days} days")
    return removed
