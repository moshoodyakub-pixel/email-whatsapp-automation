"""
AI-powered email summarization using Google Gemini.
Generates concise summaries of email content.
"""

import logging
import time
import google.generativeai as genai
from typing import Dict, Optional

from config import Config

logger = logging.getLogger(__name__)


class EmailSummarizer:
    """Generates AI-powered email summaries using Google Gemini"""
    
    def __init__(self):
        """Initialize Gemini AI client"""
        self.api_key = Config.GEMINI_API_KEY
        self.model_name = Config.GEMINI_MODEL
        self.model = None
        self.request_count = 0
        self.last_request_time = 0
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        
        logger.info(f"Initialized Gemini AI with model: {self.model_name}")
    
    def summarize_email(self, email_data: Dict) -> Optional[str]:
        """
        Generate a summary of an email.
        
        Args:
            email_data: Dictionary containing email fields (sender, subject, body)
        
        Returns:
            String summary or None if failed
        """
        try:
            sender = email_data.get('sender', 'Unknown')
            subject = email_data.get('subject', 'No Subject')
            body = email_data.get('body', email_data.get('snippet', ''))
            
            # Rate limiting (Gemini free tier: 60 requests/minute)
            self._rate_limit()
            
            # Get prompt template
            prompt_template = Config.get_summary_prompt()
            prompt = prompt_template.format(
                sender=sender,
                subject=subject,
                body=body
            )
            
            logger.info(f"Generating summary for email: {subject}")
            logger.debug(f"Prompt length: {len(prompt)} characters")
            
            # Generate summary
            response = self.model.generate_content(prompt)
            summary = response.text.strip()
            
            logger.info(f"Summary generated successfully ({len(summary)} chars)")
            logger.debug(f"Summary: {summary}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}", exc_info=True)
            
            # Fallback to simple extraction
            return self._fallback_summary(email_data)
    
    def _rate_limit(self):
        """Simple rate limiting to avoid API quota issues"""
        current_time = time.time()
        
        # Reset counter every minute
        if current_time - self.last_request_time > 60:
            self.request_count = 0
            self.last_request_time = current_time
        
        # If approaching limit, wait
        if self.request_count >= 55:  # Leave some buffer
            wait_time = 60 - (current_time - self.last_request_time)
            if wait_time > 0:
                logger.warning(f"Rate limit approaching, waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                self.request_count = 0
                self.last_request_time = time.time()
        
        self.request_count += 1
    
    def _fallback_summary(self, email_data: Dict) -> str:
        """
        Generate a simple fallback summary if AI fails.
        
        Args:
            email_data: Email data dictionary
        
        Returns:
            Simple text summary
        """
        sender = email_data.get('sender', 'Unknown')
        subject = email_data.get('subject', 'No Subject')
        snippet = email_data.get('snippet', '')
        
        # Extract just the email address if sender is in "Name <email>" format
        if '<' in sender and '>' in sender:
            sender_email = sender[sender.index('<')+1:sender.index('>')]
        else:
            sender_email = sender
        
        summary = f"Email from {sender_email}\n"
        summary += f"Subject: {subject}\n"
        
        if snippet:
            # Limit snippet length
            if len(snippet) > 150:
                snippet = snippet[:150] + "..."
            summary += f"\n{snippet}"
        
        logger.info("Using fallback summary (AI unavailable)")
        return summary
    
    def test_connection(self) -> bool:
        """
        Test Gemini API connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info("Testing Gemini API connection...")
            
            test_prompt = "Say 'Hello' in one word."
            response = self.model.generate_content(test_prompt)
            
            logger.info(f"Test response: {response.text}")
            logger.info("Gemini API connection successful!")
            
            return True
            
        except Exception as e:
            logger.error(f"Gemini API connection failed: {e}")
            return False


def main():
    """Test summarizer"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Email Summarizer Test')
    parser.add_argument('--test', action='store_true', help='Test API connection')
    args = parser.parse_args()
    
    summarizer = EmailSummarizer()
    
    if args.test:
        summarizer.test_connection()
        return
    
    # Test with sample email
    sample_email = {
        'sender': 'John Doe <john.doe@example.com>',
        'subject': 'Q4 Project Status Update',
        'body': '''Hi Team,
        
        I wanted to provide a quick update on the Q4 marketing project. 
        We've completed the initial research phase and are now moving into 
        the design stage. The timeline is still on track for a December 15th 
        launch.
        
        However, I need the final budget approval by this Friday to proceed 
        with the vendor contracts. Can we schedule a quick review meeting 
        early next week?
        
        Please let me know your availability.
        
        Best regards,
        John'''
    }
    
    print("\n" + "="*60)
    print("SAMPLE EMAIL")
    print("="*60)
    print(f"From: {sample_email['sender']}")
    print(f"Subject: {sample_email['subject']}")
    print(f"Body: {sample_email['body']}")
    print("="*60)
    
    print("\nGenerating summary...\n")
    
    summary = summarizer.summarize_email(sample_email)
    
    print("="*60)
    print("AI SUMMARY")
    print("="*60)
    print(summary)
    print("="*60)


if __name__ == '__main__':
    main()
