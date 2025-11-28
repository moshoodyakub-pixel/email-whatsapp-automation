"""
Configuration management for Email-to-WhatsApp automation platform.
Loads environment variables and provides centralized configuration.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / 'config' / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Central configuration class"""
    
    # Project paths
    BASE_DIR = Path(__file__).parent.parent
    CONFIG_DIR = BASE_DIR / 'config'
    LOGS_DIR = BASE_DIR / 'logs'
    
    # Gmail Configuration
    GMAIL_CREDENTIALS_PATH = os.getenv('GMAIL_CREDENTIALS_PATH', 'config/credentials.json')
    GMAIL_TOKEN_PATH = os.getenv('GMAIL_TOKEN_PATH', 'config/token.pickle')
    GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/pubsub']
    
    # Google Cloud Pub/Sub Configuration
    PUBSUB_PROJECT_ID = os.getenv('PUBSUB_PROJECT_ID', '')
    PUBSUB_TOPIC_NAME = os.getenv('PUBSUB_TOPIC_NAME', 'gmail-notifications')
    PUBSUB_SUBSCRIPTION_NAME = os.getenv('PUBSUB_SUBSCRIPTION_NAME', 'gmail-sub')
    
    # Google Gemini AI Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL = 'gemini-pro'
    
    # WhatsApp Configuration
    YOUR_WHATSAPP_NUMBER = os.getenv('YOUR_WHATSAPP_NUMBER', '')
    WHATSAPP_SESSION_PATH = os.getenv('WHATSAPP_SESSION_PATH', '.wwebjs_auth')
    WHATSAPP_SERVICE_URL = 'http://localhost:3000'
    
    # Monitoring Settings
    PROCESS_EXISTING = os.getenv('PROCESS_EXISTING', 'false').lower() == 'true'
    SUMMARY_LENGTH = os.getenv('SUMMARY_LENGTH', 'standard')
    EMAIL_CHECK_INTERVAL = int(os.getenv('EMAIL_CHECK_INTERVAL', '300'))
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', '10485760'))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    # Application Settings
    TIMEZONE = os.getenv('TIMEZONE', 'UTC')
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '5'))
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present"""
        errors = []
        
        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is not set")
        
        if not cls.YOUR_WHATSAPP_NUMBER:
            errors.append("YOUR_WHATSAPP_NUMBER is not set")
        
        if not cls.PUBSUB_PROJECT_ID:
            errors.append("PUBSUB_PROJECT_ID is not set")
        
        # Check if credentials file exists
        creds_path = cls.BASE_DIR / cls.GMAIL_CREDENTIALS_PATH
        if not creds_path.exists():
            errors.append(f"Gmail credentials file not found at {creds_path}")
        
        if errors:
            raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
        
        return True
    
    @classmethod
    def get_summary_prompt(cls):
        """Get the AI prompt template based on summary length"""
        prompts = {
            'brief': """Summarize this email in ONE concise sentence.
Include only the most critical information.

From: {sender}
Subject: {subject}
Body: {body}

Provide only the summary, no additional text.""",
            
            'standard': """Summarize this email in 2-3 clear sentences.
Include: who sent it, what it's about, and any action needed.

From: {sender}
Subject: {subject}
Body: {body}

Format for WhatsApp messaging. Be concise and actionable.""",
            
            'detailed': """Provide a comprehensive summary of this email.
Include: sender, main topic, key points, and any action items or deadlines.

From: {sender}
Subject: {subject}
Body: {body}

Format the summary for WhatsApp with clear structure. Use bullet points if needed."""
        }
        
        return prompts.get(cls.SUMMARY_LENGTH, prompts['standard'])
    
    @classmethod
    def setup_logging(cls):
        """Setup logging configuration"""
        # Create logs directory if it doesn't exist
        cls.LOGS_DIR.mkdir(exist_ok=True)
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Setup file handler with rotation
        from logging.handlers import RotatingFileHandler
        log_path = cls.BASE_DIR / cls.LOG_FILE
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=cls.LOG_MAX_BYTES,
            backupCount=cls.LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(getattr(logging, cls.LOG_LEVEL))
        
        # Setup console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(getattr(logging, cls.LOG_LEVEL))
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, cls.LOG_LEVEL))
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        return root_logger


# Initialize logging when module is imported
Config.setup_logging()
