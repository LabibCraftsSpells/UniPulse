"""
Gmail & Inbox router for UniPulse 2.0.
Provides sub-second cached inbox retrieval, on-demand AI analysis,
sanitized original message detail, and Daily Academic Briefing.
"""

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, case

from backend.database import get_db, async_session
from backend.models import User, EmailAnalysis, ActionTask, UserSyncState, utcnow
from backend.auth.dependencies import get_current_user
from backend.gmail.service import sync_user_emails, complete_initial_sync_background
from backend.ai.analyzer import analyze_message_by_id, process_pending_email_batch
from backend.schemas import (
    InboxResponse, EmailListItem, EmailDetailResponse, InboxCounts,
    SyncStateResponse, SyncTimingStats, DailyBriefing, TaskResponse, EmailAnalysisResult,
    EmailCardResponse
)

router = APIRouter(prefix="/api", tags=["emails"])

# Concurrency lock to prevent duplicate simultaneous background syncs for the same user
_USER_SYNC_LOCKS: dict[str, bool] = {}


async def _background_sync_task(user_id: str):
    """Background task to synchronize emails and queue analysis separately."""
    if _USER_SYNC_LOCKS.get(user_id):
        return
    _USER_SYNC_LOCKS[user_id] = True
    sync_result = None
    try:
        async with async_session() as db:
            user_res = await db.execute(select(User).where(User.id == user_id))
            user = user_res.scalar_one_or_none()
            if not user:
                return

            sync_result = await sync_user_emails(user, db, first_chunk_only=True)
    except Exception as e:
        print(f"[BACKGROUND SYNC ERROR] User {user_id}: {e}")
    finally:
        # Release the sync lock IMMEDIATELY so the user can interact and sync status becomes idle
        _USER_SYNC_LOCKS.pop(user_id, None)

    # If initial sync incomplete, complete it progressively in background
    if sync_result and not sync_result.is_initial_sync_complete:
        try:
            await complete_initial_sync_background(user_id)
        except Exception as e:
            print(f"[BACKGROUND INITIAL IMPORT ERROR] User {user_id}: {e}")

    # Process AI analysis independently in the background WITHOUT holding the sync lock
    try:
        await process_pending_email_batch(user_id, limit=20)
    except Exception as e:
        print(f"[BACKGROUND AI ERROR] User {user_id}: {e}")


