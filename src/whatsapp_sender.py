"""
WhatsApp sender - Python client for WhatsApp Web.js service.
Communicates with the Node.js WhatsApp service via HTTP.
"""

import logging
import requests
import time
from typing import Optional
from datetime import datetime

from config import Config

logger = logging.getLogger(__name__)


class WhatsAppSender:
    """Sends messages to WhatsApp via the Node.js service"""
    
    def __init__(self):
        """Initialize WhatsApp sender"""
        self.service_url = Config.WHATSAPP_SERVICE_URL
        self.target_number = Config.YOUR_WHATSAPP_NUMBER
        self.max_retries = Config.MAX_RETRIES
        self.retry_delay = Config.RETRY_DELAY
        
        logger.info(f"WhatsApp sender initialized (service: {self.service_url})")
    
    def wait_for_ready(self, timeout=60):
        """
        Wait for WhatsApp service to be ready.
        
        Args:
            timeout: Maximum time to wait in seconds
        
        Returns:
            True if ready, False if timeout
        """
        logger.info("Waiting for WhatsApp service to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.service_url}/health", timeout=5)
                data = response.json()
                
                if data.get('status') == 'ready':
                    logger.info("WhatsApp service is ready!")
                    return True
                
                status = data.get('status', 'unknown')
                logger.info(f"WhatsApp status: {status}")
                
                if data.get('hasQR'):
                    logger.warning(f"⚠️  QR code available at: {self.service_url}/qr")
                    logger.warning("Please scan the QR code to authenticate WhatsApp")
                
            except requests.exceptions.RequestException as e:
                logger.debug(f"Service not ready: {e}")
            
            time.sleep(5)
        
        logger.error("Timeout waiting for WhatsApp service")
        return False
    
    def send_message(self, message: str, number: Optional[str] = None) -> bool:
        """
        Send a message to WhatsApp.
        
        Args:
            message: Message text to send
            number: Optional phone number (uses configured number if not provided)
        
        Returns:
            True if sent successfully, False otherwise
        """
        target = number or self.target_number
        
        logger.info(f"Sending WhatsApp message to {target}")
        logger.debug(f"Message: {message[:100]}...")
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.service_url}/send",
                    json={
                        'number': target,
                        'message': message
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        logger.info("✅ WhatsApp message sent successfully!")
                        return True
                    else:
                        error = data.get('error', 'Unknown error')
                        logger.error(f"WhatsApp service error: {error}")
                
                elif response.status_code == 503:
                    logger.warning("WhatsApp service not ready, waiting...")
                    if not self.wait_for_ready(timeout=30):
                        logger.error("WhatsApp service did not become ready")
                        return False
                    continue
                
                else:
                    logger.error(f"HTTP error {response.status_code}: {response.text}")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
            
            # Retry with delay
            if attempt < self.max_retries - 1:
                logger.info(f"Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
        
        logger.error("Failed to send WhatsApp message after all retries")
        return False
    
    def send_email_notification(self, email_data: dict, summary: str) -> bool:
        """
        Send a formatted email notification to WhatsApp.
        
        Args:
            email_data: Email data dictionary
            summary: AI-generated summary
        
        Returns:
            True if sent successfully
        """
        # Format the message
        sender = email_data.get('sender', 'Unknown')
        subject = email_data.get('subject', 'No Subject')
        date = email_data.get('date', '')
        
        # Parse and format date
        timestamp = self._format_timestamp(date)
        
        # Build message
        message = f"📧 *New Email*\n\n"
        message += f"👤 *From:* {sender}\n\n"
        message += f"📌 *Subject:* {subject}\n\n"
        message += f"📝 *Summary:*\n{summary}\n\n"
        message += f"🕐 *Received:* {timestamp}"
        
        return self.send_message(message)
    
    def _format_timestamp(self, date_str: str) -> str:
        """Format email date string to readable timestamp"""
        if not date_str:
            return datetime.now().strftime('%I:%M %p, %b %d')
        
        try:
            # Try to parse common email date formats
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            return dt.strftime('%I:%M %p, %b %d')
        except:
            # Fallback to current time
            return datetime.now().strftime('%I:%M %p, %b %d')
    
    def test_connection(self) -> bool:
        """
        Test connection to WhatsApp service.
        
        Returns:
            True if connection successful
        """
        try:
            logger.info("Testing WhatsApp service connection...")
            
            response = requests.post(
                f"{self.service_url}/test",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info("✅ WhatsApp test message sent!")
                    return True
            
            logger.error(f"Test failed: {response.text}")
            return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection test failed: {e}")
            return False


def main():
    """Test WhatsApp sender"""
    import argparse
    
    parser = argparse.ArgumentParser(description='WhatsApp Sender Test')
    parser.add_argument('--test', action='store_true', help='Send test message')
    parser.add_argument('--message', type=str, help='Custom message to send')
    args = parser.parse_args()
    
    sender = WhatsAppSender()
    
    # Wait for service to be ready
    if not sender.wait_for_ready(timeout=120):
        print("\n❌ WhatsApp service is not ready.")
        print(f"Please ensure the service is running: node src/whatsapp_service.js")
        print(f"Or authenticate first: node src/whatsapp_init.js")
        return
    
    if args.test:
        sender.test_connection()
    elif args.message:
        sender.send_message(args.message)
    else:
        # Send sample email notification
        sample_email = {
            'sender': 'John Doe <john@example.com>',
            'subject': 'Test Email Notification',
            'date': datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        }
        
        sample_summary = "This is a test email notification from your automation bot. Everything is working correctly!"
        
        sender.send_email_notification(sample_email, sample_summary)


if __name__ == '__main__':
    main()
