"""
Database models — define the structure of our database tables.

KEY CONCEPT: Models vs Tables
-------------------------------
Each class here represents a database table. Each attribute (like "email")
becomes a column. SQLAlchemy creates the actual SQL tables from these.

Think of it like this:
    Class  = Table definition (blueprint)
    Object = Row in the table (actual data)

    User(email="labib@nsu.edu")  →  one row in the "users" table
"""

from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


def utcnow():
    """Get current UTC time. Used as default for timestamps."""
    return datetime.now(timezone.utc)


class User(Base):
    """
    Stores authenticated user information.
    
    Created when a user first signs in with Google OAuth.
    We store their Google user ID, name, email, and OAuth tokens.
    
    PRIVACY NOTE: OAuth tokens are what let us access Gmail on the user's
    behalf. They should be encrypted at rest (we'll add this in Phase 2).
    """

    __tablename__ = "users"

    id = Column(String, primary_key=True)               # Google user ID
    email = Column(String, unique=True, nullable=False)  # user@nsu.edu
    name = Column(String)                                # Display name
    picture = Column(String)                             # Profile picture URL

    # OAuth tokens — these let us call Gmail API on behalf of the user
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expiry = Column(DateTime)

    created_at = Column(DateTime, default=utcnow)

    # Relationships — SQLAlchemy automatically links related objects
    profile = relationship("StudentProfile", back_populates="user", uselist=False)
    email_analyses = relationship("EmailAnalysis", back_populates="user")


class StudentProfile(Base):
    """
    Academic context used by Gemini to determine email relevance.
    
    Example: If a student lists "CSE231" in their courses, an email
    about CSE231 registration will be marked as highly relevant.
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
    Cached AI analysis of an email.
    
    WHY CACHE: We don't want to send the same email to Gemini every time
    the user opens the dashboard. Once an email is analyzed, we store the
    result and reuse it.
    
    PRIVACY NOTE: We store a short preview of the email body (for display)
    and the AI analysis. We do NOT store the full email body permanently.
    The full content is only in the user's Gmail account.
    """

    __tablename__ = "email_analyses"

    gmail_message_id = Column(String, primary_key=True)  # Gmail's unique ID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Email metadata (safe to store — this is like an envelope)
    sender = Column(String)
    subject = Column(String)
    received_at = Column(DateTime)
    body_preview = Column(Text)      # First ~500 chars for UI display

    # Gemini's analysis result stored as a JSON string
    analysis = Column(Text)          # Full JSON analysis from Gemini
    analyzed_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="email_analyses")
