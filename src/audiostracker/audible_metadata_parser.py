"""
Audible Metadata Parser for AudioStacker
Extracts author aliases, series patterns, and volume information from Audible API metadata
"""

import json
import os
import re
from typing import Dict, List, Set, Tuple, Optional
import logging
from pathlib import Path
from difflib import SequenceMatcher

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudibleMetadataParser:
    """Parser for Audible API metadata to extract useful patterns and mappings"""
    
    def __init__(self, samples_dir: Optional[str] = None):
        """Initialize the parser with the directory containing sample files"""
        self.samples_dir = samples_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
            "tests", 
            "audiobook_samples"
        )
        
        self.author_aliases: Dict[str, Set[str]] = {}
        self.series_aliases: Dict[str, Set[str]] = {}
        self.volume_patterns: Set[str] = set()
        
    def load_sample_files(self) -> List[Dict]:
        """Load all JSON sample files"""
        samples = []
        
        try:
            for file_name in os.listdir(self.samples_dir):
                if file_name.endswith("_metadata_sample.json"):
                    file_path = os.path.join(self.samples_dir, file_name)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        samples.append(json.load(f))
                        logger.info(f"Loaded sample file: {file_name}")
        except Exception as e:
            logger.error(f"Error loading sample files: {e}")
            
        return samples
    
    def extract_author_aliases(self) -> Dict[str, Set[str]]:
        """Extract author aliases from sample data"""
        samples = self.load_sample_files()
        
        for sample in samples:
            if "products" not in sample:
                continue
                
            for product in sample["products"]:
                if "authors" not in product:
                    continue
                    
                # Extract primary author
                if product["authors"] and len(product["authors"]) > 0:
                    primary_author = product["authors"][0].get("name")
                    
                    # Skip translators and illustrators
                    if primary_author and (
                        "translator" not in primary_author.lower() and 
                        "illustrator" not in primary_author.lower()
                    ):
                        if primary_author not in self.author_aliases:
                            self.author_aliases[primary_author] = {primary_author}
                        
                        # Add all author combinations from this product
                        self._add_author_combinations(product["authors"])
        
        return self.author_aliases
    
    def _add_author_combinations(self, authors_list: List[Dict]) -> None:
        """Add all combinations of authors as aliases"""
        if not authors_list:
            return
            
        primary_author = authors_list[0].get("name")
        
        if not primary_author or "translator" in primary_author.lower() or "illustrator" in primary_author.lower():
            return
            
        # Extract base name (remove translator/illustrator suffixes)
        clean_primary = self._clean_author_name(primary_author)
        
        # Add the clean name as an alias
        if clean_primary != primary_author:
            self.author_aliases[primary_author].add(clean_primary)
            
        # Handle Japanese name order (Last First -> First Last)
        if " " in clean_primary:
            first_name, last_name = clean_primary.split(" ", 1)
            reversed_name = f"{last_name} {first_name}"
            self.author_aliases[primary_author].add(reversed_name)
            
        # Add combinations with illustrators
        for author in authors_list[1:]:
            if not author.get("name"):
                continue
                
            other_name = author.get("name")
            combined_name = f"{primary_author}, {other_name}"
            self.author_aliases[primary_author].add(combined_name)
            
            # Add illustrator first combination
            combined_name_rev = f"{other_name}, {primary_author}"
            self.author_aliases[primary_author].add(combined_name_rev)
    
    def _clean_author_name(self, author_name: str) -> str:
        """Clean author name by removing suffixes like translator, illustrator, etc."""
        if not author_name:
            return ""
            
        # Remove common suffixes
        suffixes = [
            r'\s*-\s*translator.*$',
            r'\s*-\s*illustrator.*$',
            r'\s*-\s*narrator.*$',
            r'\s*\(translator\).*$',
            r'\s*\(illustrator\).*$',
            r'\s*\(narrator\).*$',
        ]
        
        cleaned = author_name
        for suffix in suffixes:
            cleaned = re.sub(suffix, '', cleaned, flags=re.IGNORECASE)
            
        return cleaned.strip()
    
    def extract_series_patterns(self) -> Dict[str, Set[str]]:
        """Extract series name patterns and aliases"""
        samples = self.load_sample_files()
        
        for sample in samples:
            if "products" not in sample:
                continue
                
            for product in sample["products"]:
                if "series" not in product or not product["series"]:
                    continue
                    
                for series_info in product["series"]:
                    series_name = series_info.get("title")
                    if not series_name:
                        continue
                        
                    # Add to series aliases
                    if series_name not in self.series_aliases:
                        self.series_aliases[series_name] = {series_name}
                    
                    # Create variations of series name for better matching
                    self._add_series_variations(series_name)
                    
                    # Extract volume info from product title and series name
                    if "title" in product:
                        self._extract_volume_pattern(product["title"], series_name)
        
        return self.series_aliases
        
    def _add_series_variations(self, series_name: str) -> None:
        """Add variations of series names as aliases"""
        if not series_name:
            return
            
        # Add the original name
        if series_name not in self.series_aliases:
            self.series_aliases[series_name] = {series_name}
            
        # Create common variations
        variations = []
        
        # With/without "The" prefix
        if series_name.lower().startswith("the "):
            variations.append(series_name[4:])  # Without "The "
        else:
            variations.append(f"The {series_name}")  # With "The "
            
        # With/without "light novel" suffix
        ln_suffix = " (Light Novel)"
        ln_suffix_lower = ln_suffix.lower()
        if series_name.lower().endswith(ln_suffix_lower):
            variations.append(series_name[:-len(ln_suffix)])  # Without suffix
        else:
            variations.append(f"{series_name}{ln_suffix}")  # With suffix
            
        # Handling Japanese/English naming
        # Check for common Japanese light novel series with English translations
        jp_en_pairs = [
            ("tensei shitara slime datta ken", "that time i got reincarnated as a slime"),
            ("youjo senki", "saga of tanya the evil"),
            ("honzuki no gekokujou", "ascendance of a bookworm"),
            ("mahouka koukou no rettousei", "the irregular at magic high school"),
            ("tate no yuusha", "the rising of the shield hero"),
            ("kono subarashii sekai ni shukufuku wo", "konosuba"),
        ]
        
        for jp, en in jp_en_pairs:
            if jp in series_name.lower():
                variations.append(en)
            if en in series_name.lower():
                variations.append(jp)
                
        # Add all variations as aliases
        for variation in variations:
            self.series_aliases[series_name].add(variation)
    
    def _extract_volume_pattern(self, title: str, series_name: str) -> None:
        """Extract volume pattern from title and series name"""
        # Remove series name from title to isolate volume info
        if series_name in title:
            title_remainder = title.replace(series_name, '').strip()
        else:
            title_remainder = title  # Use whole title if series name isn't present
            
        title_remainder = re.sub(r'^[,:\s]+', '', title_remainder)
        
        # Common patterns to check
        patterns = [
            r'vol\.?\s*(\d+(?:\.\d+)?)',
            r'volume\s*(\d+(?:\.\d+)?)',
            r'book\s*(\d+(?:\.\d+)?)',
            r'(?:^|\s)(\d+)(?:\s|$)',
            r'\(light novel\)',
            r'\(ln\)',
            r'part\s*(\d+)',
            r'#(\d+)',
            r'-\s*(\d+)',
            r'\[(\d+)\]',
            r'\((\d+)\)',
            r'season\s*(\d+)',
            r'chapter\s*(\d+)',
        ]
        
        for pattern in patterns:
            if re.search(pattern, title_remainder, re.IGNORECASE):
                self.volume_patterns.add(pattern)
                
        # Detect special volume terms
        special_terms = self.detect_special_volume_terms(title_remainder)
        for term, volume_number in special_terms:
            # Create a pattern like r'\bterm\b' to match the whole term
            term_pattern = rf'\b{re.escape(term)}\b'
            self.volume_patterns.add(term_pattern)
    
    def detect_special_volume_terms(self, title: str) -> List[Tuple[str, float]]:
        """
        Detect special volume indicators in a title and return potential volume numbers
        
        Returns:
            List of tuples (term, volume_number)
        """
        special_terms = []
        
        # Convert to lowercase for matching
        title_lower = title.lower()
        
        # Check for common special volume indicators
        if "prologue" in title_lower:
            special_terms.append(("prologue", 0))
        elif "prequel" in title_lower:
            special_terms.append(("prequel", 0))
        elif "epilogue" in title_lower:
            special_terms.append(("epilogue", 9999))
        elif "finale" in title_lower or "final" in title_lower:
            special_terms.append(("finale", 9999))
        elif "side story" in title_lower or "side stories" in title_lower:
            special_terms.append(("side stories", 0.5))
        elif "short story" in title_lower or "short stories" in title_lower:
            special_terms.append(("short stories", 0.5))
        elif "interlude" in title_lower:
            special_terms.append(("interlude", 0.5))
        
        # Check for chapter-based volumes
        chapter_match = re.search(r'chapter\s+(one|two|three|four|five|six|seven|eight|nine|ten)', title_lower)
        if chapter_match:
            chapter_word = chapter_match.group(1)
            chapter_numbers = {
                "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, 
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
            }
            if chapter_word in chapter_numbers:
                special_terms.append((f"chapter {chapter_word}", chapter_numbers[chapter_word]))
        
        # Check for season-based volumes  
        season_match = re.search(r'(first|second|third|fourth|fifth)\s+season', title_lower)
        if season_match:
            season_word = season_match.group(1)
            season_numbers = {
                "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5
            }
            if season_word in season_numbers:
                special_terms.append((f"{season_word} season", season_numbers[season_word]))
        
        # Check for arc-based volumes
        arc_match = re.search(r'(first|second|third|fourth|fifth)\s+arc', title_lower)
        if arc_match:
            arc_word = arc_match.group(1)
            arc_numbers = {
                "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5
            }
            if arc_word in arc_numbers:
                special_terms.append((f"{arc_word} arc", arc_numbers[arc_word]))
        
        # Check for special collection terms
        if "omnibus" in title_lower:
            special_terms.append(("omnibus", 8888))
        elif "box set" in title_lower or "boxset" in title_lower:
            special_terms.append(("box set", 8889))
        elif "collection" in title_lower and ("complete" in title_lower or "full" in title_lower):
            special_terms.append(("complete collection", 8890))
        
        return special_terms
    
    def extract_all_patterns(self) -> Dict:
        """Extract all patterns: author aliases, series aliases, volume patterns"""
        self.extract_author_aliases()
        self.extract_series_patterns()
        
        return {
            "author_aliases": self.author_aliases,
            "series_aliases": self.series_aliases,
            "volume_patterns": self.volume_patterns
        }
    
    def generate_update_code(self) -> Dict[str, str]:
        """Generate code snippets for updating the matching modules"""
        self.extract_all_patterns()
        
        # Generate author_matching.py update
        author_code = "self.author_aliases: Dict[str, Set[str]] = {\n"
        for author, aliases in self.author_aliases.items():
            author_code += f'    "{author}": {{\n'
            for alias in aliases:
                author_code += f'        "{alias}",\n'
            author_code += "    },\n"
        author_code += "    # Add more author mappings as needed\n}"
        
        # Generate series normalization update
        series_code = "series_aliases = {\n"
        for series, aliases in self.series_aliases.items():
            series_normalized = series.lower().replace("(", "").replace(")", "").replace("light novel", "").strip()
            for alias in aliases:
                alias_normalized = alias.lower().replace("(", "").replace(")", "").replace("light novel", "").strip()
                if series_normalized != alias_normalized:
                    series_code += f'    "{alias_normalized}": "{series_normalized}",\n'
        series_code += "    # Add more mappings as needed\n}"
        
        # Generate volume patterns update
        volume_code = "self.volume_patterns = [\n"
        for pattern in self.volume_patterns:
            volume_code += f'    r\'{pattern}\',  # Add comment here\n'
        volume_code += "    # Add more patterns as needed\n]"
        
        return {
            "author_matching": author_code,
            "series_analysis_aliases": series_code,
            "volume_patterns": volume_code
        }
    
    def integrate_with_matching_system(self):
        """Integrate parsed data with the matching system"""
        from .author_matching import author_matcher
        from .series_analysis import SeriesVolumeAnalyzer
        
        # Extract all patterns
        self.extract_all_patterns()
        
        # Create series analyzer instance
        series_analyzer = SeriesVolumeAnalyzer()
        
        updated_count = 0
        author_updates = 0
        series_updates = 0
        volume_updates = 0
        
        # Update author aliases
        for canonical, aliases in self.author_aliases.items():
            for alias in aliases:
                if canonical not in author_matcher.author_aliases:
                    author_matcher.author_aliases[canonical] = {canonical}
                
                if alias not in author_matcher.author_aliases.get(canonical, set()):
                    # Add the new alias
                    author_matcher.add_author_alias(canonical, alias)
                    author_updates += 1
                    
        # Rebuild reverse mapping to reflect changes
        author_matcher.alias_to_canonical = {}
        for canonical, aliases in author_matcher.author_aliases.items():
            for alias in aliases:
                author_matcher.alias_to_canonical[author_matcher.normalize_author_name(alias)] = canonical
        
        # Update volume patterns
        for pattern in self.volume_patterns:
            # Handle special patterns separately
            if pattern.startswith('special:'):
                special_term = pattern.split(':', 1)[1]
                if special_term not in series_analyzer.special_title_volume_map:
                    # Add with a sensible default value
                    if special_term in ['prologue', 'prequel', 'genesis', 'beginning', 'origins', 'zero', 'the beginning']:
                        series_analyzer.special_title_volume_map[special_term] = 0
                    elif special_term in ['interlude', 'short stories', 'side stories']:
                        series_analyzer.special_title_volume_map[special_term] = 0.5
                    elif special_term in ['epilogue', 'finale', 'final', 'the end']:
                        series_analyzer.special_title_volume_map[special_term] = 9999
                    elif 'first' in special_term:
                        series_analyzer.special_title_volume_map[special_term] = 1
                    elif 'second' in special_term:
                        series_analyzer.special_title_volume_map[special_term] = 2
                    elif 'third' in special_term:
                        series_analyzer.special_title_volume_map[special_term] = 3
                    elif 'fourth' in special_term:
                        series_analyzer.special_title_volume_map[special_term] = 4
                    else:
                        series_analyzer.special_title_volume_map[special_term] = 0
                    volume_updates += 1
            elif pattern not in series_analyzer.volume_patterns:
                series_analyzer.volume_patterns.append(pattern)
                volume_updates += 1
        
        # Update series aliases
        for series, aliases in self.series_aliases.items():
            for alias in aliases:
                series_normalized = series.lower().replace("(", "").replace(")", "").replace("light novel", "").strip()
                alias_normalized = alias.lower().replace("(", "").replace(")", "").replace("light novel", "").strip()
                
                # Only add meaningful mappings
                if series_normalized != alias_normalized:
                    # Add to series aliases
                    if alias_normalized not in series_analyzer.series_aliases:
                        series_analyzer.series_aliases[alias_normalized] = series_normalized
                        series_updates += 1
        
        updated_count = author_updates + series_updates + volume_updates
        
        return {
            'total_updates': updated_count,
            'author_updates': author_updates,
            'series_updates': series_updates,
            'volume_updates': volume_updates
        }

    def extract_series_aliases(self) -> Dict[str, Set[str]]:
        """Extract series aliases and variants from sample data"""
        samples = self.load_sample_files()
        series_aliases: Dict[str, Set[str]] = {}
        
        for sample in samples:
            if "products" not in sample:
                continue
                
            for product in sample["products"]:
                # Extract series information
                if "series" in product and product["series"]:
                    for series in product["series"]:
                        series_name = series.get("title", "").strip()
                        if not series_name:
                            continue
                        
                        # Clean series name
                        cleaned_name = self._clean_series_name(series_name)
                        
                        # Extract from title if it might contain series info
                        title = product.get("title", "").strip()
                        if title:
                            # Look for series name in title
                            series_in_title = self._extract_series_from_title(title, series_name)
                            
                            if series_in_title and series_in_title != series_name:
                                # Store relationship
                                if cleaned_name not in series_aliases:
                                    series_aliases[cleaned_name] = {cleaned_name}
                                
                                series_aliases[cleaned_name].add(self._clean_series_name(series_in_title))
        
        # Add reverse mappings (bidirectional)
        bidirectional_aliases = {}
        for canonical, aliases in series_aliases.items():
            for alias in aliases:
                if alias not in bidirectional_aliases:
                    bidirectional_aliases[alias] = {alias}
                bidirectional_aliases[alias].add(canonical)
        
        return bidirectional_aliases
    
    def _clean_series_name(self, name: str) -> str:
        """Clean and normalize series name"""
        if not name:
            return ""
        
        # Convert to lowercase
        name = name.lower().strip()
        
        # Remove common punctuation
        name = re.sub(r'[.,;:\-_()]', ' ', name)
        name = re.sub(r'\s+', ' ', name)
        
        # Remove common suffixes
        suffixes = [
            r'\s*series\s*$',
            r'\s*novel\s*$',
            r'\s*novels\s*$',
            r'\s*light novel\s*$',
            r'\s*light novels\s*$',
            r'\s*ln\s*$',
            r'\s*collection\s*$',
            r'\s*audiobook\s*$',
            r'\s*the complete series\s*$',
        ]
        
        for suffix in suffixes:
            name = re.sub(suffix, '', name, flags=re.IGNORECASE)
        
        return name.strip()
    
    def _extract_series_from_title(self, title: str, known_series: str) -> str:
        """
        Extract potential series name from a title if it's different from the known series
        Returns the series name if found, empty string otherwise
        """
        # Check for common patterns like "Series Name, Vol. X" or "Series Name: Vol X"
        colon_pattern = re.match(r'(.+?)(?::|,|\s+-)\s+(?:vol\.?|volume|book|part)', title, re.IGNORECASE)
        if colon_pattern:
            extracted = colon_pattern.group(1).strip()
            if self._is_significantly_different(extracted, known_series):
                return extracted
        
        # Check for pattern like "Series Name #" or "Series Name 3"
        number_pattern = re.match(r'(.+?)\s+(?:#\d+|\d+)(?:\s|$)', title, re.IGNORECASE)
        if number_pattern:
            extracted = number_pattern.group(1).strip()
            if self._is_significantly_different(extracted, known_series):
                return extracted
                
        return ""
    
    def _is_significantly_different(self, str1: str, str2: str) -> bool:
        """Check if two strings are significantly different"""
        # Clean both strings
        str1 = self._clean_series_name(str1)
        str2 = self._clean_series_name(str2)
        
        # Check if they're exactly the same
        if str1 == str2:
            return False
            
        # Check if one is completely contained in the other
        if str1 in str2 or str2 in str1:
            # Not different enough
            return False
            
        # Calculate string similarity
        similarity = SequenceMatcher(None, str1, str2).ratio()
        
        # Only consider different if below similarity threshold
        return similarity < 0.7
    
    def apply_learnings_to_analyzer(self, analyzer=None):
        """Apply all learned patterns to the Series Volume Analyzer"""
        from .series_analysis import SeriesVolumeAnalyzer
        
        # Create a new analyzer if none was provided
        series_analyzer = analyzer or SeriesVolumeAnalyzer()
        
        # Extract special volume terms from our detect_special_volume_terms method
        special_terms_added = 0
        for title in self._get_all_titles():
            detected_terms = self.detect_special_volume_terms(title)
            for term, vol_num in detected_terms:
                if term not in series_analyzer.special_title_volume_map:
                    series_analyzer.special_title_volume_map[term] = vol_num
                    special_terms_added += 1
        
        # Extract new volume patterns
        volume_patterns_added = 0
        patterns_found = set()
        for product in self._get_all_products():
            title = product.get("title", "")
            if not title:
                continue
                
            # Look for patterns like "Vol. X", "Book Y", etc.
            pattern_matches = [
                (r'vol\.?\s*(\d+)', "vol. {}"),
                (r'volume\s*(\d+)', "volume {}"),
                (r'book\s*(\d+)', "book {}"),
                (r'part\s*(\d+)', "part {}"),
                (r'chapter\s*(\d+)', "chapter {}"),
                (r'#(\d+)', "#{}"),
                (r'-\s*(\d+)(?:\s|$)', "- {}"),
            ]
            
            for regex, pattern_template in pattern_matches:
                if re.search(regex, title, re.IGNORECASE):
                    pattern = r'' + regex
                    if pattern not in series_analyzer.volume_patterns and pattern not in patterns_found:
                        patterns_found.add(pattern)
                        volume_patterns_added += 1
        
        # Apply series aliases from our extraction method
        series_aliases = self.extract_series_aliases()
        series_aliases_added = 0
        
        for series, aliases in series_aliases.items():
            for alias in aliases:
                if alias != series and alias not in series_analyzer.series_aliases:
                    series_analyzer.series_aliases[alias] = series
                    series_aliases_added += 1
                        
        return {
            "analyzer": series_analyzer,
            "special_terms_added": special_terms_added,
            "volume_patterns_added": volume_patterns_added,
            "series_aliases_added": series_aliases_added
        }
        
    def _get_all_titles(self):
        """Get all titles from product samples"""
        titles = []
        for sample in self.load_sample_files():
            if "products" not in sample:
                continue
                
            for product in sample["products"]:
                title = product.get("title", "")
                if title:
                    titles.append(title)
        
        return titles
        
    def _get_all_products(self):
        """Get all products from samples"""
        products = []
        for sample in self.load_sample_files():
            if "products" not in sample:
                continue
                
            products.extend(sample["products"])
        
        return products
def main():
    """Main function to run the parser"""
    parser = AudibleMetadataParser()
    updates = parser.generate_update_code()
    
    print("=" * 80)
    print("AUTHOR ALIASES UPDATE:")
    print("=" * 80)
    print(updates["author_matching"])
    
    print("\n" + "=" * 80)
    print("SERIES ALIASES UPDATE:")
    print("=" * 80)
    print(updates["series_analysis_aliases"])
    
    print("\n" + "=" * 80)
    print("VOLUME PATTERNS UPDATE:")
    print("=" * 80)
    print(updates["volume_patterns"])

if __name__ == "__main__":
    main()
