"""
Pydantic schemas — define the shape of API request/response data.

KEY CONCEPT: Models vs Schemas
---------------------------------
- Database models (models.py) = how data is stored in the database
- Pydantic schemas (this file) = how data is sent/received via the API

When the frontend sends a request or receives a response, the data
must match these schemas. FastAPI automatically validates the data
and returns clear error messages if something is wrong.

Think of schemas as a "contract" between frontend and backend:
    "The dashboard response will ALWAYS have these fields in this format."
"""

from datetime import datetime
from pydantic import BaseModel


# ============================================================
# User schemas
# ============================================================

class UserResponse(BaseModel):
    """What we send to the frontend about the current user."""
    id: str
    email: str
    name: str | None = None
    picture: str | None = None
    has_profile: bool = False


# ============================================================
# Student profile schemas
# ============================================================

class StudentProfileUpdate(BaseModel):
    """What the frontend sends when updating a student profile."""
    university: str = ""
    major: str = ""
    semester: int = 0
    courses: list[str] = []
    interests: list[str] = []


class StudentProfileResponse(BaseModel):
    """What we send back about a student's profile."""
    university: str = ""
    major: str = ""
    semester: int = 0
    courses: list[str] = []
    interests: list[str] = []


from typing import Literal
from pydantic import BaseModel, Field

# ============================================================
# Email analysis schemas
# ============================================================

class Deadline(BaseModel):
    """A deadline extracted from an email."""
    date: str | None = None           # "2026-10-15"
    time: str | None = None           # "23:59" or null
    description: str | None = None    # "Course registration deadline"


class ImportantLink(BaseModel):
    """A link extracted from an email."""
    title: str | None = None
    url: str


class EmailAnalysisResult(BaseModel):
    """
    The structured output from Gemini's analysis of one email.
    """
    priority: Literal["high", "medium", "low"]
    relevance: Literal["relevant", "not_relevant"]
    category: Literal["academic", "registration", "exam", "assignment", "event", "administrative", "security", "social", "promotional", "other"]
    summary: str
    action_required: bool
    action_items: list[str]
    deadlines: list[Deadline]
    important_links: list[ImportantLink]
    what_this_means: str
    sender: str
    subject: str
    date: str


class EmailCardResponse(BaseModel):
    """One email card on the dashboard — combines email metadata + analysis."""
    gmail_message_id: str
    subject: str = ""
    sender: str = ""
    received_at: datetime | None = None
    body_preview: str = ""
    gmail_link: str = ""
    analysis: EmailAnalysisResult | None = None
    
    # We store the full body internally to send to Gemini, 
    # but exclude=True prevents it from being sent to the frontend to save bandwidth.
    full_body: str | None = Field(default=None, exclude=True)


# ============================================================
# Dashboard schemas
# ============================================================

class DashboardStats(BaseModel):
    """Summary counts for the dashboard header."""
    needs_action: int = 0
    important: int = 0
    no_action: int = 0
    total: int = 0


class DashboardResponse(BaseModel):
    """The full dashboard response sent to the frontend."""
    user_name: str = ""
    stats: DashboardStats
    emails: list[EmailCardResponse] = []
    last_refreshed: datetime | None = None
