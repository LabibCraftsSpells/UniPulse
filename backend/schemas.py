"""
Pydantic schemas — define the shape of API request/response data for UniPulse 2.0.
Contracts for high-speed inbox list, detailed panel, AI analysis, tasks, and daily briefing.
"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


# ============================================================
# User & Profile schemas
# ============================================================

class UserResponse(BaseModel):
    """What we send to the frontend about the current user."""
    id: str
    email: str
    name: str | None = None
    picture: str | None = None
    has_profile: bool = False


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


# ============================================================
# Structured AI Analysis Schemas (Section 8)
# ============================================================

class ExtractedDeadline(BaseModel):
    """A deadline extracted from an email."""
    date: str | None = None                          # e.g., "2026-10-15" or null if ambiguous
    time: str | None = None                          # e.g., "23:59" or null
    source_text: str | None = None                   # Exact source sentence/phrase
    confidence: Literal["explicit", "ambiguous", "inferred", "none"] = "none"


class ExtractedActionItem(BaseModel):
    """A concrete action item extracted from an email."""
    title: str
    deadline: str | None = None                      # Extracted deadline string if associated
    deadline_confidence: Literal["explicit", "ambiguous", "inferred", "none"] = "none"
    completed: bool = False


class ExtractedLink(BaseModel):
    """A relevant link extracted from the email."""
    label: str                                       # Descriptive title/label
    url: str                                         # Sanitized destination URL


class EmailAnalysisResult(BaseModel):
    """
    Structured Gemini output grounded strictly in email facts.
    Follows Section 8 specification.
    """
    summary: str
    priority: Literal["high", "medium", "low"]
    priority_reason: str
    category: str = "announcement"                   # course, exam, assignment, registration, announcement, administrative, other
    course: str | None = None                        # e.g., "CSE231", "PHY108", or null
    what_this_means: str = ""                        # Student-oriented interpretation
    action_items: list[ExtractedActionItem] = []
    deadlines: list[ExtractedDeadline] = []
    important_links: list[ExtractedLink] = []


# ============================================================
# Inbox & Email Detail Schemas
# ============================================================

class EmailListItem(BaseModel):
    """
    Lightweight email item optimized for fast inbox list rendering.
    Omits large full bodies to keep payload under ~50KB for 50 items.
    """
    gmail_message_id: str
    thread_id: str | None = None
    sender: str
    sender_name: str | None = None
    subject: str = ""
    received_at: datetime | None = None
    snippet: str = ""
    body_preview: str = ""
    gmail_link: str = ""
    is_unread: bool = True
    has_attachments: bool = False

    # Analysis status & summary fields
    status: Literal["pending", "analyzing", "completed", "failed"] = "pending"
    priority: Literal["high", "medium", "low"] | None = None
    priority_reason: str | None = None
    category: str | None = None
    course: str | None = None
    summary: str | None = None
    deadline_count: int = 0
    action_item_count: int = 0
    next_deadline: str | None = None


class EmailDetailResponse(BaseModel):
    """
    Full detail representation displayed in the right-side detail panel.
    """
    gmail_message_id: str
    thread_id: str | None = None
    sender: str
    sender_name: str | None = None
    subject: str = ""
    received_at: datetime | None = None
    snippet: str = ""
    gmail_link: str = ""
    is_unread: bool = True
    has_attachments: bool = False

    # Content representation
    body_text: str = ""
    body_html: str = ""                              # Sanitized safe HTML

    # Full analysis state
    status: Literal["pending", "analyzing", "completed", "failed"] = "pending"
    analysis: EmailAnalysisResult | None = None
    analyzed_at: datetime | None = None


# Backward compatibility with older Phase 3 / Phase 4 endpoints
class EmailCardResponse(BaseModel):
    gmail_message_id: str
    subject: str = ""
    sender: str = ""
    received_at: datetime | None = None
    body_preview: str = ""
    gmail_link: str = ""
    analysis: EmailAnalysisResult | None = None
    full_body: str | None = Field(default=None, exclude=True)


# ============================================================
# Action Center Task Schemas (Section 10)
# ============================================================

class TaskResponse(BaseModel):
    """A task in the Action Center."""
    id: int
    gmail_message_id: str | None = None
    email_subject: str | None = None
    email_sender: str | None = None
    title: str
    deadline_date: str | None = None
    deadline_time: str | None = None
    deadline_confidence: str = "none"
    completed: bool = False
    completed_at: datetime | None = None
    course: str | None = None
    priority: str = "medium"
    created_at: datetime | None = None


class TaskCreate(BaseModel):
    """User-created task or deadline task."""
    title: str
    gmail_message_id: str | None = None
    deadline_date: str | None = None
    deadline_time: str | None = None
    deadline_confidence: str = "explicit"
    course: str | None = None
    priority: str = "medium"


class TaskUpdate(BaseModel):
    """Fields that can be updated on an action task."""
    title: str | None = None
    completed: bool | None = None
    deadline_date: str | None = None
    deadline_time: str | None = None
    priority: str | None = None
    course: str | None = None


# ============================================================
# Sync State & Daily Briefing Schemas (Section 6 & 11)
# ============================================================

class SyncStateResponse(BaseModel):
    """Status of background synchronization."""
    status: Literal["idle", "syncing", "error"] = "idle"
    last_synced_at: datetime | None = None
    total_synced: int = 0
    total_available: int = 0
    is_initial_sync_complete: bool = False
    sync_progress: int = 0
    error: str | None = None


class SyncTimingStats(BaseModel):
    """Timing and result telemetry for high-speed synchronization."""
    status: str = "completed"
    sync_type: str = "incremental_history"
    new_messages: int = 0
    total_synced: int = 0
    total_available: int = 0
    is_initial_sync_complete: bool = False
    gmail_api_ms: float = 0.0
    db_ms: float = 0.0
    total_sync_ms: float = 0.0
    history_id: str | None = None
    last_synced_at: datetime | None = None


class InboxCounts(BaseModel):
    """Summary counts for sidebar filters and badge indicators."""
    all: int = 0
    unread: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    pending: int = 0
    deadlines: int = 0
    tasks_pending: int = 0
    tasks_overdue: int = 0


class InboxResponse(BaseModel):
    """The paginated inbox response with sync status and filter counts."""
    emails: list[EmailListItem] = []
    total: int = 0
    limit: int = 50
    offset: int = 0
    counts: InboxCounts
    sync_state: SyncStateResponse


class DailyBriefing(BaseModel):
    """
    Daily Academic Briefing computed from real stored data (Section 11).
    Zero extra Gemini latency.
    """
    unread_requiring_attention: int = 0
    upcoming_deadlines_count: int = 0
    overdue_tasks_count: int = 0
    high_priority_count: int = 0
    new_since_last_sync: int = 0
    last_synced_at: datetime | None = None
    upcoming_deadlines: list[TaskResponse] = []
    recent_high_priority: list[EmailListItem] = []
