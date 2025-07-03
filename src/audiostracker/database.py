import sqlite3
from contextlib import closing
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

DB_FILE = os.path.join(os.path.dirname(__file__), 'audiobooks.db')

def get_connection():
    """
    Get a connection to the SQLite database with improved settings for reliability.
    
    Returns:
        sqlite3.Connection: A connection to the SQLite database
    """
    conn = sqlite3.connect(DB_FILE, timeout=30)  # Add timeout to handle busy database
    
    # Set pragmas for better performance and reliability
    conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging for better concurrency
    conn.execute("PRAGMA synchronous = NORMAL")  # Balance between safety and speed
    conn.execute("PRAGMA foreign_keys = ON")  # Enforce foreign key constraints
    
    # Enable extended error codes for better diagnostics
    conn.execute("PRAGMA locking_mode = NORMAL")
    
    # Have SQLite return Row objects
    conn.row_factory = sqlite3.Row
    
    return conn

def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        
        # Existing audiobooks table
        c.execute('''
            CREATE TABLE IF NOT EXISTS audiobooks (
                asin TEXT PRIMARY KEY,
                title TEXT,
                author TEXT,
                narrator TEXT,
                publisher TEXT,
                series TEXT,
                series_number TEXT,
                release_date TEXT,
                last_checked TIMESTAMP,
                notified_channels TEXT DEFAULT '{}' -- JSON string for channel tracking
            )
        ''')
        
        # New watchlist table to replace audiobooks.yaml
        c.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_name TEXT NOT NULL,
                title_filter TEXT,
                series_filter TEXT,
                publisher_filter TEXT,
                narrator_filter TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active BOOLEAN DEFAULT 1,
                UNIQUE(author_name, title_filter, series_filter)
            )
        ''')
        
        # Add indexes for better performance
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_watchlist_author 
            ON watchlist(author_name)
        ''')
        
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_watchlist_active 
            ON watchlist(active)
        ''')
        
        # Migrate existing notified column to notified_channels if needed
        try:
            c.execute("SELECT notified FROM audiobooks LIMIT 1")
            # If this succeeds, we have the old schema - migrate it
            c.execute("ALTER TABLE audiobooks ADD COLUMN notified_channels_temp TEXT DEFAULT '{}'")
            c.execute("""
                UPDATE audiobooks 
                SET notified_channels_temp = CASE 
                    WHEN notified = 1 THEN '{"legacy": true}' 
                    ELSE '{}' 
                END
            """)
            c.execute("ALTER TABLE audiobooks DROP COLUMN notified")
            c.execute("ALTER TABLE audiobooks RENAME COLUMN notified_channels_temp TO notified_channels")
            logging.info("Migrated database schema from notified to notified_channels")
        except sqlite3.OperationalError:
            # Column doesn't exist, we're already on new schema
            pass
        
        conn.commit()

def insert_or_update_audiobook(asin, title, author, narrator, publisher, series, series_number, release_date, notified_channels=None):
    if notified_channels is None:
        notified_channels = {}
    
    notified_channels_json = json.dumps(notified_channels)
    
    with get_connection() as conn:
        c = conn.cursor()
        
        # Check if the audiobook already exists
        c.execute('SELECT asin FROM audiobooks WHERE asin=?', (asin,))
        exists = c.fetchone() is not None
        
        c.execute('''
            INSERT INTO audiobooks (asin, title, author, narrator, publisher, series, series_number, release_date, last_checked, notified_channels)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
            ON CONFLICT(asin) DO UPDATE SET
                title=excluded.title,
                author=excluded.author,
                narrator=excluded.narrator,
                publisher=excluded.publisher,
                series=excluded.series,
                series_number=excluded.series_number,
                release_date=excluded.release_date,
                last_checked=datetime('now')
                -- Don't overwrite notified_channels on update
        ''', (asin, title, author, narrator, publisher, series, series_number, release_date, notified_channels_json))
        conn.commit()
        
        # Return True if this was a new insertion, False if it was an update
        return not exists

def is_notified_for_channel(asin: str, channel: str) -> bool:
    """Check if an audiobook has been notified for a specific channel"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT notified_channels FROM audiobooks WHERE asin=?', (asin,))
        row = c.fetchone()
        if not row or not row[0]:
            return False
        
        try:
            notified_channels = json.loads(row[0])
            return notified_channels.get(channel, False)
        except (json.JSONDecodeError, AttributeError):
            return False

def mark_notified_for_channel(asin: str, channel: str):
    """Mark an audiobook as notified for a specific channel"""
    with get_connection() as conn:
        c = conn.cursor()
        # Get current notified_channels
        c.execute('SELECT notified_channels FROM audiobooks WHERE asin=?', (asin,))
        row = c.fetchone()
        
        if row and row[0]:
            try:
                notified_channels = json.loads(row[0])
            except json.JSONDecodeError:
                notified_channels = {}
        else:
            notified_channels = {}
        
        notified_channels[channel] = True
        
        c.execute(
            'UPDATE audiobooks SET notified_channels=? WHERE asin=?',
            (json.dumps(notified_channels), asin)
        )
        conn.commit()

def get_unnotified_for_channel(channel: str) -> List[Dict]:
    """Get all audiobooks that haven't been notified for a specific channel"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM audiobooks')
        rows = c.fetchall()
        columns = [desc[0] for desc in c.description]
        
        unnotified = []
        for row in rows:
            audiobook = dict(zip(columns, row))
            try:
                notified_channels = json.loads(audiobook.get('notified_channels', '{}'))
                if not notified_channels.get(channel, False):
                    audiobook['notified_channels'] = notified_channels
                    unnotified.append(audiobook)
            except json.JSONDecodeError:
                # If JSON parsing fails, treat as unnotified
                audiobook['notified_channels'] = {}
                unnotified.append(audiobook)
        
        return unnotified

def prune_old_entries(days=90):
    """Delete entries older than `days` and already notified."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM audiobooks WHERE json_extract(notified_channels, '$') != '{}' AND release_date < ?", (cutoff,))
        conn.commit()

def prune_released(grace_period_days: int = 0):
    """
    Delete audiobooks whose release date has passed.
    
    Args:
        grace_period_days: Number of days to keep audiobooks after their release date (0 = remove on release day)
    
    Returns:
        int: Number of deleted records
        
    This function removes audiobooks from the database when they've been released.
    With grace_period_days=0, books are removed on their exact release date.
    With grace_period_days>0, books are kept for that many days after release.
    """
    today = datetime.now().date()
    cutoff_date = today - timedelta(days=grace_period_days)
    
    # First, get info about what will be deleted for logging
    deleted_books = []
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT asin, title, author, release_date FROM audiobooks 
            WHERE date(release_date) <= ? 
            ORDER BY release_date
        ''', (cutoff_date.isoformat(),))
        
        deleted_books = [dict(zip(("asin", "title", "author", "release_date"), row)) for row in c.fetchall()]
    
    # Now perform the deletion
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM audiobooks WHERE date(release_date) <= ?', (cutoff_date.isoformat(),))
        deleted_count = c.rowcount
        conn.commit()
    
    # Log details about what was removed
    if deleted_count > 0:
        logging.info(f"Removed {deleted_count} released audiobooks with cutoff date {cutoff_date}")
        for book in deleted_books:
            logging.debug(f"Removed released book: {book['title']} by {book['author']} (Released: {book['release_date']})")
    
    return deleted_count

