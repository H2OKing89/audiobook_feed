# AudioStacker Implementation Guide

## Project Overview

AudioStacker is a utility that tracks audiobook releases on Audible based on your configured preferences. It stores information about upcoming audiobooks in a local database, can notify you through multiple channels when new releases are detected, and provides calendar exports for scheduling.

## Architecture

### Core Components

1. **Audible API Client** (`audible.py`)
   - Searches Audible for audiobooks by author, title, or series
   - Handles rate limiting to avoid API restrictions
   - Normalizes data returned from the API

2. **Database Manager** (`database.py`)
   - SQLite database for storing audiobook information
   - Tracks notification status across different channels
   - Provides methods for adding, updating, and querying audiobooks

3. **Notification System** (`notify/`)
   - Modular notification architecture
   - Support for Pushover, Discord, and Email channels
   - Easily extendable for additional notification methods

4. **iCalendar Export** (`ical_export.py`)
   - Generates iCalendar (.ics) files for upcoming audiobook releases
   - Supports batch exports to avoid calendar app limitations
   - Configurable export options

5. **Configuration Management** (`utils.py`)
   - YAML-based configuration with environment variable support
   - Validation for configuration and audiobook tracking preferences

## Workflow

1. **Configuration Loading**
   - Load and validate global configuration
   - Load and validate audiobook tracking preferences
   - Set up logging based on configuration

2. **Database Initialization**
   - Initialize database if it doesn't exist
   - Clean up old releases that are no longer relevant

3. **Audiobook Discovery**
   - Search Audible for audiobooks matching configured authors
   - Identify ALL matches above confidence threshold
   - Process multiple matches per search (e.g., all volumes in a series)
   - Add all matching audiobooks to the database

4. **Notification**
   - Send notifications for new releases through configured channels
   - Track notification status to avoid duplicate notifications

5. **Calendar Export**
   - Export upcoming releases as iCalendar files
   - Generate batch exports for better calendar app compatibility

## Configuration Guide

### Global Configuration (`config.yaml`)

```yaml
# Cron settings for scheduled execution
cron_settings:
  enabled: true 
  cron: "0 9 * * *"  # Run daily at 9:00 AM
  timezone: "America/Chicago"

# API and application limits
max_results: 50
log_level: DEBUG  # DEBUG, INFO, WARNING, ERROR
log_format: json  # json, text

# Notification channel configuration
pushover:
  enabled: true
  sound: "pushover"
  priority: 0
  device: ""

discord:
  enabled: false
  webhook_url: ""
  username: "AudioStacker"
  avatar_url: ""
  color: "0x1F8B4C"

email:
  enabled: false
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  use_tls: true
  use_ssl: false
  from_email: ""
  to_emails: []

# Rate limiting settings
rate_limits:
  audible_api_per_minute: 10
  notification_per_minute: 5
  db_ops_per_second: 20

# iCalendar export settings
ical:
  enabled: true
  batch:
    enabled: true
    max_books: 10
    file_path: "data/ical_export/"
```

### Audiobook Tracking (`audiobooks.yaml`)

```yaml
audiobooks:
  author:
    "Author Name":
      - title: "Book Title"  # Optional, if looking for specific title
        series: "Series Name"  # Optional, if looking for specific series
        publisher: "Publisher Name"  # Optional
        narrator:  # Optional
          - "Narrator Name"
```

### Environment Variables (`.env`)

```env
# Pushover credentials
PUSHOVER_USER_KEY=your_user_key
PUSHOVER_API_TOKEN=your_api_token

# Discord webhook URL
DISCORD_WEBHOOK_URL=your_webhook_url

# Email credentials
EMAIL_USERNAME=your_email
EMAIL_PASSWORD=your_app_password
EMAIL_FROM=your_email@example.com
EMAIL_TO=recipient1@example.com,recipient2@example.com
```

## Database Schema

```sql
CREATE TABLE audiobooks (
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
);

CREATE INDEX idx_author ON audiobooks(author);
CREATE INDEX idx_series ON audiobooks(series, series_number);
CREATE INDEX idx_release ON audiobooks(release_date);
```

## Extending the Project

### Adding New Notification Channels

1. Create a new file in the `notify/` directory (e.g., `telegram.py`)
2. Implement the required notification interface
3. Register the new channel in `notify.py`
4. Add configuration options to `config.yaml`

### Adding Functionality

- **Additional Search Methods**: Enhance `audible.py` to support more search parameters
- **Web Interface**: Add a web-based UI for managing tracked audiobooks
- **Analytics**: Track and display statistics about audiobook releases
- **Integration**: Connect with audiobook apps or services

## Deployment

For automated execution, set up a scheduled task or cron job:

```bash
# Run daily at 9:00 AM
0 9 * * * cd /path/to/audiobook_feed && python -m src.audiostracker.main
```
