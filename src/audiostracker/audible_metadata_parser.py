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
                    
                    # Extract volume info from product title and series name
                    if "title" in product:
                        self._extract_volume_pattern(product["title"], series_name)
        
        return self.series_aliases
    
    def _extract_volume_pattern(self, title: str, series_name: str) -> None:
        """Extract volume pattern from title and series name"""
        # Remove series name from title to isolate volume info
        title_remainder = title.replace(series_name, '').strip()
        title_remainder = re.sub(r'^[,:\s]+', '', title_remainder)
        
        # Common patterns to check
        patterns = [
            r'vol\.?\s*(\d+(?:\.\d+)?)',
            r'volume\s*(\d+(?:\.\d+)?)',
            r'(?:^|\s)(\d+)(?:\s|$)',
            r'\(light novel\)',
            r'\(ln\)',
        ]
        
        for pattern in patterns:
            if re.search(pattern, title_remainder, re.IGNORECASE):
                self.volume_patterns.add(pattern)
    
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
        from .series_analysis import series_analyzer
        
        # Extract all patterns
        self.extract_all_patterns()
        
        updated_count = 0
        
        # Update author aliases
        for canonical, aliases in self.author_aliases.items():
            for alias in aliases:
                if alias not in author_matcher.author_aliases.get(canonical, set()):
                    # Add the new alias
                    author_matcher.add_author_alias(canonical, alias)
                    updated_count += 1
        
        # Update volume patterns
        for pattern in self.volume_patterns:
            if pattern not in series_analyzer.volume_patterns:
                series_analyzer.volume_patterns.append(pattern)
                updated_count += 1
        
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
                        updated_count += 1
        
        return updated_count

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
