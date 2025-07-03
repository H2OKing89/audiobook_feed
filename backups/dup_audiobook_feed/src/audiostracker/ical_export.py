import logging
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable, TypeVar
from .database import get_connection
import uuid
import pytz
from functools import wraps

# Define a generic type for the return value
T = TypeVar('T')

def retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions=(Exception,)) -> Callable:
    """
    Retry decorator with exponential backoff for improved reliability
    
    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier
        exceptions: Exceptions to catch and retry
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            mtries, mdelay = max_retries, delay
            last_exception = RuntimeError(f"Failed after {max_retries} retries with no exception captured")
            
            while mtries > 0:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logging.warning(f"Retry due to {e.__class__.__name__}: {e}. Retrying in {mdelay:.1f}s... ({mtries} tries left)")
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            
            logging.error(f"Failed after {max_retries} retries: {last_exception}")
            raise last_exception
        return wrapper
    return decorator

class ICalExporter:
    """iCalendar (.ics) export functionality for audiobook release dates"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config: Dict[str, Any] = config
        self.enabled: bool = config.get('ical', {}).get('enabled', False)
        self.export_path: str = config.get('ical', {}).get('file_path', 'data/ical_export/')
        self.batch_size: int = config.get('ical', {}).get('batch', {}).get('max_books', 10)
        self.batch_enabled: bool = config.get('ical', {}).get('batch', {}).get('enabled', True)
        
        # Ensure export directory exists
        if self.enabled:
            os.makedirs(self.export_path, exist_ok=True)
    
    def _format_ical_event(self, audiobook: Dict[str, Any]) -> str:
        """Format a single audiobook as an iCal event"""
        title = audiobook.get('title', 'Unknown Title')
        author = audiobook.get('author', 'Unknown Author')
        series = audiobook.get('series', '')
        series_number = audiobook.get('series_number', '')
        narrator = audiobook.get('narrator', 'Unknown Narrator')
        publisher = audiobook.get('publisher', 'Unknown Publisher')
        release_date = audiobook.get('release_date', '')
        asin = audiobook.get('asin', '')
        
        # Create event title
        event_title = f"📚 {title}"
        if series and series_number:
            event_title += f" ({series} #{series_number})"
        elif series:
            event_title += f" ({series})"
        
        # Create description
        description = f"New audiobook release\\n\\n"
        description += f"Title: {title}\\n"
        description += f"Author: {author}\\n"
        description += f"Narrator: {narrator}\\n"
        description += f"Publisher: {publisher}\\n"
        if series:
            description += f"Series: {series}"
            if series_number:
                description += f" (#{series_number})"
            description += "\\n"
        description += f"ASIN: {asin}\\n"
        if asin:
            description += f"Audible Link: https://www.audible.com/pd/{asin}\\n"
        
        # Parse release date and set to midnight California time
        ca_tz = pytz.timezone('America/Los_Angeles')
        try:
            # Parse the release date
            release_dt = datetime.strptime(release_date, '%Y-%m-%d')
            # Set to midnight California time
            ca_midnight = ca_tz.localize(release_dt.replace(hour=0, minute=0, second=0, microsecond=0))
            # Convert to UTC for the iCal format
            utc_start = ca_midnight.astimezone(pytz.UTC)
            utc_end = utc_start + timedelta(hours=1)  # 1-hour event
            
            # Format timestamps for iCal (YYYYMMDDTHHMMSSZ format)
            dtstart = utc_start.strftime('%Y%m%dT%H%M%SZ')
            dtend = utc_end.strftime('%Y%m%dT%H%M%SZ')
            
        except ValueError:
            # If date parsing fails, use today at midnight California time
            today = datetime.now()
            ca_midnight = ca_tz.localize(today.replace(hour=0, minute=0, second=0, microsecond=0))
            utc_start = ca_midnight.astimezone(pytz.UTC)
            utc_end = utc_start + timedelta(hours=1)
            
            dtstart = utc_start.strftime('%Y%m%dT%H%M%SZ')
            dtend = utc_end.strftime('%Y%m%dT%H%M%SZ')
        
        # Generate unique ID
        uid = f"audiobook-{asin}-{datetime.now().strftime('%Y%m%d%H%M%S')}@audiostacker"
        
        # Create timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        
        # Format the event
        event = f"""BEGIN:VEVENT
UID:{uid}
DTSTART:{dtstart}
DTEND:{dtend}
DTSTAMP:{timestamp}
SUMMARY:{event_title}
DESCRIPTION:{description}
CATEGORIES:Audiobooks,Entertainment
STATUS:CONFIRMED
TRANSP:OPAQUE
END:VEVENT"""
        
        return event
    
    def _create_ical_header(self) -> str:
        """Create the iCal file header with timezone support"""
        return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AudioStacker//AudioStacker//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:AudioStacker - New Releases
