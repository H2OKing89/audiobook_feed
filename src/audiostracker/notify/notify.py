import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..utils import retry_with_exponential_backoff, safe_execute
from .pushover import PushoverNotifier
from .discord import DiscordNotifier
from .email import EmailNotifier

class NotificationDispatcher:
    """Central dispatcher for all notification channels"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.channels = {}
        self._initialize_channels()
    
    def _initialize_channels(self):
        """Initialize enabled notification channels"""
        # Pushover
        if self.config.get('pushover', {}).get('enabled', False):
            try:
                self.channels['pushover'] = PushoverNotifier(self.config['pushover'])
                logging.info("Pushover notification channel initialized")
            except Exception as e:
                logging.error(f"Failed to initialize Pushover: {e}")
        
        # Discord
        if self.config.get('discord', {}).get('enabled', False):
            try:
                self.channels['discord'] = DiscordNotifier(self.config['discord'])
                logging.info("Discord notification channel initialized")
            except Exception as e:
                logging.error(f"Failed to initialize Discord: {e}")
        
        # Email
        if self.config.get('email', {}).get('enabled', False):
            try:
                self.channels['email'] = EmailNotifier(self.config['email'])
                logging.info("Email notification channel initialized")
            except Exception as e:
                logging.error(f"Failed to initialize Email: {e}")
        
        logging.info(f"Initialized {len(self.channels)} notification channels: {list(self.channels.keys())}")
    
    def get_enabled_channels(self) -> List[str]:
        """Get list of enabled channel names"""
        return list(self.channels.keys())
    
    @retry_with_exponential_backoff(max_retries=3)
    def send_notification(self, channel: str, audiobooks: List[Dict[str, Any]], ical_files: Optional[List[str]] = None) -> bool:
        """
        Send notification for a list of audiobooks to a specific channel
        
        Args:
            channel: Channel name (e.g., 'pushover', 'discord')
            audiobooks: List of audiobook dictionaries
            ical_files: Optional list of iCal file paths to attach
            
        Returns:
            bool: True if notification was sent successfully
        """
        if not audiobooks:
            logging.debug(f"No audiobooks to notify for channel: {channel}")
            return True
        if channel not in self.channels:
            logging.warning(f"Channel '{channel}' not available or not enabled")
            return False
        
        try:
            notifier = self.channels[channel]
            
            # For Discord, pass ical_files to show note about availability
            # For Email, pass ical_files to attach them
            # For Pushover, don't pass ical_files (not supported)
            if channel == 'discord':
                success = notifier.send_digest(audiobooks, ical_files)
            elif channel == 'email':
                success = notifier.send_digest(audiobooks, ical_files)
            else:  # pushover or other channels
                success = notifier.send_digest(audiobooks)
            
            if success:
                logging.info(f"Successfully sent notification to {channel} for {len(audiobooks)} audiobooks" +
                           (f" with {len(ical_files)} iCal files" if ical_files and channel == 'email' else ""))
            else:
                logging.error(f"Failed to send notification to {channel}")
            
            return success
            
        except Exception as e:
            logging.error(f"Error sending notification to {channel}: {e}")
            raise e
    
    def send_to_all_channels(self, audiobooks: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Send notifications to all enabled channels
        
        Returns:
            Dict[str, bool]: Channel name -> success status
        """
        results = {}
        
        for channel in self.channels:
            success, _, exception = safe_execute(
                self.send_notification, channel, audiobooks
            )
            results[channel] = success
            
            if not success and exception:
                logging.error(f"Failed to send to {channel}: {exception}")
        
        return results
    
    def send_daily_digest(self, audiobooks: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Send daily digest to all channels
        
        Args:
            audiobooks: List of new audiobooks found today
            
        Returns:
            Dict[str, bool]: Channel name -> success status
        """
        if not audiobooks:
            logging.info("No new audiobooks found for daily digest")
            return {}
        
        logging.info(f"Sending daily digest with {len(audiobooks)} audiobooks")
        return self.send_to_all_channels(audiobooks)

# Convenience functions for easy import
def create_dispatcher(config: Dict[str, Any]) -> NotificationDispatcher:
    """Factory function to create a notification dispatcher"""
    return NotificationDispatcher(config)

def send_notifications_for_audiobooks(audiobooks: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, bool]:
    """
    Convenience function to send notifications for a list of audiobooks
    
    Args:
        audiobooks: List of audiobook dictionaries
        config: Configuration dictionary
        
    Returns:
        Dict[str, bool]: Channel name -> success status
    """
    dispatcher = create_dispatcher(config)
    return dispatcher.send_daily_digest(audiobooks)