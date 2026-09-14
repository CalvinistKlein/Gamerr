"""
DAT File Parser for No-Intro and Redump XML format
Parses DAT files to extract game titles, regions, and file hashes
"""

import os
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ROMInfo:
    """Information about a ROM file"""
    name: str
    size: int
    crc: Optional[str] = None
    md5: Optional[str] = None
    sha1: Optional[str] = None
    sha256: Optional[str] = None
    serial: Optional[str] = None
    status: str = "verified"  # verified, bad, alternate


@dataclass
class GameEntry:
    """Game entry from DAT file"""
    name: str
    description: str
    roms: List[ROMInfo]
    category: Optional[str] = None
    publisher: Optional[str] = None
    developer: Optional[str] = None
    region: Optional[str] = None
    release_date: Optional[str] = None
    version: Optional[str] = None
    serial: Optional[str] = None
    edition: Optional[str] = None
    languages: List[str] = None
    
    def __post_init__(self):
        if self.languages is None:
            self.languages = []
    
    @property
    def clean_title(self) -> str:
        """Extract clean title by removing region, version, and other tags"""
        title = self.name
        
        # Remove common tags in parentheses
        patterns = [
            r'\s*\([^)]*(?:USA|Europe|Japan|World|Asia|Korea|Brazil|Germany|France|Italy|Spain|Australia|China|Taiwan|Hong Kong)[^)]*\)',
            r'\s*\([^)]*(?:Rev \d+|Version \d+\.\d+|v\d+\.\d+)[^)]*\)',
            r'\s*\([^)]*(?:Beta|Proto|Prototype|Demo|Sample|Preview)[^)]*\)',
            r'\s*\([^)]*(?:Unl|Aftermarket|Pirate|Bootleg)[^)]*\)',
            r'\s*\([^)]*(?:En|Fr|De|Es|It|Ja|Ko|Zh)[^)]*\)',
        ]
        
        for pattern in patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # Remove trailing spaces and special characters
        title = title.strip()
        
        return title
    
    @property
    def extracted_region(self) -> Optional[str]:
        """Extract region from game name"""
        region_patterns = {
            'USA': ['USA', 'United States', 'US', 'America'],
            'Europe': ['Europe', 'EU', 'PAL', 'UK', 'United Kingdom', 'Germany', 'France', 'Italy', 'Spain'],
            'Japan': ['Japan', 'JP', 'JPN'],
            'World': ['World', 'Worldwide'],
            'Asia': ['Asia', 'Korea', 'China', 'Taiwan', 'Hong Kong'],
            'Australia': ['Australia', 'AU'],
            'Brazil': ['Brazil', 'BR'],
        }
        
        for region, patterns in region_patterns.items():
            for pattern in patterns:
                if re.search(rf'\b{pattern}\b', self.name, re.IGNORECASE):
                    return region
        
        return None
    
    @property
    def is_prototype(self) -> bool:
        """Check if this is a prototype/beta version"""
        prototype_indicators = ['Beta', 'Proto', 'Prototype', 'Preview', 'Sample']
        return any(indicator in self.name for indicator in prototype_indicators)
    
    @property
    def is_demo(self) -> bool:
        """Check if this is a demo version"""
        demo_indicators = ['Demo', 'Kiosk', 'Preview']
        return any(indicator in self.name for indicator in demo_indicators)
    
    @property
    def is_pirate(self) -> bool:
        """Check if this is a pirate/unlicensed release"""
        pirate_indicators = ['Pirate', 'Unl', 'Unlicensed', 'Aftermarket', 'Bootleg']
        return any(indicator in self.name for indicator in pirate_indicators)


