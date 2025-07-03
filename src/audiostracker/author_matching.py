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
            "Yuka Tachibana": {
                "Yuka Tachibana",
                "橘由華",
                "Tachibana Yuka"
            },
            "Fujino Omori": {
                "Fujino Omori",
                "大森藤ノ",
                "Omori Fujino"
            },
            "Aneko Yusagi": {
                "Aneko Yusagi",
                "悠崎あねこ",
                "Yusagi Aneko"
            },
            "NISIO ISIN": {
                "NISIO ISIN",
                "NisiOisiN",
                "西尾維新",
                "Nishio Ishin"
            },
            "Shigeru Miura": {
                "Shigeru Miura",
                "三浦しをん",
                "Miura Shigeru"
            },
            "Shibai Kineko": {
                "Shibai Kineko",
                "柴緑ねこ",
                "Kineko Shibai"
            },
            "Shu": {
                "Shu",
                "秋",
                "Shu, Tsukiko - illustrator",
                "Tsukiko - illustrator, Shu"
            },
            "Miku": {
                "Miku",
                "ミク",
                "Miku, Milcha - illustrator",
                "Milcha - illustrator, Miku"
            },
            "Sunsunsun": {
                "Sunsunsun",
                "三三三",
                "San San San",
                "Sunsunsun, Momoco - illustrator",
                "Momoco - illustrator, Sunsunsun"
            },
            "Yoshinobu Akita": {
                "Yoshinobu Akita",
                "秋田禎信",
                "Akita Yoshinobu"
            },
            "Kinoko Nasu": {
                "Kinoko Nasu", 
                "奈須きのこ", 
                "Nasu Kinoko"
            },
            "Gen Urobuchi": {
                "Gen Urobuchi",
                "虚淵玄",
                "Urobuchi Gen", 
                "Nitroplus"
            },
            "Kafka Asagiri": {
                "Kafka Asagiri",
                "朝霧カフカ",
                "Asagiri Kafka"
            },
            "Yuki Yaku": {
                "Yuki Yaku",
                "夜宵草",
                "Yaku Yuki"
            },
            "Nisio Isin": {
                "Nisio Isin",
                "西尾 維新",
                "Nishio Ishin",
                "NISIOISIN"
            },
            "Natsuki Kizu": {
                "Natsuki Kizu",
                "キヅナツキ",
                "Kizu Natsuki"
            },
            "Makoto Shinkai": {
                "Makoto Shinkai",
                "新海誠",
                "Shinkai Makoto"
            },
            "Kamome Shirahama": {
                "Kamome Shirahama",
                "白浜鴎",
                "Shirahama Kamome"
            },
            "Adachitoka": {
                "Adachitoka",
                "あだちとか"
            },
            "Tsukasa Fushimi": {
                "Tsukasa Fushimi",
                "伏見つかさ",
                "Fushimi Tsukasa"
            },
            "Wataru Watari": {
                "Wataru Watari",
                "渡航",
                "Watari Wataru"
            }
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
            r'\s*contributor\s*$',
            r'\s*editor\s*$',
            r'\s*created by\s*$',
        ]
        
        for suffix in suffixes:
            name = re.sub(suffix, '', name, flags=re.IGNORECASE)
            
        # Also remove text within parentheses at the end of the name
        name = re.sub(r'\s*\([^)]*\)\s*$', '', name)
        
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
        
        # Normalize names for comparison
        norm1 = self.normalize_author_name(author1)
        norm2 = self.normalize_author_name(author2)
        
        # Handle potentially ambiguous author names 
        ambiguity_score = self.handle_ambiguous_matches(norm1, norm2)
        
        if ambiguity_score == 0.0:
            # Rejected due to known ambiguity (e.g. "Fuse" vs "Short Fuse")
            return False, 0.0
            
        # Check for partial word match (for cases like author name contained in longer name)
        pattern1 = r'(^|\s)' + re.escape(norm1) + r'(\s|$)'
        pattern2 = r'(^|\s)' + re.escape(norm2) + r'(\s|$)'
        
        if re.search(pattern1, norm2) or re.search(pattern2, norm1):
            # More careful check to avoid matching unrelated names
            # Only match if the partial name is at least 4 characters long
            if len(norm1) >= 4 or len(norm2) >= 4:
                # Apply ambiguity adjustment
                return True, 0.85 * ambiguity_score
        
        # Fuzzy matching on normalized names
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Apply ambiguity adjustment to similarity
        adjusted_similarity = similarity * ambiguity_score
        
        return adjusted_similarity >= threshold, adjusted_similarity
    
    def add_author_alias(self, canonical: str, alias: str):
        """Add a new author alias mapping"""
        if canonical not in self.author_aliases:
            self.author_aliases[canonical] = {canonical}
        
        self.author_aliases[canonical].add(alias)
        self.alias_to_canonical[self.normalize_author_name(alias)] = canonical
    
    def handle_ambiguous_matches(self, author1: str, author2: str) -> float:
        """
        Handle special cases of ambiguous author names like 'Fuse' vs 'Short Fuse'
        
        Returns:
            float: Adjusted confidence score (0.0 to 1.0)
        """
        # Normalize both names for comparison
        name1_lower = author1.lower().strip()
        name2_lower = author2.lower().strip()
        
        # List of known ambiguous name pairs to reject
        ambiguous_pairs = [
            ("fuse", "short fuse"),
            ("fuse", "science fuse"),
            ("fuse", "fuse media"),
            ("fuse", "fuse vc"),
            ("fuse", "fuse inventory"),
            ("fuse", "fuse campaign"),
            ("fuse", "fuse the world"),
            ("fuse", "tammy fuse"),
            ("fuse", "fuse kattai"),
            ("fuse", "world fuse"),
            ("ciel", "black ciel"),
            ("mori", "kotaro mori"),
            ("kuro", "kurobane"),
            ("sora", "sorata akizuki")
        ]
        
        # Check if we have an ambiguous pair
        for pair in ambiguous_pairs:
            if (pair[0] in name1_lower and pair[1] in name2_lower) or \
               (pair[0] in name2_lower and pair[1] in name1_lower):
                return 0.0  # Reject the match completely
                
        # For partial name matches, be more strict
        if len(name1_lower) < 5 or len(name2_lower) < 5:
            # For very short names, one must be contained in the other
            if name1_lower in name2_lower or name2_lower in name1_lower:
                # Short name is substring of longer name
                return 0.75
            else:
                # Short names that don't match exactly are likely different authors
                return 0.0
                
        return 1.0  # No ambiguity detected, use normal matching


# Global instance
author_matcher = AuthorMatcher()

def match_authors(author1: str, author2: str, author_matcher_instance = None, threshold: float = 0.8) -> Tuple[bool, float]:
    """Convenience function for author matching"""
    if isinstance(author_matcher_instance, AuthorMatcher):
        # If an AuthorMatcher instance is provided, use it
        return author_matcher_instance.authors_match(author1, author2, threshold)
    else:
        # Otherwise, use the global instance and treat the third argument as threshold if provided
        if author_matcher_instance is not None and isinstance(author_matcher_instance, (int, float)):
            threshold = author_matcher_instance
        return author_matcher.authors_match(author1, author2, threshold)

def get_canonical_author_name(author: str) -> str:
    """Get canonical author name"""
    return author_matcher.get_canonical_author(author)
