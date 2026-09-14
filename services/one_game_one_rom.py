"""
1G1R (One Game One ROM) Filtering Logic
Prioritizes the best version of each game when multiple versions exist
"""

import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import logging
from services.dat_parser import GameEntry

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RegionPriority(Enum):
    """Region priority for 1G1R selection"""
    USA = 1
    WORLD = 2
    EUROPE = 3
    JAPAN = 4
    ASIA = 5
    AUSTRALIA = 6
    BRAZIL = 7
    KOREA = 8
    CHINA = 9
    OTHER = 10
    DEMO = 20
    BETA = 30
    PIRATE = 40


class VersionType(Enum):
    """Type of game version"""
    RETAIL = 1
    REVISION = 2
    BETA = 3
    PROTOTYPE = 4
    DEMO = 5
    SAMPLE = 6
    PIRATE = 7
    HACK = 8
    TRANSLATION = 9


@dataclass
class GameVersion:
    """Represents a version of a game for 1G1R analysis"""
    game_entry: GameEntry
    region_priority: RegionPriority
    version_type: VersionType
    revision_number: Optional[int] = None
    is_enhanced: bool = False  # Enhanced/updated version
    is_best_version: bool = False  # Best version for this region
    score: float = 0.0  # Overall score for ranking
    
    @property
    def title(self) -> str:
        return self.game_entry.name
    
    @property
    def clean_title(self) -> str:
        return self.game_entry.clean_title
    
    @property
    def region(self) -> Optional[str]:
        return self.game_entry.extracted_region
    
    @property
    def is_prototype(self) -> bool:
        return self.game_entry.is_prototype
    
    @property
    def is_demo(self) -> bool:
        return self.game_entry.is_demo
    
    @property
    def is_pirate(self) -> bool:
        return self.game_entry.is_pirate


