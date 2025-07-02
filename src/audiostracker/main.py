import logging
from .utils import load_yaml, validate_config, validate_audiobooks, setup_logging, merge_env_config
from .database import init_db, insert_or_update_audiobook, prune_released, get_unnotified_for_channel, mark_notified_for_channel, vacuum_db, DB_FILE
from .audible import search_audible, search_audible_parallel, set_audible_rate_limit, set_language_filter, confidence, find_best_match_with_review, find_all_good_matches
from .notify.notify import create_dispatcher
from .ical_export import create_exporter
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
AUDIOBOOKS_PATH = os.path.join(os.path.dirname(__file__), 'config', 'audiobooks.yaml')
ENV_PATH = os.path.join(os.path.dirname(__file__), 'config', '.env')

def main():
    # Load environment variables from .env file
    load_dotenv(ENV_PATH)
    
    config = load_yaml(CONFIG_PATH)
    config = merge_env_config(config)  # Merge environment variables into config
    validate_config(config)
    setup_logging(config)
    set_audible_rate_limit(config.get('rate_limits', {}).get('audible_api_per_minute', 10))
    set_language_filter(config.get('language', 'english'))  # Set language filter from config
    wanted = load_yaml(AUDIOBOOKS_PATH)
    validate_audiobooks(wanted)
    # Init DB
    init_db()
    
    # Get cleanup configuration with default value of 0 (remove on exact release date)
    cleanup_grace_period = config.get('database', {}).get('cleanup_grace_period_days', 0)
    
    # Clean DB: remove audiobooks that have been released
    deleted_count = prune_released(grace_period_days=cleanup_grace_period)
    
    # Periodically optimize the database
    vacuum_interval = config.get('database', {}).get('vacuum_interval_days', 7)
    last_vacuum_file = os.path.join(os.path.dirname(DB_FILE), '.last_vacuum')
    
    should_vacuum = False
    if os.path.exists(last_vacuum_file):
        try:
            with open(last_vacuum_file, 'r') as f:
                last_vacuum = datetime.fromisoformat(f.read().strip())
            days_since_vacuum = (datetime.now() - last_vacuum).days
            should_vacuum = days_since_vacuum >= vacuum_interval
        except (ValueError, IOError):
            should_vacuum = True
    else:
        should_vacuum = True
    
    if should_vacuum:
        logging.info(f"Running scheduled database optimization (interval: {vacuum_interval} days)")
        vacuum_db()
        # Record vacuum time
        try:
            with open(last_vacuum_file, 'w') as f:
                f.write(datetime.now().isoformat())
        except IOError as e:
            logging.warning(f"Failed to update vacuum timestamp: {e}")
    
    today = datetime.now().date()  # Define today for use in filtering logic
    # Enhanced confidence thresholds
    MIN_CONFIDENCE = 0.5    # Minimum acceptable confidence
    PREFERRED_CONFIDENCE = 0.7  # Preferred confidence level
    all_new = []
    needs_review_books = []  # Track books that need manual review
    
    authors = wanted['audiobooks'].get('author', {})
    for author_name, books in authors.items():
        logging.info(f"Searching Audible for author: {author_name}")
        results = search_audible_parallel(author_name, search_field='author')
        logging.info(f"Found {len(results)} results for author '{author_name}'")
        
        for book in books:
            wanted_info = dict(book)
            wanted_info['author'] = author_name
            
            # Filter results by release date first
            future_results = []
            for result in results:
                try:
                    release = datetime.strptime(result['release_date'], '%Y-%m-%d').date()
                except Exception:
                    continue  # skip if date is missing or invalid
                if release >= today:  # only keep today or future
                    future_results.append(result)
            
            if not future_results:
                continue
            
            # Use enhanced matching to find ALL good matches
            good_matches = find_all_good_matches(
                future_results, 
                wanted_info, 
                MIN_CONFIDENCE, 
                PREFERRED_CONFIDENCE
            )
            
            for best_match in good_matches:
                is_new = insert_or_update_audiobook(
                    asin=best_match['asin'],
                    title=best_match['title'],
                    author=best_match['author'],
                    narrator=best_match['narrator'],
                    publisher=best_match['publisher'],
                    series=best_match['series'],
                    series_number=best_match['series_number'],
                    release_date=best_match['release_date']
                )
                
                if best_match.get('needs_review', False):
                    needs_review_books.append({
                        'book': best_match,
                        'wanted': wanted_info,
                        'confidence': best_match.get('confidence_score', 0)
                    })
                
                if is_new:
                    logging.debug(f"Inserted new: {best_match['title']} (ASIN: {best_match['asin']}) by {best_match['author']} (confidence={best_match.get('confidence_score', 0):.2f})")
                    all_new.append(best_match)
                else:
                    logging.debug(f"Updated existing: {best_match['title']} (ASIN: {best_match['asin']}) by {best_match['author']} (confidence={best_match.get('confidence_score', 0):.2f})")
                    
        # Process series searches for this author
        for book in books:
            if book.get('series'):
                # Search using the book title instead of series name for better API results
                search_query = book.get('title', book['series'])
                logging.info(f"Searching Audible for series '{book['series']}' using query: {search_query}")
                series_results = search_audible_parallel(search_query, search_field='title')
                logging.info(f"Found {len(series_results)} results for query '{search_query}'")
                
                wanted_info = dict(book)
                wanted_info['author'] = author_name
                
                # Filter results by release date first
                future_series_results = []
                for result in series_results:
                    try:
                        release = datetime.strptime(result['release_date'], '%Y-%m-%d').date()
                    except Exception:
                        continue
                    if release >= today:
                        future_series_results.append(result)
                
                if not future_series_results:
                    continue
                
                # Use enhanced matching to find ALL good matches for series
                good_series_matches = find_all_good_matches(
                    future_series_results, 
                    wanted_info, 
                    MIN_CONFIDENCE, 
                    PREFERRED_CONFIDENCE
                )
                
                for best_series_match in good_series_matches:
                    is_new = insert_or_update_audiobook(
                        asin=best_series_match['asin'],
                        title=best_series_match['title'],
                        author=best_series_match['author'],
                        narrator=best_series_match['narrator'],
                        publisher=best_series_match['publisher'],
                        series=best_series_match['series'],
                        series_number=best_series_match['series_number'],
                        release_date=best_series_match['release_date']
                    )
                    
                    if best_series_match.get('needs_review', False):
                        needs_review_books.append({
                            'book': best_series_match,
                            'wanted': wanted_info,
                            'confidence': best_series_match.get('confidence_score', 0)
                        })
                    
                    if is_new:
                        logging.debug(f"Inserted new: {best_series_match['title']} (ASIN: {best_series_match['asin']}) by {best_series_match['author']} (confidence={best_series_match.get('confidence_score', 0):.2f})")
                        all_new.append(best_series_match)
                    else:
                        logging.debug(f"Updated existing: {best_series_match['title']} (ASIN: {best_series_match['asin']}) by {best_series_match['author']} (confidence={best_series_match.get('confidence_score', 0):.2f})")
    
    # Log summary of books needing review
    if needs_review_books:
        logging.warning(f"Found {len(needs_review_books)} books that need manual review:")
        for item in needs_review_books:
            book = item['book']
            confidence = item['confidence']
            logging.warning(f"  REVIEW: {book['title']} by {book['author']} (confidence: {confidence:.2f})")
    
    logging.info(f"Inserted/updated {len(all_new)} future audiobooks in total.")
    
    # Export iCal files for new audiobooks first
    ical_files = []
    ical_exporter = create_exporter(config)
    if config.get('ical', {}).get('enabled', False) and all_new:
        try:
            exported_files = ical_exporter.export_new_audiobooks(all_new)
            if exported_files:
                ical_files = exported_files
                logging.info(f"Exported iCal files: {exported_files}")
            else:
                logging.info("No iCal files exported (no new releases)")
        except Exception as e:
            logging.error(f"Failed to export iCal files: {e}")
    
    # Send notifications for new audiobooks
    dispatcher = create_dispatcher(config)
    enabled_channels = dispatcher.get_enabled_channels()
    
    if enabled_channels:
        logging.info(f"Checking for notifications across {len(enabled_channels)} channels: {enabled_channels}")
        
        for channel in enabled_channels:
            # Get audiobooks that haven't been notified for this channel
            unnotified = get_unnotified_for_channel(channel)
            
            if unnotified:
                logging.info(f"Found {len(unnotified)} unnotified audiobooks for channel '{channel}'")
                # Pass iCal files to notification if there are new audiobooks
                success = dispatcher.send_notification(channel, unnotified, ical_files if all_new else None)
                
                if success:
                    # Mark all as notified for this channel
                    for audiobook in unnotified:
                        mark_notified_for_channel(audiobook['asin'], channel)
                    logging.info(f"Marked {len(unnotified)} audiobooks as notified for channel '{channel}'")
                else:
                    logging.error(f"Failed to send notifications to channel '{channel}'")
            else:
                logging.info(f"No unnotified audiobooks for channel '{channel}'")
    else:
        logging.info("No notification channels enabled")
    
    print(f"Inserted/updated {len(all_new)} future audiobooks.")

if __name__ == "__main__":
    main()
