import google.genai as genai
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='config/.env')

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("GEMINI_API_KEY not found in config/.env file.")
else:
    try:
        client = genai.Client(api_key=api_key)
        print("Available models:")
        for model in client.models.list():
            print(model.name)
    except Exception as e:
        print(f"An error occurred: {e}")
