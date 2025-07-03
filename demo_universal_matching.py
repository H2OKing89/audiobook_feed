#!/usr/bin/env python3
"""
Demonstrate the universal author matching system with real examples
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from audiostracker.author_matching import AuthorMatcher
import json

def demonstrate_universal_matching():
    """Demonstrate the universal author matching system"""
    print("🌍 Universal Author Matching System Demo")
    print("=" * 50)
    
    # Create a fresh matcher instance
    matcher = AuthorMatcher()
    
    print("\n1. Basic Author Matching:")
    print("-" * 30)
    
    test_cases = [
        ("John Smith", "john smith"),
        ("John Smith", "Smith, John"),
        ("John Smith", "J. Smith"),
        ("John Smith - Author", "John Smith"),
        ("Fuse", "FUSE"),
        ("Fuse", "Short Fuse"),  # This should NOT match easily
    ]
    
    for author1, author2 in test_cases:
        result = matcher.authors_match(author1, author2)
        print(f"'{author1}' vs '{author2}': {result}")
    
    print("\n2. Japanese Name Transliteration:")
    print("-" * 30)
    
    # Test Japanese transliteration
    japanese_tests = [
        ("理不尽な孫の手", "Rifujin na Magonote"),
        ("鈴木", "Suzuki"),
        ("佐藤", "Sato"),
        ("田中", "Tanaka"),
        ("フューズ", "Fuse"),
    ]
    
    for japanese, romaji in japanese_tests:
        # Show transliteration variants
        variants = matcher.transliterate_name(japanese)
        print(f"'{japanese}' -> variants: {variants}")
        
        # Test matching
        result = matcher.authors_match(japanese, romaji)
        print(f"  Match with '{romaji}': {result}")
    
    print("\n3. Chinese Name Transliteration:")
    print("-" * 30)
    
    chinese_tests = [
        ("李明", "Li Ming"),
        ("王小明", "Wang Xiaoming"),
        ("张三", "Zhang San"),
    ]
    
    for chinese, pinyin in chinese_tests:
        variants = matcher.transliterate_name(chinese)
        print(f"'{chinese}' -> variants: {variants}")
        
        result = matcher.authors_match(chinese, pinyin)
        print(f"  Match with '{pinyin}': {result}")
    
    print("\n4. Cyrillic Name Transliteration:")
    print("-" * 30)
    
    cyrillic_tests = [
        ("Иван Иванов", "Ivan Ivanov"),
        ("Мария Петрова", "Maria Petrova"),
        ("Александр Пушкин", "Alexander Pushkin"),
    ]
    
    for cyrillic, latin in cyrillic_tests:
        variants = matcher.transliterate_name(cyrillic)
        print(f"'{cyrillic}' -> variants: {variants}")
        
        result = matcher.authors_match(cyrillic, latin)
        print(f"  Match with '{latin}': {result}")
    
    print("\n5. Learning from Real Data:")
    print("-" * 30)
    
    # Load real audiobook data
    sample_files = [
        "tests/audiobook_samples/Rifujin_na_Magonote_sample.json"
    ]
    
    audiobooks = []
    for file_path in sample_files:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                audiobooks.extend(data)
                print(f"Loaded {len(data)} books from {file_path}")
    
    if audiobooks:
        print(f"Learning from {len(audiobooks)} audiobooks...")
        matcher.learn_from_audiobook_data(audiobooks)
        
        # Test the learned aliases
        print("\nTesting learned aliases:")
        test_result = matcher.authors_match("理不尽な孫の手", "Rifujin na Magonote")
        print(f"'理不尽な孫の手' vs 'Rifujin na Magonote': {test_result}")
        
        # Check reverse matching
        test_result_reverse = matcher.authors_match("Rifujin na Magonote", "理不尽な孫の手")
        print(f"'Rifujin na Magonote' vs '理不尽な孫の手': {test_result_reverse}")
    
    print("\n6. Manual Alias Addition:")
    print("-" * 30)
    
    # Add some manual aliases
    matcher.add_author_alias("Rifujin na Magonote", "理不尽な孫の手")
    matcher.add_author_alias("Fuse", "フューズ")
    matcher.add_author_alias("Tappei Nagatsuki", "長月達平")
    
    print("Added manual aliases:")
    print("- Rifujin na Magonote ←→ 理不尽な孫の手")
    print("- Fuse ←→ フューズ")
    print("- Tappei Nagatsuki ←→ 長月達平")
    
    # Test the manual aliases
    manual_tests = [
        ("Rifujin na Magonote", "理不尽な孫の手"),
        ("Fuse", "フューズ"),
        ("Tappei Nagatsuki", "長月達平"),
    ]
    
    for canonical, alias in manual_tests:
        result = matcher.authors_match(canonical, alias)
        print(f"'{canonical}' vs '{alias}': {result}")
    
    print("\n7. System Statistics:")
    print("-" * 30)
    
    stats = matcher.get_matching_statistics()
    print(f"Total canonical authors: {stats['total_canonical_authors']}")
    print(f"Total aliases: {stats['total_aliases']}")
    print(f"Transliteration engines: {stats['transliteration_engines']}")
    print(f"Fuzzy matching: {stats['fuzzy_matching']}")
    
    print("\n8. User Feedback Example:")
    print("-" * 30)
    
    # Simulate user feedback
    print("User says: 'Short Fuse' and 'Fuse' are NOT the same author")
    matcher.add_user_feedback("Short Fuse", "Fuse", False)
    
    print("User says: 'J.K. Rowling' and 'Joanne Rowling' are the same author")
    matcher.add_user_feedback("J.K. Rowling", "Joanne Rowling", True)
    
    # Test the feedback
    result = matcher.authors_match("J.K. Rowling", "Joanne Rowling")
    print(f"'J.K. Rowling' vs 'Joanne Rowling': {result}")
    
    print("\n" + "=" * 50)
    print("🎉 Universal Author Matching Demo Complete!")
    print("\nKey Features Demonstrated:")
    print("✓ Multi-script transliteration (Japanese, Chinese, Cyrillic)")
    print("✓ Dynamic alias learning from real data")
    print("✓ Persistent alias storage")
    print("✓ User feedback integration")
    print("✓ Fast fuzzy matching with RapidFuzz")
    print("✓ Intelligent name variant detection")
    print("✓ Role/metadata filtering")

if __name__ == "__main__":
    demonstrate_universal_matching()
