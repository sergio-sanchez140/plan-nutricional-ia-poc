import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    GROQ_API_URL: str = "https://api.groq.com/openai/v1/chat/completions"
    GROQ_MODEL = "llama-3.3-70b-versatile" 

settings = Settings()