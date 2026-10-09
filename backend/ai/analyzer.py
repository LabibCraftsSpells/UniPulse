"""
AI analyzer — Gemini structured analysis, background processing queue, and task extraction for UniPulse 2.0.
"""

import asyncio
import json
import time
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from google import genai
from google.genai import types
from fastapi import HTTPException, status

from backend.config import settings
from backend.models import EmailAnalysis, ActionTask, StudentProfile, utcnow
from backend.schemas import EmailAnalysisResult, ExtractedActionItem, ExtractedDeadline, ExtractedLink
from backend.database import async_session

# Concurrency semaphore to respect Gemini rate limits
_GEMINI_SEMAPHORE = asyncio.Semaphore(4)

# In-memory deduplication of active analysis tasks: message_id -> asyncio.Task
_ACTIVE_ANALYSES: Dict[str, asyncio.Task] = {}


SYSTEM_INSTRUCTION = """
You are an AI academic command center assistant for university students analyzing official university emails.
Read the provided university email carefully and extract structured academic intelligence.

CRITICAL RULES:
1. NEVER INVENT or hallucinate any deadlines, dates, times, course requirements, exam schedules, actions, or URLs.
2. If an email does NOT explicitly state a deadline, return an empty array for deadlines.
3. If no student action is required, return an empty array for action_items.
4. If a course code (like CSE231, PHY108, MAT120, HIS102, ENG102) is mentioned or clearly identifiable, extract it into 'course'. Otherwise return null.
5. Strictly separate objective facts from interpretation in 'what_this_means'.
6. Treat security notices, social invites, newsletters, and promotional university emails appropriately: do not mark everything as high priority.
7. 'priority' must be:
   - 'high': Immediate action required, near-term assignment/exam/quiz deadline, urgent registration or clearance issue.
   - 'medium': Important announcements, syllabus/class schedule updates, academic guidance with no immediate emergency.
   - 'low': General campus club activities, promotional events, non-urgent university broad announcements.
8. 'priority_reason' must briefly state WHY based on real email content (e.g. "Contains submission deadline for assignment 2").
"""


async def analyze_email_record(email: EmailAnalysis, db: AsyncSession) -> EmailAnalysisResult | None:
    """
    Perform grounded Gemini analysis for a single email record and persist
    structured fields and ActionTasks into SQLite.
    """
    if not settings.GEMINI_API_KEY:
        print("[AI WARNING] GEMINI_API_KEY is not configured.")
        return None

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    # Fetch student profile for personalized academic relevance
    prof_res = await db.execute(select(StudentProfile).where(StudentProfile.user_id == email.user_id))
    profile = prof_res.scalar_one_or_none()
    profile_ctx = ""
    if profile:
        profile_ctx = f"\nStudent Profile Context: University: {profile.university}, Major: {profile.major}, Current Courses: {profile.courses}"

    prompt = (
        f"Sender: {email.sender_name or ''} <{email.sender}>\n"
        f"Subject: {email.subject}\n"
        f"Date: {email.received_at}\n"
        f"{profile_ctx}\n\n"
        f"Email Content:\n{email.body_text or email.snippet or ''}"
    )

    t_start = time.perf_counter()
    async with _GEMINI_SEMAPHORE:
        try:
            response = await client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=EmailAnalysisResult,
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.1,  # Highly deterministic factual extraction
                )
            )
            raw_text = response.text
            parsed = EmailAnalysisResult.model_validate_json(raw_text)
        except Exception as e:
            t_fail = (time.perf_counter() - t_start) * 1000
            print(f"[AI ERROR] Analysis failed for {email.gmail_message_id} in {t_fail:.1f}ms: {e}")
            email.status = "failed"
            await db.commit()
            return None

    t_ai = (time.perf_counter() - t_start) * 1000

    # Persist structured analysis fields in SQLite
    email.status = "completed"
    email.priority = parsed.priority
    email.priority_reason = parsed.priority_reason
    email.category = parsed.category
    email.course = parsed.course
    email.summary = parsed.summary
    email.what_this_means = parsed.what_this_means
    email.action_items = json.dumps([item.model_dump() for item in parsed.action_items])
    email.deadlines = json.dumps([dl.model_dump() for dl in parsed.deadlines])
    email.important_links = json.dumps([link.model_dump() for link in parsed.important_links])
    email.analysis = raw_text
    email.analyzed_at = utcnow()

    # Synchronize action tasks into ActionCenter table
    # Avoid duplicate tasks by checking existing tasks for this message
    existing_tasks_res = await db.execute(select(ActionTask).where(ActionTask.gmail_message_id == email.gmail_message_id))
    existing_tasks = existing_tasks_res.scalars().all()
    existing_titles = {t.title.lower().strip() for t in existing_tasks}

    new_tasks = []
    # 1. Add extracted action items
    for item in parsed.action_items:
        if item.title.lower().strip() not in existing_titles:
            new_tasks.append(
                ActionTask(
                    user_id=email.user_id,
                    gmail_message_id=email.gmail_message_id,
                    title=item.title,
                    deadline_date=item.deadline,
                    deadline_confidence=item.deadline_confidence,
                    completed=False,
                    course=parsed.course,
                    priority=parsed.priority,
                )
            )
            existing_titles.add(item.title.lower().strip())

    # 2. Add extracted deadlines as actionable tasks if not already covered
    for dl in parsed.deadlines:
        dl_desc = f"{dl.source_text or 'Deadline'}"
        if dl.date and dl_desc.lower().strip() not in existing_titles:
            new_tasks.append(
                ActionTask(
                    user_id=email.user_id,
                    gmail_message_id=email.gmail_message_id,
                    title=dl_desc,
                    deadline_date=dl.date,
                    deadline_time=dl.time,
                    deadline_confidence=dl.confidence,
                    completed=False,
                    course=parsed.course,
                    priority=parsed.priority,
                )
            )
            existing_titles.add(dl_desc.lower().strip())

    if new_tasks:
        db.add_all(new_tasks)

    await db.commit()
    print(f"[AI] Analyzed {email.gmail_message_id} ({parsed.priority.upper()}) in {t_ai:.1f}ms with {len(new_tasks)} new tasks.")

    return parsed


