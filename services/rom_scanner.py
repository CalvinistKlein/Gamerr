"""
Enhanced ROM Scanner with Hash Calculation
Extends the existing ROM detector with file hashing and improved metadata extraction
"""

import os
import re
import hashlib
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import logging

from services.rom_detector import ROMDetector

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ROMFile:
    """Represents a discovered ROM file with calculated metadata"""
    path: str
    filename: str
    size: int
    modified_time: datetime
    platform: str
    extension: str
    
    # Hashes
    crc32: Optional[str] = None
    md5: Optional[str] = None
    sha1: Optional[str] = None
    
    # Extracted metadata
    title: Optional[str] = None
    region: Optional[str] = None
    version: Optional[str] = None
    language: Optional[str] = None
    
    # Detection confidence
    confidence: float = 0.0
    detection_method: str = "unknown"
    
    # Raw data for debugging
    raw_filename: str = ""
    

class ROMScanner:
    """Enhanced ROM scanning service with hash calculation"""
    
    # Region patterns in filenames
    REGION_PATTERNS = {
        'USA': [r'\(usa\)', r'\[usa\]', r'\busa\b', r'\(u\)', r'\[u\]'],
        'Europe': [r'\(europe\)', r'\[europe\]', r'\beurope\b', r'\(eu\)', r'\[eu\]', r'\(e\)', r'\[e\]'],
        'Japan': [r'\(japan\)', r'\[japan\]', r'\bjapan\b', r'\(j\)', r'\[j\]'],
        'Asia': [r'\(asia\)', r'\[asia\]', r'\basia\b'],
        'Australia': [r'\(australia\)', r'\[australia\]', r'\baustralia\b', r'\(aus\)', r'\[aus\]'],
        'Brazil': [r'\(brazil\)', r'\[brazil\]', r'\bbrazil\b', r'\(br\)', r'\[br\]'],
        'World': [r'\(world\)', r'\[world\]', r'\bworld\b'],
        'Korea': [r'\(korea\)', r'\[korea\]', r'\bkorea\b', r'\(kr\)', r'\[kr\]'],
        'China': [r'\(china\)', r'\[china\]', r'\bchina\b', r'\(cn\)', r'\[cn\]'],
        'Taiwan': [r'\(taiwan\)', r'\[taiwan\]', r'\btaiwan\b', r'\(tw\)', r'\[tw\]'],
    }
    
    # Version patterns
    VERSION_PATTERNS = {
        'Rev A': [r'\(rev a\)', r'\[rev a\]', r'\brev a\b'],
        'Rev B': [r'\(rev b\)', r'\[rev b\]', r'\brev b\b'],
        'Rev 1': [r'\(rev 1\)', r'\[rev 1\]', r'\brev 1\b'],
        'Rev 2': [r'\(rev 2\)', r'\[rev 2\]', r'\brev 2\b'],
        'Beta': [r'\(beta\)', r'\[beta\]', r'\bbeta\b'],
        'Proto': [r'\(proto\)', r'\[proto\]', r'\bproto\b'],
        'Demo': [r'\(demo\)', r'\[demo\]', r'\bdemo\b'],
        'Unl': [r'\(unl\)', r'\[unl\]', r'\bunl\b'],  # Unlicensed
    }
    
    # Language patterns
    LANGUAGE_PATTERNS = {
        'English': [r'\(en\)', r'\[en\]', r'\benglish\b'],
        'Japanese': [r'\(ja\)', r'\[ja\]', r'\bjapanese\b'],
        'French': [r'\(fr\)', r'\[fr\]', r'\bfrench\b'],
        'German': [r'\(de\)', r'\[de\]', r'\bgerman\b'],
        'Spanish': [r'\(es\)', r'\[es\]', r'\bspanish\b'],
        'Italian': [r'\(it\)', r'\[it\]', r'\bitalian\b'],
    }
    
    @classmethod
    def scan_directory(cls, directory_path: str, recursive: bool = True) -> List[ROMFile]:
        """
        Scan a directory for ROM files
        
        Args:
            directory_path: Path to scan
            recursive: Whether to scan subdirectories
            
        Returns:
            List of discovered ROM files
        """
        rom_files = []
        path = Path(directory_path)
        
        if not path.exists():
            logger.error(f"Directory does not exist: {directory_path}")
            return rom_files
        
        # Determine scan method
        if recursive:
            scan_method = path.rglob
        else:
            scan_method = path.glob
        
        # Supported extensions from ROMDetector
        supported_extensions = set(ROMDetector.EXTENSION_MAP.keys())
        
        # Scan for files
        for file_path in scan_method('*'):
            if file_path.is_file():
                extension = file_path.suffix.lower()
                
                # Check if file has supported extension
                if extension in supported_extensions:
                    try:
                        rom_file = cls.analyze_file(str(file_path))
                        if rom_file:
                            rom_files.append(rom_file)
                    except Exception as e:
                        logger.error(f"Error analyzing file {file_path}: {e}")
        
        logger.info(f"Found {len(rom_files)} ROM files in {directory_path}")
        return rom_files
    
    @classmethod
    def analyze_file(cls, file_path: str) -> Optional[ROMFile]:
        """
        Analyze a single ROM file and extract metadata
        
        Args:
            file_path: Path to the ROM file
            
        Returns:
            ROMFile object with metadata, or None if not a valid ROM
        """
        try:
            path = Path(file_path)
            
            # Basic file info
            stat = path.stat()
            filename = path.name
            extension = path.suffix.lower()
            
            # Detect platform using existing ROMDetector
            platform = cls._detect_platform(filename, extension)
            if not platform:
                logger.debug(f"Could not detect platform for {filename}")
                return None
            
            # Calculate hashes
            hashes = cls._calculate_hashes(file_path)
            
            # Extract metadata from filename
            title, region, version, language = cls._extract_metadata_from_filename(filename)
            
            # Create ROMFile object
            rom_file = ROMFile(
                path=str(file_path),
                filename=filename,
                size=stat.st_size,
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                platform=platform,
                extension=extension,
                crc32=hashes.get('crc32'),
                md5=hashes.get('md5'),
                sha1=hashes.get('sha1'),
                title=title,
                region=region,
                version=version,
                language=language,
                confidence=cls._calculate_confidence(filename, platform, hashes),
                detection_method="extension_pattern",
                raw_filename=filename
            )
            
            logger.debug(f"Analyzed {filename}: platform={platform}, size={stat.st_size}, hashes={hashes}")
            return rom_file
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return None
    
    @classmethod
    def _detect_platform(cls, filename: str, extension: str) -> Optional[str]:
        """
        Detect platform using multiple methods
        
        Args:
            filename: Name of the file
            extension: File extension
            
        Returns:
            Platform name or None if not detected
        """
        # Method 1: Use existing ROMDetector extension mapping
        platform = ROMDetector.EXTENSION_MAP.get(extension)
        if platform:
            return platform
        
        # Method 2: Use filename patterns from ROMDetector
        filename_lower = filename.lower()
        for platform_name, patterns in ROMDetector.PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, filename_lower, re.IGNORECASE):
                    return platform_name
        
        # Method 3: Check for platform keywords in filename
        platform_keywords = {
            'nes': 'NES',
            'snes': 'SNES',
            'n64': 'N64',
            'gamecube': 'GameCube',
            'wii': 'Wii',
            'switch': 'Switch',
            'gb': 'Game Boy',
            'gbc': 'Game Boy Color',
            'gba': 'Game Boy Advance',
            'genesis': 'Genesis',
            'megadrive': 'Genesis',
            'playstation': 'PlayStation',
            'ps1': 'PlayStation',
            'ps2': 'PlayStation 2',
            'ps3': 'PlayStation 3',
            'ps4': 'PlayStation 4',
            'xbox': 'Xbox',
            'xbox360': 'Xbox 360',
            'arcade': 'Arcade',
            'mame': 'Arcade',
        }
        
        for keyword, platform_name in platform_keywords.items():
            if keyword in filename_lower:
                return platform_name
        
        return None
    
    @classmethod
    def _calculate_hashes(cls, file_path: str) -> Dict[str, str]:
        """
        Calculate multiple hash types for a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with hash types as keys and hash values as values
        """
        hashes = {
            'crc32': None,
            'md5': None,
            'sha1': None
        }
        
        try:
            # Read file in chunks for memory efficiency
            chunk_size = 65536  # 64KB
            crc_value = 0
            md5_hash = hashlib.md5()
            sha1_hash = hashlib.sha1()
            
            with open(file_path, 'rb') as f:
                while chunk := f.read(chunk_size):
                    crc_value = zlib.crc32(chunk, crc_value)
                    md5_hash.update(chunk)
                    sha1_hash.update(chunk)
            
            # Convert CRC32 to hex string (ensure positive)
            hashes['crc32'] = format(crc_value & 0xFFFFFFFF, '08x')
            hashes['md5'] = md5_hash.hexdigest()
            hashes['sha1'] = sha1_hash.hexdigest()
            
        except Exception as e:
            logger.error(f"Error calculating hashes for {file_path}: {e}")
        
        return hashes
    
    @classmethod
    def _extract_metadata_from_filename(cls, filename: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        Extract metadata from filename using patterns
        
        Args:
            filename: Name of the file
            
        Returns:
            Tuple of (title, region, version, language)
        """
        # Clean filename (remove extension)
        clean_name = re.sub(r'\.[^.]*$', '', filename, flags=re.IGNORECASE)
        clean_name_lower = clean_name.lower()
        
        # Extract region
        region = None
        for region_name, patterns in cls.REGION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, clean_name_lower, re.IGNORECASE):
                    region = region_name
                    break
            if region:
                break
        
        # Extract version
        version = None
        for version_name, patterns in cls.VERSION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, clean_name_lower, re.IGNORECASE):
                    version = version_name
                    break
            if version:
                break
        
        # Extract language
        language = None
        for language_name, patterns in cls.LANGUAGE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, clean_name_lower, re.IGNORECASE):
                    language = language_name
                    break
            if language:
                break
        
        # Extract title (clean up filename)
        title = clean_name
        
        # Remove common patterns from title
        patterns_to_remove = []
        
        # Add region patterns
        if region:
            for pattern in cls.REGION_PATTERNS.get(region, []):
                patterns_to_remove.append(pattern)
        
        # Add version patterns
        if version:
            for pattern in cls.VERSION_PATTERNS.get(version, []):
                patterns_to_remove.append(pattern)
        
        # Add language patterns
        if language:
            for pattern in cls.LANGUAGE_PATTERNS.get(language, []):
                patterns_to_remove.append(pattern)
        
        # Remove patterns from title
        for pattern in patterns_to_remove:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # Clean up title
        title = re.sub(r'[\[\]()]', ' ', title)  # Remove brackets/parentheses
        title = re.sub(r'\s+', ' ', title)  # Collapse multiple spaces
        title = title.strip()
        
        # If title is empty after cleaning, use original clean name
        if not title:
            title = clean_name
        
        return title, region, version, language
    
    @classmethod
    def _calculate_confidence(cls, filename: str, platform: str, hashes: Dict[str, str]) -> float:
        """
        Calculate confidence score for detection
        
        Args:
            filename: Name of the file
            platform: Detected platform
            hashes: Calculated hashes
            
        Returns:
            Confidence score from 0.0 to 1.0
        """
        confidence = 0.0
        
        # Base confidence for having a platform
        if platform:
            confidence += 0.3
        
        # Confidence for having hashes
        if hashes.get('crc32'):
            confidence += 0.2
        if hashes.get('md5'):
            confidence += 0.2
        if hashes.get('sha1'):
            confidence += 0.2
        
        # Confidence for clean filename (no random characters)
        if re.match(r'^[a-zA-Z0-9\s\[\]()\-\.]+$', filename):
            confidence += 0.1
        
        # Cap at 1.0
        return min(confidence, 1.0)
    
    @classmethod
    def batch_process(cls, directory_path: str, recursive: bool = True) -> Dict[str, Any]:
        """
        Process a directory and return statistics
        
        Args:
            directory_path: Path to scan
            recursive: Whether to scan subdirectories
            
        Returns:
            Dictionary with processing statistics
        """
        logger.info(f"Starting batch processing of {directory_path}")
        start_time = datetime.now()
        
        # Scan directory
        rom_files = cls.scan_directory(directory_path, recursive)
        
        # Calculate statistics
        platforms = {}
        regions = {}
        total_size = 0
        
        for rom_file in rom_files:
            # Platform statistics
            platform = rom_file.platform
            platforms[platform] = platforms.get(platform, 0) + 1
            
            # Region statistics
            region = rom_file.region or 'Unknown'
            regions[region] = regions.get(region, 0) + 1
            
            # Total size
            total_size += rom_file.size
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        statistics = {
            'total_files': len(rom_files),
            'platforms': platforms,
            'regions': regions,
            'total_size_bytes': total_size,
            'total_size_gb': total_size / (1024**3),
            'processing_time_seconds': processing_time,
            'files_per_second': len(rom_files) / processing_time if processing_time > 0 else 0,
            'sample_files': [{
                'filename': f.filename,
                'platform': f.platform,
                'size': f.size,
                'hashes': {
                    'crc32': f.crc32,
                    'md5': f.md5,
                    'sha1': f.sha1
                }
            } for f in rom_files[:5]]  # First 5 files as sample
        }
        
        logger.info(f"Batch processing completed: {statistics['total_files']} files in {statistics['processing_time_seconds']:.2f}s")
        return statistics


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Test with current directory
    scanner = ROMScanner()
    stats = scanner.batch_process(".", recursive=False)
    print(f"Found {stats['total_files']} ROM files")
    print(f"Platforms: {stats['platforms']}")
    print(f"Total size: {stats['total_size_gb']:.2f} GB")