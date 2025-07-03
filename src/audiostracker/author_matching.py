"""
Enhanced author matching system for AudioStacker
Handles author name variations, translations, and aliases
"""

import re
from typing import Dict, List, Set, Tuple
from difflib import SequenceMatcher
import unicodedata

class AuthorMatcher:
    """Enhanced author matching with aliases and normalization"""
    
    def __init__(self):
        # Author aliases mapping - can be extended
        self.author_aliases: Dict[str, Set[str]] = {
            "Rifujin na Magonote": {
                "理不尽な孫の手",
                "Rifujin na Magonote", 
                "Rifujin Na Magonote",
                "Magonote Rifujin na",
                "rifujin na magonote"
            },
            "Isuna Hasekura": {
                "Isuna Hasekura",
                "ハセクラ イスナ",
                "Hasekura Isuna"
            },
            "Fuse": {
                "Fuse",
                "ヒューズ",
                "フューズ",
                "Mitz Vah - illustrator, Fuse",
                "Fuse, Mitz Vah - illustrator",
                "Fuse (Author)"
            },
            "Natsume Akatsuki": {
                "Natsume Akatsuki",
                "暁なつめ",
                "Akatsuki Natsume"
            },
            "Hajime Kamoshida": {
                "Hajime Kamoshida",
                "鴨志田一",
                "Kamoshida Hajime"
            },
            "Reki Kawahara": {
                "Reki Kawahara",
                "川原礫",
                "Kawahara Reki"
            },
            "Kumo Kagyu": {
                "Kumo Kagyu",
                "蜘蛛暮らし",
                "Kagyu Kumo",
                "蜘蛛ですが、なにか？"
            },
            "Patora Fuyuhara": {
                "Patora Fuyuhara",
                "冬原パトラ",
                "Fuyuhara Patora"
            },
            "Tappei Nagatsuki": {
                "Tappei Nagatsuki",
                "長月達平",
                "Nagatsuki Tappei"
            },
            "Akumi Agitogi": {
                "Akumi Agitogi",
                "安爾とあぎとぎ",
                "Agitogi Akumi",
                "Tsukiho Tsukioka - illustrator, Akumi Agitogi",
                "Akumi Agitogi, Tsukiho Tsukioka"
            },
            "Yu Okano": {
                "Yu Okano",
                "Okano Yu",
                "岡野ユウ"
            },
            "Tsutomu Satō": {
                "Tsutomu Satō",
                "Tsutomu Satou",
                "Satō Tsutomu",
                "Satou Tsutomu",
                "佐島勤"
            },
            "Kugane Maruyama": {
                "Kugane Maruyama",
                "丸山くがね",
                "Maruyama Kugane"
            },
            "Kisetsu Morita": {
                "Kisetsu Morita",
                "森田季節",
                "Morita Kisetsu"
            },
            "Ryohgo Narita": {
                "Ryohgo Narita",
                "成田良悟",
                "Narita Ryohgo"
            },
            "Natsuya Semikawa": {
                "Natsuya Semikawa",
                "蝉川夏哉",
                "Semikawa Natsuya"
            },
            # Add more author mappings as needed
        }
        
        # Reverse mapping for quick lookup
        self.alias_to_canonical = {}
        for canonical, aliases in self.author_aliases.items():
            for alias in aliases:
                self.alias_to_canonical[self.normalize_author_name(alias)] = canonical
    
    def normalize_author_name(self, name: str) -> str:
        """Normalize author name for comparison"""
        if not name:
            return ""
        
        # Convert to lowercase
        name = name.lower().strip()
        
        # Remove common punctuation and extra spaces
        name = re.sub(r'[.,;:\-_()]', ' ', name)
        name = re.sub(r'\s+', ' ', name)
        
        # Handle Unicode normalization (for Japanese/Chinese characters)
        name = unicodedata.normalize('NFKC', name)
        
        # Remove common suffixes
        suffixes = [
            r'\s*translator\s*$',
            r'\s*illustrator\s*$',
            r'\s*narrator\s*$',
            r'\s*author\s*$',
            r'\s*writer\s*$',
            r'\s*sensei\s*$',
        ]
        
        for suffix in suffixes:
            name = re.sub(suffix, '', name, flags=re.IGNORECASE)
        
        return name.strip()
    
    def get_canonical_author(self, author_name: str) -> str:
        """Get the canonical author name for a given name or alias"""
        normalized = self.normalize_author_name(author_name)
        
        # First check for exact match
        if normalized in self.alias_to_canonical:
            return self.alias_to_canonical[normalized]
        
        # Then check for partial match (for cases like "Fuse" vs "Short Fuse")
        for alias, canonical in self.alias_to_canonical.items():
            # Check if normalized author name is a complete standalone word in an alias
            pattern = r'(^|\s)' + re.escape(normalized) + r'(\s|$)'
            if re.search(pattern, alias):
                return canonical
        
        return author_name
    
    def authors_match(self, author1: str, author2: str, threshold: float = 0.8) -> Tuple[bool, float]:
        """
        Check if two author names match, considering aliases and fuzzy matching
        
        Returns:
            Tuple of (matches: bool, confidence: float)
        """
        if not author1 or not author2:
            return False, 0.0
        
        # Check exact match first
        if self.normalize_author_name(author1) == self.normalize_author_name(author2):
            return True, 1.0
        
        # Check canonical names
        canonical1 = self.get_canonical_author(author1)
        canonical2 = self.get_canonical_author(author2)
        
        if canonical1 == canonical2:
            return True, 0.95
        
        # Partial word match check (for cases like "Fuse" in "Short Fuse")
        norm1 = self.normalize_author_name(author1)
        norm2 = self.normalize_author_name(author2)
        
        # Check if norm1 is contained as a complete word in norm2
        pattern1 = r'(^|\s)' + re.escape(norm1) + r'(\s|$)'
        # Check if norm2 is contained as a complete word in norm1
        pattern2 = r'(^|\s)' + re.escape(norm2) + r'(\s|$)'
        
        if re.search(pattern1, norm2) or re.search(pattern2, norm1):
            # More careful check to avoid matching unrelated names
            # Only match if the partial name is at least 4 characters long
            if len(norm1) >= 4 or len(norm2) >= 4:
                return True, 0.85
        
        # Fuzzy matching on normalized names
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        return similarity >= threshold, similarity
    
    def add_author_alias(self, canonical: str, alias: str):
        """Add a new author alias mapping"""
        if canonical not in self.author_aliases:
            self.author_aliases[canonical] = {canonical}
        
        self.author_aliases[canonical].add(alias)
        self.alias_to_canonical[self.normalize_author_name(alias)] = canonical


# Global instance
author_matcher = AuthorMatcher()

def match_authors(author1: str, author2: str, threshold: float = 0.8) -> Tuple[bool, float]:
    """Convenience function for author matching"""
    return author_matcher.authors_match(author1, author2, threshold)

def get_canonical_author_name(author: str) -> str:
    """Get canonical author name"""
    return author_matcher.get_canonical_author(author)
