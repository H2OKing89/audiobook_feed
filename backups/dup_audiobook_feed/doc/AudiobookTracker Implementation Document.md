# AudioStacker **Implementation Document**

---

## I. Overview & Goals

**Purpose**
Automate discovery, tracking, and notification of new audiobook releases. Efficient caching and rate‑limited API access in a maintainable, modular code‑base.

## **Primary Goals**

1. Watch dynamic list of audiobooks (series, author, title, publisher).
2. Daily Audible queries for new items.
3. Cache results to avoid duplicates.
4. Send notifications once per release.
5. Easily extendable for new sources/channels.

> *Sonarr + anime waifu = Audiobook automation perfection.*

---

## II. Daily Workflow (TL;DR)

1. Load `config/audiobooks.yaml` (watch‑list).
2. Init SQLite cache.
3. For each watch‑item:

   * Query Audible (auto‑paginate ≤50/page)
   * Filter podcasts & past releases
   * Insert/update DB → notify if `notified=0`
4. **Prune cache** of released books (`release_date < today`). Log the current **UTC date** used for this comparison to avoid timezone ambiguity.
5. Log JSON → `logs/`. Exit.

---

## III. MVP Project Breakdown

### A. Config & Data

Two YAML files live under `config/`:

| File              | Purpose                                                                                                   |
| ----------------- | --------------------------------------------------------------------------------------------------------- |
| `config.yaml`     | Runtime behaviour, cron schedule, logging, notification channel defaults, rate limits, iCal export flags. |
| `audiobooks.yaml` | Watch‑list grouped by **author** ➜ list of desired `title` / `series` / publisher / narrator tuples.      |

#### `config.yaml` keys (current set)

| Key                                       | Type | Example               | Notes                                             |
| ----------------------------------------- | ---- | --------------------- | ------------------------------------------------- |
| **`cron_settings.enabled`**               | bool | `true`                | Toggle the background scheduler.                  |
| **`cron_settings.cron`**                  | str  | `"0 9 * * *"`         | Standard 5‑field cron expression.                 |
| **`cron_settings.timezone`**              | str  | `"America/Chicago"`   | Olson TZ database name.                           |
| **`max_results`**                         | int  | `50`                  | Audible hard‑caps at 50; leave at 50.             |
| **`log_level`**                           | enum | `DEBUG`               | `DEBUG \| INFO \| WARNING \| ERROR`.              |
| **`log_format`**                          | enum | `json`                | `json` = machine‑readable, `text` = human.        |
| **`pushover.enabled`**                    | bool | `true`                | Master switch.                                    |
| **`pushover.sound`**                      | str  | `"pushover"`          | Any valid Pushover sound id.                      |
| **`pushover.priority`**                   | int  | `0`                   | ‑2 (Low) → 2 (Emergency).                         |
| **`pushover.device`**                     | str  | `""`                  | Blank = all devices.                              |
| **`rate_limits.audible_api_per_minute`**  | int  | `10`                  | Soft reference; actual guard in code.             |
| **`rate_limits.notification_per_minute`** | int  | `5`                   | Ditto.                                            |
| **`rate_limits.db_ops_per_second`**       | int  | `20`                  | Ditto.                                            |
| **`ical.enabled`**                        | bool | `true`                | Toggle iCal export.                               |
| **`ical.interval`**                       | sec  | `60`                  | How often to batch‑flush .ics files during a run. |
| **`ical.batch.enabled`**                  | bool | `true`                | Whether to group events.                          |
| **`ical.batch.max_books`**                | int  | `10`                  | Max events per .ics.                              |
| **`ical.batch.file_path`**                | str  | `"data/ical_export/"` | Directory for output files.                       |

*Secrets* (`pushover.user_key`, `pushover.api_token`, etc.) are read from environment variables, **never** committed to Git.

#### `audiobooks.yaml` structure

```yaml
audiobooks:
  author:
    Author Name:
      - title: "Series/Book Title"
        series: "Series Name"
        publisher: "Publisher"
        narrator:
          - "Primary Narrator"
          - "Optional Co‑Narrator"
```

### Retention

