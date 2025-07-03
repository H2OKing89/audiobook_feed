#!/usr/bin/env python3
"""
Deep analysis of the new author samples to identify potential issues and improvements
"""

import sys
import os
import json
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from audiostracker.author_matching import AuthorMatcher, match_authors, get_canonical_author_name

def analyze_ryuto_sample():
    """Analyze the Ryuto sample which showed inconsistency"""
    print("🔍 Analyzing Ryuto Sample Issue")
    print("=" * 40)
    
    filepath = Path("tests/audiobook_samples/Ryuto_sample.json")
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        books = json.load(f)
    
    # Analyze author fields
    authors = Counter()
    for book in books:
        if 'author' in book and book['author']:
            authors[book['author']] += 1
    
    print(f"Authors found in Ryuto sample:")
    for author, count in authors.items():
        print(f"  '{author}': {count} books")
    
    # Check if this is a multi-author series or narrator issue
    print("\nBook details:")
    for i, book in enumerate(books[:5]):  # Show first 5 books
        print(f"  Book {i+1}: '{book.get('title', 'N/A')}'")
        print(f"    Author: '{book.get('author', 'N/A')}'")
        print(f"    Narrator: '{book.get('narrator', 'N/A')}'")
        print()

def analyze_kanji_transliteration():
    """Analyze kanji transliteration issues"""
    print("🌐 Analyzing Kanji Transliteration")
    print("=" * 40)
    
    matcher = AuthorMatcher()
    
    # Test kanji names and their expected romanizations
    test_cases = [
        ("田中雄", "Yuu Tanaka"),
        ("竜翔", "Ryuto"),
        ("白米良", "Ryo Shirakome"),
        ("理不尽な孫の手", "Rifujin na Magonote"),
    ]
    
    for kanji, expected_roman in test_cases:
        print(f"\n📝 Testing: '{kanji}' -> '{expected_roman}'")
        
        # Get transliteration variants
        variants = matcher.transliterate_name(kanji)
        print(f"  Generated variants: {variants}")
        
        # Test matching
        match_result = match_authors(kanji, expected_roman)
        print(f"  Direct match: {match_result}")
        
        # Check if any variant matches
        best_match = False
        best_score = 0
        for variant in variants:
            result = match_authors(variant, expected_roman)
            if result[0] or result[1] > best_score:
                best_match = result[0]
                best_score = result[1]
        
        print(f"  Best variant match: ({best_match}, {best_score:.3f})")
        
        # Suggest improvements
        if not best_match and best_score < 0.8:
            print(f"  ⚠️  Transliteration may need improvement")

def analyze_pen_names():
    """Analyze pen names and unique author names"""
    print("🖊️ Analyzing Pen Names and Unique Authors")
    print("=" * 40)
    
    # Authors with interesting pen names
    pen_names = [
        "Sunsunsun",      # サンサンサン
        "Shirtaloon",     # English pen name
        "TurtleMe",       # English pen name
        "Matt Dinniman",  # Real name
    ]
    
    matcher = AuthorMatcher()
    
    for name in pen_names:
        print(f"\n🏷️  Analyzing: '{name}'")
        
        # Check normalization
        canonical = get_canonical_author_name(name)
        print(f"  Canonical: '{canonical}'")
        
        # Check transliteration (should be minimal for these)
        variants = matcher.transliterate_name(name)
        print(f"  Variants: {variants}")
        
        # Test common variations
        variations = [
            name.lower(),
            name.upper(),
            name.replace("Me", "me"),  # For TurtleMe
            name.replace("loon", "Loon"),  # For Shirtaloon
        ]
        
        for var in variations:
            if var != name:
                match_result = match_authors(name, var)
                print(f"  '{name}' vs '{var}': {match_result}")

def check_sample_data_quality():
    """Check the quality and consistency of sample data"""
    print("📊 Checking Sample Data Quality")
    print("=" * 40)
    
    samples_dir = Path("tests/audiobook_samples")
    
    # Files to check
    new_files = [
        "Yuu Tanaka_sample.json",
        "Sunsunsun_sample.json", 
        "Ryuto_sample.json",
        "Ryo Shirakome_sample.json",
        "Shirtaloon_sample.json",
        "TurtleMe_sample.json",
    ]
    
    for filename in new_files:
        filepath = samples_dir / filename
        if not filepath.exists():
            print(f"❌ Missing file: {filename}")
            continue
        
        print(f"\n📋 Checking {filename}:")
        print("-" * 30)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            books = json.load(f)
        
        if not books:
            print("  ⚠️  Empty file")
            continue
        
        # Check data consistency
        authors = set()
        titles = set()
        series = set()
        
        for book in books:
            if 'author' in book and book['author']:
                authors.add(book['author'])
            if 'title' in book and book['title']:
                titles.add(book['title'])
            if 'series' in book and book['series']:
                series.add(book['series'])
        
        print(f"  Books: {len(books)}")
        print(f"  Unique authors: {len(authors)} -> {list(authors)}")
        print(f"  Unique titles: {len(titles)}")
        print(f"  Unique series: {len(series)} -> {list(series)[:3]}{'...' if len(series) > 3 else ''}")
        
        # Check for potential issues
        if len(authors) > 1:
            print(f"  ⚠️  Multiple authors detected - may need investigation")
        
        # Check sample book structure
        if books:
            sample_book = books[0]
            required_fields = ['title', 'author', 'series']
            missing_fields = [field for field in required_fields if field not in sample_book]
            if missing_fields:
                print(f"  ⚠️  Missing fields in sample: {missing_fields}")
            else:
                print(f"  ✅ All required fields present")

def suggest_improvements():
    """Suggest improvements based on analysis"""
    print("💡 Suggested Improvements")
    print("=" * 40)
    
    print("""
Based on the analysis, here are some suggestions:

1. **Kanji Transliteration Enhancement**:
   - The current kanji->romaji transliteration needs improvement
   - Consider adding a kanji->romaji mapping database
   - Implement name-specific transliteration rules

2. **Multiple Author Detection**:
   - The Ryuto sample contains both 'Ryuto' and 'Mike Unwin'
   - This might be author vs narrator, or co-authors
   - Consider adding author role detection

3. **Pen Name Recognition**:
   - Pen names like 'Sunsunsun', 'Shirtaloon', 'TurtleMe' are handled well
   - Consider adding pen name pattern recognition

4. **Data Quality Improvements**:
   - Add validation for multi-author samples
   - Consider adding metadata for author roles (author, narrator, translator)
   - Add series-context boosting for author matching

5. **Transliteration Enhancements**:
   - Add specialized Japanese name transliteration
   - Consider using name-specific dictionaries
   - Add context-aware transliteration
""")

def main():
    """Run all analyses"""
    print("🔬 Deep Analysis of New Author Samples")
    print("=" * 50)
    
    analyze_ryuto_sample()
    print()
    analyze_kanji_transliteration()
    print()
    analyze_pen_names()
    print()
    check_sample_data_quality()
    print()
    suggest_improvements()
    
    print("\n✅ Analysis completed!")

if __name__ == "__main__":
    main()
