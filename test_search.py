#!/usr/bin/env python3

import sys
import os

# Add the audiostracker directory to the Python path
audiostracker_path = os.path.join(os.path.dirname(__file__), 'src', 'audiostracker')
sys.path.insert(0, audiostracker_path)
sys.path.insert(0, os.path.dirname(audiostracker_path))

# Change to the audiostracker directory to avoid relative import issues
os.chdir(audiostracker_path)

try:
    print("Testing Python search functionality...")
    
    # Import the audible module
    import audible
    print("✓ Successfully imported audible module")
    
    # Test search for "Shirtaloon"
    print("\nSearching for 'Shirtaloon' as author...")
    results = audible.search_audible('Shirtaloon', search_field='author')
    print(f"Found {len(results)} results")
    
    if results:
        print("\nFirst few results:")
        for i, book in enumerate(results[:5]):
            print(f"{i+1}. '{book.get('title', 'Unknown Title')}' by {book.get('author', 'Unknown Author')}")
            if book.get('series'):
                print(f"   Series: {book.get('series')}")
    else:
        print("No results found for Shirtaloon")
        
    # Test search for "Brandon Sanderson" as a known author
    print("\nTesting with a known author 'Brandon Sanderson'...")
    results2 = audible.search_audible('Brandon Sanderson', search_field='author')
    print(f"Found {len(results2)} results for Brandon Sanderson")
    
    if results2:
        print("\nFirst few results:")
        for i, book in enumerate(results2[:3]):
            print(f"{i+1}. '{book.get('title', 'Unknown Title')}' by {book.get('author', 'Unknown Author')}")
    
except Exception as e:
    import traceback
    print(f"❌ Error: {e}")
    print("Full traceback:")
    print(traceback.format_exc())