* Cache pruned the **day *after* release** (`release_date < DATE('now','-1 day')`).
* One‑time notification per ASIN per channel (tracked via `notified_channels`).

### B. Project Structure

``` tree
# top‑level (excluding .venv, .git, __pycache__)
.
├── bin/
│   └── scripts/                # CLI helpers & cron wrappers
├── doc/                        # Markdown docs (this file + API cheat‑sheet)
├── logs/
│   └── audiostacker.log        # JSON run‑time logs
├── pytest.ini
├── requirements.txt
├── src/
│   └── audiostracker/
│       ├── __init__.py
│       ├── main.py             # orchestrator / CLI
│       ├── models.py           # Audiobook dataclass / Pydantic model
│       ├── audible.py          # API client & normaliser
│       ├── database.py         # SQLite cache & prune logic
│       ├── utils.py            # logging, rate‑limit, normalization
│       ├── export_db_to_json.py# helper for manual DB dumps
│       ├── config/
│       │   ├── config.yaml     # runtime settings
│       │   └── audiobooks.yaml # watch‑list
│       ├── notify/
│       │   ├── __init__.py
│       │   ├── notify.py       # dispatcher
│       │   └── pushover.py     # Pushover channel
│       └── web/
│           ├── static/         # CSS/JS/images for future UI
│           └── templates/      # Jinja2 / HTML templates
└── tests/
    └── test_audible.py         # pytest suite
```

*Folders may grow (e.g. additional `notify/discord.py`, more tests), but this reflects the current repository layout.*

### C. Database Schema. Database Schema

```sql
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
    notified INTEGER DEFAULT 0
);
```

---

## IV. Updated Logic Details

### 1. Cache Pruning

* **When:** start of run
* **Action:** DELETE FROM audiobooks WHERE release\_date < DATE('now');
* **Why:** Only track upcoming/new releases.

### 2. Multi-Match Processing

* **All Good Matches:** Process ALL search results above confidence threshold (min 0.5)
* **No Deduplication:** Multiple volumes in a series (e.g., Vol. 4, Vol. 5) will ALL be added to the database and notified
* **Confidence Thresholds:** High confidence (≥0.7) for normal processing, low confidence (0.5-0.7) flagged for manual review
* **Parallel Search:** Asynchronously search and process results for maximum efficiency

### 3. Notification Logic

* **Notify once per ASIN *per channel***: track a `notified_channels` set (e.g. `{"pushover", "discord"}`) or a versioned table.
* On the first successful send to a channel, add that channel to `notified_channels`.
* Subsequent runs skip any channel already recorded, preventing double‑sends when multiple notification back‑ends are enabled.
* **No suppression days**—each channel fires once per release, period.

### 3. DB Operations. DB Operations

* **Insert/Upsert:** on new/updated book
* **Prune released:** daily
* **Mark notified:** after successful notification

---

## V. Next Steps

1. Update `database.py`:

   * Add `prune_released()` to delete old ASINs.
2. Remove suppression config from `config.yaml`.
3. Simplify notification in `main.py`: notify on first insert only.
4. Update docs **and implement an integration test** that mocks two consecutive runs: first run inserts & notifies, second run verifies no duplicate notification occurs **and** that pruning removed past releases.

---

*This doc is a living artifact; refine as we build and learn.*

---

## VI. ✅ COMPLETED FEATURES UPDATE (June 2025)

### Multi-Channel Notification System ✅

**Implemented comprehensive multi-channel notification support:**

* ✅ **Database Schema**: Migrated to `notified_channels` JSON column for per-channel tracking
* ✅ **Pushover Integration**: Complete with priority, sound, and device targeting
* ✅ **Discord Integration**: Webhook-based notifications with rich embeds and batching
* ✅ **Email Integration**: SMTP support with HTML/text multipart messages
* ✅ **Notification Dispatcher**: Centralized management for all channels

**Configuration Example:**

```yaml
pushover:
  enabled: true
  sound: "pushover"
  priority: 0
  device: ""

discord:
  enabled: false
  webhook_url: ""  # From .env
  username: "AudioStacker"
  color: "0x1F8B4C"

email:
  enabled: false
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  use_tls: true
  from_email: ""  # From .env
  to_emails: []   # From .env
```

