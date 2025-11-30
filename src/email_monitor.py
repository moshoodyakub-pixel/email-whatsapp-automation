"""
Email monitoring service using Gmail API with push notifications.
Monitors inbox for new emails and triggers processing.
"""
import logging
import base64
import time
import re
from datetime import datetime, timedelta
from google.cloud import pubsub_v1
from googleapiclient.errors import HttpError
from config import Config
from gmail_auth import GmailAuthenticator

logger = logging.getLogger(__name__)

class EmailMonitor:
    """Monitors Gmail inbox using push notifications"""
    def __init__(self, on_new_email_callback):
        self.auth = GmailAuthenticator()
        self.service = None
        self.callback = on_new_email_callback
        self.processed_emails = set()
        self.watch_expiration = None
        
        # Pub/Sub setup from Config
        self.project_id = Config.PUBSUB_PROJECT_ID
        self.topic_name = Config.PUBSUB_TOPIC_NAME
        self.subscription_name = Config.PUBSUB_SUBSCRIPTION_NAME
        self.subscriber = None
    
    def initialize(self):
        logger.info("Initializing email monitor...")
        self.service = self.auth.authenticate()
        self.setup_push_notifications()
        if Config.PROCESS_EXISTING:
            logger.info("Processing existing unread emails...")
            self.process_existing_emails()
        logger.info("Email monitor initialized successfully!")
    
    def setup_push_notifications(self):
        """Setup Gmail push notifications via Pub/Sub"""
        try:
            logger.info("Setting up Gmail push notifications...")
            
            # Safely extract Project ID and Topic ID regardless of .env format

            # Extract just the project ID from the variable
            project_id_match = re.search(r'projects/([^/]+)', self.project_id)
            if project_id_match:
                project_id = project_id_match.group(1)
            else:
                project_id = self.project_id.strip()

            # Extract just the topic ID from the variable
            topic_id_match = re.search(r'topics/([^/]+)', self.topic_name)
            if topic_id_match:
                topic_id = topic_id_match.group(1)
            else:
                topic_id = self.topic_name.strip()

            # Build the canonical path
            topic_path = f"projects/{project_id}/topics/{topic_id}"

            logger.info(f"Using Pub/Sub project ID: {project_id}")
            logger.info(f"Using Pub/Sub topic path: {topic_path}")
            
            request = {
                'labelIds': ['INBOX'],
                'topicName': topic_path
            }
            
            response = self.service.users().watch(userId='me', body=request).execute()
            
            self.watch_expiration = datetime.fromtimestamp(int(response['expiration']) / 1000)
            logger.info(f"Push notifications active until: {self.watch_expiration}")
            logger.info(f"History ID: {response['historyId']}")
            
            return response
            
        except HttpError as error:
            logger.error(f"Failed to setup push notifications: {error}")
            raise

    def renew_watch(self):
        if self.watch_expiration and datetime.now() >= self.watch_expiration - timedelta(hours=1):
            logger.info("Renewing push notification watch...")
            self.setup_push_notifications()
    
    def start_listening(self):
        logger.info("Starting Pub/Sub listener...")
        self.subscriber = pubsub_v1.SubscriberClient()
        subscription_path = self.subscriber.subscription_path(self.project_id, self.subscription_name)
        
        def pubsub_callback(message):
            logger.info(f"Received push notification: {message.data}")
            message.ack()
            self.handle_push_notification(message)
        
        streaming_pull_future = self.subscriber.subscribe(subscription_path, callback=pubsub_callback)
        logger.info(f"Listening for messages on {subscription_path}...")
        
        try:
            while True:
                time.sleep(60)
                self.renew_watch()
        except KeyboardInterrupt:
            logger.info("Stopping listener...")
            streaming_pull_future.cancel()
            streaming_pull_future.result()

    def handle_push_notification(self, message):
        try:
            import json
            data = json.loads(message.data.decode('utf-8'))
            email_address = data.get('emailAddress')
            history_id = data.get('historyId')
            logger.info(f"Push notification for {email_address}, history ID: {history_id}")
            self.fetch_new_messages(history_id)
        except Exception as e:
            logger.error(f"Error handling push notification: {e}", exc_info=True)
    
    def fetch_new_messages(self, history_id):
        try:
            history = self.service.users().history().list(userId='me', startHistoryId=history_id, historyTypes=['messageAdded']).execute()
            if 'history' not in history:
                return
            for record in history['history']:
                if 'messagesAdded' in record:
                    for msg_added in record['messagesAdded']:
                        msg_id = msg_added['message']['id']
                        if msg_id in self.processed_emails:
                            continue
                        if 'INBOX' in msg_added['message'].get('labelIds', []):
                            self.process_email(msg_id)
        except HttpError as error:
            logger.error(f"Error fetching history: {error}")

    def process_email(self, email_id):
        try:
            self.processed_emails.add(email_id)
            email_data = self.get_email_data(email_id)
            if email_data:
                self.callback(email_id, email_data)
        except Exception as e:
            logger.error(f"Error processing email {email_id}: {e}", exc_info=True)

    def get_email_data(self, email_id):
        try:
            message = self.service.users().messages().get(userId='me', id=email_id, format='full').execute()
            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
            body = self.extract_body(message['payload'])
            return {'id': email_id, 'subject': subject, 'sender': sender, 'date': date, 'body': body, 'snippet': message.get('snippet', '')}
        except HttpError as error:
            logger.error(f"Error fetching email {email_id}: {error}")
            return None

    def extract_body(self, payload):
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
                elif part['mimeType'] == 'text/html' and not body and 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        elif 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        return ' '.join(body.split())[:5000]

    def process_existing_emails(self):
        try:
            results = self.service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=10).execute()
            messages = results.get('messages', [])
            if messages:
                logger.info(f"Found {len(messages)} unread emails")
                for message in messages:
                    self.process_email(message['id'])
        except HttpError as error:
            logger.error(f"Error fetching existing emails: {error}")

if __name__ == '__main__':
    def test_callback(email_id, email_data):
        print(f"\n{'='*60}\nNew Email: {email_id}\nFrom: {email_data['sender']}\nSubject: {email_data['subject']}\nBody: {email_data['body'][:200]}...\n{'='*60}\n")
    
    monitor = EmailMonitor(on_new_email_callback=test_callback)
    monitor.initialize()
    print("Email monitor is running. Press Ctrl+C to stop.")
    monitor.start_listening()
