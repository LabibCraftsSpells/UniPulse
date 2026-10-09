"""
Gmail router — endpoints for fetching and managing emails.

KEY CONCEPT: REST API Design
-------------------------------
REST APIs use HTTP methods to indicate what you want to do:

    GET    = "Give me data"     (read)
    POST   = "Process this"     (create/action)
    PUT    = "Update this"      (replace)
    DELETE = "Remove this"      (delete)

Our email endpoints:
    GET  /api/emails          → Fetch recent emails from Gmail
    POST /api/emails/analyze  → Send emails to Gemini for analysis
    GET  /api/dashboard       → Get the analyzed dashboard data

IMPORTANT: These routes are placeholder skeletons.
Full implementation comes in Phases 3-5.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from backend.models import User
from backend.auth.dependencies import get_current_user
from backend.gmail.service import fetch_recent_emails
from backend.schemas import EmailCardResponse

router = APIRouter(prefix="/api", tags=["emails"])


@router.get("/emails", response_model=list[EmailCardResponse])
async def get_emails(user: User = Depends(get_current_user)):
    """
    Fetch recent emails from the user's Gmail.
    
    Uses the stored OAuth tokens to call Gmail API, retrieves the
    latest messages, extracts metadata (sender, subject, body preview),
    and returns them to the frontend.
    """
    emails = await fetch_recent_emails(user)
    return emails


from backend.ai.analyzer import analyze_emails


@router.post("/emails/analyze", response_model=list[EmailCardResponse])
async def analyze_inbox(user: User = Depends(get_current_user)):
    """
    Fetch recent emails and run them through Gemini for analysis.
    
    1. Fetches recent emails from Gmail API.
    2. Sends the batch to Gemini for structured JSON extraction.
    3. Returns the analyzed emails.
    """
    # 1. Fetch emails
    emails = await fetch_recent_emails(user)
    
    # 2. Analyze them with Gemini
    analyzed_emails = await analyze_emails(emails)
    
    return analyzed_emails


@router.get("/dashboard")
async def get_dashboard():
    """
    Get the full dashboard data.
    
    Returns analyzed emails grouped by priority, with summary stats.
    This is what powers the main dashboard UI.
    
    → Implemented in Phase 5
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Dashboard not yet implemented — coming in Phase 5"},
    )
