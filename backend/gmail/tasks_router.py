"""
Action Center Tasks Router — handles academic tasks, deadlines, and completion states (Section 10).
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from backend.database import get_db
from backend.models import User, ActionTask, EmailAnalysis, utcnow
from backend.auth.dependencies import get_current_user
from backend.schemas import TaskResponse, TaskCreate, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskResponse])
async def get_tasks(
    filter: Optional[str] = Query("all", description="all, upcoming, overdue, completed"),
    course: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve user tasks filtered by completion, urgency, and course.
    """
    query = (
        select(ActionTask, EmailAnalysis.subject, EmailAnalysis.sender_name, EmailAnalysis.sender)
        .outerjoin(EmailAnalysis, ActionTask.gmail_message_id == EmailAnalysis.gmail_message_id)
        .where(ActionTask.user_id == user.id)
    )

    if course:
        query = query.where(ActionTask.course == course)

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if filter == "completed":
        query = query.where(ActionTask.completed == True)
    elif filter == "upcoming":
        query = query.where(
            ActionTask.completed == False,
            or_(ActionTask.deadline_date >= today_str, ActionTask.deadline_date.is_(None))
        )
    elif filter == "overdue":
        query = query.where(
            ActionTask.completed == False,
            ActionTask.deadline_date < today_str,
            ActionTask.deadline_date.is_not(None)
        )
    # default "all" orders pending first, then by deadline
    query = query.order_by(
        ActionTask.completed.asc(),
        ActionTask.deadline_date.asc().nullslast(),
        ActionTask.created_at.desc()
    )

    results = await db.execute(query)
    rows = results.all()

    response = []
    for task, subject, sender_name, sender in rows:
        sender_display = sender_name or sender
        response.append(
            TaskResponse(
                id=task.id,
                gmail_message_id=task.gmail_message_id,
                email_subject=subject,
                email_sender=sender_display,
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
        )
    return response


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new task manually or from an email deadline."""
    task = ActionTask(
        user_id=user.id,
        gmail_message_id=payload.gmail_message_id,
        title=payload.title,
        deadline_date=payload.deadline_date,
        deadline_time=payload.deadline_time,
        deadline_confidence=payload.deadline_confidence,
        completed=False,
        course=payload.course,
        priority=payload.priority,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    subject = None
    sender = None
    if task.gmail_message_id:
        email_res = await db.execute(select(EmailAnalysis).where(EmailAnalysis.gmail_message_id == task.gmail_message_id))
        email = email_res.scalar_one_or_none()
        if email:
            subject = email.subject
            sender = email.sender_name or email.sender

    return TaskResponse(
        id=task.id,
        gmail_message_id=task.gmail_message_id,
        email_subject=subject,
        email_sender=sender,
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


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle completion status or edit task title/deadline."""
    res = await db.execute(
        select(ActionTask).where(ActionTask.id == task_id, ActionTask.user_id == user.id)
    )
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if payload.title is not None:
        task.title = payload.title
    if payload.completed is not None:
        task.completed = payload.completed
        task.completed_at = utcnow() if payload.completed else None
    if payload.deadline_date is not None:
        task.deadline_date = payload.deadline_date
    if payload.deadline_time is not None:
        task.deadline_time = payload.deadline_time
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.course is not None:
        task.course = payload.course

    await db.commit()
    await db.refresh(task)

    subject = None
    sender = None
    if task.gmail_message_id:
        email_res = await db.execute(select(EmailAnalysis).where(EmailAnalysis.gmail_message_id == task.gmail_message_id))
        email = email_res.scalar_one_or_none()
        if email:
            subject = email.subject
            sender = email.sender_name or email.sender

    return TaskResponse(
        id=task.id,
        gmail_message_id=task.gmail_message_id,
        email_subject=subject,
        email_sender=sender,
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


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a task from the Action Center."""
    res = await db.execute(
        select(ActionTask).where(ActionTask.id == task_id, ActionTask.user_id == user.id)
    )
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()
    return None
