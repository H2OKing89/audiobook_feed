#!/usr/bin/env python3
"""
Comprehensive demonstration of title and series matching with real audiobook data
"""

import sys
import os
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from audiostracker.title_series_matching import (
    TitleSeriesMatcher, normalize_title, normalize_series, 
    extract_volume_number, titles_match, series_match, match_audiobooks
)

def demonstrate_title_series_matching():
    """Demonstrate comprehensive title and series matching capabilities"""
    print("🎯 Comprehensive Title & Series Matching Demonstration")
    print("=" * 60)
    
    # Create matcher instance
    matcher = TitleSeriesMatcher()
    
    print("\n📚 1. Title Normalization Examples")
    print("-" * 40)
    
    title_examples = [
        ("Spice and Wolf, Vol. 14", "Spice and Wolf"),
        ("He Who Fights with Monsters 12: A LitRPG Adventure", "He Who Fights with Monsters"),
        ("Reincarnated as a Sword, Volume 11", None),
        ("Goblin Slayer Book 5 (Light Novel)", None),
        ("Alya Sometimes Hides Her Feelings in Russian, Vol. 4.5", "Alya Sometimes Hides Her Feelings in Russian"),
    ]
    
    for title, series in title_examples:
        normalized = normalize_title(title, series)
        volume = extract_volume_number(title)
        print(f"  📖 '{title}'")
        if series:
            print(f"      Series: '{series}'")
        print(f"      → Normalized: '{normalized}'")
        print(f"      → Volume: {volume}")
        print()
    
    print("\n📂 2. Series Normalization Examples")
    print("-" * 40)
    
    series_examples = [
        "Spice and Wolf",
        "Dungeon Crawler Carl [French edition]",
        "Rascal Does Not Dream (light novel)",
        "Some Story Collection",
        "He Who Fights with Monsters",
    ]
    
    for series in series_examples:
        normalized = normalize_series(series)
        print(f"  📚 '{series}' → '{normalized}'")
    
    print("\n🔍 3. Series Matching Examples")
    print("-" * 40)
    
    series_pairs = [
        ("Spice and Wolf", "Spice and Wolf"),
        ("Dungeon Crawler Carl", "Dungeon Crawler Carl [French edition]"),
        ("Some Series", "Some Series (Light Novel)"),
        ("He Who Fights with Monsters", "He Who Fights Monsters"),
        ("Completely Different", "Another Series"),
    ]
    
    for series1, series2 in series_pairs:
        match, similarity = series_match(series1, series2)
        status = "✅ MATCH" if match else "❌ NO MATCH"
        print(f"  {status} '{series1}' vs '{series2}' (sim: {similarity:.3f})")
    
    print("\n📖 4. Title Matching Examples")
    print("-" * 40)
    
    title_pairs = [
        ("Spice and Wolf, Vol. 14", "Spice and Wolf, Volume 14", "Spice and Wolf", "Spice and Wolf"),
        ("He Who Fights with Monsters 12", "He Who Fights with Monsters 11", "He Who Fights with Monsters", "He Who Fights with Monsters"),
        ("Mushoku Tensei: Jobless Reincarnation Vol. 5", "Jobless Reincarnation Vol. 5", "Mushoku Tensei", None),
        ("Completely Different Title", "Another Title Entirely", None, None),
    ]
    
    for title1, title2, series1, series2 in title_pairs:
        match, similarity = titles_match(title1, title2, 0.8, series1, series2)
        status = "✅ MATCH" if match else "❌ NO MATCH"
        print(f"  {status} '{title1}' vs '{title2}' (sim: {similarity:.3f})")
    
    print("\n🎯 5. Full Audiobook Matching")
    print("-" * 40)
    
    book_pairs = [
        (
            {"title": "Spice and Wolf, Vol. 14", "series": "Spice and Wolf", "author": "Isuna Hasekura"},
            {"title": "Spice and Wolf, Volume 14", "series": "Spice and Wolf", "author": "Isuna Hasekura"}
        ),
        (
            {"title": "He Who Fights with Monsters 12", "series": "He Who Fights with Monsters", "author": "Shirtaloon"},
            {"title": "He Who Fights with Monsters 11", "series": "He Who Fights with Monsters", "author": "Shirtaloon"}
        ),
        (
            {"title": "Goblin Slayer, Vol. 5", "series": "Goblin Slayer", "author": "Kumo Kagyu"},
            {"title": "Completely Different Book", "series": "Different Series", "author": "Other Author"}
        ),
    ]
    
    for book1, book2 in book_pairs:
        result = match_audiobooks(book1, book2)
        status = "✅ OVERALL MATCH" if result['overall_match'] else "❌ NO MATCH"
        print(f"  {status}")
        print(f"    Book 1: '{book1['title']}' ({book1['series']})")
        print(f"    Book 2: '{book2['title']}' ({book2['series']})")
        print(f"    Title match: {result['titles_match']} (sim: {result['title_similarity']:.3f})")
        print(f"    Series match: {result['series_match']} (sim: {result['series_similarity']:.3f})")
        print(f"    Volume 1: {result['volume1']}, Volume 2: {result['volume2']}")
        print()

