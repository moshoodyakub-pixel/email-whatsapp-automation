"""
Main orchestration script for Email-to-WhatsApp automation.
Coordinates email monitoring, AI summarization, and WhatsApp notifications.
"""

import logging
import sys
import signal
import time
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from email_monitor import EmailMonitor
from ai_summarizer import EmailSummarizer
from whatsapp_sender import WhatsAppSender

logger = logging.getLogger(__name__)


class EmailWhatsAppBot:
    """Main bot orchestrator"""
    
    def __init__(self):
        """Initialize all components"""
        self.email_monitor = None
        self.summarizer = None
        self.whatsapp = None
        self.running = False
        self.stats = {
            'emails_processed': 0,
            'summaries_generated': 0,
            'messages_sent': 0,
            'errors': 0
        }
    
    def initialize(self):
        """Initialize all services"""
        logger.info("="*60)
        logger.info("Email-to-WhatsApp Automation Bot")
        logger.info("="*60)
        
        try:
            # Validate configuration
            logger.info("Validating configuration...")
            Config.validate()
            logger.info("OK: Configuration valid")
            
            # Initialize AI summarizer
            logger.info("\n[AI] Initializing AI summarizer...")
            self.summarizer = EmailSummarizer()
            if not self.summarizer.test_connection():
                raise Exception("Failed to connect to Gemini AI")
            logger.info("OK: AI summarizer ready")
            
            # Initialize WhatsApp sender
            logger.info("\n[WhatsApp] Initializing WhatsApp sender...")
            self.whatsapp = WhatsAppSender()
            logger.info("OK: WhatsApp sender ready")
            
            # Wait for WhatsApp service
            logger.info("\n[System] Waiting for WhatsApp service...")
            if not self.whatsapp.wait_for_ready(timeout=120):
                logger.error("\nERROR: WhatsApp service is not ready!")
                logger.error("Please ensure:")
                logger.error("  1. WhatsApp service is running: node src/whatsapp_service.js")
                logger.error("  2. You have authenticated: node src/whatsapp_init.js")
                raise Exception("WhatsApp service not ready")
            logger.info("OK: WhatsApp service connected")
            
            # Initialize email monitor (with callback)
            logger.info("\n[Email] Initializing email monitor...")
            self.email_monitor = EmailMonitor(
                on_new_email_callback=self.handle_new_email
            )
            self.email_monitor.initialize()
            logger.info("OK: Email monitor ready")
            
            logger.info("\n" + "="*60)
            logger.info("All systems initialized successfully!")
            logger.info("="*60)
            logger.info(f"Summary mode: {Config.SUMMARY_LENGTH}")
            logger.info(f"Target WhatsApp: {Config.YOUR_WHATSAPP_NUMBER}")
            logger.info(f"Logs: {Config.LOG_FILE}")
            logger.info("="*60 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"\nERROR: Initialization failed: {e}", exc_info=True)
            return False
    
    def handle_new_email(self, email_id: str, email_data: dict):
        """
        Callback function for new emails.
        
        Args:
            email_id: Gmail message ID
            email_data: Email data dictionary
        """
        try:
            logger.info("\n" + "="*60)
            logger.info(f"[Email] Processing new email: {email_id}")
            logger.info("="*60)
            
            sender = email_data.get('sender', 'Unknown')
            subject = email_data.get('subject', 'No Subject')
            
            logger.info(f"From: {sender}")
            logger.info(f"Subject: {subject}")
            
            self.stats['emails_processed'] += 1
            
            # Generate AI summary
            logger.info("\n[AI] Generating AI summary...")
            summary = self.summarizer.summarize_email(email_data)
            
            if not summary:
                logger.error("Failed to generate summary")
                self.stats['errors'] += 1
                return
            
            self.stats['summaries_generated'] += 1
            logger.info(f"Summary: {summary[:100]}...")
            
            # Send to WhatsApp
            logger.info("\n[WhatsApp] Sending WhatsApp notification...")
            success = self.whatsapp.send_email_notification(email_data, summary)
            
            if success:
                self.stats['messages_sent'] += 1
                logger.info("OK: Email notification sent successfully!")
            else:
                logger.error("ERROR: Failed to send WhatsApp notification")
                self.stats['errors'] += 1
            
            # Log stats
            logger.info("\n[Stats] Statistics:")
            logger.info(f"  Emails processed: {self.stats['emails_processed']}")
            logger.info(f"  Summaries generated: {self.stats['summaries_generated']}")
            logger.info(f"  Messages sent: {self.stats['messages_sent']}")
            logger.info(f"  Errors: {self.stats['errors']}")
            logger.info("="*60 + "\n")
            
        except Exception as e:
            logger.error(f"Error handling email {email_id}: {e}", exc_info=True)
            self.stats['errors'] += 1
    
    def run(self):
        """Start the bot"""
        if not self.initialize():
            logger.error("Failed to initialize. Exiting.")
            return False
        
        self.running = True
        
        try:
            logger.info("Bot is now running and monitoring your inbox...")
            logger.info("Press Ctrl+C to stop.\n")
            
            # Start email monitoring (blocks until interrupted)
            self.email_monitor.start_listening()
            
        except KeyboardInterrupt:
            logger.info("\n\n[System] Received shutdown signal...")
            self.shutdown()
        except Exception as e:
            logger.error(f"\nERROR: Fatal error: {e}", exc_info=True)
            self.shutdown()
            return False
        
        return True
    
    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down bot...")
        self.running = False
        
        # Log final stats
        logger.info("\n" + "="*60)
        logger.info("[Stats] Final Statistics")
        logger.info("="*60)
        logger.info(f"Emails processed: {self.stats['emails_processed']}")
        logger.info(f"Summaries generated: {self.stats['summaries_generated']}")
        logger.info(f"Messages sent: {self.stats['messages_sent']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info("="*60)
        
        logger.info("\nGoodbye!\n")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Email-to-WhatsApp Automation Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              # Run the bot
  python main.py --test       # Test all components
  
Before running:
  1. Configure .env file with your credentials
  2. Authenticate Gmail: python src/gmail_auth.py
  3. Authenticate WhatsApp: node src/whatsapp_init.js
  4. Start WhatsApp service: node src/whatsapp_service.js (in separate terminal)
        """
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test all components without starting monitoring'
    )
    
    args = parser.parse_args()
    
    bot = EmailWhatsAppBot()
    
    if args.test:
        logger.info("Running component tests...\n")
        
        # Test configuration
        try:
            Config.validate()
            logger.info("OK: Configuration valid\n")
        except Exception as e:
            logger.error(f"ERROR: Configuration error: {e}\n")
            return
        
        # Test AI
        summarizer = EmailSummarizer()
        if summarizer.test_connection():
            logger.info("OK: Gemini AI connected\n")
        else:
            logger.error("ERROR: Gemini AI connection failed\n")
        
        # Test WhatsApp
        whatsapp = WhatsAppSender()
        if whatsapp.wait_for_ready(timeout=30):
            logger.info("OK: WhatsApp service ready\n")
            if whatsapp.test_connection():
                logger.info("OK: WhatsApp test message sent\n")
        else:
            logger.error("ERROR: WhatsApp service not ready\n")
        
        logger.info("Test complete!")
        
    else:
        # Run the bot
        bot.run()


if __name__ == '__main__':
    main()
