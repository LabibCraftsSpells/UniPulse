"""
Gmail service — handles communication with the Gmail API.

KEY CONCEPT: The Gmail API Client
----------------------------------
To talk to Gmail, we use the `googleapiclient.discovery.build` function. 
We must provide it with "Credentials". Instead of making the user log in again, 
we build these Credentials using the encrypted tokens we saved in our database 
during the Phase 2 OAuth flow.

KEY CONCEPT: Token Refresh
---------------------------
Access tokens expire after ~1 hour. If we pass the `refresh_token` to the 
Credentials object, the Google client will automatically fetch a brand new 
access token behind the scenes if the current one is expired!

KEY CONCEPT: Multipart Emails
------------------------------
Emails are not just simple text. They are "multipart" — they contain a plain text
version, an HTML version, and attachments, all nested inside each other. We use a 
recursive function (`extract_body`) to dig through these parts and find the text.
"""

import base64
import asyncio
from datetime import datetime
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError
from fastapi import HTTPException, status

from backend.config import settings
from backend.models import User
from backend.auth.crypto import decrypt_token
from backend.schemas import EmailCardResponse


def clean_html(html_content: str) -> str:
    """Strip HTML tags from email bodies to get plain text."""
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "html.parser")
    for element in soup(["script", "style", "head"]):
        element.decompose()

    text = soup.get_text(separator=" ", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def get_header(headers: list, name: str) -> str:
    """Helper to extract a specific header (like 'Subject' or 'From') from Gmail payload."""
    for header in headers:
        if header['name'].lower() == name.lower():
            return header['value']
    return ""


def extract_body(payload: dict) -> str:
    """
    Recursively extract plain text or HTML body from a Gmail message payload.
    """
    body = ""
    if 'parts' in payload:
        for part in payload['parts']:
            mime_type = part.get('mimeType', '')
            if mime_type == 'text/plain':
                data = part.get('body', {}).get('data')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
            elif mime_type == 'text/html':
                data = part.get('body', {}).get('data')
                if data:
                    html = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                    return clean_html(html)
            elif 'parts' in part:
                # Recursive search inside nested parts
                nested_body = extract_body(part)
                if nested_body:
                    return nested_body
    else:
        # Not multipart, just a single body
        data = payload.get('body', {}).get('data')
        if data:
            text = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
            if payload.get('mimeType') == 'text/html':
                return clean_html(text)
            return text
    return body


async def fetch_recent_emails(user: User) -> list[EmailCardResponse]:
    """
    Fetch recent emails from Gmail API using the user's decrypted tokens.
    """
    # 1. We must have a token to proceed
    access_token = decrypt_token(user.access_token)
    refresh_token = decrypt_token(user.refresh_token)
    
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No Gmail access token found. Please reconnect your account."
        )

    try:
        # 2. Build the Google Credentials object
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )

        # 3. Build the Gmail service client
        service = build('gmail', 'v1', credentials=creds)

        # 4. List recent message IDs
        # We use asyncio.to_thread because googleapiclient is synchronous (blocking)
        # and we don't want to freeze our FastAPI async event loop.
        results = await asyncio.to_thread(
            service.users().messages().list(userId='me', maxResults=settings.MAX_EMAILS_TO_FETCH).execute
        )

        messages = results.get('messages', [])
        email_cards = []

        # 5. Fetch the full content for each message ID
        for msg in messages:
            msg_id = msg['id']
            # format='full' gets the headers and the body payload
            full_msg = await asyncio.to_thread(
                service.users().messages().get(userId='me', id=msg_id, format='full').execute
            )
            
            payload = full_msg.get('payload', {})
            headers = payload.get('headers', [])
            
            subject = get_header(headers, 'Subject')
            sender = get_header(headers, 'From')
            date_str = get_header(headers, 'Date')
            
            # Parse the date string into a Python datetime object
            received_at = None
            if date_str:
                try:
                    received_at = parsedate_to_datetime(date_str)
                except (TypeError, ValueError):
                    pass

            # Extract body and fallback to the Gmail 'snippet' if extraction fails
            body_text = extract_body(payload)
            if not body_text:
                body_text = full_msg.get('snippet', '')
            
            # Truncate to a reasonable preview length so we don't send megabytes of text to frontend
            body_preview = body_text[:500] + ("..." if len(body_text) > 500 else "")

            # Generate a link the user can click to open this email in real Gmail
            gmail_link = f"https://mail.google.com/mail/u/0/#inbox/{msg_id}"

            email_cards.append(
                EmailCardResponse(
                    gmail_message_id=msg_id,
                    subject=subject,
                    sender=sender,
                    received_at=received_at,
                    body_preview=body_preview,
                    gmail_link=gmail_link,
                    analysis=None, # Gemini analysis is Phase 4!
                    full_body=body_text # Hidden from frontend, used by Gemini
                )
            )

        return email_cards

    except RefreshError:
        # This happens if the user changed their Google password or manually revoked our app
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gmail session expired or revoked. Please disconnect and reconnect your account."
        )
    except Exception as e:
        print(f"Gmail fetch error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch emails from Gmail."
        )
