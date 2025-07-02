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
        c.execute('CREATE INDEX IF NOT EXISTS idx_author ON audiobooks(author)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_series ON audiobooks(series, series_number)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_release ON audiobooks(release_date)')
        
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
    """Delete entries older than `days` and notified=1."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM audiobooks WHERE notified=1 AND release_date < ?', (cutoff,))
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
