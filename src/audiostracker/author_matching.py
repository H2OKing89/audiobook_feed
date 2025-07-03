"""
Enhanced author matching system for AudioStacker
Handles author name variations, translations, and aliases with universal transliteration support
"""

import re
import json
import os
from typing import Dict, List, Set, Tuple, Optional, Any
from pathlib import Path
import unicodedata

# Import transliteration libraries
try:
    from rapidfuzz import fuzz
    USE_RAPIDFUZZ = True
except ImportError:
    from difflib import SequenceMatcher
    USE_RAPIDFUZZ = False

try:
    import pykakasi
    PYKAKASI_AVAILABLE = True
except ImportError:
    PYKAKASI_AVAILABLE = False

try:
    from pypinyin import lazy_pinyin, Style
    PYPINYIN_AVAILABLE = True
except ImportError:
    PYPINYIN_AVAILABLE = False

try:
    from unidecode import unidecode
    UNIDECODE_AVAILABLE = True
except ImportError:
    UNIDECODE_AVAILABLE = False

class AuthorMatcher:
    """Enhanced author matching with universal transliteration and aliases"""
    
    def __init__(self, cache_file: Optional[str] = None):
        # Dynamic author aliases mapping - learned from data, not pre-populated
        self.author_aliases: Dict[str, Set[str]] = {}
        
        # Setup cache file path
        if cache_file is None:
            # Default to data directory
            self.cache_file = Path(__file__).parent / "data" / "author_aliases.json"
        else:
            self.cache_file = Path(cache_file)
        
        # Ensure cache directory exists
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize transliteration engines
        self._setup_transliteration()
        
        # Load existing aliases from cache
        self._load_aliases_cache()
        
        # Common name format patterns for intelligent matching
        self.name_patterns = [
            # Japanese name order variations
            r'^([A-Za-z]+)\s+([A-Za-z]+)$',  # "Firstname Lastname"
            r'^([A-Za-z]+),\s*([A-Za-z]+)$', # "Lastname, Firstname"
        ]
        
        # Reverse mapping for quick lookup - will be built dynamically
        self.alias_to_canonical = {}
        self._rebuild_alias_mapping()
    
    def _setup_transliteration(self):
        """Initialize transliteration engines"""
        self.kakasi = None
        if PYKAKASI_AVAILABLE:
            try:
                self.kakasi = pykakasi.kakasi()
                self.kakasi.setMode("H", "a")  # Hiragana to ASCII
                self.kakasi.setMode("K", "a")  # Katakana to ASCII  
                self.kakasi.setMode("J", "a")  # Japanese to ASCII
                self.kakasi.setMode("r", "Hepburn")  # Romaji style
                self.kakasi.setMode("C", True)  # Enable capitalization
                self.kakasi_conv = self.kakasi.getConverter()
            except Exception as e:
                print(f"Warning: Failed to initialize pykakasi: {e}")
                self.kakasi = None
    
    def _load_aliases_cache(self):
        """Load previously learned aliases from cache file"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    # Convert sets back from lists
                    for canonical, aliases in cache_data.items():
                        self.author_aliases[canonical] = set(aliases)
                print(f"Loaded {len(self.author_aliases)} author aliases from cache")
            except Exception as e:
                print(f"Warning: Failed to load aliases cache: {e}")
    
    def _save_aliases_cache(self):
        """Save learned aliases to cache file"""
        try:
            # Convert sets to lists for JSON serialization
            cache_data = {
                canonical: list(aliases) 
                for canonical, aliases in self.author_aliases.items()
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save aliases cache: {e}")
    
    def transliterate_name(self, name: str) -> List[str]:
        """
        Generate transliterated variants of a name
        
        Args:
            name: The name to transliterate
            
        Returns:
            List of transliterated variants including the original
        """
        if not name:
            return []
        
        variants = [name]  # Always include original
        
        # Japanese transliteration
        if self.kakasi and PYKAKASI_AVAILABLE:
            # Check if name contains Japanese characters
            if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', name):
                try:
                    romaji = self.kakasi_conv.do(name)
                    if romaji and romaji != name:
                        variants.append(romaji)
                except Exception:
                    pass
        
        # Chinese transliteration
        if PYPINYIN_AVAILABLE:
            # Check if name contains Chinese characters
            if re.search(r'[\u4E00-\u9FFF]', name):
                try:
                    pinyin = ' '.join(lazy_pinyin(name, style=Style.NORMAL))
                    if pinyin and pinyin != name:
                        variants.append(pinyin)
                    
                    # Also try without tone marks
                    pinyin_no_tone = ' '.join(lazy_pinyin(name, style=Style.TONE3))
                    if pinyin_no_tone and pinyin_no_tone != name and pinyin_no_tone != pinyin:
                        variants.append(pinyin_no_tone)
                except Exception:
                    pass
        
        # General Unicode transliteration (handles Cyrillic, Arabic, etc.)
        if UNIDECODE_AVAILABLE:
            try:
                ascii_version = unidecode(name)
                if ascii_version and ascii_version != name:
                    variants.append(ascii_version)
            except Exception:
                pass
        
        return list(set(variants))  # Remove duplicates
    
    def _rebuild_alias_mapping(self):
        """Rebuild the reverse alias mapping"""
        self.alias_to_canonical = {}
        for canonical, aliases in self.author_aliases.items():
            for alias in aliases:
                self.alias_to_canonical[self.normalize_author_name(alias)] = canonical
    
    def extract_author_name(self, full_name: str) -> str:
        """Extract just the author name from a string that may contain roles, etc."""
        if not full_name:
            return ""
        
        # Remove common role indicators
        role_patterns = [
            r'\s*-\s*(translator|illustrator|narrator|author|writer|editor|contributor)\s*$',
            r'\s*\((translator|illustrator|narrator|author|writer|editor|contributor)\)\s*$',
            r'\s*(translator|illustrator|narrator|author|writer|editor|contributor)\s*$',
        ]
        
        cleaned_name = full_name.strip()
        for pattern in role_patterns:
            cleaned_name = re.sub(pattern, '', cleaned_name, flags=re.IGNORECASE)
        
        # Handle comma-separated lists (e.g., "Author1, Illustrator - role")
        # But preserve "Lastname, Firstname" format
        if ',' in cleaned_name:
            parts = cleaned_name.split(',')
            # Check if this might be "Lastname, Firstname" format
            if len(parts) == 2 and not re.search(r'(translator|illustrator|narrator|editor|contributor)', cleaned_name, re.IGNORECASE):
                # This is likely "Lastname, Firstname" - keep the whole thing
                pass
            else:
                # This is likely "Author1, Illustrator - role" - take only the first part
                for part in parts:
                    # Check if this part contains role keywords
                    if not re.search(r'(translator|illustrator|narrator|editor|contributor)', part, re.IGNORECASE):
                        cleaned_name = part.strip()
                        break
        
        return cleaned_name.strip()
    
    def normalize_author_name(self, name: str) -> str:
        """Normalize author name for comparison with transliteration support"""
        if not name:
            return ""
        
        # Extract just the author name, removing roles and other metadata
        name = self.extract_author_name(name)
        
        # Convert to lowercase
        name = name.lower().strip()
        
        # Remove common punctuation and extra spaces
        name = re.sub(r'[.,;:\-_()]', ' ', name)
        name = re.sub(r'\s+', ' ', name)
        
        # Handle Unicode normalization (for Japanese/Chinese characters)
        name = unicodedata.normalize('NFKC', name)
        
        return name.strip()
    
    def detect_name_variants(self, name: str) -> List[str]:
        """Generate possible name variants including transliterations"""
        normalized = self.normalize_author_name(name)
        variants = [normalized]
        
        # Get transliterated variants
        transliterated = self.transliterate_name(name)
        for trans in transliterated:
            normalized_trans = self.normalize_author_name(trans)
            if normalized_trans and normalized_trans not in variants:
                variants.append(normalized_trans)
        
        # Handle name order variations (Japanese names often swap order)
        all_variants = []
        for variant in variants:
            all_variants.append(variant)
            if ' ' in variant:
                parts = variant.split()
                if len(parts) == 2:
                    # Add reversed order
                    all_variants.append(f"{parts[1]} {parts[0]}")
                    # Add comma-separated version
                    all_variants.append(f"{parts[1]}, {parts[0]}")
        
        # Handle common romanization variations
        romanization_variants = {
            'ou': 'o',    # Satou -> Sato
            'uu': 'u',    # Yuuki -> Yuki  
            'oh': 'o',    # Satoh -> Sato
            'wo': 'o',    # Tsukiwo -> Tsukio
            'aa': 'a',    # Ryuuji -> Ryuji
            'ee': 'e',    # Keeki -> Keki
            'ii': 'i',    # Shiina -> Shina
        }
        
        final_variants = []
        for variant in all_variants:
            final_variants.append(variant)
            for old, new in romanization_variants.items():
                if old in variant:
                    final_variants.append(variant.replace(old, new))
        
        return list(set(final_variants))  # Remove duplicates
    
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
        Check if two author names match using intelligent pattern matching
        
        Returns:
            Tuple of (matches: bool, confidence: float)
        """
        if not author1 or not author2:
            return False, 0.0
        
        # Extract clean author names (remove roles, etc.)
        clean1 = self.extract_author_name(author1)
        clean2 = self.extract_author_name(author2)
        
        if not clean1 or not clean2:
            return False, 0.0
        
        # Normalize for comparison
        norm1 = self.normalize_author_name(clean1)
        norm2 = self.normalize_author_name(clean2)
        
        # Check exact match first
        if norm1 == norm2:
            return True, 1.0
        
        # Check learned aliases
        canonical1 = self.get_canonical_author(clean1)
        canonical2 = self.get_canonical_author(clean2)
        
        if canonical1 == canonical2 and canonical1 != clean1:  # Only if we found an alias
            return True, 0.95
        
        # Generate name variants and check for matches
        variants1 = self.detect_name_variants(clean1)
        variants2 = self.detect_name_variants(clean2)
        
        # Check all variant combinations
        best_score = 0.0
        for v1 in variants1:
            for v2 in variants2:
                if v1 == v2:
                    return True, 0.9  # High confidence for variant match
                
                # Check similarity between variants
                if USE_RAPIDFUZZ:
                    similarity = fuzz.ratio(v1, v2) / 100.0
                else:
                    similarity = SequenceMatcher(None, v1, v2).ratio()
                best_score = max(best_score, similarity)
        
        # Handle potentially ambiguous matches
        ambiguity_score = self.handle_ambiguous_matches(norm1, norm2)
        
        if ambiguity_score == 0.0:
            return False, 0.0
        
        # Apply ambiguity adjustment
        final_score = best_score * ambiguity_score
        
        return final_score >= threshold, final_score
    
    def add_author_alias(self, canonical: str, alias: str):
        """Add a new author alias mapping"""
        # Clean the names first
        clean_canonical = self.extract_author_name(canonical)
        clean_alias = self.extract_author_name(alias)
        
        if not clean_canonical or not clean_alias:
            return
        
        if clean_canonical not in self.author_aliases:
            self.author_aliases[clean_canonical] = {clean_canonical}
        
        self.author_aliases[clean_canonical].add(clean_alias)
        self._rebuild_alias_mapping()
        
        # Save to cache
        self._save_aliases_cache()
    
    def learn_from_audiobook_data(self, audiobooks: List[Dict]):
        """
        Learn author aliases from audiobook metadata
        Look for patterns like same series with different author name formats
        """
        # Group books by series
        series_to_authors = {}
        
        for book in audiobooks:
            series = book.get('series', '')
            
            # Handle different author data formats
            if 'author' in book:
                # Single author field
                author_name = book['author']
                if author_name:
                    clean_name = self.extract_author_name(author_name)
                    if clean_name and series:
                        if series not in series_to_authors:
                            series_to_authors[series] = set()
                        series_to_authors[series].add(clean_name)
            elif 'authors' in book:
                # Multiple authors field
                authors = book.get('authors', [])
                if series and authors:
                    if series not in series_to_authors:
                        series_to_authors[series] = set()
                    
                    for author_data in authors:
                        if isinstance(author_data, dict):
                            author_name = author_data.get('name', '')
                        else:
                            author_name = str(author_data)
                        
                        if author_name:
                            clean_name = self.extract_author_name(author_name)
                            if clean_name:
                                series_to_authors[series].add(clean_name)
        
        # Look for likely aliases (same series, similar names)
        for series, authors in series_to_authors.items():
            authors_list = list(authors)
            
            # Only process if we have multiple author variations for a series
            if len(authors_list) > 1:
                # Check for similar names that might be the same author
                for i, author1 in enumerate(authors_list):
                    for author2 in authors_list[i+1:]:
                        # Use relaxed matching to detect potential aliases
                        variants1 = self.detect_name_variants(author1)
                        variants2 = self.detect_name_variants(author2)
                        
                        # Check for high similarity or variant matches
                        is_likely_alias = False
                        for v1 in variants1:
                            for v2 in variants2:
                                if USE_RAPIDFUZZ:
                                    similarity = fuzz.ratio(v1, v2) / 100.0
                                else:
                                    similarity = SequenceMatcher(None, v1, v2).ratio()
                                if similarity > 0.85:  # High similarity threshold
                                    is_likely_alias = True
                                    break
                            if is_likely_alias:
                                break
                        
                        if is_likely_alias:
                            # Choose the more "standard" looking name as canonical
                            if len(author1) >= len(author2):
                                canonical = author1
                                alias = author2
                            else:
                                canonical = author2
                                alias = author1
                            
                            self.add_author_alias(canonical, alias)
                            print(f"Learned alias: '{alias}' -> '{canonical}' (from series '{series}')")
    
    def handle_ambiguous_matches(self, author1: str, author2: str) -> float:
        """
        Handle special cases of ambiguous author names
        Focus on common real-world ambiguity issues
        
        Returns:
            float: Adjusted confidence score (0.0 to 1.0)
        """
        name1_lower = author1.lower().strip()
        name2_lower = author2.lower().strip()
        
        # Very short names are inherently ambiguous unless one contains the other
        if len(name1_lower) <= 3 or len(name2_lower) <= 3:
            # For very short names, require exact containment
            if name1_lower in name2_lower or name2_lower in name1_lower:
                return 0.7  # Medium confidence for short name matches
            else:
                return 0.0  # Reject short names that don't match
        
        # Single word vs multi-word name matching
        words1 = name1_lower.split()
        words2 = name2_lower.split()
        
        # If one is a single word and the other is multi-word
        if len(words1) == 1 and len(words2) > 1:
            # Check if the single word appears as a complete word in the multi-word name
            if words1[0] in words2:
                return 0.8  # Good confidence if single name is part of full name
            else:
                return 0.2  # Low confidence for unrelated single vs multi-word
        elif len(words2) == 1 and len(words1) > 1:
            # Same check reversed
            if words2[0] in words1:
                return 0.8
            else:
                return 0.2
        
        return 1.0  # No ambiguity detected

    def add_user_feedback(self, author1: str, author2: str, should_match: bool):
        """
        Add user feedback to improve author matching
        
        Args:
            author1: First author name
            author2: Second author name  
            should_match: True if these authors should be considered the same
        """
        clean1 = self.extract_author_name(author1)
        clean2 = self.extract_author_name(author2)
        
        if not clean1 or not clean2:
            return
        
        if should_match:
            # Choose the longer/more complete name as canonical
            if len(clean1) >= len(clean2):
                canonical = clean1
                alias = clean2
            else:
                canonical = clean2
                alias = clean1
            
            self.add_author_alias(canonical, alias)
            print(f"User feedback: Added alias '{alias}' for '{canonical}'")
        else:
            # For negative feedback, we could implement a "blacklist" of non-matches
            # For now, just log the feedback
            print(f"User feedback: '{clean1}' and '{clean2}' should NOT match")
    
    def get_matching_statistics(self) -> Dict[str, Any]:
        """Get statistics about the author matching system"""
        stats: Dict[str, Any] = {
            'total_canonical_authors': len(self.author_aliases),
            'total_aliases': sum(len(aliases) for aliases in self.author_aliases.values()),
            'transliteration_engines': [],
            'fuzzy_matching': 'unknown'
        }
        
        if PYKAKASI_AVAILABLE and self.kakasi:
            stats['transliteration_engines'].append('Japanese (pykakasi)')
        if PYPINYIN_AVAILABLE:
            stats['transliteration_engines'].append('Chinese (pypinyin)')
        if UNIDECODE_AVAILABLE:
            stats['transliteration_engines'].append('Universal (unidecode)')
        if USE_RAPIDFUZZ:
            stats['fuzzy_matching'] = 'rapidfuzz'
        else:
            stats['fuzzy_matching'] = 'difflib'
        
        return stats

    def reset_aliases(self):
        """Reset all learned aliases (for testing purposes)"""
        self.author_aliases = {}
        self.alias_to_canonical = {}
        self._save_aliases_cache()
        print("All author aliases have been reset")


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
