"""
Enhanced series and volume matching for AudioStacker
"""

import re
from decimal import Decimal
from typing import Optional, List, Dict, Tuple
from difflib import SequenceMatcher

class SeriesVolumeAnalyzer:
    """Analyze series and detect missing volumes, duplicates, etc."""
    
    def __init__(self):
        # Enhanced volume patterns
        self.volume_patterns = [
            r'vol\.?\s*(\d+(?:\.\d+)?)',                    # Vol. 19, Vol 19.5
            r'volume\s*(\d+(?:\.\d+)?)',                    # Volume 19
            r'book\s*(\d+(?:\.\d+)?)',                      # Book 19
            r'(?:^|\W)(\d+(?:\.\d+)?)\s*\(light novel\)',  # 19 (Light Novel)
            r'(?:^|\W)(\d+(?:\.\d+)?)\s*\(ln\)',           # 19 (LN)
            r',\s*vol\.?\s*(\d+(?:\.\d+)?)',               # , Vol. 19
            r':\s*volume\s*(\d+(?:\.\d+)?)',               # : Volume 19
            r'\s+(\d+(?:\.\d+)?)$',                        # " 19" at end
            r'(?:^|\W)vol\.?\s*(\d+(?:\.\d+)?)\s*\(light novel\)', # Vol. 5 (Light Novel)
            r',\s*vol\.?\s*(\d+(?:\.\d+)?)\s*\(light novel\)', # , Vol. 5 (Light Novel)
            r'(?<=\s)(\d+)(?=\s|$)',                       # Extract standalone numbers like "Sword Art Online 15"
            r'(?<![a-zA-Z])(\d+)(?![a-zA-Z])',             # Extract numeric part from titles
            r'(\d+)(?:\.\d+)?(?=:)',                       # Numbers before colon: "Vol 10: Gamble Scramble!"
            r'(?:\s|^)(\d+)(?:\s|$)',                      # Standalone number in the title
            r'(\d+(?:\.\d+)?)\s*$',                        # "19" at very end
            r'part\s*(\d+)',                               # "Part 1", "Part 2"
            r'season\s*(\d+)',                             # "Season 1", "Season 2"
            r'act\s*(\d+)',                                # "Act 1", "Act 2"
            r'arc\s*(\d+)',                                # "Arc 1", "Arc 2"
        ]
        
        # Special volume title mapping for titles without numeric identifiers
        self.special_title_volume_map = {
            "prologue": 0,
            "prequel": 0,
            "interlude": 0.5,
            "epilogue": 9999,  # High number to indicate end of series
            "a journey of black and white": 9,  # Example of explicit mapping
            "a journey of two lifetimes": 10,   # Example of explicit mapping
            "axis church vs. eris church": 8,   # Example for Konosuba
        }
        
        # Series name aliases for normalized comparison
        self.series_aliases = {
            "my happy marriage": "my happy marriage",
            "that time i got reincarnated as a slime": "tensei shitara slime datta ken",
            "tensei shitara slime datta ken": "that time i got reincarnated as a slime",
            "in another world with my smartphone": "in another world with my smartphone",
            "in another world with my smartphone series": "in another world with my smartphone",
            "rascal does not dream": "rascal does not dream",
            "rascal does not dream of": "rascal does not dream",
            "konosuba": "konosuba gods blessing on this wonderful world",
            "konosuba gods blessing on this wonderful world": "konosuba",
            "gods blessing on this wonderful world": "konosuba",
            "mushoku tensei jobless reincarnation": "mushoku tensei",
            "mushoku tensei": "mushoku tensei jobless reincarnation",
            "jobless reincarnation": "mushoku tensei",
            "sword art online": "sao",
            "sao": "sword art online",
            "sao progressive": "sword art online progressive",
            "sword art online progressive": "sao progressive",
            "spice and wolf": "spice & wolf",
            "spice & wolf": "spice and wolf",
            "goblin slayer": "goblin slayer",
            "reborn as a vending machine": "reborn as a vending machine i now wander the dungeon",
            "reborn as a vending machine i now wander the dungeon": "reborn as a vending machine",
            "overlord": "overlord",
            "dragon and ceremony": "the dragon and the ceremony", 
            "the dragon and the ceremony": "dragon and ceremony",
            "isekai medical": "isekai medical",
            "isekai pharmacy": "isekai medical",
            "reincarnated as the piggy duke": "reincarnated as the piggy duke this time im gonna tell her how i feel",
            "reincarnated as the piggy duke this time im gonna tell her how i feel": "reincarnated as the piggy duke",
            # Add more mappings as needed
        }
    
    def extract_volume_number(self, title: str) -> Optional[Decimal]:
        """Extract volume number from title with enhanced patterns"""
        if not title:
            return None
        
        title_lower = title.lower().strip()
        
        # Check for special title mappings first
        for special_title, volume_number in self.special_title_volume_map.items():
            if special_title in title_lower:
                return Decimal(str(volume_number))
        
        for pattern in self.volume_patterns:
            match = re.search(pattern, title_lower)
            if match:
                try:
                    return Decimal(match.group(1))
                except (ValueError, TypeError):
                    continue
        
        # Named volume detection for cases without numeric indicators
        if " final " in title_lower or " finale " in title_lower:
            # Try to estimate a high number for final volumes
            return Decimal("9999")
        
        return None
    
    def analyze_series_volumes(self, books: List[Dict]) -> Dict:
        """
        Analyze a series to find gaps, duplicates, and inconsistencies
        
        Args:
            books: List of book dictionaries with title, series, etc.
            
        Returns:
            Analysis results including gaps, duplicates, etc.
        """
        volume_info = []
        
        for book in books:
            volume = self.extract_volume_number(book.get('title', ''))
            if volume is not None:
                volume_info.append({
                    'volume': float(volume),
                    'book': book,
                    'title': book.get('title', ''),
                    'asin': book.get('asin', ''),
                    'release_date': book.get('release_date', '')
                })
        
        # Sort by volume number
        volume_info.sort(key=lambda x: x['volume'])
        
        # Find gaps
        volumes = [info['volume'] for info in volume_info]
        gaps = []
        if volumes:
            min_vol = int(min(volumes))
            max_vol = int(max(volumes))
            
            for i in range(min_vol + 1, max_vol):
                if i not in volumes:
                    gaps.append(i)
        
        # Find duplicates
        volume_counts = {}
        for info in volume_info:
            vol = info['volume']
            if vol not in volume_counts:
                volume_counts[vol] = []
            volume_counts[vol].append(info)
        
        duplicates = {vol: infos for vol, infos in volume_counts.items() if len(infos) > 1}
        
        return {
            'total_volumes': len(volume_info),
            'volume_range': (min(volumes), max(volumes)) if volumes else (None, None),
            'gaps': gaps,
            'duplicates': duplicates,
            'volumes': volume_info
        }
    
    def normalize_series_name(self, series_name: str) -> str:
        """Normalize series name for better matching"""
        if not series_name:
            return ""
        
        # Convert to lowercase and remove extra whitespace
        normalized = series_name.lower().strip()
        
        # Remove common suffixes that might vary
        suffixes_to_remove = [
            r'\s*series\s*$',
            r'\s*\(light novel\)\s*$',
            r'\s*\(ln\)\s*$',
            r'\s*light novel\s*$',
            r'\s*audiobook\s*$',
            r'\s*\(audiobook\)\s*$',
            r'\s*\(series\)\s*$',
            r'\s*novels?\s*$',
            r'\s*\(novels?\)\s*$',
            r'\s*\(complete\)\s*$',
            r'\s*\(unabridged\)\s*$',
            r'\s*manga\s*$',
            r'\s*\(manga\)\s*$',
        ]
        
        for suffix in suffixes_to_remove:
            normalized = re.sub(suffix, '', normalized, flags=re.IGNORECASE)
        
        # Normalize punctuation
        normalized = re.sub(r'[:\-_]+', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Check for aliases
        if normalized in self.series_aliases:
            normalized = self.series_aliases[normalized]
        
        return normalized.strip()
    
    def series_similarity(self, series1: str, series2: str) -> float:
        """Calculate similarity between two series names"""
        if not series1 or not series2:
            return 0.0
        
        norm1 = self.normalize_series_name(series1)
        norm2 = self.normalize_series_name(series2)
        
        if norm1 == norm2:
            return 1.0
        
        return SequenceMatcher(None, norm1, norm2).ratio()


# Global instance
series_analyzer = SeriesVolumeAnalyzer()

def extract_volume_number(title: str) -> Optional[Decimal]:
    """Extract volume number from title"""
    return series_analyzer.extract_volume_number(title)

def analyze_series(books: List[Dict]) -> Dict:
    """Analyze series for gaps and duplicates"""
    return series_analyzer.analyze_series_volumes(books)

def normalize_series_name(series: str) -> str:
    """Normalize series name"""
    return series_analyzer.normalize_series_name(series)
