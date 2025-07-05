#!/usr/bin/env python3
"""Debug series normalization in detail"""

import sys
import os
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def debug_series_normalization():
    """Debug series normalization step by step"""
    
    # Test series patterns
    series_suffixes = [
        r'\s+series$',  # Only remove "series" if it's at the end and preceded by space
        r'\s*\[.*edition\]$',  # [French edition], etc.
        r'\s*\(light novel\)$',
        r'\s*\(ln\)$',
        r'\s+collection$',
        r'\s+saga$',
    ]
    
    test_cases = [
        'Some Series',
        'Some Story Collection',
        'Epic Saga',
        'Some Series (Light Novel)',
        'Regular Series Name',
    ]
    
    for text in test_cases:
        print(f"\nTesting: '{text}'")
        normalized = text.strip()
        
        # Test each pattern
        for suffix_pattern in series_suffixes:
            if re.search(suffix_pattern, normalized, re.IGNORECASE):
                print(f"  Pattern '{suffix_pattern}' matches!")
                before = normalized
                normalized = re.sub(suffix_pattern, '', normalized, flags=re.IGNORECASE)
                print(f"  Before: '{before}' -> After: '{normalized}'")
                break
        
        # Clean up punctuation and whitespace
        normalized = re.sub(r'[,:\-_()]+', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = normalized.strip()
        
        print(f"  Final result: '{normalized}'")

if __name__ == "__main__":
    debug_series_normalization()
