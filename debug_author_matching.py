#!/usr/bin/env python3
"""
Debug the universal author matching system
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from audiostracker.author_matching import AuthorMatcher

def debug_basic_matching():
    """Debug basic author matching"""
    print("=== Debug Basic Author Matching ===")
    
    matcher = AuthorMatcher()
    
    # Test cases with detailed output
    test_cases = [
        ("John Smith", "John Smith"),
        ("John Smith", "john smith"),
        ("John Smith", "John Smith - Author"),
        ("John Smith (Author)", "John Smith"),
        ("John Smith", "Smith, John"),
    ]
    
    for author1, author2 in test_cases:
        result = matcher.authors_match(author1, author2)
        print(f"Match '{author1}' vs '{author2}': {result}")
        
        # Show the variants generated
        variants1 = matcher.detect_name_variants(author1)
        variants2 = matcher.detect_name_variants(author2)
        print(f"  Variants for '{author1}': {variants1}")
        print(f"  Variants for '{author2}': {variants2}")
        
        # Show normalized versions
        norm1 = matcher.normalize_author_name(author1)
        norm2 = matcher.normalize_author_name(author2)
        print(f"  Normalized '{author1}': '{norm1}'")
        print(f"  Normalized '{author2}': '{norm2}'")
        print()

if __name__ == "__main__":
    debug_basic_matching()
