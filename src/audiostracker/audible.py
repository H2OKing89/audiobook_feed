import requests
import aiohttp
import asyncio
import logging
import time
import json
import os
import hashlib
from datetime import datetime, timedelta
from threading import Lock
from difflib import SequenceMatcher
from decimal import Decimal
import re
from .utils import retry_with_exponential_backoff, normalize_string, normalize_list, fuzzy_ratio
from typing import Dict, List, Any, Optional

# Global rate limit state
_last_api_call = 0
_api_lock = Lock()
_api_min_interval = 6  # default: 10 calls/minute = 6s between calls

# Cache settings
_cache_dir = os.path.join(os.path.dirname(__file__), 'data', 'cache')
_cache_ttl = 24 * 60 * 60  # 24 hours in seconds

# Language filtering
_default_language = "english"  # default language for filtering results

def set_audible_rate_limit(calls_per_minute: int) -> None:
    """
    Configure the rate limiting for Audible API calls.
    
    Args:
        calls_per_minute: Maximum number of API calls allowed per minute
    """
    global _api_min_interval
    _api_min_interval = 60.0 / max(1, calls_per_minute)

def set_cache_ttl(hours: int) -> None:
    """
    Set the time-to-live for cached results in hours
    
    Args:
        hours: Number of hours to keep cached results
    """
    global _cache_ttl
    _cache_ttl = hours * 60 * 60

def set_language_filter(language: str) -> None:
    """
    Set the language filter for Audible API results
    
    Args:
        language: Language to filter results by (e.g., "english", "spanish", "french")
    """
    global _default_language
    _default_language = language.lower()

def _get_cache_key(query: str, search_field: str, page: int, results_per_page: int) -> str:
    """
    Generate a cache key for an API request
    
    Args:
        query: Search query
        search_field: Field to search (title, author, etc.)
        page: Page number
        results_per_page: Results per page
        
    Returns:
        str: Cache key (MD5 hash)
    """
    # Create a string representing the query parameters
    param_str = f"{query.lower()}:{search_field}:{page}:{results_per_page}"
    
    # Return an MD5 hash of the parameter string
    return hashlib.md5(param_str.encode('utf-8')).hexdigest()

def _get_cached_results(cache_key: str) -> Optional[List[Dict[str, Any]]]:
    """
    Try to get cached results for a query
    
    Args:
        cache_key: Cache key
        
    Returns:
        Optional[List[Dict[str, Any]]]: Cached results or None if not found or expired
    """
    if not os.path.exists(_cache_dir):
        os.makedirs(_cache_dir, exist_ok=True)
        return None
    
    cache_file = os.path.join(_cache_dir, f"{cache_key}.json")
    
    if not os.path.exists(cache_file):
        return None
    
    # Check if cache is expired
    file_mtime = os.path.getmtime(cache_file)
    if time.time() - file_mtime > _cache_ttl:
        logging.debug(f"Cache expired for key {cache_key}")
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cached_data = json.load(f)
            logging.debug(f"Using cached results for key {cache_key}")
            return cached_data
    except (json.JSONDecodeError, IOError) as e:
        logging.warning(f"Failed to read cache file {cache_file}: {e}")
        return None

def _cache_results(cache_key: str, results: List[Dict[str, Any]]) -> None:
    """
    Cache results for a query
    
    Args:
        cache_key: Cache key
        results: Results to cache
    """
    if not os.path.exists(_cache_dir):
        os.makedirs(_cache_dir, exist_ok=True)
    
    cache_file = os.path.join(_cache_dir, f"{cache_key}.json")
    
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(results, f)
            logging.debug(f"Cached results for key {cache_key}")
    except IOError as e:
        logging.warning(f"Failed to write cache file {cache_file}: {e}")

def audible_rate_limited(func):
    """
    Decorator that enforces rate limiting for Audible API calls.
    
    This decorator ensures that API calls are spaced according to 
    the configured _api_min_interval to avoid hitting API rate limits.
    
    Args:
        func: The function to be rate-limited
        
    Returns:
        A wrapped function that respects the rate limit
    """
    def wrapper(*args, **kwargs):
        global _last_api_call
        with _api_lock:
            now = time.time()
            wait = _last_api_call + _api_min_interval - now
            if wait > 0:
                logging.debug(f"Rate limiting: sleeping {wait:.2f}s before next Audible API call.")
                time.sleep(wait)
            result = func(*args, **kwargs)
            _last_api_call = time.time()
            return result
    return wrapper

