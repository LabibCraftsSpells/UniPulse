"""
Application configuration.

This module loads settings from environment variables using python-dotenv.

KEY CONCEPT: Environment Variables
-----------------------------------
Environment variables are values stored OUTSIDE your code (in a .env file
or your system). This keeps secrets like API keys out of your source code.

python-dotenv reads the .env file and makes those values available via
os.getenv(). If the .env file doesn't exist, the app still works —
it just won't have the secrets (and will fail when trying to use them).
"""

import os
from dotenv import load_dotenv

# Load .env file from the project root
# This reads the .env file and sets the values as environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))


class Settings:
    """
    Central place for all configuration.
    
    Every setting reads from an environment variable with a fallback default.
    Secrets have no default — they MUST be set in .env.
    """

    # --- Google OAuth ---
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")

    # The OAuth callback URL — Google redirects here after user approves access
    GOOGLE_REDIRECT_URI: str = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/auth/google/callback",
    )

    # What permissions we request from the user's Google account
    # gmail.readonly = read emails but CANNOT send, delete, or modify
    GOOGLE_SCOPES: list[str] = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid",
    ]

    # --- Gemini AI ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"

    # --- App ---
    APP_SECRET_KEY: str = os.getenv("APP_SECRET_KEY", "dev-secret-change-me")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")

    # --- Database ---
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./student_mail_copilot.db",
    )

    # --- Email fetching & Synchronization ---
    INITIAL_SYNC_MAX_EMAILS: int = int(os.getenv("INITIAL_SYNC_MAX_EMAILS", "0"))  # 0 = Entire Mailbox without artificial caps
    MAX_EMAILS_TO_FETCH: int = int(os.getenv("MAX_EMAILS_TO_FETCH", "100"))
    SYNC_BATCH_SIZE: int = 50


# Single global instance — import this wherever you need settings
settings = Settings()