class DATParser:
    """Parser for No-Intro and Redump DAT files"""
    
    def __init__(self):
        self.games: List[GameEntry] = []
        self.platform: Optional[str] = None
        self.dat_type: Optional[str] = None  # 'no-intro' or 'redump'
    
    def parse_file(self, filepath: str) -> List[GameEntry]:
        """
        Parse a DAT file and extract game information
        
        Args:
            filepath: Path to DAT file
            
        Returns:
            List of GameEntry objects
        """
        logger.info(f"Parsing DAT file: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Detect DAT format
            if self._is_xml_format(content):
                return self._parse_xml_dat(content, filepath)
            else:
                return self._parse_text_dat(content, filepath)
                
        except Exception as e:
            logger.error(f"Error parsing DAT file {filepath}: {e}")
            return []
    
    def _is_xml_format(self, content: str) -> bool:
        """Check if DAT file is in XML format"""
        return content.strip().startswith('<?xml') or '<datafile>' in content[:1000]
    
    def _parse_xml_dat(self, content: str, filepath: str) -> List[GameEntry]:
        """Parse XML format DAT file (Redump/No-Intro XML)"""
        try:
            root = ET.fromstring(content)
            
            # Determine DAT type from root element
            if root.tag == 'datafile':
                self.dat_type = 'redump' if 'redump' in content.lower() else 'no-intro'
                
                # Extract header information
                header = root.find('header')
                if header is not None:
                    name_elem = header.find('name')
                    if name_elem is not None:
                        self.platform = name_elem.text
                        logger.info(f"Platform: {self.platform}")
                
                # Parse games
                self.games = []
                for game_elem in root.findall('game'):
                    game = self._parse_xml_game_element(game_elem)
                    if game:
                        self.games.append(game)
                
                logger.info(f"Parsed {len(self.games)} games from XML DAT")
                return self.games
                
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            # Fall back to text parsing
            return self._parse_text_dat(content, filepath)
        
        return []
    
    def _parse_xml_game_element(self, game_elem) -> Optional[GameEntry]:
        """Parse individual game element from XML"""
        try:
            name = game_elem.get('name', '')
            description = game_elem.findtext('description', '')
            
            # Parse ROMs
            roms = []
            for rom_elem in game_elem.findall('rom'):
                rom_name = rom_elem.get('name', '')
                rom_size = int(rom_elem.get('size', 0))
                rom_crc = rom_elem.get('crc', '').upper() or None
                rom_md5 = rom_elem.get('md5', '').lower() or None
                rom_sha1 = rom_elem.get('sha1', '').lower() or None
                rom_sha256 = rom_elem.get('sha256', '').lower() or None
                rom_serial = rom_elem.get('serial')
                
                rom = ROMInfo(
                    name=rom_name,
                    size=rom_size,
                    crc=rom_crc,
                    md5=rom_md5,
                    sha1=rom_sha1,
                    sha256=rom_sha256,
                    serial=rom_serial
                )
                roms.append(rom)
            
            # Extract additional metadata
            category = None
            publisher = None
            developer = None
            region = None
            release_date = None
            
            # Try to extract from description or other elements
            release_elem = game_elem.find('release')
            if release_elem is not None:
                region = release_elem.get('region')
                release_date = release_elem.get('date')
            
            publisher_elem = game_elem.find('publisher')
            if publisher_elem is not None:
                publisher = publisher_elem.text
            
            developer_elem = game_elem.find('developer')
            if developer_elem is not None:
                developer = developer_elem.text
            
            return GameEntry(
                name=name,
                description=description,
                roms=roms,
                category=category,
                publisher=publisher,
                developer=developer,
                region=region,
                release_date=release_date
            )
            
        except Exception as e:
            logger.error(f"Error parsing XML game element: {e}")
            return None
    
    def _parse_text_dat(self, content: str, filepath: str) -> List[GameEntry]:
        """Parse text format DAT file (ClrMamePro format)"""
        logger.info(f"Parsing text DAT file: {filepath}")
        
        # Extract platform from filename
        filename = os.path.basename(filepath)
        self.platform = filename.replace('.dat', '').replace('_', ' ')
        
        # Try to detect DAT type from content
        if 'no-intro' in content.lower():
            self.dat_type = 'no-intro'
        elif 'redump' in content.lower():
            self.dat_type = 'redump'
        else:
            self.dat_type = 'unknown'
        
        # Parse games using regex
        self.games = []
        
        # Pattern for game entries in ClrMamePro format
        # game (
        #   name "Game Title (Region)"
        #   description "Game Description"
        #   rom ( name "romfile.bin" size 123456 crc ABCD1234 md5 ... sha1 ... )
        # )
        
        # Find all game blocks
        game_pattern = r'game\s*\(\s*(.*?)\s*\)\s*(?=game\s*\(|$)'
        game_blocks = re.findall(game_pattern, content, re.DOTALL | re.IGNORECASE)
        
        logger.info(f"Found {len(game_blocks)} game blocks")
        
        for block in game_blocks:
            try:
                game = self._parse_text_game_block(block)
                if game:
                    self.games.append(game)
            except Exception as e:
                logger.warning(f"Error parsing game block: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(self.games)} games")
        return self.games
    
    def _parse_text_game_block(self, block: str) -> Optional[GameEntry]:
        """Parse individual game block from text DAT"""
        try:
            # Extract name - try name field first, then comment field
            name_match = re.search(r'name\s+"([^"]*)"', block, re.IGNORECASE)
            if not name_match:
                # Try comment field (used in metadat/publisher files)
                name_match = re.search(r'comment\s+"([^"]*)"', block, re.IGNORECASE)
                if not name_match:
                    return None
            
            name = name_match.group(1)
            
            # Extract description
            desc_match = re.search(r'description\s+"([^"]*)"', block, re.IGNORECASE)
            description = desc_match.group(1) if desc_match else name
            
            # Extract ROMs
            roms = []
            rom_pattern = r'rom\s*\(\s*(.*?)\s*\)'
            rom_blocks = re.findall(rom_pattern, block, re.DOTALL | re.IGNORECASE)
            
            for rom_block in rom_blocks:
                rom = self._parse_rom_block(rom_block)
                if rom:
                    roms.append(rom)
            
            # Extract additional metadata if available
            category = None
            publisher = None
            developer = None
            
            # Try to extract publisher
            pub_match = re.search(r'publisher\s+"([^"]*)"', block, re.IGNORECASE)
            if pub_match:
                publisher = pub_match.group(1)
            
            # Try to extract developer
            dev_match = re.search(r'developer\s+"([^"]*)"', block, re.IGNORECASE)
            if dev_match:
                developer = dev_match.group(1)
            
            return GameEntry(
                name=name,
                description=description,
                roms=roms,
                category=category,
                publisher=publisher,
                developer=developer
            )
            
        except Exception as e:
            logger.error(f"Error parsing game block: {e}")
            return None
    
    def _parse_rom_block(self, rom_block: str) -> Optional[ROMInfo]:
        """Parse ROM block from text DAT"""
        try:
            # Extract ROM name - try name field first
            name_match = re.search(r'name\s+"([^"]*)"', rom_block, re.IGNORECASE)
            if name_match:
                name = name_match.group(1)
            else:
                # If no name, generate a placeholder
                name = "unknown.bin"
            
            # Extract size
            size_match = re.search(r'size\s+(\d+)', rom_block, re.IGNORECASE)
            size = int(size_match.group(1)) if size_match else 0
            
            # Extract hashes
            crc_match = re.search(r'crc\s+([0-9A-Fa-f]+)', rom_block, re.IGNORECASE)
            crc = crc_match.group(1).upper() if crc_match else None
            
            md5_match = re.search(r'md5\s+([0-9A-Fa-f]+)', rom_block, re.IGNORECASE)
            md5 = md5_match.group(1).lower() if md5_match else None
            
            sha1_match = re.search(r'sha1\s+([0-9A-Fa-f]+)', rom_block, re.IGNORECASE)
            sha1 = sha1_match.group(1).lower() if sha1_match else None
            
            sha256_match = re.search(r'sha256\s+([0-9A-Fa-f]+)', rom_block, re.IGNORECASE)
            sha256 = sha256_match.group(1).lower() if sha256_match else None
            
            # Extract serial if available (common in Redump)
            serial_match = re.search(r'serial\s+"([^"]*)"', rom_block, re.IGNORECASE)
            serial = serial_match.group(1) if serial_match else None
            
            # For simple format like "rom ( crc ABCD1234 )", we at least need CRC
            if not crc and not md5 and not sha1:
                logger.warning(f"No hash found in ROM block: {rom_block[:50]}...")
                return None
            
            return ROMInfo(
                name=name,
                size=size,
                crc=crc,
                md5=md5,
                sha1=sha1,
                sha256=sha256,
                serial=serial
            )
            
        except Exception as e:
            logger.error(f"Error parsing ROM block: {e}")
            return None
    
    def get_unique_games(self) -> Dict[str, List[GameEntry]]:
        """
        Group games by clean title for 1G1R analysis
        
        Returns:
            Dictionary mapping clean titles to list of GameEntry objects
        """
        grouped = {}
        
        for game in self.games:
            clean_title = game.clean_title
            if clean_title not in grouped:
                grouped[clean_title] = []
            grouped[clean_title].append(game)
        
        return grouped
    
    def get_platform_info(self) -> Dict[str, str]:
        """Get platform information from parsed DAT"""
        return {
            'platform': self.platform,
            'dat_type': self.dat_type,
            'game_count': len(self.games),
            'rom_count': sum(len(game.roms) for game in self.games)
        }
    
    def export_to_csv(self, output_path: str) -> bool:
        """Export parsed games to CSV file"""
        try:
            import csv
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'title', 'clean_title', 'platform', 'region', 'publisher', 'developer',
                    'release_date', 'is_prototype', 'is_demo', 'is_pirate',
                    'rom_name', 'rom_size', 'crc', 'md5', 'sha1'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for game in self.games:
                    for rom in game.roms:
                        writer.writerow({
                            'title': game.name,
                            'clean_title': game.clean_title,
                            'platform': self.platform,
                            'region': game.extracted_region or game.region,
                            'publisher': game.publisher,
                            'developer': game.developer,
                            'release_date': game.release_date,
                            'is_prototype': game.is_prototype,
                            'is_demo': game.is_demo,
                            'is_pirate': game.is_pirate,
                            'rom_name': rom.name,
                            'rom_size': rom.size,
                            'crc': rom.crc,
                            'md5': rom.md5,
                            'sha1': rom.sha1
                        })
            
            logger.info(f"Exported {len(self.games)} games to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return False


def parse_dat_directory(directory_path: str, recursive: bool = True) -> Dict[str, List[GameEntry]]:
    """
    Parse all DAT files in a directory
    
    Args:
        directory_path: Path to directory containing DAT files
        recursive: Whether to search recursively
        
    Returns:
        Dictionary mapping platform names to list of GameEntry objects
    """
    parser = DATParser()
    results = {}
    
    try:
        if recursive:
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    if file.lower().endswith('.dat'):
                        filepath = os.path.join(root, file)
                        games = parser.parse_file(filepath)
                        if games:
                            platform = parser.platform or os.path.splitext(file)[0]
                            results[platform] = games
                            logger.info(f"Parsed {len(games)} games from {file}")
        else:
            for file in os.listdir(directory_path):
                if file.lower().endswith('.dat'):
                    filepath = os.path.join(directory_path, file)
                    games = parser.parse_file(filepath)
                    if games:
                        platform = parser.platform or os.path.splitext(file)[0]
                        results[platform] = games
                        logger.info(f"Parsed {len(games)} games from {file}")
    
    except Exception as e:
        logger.error(f"Error parsing DAT directory {directory_path}: {e}")
    
    return results


def main():
    """Command-line interface for DAT parser"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Parse No-Intro/Redump DAT files')
    parser.add_argument('input', help='DAT file or directory to parse')
    parser.add_argument('--output', '-o', help='Output CSV file path')
    parser.add_argument('--recursive', '-r', action='store_true', help='Search directories recursively')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Check if input is file or directory
    if os.path.isfile(args.input):
        dat_parser = DATParser()
        games = dat_parser.parse_file(args.input)
        
        if games:
            print(f"Parsed {len(games)} games from {args.input}")
            print(f"Platform: {dat_parser.platform}")
            print(f"Type: {dat_parser.dat_type}")
            
            # Export to CSV if output specified
            if args.output:
                success = dat_parser.export_to_csv(args.output)
                if success:
                    print(f"Exported to {args.output}")
            
            # Show sample games
            print("\nSample games:")
            for i, game in enumerate(games[:5]):
                print(f"  {i+1}. {game.name}")
                if game.roms:
                    print(f"     ROM: {game.roms[0].name} ({game.roms[0].size} bytes)")
    
    elif os.path.isdir(args.input):
        results = parse_dat_directory(args.input, args.recursive)
        
        total_games = sum(len(games) for games in results.values())
        print(f"Parsed {total_games} games from {len(results)} platforms")
        
        for platform, games in results.items():
            print(f"  {platform}: {len(games)} games")
        
        # Export all to CSV if output specified
        if args.output and results:
            try:
                import csv
                
                with open(args.output, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = [
                        'platform', 'title', 'clean_title', 'region', 'publisher', 'developer',
                        'is_prototype', 'is_demo', 'is_pirate', 'rom_count'
                    ]
                    
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for platform, games in results.items():
                        for game in games:
                            writer.writerow({
                                'platform': platform,
                                'title': game.name,
                                'clean_title': game.clean_title,
                                'region': game.extracted_region or game.region,
                                'publisher': game.publisher,
                                'developer': game.developer,
                                'is_prototype': game.is_prototype,
                                'is_demo': game.is_demo,
                                'is_pirate': game.is_pirate,
                                'rom_count': len(game.roms)
                            })
                
                print(f"Exported summary to {args.output}")
                
            except Exception as e:
                print(f"Error exporting to CSV: {e}")
    
    else:
        print(f"Error: {args.input} is not a valid file or directory")


if __name__ == '__main__':
    main()
