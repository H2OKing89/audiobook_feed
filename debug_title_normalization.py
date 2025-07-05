#!/usr/bin/env python3
"""Debug title normalization"""

import sys
import os
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def debug_title_normalization():
    """Debug title normalization step by step"""
    
    title = 'He Who Fights with Monsters 12: A LitRPG Adventure'
    series = 'He Who Fights with Monsters'
    
    print(f"Title: '{title}'")
    print(f"Series: '{series}'")
    
    normalized = title.strip()
    print(f"1. Start: '{normalized}'")
    
    # Volume patterns
    volume_patterns = [
        r'vol\.?\s*(\d+(?:\.\d+)?)',
        r'volume\s*(\d+(?:\.\d+)?)',
        r'book\s*(\d+(?:\.\d+)?)',
        r'part\s*(\d+(?:\.\d+)?)',
        r'chapter\s*(\d+(?:\.\d+)?)',
        r'#(\d+(?:\.\d+)?)',
        r'-\s*(\d+(?:\.\d+)?)(?:\s|$)',
        r'\((\d+(?:\.\d+)?)\)',
        r':\s*(\d+(?:\.\d+)?)(?:\s|$)',
        r'\s+(\d+)(?:\s|$)',
        r'(?:^|\s)(\d+)(?:\s|$)',
    ]
    
    # Remove volume indicators first
    for pattern in volume_patterns:
        matches = re.findall(pattern, normalized, flags=re.IGNORECASE)
        if matches:
            print(f"  Pattern '{pattern}' matches: {matches}")
            temp = re.sub(pattern, '', normalized, flags=re.IGNORECASE).strip()
            print(f"  After removal: '{temp}'")
            if temp and len(temp) >= 3:
                normalized = temp
                print(f"  Applied: '{normalized}'")
                break
    
    print(f"2. After volume removal: '{normalized}'")
    
    # Remove series
    if series:
        pattern = r'\b' + re.escape(series) + r'\b'
        print(f"3. Series pattern: '{pattern}'")
        temp = re.sub(pattern, '', normalized, flags=re.IGNORECASE).strip()
        print(f"4. After series removal: '{temp}'")
        if temp and len(temp) > 1:
            normalized = temp
        elif not temp.strip():
            normalized = ""
        
        # Clean up punctuation after series removal
        normalized = re.sub(r'^[,:\-\s]+', '', normalized)
        normalized = re.sub(r'[,:\-\s]+$', '', normalized)
        print(f"5. After cleanup: '{normalized}'")
    
    print(f"Final result: '{normalized}'")
    print(f"Expected: 'A LitRPG Adventure'")

if __name__ == "__main__":
    debug_title_normalization()
