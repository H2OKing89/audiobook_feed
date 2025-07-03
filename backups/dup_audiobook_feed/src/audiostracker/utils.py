import os
import yaml
from dotenv import load_dotenv
import logging
import json
import time
import random
import re
from difflib import SequenceMatcher
from functools import wraps
from typing import Callable, Any, Optional
from decimal import Decimal
import requests

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'time': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
        }
        if record.exc_info:
            log_record['exc_info'] = self.formatException(record.exc_info)
        return json.dumps(log_record)

# Load .env for secrets
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), 'config', '.env')
    load_dotenv(dotenv_path=env_path)
    user_key = os.getenv('PUSHOVER_USER_KEY')
    api_token = os.getenv('PUSHOVER_API_TOKEN')
    if not user_key or not api_token:
        raise ValueError("Missing Pushover user key or API token in .env")
    return user_key, api_token

def merge_env_config(config):
    """Merge environment variables into config for all notification channels"""
    env_path = os.path.join(os.path.dirname(__file__), 'config', '.env')
    load_dotenv(dotenv_path=env_path)
    
    # Pushover
    if 'pushover' in config:
        config['pushover']['user_key'] = os.getenv('PUSHOVER_USER_KEY', config['pushover'].get('user_key', ''))
        config['pushover']['api_token'] = os.getenv('PUSHOVER_API_TOKEN', config['pushover'].get('api_token', ''))
    
    # Discord
    if 'discord' in config:
        config['discord']['webhook_url'] = os.getenv('DISCORD_WEBHOOK_URL', config['discord'].get('webhook_url', ''))
    
    # Email
    if 'email' in config:
        config['email']['from_email'] = os.getenv('EMAIL_FROM', config['email'].get('from_email', ''))
        config['email']['username'] = os.getenv('EMAIL_USERNAME', config['email'].get('username', ''))
        config['email']['password'] = os.getenv('EMAIL_PASSWORD', config['email'].get('password', ''))
        
        # Handle EMAIL_TO as comma-separated string
        email_to = os.getenv('EMAIL_TO', '')
        if email_to:
            config['email']['to_emails'] = [email.strip() for email in email_to.split(',') if email.strip()]
        elif not config['email'].get('to_emails'):
            config['email']['to_emails'] = []
    
    return config

# Load YAML config
def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# Validate config.yaml
def validate_config(cfg):
    missing = [k for k in REQUIRED_CONFIG_KEYS if k not in cfg]
    if missing:
        raise ValueError(f"Missing config keys: {missing}")
    for k in REQUIRED_PUSHOVER_KEYS:
        if k not in cfg['pushover']:
            raise ValueError(f"Missing pushover config key: {k}")
    for k in REQUIRED_ICAL_KEYS:
        if k not in cfg['ical']:
            raise ValueError(f"Missing ical config key: {k}")
    for k in REQUIRED_ICAL_BATCH_KEYS:
        if k not in cfg['ical']['batch']:
            raise ValueError(f"Missing ical.batch config key: {k}")
    
    # Validate log level
    if cfg['log_level'] not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
        raise ValueError("log_level must be one of: DEBUG, INFO, WARNING, ERROR")
    
    # Validate log format
    if cfg['log_format'] not in ['json', 'text']:
        raise ValueError("log_format must be 'json' or 'text'")
    
    # Validate max_results
    if not isinstance(cfg['max_results'], int) or cfg['max_results'] < 1 or cfg['max_results'] > 50:
        raise ValueError("max_results must be an integer between 1 and 50")
    return True

# Validate audiobooks.yaml (basic)
def validate_audiobooks(data):
    if 'audiobooks' not in data:
        raise ValueError("audiobooks.yaml missing 'audiobooks' root key")
    if not isinstance(data['audiobooks'], dict):
        raise ValueError("'audiobooks' must be a dict")
    return True

def setup_logging(config, log_path=None):
    log_level = getattr(logging, str(config.get('log_level', 'INFO')).upper(), logging.INFO)
    log_format = config.get('log_format', 'text')
    if not log_path:
        log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'logs', 'audiostacker.log')
    handlers = []
    file_handler = logging.FileHandler(log_path)
    if log_format == 'json':
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    handlers.append(file_handler)
    # Also log to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    logging.basicConfig(level=log_level, handlers=handlers, force=True)

