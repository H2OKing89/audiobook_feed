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
        """Initialize the analyzer with volume patterns and special mappings"""
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
            r'chapter\s*(\d+)',                            # "Chapter 1", "Chapter 2"
            r'-\s*(\d+)(?:\s|$)',                          # "MyTitle - 3" pattern
            r'\[(\d+(?:\.\d+)?)\]',                        # [3] or [3.5] pattern
            r'\((\d+(?:\.\d+)?)\)',                        # (3) or (3.5) pattern (careful with this one)
            r'#(\d+(?:\.\d+)?)',                           # #3 or #3.5 pattern
        ]
        
        # Special volume title mapping for titles without numeric identifiers
        self.special_title_volume_map = {
            "prologue": 0,
            "prequel": 0,
            "interlude": 0.5,
            "epilogue": 9999,  # High number to indicate end of series
            "finale": 9999,    # High number to indicate end of series
            "final": 9999,     # High number to indicate end of series
            "a journey of black and white": 9,  # Example of explicit mapping for Konosuba
            "a journey of two lifetimes": 10,   # Example for Konosuba
            "axis church vs. eris church": 8,   # Example for Konosuba
            "first day": 1,                     # For Re:Zero
            "second day": 2,                    # For Re:Zero
            "third day": 3,                     # For Re:Zero
            "fourth day": 4,                    # For Re:Zero
            "zero": 0,                          # Common pattern for prequels
            "genesis": 0,                       # Common pattern for first volumes or prequels
            "origins": 0,                       # Common pattern for first volumes or prequels
            "beginning": 0,                     # Common pattern for first volumes
            "homecoming": 9998,                 # Often used for late/final volumes
            "the beginning": 0,                 # Common pattern for first volumes
            "the end": 9999,                    # Common pattern for final volumes
            "short stories": 0.5,               # Often between major volumes
            "side stories": 0.5,                # Often between major volumes
            "first steps": 1,                   # Usually first volume
            "maiden flight": 1,                 # Usually first volume
            "origin story": 0,                  # Common pattern for prequels
            "origin stories": 0,                # Common pattern for prequels
            "anniversary": 9997,                # Special volumes often released after main series
            "collector's edition": 9996,        # Special editions 
            "omnibus": 8888,                    # Collection volumes
            "box set": 8889,                    # Box sets
            "complete collection": 8890,        # Complete collections
            "first season": 1,                  # Season-based naming scheme
            "second season": 2,                 # Season-based naming scheme
            "third season": 3,                  # Season-based naming scheme
            "fourth season": 4,                 # Season-based naming scheme
            "fifth season": 5,                  # Season-based naming scheme
            "special edition": 9995,            # Special editions
            "extras": 0.75,                     # Bonus content
            "bonus": 0.75,                      # Bonus content
            "gaiden": 0.8,                      # Japanese term for side story
            "chapter one": 1,                   # Chapter-based naming scheme
            "chapter two": 2,                   # Chapter-based naming scheme  
            "chapter three": 3,                 # Chapter-based naming scheme
            "chapter four": 4,                  # Chapter-based naming scheme
            "first arc": 1,                     # Arc-based naming scheme
            "second arc": 2,                    # Arc-based naming scheme
            "third arc": 3,                     # Arc-based naming scheme
            "fourth arc": 4,                    # Arc-based naming scheme
        }
        
        # Initialize series aliases
        self.initialize_series_aliases()

    def initialize_series_aliases(self):
        """Initialize the series aliases dictionary with common mappings"""
        self.series_aliases = {
            # Japanese light novels
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
            
            # Monogatari series
            "monogatari": "monogatari series",
            "monogatari series": "monogatari",
            "bakemonogatari": "monogatari series",
            "nisemonogatari": "monogatari series",
            "nekomonogatari": "monogatari series",
            "tsukimonogatari": "monogatari series",
            "owarimonogatari": "monogatari series",
            "kizumonogatari": "monogatari series",
            "kabukimonogatari": "monogatari series",
            "hanamonogatari": "monogatari series",
            "otorimonogatari": "monogatari series",
            "onimonogatari": "monogatari series",
            "koyomimonogatari": "monogatari series",
            "zokuowarimonogatari": "monogatari series",
            
            # Re:Zero
            "rezero": "re zero starting life in another world",
            "re zero": "re zero starting life in another world",
            "re:zero": "re zero starting life in another world",
            "re zero starting life in another world": "re zero",
            
            # Danmachi
            "is it wrong to try to pick up girls in a dungeon": "danmachi",
            "dungeon": "danmachi",
            "danmachi": "is it wrong to try to pick up girls in a dungeon",
            
            # Saga of Tanya the Evil
            "saga of tanya the evil": "youjo senki",
            "youjo senki": "saga of tanya the evil",
            
            # Ascendance of a Bookworm
            "ascendance of a bookworm": "honzuki no gekokujou",
            "honzuki no gekokujou": "ascendance of a bookworm",
            
            # Classroom of the Elite
            "classroom of the elite": "youjitsu",
            "youjitsu": "classroom of the elite",
            
            # More light novels/web novel series
            "death march to the parallel world rhapsody": "death march",
            "death march": "death march to the parallel world rhapsody",
            "the eminence in shadow": "kage no jitsuryokusha ni naritakute",
            "kage no jitsuryokusha ni naritakute": "the eminence in shadow",
            "my youth romantic comedy is wrong as i expected": "oregairu",
            "oregairu": "my youth romantic comedy is wrong as i expected",
            "86": "eighty-six",
            "eighty-six": "86",
            "reincarnated as a sword": "tensei shitara ken deshita",
            "tensei shitara ken deshita": "reincarnated as a sword",
            "arifureta": "arifureta shokugyou de sekai saikyou",
            "arifureta shokugyou de sekai saikyou": "arifureta from commonplace to worlds strongest",
            "arifureta from commonplace to worlds strongest": "arifureta",
            "the rising of the shield hero": "tate no yuusha no nariagari",
            "tate no yuusha no nariagari": "the rising of the shield hero",
            "so im a spider so what": "kumo desu ga nani ka",
            "kumo desu ga nani ka": "so im a spider so what",
            "torture princess": "torture princess fremd torturchen",
            "torture princess fremd torturchen": "torture princess",
            "my happy marriage": "watashi no shiawase na kekkon",
            "watashi no shiawase na kekkon": "my happy marriage",
            "the alchemist who survived now dreams of a quiet city life": "ikinokori renkinjutsushi",
            "ikinokori renkinjutsushi": "the alchemist who survived now dreams of a quiet city life",
        }

    def enhance_special_title_mappings(self):
        """Add additional special title mappings for better volume identification."""
        # Additional common volume naming patterns
        additional_mappings = {
            "homecoming": 9998,                 # Often used for late/final volumes
            "the beginning": 0,                 # Common pattern for first volumes
            "the end": 9999,                    # Common pattern for final volumes
            "short stories": 0.5,               # Often between major volumes
            "side stories": 0.5,                # Often between major volumes
            "first steps": 1,                   # Usually first volume
            "maiden flight": 1,                 # Usually first volume
            "origin story": 0,                  # Common pattern for prequels
            "origin stories": 0,                # Common pattern for prequels
            "anniversary": 9997,                # Special volumes often released after main series
            "collector's edition": 9996,        # Special editions 
            "omnibus": 8888,                    # Collection volumes
            "box set": 8889,                    # Box sets
            "complete collection": 8890,        # Complete collections
            "first season": 1,                  # Season-based naming scheme
            "second season": 2,                 # Season-based naming scheme
            "third season": 3,                  # Season-based naming scheme
            "fourth season": 4,                 # Season-based naming scheme
            "fifth season": 5,                  # Season-based naming scheme
            "special edition": 9995,            # Special editions
            "extras": 0.75,                     # Bonus content
            "bonus": 0.75,                      # Bonus content
            "gaiden": 0.8,                      # Japanese term for side story
            "chapter one": 1,                   # Chapter-based naming scheme
            "chapter two": 2,                   # Chapter-based naming scheme  
            "chapter three": 3,                 # Chapter-based naming scheme
            "chapter four": 4,                  # Chapter-based naming scheme
            "first arc": 1,                     # Arc-based naming scheme
            "second arc": 2,                    # Arc-based naming scheme
            "third arc": 3,                     # Arc-based naming scheme
            "fourth arc": 4,                    # Arc-based naming scheme
        }
        
        # Add to the existing mappings
        for title, volume in additional_mappings.items():
            if title not in self.special_title_volume_map:
                self.special_title_volume_map[title] = volume

    def extract_volume_number(self, title: str) -> Optional[float]:
        """
        Extract volume number from title with enhanced pattern matching
        Returns None if no volume number found
        """
        if not title:
            return None
            
        # Convert to lowercase for consistent matching
        title_lower = title.lower()
        
        # First check special title mapping
        for special_title, volume_number in self.special_title_volume_map.items():
            if special_title in title_lower:
                return float(volume_number)
        
        # Then try regex patterns
        for pattern in self.volume_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                try:
                    # Convert to float for consistent comparison
                    return float(match.group(1))
                except (ValueError, IndexError):
                    continue
                    
        return None
    
    def normalize_series_name(self, series_name: str) -> str:
        """
        Normalize series name for consistent comparison
        Handles common variants, suffixes, and punctuation
        """
        if not series_name:
            return ""
        
        # Convert to lowercase
        series_name = series_name.lower().strip()
        
        # Remove common punctuation
        series_name = re.sub(r'[.,;:\-_()]', ' ', series_name)
        series_name = re.sub(r'\s+', ' ', series_name)
        
        # Remove common suffixes
        suffixes = [
            r'\s*series\s*$',
            r'\s*\(light novel\)\s*$',
            r'\s*\(ln\)\s*$',
            r'\s*light novel\s*$',
            r'\s*light novels\s*$',
            r'\s*novel\s*$',
            r'\s*novels\s*$',
            r'\s*manga\s*$',
            r'\s*anime\s*$',
            r'\s*the animation\s*$',
            r'\s*audiobook\s*$',
            r'\s*boxset\s*$',
            r'\s*box set\s*$',
            r'\s*collection\s*$',
            r'\s*the complete series\s*$',
        ]
        
        for suffix in suffixes:
            series_name = re.sub(suffix, '', series_name, flags=re.IGNORECASE)
        
        # Look for series name aliases
        if series_name in self.series_aliases:
            return self.series_aliases[series_name]
            
        return series_name.strip()
    
    def detect_missing_volumes(self, volumes: List[float]) -> List[float]:
        """
        Detect missing volumes in a series
        Returns list of missing volume numbers
        """
        if not volumes:
            return []
            
        # Sort volumes
        volumes = sorted(volumes)
        
        # Skip if no clear sequence (e.g. only one volume or gaps too large)
        if len(volumes) <= 1:
            return []
            
        # Find regular numbered volumes (exclude special volumes like 0, 9999, etc.)
        regular_volumes = [v for v in volumes if 0.1 <= v <= 100]
        
        if len(regular_volumes) <= 1:
            return []
            
        # Detect missing
        missing = []
        
        # Check for common patterns (1,2,4,5) - missing 3
        for i in range(len(regular_volumes) - 1):
            current = regular_volumes[i]
            next_vol = regular_volumes[i + 1]
            
            # Only consider integer gaps for now (simplification)
            if int(next_vol) - int(current) > 1:
                for missing_vol in range(int(current) + 1, int(next_vol)):
                    missing.append(float(missing_vol))
                    
        return missing
    
    def detect_duplicate_volumes(self, titles: List[str]) -> Dict[float, List[str]]:
        """
        Detect duplicate volume numbers in a series
        Returns dict mapping volume numbers to lists of titles
        """
        if not titles:
            return {}
            
        # Extract volume numbers
        title_to_volume = {}
        for title in titles:
            vol = self.extract_volume_number(title)
            if vol is not None:
                title_to_volume[title] = vol
                
        # Group by volume number
        volume_to_titles = {}
        for title, vol in title_to_volume.items():
            if vol not in volume_to_titles:
                volume_to_titles[vol] = []
            volume_to_titles[vol].append(title)
                
        # Filter to only include duplicates
        duplicates = {vol: titles for vol, titles in volume_to_titles.items() 
                     if len(titles) > 1}
                     
        return duplicates
    
    def compare_series_names(self, name1: str, name2: str) -> float:
        """
        Compare two series names and return similarity score
        Takes into account aliases and normalization
        Returns float from 0.0 (completely different) to 1.0 (identical)
        """
        if not name1 or not name2:
            return 0.0
            
        # Normalize both names
        norm1 = self.normalize_series_name(name1)
        norm2 = self.normalize_series_name(name2)
        
        # Check for exact match after normalization
        if norm1 == norm2:
            return 1.0
            
        # Check for alias match
        if norm1 in self.series_aliases and self.series_aliases[norm1] == norm2:
            return 0.95
            
        if norm2 in self.series_aliases and self.series_aliases[norm2] == norm1:
            return 0.95
            
        # Check for partial containment
        if norm1 in norm2 or norm2 in norm1:
            # Adjust score based on length difference
            shorter = norm1 if len(norm1) < len(norm2) else norm2
            longer = norm2 if len(norm1) < len(norm2) else norm1
            
            if len(shorter) / len(longer) > 0.7:
                return 0.85
            else:
                return 0.7
                
        # Fallback to sequence matching
        return SequenceMatcher(None, norm1, norm2).ratio()

    def analyze_series_volumes(self, book_data: List[Dict]) -> Dict:
        """
        Analyze volumes in a series to detect gaps, duplicates, etc.
        
        Args:
            book_data: List of book dictionaries with 'title' and 'series' keys
            
        Returns:
            Dict with analysis results:
                - total_volumes: int - number of volumes found
                - volume_range: tuple - (min, max) volume numbers
                - gaps: list - missing volume numbers
                - duplicates: dict - mapping of duplicate volumes to title lists
        """
        # Extract volume numbers from titles
        volumes = []
        for book in book_data:
            title = book.get('title', '')
            vol = self.extract_volume_number(title)
            if vol is not None:
                volumes.append(vol)
        
        # Calculate statistics
        if not volumes:
            return {
                'total_volumes': 0,
                'volume_range': (0, 0),
                'gaps': [],
                'duplicates': {}
            }
            
        # Find missing volumes
        volumes = sorted(volumes)
        min_vol = min(volumes)
        max_vol = max(volumes)
        
        # Detect gaps (missing volumes)
        expected_volumes = set(v for v in range(int(min_vol), int(max_vol) + 1))
        actual_volumes = set(int(v) for v in volumes if v.is_integer())
        gaps = sorted(list(expected_volumes - actual_volumes))
        
        # Find duplicates
        volume_count = {}
        for vol in volumes:
            if vol not in volume_count:
                volume_count[vol] = 0
            volume_count[vol] += 1
            
        duplicates = {vol: [] for vol, count in volume_count.items() if count > 1}
        
        # Map titles to duplicate volumes
        for book in book_data:
            title = book.get('title', '')
            vol = self.extract_volume_number(title)
            if vol is not None and vol in duplicates:
                duplicates[vol].append(title)
        
        return {
            'total_volumes': len(volumes),
            'volume_range': (min_vol, max_vol),
            'gaps': gaps,
            'duplicates': duplicates
        }
