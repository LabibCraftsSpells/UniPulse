"""
Cryptography utilities for encrypting sensitive data at rest.

KEY CONCEPT: Encryption at Rest
--------------------------------
OAuth tokens allow us to access a user's Gmail. If our database is ever
leaked or compromised, we don't want an attacker to have those tokens.
We use symmetric encryption (Fernet) to encrypt the tokens before saving
them to the database, and decrypt them when we need to use them.

The key used for encryption is derived from APP_SECRET_KEY in your .env file.
If you lose APP_SECRET_KEY, all stored tokens become permanently unreadable!
"""

import base64
import hashlib
from cryptography.fernet import Fernet
from backend.config import settings

# Fernet requires a 32-byte url-safe base64-encoded key.
# We hash our APP_SECRET_KEY to ensure it's exactly the right length and format.
_key = base64.urlsafe_b64encode(hashlib.sha256(settings.APP_SECRET_KEY.encode()).digest())
_cipher_suite = Fernet(_key)

def encrypt_token(token: str | None) -> str | None:
    """Encrypt a plain text token."""
    if not token:
        return None
    return _cipher_suite.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str | None) -> str | None:
    """Decrypt an encrypted token back to plain text."""
    if not encrypted_token:
        return None
    return _cipher_suite.decrypt(encrypted_token.encode()).decode()
