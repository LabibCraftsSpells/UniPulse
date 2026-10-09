"""
Database models — define the structure of our database tables.
UniPulse 2.0 Academic Command Center.
"""

from datetime import datetime, timezone
import json
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship

from backend.database import Base


def utcnow():
    """Get current UTC time. Used as default for timestamps."""
    return datetime.now(timezone.utc)


class User(Base):
    """
    Stores authenticated user information.
    Created when a user first signs in with Google OAuth.
    """
    __tablename__ = "users"

    id = Column(String, primary_key=True)               # Google user ID
    email = Column(String, unique=True, nullable=False)  # user@nsu.edu
    name = Column(String)                                # Display name
    picture = Column(String)                             # Profile picture URL

    # Encrypted OAuth tokens
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expiry = Column(DateTime)

    created_at = Column(DateTime, default=utcnow)

    # Relationships
    profile = relationship("StudentProfile", back_populates="user", uselist=False)
    email_analyses = relationship("EmailAnalysis", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("ActionTask", back_populates="user", cascade="all, delete-orphan")
    sync_state = relationship("UserSyncState", back_populates="user", uselist=False, cascade="all, delete-orphan")


class StudentProfile(Base):
    """
    Academic context used by Gemini to determine email relevance.
    """
    __tablename__ = "student_profiles"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    university = Column(String, default="")
    major = Column(String, default="")
    semester = Column(Integer, default=0)
    courses = Column(Text, default="[]")       # JSON array: ["CSE231", "PHY108"]
    interests = Column(Text, default="[]")     # JSON array: ["research", "clubs"]

    user = relationship("User", back_populates="profile")


class EmailAnalysis(Base):
    """
    Persistent cached email record and AI analysis.
    Stores metadata, clean body, sanitized preview, and structured Gemini analysis.
    """
    __tablename__ = "email_analyses"

    gmail_message_id = Column(String, primary_key=True)  # Gmail's unique ID
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Email envelope & metadata
    thread_id = Column(String, nullable=True)
    sender = Column(String)
    sender_name = Column(String, nullable=True)
    subject = Column(String)
    received_at = Column(DateTime, index=True)
    snippet = Column(Text, nullable=True)
    body_preview = Column(Text)                         # First ~500 chars for list display
    body_text = Column(Text, nullable=True)             # Full clean text
    body_html = Column(Text, nullable=True)             # Clean sanitized HTML
    is_unread = Column(Boolean, default=True, index=True)
    has_attachments = Column(Boolean, default=False)
    history_id = Column(String, nullable=True)

    # Analysis lifecycle status: "pending", "analyzing", "completed", "failed"
    status = Column(String, default="pending", index=True)

    # Structured AI Fields (parsed from Gemini output for high-speed indexing & sorting)
    priority = Column(String, nullable=True, index=True) # "high", "medium", "low", or None
    priority_reason = Column(Text, nullable=True)
    category = Column(String, nullable=True, index=True) # "course", "exam", "assignment", etc.
    course = Column(String, nullable=True, index=True)   # "CSE231", "PHY108", etc.
    summary = Column(Text, nullable=True)
    what_this_means = Column(Text, nullable=True)
    action_items = Column(Text, nullable=True)          # JSON array of action items
    deadlines = Column(Text, nullable=True)             # JSON array of extracted deadlines
    important_links = Column(Text, nullable=True)       # JSON array of URLs
    analysis = Column(Text, nullable=True)              # Complete raw JSON string from Gemini

    analyzed_at = Column(DateTime, nullable=True)
    last_synced_at = Column(DateTime, default=utcnow)

    # Relationships
    user = relationship("User", back_populates="email_analyses")
    tasks = relationship("ActionTask", back_populates="email", cascade="all, delete-orphan")


class ActionTask(Base):
    """
    Unified academic task extracted from email or created by student.
    Persisted in SQLite and synced with Action Center.
    """
    __tablename__ = "action_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    gmail_message_id = Column(String, ForeignKey("email_analyses.gmail_message_id"), nullable=True, index=True)

    title = Column(String, nullable=False)
    deadline_date = Column(String, nullable=True)       # "YYYY-MM-DD"
    deadline_time = Column(String, nullable=True)       # "HH:MM"
    deadline_confidence = Column(String, default="none") # "explicit", "ambiguous", "inferred", "none"
    completed = Column(Boolean, default=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    course = Column(String, nullable=True)
    priority = Column(String, default="medium")         # "high", "medium", "low"

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="tasks")
    email = relationship("EmailAnalysis", back_populates="tasks")


class UserSyncState(Base):
    """
    Sync metadata per user to support efficient incremental sync and status tracking.
    """
    __tablename__ = "user_sync_states"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    last_history_id = Column(String, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    sync_status = Column(String, default="idle")        # "idle", "syncing", "error"
    sync_error = Column(Text, nullable=True)
    total_synced = Column(Integer, default=0)
    total_available = Column(Integer, default=0)        # Total messages in Gmail mailbox (from getProfile)
    is_initial_sync_complete = Column(Boolean, default=False)
    sync_progress = Column(Integer, default=0)          # Number of messages imported in current run

    user = relationship("User", back_populates="sync_state")
