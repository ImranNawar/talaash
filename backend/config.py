"""
config.py - loads all environment variables / API keys.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent

# Load .env from the backend directory (not CWD), then .env.local
load_dotenv(_BACKEND_DIR / ".env")
load_dotenv(_BACKEND_DIR / ".env.local", override=False)

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "")
GOOGLE_CSE_KEY: str = os.getenv("GOOGLE_CSE_KEY", "")
GOOGLE_CSE_CX: str = os.getenv("GOOGLE_CSE_CX", "")

# Validate critical keys on startup
if not GROQ_API_KEY:
    raise ValueError(
        "Missing GROQ_API_KEY. Please set it in .env or .env.local. "
        "Get it from: https://console.groq.com"
    )
if not GEMINI_API_KEY:
    raise ValueError(
        "Missing GEMINI_API_KEY. Please set it in .env or .env.local. "
        "Get it from: https://aistudio.google.com"
    )
