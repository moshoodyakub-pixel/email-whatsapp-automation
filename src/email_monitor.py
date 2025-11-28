"""
Email monitoring service using Gmail API with push notifications.
Monitors inbox for new emails and triggers processing.
"""

import logging
import base64
import time
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from google.cloud import pubsub_v1
from googleapiclient.errors import HttpError

from config import Config
from gmail_auth import GmailAuthenticator

logger = logging.getLogger(__name__)


class EmailMonitor:
    """Monitors Gmail inbox using push notifications"""
    
    def __init__(self, on_new_email_callback):
        """
        Initialize email monitor.
        
        Args:
            on_new_email_callback: Function to call when new email arrives.
                                   Should accept (email_id, email_data) as parameters.
        """
        self.auth = GmailAuthenticator()
        self.service = None
        self.callback = on_new_email_callback
        self.processed_emails = set()
        self.watch_expiration = None
        
        # Pub/Sub setup
        self.project_id = Config.PUBSUB_PROJECT_ID
        self.topic_name = Config.PUBSUB_TOPIC_NAME
        self.subscription_name = Config.PUBSUB_SUBSCRIPTION_NAME
        self.subscriber = None
    
    def initialize(self):
        """Initialize Gmail service and setup push notifications"""
        logger.info("Initializing email monitor...")
        
        # Authenticate with Gmail
        self.service = self.auth.authenticate()
        
        # Setup push notifications
        self.setup_push_notifications()
        
        # Process existing unread emails if configured
        if Config.PROCESS_EXISTING:
            logger.info("Processing existing unread emails...")
            self.process_existing_emails()
        
        logger.info("Email monitor initialized successfully!")
    
    def setup_push_notifications(self):
        """Setup Gmail push notifications via Pub/Sub"""
        try:
            logger.info("Setting up Gmail push notifications...")
            
            # Create watch request
            topic_path = f"projects/{self.project_id}/topics/{self.topic_name}"
            
            request = {
                'labelIds': ['INBOX'],
                'topicName': topic_path
            }
            
            # Start watching
            response = self.service.users().watch(userId='me', body=request).execute()
            
            self.watch_expiration = datetime.fromtimestamp(int(response['expiration']) / 1000)
            logger.info(f"Push notifications active until: {self.watch_expiration}")
            logger.info(f"History ID: {response['historyId']}")
            
            return response
            
        except HttpError as error:
            logger.error(f"Failed to setup push notifications: {error}")
            raise
    
    def renew_watch(self):
        """Renew push notification watch (expires after 7 days)"""
        if self.watch_expiration and datetime.now() >= self.watch_expiration - timedelta(hours=1):
            logger.info("Renewing push notification watch...")
            self.setup_push_notifications()
    
    def start_listening(self):
        """Start listening for push notifications"""
        logger.info("Starting Pub/Sub listener...")
        
        # Create subscriber
        self.subscriber = pubsub_v1.SubscriberClient()
        subscription_path = self.subscriber.subscription_path(
            self.project_id,
            self.subscription_name
        )
        
        # Define callback for messages
        def pubsub_callback(message):
            logger.info(f"Received push notification: {message.data}")
            message.ack()
            
            # Process the notification
            self.handle_push_notification(message)
        
        # Subscribe
        streaming_pull_future = self.subscriber.subscribe(
            subscription_path,
            callback=pubsub_callback
        )
        
        logger.info(f"Listening for messages on {subscription_path}...")
        
        try:
            # Keep the main thread alive
            while True:
                time.sleep(60)
                self.renew_watch()  # Check if watch needs renewal
        except KeyboardInterrupt:
            logger.info("Stopping listener...")
            streaming_pull_future.cancel()
            streaming_pull_future.result()
    
    def handle_push_notification(self, message):
        """Handle incoming push notification from Gmail"""
        try:
            # Decode message data
            import json
            data = json.loads(message.data.decode('utf-8'))
            
            email_address = data.get('emailAddress')
            history_id = data.get('historyId')
            
            logger.info(f"Push notification for {email_address}, history ID: {history_id}")
            
            # Fetch new messages using history
            self.fetch_new_messages(history_id)
            
        except Exception as e:
            logger.error(f"Error handling push notification: {e}", exc_info=True)
    
    def fetch_new_messages(self, history_id):
        """Fetch new messages using Gmail history API"""
        try:
            # Get history of changes
            history = self.service.users().history().list(
                userId='me',
                startHistoryId=history_id,
                historyTypes=['messageAdded']
            ).execute()
            
            if 'history' not in history:
                logger.debug("No new messages in history")
                return
            
            # Process each new message
            for record in history['history']:
                if 'messagesAdded' in record:
                    for msg_added in record['messagesAdded']:
                        message = msg_added['message']
                        msg_id = message['id']
                        
                        # Skip if already processed
                        if msg_id in self.processed_emails:
                            continue
                        
                        # Check if message is in INBOX
                        if 'INBOX' in message.get('labelIds', []):
                            logger.info(f"New email detected: {msg_id}")
                            self.process_email(msg_id)
            
        except HttpError as error:
            logger.error(f"Error fetching history: {error}")
    
    def process_email(self, email_id):
        """Process a single email"""
        try:
            # Mark as processed
            self.processed_emails.add(email_id)
            
            # Fetch full email data
            email_data = self.get_email_data(email_id)
            
            if email_data:
                # Call the callback function
                self.callback(email_id, email_data)
            
        except Exception as e:
            logger.error(f"Error processing email {email_id}: {e}", exc_info=True)
    
    def get_email_data(self, email_id):
        """Fetch email data from Gmail API"""
        try:
            # Get message
            message = self.service.users().messages().get(
                userId='me',
                id=email_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
            
            # Extract body
            body = self.extract_body(message['payload'])
            
            email_data = {
                'id': email_id,
                'subject': subject,
                'sender': sender,
                'date': date,
                'body': body,
                'snippet': message.get('snippet', '')
            }
            
            logger.info(f"Fetched email: {subject} from {sender}")
            return email_data
            
        except HttpError as error:
            logger.error(f"Error fetching email {email_id}: {error}")
            return None
    
    def extract_body(self, payload):
        """Extract email body from payload"""
        body = ""
        
        if 'parts' in payload:
            # Multipart message
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html' and not body:
                    if 'data' in part['body']:
                        # Fallback to HTML if no plain text
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        else:
            # Simple message
            if 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        # Clean up body (remove excessive whitespace)
        body = ' '.join(body.split())
        
        # Limit body length for processing
        if len(body) > 5000:
            body = body[:5000] + "... [truncated]"
        
        return body
    
    def process_existing_emails(self):
        """Process existing unread emails in inbox"""
        try:
            # Query for unread messages
            results = self.service.users().messages().list(
                userId='me',
                labelIds=['INBOX', 'UNREAD'],
                maxResults=10  # Limit to avoid overwhelming
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                logger.info("No existing unread emails")
                return
            
            logger.info(f"Found {len(messages)} unread emails")
            
            for message in messages:
                email_id = message['id']
                self.process_email(email_id)
            
        except HttpError as error:
            logger.error(f"Error fetching existing emails: {error}")


def main():
    """Test email monitor"""
    def test_callback(email_id, email_data):
        print(f"\n{'='*60}")
        print(f"New Email: {email_id}")
        print(f"From: {email_data['sender']}")
        print(f"Subject: {email_data['subject']}")
        print(f"Body: {email_data['body'][:200]}...")
        print(f"{'='*60}\n")
    
    monitor = EmailMonitor(on_new_email_callback=test_callback)
    monitor.initialize()
    
    print("Email monitor is running. Press Ctrl+C to stop.")
    monitor.start_listening()


if __name__ == '__main__':
    main()