class OneGameOneRomFilter:
    """1G1R filtering logic"""
    
    # Region mapping for priority
    REGION_PRIORITY_MAP = {
        'USA': RegionPriority.USA,
        'US': RegionPriority.USA,
        'United States': RegionPriority.USA,
        'America': RegionPriority.USA,
        
        'World': RegionPriority.WORLD,
        'Worldwide': RegionPriority.WORLD,
        
        'Europe': RegionPriority.EUROPE,
        'EU': RegionPriority.EUROPE,
        'PAL': RegionPriority.EUROPE,
        'UK': RegionPriority.EUROPE,
        'United Kingdom': RegionPriority.EUROPE,
        'Germany': RegionPriority.EUROPE,
        'France': RegionPriority.EUROPE,
        'Italy': RegionPriority.EUROPE,
        'Spain': RegionPriority.EUROPE,
        
        'Japan': RegionPriority.JAPAN,
        'JP': RegionPriority.JAPAN,
        'JPN': RegionPriority.JAPAN,
        
        'Asia': RegionPriority.ASIA,
        'Taiwan': RegionPriority.ASIA,
        'Hong Kong': RegionPriority.ASIA,
        
        'Australia': RegionPriority.AUSTRALIA,
        'AU': RegionPriority.AUSTRALIA,
        
        'Brazil': RegionPriority.BRAZIL,
        'BR': RegionPriority.BRAZIL,
        
        'Korea': RegionPriority.KOREA,
        'KR': RegionPriority.KOREA,
        
        'China': RegionPriority.CHINA,
        'CN': RegionPriority.CHINA,
        
        'Demo': RegionPriority.DEMO,
        'Beta': RegionPriority.BETA,
        'Pirate': RegionPriority.PIRATE,
    }
    
    # Version type detection patterns
    VERSION_PATTERNS = {
        VersionType.RETAIL: [],
        VersionType.REVISION: [r'\(Rev \d+\)', r'\(Version \d+\)', r'\(v\d+\.\d+\)', r'\(Revision \d+\)'],
        VersionType.BETA: [r'\(Beta\)', r'\(Prototype\)', r'\(Proto\)'],
        VersionType.PROTOTYPE: [r'\(Prototype\)', r'\(Proto \d+\)'],
        VersionType.DEMO: [r'\(Demo\)', r'\(Kiosk\)', r'\(Sample\)', r'\(Preview\)'],
        VersionType.SAMPLE: [r'\(Sample\)'],
        VersionType.PIRATE: [r'\(Pirate\)', r'\(Unl\)', r'\(Unlicensed\)', r'\(Aftermarket\)', r'\(Bootleg\)'],
        VersionType.HACK: [r'\(Hack\)', r'\(Translation\)', r'\(Mod\)'],
        VersionType.TRANSLATION: [r'\(Translation\)', r'\(Translated\)'],
    }
    
    def __init__(self, prefer_usa: bool = True, prefer_english: bool = True, 
                 exclude_prototypes: bool = True, exclude_demos: bool = True,
                 exclude_pirates: bool = True):
        """
        Initialize 1G1R filter
        
        Args:
            prefer_usa: Prefer USA region versions
            prefer_english: Prefer English language versions
            exclude_prototypes: Exclude prototype/beta versions
            exclude_demos: Exclude demo versions
            exclude_pirates: Exclude pirate/unlicensed versions
        """
        self.prefer_usa = prefer_usa
        self.prefer_english = prefer_english
        self.exclude_prototypes = exclude_prototypes
        self.exclude_demos = exclude_demos
        self.exclude_pirates = exclude_pirates
        
    def filter_games(self, games: List[GameEntry]) -> List[GameEntry]:
        """
        Apply 1G1R filtering to a list of games
        
        Args:
            games: List of GameEntry objects
            
        Returns:
            Filtered list with one version per game
        """
        if not games:
            return []
        
        # Group games by clean title
        grouped = self._group_by_clean_title(games)
        
        # Filter each group
        filtered_games = []
        for clean_title, game_list in grouped.items():
            selected = self._select_best_version(game_list)
            if selected:
                filtered_games.append(selected)
        
        logger.info(f"1G1R filtering: {len(games)} -> {len(filtered_games)} games")
        return filtered_games
    
    def _group_by_clean_title(self, games: List[GameEntry]) -> Dict[str, List[GameEntry]]:
        """Group games by clean title"""
        grouped = {}
        
        for game in games:
            clean_title = game.clean_title
            if clean_title not in grouped:
                grouped[clean_title] = []
            grouped[clean_title].append(game)
        
        return grouped
    
    def _select_best_version(self, games: List[GameEntry]) -> Optional[GameEntry]:
        """
        Select the best version from a list of same-game variants
        
        Args:
            games: List of GameEntry objects for the same game
            
        Returns:
            Best GameEntry or None if all filtered out
        """
        if not games:
            return None
        
        # If only one version, return it (if not excluded)
        if len(games) == 1:
            game = games[0]
            if self._should_exclude(game):
                return None
            return game
        
        # Convert to GameVersion objects for analysis
        game_versions = [self._create_game_version(game) for game in games]
        
        # Filter out excluded versions
        filtered_versions = [v for v in game_versions if not self._should_exclude(v.game_entry)]
        
        if not filtered_versions:
            return None
        
        # Score each version
        scored_versions = []
        for version in filtered_versions:
            score = self._calculate_version_score(version)
            version.score = score
            scored_versions.append(version)
        
        # Sort by score (descending)
        scored_versions.sort(key=lambda v: v.score, reverse=True)
        
        # Select best version
        best_version = scored_versions[0]
        best_version.is_best_version = True
        
        logger.debug(f"Selected '{best_version.title}' (score: {best_version.score:.2f}) "
                    f"from {len(games)} versions")
        
        return best_version.game_entry
    
    def _create_game_version(self, game: GameEntry) -> GameVersion:
        """Create GameVersion from GameEntry"""
        # Determine region priority
        region_priority = self._determine_region_priority(game)
        
        # Determine version type
        version_type = self._determine_version_type(game)
        
        # Extract revision number if available
        revision_number = self._extract_revision_number(game)
        
        # Check if enhanced version
        is_enhanced = self._is_enhanced_version(game)
        
        return GameVersion(
            game_entry=game,
            region_priority=region_priority,
            version_type=version_type,
            revision_number=revision_number,
            is_enhanced=is_enhanced
        )
    
    def _determine_region_priority(self, game: GameEntry) -> RegionPriority:
        """Determine region priority for a game"""
        region = game.extracted_region
        
        if not region:
            # Try to extract from name
            for region_name, priority in self.REGION_PRIORITY_MAP.items():
                if region_name.lower() in game.name.lower():
                    return priority
        
        # Map region to priority
        for region_name, priority in self.REGION_PRIORITY_MAP.items():
            if region and region_name.lower() in region.lower():
                return priority
        
        # Check for demo/beta/pirate
        if game.is_demo:
            return RegionPriority.DEMO
        elif game.is_prototype:
            return RegionPriority.BETA
        elif game.is_pirate:
            return RegionPriority.PIRATE
        
        return RegionPriority.OTHER
    
    def _determine_version_type(self, game: GameEntry) -> VersionType:
        """Determine version type for a game"""
        name_lower = game.name.lower()
        
        # Check each version type pattern
        for version_type, patterns in self.VERSION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, game.name, re.IGNORECASE):
                    return version_type
        
        # Check for demo/prototype/pirate flags
        if game.is_demo:
            return VersionType.DEMO
        elif game.is_prototype:
            return VersionType.BETA
        elif game.is_pirate:
            return VersionType.PIRATE
        
        # Default to retail
        return VersionType.RETAIL
    
    def _extract_revision_number(self, game: GameEntry) -> Optional[int]:
        """Extract revision number from game name"""
        # Patterns: (Rev 1), (Revision 2), (v1.1), (Version 3)
        patterns = [
            r'\(Rev\s*(\d+)\)',
            r'\(Revision\s*(\d+)\)',
            r'\(v\d+\.(\d+)\)',
            r'\(Version\s*(\d+)\)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, game.name, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _is_enhanced_version(self, game: GameEntry) -> bool:
        """Check if this is an enhanced/updated version"""
        enhanced_indicators = [
            'Enhanced', 'Updated', 'Plus', '+', 'Deluxe', 'Special',
            'Director\'s Cut', 'Gold', 'Platinum', 'Greatest Hits',
            'Player\'s Choice', 'Classics', 'Best'
        ]
        
        name_lower = game.name.lower()
        return any(indicator.lower() in name_lower for indicator in enhanced_indicators)
    
    def _should_exclude(self, game: GameEntry) -> bool:
        """Check if a game should be excluded based on filters"""
        if self.exclude_prototypes and game.is_prototype:
            return True
        
        if self.exclude_demos and game.is_demo:
            return True
        
        if self.exclude_pirates and game.is_pirate:
            return True
        
        return False
    
    def _calculate_version_score(self, version: GameVersion) -> float:
        """Calculate score for a game version (higher is better)"""
        score = 0.0
        
        # Base score based on version type
        version_scores = {
            VersionType.RETAIL: 100,
            VersionType.REVISION: 90,
            VersionType.TRANSLATION: 80,
            VersionType.HACK: 70,
            VersionType.DEMO: 30,
            VersionType.SAMPLE: 20,
            VersionType.BETA: 10,
            VersionType.PROTOTYPE: 5,
            VersionType.PIRATE: 0,
        }
        
        base_score = version_scores.get(version.version_type, 50)
        score += base_score
        
        # Bonus for enhanced versions (handled separately since not a VersionType)
        if version.is_enhanced:
            score += 10
        
        # Region priority (lower number = higher priority)
        region_score = 50 - (version.region_priority.value * 2)
        score += region_score
        
        # Bonus for USA region if preferred
        if self.prefer_usa and version.region_priority == RegionPriority.USA:
            score += 20
        
        # Bonus for English language if preferred
        if self.prefer_english and self._is_english_version(version.game_entry):
            score += 15
        
        # Bonus for higher revision number
        if version.revision_number:
            score += min(version.revision_number * 2, 20)  # Max 20 bonus
        
        # Bonus for enhanced versions
        if version.is_enhanced:
            score += 10
        
        # Penalty for non-retail versions
        if version.version_type != VersionType.RETAIL:
            score -= 10
        
        return max(0.0, score)
    
    def _is_english_version(self, game: GameEntry) -> bool:
        """Check if game is likely English version"""
        name_lower = game.name.lower()
        
        # English indicators
        english_indicators = ['(en)', '(english)', '(usa)', '(us)', '(uk)', '(pal)']
        
        # Check for English language tags
        for indicator in english_indicators:
            if indicator in name_lower:
                return True
        
        # Check region
        region = game.extracted_region
        if region and region.upper() in ['USA', 'US', 'UK', 'EUROPE', 'AUSTRALIA']:
            return True
        
        # Check if name contains non-English characters (simple check)
        non_english_pattern = r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef]'
        if re.search(non_english_pattern, game.name):
            return False
        
        return True  # Assume English by default
    
    def analyze_game_group(self, games: List[GameEntry]) -> Dict:
        """
        Analyze a group of same-game variants
        
        Args:
            games: List of GameEntry objects for the same game
            
        Returns:
            Analysis dictionary with statistics
        """
        if not games:
            return {}
        
        game_versions = [self._create_game_version(game) for game in games]
        
        # Count by region
        region_counts = {}
        for version in game_versions:
            region = str(version.region_priority)
            region_counts[region] = region_counts.get(region, 0) + 1
        
        # Count by version type
        version_counts = {}
        for version in game_versions:
            vtype = str(version.version_type)
            version_counts[vtype] = version_counts.get(vtype, 0) + 1
        
        # Score all versions
        scored_versions = []
        for version in game_versions:
            score = self._calculate_version_score(version)
            version.score = score
            scored_versions.append(version)
        
        # Sort by score
        scored_versions.sort(key=lambda v: v.score, reverse=True)
        
        # Get best version
        best_version = scored_versions[0] if scored_versions else None
        
        return {
            'total_versions': len(games),
            'clean_title': games[0].clean_title if games else '',
            'region_counts': region_counts,
            'version_counts': version_counts,
            'best_version': {
                'title': best_version.title if best_version else None,
                'region': best_version.region,
                'version_type': str(best_version.version_type) if best_version else None,
                'score': best_version.score if best_version else 0
            },
            'all_versions': [
                {
                    'title': v.title,
                    'region': v.region,
                    'version_type': str(v.version_type),
                    'score': v.score
                }
                for v in scored_versions
            ]
        }


