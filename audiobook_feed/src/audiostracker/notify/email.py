import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..utils import retry_with_exponential_backoff

class EmailNotifier:
    """SMTP email notifier"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.smtp_server: str = config.get('smtp_server', '')
        self.smtp_port: int = config.get('smtp_port', 587)
        self.username: str = config.get('username', '')
        self.password: str = config.get('password', '')
        self.from_email: str = config.get('from_email', '')
        self.to_emails: List[str] = config.get('to_emails', [])
        self.use_tls: bool = config.get('use_tls', True)
        self.use_ssl: bool = config.get('use_ssl', False)
        
        # Validate required fields
        if not self.smtp_server:
            raise ValueError("Email smtp_server is required")
        if not self.from_email:
            raise ValueError("Email from_email is required")
        if not self.to_emails:
            raise ValueError("Email to_emails list is required")
        if not self.username:
            raise ValueError("Email username is required")
        if not self.password:
            raise ValueError("Email password is required")
    
    def _format_audiobook_html(self, audiobook: Dict[str, Any]) -> str:
        """Format an audiobook as HTML"""
        title = audiobook.get('title', 'Unknown Title')
        author = audiobook.get('author', 'Unknown Author')
        narrator = audiobook.get('narrator', 'Unknown Narrator')
        series = audiobook.get('series', '')
        series_number = audiobook.get('series_number', '')
        publisher = audiobook.get('publisher', 'Unknown Publisher')
        release_date = audiobook.get('release_date', 'Unknown Date')
        asin = audiobook.get('asin', '')
        
        # Create the title with series info if available
        display_title = title
        if series and series_number:
            display_title = f"{title} ({series} #{series_number})"
        elif series:
            display_title = f"{title} ({series})"
        
        # Create Audible link if ASIN is available
        if asin:
            audible_link = f'<a href="https://www.audible.com/pd/{asin}">View on Audible</a>'
        else:
            audible_link = "No Audible link available"
        
        html = f"""
        <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;">
            <h3 style="color: #1F8B4C; margin: 0 0 10px 0;">{display_title}</h3>
            <p><strong>Author:</strong> {author}</p>
            <p><strong>Narrator:</strong> {narrator}</p>
            <p><strong>Publisher:</strong> {publisher}</p>
            <p><strong>Release Date:</strong> {release_date}</p>
            <p><strong>ASIN:</strong> {asin}</p>
            <p>{audible_link}</p>
        </div>
        """
        
        return html
    
    def _format_audiobook_text(self, audiobook: Dict[str, Any]) -> str:
        """Format an audiobook as plain text"""
        title = audiobook.get('title', 'Unknown Title')
        author = audiobook.get('author', 'Unknown Author')
        narrator = audiobook.get('narrator', 'Unknown Narrator')
        series = audiobook.get('series', '')
        series_number = audiobook.get('series_number', '')
        publisher = audiobook.get('publisher', 'Unknown Publisher')
        release_date = audiobook.get('release_date', 'Unknown Date')
        asin = audiobook.get('asin', '')
        
        # Create the title with series info if available
        display_title = title
        if series and series_number:
            display_title = f"{title} ({series} #{series_number})"
        elif series:
            display_title = f"{title} ({series})"
        
        text = f"""
{display_title}
{'=' * len(display_title)}
Author: {author}
Narrator: {narrator}
Publisher: {publisher}
Release Date: {release_date}
ASIN: {asin}
Audible Link: https://www.audible.com/pd/{asin}

"""
        
        return text
    
    @retry_with_exponential_backoff(max_retries=3)
    def send_single_notification(self, audiobook: Dict[str, Any]) -> bool:
        """Send notification for a single audiobook"""
        try:
            title = audiobook.get('title', 'Unknown Title')
            subject = f"📚 New Audiobook: {title}"
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            # Create text and HTML versions
            text_content = f"New audiobook found:\n\n{self._format_audiobook_text(audiobook)}"
            html_content = f"""
            <html>
            <body>
                <h2>📚 New Audiobook Found</h2>
                {self._format_audiobook_html(audiobook)}
                <p><em>Sent by AudioStacker on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
            </body>
            </html>
            """
            
            # Attach parts
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            msg.attach(text_part)
            msg.attach(html_part)
              # Send email
            self._send_email(msg)
            
            logging.debug(f"Successfully sent email notification for: {title}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send email notification: {e}")
            raise e

    @retry_with_exponential_backoff(max_retries=3)
    def send_digest(self, audiobooks: List[Dict[str, Any]], ical_files: Optional[List[str]] = None) -> bool:
        """Send a digest notification for multiple audiobooks"""
        if not audiobooks:
            return True
        
        try:
            count = len(audiobooks)
            subject = f"📚 AudioStacker Digest - {count} New Audiobook{'s' if count != 1 else ''}"
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            # Create text version
            text_content = f"AudioStacker found {count} new audiobook{'s' if count != 1 else ''}:\n\n"
            for i, audiobook in enumerate(audiobooks, 1):
                text_content += f"{i}. {self._format_audiobook_text(audiobook)}"
            
            # Create HTML version
            html_content = f"""
            <html>
            <body>
                <h2>📚 AudioStacker Digest</h2>
                <p>Found {count} new audiobook{'s' if count != 1 else ''}:</p>
            """
            
            for audiobook in audiobooks:
                html_content += self._format_audiobook_html(audiobook)
            
            html_content += f"""
                <p><em>Sent by AudioStacker on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
            </body>
            </html>
            """
              # Attach parts
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Attach iCal files if provided
            if ical_files:
                for ical_file in ical_files:
                    if os.path.exists(ical_file):
                        try:
                            with open(ical_file, 'rb') as f:
                                attachment = MIMEBase('text', 'calendar')
                                attachment.set_payload(f.read())
                                encoders.encode_base64(attachment)
                                attachment.add_header(
                                    'Content-Disposition',
                                    f'attachment; filename="{os.path.basename(ical_file)}"'
                                )
                                msg.attach(attachment)
                                logging.debug(f"Attached iCal file: {ical_file}")
                        except Exception as e:
                            logging.warning(f"Failed to attach iCal file {ical_file}: {e}")
                    else:
                        logging.warning(f"iCal file not found: {ical_file}")
            
            # Send email
            self._send_email(msg)
            
            logging.info(f"Successfully sent email digest for {count} audiobooks")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send email digest: {e}")
            raise e
    
    def _send_email(self, msg: MIMEMultipart):
        """Send an email message using SMTP"""
        if self.use_ssl:
            server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
        else:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()
        
        try:
            server.login(self.username, self.password)
            server.send_message(msg)
            logging.debug("Email sent successfully")
        finally:
            server.quit()
    
    def test_connection(self) -> bool:
        """Test the SMTP connection"""
        try:
            subject = "AudioStacker Test Email"
            
            # Create test message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            text_content = "This is a test email from AudioStacker to verify the email configuration."
            html_content = """
            <html>
            <body>
                <h2>🧪 AudioStacker Test Email</h2>
                <p>This is a test email to verify the email configuration.</p>
                <p><em>If you received this, your email notifications are working correctly!</em></p>
            </body>
            </html>
            """
            
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send test email
            self._send_email(msg)
            
            logging.info("Email test successful")
            return True
            
        except Exception as e:
            logging.error(f"Email test failed: {e}")
            return False
