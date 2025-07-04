#!/usr/bin/env python3
"""
AudioStacker Web UI - FastAPI Application
A modern, modular web interface for managing audiobook collections.
"""

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, field_validator
import os
import shutil
from datetime import datetime
import yaml
import sqlite3
import sys

# Add the parent directory to the path so we can import from audiostracker
sys.path.append(str(Path(__file__).parent.parent))
from database import get_connection, init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AudioStacker Web UI",
    description="A modern web interface for managing audiobook collections",
    version="1.0.0"
)

# Paths
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
CONFIG_DIR = BASE_DIR.parent / "config"
AUDIOBOOKS_FILE = CONFIG_DIR / "audiobooks.json"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

# Load configuration
def load_config() -> dict:
    """Load configuration from config.yaml"""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {CONFIG_FILE}")
                return config
        else:
            logger.warning(f"Config file not found: {CONFIG_FILE}")
            return {}
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}

# Load config
config = load_config()
web_config = config.get('web_ui', {})

# Web UI configuration with defaults
WEB_HOST = web_config.get('host', '127.0.0.1')
WEB_PORT = web_config.get('port', 5005)
WEB_RELOAD = web_config.get('reload', True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Pydantic models for data validation
class Audiobook(BaseModel):
    title: str = ""
    series: str = ""
    publisher: str = ""
    narrator: List[str] = []

    @field_validator('narrator', mode='before')
    @classmethod
    def ensure_narrator_list(cls, v):
        if isinstance(v, str):
            return [v] if v else []
        return v or []

class AuthorBooks(BaseModel):
    books: List[Audiobook]

class AudiobookCollection(BaseModel):
    audiobooks: Dict[str, Dict[str, List[Audiobook]]]

# Data management functions
def load_audiobooks() -> dict:
    """Load audiobooks data from JSON file"""
    try:
        if AUDIOBOOKS_FILE.exists():
            with open(AUDIOBOOKS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loaded audiobooks data from {AUDIOBOOKS_FILE}")
                return data
        else:
            logger.warning(f"Audiobooks file not found: {AUDIOBOOKS_FILE}")
            return {"audiobooks": {"author": {}}}
    except Exception as e:
        logger.error(f"Error loading audiobooks: {e}")
        return {"audiobooks": {"author": {}}}

def save_audiobooks(data: dict) -> bool:
    """Save audiobooks data to JSON file with backup"""
    try:
        # Create backup
        if AUDIOBOOKS_FILE.exists():
            backup_path = AUDIOBOOKS_FILE.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            shutil.copy2(AUDIOBOOKS_FILE, backup_path)
            logger.info(f"Created backup: {backup_path}")
        
        # Ensure directory exists
        AUDIOBOOKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Save data
        with open(AUDIOBOOKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved audiobooks data to {AUDIOBOOKS_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error saving audiobooks: {e}")
        return False

def get_stats(data: dict) -> dict:
    """Calculate collection statistics for configuration"""
    authors = data.get("audiobooks", {}).get("author", {})
    total_books = sum(len(books) for books in authors.values())
    total_authors = len(authors)
    
    # Calculate publisher and narrator stats for reference
    all_publishers = set()
    all_narrators = set()
    
    for author_books in authors.values():
        for book in author_books:
            if book.get("publisher"):
                all_publishers.add(book["publisher"])
            if book.get("narrator"):
                for narrator in book["narrator"]:
                    if narrator.strip():
                        all_narrators.add(narrator.strip())
    
    return {
        "total_books": total_books,
        "total_authors": total_authors,
        "total_publishers": len(all_publishers),
        "total_narrators": len(all_narrators),
        "publishers": sorted(list(all_publishers)),
        "narrators": sorted(list(all_narrators))
    }

def get_upcoming_audiobooks() -> List[dict]:
    """Get upcoming audiobooks from the database"""
    try:
        # Initialize database if it doesn't exist
        init_db()
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT asin, title, author, narrator, publisher, series, series_number, 
                       release_date, link, image_url, merchandising_summary, publisher_name,
                       last_checked, notified_channels
                FROM audiobooks 
                WHERE release_date >= date('now')
                ORDER BY release_date ASC, author ASC, series ASC, series_number ASC
            """)
            
            audiobooks = []
            for row in cursor.fetchall():
                audiobook = {
                    "asin": row["asin"],
                    "title": row["title"],
                    "author": row["author"],
                    "narrator": row["narrator"],
                    "publisher": row["publisher"],
                    "series": row["series"],
                    "series_number": row["series_number"],
                    "release_date": row["release_date"],
                    "link": row["link"],
                    "image_url": row["image_url"],
                    "merchandising_summary": row["merchandising_summary"],
                    "publisher_name": row["publisher_name"],
                    "last_checked": row["last_checked"],
                    "notified_channels": json.loads(row["notified_channels"]) if row["notified_channels"] else {}
                }
                audiobooks.append(audiobook)
            
            return audiobooks
    except Exception as e:
        logger.error(f"Error getting upcoming audiobooks: {e}")
        return []

def get_database_stats() -> dict:
    """Get statistics from the database"""
    try:
        init_db()
        
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Total upcoming books
            cursor.execute("SELECT COUNT(*) FROM audiobooks WHERE release_date >= date('now')")
            upcoming_books = cursor.fetchone()[0]
            
            # Total authors
            cursor.execute("SELECT COUNT(DISTINCT author) FROM audiobooks WHERE release_date >= date('now')")
            total_authors = cursor.fetchone()[0]
            
            # Total publishers
            cursor.execute("SELECT COUNT(DISTINCT publisher) FROM audiobooks WHERE release_date >= date('now')")
            total_publishers = cursor.fetchone()[0]
            
            # Books by month
            cursor.execute("""
                SELECT strftime('%Y-%m', release_date) as month, COUNT(*) as count
                FROM audiobooks 
                WHERE release_date >= date('now')
                GROUP BY strftime('%Y-%m', release_date)
                ORDER BY month
                LIMIT 12
            """)
            monthly_releases = [{"month": row[0], "count": row[1]} for row in cursor.fetchall()]
            
            # Recent additions (books added to DB in last 7 days)
            cursor.execute("""
                SELECT COUNT(*) FROM audiobooks 
                WHERE last_checked >= datetime('now', '-7 days')
            """)
            recent_additions = cursor.fetchone()[0]
            
            return {
                "upcoming_books": upcoming_books,
                "total_authors": total_authors,
                "total_publishers": total_publishers,
                "monthly_releases": monthly_releases,
                "recent_additions": recent_additions
            }
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {
            "upcoming_books": 0,
            "total_authors": 0,
            "total_publishers": 0,
            "monthly_releases": [],
            "recent_additions": 0
        }

# API Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main page with upcoming audiobooks from database"""
    upcoming_audiobooks = get_upcoming_audiobooks()
    stats = get_database_stats()
    return templates.TemplateResponse("upcoming.html", {
        "request": request,
        "upcoming_audiobooks": upcoming_audiobooks,
        "stats": stats
    })

@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """Configuration page for managing JSON watchlist"""
    data = load_audiobooks()
    stats = get_stats(data)
    return templates.TemplateResponse("config.html", {
        "request": request,
        "audiobooks": data,
        "stats": stats
    })

@app.get("/api/upcoming")
async def get_upcoming():
    """Get upcoming audiobooks from database"""
    return get_upcoming_audiobooks()

@app.get("/api/database/stats")
async def get_database_stats_api():
    """Get database statistics"""
    return get_database_stats()

@app.get("/api/audiobooks")
async def get_audiobooks():
    """Get all audiobooks data"""
    data = load_audiobooks()
    stats = get_stats(data)
    return {"data": data, "stats": stats}

@app.post("/api/audiobooks")
async def save_audiobooks_api(audiobooks: dict):
    """Save audiobooks data"""
    try:
        # Validate the structure
        if "audiobooks" not in audiobooks or "author" not in audiobooks["audiobooks"]:
            raise HTTPException(status_code=400, detail="Invalid audiobook data structure")
        
        if save_audiobooks(audiobooks):
            stats = get_stats(audiobooks)
            return {"success": True, "message": "Audiobooks saved successfully", "stats": stats}
        else:
            raise HTTPException(status_code=500, detail="Failed to save audiobooks")
    except Exception as e:
        logger.error(f"Error in save_audiobooks_api: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/authors")
async def add_author(author_name: str = Form(...)):
    """Add a new author"""
    try:
        data = load_audiobooks()
        authors = data["audiobooks"]["author"]
        
        if author_name in authors:
            raise HTTPException(status_code=400, detail="Author already exists")
        
        authors[author_name] = []
        
        if save_audiobooks(data):
            return {"success": True, "message": f"Author '{author_name}' added successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save changes")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding author: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/authors/{author_name}")
async def delete_author(author_name: str):
    """Delete an author and all their books"""
    try:
        data = load_audiobooks()
        authors = data["audiobooks"]["author"]
        
        if author_name not in authors:
            raise HTTPException(status_code=404, detail="Author not found")
        
        del authors[author_name]
        
        if save_audiobooks(data):
            return {"success": True, "message": f"Author '{author_name}' deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save changes")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting author: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/authors/{author_name}/books")
async def add_book(author_name: str, book: Audiobook):
    """Add a book to an author"""
    try:
        data = load_audiobooks()
        authors = data["audiobooks"]["author"]
        
        if author_name not in authors:
            authors[author_name] = []
        
        book_dict = book.dict()
        authors[author_name].append(book_dict)
        
        if save_audiobooks(data):
            return {"success": True, "message": f"Book added to {author_name}", "book": book_dict}
        else:
            raise HTTPException(status_code=500, detail="Failed to save changes")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding book: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/authors/{author_name}/books/{book_index}")
async def update_book(author_name: str, book_index: int, book: Audiobook):
    """Update a specific book"""
    try:
        data = load_audiobooks()
        authors = data["audiobooks"]["author"]
        
        if author_name not in authors:
            raise HTTPException(status_code=404, detail="Author not found")
        
        if book_index >= len(authors[author_name]):
            raise HTTPException(status_code=404, detail="Book not found")
        
        book_dict = book.dict()
        authors[author_name][book_index] = book_dict
        
        if save_audiobooks(data):
            return {"success": True, "message": "Book updated successfully", "book": book_dict}
        else:
            raise HTTPException(status_code=500, detail="Failed to save changes")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating book: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/authors/{author_name}/books/{book_index}")
async def delete_book(author_name: str, book_index: int):
    """Delete a specific book"""
    try:
        data = load_audiobooks()
        authors = data["audiobooks"]["author"]
        
        if author_name not in authors:
            raise HTTPException(status_code=404, detail="Author not found")
        
        if book_index >= len(authors[author_name]):
            raise HTTPException(status_code=404, detail="Book not found")
        
        deleted_book = authors[author_name].pop(book_index)
        
        if save_audiobooks(data):
            return {"success": True, "message": "Book deleted successfully", "deleted_book": deleted_book}
        else:
            raise HTTPException(status_code=500, detail="Failed to save changes")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting book: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_collection_stats():
    """Get collection statistics"""
    data = load_audiobooks()
    stats = get_stats(data)
    return stats

@app.post("/api/export")
async def export_collection():
    """Export the current collection as JSON file"""
    try:
        data = load_audiobooks()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"audiobooks_export_{timestamp}.json"
        json_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        return StreamingResponse(
            iter([json_bytes]),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        logger.error(f"Error exporting collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/import")
async def import_collection(import_data: dict):
    """Import audiobook collection data"""
    try:
        # Validate structure
        if "audiobooks" not in import_data or "author" not in import_data["audiobooks"]:
            raise HTTPException(status_code=400, detail="Invalid import data structure")
        
        # Create backup before import
        current_data = load_audiobooks()
        backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = AUDIOBOOKS_FILE.with_suffix(f'.pre_import_backup_{backup_timestamp}.json')
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, indent=2, ensure_ascii=False)
        
        # Save imported data
        if save_audiobooks(import_data):
            stats = get_stats(import_data)
            return {
                "success": True,
                "message": "Collection imported successfully",
                "stats": stats,
                "backup_created": str(backup_path)
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save imported data")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting AudioStacker Web UI on {WEB_HOST}:{WEB_PORT}")
    logger.info(f"Configuration loaded from {CONFIG_FILE}")
    logger.info(f"Reload mode: {WEB_RELOAD}")
    
    uvicorn.run(
        "app:app",  # Use string import for proper reload support
        host=WEB_HOST,
        port=WEB_PORT,
        reload=WEB_RELOAD,
        log_level="info"
    )