### Enhanced Error Handling ✅

**Implemented robust retry logic with exponential backoff:**

* ✅ **Retry Decorator**: `@retry_with_exponential_backoff()` for all external calls
* ✅ **Rate Limiting**: Configurable API rate limits with decorator pattern
* ✅ **Exception Handling**: Comprehensive error catching with detailed logging
* ✅ **Safe Execution**: Wrapper functions for critical operations

### iCal Export System ✅

**Complete calendar export functionality:**

* ✅ **RFC Compliance**: Standards-compliant iCalendar file generation
* ✅ **Batch Export**: Configurable batching for large datasets
* ✅ **Automatic Cleanup**: Removes old export files (30+ days)
* ✅ **Integration**: Seamless integration with main workflow

```yaml
ical:
  enabled: true
  batch:
    enabled: true
    max_books: 10
    file_path: "data/ical_export/"
```

### Pydantic Models & Validation ✅

**Complete type safety and validation:**

* ✅ **Configuration Models**: Validated config loading with clear error messages
* ✅ **Audiobook Models**: Type-safe audiobook data structures
* ✅ **Notification Models**: Channel-specific configuration validation
* ✅ **Database Migration**: Automatic schema updates with validation

```python
# Example models implemented:
class Config(BaseModel): ...
class Audiobook(BaseModel): ...
class PushoverConfig(NotificationConfig): ...
class DiscordConfig(NotificationConfig): ...
class EmailConfig(NotificationConfig): ...
```

### Updated Database Schema ✅

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
    notified_channels TEXT DEFAULT '{}' -- JSON: {"pushover": true, "discord": false}
);
```

### Testing Suite ✅

**Comprehensive test coverage:**

* ✅ **Integration Tests**: Multi-channel notifications, database operations
* ✅ **Unit Tests**: Individual component testing with mocks
* ✅ **End-to-End Tests**: Complete workflow validation
* ✅ **Feature Tests**: Dedicated test script (`test_features.py`)

### Updated Workflow

``` plaintext
1. Load config and validate with Pydantic models
2. Initialize database with automatic schema migration
3. Query Audible API with retry logic and rate limiting
4. Find ALL matching audiobooks above confidence threshold
   - High confidence matches (≥0.7): Ready for notification
   - Low confidence matches (0.5-0.7): Flagged for manual review
   - Multiple volumes for same series ALL processed (no deduplication)
5. Store ALL good matches in the database
6. Prune released audiobooks (day after release)
7. Send notifications via enabled channels:
   - Check per-channel notification status
   - Send to unnotified channels only
   - Mark as notified per channel
8. Export to iCal if enabled
9. Cleanup old exports
```

### File Structure Updates

``` tree
src/audiostracker/
├── main.py              # Updated with multi-channel notifications
├── audible.py           # Enhanced with retry logic
├── database.py          # Multi-channel schema and operations
├── utils.py             # Retry logic and validation
├── models.py            # ✅ NEW: Pydantic models
├── ical_export.py       # ✅ NEW: iCal export functionality
├── notify/
│   ├── __init__.py
│   ├── notify.py        # ✅ UPDATED: Multi-channel dispatcher
│   ├── pushover.py      # Enhanced with retry logic
│   ├── discord.py       # ✅ NEW: Discord notifications
│   └── email.py         # ✅ NEW: Email notifications
└── config/
    ├── config.yaml      # Updated with all channels
    └── audiobooks.yaml
```

### Environment Variables Required

```bash
# Pushover
PUSHOVER_USER_KEY=your_pushover_user_key
PUSHOVER_API_TOKEN=your_pushover_api_token

# Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Email
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient1@example.com,recipient2@example.com
```

### Summary

**All requested features have been successfully implemented:**

* ✅ Multi-channel notification support with database tracking
* ✅ Better error handling with exponential backoff retry logic
* ✅ Complete notification implementations (Pushover, Discord, Email)
* ✅ iCal export functionality with batching and cleanup
* ✅ Pydantic models for validation and type safety
* ✅ Comprehensive testing suite

The system is now production-ready with enterprise-grade reliability and maintainability.
