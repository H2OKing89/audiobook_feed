"""
Enhanced Title and Series Matching for AudioStacker
Handles title variations, series normalization, and volume extraction
"""

import re
from typing import Dict, List, Set, Tuple, Optional, Union
from pathlib import Path

try:
    from rapidfuzz import fuzz
    USE_RAPIDFUZZ = True
except ImportError:
    from difflib import SequenceMatcher
    USE_RAPIDFUZZ = False

class TitleSeriesMatcher:
    """Enhanced title and series matching with normalization and fuzzy matching"""
    
    def __init__(self):
        # Volume patterns (more specific first)
        self.volume_patterns = [
            r'vol\.?\s*(\d+(?:\.\d+)?)',
            r'volume\s*(\d+(?:\.\d+)?)',
            r'book\s*(\d+(?:\.\d+)?)',
            r'part\s*(\d+(?:\.\d+)?)',
            r'chapter\s*(\d+(?:\.\d+)?)',
            r'#(\d+(?:\.\d+)?)',
            r'\s+(\d+):\s*',  # " 12: " pattern (more specific)
            r'\s+(\d+)(?:\s|$)',  # " 12 " or " 12" at end
            r'-\s*(\d+(?:\.\d+)?)(?:\s|$)',
            r'\((\d+(?:\.\d+)?)\)',
            r'(?:^|\s)(\d+)(?:\s|$)',  # Standalone number (last resort)
        ]
        
        # Common title suffixes to normalize
        self.title_suffixes = [
            r'\s*\(light novel\)$',
            r'\s*\(ln\)$',
            r'\s*:\s*a\s+litrpg\s+adventure$',
            r'\s*-\s*a\s+litrpg\s+adventure$',
            r'\s*\(audiobook\)$',
            r'\s*audiobook$',
        ]
        
        # Common series suffixes to normalize
        self.series_suffixes = [
            r'\s*\[.*edition\]$',  # [French edition], etc.
            r'\s*\(light novel\)$',
            r'\s*\(ln\)$',
            # Only remove series/collection/saga if there's a word before it
            r'\s+series$',  # Matches " series" at the end
            r'\s+collection$',  # Matches " collection" at the end  
            r'\s+saga$',  # Matches " saga" at the end
        ]
        
        # Special volume terms
        self.special_volumes = {
            'prologue': 0,
            'prequel': 0,
            'genesis': 0,
            'beginning': 0,
            'origins': 0,
            'zero': 0,
            'epilogue': 9999,
            'finale': 9999,
            'final': 9999,
            'the end': 9999,
            'side story': 0.5,
            'side stories': 0.5,
            'short story': 0.5,
            'short stories': 0.5,
            'interlude': 0.5,
            'omnibus': 8888,
            'box set': 8889,
            'complete collection': 8890,
        }
        
        # Learned series aliases
        self.series_aliases: Dict[str, str] = {}
        
        # Learned title patterns
        self.title_patterns: Dict[str, List[str]] = {}
    
    def normalize_title(self, title: str, remove_series: Optional[str] = None) -> str:
        """
        Normalize a title by removing volume indicators, suffixes, and optionally series name
        """
        if not title:
            return ""
        
        normalized = title.strip()
        
        # Remove volume indicators first (before series removal)
        original_normalized = normalized
        for pattern in self.volume_patterns:
            # Only remove if the pattern doesn't consume the entire title
            matches = re.findall(pattern, normalized, flags=re.IGNORECASE)
            if matches:
                # Create a pattern that captures the volume part to remove
                temp_normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
                temp_normalized = temp_normalized.strip()
                # Only apply if we still have meaningful content (at least 3 chars)
                if temp_normalized and len(temp_normalized) >= 3:
                    normalized = temp_normalized
                    break
        
        # Remove series name if provided
        if remove_series:
            series_normalized = self.normalize_series(remove_series)
            # Try multiple variations of series removal
            variations = [
                remove_series,
                series_normalized,
            ]
            
            for series_var in variations:
                if series_var and len(series_var) > 2:
                    # Use word boundaries to avoid partial matches
                    pattern = r'\b' + re.escape(series_var) + r'\b'
                    temp_normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
                    # Only apply if we still have meaningful content or if it's a complete match
                    if temp_normalized.strip() and len(temp_normalized.strip()) > 1:
                        normalized = temp_normalized
                        break
                    elif not temp_normalized.strip():
                        # Complete match - series name is the entire title
                        normalized = ""
                        break
            
            # Clean up punctuation after series removal
            normalized = re.sub(r'^[,:\-\s]+', '', normalized)  # Clean leading punct
            normalized = re.sub(r'[,:\-\s]+$', '', normalized)  # Clean trailing punct
        
        # Remove common suffixes
        for suffix_pattern in self.title_suffixes:
            normalized = re.sub(suffix_pattern, '', normalized, flags=re.IGNORECASE)
        
        # Clean up punctuation and whitespace
        normalized = re.sub(r'[,:\-_()]+', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = normalized.strip()
        
        return normalized
    
    def normalize_series(self, series: str) -> str:
        """
        Normalize a series name by removing common suffixes and variations
        """
        if not series or series == 'N/A':
            return ""
        
        normalized = series.strip()
        
        # Remove common suffixes, but be careful not to remove core parts of the name
        for suffix_pattern in self.series_suffixes:
            if re.search(suffix_pattern, normalized, re.IGNORECASE):
                # Test what would happen if we remove this suffix
                temp_result = re.sub(suffix_pattern, '', normalized, flags=re.IGNORECASE).strip()
                
                # Only apply the removal if:
                # 1. We have a meaningful result (more than just one word)
                # 2. OR it's a parenthetical/bracket suffix (always safe to remove)
                if (len(temp_result.split()) > 1 or 
                    suffix_pattern in [r'\s*\[.*edition\]$', r'\s*\(light novel\)$', r'\s*\(ln\)$']):
                    normalized = temp_result
                    break
        
        # Clean up punctuation and whitespace
        normalized = re.sub(r'[,:\-_()]+', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = normalized.strip()
        
        return normalized
    
    def extract_volume_number(self, title: str) -> Optional[Union[int, float]]:
        """
        Extract volume number from title
        """
        if not title:
            return None
        
        # Check for special volume terms first
        title_lower = title.lower()
        for term, volume in self.special_volumes.items():
            if term in title_lower:
                return volume
        
        # Check for numeric volume patterns
        for pattern in self.volume_patterns:
            matches = re.findall(pattern, title, re.IGNORECASE)
            if matches:
                try:
                    # Return the first match, converted to int or float
                    volume_str = matches[0]
                    if '.' in volume_str:
                        return float(volume_str)
                    else:
                        return int(volume_str)
                except ValueError:
                    continue
        
        return None
    
    def extract_series_from_title(self, title: str) -> Optional[str]:
        """
        Extract potential series name from title using common patterns
        """
        if not title:
            return None
        
        # Look for patterns like "Series Name: Volume X" or "Series Name, Vol. X"
        patterns = [
            r'^(.+?)(?::|,)\s*(?:vol\.?|volume|book|part|chapter)\s*\d+',
            r'^(.+?)(?::|,)\s*(?:#\d+)',
            r'^(.+?)\s*-\s*(?:vol\.?|volume|book|part)\s*\d+',
            r'^(.+?)\s+(?:vol\.?|volume|book|part)\s*\d+$',
            r'^(.+?)\s+\d+$',  # Series Name + number
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                potential_series = match.group(1).strip()
                # Make sure it's not too short or too long
                if 3 <= len(potential_series) <= 100:
                    return self.normalize_series(potential_series)
        
        return None
    
    def titles_match(self, title1: str, title2: str, threshold: float = 0.8, 
                    series1: Optional[str] = None, series2: Optional[str] = None) -> Tuple[bool, float]:
        """
        Check if two titles match, considering normalization and fuzzy matching
        """
        if not title1 or not title2:
            return False, 0.0
        
        # Normalize both titles
        norm1 = self.normalize_title(title1, series1)
        norm2 = self.normalize_title(title2, series2)
        
        # Exact match after normalization
        if norm1.lower() == norm2.lower():
            return True, 1.0
        
        # Skip very short normalized titles
        if len(norm1) < 3 or len(norm2) < 3:
            return False, 0.0
        
        # Fuzzy matching
        if USE_RAPIDFUZZ:
            similarity = fuzz.ratio(norm1.lower(), norm2.lower()) / 100.0
        else:
            similarity = SequenceMatcher(None, norm1.lower(), norm2.lower()).ratio()
        
        return similarity >= threshold, similarity
    
    def series_match(self, series1: str, series2: str, threshold: float = 0.85) -> Tuple[bool, float]:
        """
        Check if two series names match, considering normalization and fuzzy matching
        """
        if not series1 or not series2 or series1 == 'N/A' or series2 == 'N/A':
            return False, 0.0
        
        # Normalize both series
        norm1 = self.normalize_series(series1)
        norm2 = self.normalize_series(series2)
        
        # Check aliases first
        canonical1 = self.series_aliases.get(norm1.lower(), norm1)
        canonical2 = self.series_aliases.get(norm2.lower(), norm2)
        
        # Exact match after normalization and alias resolution
        if canonical1.lower() == canonical2.lower():
            return True, 1.0
        
        # Skip very short series names
        if len(norm1) < 3 or len(norm2) < 3:
            return False, 0.0
        
        # Special case: if one is a substring of the other after normalization
        if norm1.lower() in norm2.lower() or norm2.lower() in norm1.lower():
            # But only if the shorter one is at least 60% of the longer one
            min_len = min(len(norm1), len(norm2))
            max_len = max(len(norm1), len(norm2))
            if min_len / max_len >= 0.6:
                return True, 0.95
        
        # Fuzzy matching
        if USE_RAPIDFUZZ:
            similarity = fuzz.ratio(canonical1.lower(), canonical2.lower()) / 100.0
        else:
            similarity = SequenceMatcher(None, canonical1.lower(), canonical2.lower()).ratio()
        
        return similarity >= threshold, similarity
    
    def add_series_alias(self, canonical: str, alias: str):
        """Add a series alias mapping"""
        canonical_norm = self.normalize_series(canonical).lower()
        alias_norm = self.normalize_series(alias).lower()
        
        if canonical_norm and alias_norm and canonical_norm != alias_norm:
            self.series_aliases[alias_norm] = canonical_norm
    
    def learn_from_data(self, books: List[Dict]):
        """
        Learn patterns from book data
        """
        # Group books by author/series to find patterns
        author_series = {}
        series_titles = {}
        
        for book in books:
            author = book.get('author', '')
            series = book.get('series', '')
            title = book.get('title', '')
            
            if not all([author, series, title]) or series == 'N/A':
                continue
            
            # Track author-series relationships
            if author not in author_series:
                author_series[author] = set()
            author_series[author].add(series)
            
            # Track series-title relationships
            if series not in series_titles:
                series_titles[series] = []
            series_titles[series].append(title)
        
        # Learn series variations within authors
        for author, series_set in author_series.items():
            series_list = list(series_set)
            for i, series1 in enumerate(series_list):
                for series2 in series_list[i+1:]:
                    # Check if these might be the same series with different formatting
                    norm1 = self.normalize_series(series1)
                    norm2 = self.normalize_series(series2)
                    
                    if norm1 and norm2 and norm1.lower() != norm2.lower():
                        # Check similarity
                        if USE_RAPIDFUZZ:
                            similarity = fuzz.ratio(norm1.lower(), norm2.lower()) / 100.0
                        else:
                            similarity = SequenceMatcher(None, norm1.lower(), norm2.lower()).ratio()
                        
                        # More lenient learning threshold
                        if similarity > 0.7:  # High similarity suggests they're the same series
                            # Use the longer, more complete name as canonical
                            if len(series1) >= len(series2):
                                self.add_series_alias(series1, series2)
                            else:
                                self.add_series_alias(series2, series1)
                        
                        # Also check if one is a substring of the other
                        elif norm1.lower() in norm2.lower() or norm2.lower() in norm1.lower():
                            min_len = min(len(norm1), len(norm2))
                            max_len = max(len(norm1), len(norm2))
                            if min_len / max_len >= 0.6:  # 60% overlap
                                if len(series1) >= len(series2):
                                    self.add_series_alias(series1, series2)
                                else:
                                    self.add_series_alias(series2, series1)
        
        # Learn from common patterns across different authors
        all_series = list(series_titles.keys())
        for i, series1 in enumerate(all_series):
            for series2 in all_series[i+1:]:
                norm1 = self.normalize_series(series1)
                norm2 = self.normalize_series(series2)
                
                if norm1 and norm2 and norm1.lower() != norm2.lower():
                    # Only learn if they're very similar (high threshold for cross-author)
                    if USE_RAPIDFUZZ:
                        similarity = fuzz.ratio(norm1.lower(), norm2.lower()) / 100.0
                    else:
                        similarity = SequenceMatcher(None, norm1.lower(), norm2.lower()).ratio()
                    
                    if similarity > 0.9:  # Very high threshold for cross-author aliases
                        if len(series1) >= len(series2):
                            self.add_series_alias(series1, series2)
                        else:
                            self.add_series_alias(series2, series1)
    
    def match_audiobook(self, book1: Dict, book2: Dict, 
                       title_threshold: float = 0.8, 
                       series_threshold: float = 0.85) -> Dict[str, Union[bool, float, int, None]]:
        """
        Comprehensive matching between two audiobooks
        """
        result = {
            'titles_match': False,
            'title_similarity': 0.0,
            'series_match': False,
            'series_similarity': 0.0,
            'same_volume': False,
            'volume1': None,
            'volume2': None,
            'overall_match': False,
        }
        
        # Extract data
        title1 = book1.get('title', '')
        title2 = book2.get('title', '')
        series1 = book1.get('series', '')
        series2 = book2.get('series', '')
        
        # Title matching
        if title1 and title2:
            title_match, title_sim = self.titles_match(title1, title2, title_threshold, series1, series2)
            result['titles_match'] = title_match
            result['title_similarity'] = title_sim
        
        # Series matching
        if series1 and series2:
            series_match, series_sim = self.series_match(series1, series2, series_threshold)
            result['series_match'] = series_match
            result['series_similarity'] = series_sim
        
        # Volume matching
        vol1 = self.extract_volume_number(title1)
        vol2 = self.extract_volume_number(title2)
        result['volume1'] = vol1
        result['volume2'] = vol2
        result['same_volume'] = vol1 is not None and vol2 is not None and vol1 == vol2
        
        # Overall matching logic
        title_sim = result['title_similarity'] or 0.0
        overall_match = (
            (result['series_match'] and result['same_volume']) or
            (result['series_match'] and title_sim > 0.7) or
            (title_sim > 0.9)
        )
        
        result['overall_match'] = overall_match
        
        return result

# Global instance for easy access
title_series_matcher = TitleSeriesMatcher()

# Convenience functions
def normalize_title(title: str, remove_series: Optional[str] = None) -> str:
    """Normalize a title"""
    return title_series_matcher.normalize_title(title, remove_series)

def normalize_series(series: str) -> str:
    """Normalize a series name"""
    return title_series_matcher.normalize_series(series)

def extract_volume_number(title: str) -> Optional[Union[int, float]]:
    """Extract volume number from title"""
    return title_series_matcher.extract_volume_number(title)

def titles_match(title1: str, title2: str, threshold: float = 0.8,
                series1: Optional[str] = None, series2: Optional[str] = None) -> Tuple[bool, float]:
    """Check if two titles match"""
    return title_series_matcher.titles_match(title1, title2, threshold, series1, series2)

def series_match(series1: str, series2: str, threshold: float = 0.85) -> Tuple[bool, float]:
    """Check if two series match"""
    return title_series_matcher.series_match(series1, series2, threshold)

def match_audiobooks(book1: Dict, book2: Dict, 
                    title_threshold: float = 0.8, 
                    series_threshold: float = 0.85) -> Dict:
    """Comprehensive audiobook matching"""
    return title_series_matcher.match_audiobook(book1, book2, title_threshold, series_threshold)
