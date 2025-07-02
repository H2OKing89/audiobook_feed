import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..utils import retry_with_exponential_backoff

class DiscordNotifier:
    """Discord webhook notifier"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.webhook_url: str = config.get('webhook_url', '')
        self.username = config.get('username', 'AudioStacker')
        self.avatar_url = config.get('avatar_url')
        self.color = int(config.get('color', '0x1F8B4C'), 16)  # Default green
        
        if not self.webhook_url:
            raise ValueError("Discord webhook_url is required")
        
        # Ensure webhook_url is a string
        if not isinstance(self.webhook_url, str):
            raise ValueError("Discord webhook_url must be a string")
    
    def _format_audiobook_embed(self, audiobook: Dict[str, Any]) -> Dict[str, Any]:
        """Format an audiobook as a Discord embed"""
        title = audiobook.get('title', 'Unknown Title')
        author = audiobook.get('author', 'Unknown Author')
        narrator = audiobook.get('narrator', 'Unknown Narrator')
        series = audiobook.get('series', '')
        series_number = audiobook.get('series_number', '')
        publisher = audiobook.get('publisher', 'Unknown Publisher')
        release_date = audiobook.get('release_date', 'Unknown Date')
        asin = audiobook.get('asin', '')
        
        # Create the title with series info if available
        embed_title = title
        if series and series_number:
            embed_title = f"{title} ({series} #{series_number})"
        elif series:
            embed_title = f"{title} ({series})"
        
        # Create description
        description = f"**Author:** {author}\n**Narrator:** {narrator}\n**Publisher:** {publisher}\n**Release Date:** {release_date}"
        
        embed = {
            "title": embed_title,
            "description": description,
            "color": self.color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": f"ASIN: {asin}"
            }
        }
        
        # Add Audible link if ASIN is available
        if asin:
            embed["url"] = f"https://www.audible.com/pd/{asin}"
        
        return embed
    
    @retry_with_exponential_backoff(max_retries=3)
    def send_single_notification(self, audiobook: Dict[str, Any]) -> bool:
        """Send notification for a single audiobook"""
        try:
            embed = self._format_audiobook_embed(audiobook)
            
            payload = {
                "username": self.username,
                "embeds": [embed]
            }
            
            if self.avatar_url:
                payload["avatar_url"] = self.avatar_url
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            logging.debug(f"Successfully sent Discord notification for: {audiobook.get('title', 'Unknown')}")
            return True
            
        except requests.RequestException as e:
            logging.error(f"Failed to send Discord notification: {e}")
            raise e
        except Exception as e:
            logging.error(f"Unexpected error sending Discord notification: {e}")
            raise e
    
    @retry_with_exponential_backoff(max_retries=3)
    def send_digest(self, audiobooks: List[Dict[str, Any]], ical_files: Optional[List[str]] = None) -> bool:
        """Send a digest notification for multiple audiobooks"""
        if not audiobooks:
            return True
        
        try:
            # Discord has a limit of 10 embeds per message
            MAX_EMBEDS_PER_MESSAGE = 10
            
            for i in range(0, len(audiobooks), MAX_EMBEDS_PER_MESSAGE):
                batch = audiobooks[i:i + MAX_EMBEDS_PER_MESSAGE]
                embeds = [self._format_audiobook_embed(book) for book in batch]
                
                # Create header message for the batch
                if len(audiobooks) > MAX_EMBEDS_PER_MESSAGE:
                    batch_info = f" (Batch {i//MAX_EMBEDS_PER_MESSAGE + 1})"
                else:
                    batch_info = ""
                
                content = f"📚 **New Audiobooks Found{batch_info}** - {len(batch)} book{'s' if len(batch) != 1 else ''}"
                
                # Add note about iCal files if present (Discord doesn't support file attachments via webhooks)
                if ical_files:
                    content += f"\n\n📅 **iCal files generated:** {len(ical_files)} file{'s' if len(ical_files) != 1 else ''} (available via email notifications)"
                
                payload = {
                    "username": self.username,
                    "content": content,
                    "embeds": embeds
                }
                
                if self.avatar_url:
                    payload["avatar_url"] = self.avatar_url
                
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                response.raise_for_status()
                logging.debug(f"Successfully sent Discord digest batch {i//MAX_EMBEDS_PER_MESSAGE + 1}")
            
            logging.info(f"Successfully sent Discord digest for {len(audiobooks)} audiobooks")
            return True
            
        except requests.RequestException as e:
            logging.error(f"Failed to send Discord digest: {e}")
            raise e
        except Exception as e:
            logging.error(f"Unexpected error sending Discord digest: {e}")
            raise e
    
    def test_connection(self) -> bool:
        """Test the Discord webhook connection"""
        try:
            test_embed = {
                "title": "AudioStacker Test",
                "description": "Testing Discord webhook connection",
                "color": self.color,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            payload = {
                "username": self.username,
                "content": "🧪 **Test Notification**",
                "embeds": [test_embed]
            }
            
            if self.avatar_url:
                payload["avatar_url"] = self.avatar_url
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            response.raise_for_status()
            logging.info("Discord webhook test successful")
            return True
            
        except Exception as e:
            logging.error(f"Discord webhook test failed: {e}")
            return False