@audible_rate_limited
@retry_with_exponential_backoff(max_retries=3, retry_on_exceptions=(requests.RequestException, requests.HTTPError, requests.Timeout))
def _fetch_audible_page(query: str, search_field: str, page: int, results_per_page: int) -> List[Dict[str, Any]]:
    """
    Fetch a single page of results from Audible API
    
    Args:
        query: Search query
        search_field: Field to search (title, author, etc.)
        page: Page number
        results_per_page: Results per page
        
    Returns:
        List[Dict[str, Any]]: Normalized results
    """
    base_url = "https://api.audible.com/1.0/catalog/products"
    base_params = {
        search_field: query,
        'num_results': results_per_page,
        'products_sort_by': '-ReleaseDate',
        'response_groups': 'product_desc,media,contributors,series,product_attrs,relationships,product_extended_attrs,category_ladders',
        'marketplace': 'US',  # Ensure consistent US marketplace
    }
    
    headers = {
        'User-Agent': 'curl/8.5.0',
    }
    
    if page > 0:
        base_params['page'] = page
    
    response = requests.get(base_url, params=base_params, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    products = data.get('products', [])
    normalized = []
    
    for product in products:
        # Language filtering - skip non-matching languages
        product_language = product.get('language', '').lower()
        if product_language and product_language != _default_language:
            logging.debug(f"Skipping book '{product.get('title', '')}' due to language mismatch: {product_language} != {_default_language}")
            continue
        
        # Skip podcasts and other non-audiobook content
        content_type = product.get('content_type', '').lower()
        if content_type and content_type == 'podcast':
            logging.debug(f"Skipping podcast: {product.get('title', '')}")
            continue
        
        # Process the product using the shared function
        normalized_product = _process_product(product)
        normalized.append(normalized_product)
    
    return normalized

async def _fetch_audible_page_async(session: aiohttp.ClientSession, query: str, search_field: str, page: int, results_per_page: int) -> List[Dict[str, Any]]:
    """
    Asynchronously fetch a single page of results from Audible API
    
    Args:
        session: aiohttp ClientSession
        query: Search query
        search_field: Field to search (title, author, etc.)
        page: Page number
        results_per_page: Results per page
        
    Returns:
        List[Dict[str, Any]]: Normalized results
    """
    base_url = "https://api.audible.com/1.0/catalog/products"
    base_params = {
        search_field: query,
        'num_results': results_per_page,
        'products_sort_by': '-ReleaseDate',
        'response_groups': 'product_desc,media,contributors,series,product_attrs,relationships,product_extended_attrs,category_ladders',
        'marketplace': 'US',  # Ensure consistent US marketplace
    }
    
    if page > 0:
        base_params['page'] = page
    
    # Apply rate limiting (4 requests per second)
    await asyncio.sleep(0.25)
    
    try:
        async with session.get(base_url, params=base_params) as response:
            response.raise_for_status()
            
            try:
                data = await response.json()
            except aiohttp.ContentTypeError as e:
                logging.error(f"Failed to parse JSON response for query '{query}' page {page}: {e}")
                return []
            
            products = data.get('products', [])
            normalized = []
            
            for product in products:
                # Language filtering - skip non-matching languages
                product_language = product.get('language', '').lower()
                if product_language and product_language != _default_language:
                    logging.debug(f"Skipping book '{product.get('title', '')}' due to language mismatch: {product_language} != {_default_language}")
                    continue
                
                # Skip podcasts and other non-audiobook content
                content_type = product.get('content_type', '').lower()
                if content_type and content_type == 'podcast':
                    logging.debug(f"Skipping podcast: {product.get('title', '')}")
                    continue
                
                # Process the product using the shared function
                normalized_product = _process_product(product)
                normalized.append(normalized_product)
            
            return normalized
            
    except aiohttp.ServerDisconnectedError as e:
        logging.error(f"Server disconnected for query '{query}' page {page}: {e}")
        return []
    except aiohttp.ClientError as e:
        logging.error(f"Client error for query '{query}' page {page}: {e}")
        return []
    except asyncio.TimeoutError as e:
        logging.error(f"Timeout error for query '{query}' page {page}: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected async fetch error for query '{query}' page {page}: {e}")
        return []

def search_audible(query: str, search_field: str = "title", max_pages: int = 4, results_per_page: int = 50) -> List[Dict[str, Any]]:
    """
    Search Audible API for audiobooks matching the query.
    Uses caching to minimize API calls for repeated searches.
    
    Args:
        query: Search query
        search_field: 'title', 'author', or 'series'
        max_pages: Maximum number of pages to fetch
        results_per_page: Number of results per page
        
    Returns:
        List[Dict[str, Any]]: Normalized audiobook results
    """
    all_results = []
    
    # Try to get page 0 from cache first
    cache_key = _get_cache_key(query, search_field, 0, results_per_page)
    cached_results = _get_cached_results(cache_key)
    
    if cached_results is not None:
        # Use cached results for page 0
        all_results.extend(cached_results)
        logging.info(f"Found {len(cached_results)} cached results for query '{query}'")
    else:
        # Fetch page 0 from API
        try:
            page_results = _fetch_audible_page(query, search_field, 0, results_per_page)
            all_results.extend(page_results)
            
            # Cache the results
            _cache_results(cache_key, page_results)
            
            logging.info(f"Fetched {len(page_results)} results from API for query '{query}'")
        except Exception as e:
            logging.error(f"Failed to fetch page 0 for query '{query}': {e}")
    
    # Fetch additional pages if needed
    for page in range(1, max_pages):
        # Check if we need more results
        if len(all_results) < page * results_per_page:
            # We got fewer results than expected, no need to fetch more
            break
            
        # Try cache first
        cache_key = _get_cache_key(query, search_field, page, results_per_page)
        cached_results = _get_cached_results(cache_key)
        
        if cached_results is not None:
            all_results.extend(cached_results)
            logging.info(f"Found {len(cached_results)} cached results for query '{query}' page {page}")
        else:
            # Fetch from API
            try:
                page_results = _fetch_audible_page(query, search_field, page, results_per_page)
                all_results.extend(page_results)
                
                # Cache the results
                _cache_results(cache_key, page_results)
                
                logging.info(f"Fetched {len(page_results)} results from API for query '{query}' page {page}")
                
                # If we got fewer results than requested, we've reached the end
                if len(page_results) < results_per_page:
                    break
            except Exception as e:
                logging.error(f"Failed to fetch page {page} for query '{query}': {e}")
                break
    
    return all_results

async def search_audible_async(query: str, search_field: str = "title", max_pages: int = 4, results_per_page: int = 50) -> List[Dict[str, Any]]:
    """
    Asynchronously search Audible API for audiobooks matching the query.
    Uses parallel requests within rate limits for improved performance.
    
    Args:
        query: Search query
        search_field: 'title', 'author', or 'series'
        max_pages: Maximum number of pages to fetch
        results_per_page: Number of results per page
        
    Returns:
        List[Dict[str, Any]]: Normalized audiobook results
    """
    all_results = []
    
    # Check cache for all pages first
    cached_pages = {}
    pages_to_fetch = []
    
    for page in range(max_pages):
        cache_key = _get_cache_key(query, search_field, page, results_per_page)
        cached_results = _get_cached_results(cache_key)
        
        if cached_results is not None:
            cached_pages[page] = cached_results
            logging.info(f"Found {len(cached_results)} cached results for query '{query}' page {page}")
        else:
            pages_to_fetch.append(page)
    
    # If we have all pages cached, return them
    if not pages_to_fetch:
        for page in range(max_pages):
            if page in cached_pages:
                all_results.extend(cached_pages[page])
        return all_results
    
    # Fetch missing pages asynchronously with proper session management
    headers = {
        'User-Agent': 'curl/8.5.0',
    }
    
    # Use longer timeout and robust connector settings
    timeout = aiohttp.ClientTimeout(total=120, connect=15, sock_read=30)
    connector = aiohttp.TCPConnector(
        limit=4, 
        limit_per_host=4, 
        enable_cleanup_closed=True
    )
    
    try:
        async with aiohttp.ClientSession(headers=headers, timeout=timeout, connector=connector) as session:
            # Create tasks for all pages to fetch
            tasks = []
            for page in pages_to_fetch:
                task = _fetch_audible_page_async(session, query, search_field, page, results_per_page)
                tasks.append((page, task))
            
            # Wait for ALL tasks to complete before session closes
            if tasks:
                try:
                    # Use gather to wait for all tasks simultaneously
                    task_results = await asyncio.gather(
                        *[task for _, task in tasks], 
                        return_exceptions=True
                    )
                    
                    # Process results
                    fetched_pages = {}
                    for i, (page, _) in enumerate(tasks):
                        result = task_results[i]
                        if isinstance(result, Exception):
                            logging.error(f"Failed to fetch page {page} for query '{query}': {result}")
                            continue
                        
                        # Ensure result is a list before processing
                        if not isinstance(result, list):
                            logging.error(f"Unexpected result type for page {page}: {type(result)}")
                            continue
                            
                        fetched_pages[page] = result
                        
                        # Cache the results
                        cache_key = _get_cache_key(query, search_field, page, results_per_page)
                        _cache_results(cache_key, result)
                        
                        logging.info(f"Fetched {len(result)} results from API for query '{query}' page {page}")
                        
                        # If we got fewer results than requested, we've reached the end
                        if len(result) < results_per_page:
                            break
                            
                except Exception as e:
                    logging.error(f"Error gathering async tasks for query '{query}': {e}")
                    fetched_pages = {}
            else:
                fetched_pages = {}
                
    except Exception as e:
        logging.error(f"Session error for query '{query}': {e}")
        fetched_pages = {}
    
    # Combine cached and fetched results in order
    for page in range(max_pages):
        if page in cached_pages:
            all_results.extend(cached_pages[page])
        elif page in fetched_pages:
            all_results.extend(fetched_pages[page])
        else:
            # If this page failed and it's not page 0, we can stop
            if page > 0:
                break
    
    return all_results

def search_audible_parallel(query: str, search_field: str = "title", max_pages: int = 4, results_per_page: int = 50) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for async search that provides parallel execution.
    Use this for improved performance over the standard search_audible function.
    
    Args:
        query: Search query  
        search_field: 'title', 'author', or 'series'
        max_pages: Maximum number of pages to fetch
        results_per_page: Number of results per page
        
    Returns:
        List[Dict[str, Any]]: Normalized audiobook results
    """
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, create a new event loop in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, 
                    search_audible_async(query, search_field, max_pages, results_per_page)
                )
                return future.result()
        else:
            # Use the existing event loop
            return loop.run_until_complete(
                search_audible_async(query, search_field, max_pages, results_per_page)
            )
    except RuntimeError:
        # No event loop exists, create one
        return asyncio.run(
            search_audible_async(query, search_field, max_pages, results_per_page)
        )

def narrator_match(narrators_result, narrators_wanted):
    """Check if any narrator in the result matches any in the wanted list"""
    if not narrators_result or not narrators_wanted:
        return False
    
    # Normalize both lists
    norm_result = normalize_list(narrators_result)
    norm_wanted = normalize_list(narrators_wanted)
    
    # If either list is empty after normalization, return False
    if not norm_result or not norm_wanted:
        return False
    
    # Check for direct matches first
    for nr in norm_result:
        for nw in norm_wanted:
            if nr == nw:
                return True
            # Use a high threshold for narrator matching
            if fuzzy_ratio(nr, nw) >= 0.9:  # 90% similarity
                logging.debug(f"Fuzzy narrator match: '{nr}' ~ '{nw}'")
                return True
    
    return False

def confidence(result, wanted):
    """
    Calculate a confidence score for how well a search result matches wanted criteria
    
    The confidence score uses a fuzzy-friendly approach where core fields (title, author, series)
    are required for a good match, while optional fields (publisher, narrator) only boost scores.
    
    Core weights:
    - Title: 50% (0.5) - most important
    - Author: 30% (0.3) - very important  
    - Series: 20% (0.2) - important for series books
    
    Boost weights (additive, can exceed 1.0):
    - Publisher: +0.1 bonus if matches
    - Narrator: +0.1 bonus if matches
    - Volume Recency: +0.05 bonus for newer volumes in same series
    
    Args:
        result: Dictionary containing audiobook data from Audible API
        wanted: Dictionary containing the desired audiobook criteria
        
    Returns:
        float: Confidence score between 0 and 1+ (can exceed 1.0 with bonuses)
    """
    # Define core weights (must sum to 1.0)
    core_weights = {
        'title': 0.5,   # Increased from 0.4
        'author': 0.3,  # Increased from 0.2  
        'series': 0.2,  # Same
    }
    
    # Bonus weights (additive)
    bonus_weights = {
        'publisher': 0.1,      # Bonus for publisher match
        'narrator': 0.1,       # Bonus for narrator match
        'volume_recency': 0.05 # Bonus for newer volumes in same series
    }
    
    thresholds = {
        'title': {'exact': 1.0, 'high': 0.85, 'medium': 0.70},
        'series': {'exact': 1.0, 'high': 0.85, 'medium': 0.70},
        'author': {'exact': 1.0, 'high': 0.90, 'medium': 0.75},
        'publisher': {'exact': 1.0, 'high': 0.95, 'medium': 0.80}
    }
    
    # Partial credit multipliers for different match quality levels
    credit = {
        'exact': 1.0,    # Full credit for exact matches
        'high': 0.9,     # 90% credit for high quality fuzzy matches
        'medium': 0.6,   # 60% credit for medium quality matches
        'low': 0.0       # No credit for poor matches
    }
    
    score = 0.0
    log_parts = []
    
    # Extract volume information early for volume-aware matching
    result_volume = extract_volume_number(result['title'])
    wanted_volume = extract_volume_number(wanted.get('title', ''))
    
    # Title matching - use volume-aware normalization for series books
    norm_title_result = normalize_string(result['title'])
    norm_title_wanted = normalize_string(wanted.get('title', ''))
    
    # For series books, compare base titles without volume numbers
    result_series = result.get('series', '')
    wanted_series = wanted.get('series', '')
    
    if result_series and wanted_series and normalize_string(result_series) == normalize_string(wanted_series):
        # Same series - use volume-aware title matching
        result_base_title = get_title_volume_key(result['title'])
        wanted_base_title = get_title_volume_key(wanted.get('title', ''))
        
        if result_base_title == wanted_base_title:
            # Same base title (series match) - give high score
            score += core_weights['title'] * credit['exact']
            log_parts.append(f"Series title match: '{result_base_title}' == '{wanted_base_title}'")
            
            # Volume recency bonus - prefer higher volume numbers
            if result_volume and wanted_volume:
                if result_volume > wanted_volume:
                    score += bonus_weights['volume_recency']
                    log_parts.append(f"Volume recency bonus: {result_volume} > {wanted_volume}")
                elif result_volume == wanted_volume:
                    log_parts.append(f"Same volume: {result_volume}")
                else:
                    log_parts.append(f"Older volume: {result_volume} < {wanted_volume}")
            elif result_volume:
                # Has volume info when wanted doesn't - small bonus
                score += bonus_weights['volume_recency'] * 0.5
                log_parts.append(f"Has volume info: {result_volume}")
        else:
            # Different base titles in same series
            title_ratio = fuzzy_ratio(result['title'], wanted.get('title', ''))
            if title_ratio >= thresholds['title']['high']:
                score += core_weights['title'] * credit['high']
                log_parts.append(f"Fuzzy series title match: '{result_base_title}' ~ '{wanted_base_title}' ({title_ratio:.2f})")
            elif title_ratio >= thresholds['title']['medium']:
                score += core_weights['title'] * credit['medium']
                log_parts.append(f"Partial series title match: '{result_base_title}' ~ '{wanted_base_title}' ({title_ratio:.2f})")
    else:
        # Regular title matching for non-series or different series
        title_ratio = fuzzy_ratio(result['title'], wanted.get('title', ''))
        
        if norm_title_result and norm_title_wanted:
            if norm_title_result == norm_title_wanted:
                score += core_weights['title'] * credit['exact']
            elif title_ratio >= thresholds['title']['high']:
                score += core_weights['title'] * credit['high']
                log_parts.append(f"Fuzzy title match: '{norm_title_result}' ~ '{norm_title_wanted}' ({title_ratio:.2f})")
            elif title_ratio >= thresholds['title']['medium']:
                score += core_weights['title'] * credit['medium']
                log_parts.append(f"Partial title match: '{norm_title_result}' ~ '{norm_title_wanted}' ({title_ratio:.2f})")
            else:
                log_parts.append(f"Title mismatch: '{norm_title_result}' vs '{norm_title_wanted}' ({title_ratio:.2f})")
    
    # Series matching
    norm_series_result = normalize_string(result['series'])
    norm_series_wanted = normalize_string(wanted.get('series', ''))
    series_ratio = fuzzy_ratio(result['series'], wanted.get('series', ''))
    
    if norm_series_result and norm_series_wanted:
        if norm_series_result == norm_series_wanted:
            score += core_weights['series'] * credit['exact']
        elif series_ratio >= thresholds['series']['high']:
            score += core_weights['series'] * credit['high']
            log_parts.append(f"Fuzzy series match: '{norm_series_result}' ~ '{norm_series_wanted}' ({series_ratio:.2f})")
        elif series_ratio >= thresholds['series']['medium']:
            score += core_weights['series'] * credit['medium']
            log_parts.append(f"Partial series match: '{norm_series_result}' ~ '{norm_series_wanted}' ({series_ratio:.2f})")
        else:
            log_parts.append(f"Series mismatch: '{norm_series_result}' vs '{norm_series_wanted}' ({series_ratio:.2f})")
    
    # Author matching - handle multiple authors
    norm_author_result = normalize_string(result['author'])
    norm_author_wanted = normalize_string(wanted.get('author', ''))
    
    # Check if any author in the result matches the wanted author
    result_authors = [a.strip() for a in result['author'].split(',') if a.strip()]
    wanted_author = wanted.get('author', '')
    
    best_author_ratio = 0.0
    for res_author in result_authors:
        ratio = fuzzy_ratio(res_author, wanted_author)
        best_author_ratio = max(best_author_ratio, ratio)
    
    if norm_author_result and norm_author_wanted:
        if norm_author_result == norm_author_wanted:
            score += core_weights['author'] * credit['exact']
        elif best_author_ratio >= thresholds['author']['high']:
            score += core_weights['author'] * credit['high']
            log_parts.append(f"Fuzzy author match: '{norm_author_result}' ~ '{norm_author_wanted}' ({best_author_ratio:.2f})")
        elif best_author_ratio >= thresholds['author']['medium']:
            score += core_weights['author'] * credit['medium']
            log_parts.append(f"Partial author match: '{norm_author_result}' ~ '{norm_author_wanted}' ({best_author_ratio:.2f})")
        else:
            log_parts.append(f"Author mismatch: '{norm_author_result}' vs '{norm_author_wanted}' ({best_author_ratio:.2f})")
    
    # Publisher matching (BONUS - only adds, never subtracts)
    norm_publisher_result = normalize_string(result['publisher'])
    norm_publisher_wanted = normalize_string(wanted.get('publisher', ''))
    
    if norm_publisher_result and norm_publisher_wanted:
        if (norm_publisher_wanted in norm_publisher_result or 
            norm_publisher_result in norm_publisher_wanted or 
            fuzzy_ratio(result['publisher'], wanted.get('publisher', '')) >= 0.8):
            score += bonus_weights['publisher']
            log_parts.append(f"Publisher bonus: '{norm_publisher_result}' matches '{norm_publisher_wanted}'")
    
    # Narrator matching (BONUS - only adds, never subtracts)
    narrators_result = [result['narrator']] if isinstance(result['narrator'], str) else (result['narrator'] or [])
    narrators_wanted = wanted.get('narrator', [])
    
    if narrators_wanted and narrators_result:
        if narrator_match(narrators_result, narrators_wanted):
            score += bonus_weights['narrator']
            log_parts.append(f"Narrator bonus: matches found")
    
    # Log detailed match information for debugging
    if log_parts:
        log_level = logging.DEBUG if score >= 0.7 else logging.INFO
        logging.log(log_level, f"Match score: {score:.2f}; " + "; ".join(log_parts))
    
    return score

@audible_rate_limited
@retry_with_exponential_backoff(max_retries=3, retry_on_exceptions=(requests.RequestException, requests.HTTPError, requests.Timeout))
def get_book_by_asin(asin: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific audiobook by ASIN
    
    Args:
        asin: The Amazon Standard Identification Number for the book
        
    Returns:
        Optional[Dict[str, Any]]: Normalized book data or None if not found
    """
    if not asin:
        return None
    
    # Check cache first
    cache_key = hashlib.md5(f"asin:{asin}".encode('utf-8')).hexdigest()
    cached_result = _get_cached_results(cache_key)
    if cached_result:
        logging.debug(f"Using cached result for ASIN {asin}")
        return cached_result[0] if cached_result else None
    
    base_url = f"https://api.audible.com/1.0/catalog/products/{asin}"
    base_params = {
        'response_groups': 'product_desc,media,contributors,series,product_attrs,relationships,product_extended_attrs,category_ladders',
        'marketplace': 'US',
    }
    
    headers = {
        'User-Agent': 'curl/8.5.0',
    }
    
    try:
        response = requests.get(base_url, params=base_params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        product = data.get('product')
        if not product:
            return None
        
        # Apply the same filtering and processing as in _fetch_audible_page
        # Language filtering
        product_language = product.get('language', '').lower()
        if product_language and product_language != _default_language:
            logging.debug(f"Skipping book '{product.get('title', '')}' due to language mismatch: {product_language} != {_default_language}")
            return None
        
        # Skip podcasts
        content_type = product.get('content_type', '').lower()
        if content_type and content_type == 'podcast':
            logging.debug(f"Skipping podcast: {product.get('title', '')}")
            return None
        
        # Process the product using the same logic as _fetch_audible_page
        normalized = _process_product(product)
        
        # Cache the result
        if normalized:
            _cache_results(cache_key, [normalized])
        
        return normalized
        
    except Exception as e:
        logging.error(f"Failed to fetch book by ASIN {asin}: {e}")
        return None

def _process_product(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single product from Audible API into normalized format
    
    Args:
        product: Raw product data from Audible API
        
    Returns:
        Dict[str, Any]: Normalized product data
    """
    asin = product.get('asin', '')
    title = product.get('title', '')
    
    # Author processing - filter out illustrators, translators, etc.
    authors = []
    for author in product.get('authors', []):
        name = author.get('name', '')
        # Skip illustrators, translators, editors, and other non-primary authors
        if name and not any(role in name.lower() for role in [
            '- illustrator', 'illustrator', 
            '- translator', 'translator', 'translated by',
            '- editor', 'editor', 'edited by',
            'foreword', 'afterword',
            'introduction', 'preface',
            'contributor', 'adapter', 'adaptor',
            'compiler', 'compiled by',
            'cover designer', 'cover artist',
            'commentary', 'annotated by',
            'revised by', 'reviser'
        ]):
            authors.append(name)
    author_str = ', '.join(authors) if authors else ''
    
    # Narrator processing
    narrators = []
    for narrator in product.get('narrators', []):
        narrators.append(narrator.get('name', ''))
    narrator_str = ', '.join(narrators) if narrators else ''
    
    # Publisher
    publisher = product.get('publisher_name', '')
    
    # Series information
    series_name = ''
    series_position = ''
    series_info = product.get('series', [])
    if series_info:
        # Use the first series entry
        series = series_info[0]
        series_name = series.get('title', '')
        sequence = series.get('sequence', '')
        if sequence and isinstance(sequence, str) and sequence.replace('.', '', 1).isdigit():
            series_position = sequence
    
    # Get release date from the most reliable source
    release_date = ''
    if 'release_date' in product:
        release_date = product['release_date']
    elif 'issue_date' in product:
        release_date = product['issue_date']
    
    # Additional fields inspired by their implementation
    subtitle = product.get('subtitle', '')
    description = product.get('publisher_summary', '')
    runtime_minutes = product.get('runtime_length_min', 0)
    
    # Extract genres and tags from category_ladders
    genres = []
    tags = []
    if 'category_ladders' in product:
        for ladder in product['category_ladders']:
            for i, item in enumerate(ladder.get('ladder', [])):
                # First item is genre, rest are tags
                if i == 0:
                    genres.append(item.get('name', ''))
                else:
                    tags.append(item.get('name', ''))
    
    # Product URL
    url = f"https://www.audible.com/pd/{asin}"
    
    return {
        'asin': asin,
        'title': title,
        'subtitle': subtitle,
        'author': author_str,
        'narrator': narrator_str,
        'publisher': publisher,
        'series': series_name,
        'series_number': series_position,
        'release_date': release_date,
        'description': description,
        'runtime_minutes': runtime_minutes,
        'genres': genres,
        'tags': tags,
        'link': url
    }

def extract_volume_number(title: str) -> Optional[Decimal]:
    """
    Extract and normalize volume numbers from book titles with decimal support
    
    This function has been moved to utils.py for shared use.
    Importing here for backwards compatibility.
    """
    from .utils import extract_volume_number as utils_extract_volume_number
    return utils_extract_volume_number(title)

def get_title_volume_key(title: str) -> str:
    """
    Generate a standardized key for title matching that removes volume variations
    
    Args:
        title: Book title
        
    Returns:
        str: Normalized title key for matching
    """
    if not title:
        return ""
    
    title_lower = title.lower().strip()
    
    # Remove common volume indicators and normalize
    volume_removals = [
        r'\s*vol\.?\s*\d+.*$',           # Remove "Vol. 14" and everything after
        r'\s*volume\s*\d+.*$',           # Remove "Volume 14" and everything after  
        r'\s*book\s*\d+.*$',             # Remove "Book 14" and everything after
        r'\s*\d+\s*\(light novel\).*$',  # Remove "14 (Light Novel)" and after
        r'\s*\d+\s*\(ln\).*$',           # Remove "14 (LN)" and after
        r',\s*vol\.?\s*\d+.*$',          # Remove ", Vol. 14" and after
        r':\s*volume\s*\d+.*$',          # Remove ": Volume 14" and after
        r'\s+\d+$',                      # Remove " 14" at end
    ]
    
    normalized = title_lower
    for pattern in volume_removals:
        normalized = re.sub(pattern, '', normalized)
    
    # Clean up extra spaces and punctuation
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    return normalized

def find_best_match_with_review(results: List[Dict[str, Any]], wanted: Dict[str, Any], 
                                min_confidence: float = 0.5, 
                                preferred_confidence: float = 0.7) -> Optional[Dict[str, Any]]:
    """
    Find the best match with dynamic confidence floor and review flagging
    
    Args:
        results: List of search results
        wanted: Wanted book criteria
        min_confidence: Minimum acceptable confidence (default 0.5)
        preferred_confidence: Preferred confidence level (default 0.7)
        
    Returns:
        Optional[Dict[str, Any]]: Best match with added 'needs_review' flag, or None
    """
    if not results:
        return None
    
    # Score all results
    scored_results = []
    for result in results:
        score = confidence(result, wanted)
        scored_results.append((score, result))
    
    # Sort by confidence score (highest first)
    scored_results.sort(key=lambda x: x[0], reverse=True)
    
    if not scored_results:
        return None
    
    best_score, best_result = scored_results[0]
    
    # Check if any result meets the preferred threshold
    if best_score >= preferred_confidence:
        best_result['needs_review'] = False
        best_result['confidence_score'] = best_score
        logging.info(f"High confidence match ({best_score:.2f}): {best_result['title']}")
        return best_result
    
    # Check if the best result meets minimum threshold
    if best_score >= min_confidence:
        best_result['needs_review'] = True
        best_result['confidence_score'] = best_score
        logging.warning(f"Low confidence match ({best_score:.2f}) - needs review: {best_result['title']}")
        return best_result
    
    # No acceptable matches found
    logging.info(f"No matches above minimum confidence ({min_confidence}). Best was {best_score:.2f}")
    return None

def find_all_good_matches(results: List[Dict[str, Any]], wanted: Dict[str, Any], 
                        min_confidence: float = 0.5, 
                        preferred_confidence: float = 0.7) -> List[Dict[str, Any]]:
    """
    Find all matches that meet the minimum confidence threshold
    
    Args:
        results: List of search results
        wanted: Wanted book criteria
        min_confidence: Minimum acceptable confidence (default 0.5)
        preferred_confidence: Preferred confidence level (default 0.7)
        
    Returns:
        List[Dict[str, Any]]: All matching results with added 'needs_review' and 'confidence_score' fields
    """
    if not results:
        return []
    
    # Score all results
    scored_results = []
    for result in results:
        score = confidence(result, wanted)
        if score >= min_confidence:  # Only include results that meet minimum threshold
            result = result.copy()  # Create a copy to avoid modifying original
            result['confidence_score'] = score
            result['needs_review'] = score < preferred_confidence
            
            if score >= preferred_confidence:
                logging.info(f"High confidence match ({score:.2f}): {result['title']}")
            else:
                logging.warning(f"Low confidence match ({score:.2f}) - needs review: {result['title']}")
                
            scored_results.append((score, result))
    
    # Sort by confidence score (highest first)
    scored_results.sort(key=lambda x: x[0], reverse=True)
    
    # Extract just the results (without the scores)
    good_matches = [result for _, result in scored_results]
    
    if not good_matches:
        logging.info(f"No matches above minimum confidence ({min_confidence}).")
        
    return good_matches

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)
    authors = {
        "Patora Fuyuhara": [],
        "Another Author": [],
    }
    for author_name, books in authors.items():
        for book in books:
            if book.get('title'):
                query = book['title']
                search_field = 'title'
            elif book.get('series'):
                query = book['series']
                search_field = 'series'
            else:
                query = author_name
                search_field = 'author'
            logging.info(f"Searching Audible for: {query} (field: {search_field})")
            results = search_audible(query, search_field=search_field)
            print(f"Results for {search_field}='{query}': {len(results)}")
            for r in results:
                print(r)
