#!/usr/bin/env python3
"""
Clean up sample data and improve kanji transliteration for author matching
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from audiostracker.author_matching import AuthorMatcher

def clean_ryuto_sample():
    """Clean up the Ryuto sample by removing the Mike Unwin entry"""
    print("🧹 Cleaning Ryuto Sample")
    print("=" * 30)
    
    filepath = Path("tests/audiobook_samples/Ryuto_sample.json")
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        return
    
    # Read the sample
    with open(filepath, 'r', encoding='utf-8') as f:
        books = json.load(f)
    
    print(f"Original books count: {len(books)}")
    
    # Filter out non-Ryuto books
    ryuto_books = [book for book in books if book.get('author') == 'Ryuto']
    
    print(f"Ryuto books count: {len(ryuto_books)}")
    
    # Save cleaned sample
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(ryuto_books, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Cleaned sample saved with {len(ryuto_books)} books")

def improve_kanji_transliteration():
    """Improve kanji transliteration by adding known mappings"""
    print("\n🌐 Improving Kanji Transliteration")
    print("=" * 40)
    
    # Create a mapping for known author names
    kanji_to_romaji = {
        '田中雄': 'Yuu Tanaka',
        '竜翔': 'Ryuto', 
        '白米良': 'Ryo Shirakome',
        '理不尽な孫の手': 'Rifujin na Magonote',
        # Add more mappings as needed
    }
    
    # Test the matcher
    matcher = AuthorMatcher()
    
    # Add these as learned aliases
    for kanji, romaji in kanji_to_romaji.items():
        print(f"Adding alias: '{kanji}' -> '{romaji}'")
        matcher.add_author_alias(romaji, kanji)
    
    # Test the improved matching
    print("\nTesting improved matching:")
    for kanji, expected_romaji in kanji_to_romaji.items():
        from audiostracker.author_matching import match_authors
        result = match_authors(kanji, expected_romaji)
        print(f"  '{kanji}' vs '{expected_romaji}': {result}")
    
    # Save the improved aliases
    matcher._save_aliases_cache()
    print("✅ Improved aliases saved")

def validate_all_samples():
    """Validate all sample files for data quality"""
    print("\n📋 Validating All Sample Files")
    print("=" * 40)
    
    samples_dir = Path("tests/audiobook_samples")
    
    for json_file in samples_dir.glob("*_sample.json"):
        print(f"\n📖 Validating {json_file.name}:")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                books = json.load(f)
            
            if not books:
                print(f"  ⚠️  Empty file")
                continue
            
            # Extract expected author from filename
            expected_author = json_file.stem.replace("_sample", "").replace("_", " ")
            
            # Check author consistency
            authors = set()
            for book in books:
                if 'author' in book and book['author']:
                    authors.add(book['author'])
            
            print(f"  Expected: '{expected_author}'")
            print(f"  Found: {list(authors)}")
            
            # Check for issues
            if len(authors) > 1:
                print(f"  ⚠️  Multiple authors found")
                
                # Check if expected author is in the list
                if expected_author in authors:
                    print(f"  ✅ Expected author found in list")
                else:
                    print(f"  ❌ Expected author not found")
                
                # Suggest cleaning
                main_author_books = [book for book in books if book.get('author') == expected_author]
                if main_author_books:
                    print(f"  💡 Suggest keeping {len(main_author_books)} books by '{expected_author}'")
            else:
                print(f"  ✅ Single author consistency")
                
        except Exception as e:
            print(f"  ❌ Error reading file: {e}")

def test_improved_matching():
    """Test the improved matching system"""
    print("\n🧪 Testing Improved Matching")
    print("=" * 40)
    
    # Test cases with the improvements
    test_cases = [
        ("田中雄", "Yuu Tanaka"),
        ("竜翔", "Ryuto"),
        ("白米良", "Ryo Shirakome"),
        ("理不尽な孫の手", "Rifujin na Magonote"),
        ("Sunsunsun", "サンサンサン"),
        ("TurtleMe", "turtle me"),
        ("Shirtaloon", "shirt a loon"),
    ]
    
    from audiostracker.author_matching import match_authors
    
    for name1, name2 in test_cases:
        result = match_authors(name1, name2)
        status = "✅" if result[0] else "❌"
        print(f"  {status} '{name1}' vs '{name2}': {result}")

def main():
    """Run all improvements and validations"""
    print("🔧 Cleaning and Improving Author Matching")
    print("=" * 50)
    
    clean_ryuto_sample()
    improve_kanji_transliteration()
    validate_all_samples()
    test_improved_matching()
    
    print("\n✅ All improvements completed!")

if __name__ == "__main__":
    main()