async def analyze_message_by_id(gmail_message_id: str, user_id: str) -> EmailAnalysis | None:
    """
    On-demand prioritized analysis for a single message.
    If an analysis is already in progress, awaits the existing task.
    """
    # Deduplicate concurrent requests
    if gmail_message_id in _ACTIVE_ANALYSES:
        try:
            await _ACTIVE_ANALYSES[gmail_message_id]
        except Exception:
            pass

    async with async_session() as db:
        res = await db.execute(
            select(EmailAnalysis).where(
                EmailAnalysis.gmail_message_id == gmail_message_id,
                EmailAnalysis.user_id == user_id
            )
        )
        email = res.scalar_one_or_none()
        if not email:
            return None

        # Return cached analysis immediately if already completed
        if email.status == "completed" and email.analysis:
            return email

        email.status = "analyzing"
        await db.commit()

        # Wrap in active task tracker
        task = asyncio.create_task(analyze_email_record(email, db))
        _ACTIVE_ANALYSES[gmail_message_id] = task
        try:
            await task
        finally:
            _ACTIVE_ANALYSES.pop(gmail_message_id, None)

        await db.refresh(email)
        return email


async def process_pending_email_batch(user_id: str, limit: int = 15):
    """
    Background worker that picks up pending emails and analyzes them sequentially or in small parallel batches.
    """
    async with async_session() as db:
        res = await db.execute(
            select(EmailAnalysis)
            .where(
                EmailAnalysis.user_id == user_id,
                EmailAnalysis.status == "pending"
            )
            .order_by(EmailAnalysis.received_at.desc())
            .limit(limit)
        )
        pending_emails = res.scalars().all()

        if not pending_emails:
            return

        print(f"[AI QUEUE] Starting concurrent background analysis for {len(pending_emails)} pending emails...")
        t_batch_start = time.perf_counter()

        async def _run_one(email_id: str):
            # Dedicated session per concurrent task prevents SQLAlchemy session conflict
            async with async_session() as task_db:
                email_res = await task_db.execute(
                    select(EmailAnalysis).where(EmailAnalysis.gmail_message_id == email_id)
                )
                em = email_res.scalar_one_or_none()
                if not em or em.status == "completed":
                    return
                em.status = "analyzing"
                await task_db.commit()
                try:
                    await analyze_email_record(em, task_db)
                except Exception as err:
                    print(f"[AI QUEUE ERROR] {email_id}: {err}")

        scheduled = []
        for email in pending_emails:
            if email.gmail_message_id in _ACTIVE_ANALYSES:
                continue
            task = asyncio.create_task(_run_one(email.gmail_message_id))
            _ACTIVE_ANALYSES[email.gmail_message_id] = task
            scheduled.append((email.gmail_message_id, task))

        if scheduled:
            await asyncio.gather(*(t for _, t in scheduled), return_exceptions=True)
            for mid, _ in scheduled:
                _ACTIVE_ANALYSES.pop(mid, None)

            t_batch = (time.perf_counter() - t_batch_start) * 1000
            avg_per = t_batch / len(scheduled) if scheduled else 0
            print(f"[AI QUEUE] Background analysis batch of {len(scheduled)} emails completed in {t_batch:.1f}ms ({avg_per:.1f}ms/email).")


# Backward compatibility for existing endpoints
async def analyze_emails(emails):
    """Legacy wrapper for older endpoints."""
    return emails