X-WR-CALDESC:New audiobook releases tracked by AudioStacker
X-WR-TIMEZONE:America/Los_Angeles
BEGIN:VTIMEZONE
TZID:America/Los_Angeles
BEGIN:DAYLIGHT
DTSTART:20070311T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
TZNAME:PDT
TZOFFSETFROM:-0800
TZOFFSETTO:-0700
END:DAYLIGHT
BEGIN:STANDARD
DTSTART:20071104T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
TZNAME:PST
TZOFFSETFROM:-0700
TZOFFSETTO:-0800
END:STANDARD
END:VTIMEZONE"""
    
    def _create_ical_footer(self) -> str:
        """Create the iCal file footer"""
        return "END:VCALENDAR"
    
    @retry(max_retries=3, exceptions=(IOError, OSError))
    def export_audiobooks(self, audiobooks: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """
        Export audiobooks to iCal format with automatic retries for IO errors
        
        Args:
            audiobooks: List of audiobook dictionaries
            filename: Optional custom filename (without extension)
            
        Returns:
            str: Path to the exported file or empty string if export failed or was skipped
        """
        if not self.enabled:
            logging.info("iCal export is disabled")
            return ""
        
        if not audiobooks:
            logging.info("No audiobooks to export to iCal")
            return ""
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"audiobooks_{timestamp}"
        
        file_path = os.path.join(self.export_path, f"{filename}.ics")
        
        try:
            # Ensure export directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write header
                f.write(self._create_ical_header() + "\n")
                
                # Write events
                events_written = 0
                for audiobook in audiobooks:
                    try:
                        event = self._format_ical_event(audiobook)
                        f.write(event + "\n")
                        events_written += 1
                    except Exception as event_error:
                        logging.error(f"Failed to format event for audiobook {audiobook.get('title', 'Unknown')}: {event_error}")
                        # Continue with the next audiobook
                
                # Write footer
                f.write(self._create_ical_footer() + "\n")
            
            logging.info(f"Successfully exported {events_written} audiobooks to {file_path}")
            return file_path
            
        except IOError as io_error:
            logging.error(f"I/O error during iCal export to {file_path}: {io_error}")
            return ""
        except Exception as e:
            logging.error(f"Failed to export audiobooks to iCal: {e}")
            # Only re-raise in development environments or for unexpected errors
            if isinstance(e, (ValueError, TypeError, KeyError)):
                # These are likely data issues we can recover from
                return ""
            raise
    
    def export_from_database(self, days_ahead: int = 30) -> str:
        """
        Export audiobooks from database that are releasing within the next N days
        
        Args:
            days_ahead: Number of days ahead to include in export
            
        Returns:
            str: Path to the exported file
        """
        if not self.enabled:
            logging.info("iCal export is disabled")
            return ""
        
        try:
            # Calculate date range
            today = datetime.now().date()
            end_date = today + timedelta(days=days_ahead)
            
            # Query database
            with get_connection() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT * FROM audiobooks 
                    WHERE date(release_date) BETWEEN ? AND ?
                    ORDER BY release_date ASC
                ''', (today.isoformat(), end_date.isoformat()))
                
                rows = c.fetchall()
                columns = [desc[0] for desc in c.description]
                
                audiobooks = [dict(zip(columns, row)) for row in rows]
            
            if not audiobooks:
                logging.info(f"No audiobooks found for the next {days_ahead} days")
                return ""
            
            # Create filename with date range
            filename = f"upcoming_releases_{today.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}"
            
            return self.export_audiobooks(audiobooks, filename)
            
        except Exception as e:
            logging.error(f"Failed to export from database: {e}")
            raise e
    
    def export_batches(self) -> List[str]:
        """
        Export audiobooks in batches if batch mode is enabled
        
        Returns:
            List[str]: List of paths to exported files
        """
        if not self.enabled:
            logging.info("iCal export is disabled")
            return []
        
        if not self.batch_enabled:
            # Export all as one file
            return [self.export_from_database()]
        
        try:
            # Get all upcoming audiobooks
            today = datetime.now().date()
            end_date = today + timedelta(days=90)  # Look ahead 3 months for batching
            
            with get_connection() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT * FROM audiobooks 
                    WHERE date(release_date) BETWEEN ? AND ?
                    ORDER BY release_date ASC
                ''', (today.isoformat(), end_date.isoformat()))
                
                rows = c.fetchall()
                columns = [desc[0] for desc in c.description]
                
                audiobooks = [dict(zip(columns, row)) for row in rows]
            
            if not audiobooks:
                logging.info("No audiobooks found for batch export")
                return []
            
            # Split into batches
            exported_files = []
            for i in range(0, len(audiobooks), self.batch_size):
                batch = audiobooks[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1
                
                filename = f"audiobooks_batch_{batch_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                file_path = self.export_audiobooks(batch, filename)
                
                if file_path:
                    exported_files.append(file_path)
            
            logging.info(f"Exported {len(audiobooks)} audiobooks in {len(exported_files)} batches")
            return exported_files
            
        except Exception as e:
            logging.error(f"Failed to export batches: {e}")
            raise e
    
    def export_new_audiobooks(self, new_audiobooks: List[Dict[str, Any]]) -> List[str]:
        """
        Export only newly discovered audiobooks
        
        Args:
            new_audiobooks: List of audiobook dictionaries that were just discovered
            
        Returns:
            List[str]: List of paths to exported files
        """
        if not self.enabled:
            logging.info("iCal export is disabled")
            return []
            
        if not new_audiobooks:
            logging.info("No new audiobooks to export")
            return []
        
        try:
            if not self.batch_enabled:
                # Export all new audiobooks as one file
                filename = f"new_audiobooks_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                file_path = self.export_audiobooks(new_audiobooks, filename)
                return [file_path] if file_path else []
            
            # Split new audiobooks into batches
            exported_files = []
            for i in range(0, len(new_audiobooks), self.batch_size):
                batch = new_audiobooks[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1
                
                filename = f"new_audiobooks_batch_{batch_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                file_path = self.export_audiobooks(batch, filename)
                
                if file_path:
                    exported_files.append(file_path)
            
            logging.info(f"Exported {len(new_audiobooks)} new audiobooks in {len(exported_files)} batches")
            return exported_files
            
        except Exception as e:
            logging.error(f"Failed to export new audiobooks: {e}")
            raise e
    
    def cleanup_old_exports(self, days_old: int = 30):
        """Remove old iCal export files"""
        if not self.enabled or not os.path.exists(self.export_path):
            return
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            removed_count = 0
            
            for filename in os.listdir(self.export_path):
                if filename.endswith('.ics'):
                    file_path = os.path.join(self.export_path, filename)
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_mtime < cutoff_date:
                        os.remove(file_path)
                        removed_count += 1
                        logging.debug(f"Removed old iCal export: {filename}")
            
            logging.info(f"Cleaned up {removed_count} old iCal export files")
            
        except Exception as e:
            logging.error(f"Failed to cleanup old exports: {e}")

# Convenience functions
def create_exporter(config: Dict[str, Any]) -> ICalExporter:
    """Factory function to create an iCal exporter"""
    return ICalExporter(config)

def export_upcoming_releases(config: Dict[str, Any], days_ahead: int = 30) -> str:
    """
    Convenience function to export upcoming releases
    
    Args:
        config: Configuration dictionary
        days_ahead: Number of days ahead to include
        
    Returns:
        str: Path to exported file
    """
    exporter = create_exporter(config)
    return exporter.export_from_database(days_ahead)
