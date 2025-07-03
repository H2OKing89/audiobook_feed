#!/usr/bin/env python3
"""
Analyze title and series patterns to design enhanced matching system
"""

import sys
import os
import json
import re
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def analyze_title_patterns():
    """Analyze title patterns across all samples"""
    print("📚 Analyzing Title Patterns")
    print("=" * 40)
    
    samples_dir = Path("tests/audiobook_samples")
    
    all_titles = []
    all_series = []
    title_patterns = defaultdict(list)
    series_patterns = defaultdict(list)
    
    # Load all sample data
    for json_file in samples_dir.glob("*_sample.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                books = json.load(f)
                
            author_name = json_file.stem.replace("_sample", "").replace("_", " ")
            
            for book in books:
                if 'title' in book and book['title']:
                    title = book['title']
                    all_titles.append(title)
                    title_patterns[author_name].append(title)
                
                if 'series' in book and book['series'] and book['series'] != 'N/A':
                    series = book['series']
                    all_series.append(series)
                    series_patterns[author_name].append(series)
                    
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
    
    print(f"Total titles found: {len(all_titles)}")
    print(f"Total series found: {len(all_series)}")
    
    # Analyze title variations
    print("\n📖 Common Title Patterns:")
    print("-" * 30)
    
    volume_patterns = Counter()
    common_words = Counter()
    title_suffixes = Counter()
    
    for title in all_titles:
        # Extract volume patterns
        vol_matches = re.findall(r'vol\.?\s*(\d+(?:\.\d+)?)', title, re.IGNORECASE)
        if vol_matches:
            volume_patterns['vol'] += 1
        
        volume_matches = re.findall(r'volume\s*(\d+(?:\.\d+)?)', title, re.IGNORECASE)
        if volume_matches:
            volume_patterns['volume'] += 1
        
        book_matches = re.findall(r'book\s*(\d+(?:\.\d+)?)', title, re.IGNORECASE)
        if book_matches:
            volume_patterns['book'] += 1
        
        # Extract common suffixes
        if '(light novel)' in title.lower():
            title_suffixes['(light novel)'] += 1
        if '(ln)' in title.lower():
            title_suffixes['(ln)'] += 1
        if ': a litrpg adventure' in title.lower():
            title_suffixes[': a litrpg adventure'] += 1
        
        # Extract common words
        words = re.findall(r'\b\w+\b', title.lower())
        for word in words:
            if len(word) > 3:  # Skip short words
                common_words[word] += 1
    
    print("Volume patterns found:")
    for pattern, count in volume_patterns.most_common():
        print(f"  {pattern}: {count} occurrences")
    
    print("\nCommon title suffixes:")
    for suffix, count in title_suffixes.most_common():
        print(f"  '{suffix}': {count} occurrences")
    
    print("\nMost common words in titles:")
    for word, count in common_words.most_common(10):
        print(f"  '{word}': {count} occurrences")
    
    # Analyze series variations
    print("\n📚 Series Pattern Analysis:")
    print("-" * 30)
    
    series_counter = Counter(all_series)
    unique_series = len(set(all_series))
    
    print(f"Unique series: {unique_series}")
    print("Most common series:")
    for series, count in series_counter.most_common(10):
        print(f"  '{series}': {count} books")
    
    # Look for series with variations
    print("\nPotential series variations:")
    series_groups = defaultdict(list)
    for series in set(all_series):
        # Group by base name (removing common suffixes)
        base_name = series.lower()
        base_name = re.sub(r'\s*\([^)]*\)\s*$', '', base_name)  # Remove (stuff) at end
        base_name = re.sub(r'\s*series\s*$', '', base_name)  # Remove "series" at end
        base_name = re.sub(r'\s*\[.*\]\s*$', '', base_name)  # Remove [stuff] at end
        series_groups[base_name].append(series)
    
    for base_name, variations in series_groups.items():
        if len(variations) > 1:
            print(f"  '{base_name}': {variations}")

def analyze_title_series_relationships():
    """Analyze relationships between titles and series"""
    print("\n🔗 Title-Series Relationship Analysis")
    print("=" * 40)
    
    samples_dir = Path("tests/audiobook_samples")
    
    title_series_pairs = []
    
    for json_file in samples_dir.glob("*_sample.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                books = json.load(f)
                
            for book in books:
                title = book.get('title', '')
                series = book.get('series', '')
                
                if title and series and series != 'N/A':
                    title_series_pairs.append((title, series))
                    
        except Exception as e:
            continue
    
    print(f"Found {len(title_series_pairs)} title-series pairs")
    
    # Analyze how series names appear in titles
    series_in_title_count = 0
    partial_series_in_title_count = 0
    
    for title, series in title_series_pairs:
        title_lower = title.lower()
        series_lower = series.lower()
        
        if series_lower in title_lower:
            series_in_title_count += 1
        else:
            # Check for partial matches
            series_words = series_lower.split()
            title_words = title_lower.split()
            
            matching_words = sum(1 for word in series_words if word in title_words)
            if matching_words >= len(series_words) * 0.5:  # At least 50% of series words in title
                partial_series_in_title_count += 1
    
    print(f"Series name appears fully in title: {series_in_title_count}/{len(title_series_pairs)} ({series_in_title_count/len(title_series_pairs)*100:.1f}%)")
    print(f"Series name appears partially in title: {partial_series_in_title_count}/{len(title_series_pairs)} ({partial_series_in_title_count/len(title_series_pairs)*100:.1f}%)")

def suggest_matching_strategies():
    """Suggest strategies for title and series matching"""
    print("\n💡 Suggested Matching Strategies")
    print("=" * 40)
    
    print("""
1. **Title Normalization**:
   - Remove volume indicators (Vol., Volume, Book, etc.)
   - Remove common suffixes like "(Light Novel)", "(LN)"
   - Remove series names from titles when they appear
   - Normalize punctuation and spacing

2. **Series Normalization**:
   - Remove suffixes like "Series", "[French edition]", "(light novel)"
   - Handle abbreviations (LN, ln)
   - Group related series with similar base names

3. **Volume Extraction**:
   - Extract volume numbers from titles: Vol. X, Volume X, Book X
   - Handle decimal volumes: Vol. 4.5
   - Detect special volumes: Prologue, Epilogue, Side Stories

4. **Fuzzy Matching**:
   - Use rapidfuzz for similarity scoring
   - Apply different thresholds for titles vs series
   - Consider length differences in matching

5. **Title-Series Relationship**:
   - Extract series name from title when not provided
   - Validate series consistency within author works
   - Handle multi-series authors

6. **Language-Specific Handling**:
   - Japanese romanization variations
   - Handle subtitle translations
   - Multi-language editions (French, English, etc.)
""")

def main():
    """Run all analyses"""
    print("📊 Title and Series Pattern Analysis")
    print("=" * 50)
    
    analyze_title_patterns()
    analyze_title_series_relationships()
    suggest_matching_strategies()
    
    print("\n✅ Analysis completed!")

if __name__ == "__main__":
    main()