def vacuum_db():
    """
    Optimize the database by rebuilding it completely.
    
    VACUUM rebuilds the entire database to defragment it and reclaim unused space.
    This should be run periodically, especially after deleting many records.
    """
    logging.info("Running database VACUUM operation to optimize storage")
    vacuum_start = time.time()
    
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute('VACUUM')
            conn.commit()
            
        vacuum_time = time.time() - vacuum_start
        logging.info(f"Database VACUUM completed successfully in {vacuum_time:.2f} seconds")
        return True
    except Exception as e:
        logging.error(f"Database VACUUM failed: {e}")
        return False

# Watchlist management functions
def get_watchlist():
    """Get all active watchlist entries"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT id, author_name, title_filter, series_filter, 
                   publisher_filter, narrator_filter, created_at, updated_at
            FROM watchlist 
            WHERE active = 1 
            ORDER BY author_name, title_filter
        ''')
        return [dict(row) for row in c.fetchall()]

def add_watchlist_entry(author_name, title_filter=None, series_filter=None, 
                       publisher_filter=None, narrator_filter=None):
    """Add a new watchlist entry"""
    with get_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('''
                INSERT INTO watchlist (author_name, title_filter, series_filter, 
                                     publisher_filter, narrator_filter, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (author_name, title_filter, series_filter, publisher_filter, narrator_filter))
            return c.lastrowid
        except sqlite3.IntegrityError:
            # Entry already exists, update it instead
            c.execute('''
                UPDATE watchlist 
                SET publisher_filter = ?, narrator_filter = ?, 
                    updated_at = CURRENT_TIMESTAMP, active = 1
                WHERE author_name = ? AND title_filter = ? AND series_filter = ?
            ''', (publisher_filter, narrator_filter, author_name, title_filter, series_filter))
            return None

def update_watchlist_entry(entry_id, author_name=None, title_filter=None, 
                          series_filter=None, publisher_filter=None, narrator_filter=None):
    """Update an existing watchlist entry"""
    with get_connection() as conn:
        c = conn.cursor()
        # Build dynamic update query
        updates = []
        values = []
        
        if author_name is not None:
            updates.append("author_name = ?")
            values.append(author_name)
        if title_filter is not None:
            updates.append("title_filter = ?")
            values.append(title_filter)
        if series_filter is not None:
            updates.append("series_filter = ?")
            values.append(series_filter)
        if publisher_filter is not None:
            updates.append("publisher_filter = ?")
            values.append(publisher_filter)
        if narrator_filter is not None:
            updates.append("narrator_filter = ?")
            values.append(narrator_filter)
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(entry_id)
            query = f"UPDATE watchlist SET {', '.join(updates)} WHERE id = ?"
            c.execute(query, values)
            return c.rowcount > 0
        return False

def delete_watchlist_entry(entry_id):
    """Delete (deactivate) a watchlist entry"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''
            UPDATE watchlist 
            SET active = 0, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (entry_id,))
        return c.rowcount > 0