@router.get("/emails", response_model=InboxResponse)
async def get_inbox_emails(
    priority: Optional[str] = Query(None, description="high, medium, low, or pending"),
    unread: Optional[bool] = Query(None),
    has_deadline: Optional[bool] = Query(None),
    course: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort: Literal["priority", "newest"] = Query("priority"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Sub-second inbox endpoint served directly from persistent SQLite cache.
    Triggers automatic background sync if mailbox is empty or hasn't synced recently.
    """
    t_start = time.perf_counter()

    # Base query for user's emails
    base_cond = [EmailAnalysis.user_id == user.id]

    # Filters
    if priority:
        if priority == "pending":
            base_cond.append(EmailAnalysis.status == "pending")
        else:
            base_cond.append(EmailAnalysis.priority == priority)

    if unread is not None:
        base_cond.append(EmailAnalysis.is_unread == unread)

    if course:
        base_cond.append(EmailAnalysis.course == course)

    if category:
        base_cond.append(EmailAnalysis.category == category)

    if has_deadline:
        base_cond.append(and_(EmailAnalysis.deadlines.is_not(None), EmailAnalysis.deadlines != "[]"))

    if search and search.strip():
        term = f"%{search.strip()}%"
        base_cond.append(
            or_(
                EmailAnalysis.subject.ilike(term),
                EmailAnalysis.sender.ilike(term),
                EmailAnalysis.sender_name.ilike(term),
                EmailAnalysis.snippet.ilike(term),
                EmailAnalysis.body_text.ilike(term),
            )
        )

    # Calculate summary counts for the sidebar across the whole user mailbox
    counts_res = await db.execute(
        select(
            func.count().label("total"),
            func.sum(case((EmailAnalysis.is_unread == True, 1), else_=0)).label("unread"),
            func.sum(case((EmailAnalysis.priority == "high", 1), else_=0)).label("high"),
            func.sum(case((EmailAnalysis.priority == "medium", 1), else_=0)).label("medium"),
            func.sum(case((EmailAnalysis.priority == "low", 1), else_=0)).label("low"),
            func.sum(case((EmailAnalysis.status == "pending", 1), else_=0)).label("pending"),
            func.sum(case((and_(EmailAnalysis.deadlines.is_not(None), EmailAnalysis.deadlines != "[]"), 1), else_=0)).label("deadlines")
        ).where(EmailAnalysis.user_id == user.id)
    )
    counts_row = counts_res.one()

    # Count pending and overdue tasks
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    task_counts_res = await db.execute(
        select(
            func.sum(case((ActionTask.completed == False, 1), else_=0)).label("pending_tasks"),
            func.sum(case((and_(ActionTask.completed == False, ActionTask.deadline_date < today_str), 1), else_=0)).label("overdue_tasks")
        ).where(ActionTask.user_id == user.id)
    )
    task_counts_row = task_counts_res.one()

    counts = InboxCounts(
        all=counts_row.total or 0,
        unread=counts_row.unread or 0,
        high=counts_row.high or 0,
        medium=counts_row.medium or 0,
        low=counts_row.low or 0,
        pending=counts_row.pending or 0,
        deadlines=counts_row.deadlines or 0,
        tasks_pending=task_counts_row.pending_tasks or 0,
        tasks_overdue=task_counts_row.overdue_tasks or 0,
    )

    # Total matching current filters
    total_matching = await db.scalar(select(func.count()).where(*base_cond))

    # Query items with sorting
    query = select(EmailAnalysis).where(*base_cond)

    if sort == "priority":
        # Group: High (1) -> Medium (2) -> Low (3) -> Pending/Failed (4), then newest within group
        priority_rank = case(
            (EmailAnalysis.priority == "high", 1),
            (EmailAnalysis.priority == "medium", 2),
            (EmailAnalysis.priority == "low", 3),
            else_=4
        )
        query = query.order_by(priority_rank.asc(), EmailAnalysis.received_at.desc())
    else:
        # Strict chronological newest first
        query = query.order_by(EmailAnalysis.received_at.desc())

    query = query.limit(limit).offset(offset)
    results = await db.execute(query)
    records = results.scalars().all()

    # Format email list items
    items = []
    for r in records:
        deadline_count = 0
        next_deadline = None
        action_item_count = 0

        if r.deadlines:
            try:
                dl_list = json.loads(r.deadlines)
                deadline_count = len(dl_list)
                if dl_list and isinstance(dl_list[0], dict):
                    next_deadline = dl_list[0].get("date")
            except Exception:
                pass

        if r.action_items:
            try:
                ai_list = json.loads(r.action_items)
                action_item_count = len(ai_list)
            except Exception:
                pass

        items.append(
            EmailListItem(
                gmail_message_id=r.gmail_message_id,
                thread_id=r.thread_id,
                sender=r.sender,
                sender_name=r.sender_name,
                subject=r.subject or "(No Subject)",
                received_at=r.received_at,
                snippet=r.snippet or "",
                body_preview=r.body_preview or "",
                gmail_link=f"https://mail.google.com/mail/u/0/#inbox/{r.gmail_message_id}",
                is_unread=r.is_unread,
                has_attachments=r.has_attachments,
                status=r.status,
                priority=r.priority,
                priority_reason=r.priority_reason,
                category=r.category,
                course=r.course,
                summary=r.summary,
                deadline_count=deadline_count,
                action_item_count=action_item_count,
                next_deadline=next_deadline,
            )
        )

    # Sync state lookup
    sync_res = await db.execute(select(UserSyncState).where(UserSyncState.user_id == user.id))
    sync_rec = sync_res.scalar_one_or_none()

    sync_state = SyncStateResponse(
        status="syncing" if _USER_SYNC_LOCKS.get(user.id) else (sync_rec.sync_status if sync_rec else "idle"),
        last_synced_at=sync_rec.last_synced_at if sync_rec else None,
        total_synced=sync_rec.total_synced if sync_rec else counts.all,
        total_available=sync_rec.total_available if sync_rec else 0,
        is_initial_sync_complete=sync_rec.is_initial_sync_complete if sync_rec else False,
        sync_progress=sync_rec.sync_progress if sync_rec else counts.all,
        error=sync_rec.sync_error if sync_rec else None,
    )

    # Auto-sync trigger on initial load, empty mailbox, incomplete initial sync, or stale cache
    should_auto_sync = (
        (counts.all == 0)
        or (sync_rec is None)
        or (not sync_rec.is_initial_sync_complete)
        or (sync_rec.total_available > 0 and counts.all < sync_rec.total_available)
        or (sync_rec.last_synced_at and (utcnow() - sync_rec.last_synced_at.replace(tzinfo=timezone.utc)) > timedelta(minutes=15))
    )
    if should_auto_sync and not _USER_SYNC_LOCKS.get(user.id):
        background_tasks.add_task(_background_sync_task, user.id)
        sync_state.status = "syncing"

    t_total = (time.perf_counter() - t_start) * 1000
    print(f"[INBOX] Served {len(items)} emails (total matching: {total_matching}) in {t_total:.1f}ms")

    return InboxResponse(
        emails=items,
        total=total_matching or 0,
        limit=limit,
        offset=offset,
        counts=counts,
        sync_state=sync_state
    )


@router.post("/sync", response_model=SyncTimingStats)
async def trigger_sync(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Sub-second Gmail synchronization.
    1. Runs incremental history sync directly (typically 200–800ms) or first chunk of initial import.
    2. Persists newly discovered Gmail messages into SQLite.
    3. Queues progressive import or AI analysis in the background without blocking.
    4. Returns verified telemetry proving all changes have been saved to database.
    """
    if _USER_SYNC_LOCKS.get(user.id):
        # A sync is already in flight, return current state
        sync_res = await db.execute(select(UserSyncState).where(UserSyncState.user_id == user.id))
        st = sync_res.scalar_one_or_none()
        return SyncTimingStats(
            status="already_syncing",
            sync_type="incremental_history",
            new_messages=0,
            total_synced=st.total_synced if st else 0,
            total_available=st.total_available if st else 0,
            is_initial_sync_complete=st.is_initial_sync_complete if st else False,
            gmail_api_ms=0.0,
            db_ms=0.0,
            total_sync_ms=0.0,
            history_id=st.last_history_id if st else None,
            last_synced_at=st.last_synced_at if st else utcnow(),
        )

    _USER_SYNC_LOCKS[user.id] = True
    try:
        sync_result = await sync_user_emails(user, db, first_chunk_only=True)
    finally:
        _USER_SYNC_LOCKS.pop(user.id, None)

    # If initial sync is not complete, schedule background completion task
    if not sync_result.is_initial_sync_complete:
        background_tasks.add_task(complete_initial_sync_background, user.id)

    # Schedule background AI analysis for any pending unanalyzed emails
    background_tasks.add_task(process_pending_email_batch, user.id, 20)

    return SyncTimingStats(
        status="completed",
        sync_type=sync_result.sync_type,
        new_messages=len(sync_result.new_message_ids),
        total_synced=sync_result.total_synced,
        total_available=sync_result.total_available,
        is_initial_sync_complete=sync_result.is_initial_sync_complete,
        gmail_api_ms=sync_result.gmail_api_time_ms,
        db_ms=sync_result.db_time_ms,
        total_sync_ms=sync_result.total_time_ms,
        history_id=sync_result.history_id,
        last_synced_at=utcnow(),
    )


@router.get("/emails/{gmail_message_id}", response_model=EmailDetailResponse)
async def get_email_detail(
    gmail_message_id: str,
    mark_read: bool = Query(True),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get full email detail and analysis for right-side detail panel.
    Returns immediately with cached data; marks email as read in local cache.
    """
    res = await db.execute(
        select(EmailAnalysis).where(
            EmailAnalysis.gmail_message_id == gmail_message_id,
            EmailAnalysis.user_id == user.id
        )
    )
    email = res.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    if mark_read and email.is_unread:
        email.is_unread = False
        await db.commit()

    analysis_result = None
    if email.analysis:
        try:
            analysis_result = EmailAnalysisResult.model_validate_json(email.analysis)
        except Exception:
            pass

    return EmailDetailResponse(
        gmail_message_id=email.gmail_message_id,
        thread_id=email.thread_id,
        sender=email.sender,
        sender_name=email.sender_name,
        subject=email.subject or "(No Subject)",
        received_at=email.received_at,
        snippet=email.snippet or "",
        gmail_link=f"https://mail.google.com/mail/u/0/#inbox/{email.gmail_message_id}",
        is_unread=email.is_unread,
        has_attachments=email.has_attachments,
        body_text=email.body_text or email.snippet or "",
        body_html=email.body_html or "",
        status=email.status,
        analysis=analysis_result,
        analyzed_at=email.analyzed_at,
    )


@router.post("/emails/{gmail_message_id}/analyze", response_model=EmailDetailResponse)
async def analyze_single_email(
    gmail_message_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    On-demand prioritized analysis for a specific email.
    If already analyzed, returns cached result instantly.
    """
    email = await analyze_message_by_id(gmail_message_id, user.id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    analysis_result = None
    if email.analysis:
        try:
            analysis_result = EmailAnalysisResult.model_validate_json(email.analysis)
        except Exception:
            pass

    return EmailDetailResponse(
        gmail_message_id=email.gmail_message_id,
        thread_id=email.thread_id,
        sender=email.sender,
        sender_name=email.sender_name,
        subject=email.subject or "(No Subject)",
        received_at=email.received_at,
        snippet=email.snippet or "",
        gmail_link=f"https://mail.google.com/mail/u/0/#inbox/{email.gmail_message_id}",
        is_unread=email.is_unread,
        has_attachments=email.has_attachments,
        body_text=email.body_text or email.snippet or "",
        body_html=email.body_html or "",
        status=email.status,
        analysis=analysis_result,
        analyzed_at=email.analyzed_at,
    )


@router.patch("/emails/{gmail_message_id}")
async def update_email_status(
    gmail_message_id: str,
    is_unread: Optional[bool] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle read/unread status in local cache."""
    res = await db.execute(
        select(EmailAnalysis).where(
            EmailAnalysis.gmail_message_id == gmail_message_id,
            EmailAnalysis.user_id == user.id
        )
    )
    email = res.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    if is_unread is not None:
        email.is_unread = is_unread
        await db.commit()

    return {"status": "ok", "is_unread": email.is_unread}


@router.get("/briefing", response_model=DailyBriefing)
async def get_daily_briefing(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Daily Academic Briefing computed from stored SQLite data (Section 11).
    Zero extra Gemini latency.
    """
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    next_week_str = (now + timedelta(days=7)).strftime("%Y-%m-%d")

    # 1. Unread requiring attention: unread AND (high priority OR has action items)
    unread_res = await db.execute(
        select(func.count()).where(
            EmailAnalysis.user_id == user.id,
            EmailAnalysis.is_unread == True,
            or_(
                EmailAnalysis.priority == "high",
                and_(EmailAnalysis.action_items.is_not(None), EmailAnalysis.action_items != "[]")
            )
        )
    )
    unread_count = unread_res.scalar() or 0

    # 2. Upcoming tasks/deadlines in next 7 days
    upcoming_tasks_res = await db.execute(
        select(ActionTask, EmailAnalysis.subject, EmailAnalysis.sender_name, EmailAnalysis.sender)
        .outerjoin(EmailAnalysis, ActionTask.gmail_message_id == EmailAnalysis.gmail_message_id)
        .where(
            ActionTask.user_id == user.id,
            ActionTask.completed == False,
            ActionTask.deadline_date >= today_str,
            ActionTask.deadline_date <= next_week_str
        )
        .order_by(ActionTask.deadline_date.asc())
        .limit(10)
    )
    upcoming_rows = upcoming_tasks_res.all()
    upcoming_tasks = [
        TaskResponse(
            id=task.id,
            gmail_message_id=task.gmail_message_id,
            email_subject=subject,
            email_sender=sender_name or sender,
            title=task.title,
            deadline_date=task.deadline_date,
            deadline_time=task.deadline_time,
            deadline_confidence=task.deadline_confidence,
            completed=task.completed,
            completed_at=task.completed_at,
            course=task.course,
            priority=task.priority,
            created_at=task.created_at
        )
        for task, subject, sender_name, sender in upcoming_rows
    ]

    # 3. Overdue tasks count
    overdue_res = await db.execute(
        select(func.count()).where(
            ActionTask.user_id == user.id,
            ActionTask.completed == False,
            ActionTask.deadline_date < today_str,
            ActionTask.deadline_date.is_not(None)
        )
    )
    overdue_count = overdue_res.scalar() or 0

    # 4. High priority count & top 3 recent high priority emails
    high_prio_res = await db.execute(
        select(EmailAnalysis).where(
            EmailAnalysis.user_id == user.id,
            EmailAnalysis.priority == "high"
        ).order_by(EmailAnalysis.received_at.desc()).limit(3)
    )
    high_prio_emails = high_prio_res.scalars().all()

    recent_high = [
        EmailListItem(
            gmail_message_id=r.gmail_message_id,
            thread_id=r.thread_id,
            sender=r.sender,
            sender_name=r.sender_name,
            subject=r.subject or "(No Subject)",
            received_at=r.received_at,
            snippet=r.snippet or "",
            body_preview=r.body_preview or "",
            gmail_link=f"https://mail.google.com/mail/u/0/#inbox/{r.gmail_message_id}",
            is_unread=r.is_unread,
            has_attachments=r.has_attachments,
            status=r.status,
            priority=r.priority,
            priority_reason=r.priority_reason,
            category=r.category,
            course=r.course,
            summary=r.summary,
        )
        for r in high_prio_emails
    ]

    total_high_res = await db.execute(
        select(func.count()).where(
            EmailAnalysis.user_id == user.id,
            EmailAnalysis.priority == "high"
        )
    )
    total_high = total_high_res.scalar() or 0

    # 5. Sync metadata
    sync_res = await db.execute(select(UserSyncState).where(UserSyncState.user_id == user.id))
    sync_rec = sync_res.scalar_one_or_none()

    return DailyBriefing(
        unread_requiring_attention=unread_count,
        upcoming_deadlines_count=len(upcoming_tasks),
        overdue_tasks_count=overdue_count,
        high_priority_count=total_high,
        new_since_last_sync=0,
        last_synced_at=sync_rec.last_synced_at if sync_rec else None,
        upcoming_deadlines=upcoming_tasks,
        recent_high_priority=recent_high,
    )


# Backward compatibility for Phase 3/4 testing endpoint
@router.post("/emails/analyze", response_model=list[EmailCardResponse])
async def legacy_analyze_inbox(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Legacy backward-compatible endpoint for older tests."""
    await sync_user_emails(user, db)
    await process_pending_email_batch(user.id, limit=10)

    res = await db.execute(
        select(EmailAnalysis).where(EmailAnalysis.user_id == user.id).order_by(EmailAnalysis.received_at.desc()).limit(30)
    )
    emails = res.scalars().all()

    cards = []
    for e in emails:
        analysis_obj = None
        if e.analysis:
            try:
                analysis_obj = EmailAnalysisResult.model_validate_json(e.analysis)
            except Exception:
                pass
        cards.append(
            EmailCardResponse(
                gmail_message_id=e.gmail_message_id,
                subject=e.subject or "(No Subject)",
                sender=e.sender,
                received_at=e.received_at,
                body_preview=e.body_preview or "",
                gmail_link=f"https://mail.google.com/mail/u/0/#inbox/{e.gmail_message_id}",
                analysis=analysis_obj,
            )
        )
    return cards