def test_with_real_data():
    """Test with real audiobook sample data"""
    print("\n📊 6. Real Data Analysis")
    print("-" * 40)
    
    samples_dir = Path("tests/audiobook_samples")
    
    # Load real data from multiple authors
    all_books = []
    authors_data = {}
    
    sample_files = [
        "Isuna Hasekura_sample.json",
        "Hajime Kamoshida_sample.json", 
        "Kumo Kagyu_sample.json",
        "Shirtaloon_sample.json",
        "Matt Dinniman_sample.json",
    ]
    
    for filename in sample_files:
        filepath = samples_dir / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                books = json.load(f)
                # Filter books with complete data
                complete_books = [book for book in books if book.get('title') and book.get('series') and book.get('author')]
                all_books.extend(complete_books)
                
                author_name = filename.replace('_sample.json', '')
                authors_data[author_name] = complete_books
                print(f"  📚 {author_name}: {len(complete_books)} books")
    
    print(f"\n  Total books loaded: {len(all_books)}")
    
    # Create matcher and learn from the data
    matcher = TitleSeriesMatcher()
    matcher.learn_from_data(all_books)
    
    print(f"  Series aliases learned: {len(matcher.series_aliases)}")
    if matcher.series_aliases:
        print("  Sample aliases:")
        for canonical, alias in list(matcher.series_aliases.items())[:5]:
            print(f"    '{alias}' → '{canonical}'")
    
    # Test cross-series matching within authors
    print("\n  🔍 Cross-series matching test:")
    test_count = 0
    match_count = 0
    
    for author, books in authors_data.items():
        if len(books) < 2:
            continue
            
        # Test first few books against each other
        for i, book1 in enumerate(books[:3]):
            for book2 in books[i+1:i+3]:
                result = match_audiobooks(book1, book2)
                test_count += 1
                if result['overall_match']:
                    match_count += 1
                    print(f"    ✅ {author}: '{book1['title']}' ↔ '{book2['title']}'")
    
    print(f"  Found {match_count} matches out of {test_count} comparisons")

def main():
    """Run all demonstrations"""
    demonstrate_title_series_matching()
    test_with_real_data()
    
    print("\n🎉 Title & Series Matching System Demo Complete!")
    print("   The system can now handle:")
    print("   ✅ Volume number extraction and normalization")
    print("   ✅ Series name variations and aliases")
    print("   ✅ Title normalization with series removal")
    print("   ✅ Fuzzy matching for similar titles/series")
    print("   ✅ Learning from real audiobook data")
    print("   ✅ Comprehensive audiobook matching logic")

if __name__ == "__main__":
    main()