def update_watchlist_entry_by_author(author_name, title_filter=None, series_filter=None, 
                              publisher_filter=None, narrator_filter=None):
    """
    Update watchlist entry by author name.
    
    Args:
        author_name (str): Author name to update
        title_filter (str, optional): Title filter. Defaults to None.
        series_filter (str, optional): Series filter. Defaults to None.
        publisher_filter (str, optional): Publisher filter. Defaults to None.
        narrator_filter (str, optional): Narrator filter. Defaults to None.
    
    Returns:
        bool: True if updated successfully
    """
    if not author_name:
        return False
    
    with get_connection() as conn:
        c = conn.cursor()
        
        # Check if the entry exists
        c.execute('SELECT id FROM watchlist WHERE author_name=?', (author_name,))
        row = c.fetchone()
        
        if not row:
            # If entry doesn't exist, add it
            return add_watchlist_entry(author_name, title_filter, series_filter, publisher_filter, narrator_filter)
        
        # If it exists, update it
        entry_id = row[0]
        return update_watchlist_entry(entry_id, author_name, title_filter, series_filter, publisher_filter, narrator_filter)

def delete_watchlist_entry_by_author(author_name):
    """
    Delete ALL watchlist entries for a given author name.
    
    Args:
        author_name (str): Author name to delete
    
    Returns:
        bool: True if one or more entries were deleted successfully
    """
    if not author_name:
        return False
    
    with get_connection() as conn:
        c = conn.cursor()
        
        # Delete all active entries for this author
        c.execute('''
            UPDATE watchlist 
            SET active = 0, updated_at = CURRENT_TIMESTAMP 
            WHERE author_name = ? AND active = 1
        ''', (author_name,))
        
        # Return True if at least one row was affected
        return c.rowcount > 0