def apply_1g1r_to_dat_files(dat_files_results: Dict[str, List[GameEntry]],
                           filter_options: Dict = None) -> Dict[str, List[GameEntry]]:
    """
    Apply 1G1R filtering to DAT file parsing results
    
    Args:
        dat_files_results: Dictionary mapping platform names to list of GameEntry objects
        filter_options: Optional dictionary of filter options
        
    Returns:
        Filtered dictionary with one version per game per platform
    """
    if filter_options is None:
        filter_options = {}
    
    # Create filter with options
    filter_instance = OneGameOneRomFilter(
        prefer_usa=filter_options.get('prefer_usa', True),
        prefer_english=filter_options.get('prefer_english', True),
        exclude_prototypes=filter_options.get('exclude_prototypes', True),
        exclude_demos=filter_options.get('exclude_demos', True),
        exclude_pirates=filter_options.get('exclude_pirates', True)
    )
    
    filtered_results = {}
    
    for platform, games in dat_files_results.items():
        filtered_games = filter_instance.filter_games(games)
        if filtered_games:
            filtered_results[platform] = filtered_games
    
    return filtered_results


def main():
    """Command-line interface for 1G1R filtering"""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='1G1R (One Game One ROM) Filtering')
    parser.add_argument('input', help='Input JSON file with game data')
    parser.add_argument('--output', '-o', help='Output JSON file for filtered results')
    parser.add_argument('--no-usa', action='store_true', help='Don\'t prefer USA region')
    parser.add_argument('--include-prototypes', action='store_true', help='Include prototype versions')
    parser.add_argument('--include-demos', action='store_true', help='Include demo versions')
    parser.add_argument('--include-pirates', action='store_true', help='Include pirate versions')
    parser.add_argument('--analyze', action='store_true', help='Show analysis instead of filtering')
    
    args = parser.parse_args()
    
    try:
        # Load game data
        with open(args.input, 'r') as f:
            data = json.load(f)
        
        # Convert to GameEntry objects (simplified for example)
        # In real usage, you'd have proper serialization
        games = []
        for item in data:
            # This is simplified - you'd need proper GameEntry creation
            pass
        
        if args.analyze:
            # Analyze without filtering
            filter_instance = OneGameOneRomFilter(
                prefer_usa=not args.no_usa,
                exclude_prototypes=not args.include_prototypes,
                exclude_demos=not args.include_demos,
                exclude_pirates=not args.include_pirates
            )
            
            # Group by clean title
            from collections import defaultdict
            grouped = defaultdict(list)
            for game in games:
                grouped[game.clean_title].append(game)
            
            # Analyze each group
            analyses = []
            for clean_title, game_list in grouped.items():
                if len(game_list) > 1:
                    analysis = filter_instance.analyze_game_group(game_list)
                    analyses.append(analysis)
            
            print(f"Found {len(analyses)} games with multiple versions")
            for analysis in analyses[:10]:  # Show first 10
                print(f"\n{analysis['clean_title']}: {analysis['total_versions']} versions")
                print(f"  Best: {analysis['best_version']['title']} (score: {analysis['best_version']['score']:.1f})")
                print(f"  Regions: {analysis['region_counts']}")
            
        else:
            # Apply filtering
            filtered_games = apply_1g1r_to_dat_files(
                {'all': games},
                {
                    'prefer_usa': not args.no_usa,
                    'exclude_prototypes': not args.include_prototypes,
                    'exclude_demos': not args.include_demos,
                    'exclude_pirates': not args.include_pirates
                }
            )
            
            filtered_list = filtered_games.get('all', [])
            print(f"Filtered: {len(games)} -> {len(filtered_list)} games")
            
            if args.output:
                # Save filtered results
                output_data = [game.__dict__ for game in filtered_list]
                with open(args.output, 'w') as f:
                    json.dump(output_data, f, indent=2)
                print(f"Saved to {args.output}")
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    main()