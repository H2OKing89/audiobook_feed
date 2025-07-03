from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import date, datetime
import re
import logging

class AudiobookEntry(BaseModel):
    """Represents a wanted audiobook entry from audiobooks.yaml"""
    title: Optional[str] = None
    series: Optional[str] = None
    publisher: Optional[str] = None
    narrator: Optional[List[str]] = None
    
    @validator('narrator', pre=True)
    def validate_narrator(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return [v]
        return v

class Audiobook(BaseModel):
    """Represents an audiobook from the Audible API"""
    asin: str = Field(..., description="Audible ASIN identifier")
    title: str
    author: str
    narrator: str
    publisher: str
    series: str
    series_number: str
    release_date: str = Field(..., description="Release date in YYYY-MM-DD format")
    link: str
    last_checked: Optional[datetime] = None
    notified_channels: Optional[Dict[str, bool]] = Field(default_factory=dict)
    
    @validator('release_date')
    def validate_release_date(cls, v):
        try:
            # First validate the format
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
                raise ValueError('release_date must be in YYYY-MM-DD format')
            
            # Then validate it's a valid date
            dt = datetime.strptime(v, '%Y-%m-%d')
            
            # Check for reasonable date range (e.g., not in the distant past or future)
            current_year = datetime.now().year
            if dt.year < current_year - 5 or dt.year > current_year + 10:
                logging.warning(f"Unusual release year detected: {dt.year} for date {v}")
            
            return v
        except ValueError as e:
            raise ValueError(f'Invalid release date: {e}')
    
    @property
    def release_date_obj(self) -> date:
        return datetime.strptime(self.release_date, '%Y-%m-%d').date()
    
    def is_released(self) -> bool:
        return self.release_date_obj <= date.today()
    
    def is_notified_for_channel(self, channel: str) -> bool:
        if self.notified_channels is None:
            return False
        return self.notified_channels.get(channel, False)
    
    def mark_notified_for_channel(self, channel: str):
        if self.notified_channels is None:
            self.notified_channels = {}
        self.notified_channels[channel] = True

class NotificationConfig(BaseModel):
    """Base configuration for notification channels"""
    enabled: bool = False

class PushoverConfig(NotificationConfig):
    """Pushover-specific configuration"""
    user_key: Optional[str] = None
    api_token: Optional[str] = None
    sound: Optional[str] = "pushover"
    priority: int = Field(default=0, ge=-2, le=2)
    device: Optional[str] = ""

class DiscordConfig(NotificationConfig):
    """Discord-specific configuration"""
    webhook_url: Optional[str] = None
    username: str = "AudioStacker"
    avatar_url: Optional[str] = None
    color: str = "0x1F8B4C"

class EmailConfig(NotificationConfig):
    """Email-specific configuration"""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    use_tls: bool = True
    use_ssl: bool = False
    from_email: Optional[str] = None
    to_emails: List[str] = Field(default_factory=list)
    username: Optional[str] = None
    password: Optional[str] = None

class ICalConfig(BaseModel):
    """iCal export configuration"""
    enabled: bool = False
    interval: int = 60
    batch: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "max_books": 10,
        "file_path": "data/ical_export/"
    })

class Config(BaseModel):
    """Main configuration model"""
    max_results: int = Field(50, ge=1, le=50)
    log_level: str = Field("INFO", pattern=r'^(DEBUG|INFO|WARNING|ERROR)$')
    log_format: str = Field("json", pattern=r'^(json|text)$')
    pushover: PushoverConfig = Field(default_factory=lambda: PushoverConfig())
    discord: DiscordConfig = Field(default_factory=lambda: DiscordConfig())
    email: EmailConfig = Field(default_factory=lambda: EmailConfig())
    ical: ICalConfig = Field(default_factory=lambda: ICalConfig())
    rate_limits: Dict[str, int] = Field(default_factory=lambda: {
        "audible_api_per_minute": 10,
        "notification_per_minute": 5,
        "db_ops_per_second": 20
    })
    
    class Config:
        extra = "allow"  # Allow additional fields for future expansion
