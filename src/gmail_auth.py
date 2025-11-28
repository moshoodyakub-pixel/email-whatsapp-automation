"""
Gmail API authentication and token management.
Handles OAuth2 flow and token persistence.
"""

import os
import pickle
import logging
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import Config

logger = logging.getLogger(__name__)


class GmailAuthenticator:
    """Handles Gmail API authentication"""
    
    def __init__(self):
        self.creds = None
        self.service = None
        self.credentials_path = Config.BASE_DIR / Config.GMAIL_CREDENTIALS_PATH
        self.token_path = Config.BASE_DIR / Config.GMAIL_TOKEN_PATH
    
    def authenticate(self):
        """
        Authenticate with Gmail API using OAuth2.
        Returns authenticated Gmail service.
        """
        logger.info("Starting Gmail authentication...")
        
        # Load existing token if available
        if self.token_path.exists():
            logger.info("Loading existing token...")
            with open(self.token_path, 'rb') as token:
                self.creds = pickle.load(token)
        
        # If no valid credentials, authenticate
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                logger.info("Refreshing expired token...")
                self.creds.refresh(Request())
            else:
                logger.info("Starting OAuth2 flow...")
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"Credentials file not found at {self.credentials_path}\n"
                        "Please download OAuth2 credentials from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path),
                    Config.GMAIL_SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            
            # Save the credentials for next run
            logger.info("Saving credentials...")
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)
        
        # Build Gmail service
        self.service = build('gmail', 'v1', credentials=self.creds)
        logger.info("Gmail authentication successful!")
        
        return self.service
    
    def get_service(self):
        """Get authenticated Gmail service"""
        if not self.service:
            self.authenticate()
        return self.service
    
    def revoke_token(self):
        """Revoke the current token (for testing/debugging)"""
        if self.token_path.exists():
            logger.info("Revoking token...")
            self.token_path.unlink()
            logger.info("Token revoked. Re-authentication required.")


def main():
    """Standalone authentication script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Gmail API Authentication')
    parser.add_argument('--revoke', action='store_true', help='Revoke existing token')
    parser.add_argument('--test', action='store_true', help='Test authentication')
    args = parser.parse_args()
    
    auth = GmailAuthenticator()
    
    if args.revoke:
        auth.revoke_token()
        return
    
    # Authenticate
    service = auth.authenticate()
    
    if args.test:
        # Test by fetching user profile
        logger.info("Testing Gmail API access...")
        profile = service.users().getProfile(userId='me').execute()
        logger.info(f"Successfully authenticated as: {profile['emailAddress']}")
        logger.info(f"Total messages: {profile.get('messagesTotal', 'N/A')}")
        logger.info(f"Total threads: {profile.get('threadsTotal', 'N/A')}")


if __name__ == '__main__':
    main()
