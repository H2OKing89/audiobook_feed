-- SQL script to create watchlist table in SQLite database
CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_name TEXT NOT NULL,
    title TEXT DEFAULT '',
    series TEXT DEFAULT '',
    publisher TEXT DEFAULT '',
    narrator TEXT DEFAULT '',
    active INTEGER DEFAULT 1,
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_checked TIMESTAMP NULL
);
