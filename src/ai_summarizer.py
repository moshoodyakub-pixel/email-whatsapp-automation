import os
import logging
import google.genai as genai
from config import Config

logger = logging.getLogger(__name__)

class EmailSummarizer:
    """Handles email summarization using the Gemini API."""

    def __init__(self):
        """Initializes the Gemini client."""
        if not Config.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not found in config.")
            raise ValueError("GEMINI_API_KEY not found in config.")
        
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
        self.model_name = f"models/{Config.GEMINI_MODEL}"
        self.model = None
        logger.info(f"Initialized Gemini AI with model: {Config.GEMINI_MODEL}")

    def test_connection(self) -> bool:
        """
        Tests the connection to the Gemini API by trying to get the configured model.
        Returns True if successful, False otherwise.
        """
        logger.info("Testing Gemini API connection...")
        try:
            self.model = self.client.models.get(model=self.model_name)
            logger.info("Gemini API connection successful.")
            return True
        except Exception as e:
            logger.error(f"Gemini API connection failed: {e}", exc_info=True)
            return False

    def summarize_email(self, email_data: dict) -> str | None:
        """
        Summarizes an email using the Gemini API.
        """
        if not self.model:
            logger.error("Summarizer model not initialized. Run test_connection() first.")
            return None

        email_body = email_data.get('body', '')
        if not email_body:
            logger.warning("Email body is empty, cannot summarize.")
            return "This email has no content to summarize."

        try:
            prompt_template = Config.get_summary_prompt()
            prompt = prompt_template.format(
                sender=email_data.get('sender', 'N/A'),
                subject=email_data.get('subject', 'N/A'),
                body=email_body
            )
            
            response = self.model.generate_content(prompt)
            
            summary = response.text.strip()
            return summary
        except Exception as e:
            logger.error(f"An error occurred while generating the summary: {e}", exc_info=True)
            return None
