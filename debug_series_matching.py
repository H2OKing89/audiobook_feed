#!/usr/bin/env python3
"""Debug series matching issue"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from audiostracker.title_series_matching import normalize_series, series_match

def debug_series_matching():
    """Debug the series matching issue"""
    s1 = 'Some Series'
    s2 = 'Some Series (Light Novel)'
    
    print(f"Original: '{s1}' vs '{s2}'")
    
    norm1 = normalize_series(s1)
    norm2 = normalize_series(s2)
    
    print(f"Normalized: '{norm1}' vs '{norm2}'")
    print(f"s1 in s2: {norm1.lower() in norm2.lower()}")
    print(f"s2 in s1: {norm2.lower() in norm1.lower()}")
    
    min_len = min(len(norm1), len(norm2))
    max_len = max(len(norm1), len(norm2))
    ratio = min_len / max_len
    print(f"Length ratio: {ratio} (need >= 0.6)")
    
    result = series_match(s1, s2)
    print(f"Final result: {result}")
    
    # Test the title normalization issues too
    print("\n=== Title Normalization Tests ===")
    
    test_cases = [
        ("Spice and Wolf, Vol. 14", "Spice and Wolf"),
        ("He Who Fights with Monsters 12: A LitRPG Adventure", "He Who Fights with Monsters"),
    ]
    
    for title, series in test_cases:
        from audiostracker.title_series_matching import normalize_title
        result = normalize_title(title, series)
        print(f"'{title}' -> '{result}' (removing series: '{series}')")

if __name__ == "__main__":
    debug_series_matching()