def convert_watchlist_to_yaml_format():
    """Convert database watchlist to the old YAML format for backward compatibility"""
    watchlist = get_watchlist()
    result = {"audiobooks": {"author": {}}}
    
    for entry in watchlist:
        author = entry['author_name']
        if author not in result["audiobooks"]["author"]:
            result["audiobooks"]["author"][author] = []
        
        book_entry = {}
        if entry['title_filter']:
            book_entry['title'] = entry['title_filter']
        if entry['series_filter']:
            book_entry['series'] = entry['series_filter']
        if entry['publisher_filter'] and isinstance(entry['publisher_filter'], str):
            book_entry['publisher'] = entry['publisher_filter']
        if entry['narrator_filter'] and isinstance(entry['narrator_filter'], str):
            # Handle both single narrator and list
            if ',' in entry['narrator_filter']:
                book_entry['narrator'] = [n.strip() for n in entry['narrator_filter'].split(',')]
            else:
                book_entry['narrator'] = entry['narrator_filter']
        
        # If no specific filters, add a generic "Any" entry
        if not book_entry:
            book_entry['title'] = 'Any'
        
        result["audiobooks"]["author"][author].append(book_entry)
    
    return result

def check_author_exists(author_name):
    """
    Check if an author already exists in the watchlist.
    
    Args:
        author_name (str): Author name to check
    
    Returns:
        dict: Dictionary containing existence info and existing entries
    """
    if not author_name:
        return {"exists": False, "entries": [], "count": 0}
    
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT id, author_name, title_filter, series_filter, 
                   publisher_filter, narrator_filter, created_at, updated_at
            FROM watchlist 
            WHERE author_name = ? AND active = 1
            ORDER BY created_at
        ''', (author_name,))
        
        try:
            entries = [dict(row) for row in c.fetchall()]
        except Exception as e:
            logging.error(f"Error processing author entries: {e}")
            entries = []
        
        return {
            "exists": len(entries) > 0,
            "entries": entries,
            "count": len(entries)
        }

def get_author_criteria_summary(author_name):
    """
    Get a summary of all criteria for an existing author.
    
    Args:
        author_name (str): Author name to summarize
    
    Returns:
        dict: Summary of all criteria for the author, or None if author doesn't exist
    """
    check_result = check_author_exists(author_name)
    if not check_result["exists"]:
        return None
    
    # Combine all criteria from all entries
    combined_criteria = {
        "series": set(),
        "include": set(),
        "publisher": set(),
        "narrator": set()
    }
    
    entries = check_result.get("entries", [])
    # Ensure entries is iterable (list, not a primitive type)
    if not isinstance(entries, list):
        logging.warning(f"Expected list for entries, got {type(entries)}: {entries}")
        entries = []
        
    for entry in entries:
        # Make sure entry is a dict before accessing its properties
        if not isinstance(entry, dict):
            logging.warning(f"Expected dict for entry, got {type(entry)}: {entry}")
            continue
            
        if entry.get("title_filter") and isinstance(entry["title_filter"], str):
            combined_criteria["include"].update(entry["title_filter"].split(","))
        if entry.get("series_filter") and isinstance(entry["series_filter"], str):
            combined_criteria["series"].update(entry["series_filter"].split(","))
        if entry.get("publisher_filter") and isinstance(entry["publisher_filter"], str):
            combined_criteria["publisher"].update(entry["publisher_filter"].split(","))
        if entry.get("narrator_filter") and isinstance(entry["narrator_filter"], str):
            combined_criteria["narrator"].update(entry["narrator_filter"].split(","))
    
    # Convert sets to sorted lists and remove empty strings
    result = {}
    for key, value_set in combined_criteria.items():
        cleaned_list = sorted([v.strip() for v in value_set if v.strip()])
        if cleaned_list:
            result[key] = cleaned_list
    
    return result

def delete_audiobook_by_asin(asin):
    """
    Delete an audiobook from the database by its ASIN.
    
    Args:
        asin (str): The ASIN of the audiobook to delete
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            
            # First, get the book details for logging
            c.execute("SELECT title, author FROM audiobooks WHERE asin = ?", (asin,))
            book_info = c.fetchone()
            
            if book_info:
                title, author = book_info
                
                # Delete the book
                c.execute("DELETE FROM audiobooks WHERE asin = ?", (asin,))
                conn.commit()
                
                # Log the deletion
                logging.info(f"Deleted audiobook: '{title}' by {author} (ASIN: {asin})")
                return True
            else:
                logging.warning(f"Attempted to delete non-existent audiobook with ASIN: {asin}")
                return False
                
    except Exception as e:
        logging.error(f"Error deleting audiobook with ASIN {asin}: {e}")
        return False

def get_all_audiobooks(filter_type='all', limit=1000):
    """
    Get all audiobooks from the database with optional filtering.
    
    Args:
        filter_type (str): Filter type: 'all', 'upcoming', 'released', or 'recent'
        limit (int): Maximum number of records to return
        
    Returns:
        list: List of audiobooks as dictionaries
    """
    with get_connection() as conn:
        c = conn.cursor()
        
        today = datetime.now().date().isoformat()
        query = ""
        params = []
        
        if filter_type == 'upcoming':
            # Filter for books not yet released
            query = "SELECT * FROM audiobooks WHERE date(release_date) >= ? ORDER BY release_date ASC LIMIT ?"
            params = [today, limit]
        elif filter_type == 'released':
            # Filter for already released books
            query = "SELECT * FROM audiobooks WHERE date(release_date) < ? ORDER BY release_date DESC LIMIT ?"
            params = [today, limit]
        elif filter_type == 'recent':
            # Most recently added to database
            query = "SELECT * FROM audiobooks ORDER BY last_checked DESC LIMIT ?"
            params = [limit]
        else:  # 'all' or any other value
            # All books, sorted by release date (upcoming first)
            query = "SELECT * FROM audiobooks ORDER BY release_date ASC LIMIT ?"
            params = [limit]
        
        c.execute(query, params)
        
        # Convert rows to dictionaries
        columns = [desc[0] for desc in c.description]
        books = []
        
        for row in c.fetchall():
            book = dict(zip(columns, row))
            
            # Parse JSON fields
            if 'notified_channels' in book and book['notified_channels']:
                try:
                    book['notified_channels'] = json.loads(book['notified_channels'])
                except json.JSONDecodeError:
                    book['notified_channels'] = {}
            
            books.append(book)
        
        return books

def count_audiobooks():
    """
    Count total number of audiobooks in the database.
    
    Returns:
        int: Total number of audiobooks
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM audiobooks")
        return c.fetchone()[0]

def count_upcoming_audiobooks():
    """
    Count upcoming audiobooks (release date in the future).
    
    Returns:
        int: Number of upcoming audiobooks
    """
    today = datetime.now().date().isoformat()
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM audiobooks WHERE date(release_date) >= ?", (today,))
        return c.fetchone()[0]

def get_last_checked_time():
    """
    Get the most recent last_checked time from the database.
    
    Returns:
        str: Last checked time in ISO format, or current time if no records
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT MAX(last_checked) FROM audiobooks")
        last_checked = c.fetchone()[0]
        
        if last_checked:
            return last_checked
        
        # If no records found, return current time
        return datetime.now().isoformat()

# Example usage (in main.py or a test script):
if __name__ == "__main__":
    init_db()
    insert_or_update_audiobook(
        asin="B0123456",
        title="Cool Book",
        author="Joe Author",
        narrator="Cliff Kirk",
        publisher="MyPub",
        series="MySeries",
        series_number="1",
        release_date="2025-01-01"
    )
    print(f"Notified for pushover: {is_notified_for_channel('B0123456', 'pushover')}")
    mark_notified_for_channel("B0123456", "pushover")
    print(f"Notified for pushover after marking: {is_notified_for_channel('B0123456', 'pushover')}")
    prune_old_entries(90)
    deleted_count = prune_released()
    print(f"Deleted {deleted_count} released audiobooks.")
    vacuum_db()
