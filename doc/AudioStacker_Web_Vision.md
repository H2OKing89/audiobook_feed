# AudioStacker Web Implementation - True to Vision

## Overview

The web interface should mirror the core AudioStacker workflow:
1. **Watch-list Management** (like Sonarr) - not just random searches
2. **Daily Query Simulation** - trigger the same logic as the CLI
3. **Cache Viewing** - see what's in the SQLite database
4. **Notification History** - track what was sent when
5. **Configuration Management** - edit YAML files through UI

## Proposed Web Interface Structure

### 1. **Dashboard** (Main Page)
- **System Status**: Last run, next scheduled run, database stats
- **Recent Discoveries**: New audiobooks found in last 24h
- **Notification Summary**: What was sent to which channels
- **Quick Actions**: Manual run, view logs, export data

### 2. **Watch-list Management** 
- **Authors Tab**: Manage `audiobooks.yaml` authors section
- **Add Author**: Search for author → add to watch-list with criteria
- **Edit Criteria**: Modify series/publisher/narrator filters per author
- **Import/Export**: Upload/download `audiobooks.yaml`

### 3. **Database Viewer**
- **Cached Books**: View current SQLite database contents
- **Filter Views**: Upcoming releases, already notified, by author/series
- **Manual Actions**: Mark as notified, delete entries, trigger notification
- **Database Stats**: Total books, notification status breakdown

### 4. **Configuration Manager**
- **Runtime Settings**: Edit `config.yaml` through web forms
- **Notification Channels**: Configure Pushover/Discord/Email settings
- **Schedule Settings**: Cron expression, timezone configuration
- **Export Settings**: iCal batch settings

### 5. **Logs & History**
- **Recent Runs**: Parse and display JSON logs in readable format
- **Notification History**: Which books were sent to which channels when
- **Error Tracking**: Failed notifications, API errors, etc.

## Updated Backend Architecture

Instead of generic search, the backend should:

1. **Expose AudioStacker Core Functions**:
   - `POST /api/run` - Execute the daily workflow manually
   - `GET /api/database` - View cached audiobooks
   - `GET /api/config` - Get current configuration
   - `PUT /api/config` - Update configuration files

2. **Watch-list Management**:
   - `GET /api/watchlist` - Get authors from audiobooks.yaml
   - `POST /api/watchlist/author` - Add author to watch-list
   - `PUT /api/watchlist/author/:name` - Update author criteria
   - `DELETE /api/watchlist/author/:name` - Remove author

3. **Database Operations**:
   - `GET /api/books` - List cached books with filters
   - `PUT /api/books/:asin/notify` - Mark as notified for specific channel
   - `DELETE /api/books/:asin` - Remove from cache

4. **System Operations**:
   - `GET /api/status` - System health, last run info
   - `GET /api/logs` - Recent logs with pagination
   - `POST /api/test-notifications` - Test notification channels

This way the web interface becomes a **management dashboard** for AudioStacker rather than a standalone search tool.
