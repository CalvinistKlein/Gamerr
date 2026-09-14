"""
ROM file detection and platform identification service
"""

import os
import re
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from config.constants import PLATFORMS

class ROMDetector:
    """Service for detecting ROM file information and platform"""
    
    # File extension to platform mapping
    EXTENSION_MAP = {
        # Nintendo
        '.nes': 'NES',
        '.smc': 'SNES',
        '.sfc': 'SNES',
        '.n64': 'N64',
        '.z64': 'N64',
        '.v64': 'N64',
        '.gcm': 'GameCube',
        '.iso': 'GameCube',
        '.wbfs': 'Wii',
        '.wad': 'Wii',
        '.wux': 'Wii U',
        '.nsp': 'Switch',
        '.xci': 'Switch',
        
        # Game Boy
        '.gb': 'Game Boy',
        '.gbc': 'Game Boy Color',
        '.gba': 'Game Boy Advance',
        '.nds': 'DS',
        '.3ds': '3DS',
        '.cia': '3DS',
        
        # Sega
        '.sms': 'Master System',
        '.gen': 'Genesis',
        '.md': 'Genesis',
        '.smd': 'Genesis',
        '.bin': 'Saturn',
        '.iso': 'Saturn',
        '.cdi': 'Dreamcast',
        '.gdi': 'Dreamcast',
        
        # PlayStation
        '.bin': 'PlayStation',
        '.cue': 'PlayStation',
        '.iso': 'PlayStation',
        '.pbp': 'PlayStation',
        '.iso': 'PlayStation 2',
        '.bin': 'PlayStation 2',
        '.iso': 'PlayStation 3',
        '.pkg': 'PlayStation 3',
        '.iso': 'PlayStation 4',
        '.pkg': 'PlayStation 4',
        
        # Xbox
        '.iso': 'Xbox',
        '.xbe': 'Xbox',
        '.iso': 'Xbox 360',
        '.xex': 'Xbox 360',
        '.iso': 'Xbox One',
        
        # Other
        '.pce': 'PC Engine',
        '.ng': 'Neo Geo',
        '.zip': 'Arcade',  # MAME ROMs often in zip
        '.7z': 'Arcade',
        '.chd': 'Arcade',
    }
    
    # Platform-specific file patterns for detection
    PLATFORM_PATTERNS = {
        'NES': [r'\.nes$', r'\(nes\)', r'\[nes\]', r'\bnes\b'],
        'SNES': [r'\.smc$', r'\.sfc$', r'\(snes\)', r'\[snes\]', r'\bsnes\b'],
        'N64': [r'\.n64$', r'\.z64$', r'\.v64$', r'\(n64\)', r'\[n64\]', r'\bn64\b'],
        'GameCube': [r'\.gcm$', r'\(gamecube\)', r'\(gc\)', r'\bgc\b'],
        'Wii': [r'\.wbfs$', r'\.wad$', r'\(wii\)', r'\bwii\b'],
        'Switch': [r'\.nsp$', r'\.xci$', r'\(switch\)', r'\bswitch\b'],
        'Game Boy': [r'\.gb$', r'\(gb\)', r'\bgame ?boy\b'],
        'Game Boy Color': [r'\.gbc$', r'\(gbc\)', r'\bgame ?boy ?color\b'],
        'Game Boy Advance': [r'\.gba$', r'\(gba\)', r'\bgame ?boy ?advance\b'],
        'DS': [r'\.nds$', r'\(ds\)', r'\bds\b', r'\bnintendo ?ds\b'],
        '3DS': [r'\.3ds$', r'\.cia$', r'\(3ds\)', r'\b3ds\b'],
        'Genesis': [r'\.gen$', r'\.md$', r'\.smd$', r'\(genesis\)', r'\(megadrive\)', r'\bgenesis\b'],
        'PlayStation': [r'\.bin$', r'\.cue$', r'\(ps1\)', r'\(psx\)', r'\bplaystation\b'],
        'PlayStation 2': [r'\(ps2\)', r'\bplaystation ?2\b'],
        'PlayStation 3': [r'\.pkg$', r'\(ps3\)', r'\bplaystation ?3\b'],
        'PlayStation 4': [r'\.pkg$', r'\(ps4\)', r'\bplaystation ?4\b'],
        'Xbox': [r'\.xbe$', r'\(xbox\)', r'\bxbox\b'],
        'Xbox 360': [r'\.xex$', r'\(xbox ?360\)', r'\bxbox ?360\b'],
        'Arcade': [r'\.zip$', r'\.7z$', r'\.chd$', r'\(arcade\)', r'\(mame\)', r'\barcade\b'],
    }
    
    # Region detection patterns
    REGION_PATTERNS = {
        'USA': [r'\(usa\)', r'\(us\)', r'\[usa\]', r'\[us\]', r'\busa\b', r'\bus\b'],
        'Europe': [r'\(europe\)', r'\(eu\)', r'\(pal\)', r'\[europe\]', r'\[eu\]', r'\beurope\b', r'\beu\b', r'\bpal\b'],
        'Japan': [r'\(japan\)', r'\(jp\)', r'\(ntsc-j\)', r'\[japan\]', r'\[jp\]', r'\bjapan\b', r'\bjp\b'],
        'Asia': [r'\(asia\)', r'\(as\)', r'\[asia\]', r'\basia\b'],
        'Australia': [r'\(australia\)', r'\(au\)', r'\[australia\]', r'\baustralia\b', r'\bau\b'],
    }
    
    @classmethod
    def detect_platform_from_filename(cls, filename: str) -> Optional[str]:
        """
        Detect platform from filename using patterns and extensions
        
        Args:
            filename: The filename to analyze
            
        Returns:
            Detected platform or None if unknown
        """
        filename_lower = filename.lower()
        
        # First check by file extension
        file_ext = Path(filename_lower).suffix
        if file_ext in cls.EXTENSION_MAP:
            return cls.EXTENSION_MAP[file_ext]
        
        # Check for platform patterns in filename
        for platform, patterns in cls.PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, filename_lower, re.IGNORECASE):
                    return platform
        
        return None
    
    @classmethod
    def detect_region_from_filename(cls, filename: str) -> Optional[str]:
        """
        Detect region from filename
        
        Args:
            filename: The filename to analyze
            
        Returns:
            Detected region or None if unknown
        """
        filename_lower = filename.lower()
        
        for region, patterns in cls.REGION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, filename_lower, re.IGNORECASE):
                    return region
        
        return None
    
    @classmethod
    def extract_title_from_filename(cls, filename: str) -> str:
        """
        Extract clean game title from filename
        
        Args:
            filename: The filename to process
            
        Returns:
            Clean game title
        """
        # Remove file extension
        name = Path(filename).stem
        
        # Common patterns to remove
        patterns_to_remove = [
            # Platform indicators
            r'\([^)]*nes[^)]*\)', r'\([^)]*snes[^)]*\)', r'\([^)]*n64[^)]*\)',
            r'\([^)]*gamecube[^)]*\)', r'\([^)]*gc[^)]*\)', r'\([^)]*wii[^)]*\)',
            r'\([^)]*switch[^)]*\)', r'\([^)]*gb[^)]*\)', r'\([^)]*gbc[^)]*\)',
            r'\([^)]*gba[^)]*\)', r'\([^)]*ds[^)]*\)', r'\([^)]*3ds[^)]*\)',
            r'\([^)]*genesis[^)]*\)', r'\([^)]*megadrive[^)]*\)',
            r'\([^)]*ps[0-9]*[^)]*\)', r'\([^)]*playstation[^)]*\)',
            r'\([^)]*xbox[^)]*\)', r'\([^)]*arcade[^)]*\)', r'\([^)]*mame[^)]*\)',
            
            # Region indicators
            r'\([^)]*usa[^)]*\)', r'\([^)]*us[^)]*\)',
            r'\([^)]*europe[^)]*\)', r'\([^)]*eu[^)]*\)', r'\([^)]*pal[^)]*\)',
            r'\([^)]*japan[^)]*\)', r'\([^)]*jp[^)]*\)', r'\([^)]*ntsc[^)]*\)',
            r'\([^)]*asia[^)]*\)', r'\([^)]*australia[^)]*\)', r'\([^)]*au[^)]*\)',
            
            # Quality indicators
            r'\([^)]*rev[^)]*\)', r'\([^)]*v[0-9][^)]*\)',
            r'\[[^\]]*nes[^\]]*\]', r'\[[^\]]*snes[^\]]*\]',
            r'\[[^\]]*usa[^\]]*\]', r'\[[^\]]*japan[^\]]*\]',
            
            # Common tags
            r'\[[^\]]*\]', r'\([^)]*\)',
            
            # File identifiers
            r'\.\w+$',  # Any remaining file extensions
        ]
        
        # Apply patterns
        for pattern in patterns_to_remove:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        # Clean up: remove extra spaces, underscores, dots
        name = name.replace('_', ' ').replace('.', ' ').strip()
        name = re.sub(r'\s+', ' ', name)  # Collapse multiple spaces
        
        # Capitalize first letter of each word
        name = ' '.join(word.capitalize() for word in name.split())
        
        return name if name else Path(filename).stem
    
    @classmethod
    def detect_file_info(cls, filepath: str) -> Dict:
        """
        Detect all information from a ROM file
        
        Args:
            filepath: Path to the ROM file
            
        Returns:
            Dictionary with detected information
        """
        filename = Path(filepath).name
        file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        
        # Detect platform
        platform = cls.detect_platform_from_filename(filename)
        
        # Detect region
        region = cls.detect_region_from_filename(filename)
        
        # Extract title
        title = cls.extract_title_from_filename(filename)
        
        # Try to detect release year from filename
        release_year = None
        year_match = re.search(r'\((\d{4})\)', filename)
        if year_match:
            try:
                release_year = int(year_match.group(1))
            except ValueError:
                pass
        
        return {
            'filename': filename,
            'file_path': filepath,
            'file_size': file_size,
            'detected_title': title,
            'detected_platform': platform,
            'detected_region': region,
            'detected_release_year': release_year,
            'confidence': 'high' if platform else 'low',
            'is_archive': filename.lower().endswith(('.zip', '.7z', '.rar'))
        }
    
    @classmethod
    def extract_roms_from_archive(cls, archive_path: str, extract_to: Optional[str] = None) -> List[Dict]:
        """
        Extract ROM files from a ZIP archive and detect their information
        
        Args:
            archive_path: Path to the ZIP archive
            extract_to: Directory to extract to (optional, uses temp directory if not provided)
            
        Returns:
            List of detected ROM file information from the archive
        """
        rom_files = []
        
        if not archive_path.lower().endswith('.zip'):
            return rom_files
        
        # Create temporary directory for extraction if not provided
        temp_dir = None
        if not extract_to:
            temp_dir = tempfile.mkdtemp(prefix='romerr_extract_')
            extract_to = temp_dir
        
        try:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                # Get list of files in archive
                file_list = zip_ref.namelist()
                
                # Filter for ROM files
                rom_extensions = set(cls.EXTENSION_MAP.keys())
                rom_files_in_archive = [
                    f for f in file_list
                    if Path(f).suffix.lower() in rom_extensions
                ]
                
                # Extract and detect each ROM
                for rom_file in rom_files_in_archive:
                    try:
                        # Extract file
                        zip_ref.extract(rom_file, extract_to)
                        extracted_path = os.path.join(extract_to, rom_file)
                        
                        # Detect file info
                        file_info = cls.detect_file_info(extracted_path)
                        file_info['archive_source'] = archive_path
                        file_info['extracted_path'] = extracted_path
                        
                        rom_files.append(file_info)
                    except Exception as e:
                        print(f"Error processing {rom_file} in archive: {e}")
                        continue
        
        except Exception as e:
            print(f"Error extracting archive {archive_path}: {e}")
        
        finally:
            # Clean up temporary directory if we created it
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
        
        return rom_files
    
    @classmethod
    def is_archive_file(cls, filename: str) -> bool:
        """
        Check if a file is an archive (ZIP, 7Z, RAR)
        
        Args:
            filename: Filename to check
            
        Returns:
            True if file is an archive
        """
        return filename.lower().endswith(('.zip', '.7z', '.rar'))
    
    @classmethod
    def scan_directory(cls, directory_path: str, extract_archives: bool = True) -> List[Dict]:
        """
        Scan a directory for ROM files and detect their information
        
        Args:
            directory_path: Path to directory to scan
            extract_archives: Whether to extract and scan ROMs from archive files
            
        Returns:
            List of detected ROM file information
        """
        rom_files = []
        
        if not os.path.exists(directory_path):
            return rom_files
        
        # Supported ROM file extensions
        rom_extensions = set(cls.EXTENSION_MAP.keys())
        archive_extensions = {'.zip', '.7z', '.rar'}
        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                filepath = os.path.join(root, file)
                file_ext = Path(file).suffix.lower()
                
                # Check if it's a ROM file
                if file_ext in rom_extensions:
                    file_info = cls.detect_file_info(filepath)
                    rom_files.append(file_info)
                
                # Check if it's an archive file and we should extract it
                elif extract_archives and file_ext in archive_extensions:
                    try:
                        if file_ext == '.zip':
                            # Extract ROMs from ZIP archive
                            archive_roms = cls.extract_roms_from_archive(filepath)
                            for rom_info in archive_roms:
                                rom_info['archive_source'] = filepath
                                rom_files.append(rom_info)
                        # Note: 7z and RAR extraction would require additional libraries
                        # For now, we just detect them as archives
                    except Exception as e:
                        print(f"Error processing archive {filepath}: {e}")
                        continue
        
        return rom_files
    
    @classmethod
    def validate_platform(cls, platform: str) -> bool:
        """
        Validate if a platform is in the supported list
        
        Args:
            platform: Platform name to validate
            
        Returns:
            True if platform is valid/supported
        """
        return platform in PLATFORMS