def retry_with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retry_on_exceptions: tuple = (requests.RequestException, ConnectionError, TimeoutError)
):
    """
    Decorator that implements exponential backoff with jitter for retrying failed operations.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        jitter: Add random jitter to delay to avoid thundering herd
        retry_on_exceptions: Tuple of exceptions to retry on
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on_exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logging.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        raise e
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    
                    # Add jitter to avoid thundering herd
                    if jitter:
                        delay *= (0.5 + random.random() * 0.5)
                    
                    logging.warning(f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {delay:.2f}s")
                    time.sleep(delay)
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    logging.error(f"Function {func.__name__} failed with unexpected exception: {e}")
                    raise e
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            else:
                raise RuntimeError(f"Function {func.__name__} failed with unknown error")
        
        return wrapper
    return decorator

def safe_execute(func: Callable, *args, **kwargs) -> tuple[bool, Any, Optional[Exception]]:
    """
    Safely execute a function and return success status, result, and any exception.
    
    Returns:
        tuple: (success: bool, result: Any, exception: Optional[Exception])
    """
    try:
        result = func(*args, **kwargs)
        return True, result, None
    except Exception as e:
        logging.error(f"Safe execution of {func.__name__} failed: {e}")
        return False, None, e

def normalize_string(s):
    """Normalize a string for comparison by removing punctuation, extra spaces, and lowercasing"""
    if not s:
        return ""
    # Convert to lowercase
    s = s.lower()
    # Remove punctuation and extra spaces
    s = re.sub(r'[^\w\s]', '', s)
    # Replace multiple spaces with single space
    s = re.sub(r'\s+', ' ', s)
    # Remove leading/trailing whitespace
    s = s.strip()
    return s

def normalize_list(items):
    """Normalize a list of strings for comparison"""
    if not items:
        return []
    return [normalize_string(item) for item in items if item]

def fuzzy_ratio(s1, s2):
    """Calculate fuzzy match ratio between two strings"""
    if not s1 or not s2:
        return 0.0
    return SequenceMatcher(None, normalize_string(s1), normalize_string(s2)).ratio()

def set_language_filter(language: str) -> None:
    """
    Set the language filter for Audible API results
    
    Args:
        language: Language to filter results by (e.g., "english", "spanish", "french")
    """
    # Import here to avoid circular imports
    from .audible import set_language_filter as set_audible_language_filter
    set_audible_language_filter(language)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
AUDIOBOOKS_PATH = os.path.join(os.path.dirname(__file__), 'config', 'audiobooks.yaml')

REQUIRED_CONFIG_KEYS = [
    'cron_settings', 'max_results', 'log_level', 'log_format', 'pushover', 'rate_limits', 'ical'
]
REQUIRED_PUSHOVER_KEYS = ['enabled', 'sound', 'priority', 'device']
REQUIRED_ICAL_KEYS = ['enabled', 'batch']
REQUIRED_ICAL_BATCH_KEYS = ['enabled', 'max_books', 'file_path']

# Volume number extraction with decimal support
VOL_RE = re.compile(
    r"""\b            # word-boundary
        (?:vol(?:ume)?\.?\s*)?   # "vol"/"volume"/"vol." (optional)
        (\d+(?:\.\d+)?)          # 3  |  3.5  | 10.25  etc.
    \b""",
    re.IGNORECASE | re.VERBOSE,
)

def extract_volume_number(title: str) -> Optional[Decimal]:
    """
    Extract and normalize volume numbers from book titles with decimal support
    
    Handles various formats:
    - "Vol. 14", "Volume 14.5", "14 (Light Novel)", "Book 4.25", etc.
    
    Args:
        title: Book title
        
    Returns:
        Optional[Decimal]: Exact volume number as Decimal or None if not found
    """
    if not title:
        return None
    
    title_lower = title.lower()
    
    # Common volume patterns with decimal support
    volume_patterns = [
        r'vol\.?\s*(\d+(?:\.\d+)?)',           # "Vol. 14", "Vol 14.5"
        r'volume\s*(\d+(?:\.\d+)?)',           # "Volume 14", "Volume 14.5"
        r'book\s*(\d+(?:\.\d+)?)',             # "Book 14", "Book 14.5"
        r'(\d+(?:\.\d+)?)\s*\(light novel\)', # "14 (Light Novel)", "14.5 (Light Novel)"
        r'(\d+(?:\.\d+)?)\s*\(ln\)',          # "14 (LN)", "14.5 (LN)"
        r',\s*vol\.?\s*(\d+(?:\.\d+)?)',      # ", Vol. 14", ", Vol. 14.5"
        r':\s*volume\s*(\d+(?:\.\d+)?)',      # ": Volume 14", ": Volume 14.5"
        r'\s+(\d+(?:\.\d+)?)$',               # " 14" or " 14.5" at end of title
    ]
    
    for pattern in volume_patterns:
        match = re.search(pattern, title_lower)
        if match:
            try:
                return Decimal(match.group(1))
            except (ValueError, TypeError):
                continue
    
    return None

if __name__ == "__main__":
    try:
        user_key, api_token = load_env()
        config = load_yaml(CONFIG_PATH)
        validate_config(config)
        audiobooks = load_yaml(AUDIOBOOKS_PATH)
        validate_audiobooks(audiobooks)
        setup_logging(config)
        print("Config and audiobooks.yaml loaded and validated successfully.")
    except Exception as e:
        print(f"Config validation failed: {e}")
