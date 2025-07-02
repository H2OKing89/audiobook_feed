# AudioStacker

A tool for tracking and notifying users about upcoming audiobook releases from Audible.

## Features

- **Audiobook Tracking**: Automatically search Audible for new audiobooks based on configured authors and series
- **Multi-Match Processing**: Identifies and processes ALL matching audiobooks above a confidence threshold (multiple volumes, editions, etc.)
- **Multiple Notification Channels**: Support for Pushover, Discord, and Email notifications
- **Calendar Integration**: Export upcoming releases as iCalendar (.ics) files for calendar applications
- **Configurable**: Easy YAML-based configuration with environment variable support
- **Database Storage**: Local SQLite database for tracking audiobooks and notification status with automatic cleanup on release date

## Installation

1. Clone this repository

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure your settings in `src/audiostracker/config/config.yaml`

4. Set up your audiobook tracking preferences in `src/audiostracker/config/audiobooks.yaml`

5. Create a `.env` file in the `src/audiostracker/config` directory with your API keys and credentials

## Usage

Run the main script:

```bash
python -m src.audiostracker.main
```

### Configuration

#### Environment Variables

Create a `.env` file in the `src/audiostracker/config` directory with the following variables:

``` env
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

#### Audiobook Configuration

Edit the `src/audiostracker/config/audiobooks.yaml` file to specify which authors and series you want to track:

```yaml
audiobooks:
  author:
    "Author Name":
      - title: "Book Title"
        series: "Series Name"
        publisher: "Publisher Name"
        narrator:
          - "Narrator Name"
```

#### Database Configuration

The database automatically removes audiobooks on their release date. You can customize this in `config.yaml`:

```yaml
database:
  cleanup_grace_period_days: 0  # 0 = remove on release day, >0 = keep for N days after release
  vacuum_interval_days: 7       # automatically optimize the database every 7 days
```

## License

MIT
