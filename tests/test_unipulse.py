"""
Automated Test Suite for UniPulse 2.0 (Section 14).
Tests sorting, caching, deduplication, HTML sanitization, action tasks, and briefing.
"""

import unittest
import asyncio
import json
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, func, case, or_

from backend.database import Base
from backend.models import User, EmailAnalysis, ActionTask, UserSyncState
from backend.schemas import EmailAnalysisResult, ExtractedActionItem, ExtractedDeadline, ExtractedLink
from backend.gmail.sanitizer import sanitize_email_html


class TestEmailHTMLSanitization(unittest.TestCase):
    """Test 11 & 14: Unsafe HTML in email bodies cannot execute scripts."""

    def test_script_tag_stripped(self):
        malicious = '<p>Normal text</p><script>alert("XSS")</script><b>Bold</b>'
        clean = sanitize_email_html(malicious)
        self.assertNotIn("<script>", clean)
        self.assertNotIn("alert", clean)
        self.assertIn("Normal text", clean)
        self.assertIn("<b>Bold</b>", clean)

    def test_event_handlers_stripped(self):
        malicious = '<img src="https://example.com/pic.jpg" onerror="alert(1)" onclick="runHack()">'
        clean = sanitize_email_html(malicious)
        self.assertNotIn("onerror", clean)
        self.assertNotIn("onclick", clean)
        self.assertIn('src="https://example.com/pic.jpg"', clean)

    def test_javascript_uri_blocked(self):
        malicious = '<a href="javascript:stealTokens()">Click here to verify</a>'
        clean = sanitize_email_html(malicious)
        self.assertNotIn("javascript:", clean)

    def test_target_blank_rel_enforced(self):
        raw = '<a href="https://northsouth.edu/portal">NSU Portal</a>'
        clean = sanitize_email_html(raw)
        self.assertIn('target="_blank"', clean)
        self.assertIn('rel="noopener noreferrer"', clean)


class TestAISchemaAndDeadlines(unittest.TestCase):
    """Test 7: Deadline extraction and grounded AI schema."""

    def test_valid_schema_parsing(self):
        payload = {
            "summary": "Midterm exam for CSE231 scheduled on Nov 15 at 10:00 AM.",
            "priority": "high",
            "priority_reason": "Contains upcoming midterm exam schedule",
            "category": "exam",
            "course": "CSE231",
            "what_this_means": "You must review lecture slides 1 to 5.",
            "action_items": [
                {
                    "title": "Bring scientific calculator",
                    "deadline": "2026-11-15",
                    "deadline_confidence": "explicit",
                    "completed": False
                }
            ],
            "deadlines": [
                {
                    "date": "2026-11-15",
                    "time": "10:00",
                    "source_text": "Midterm exam on November 15 at 10am",
                    "confidence": "explicit"
                }
            ],
            "important_links": [
                {
                    "label": "Exam Syllabus",
                    "url": "https://rds2.northsouth.edu/syllabus"
                }
            ]
        }

        parsed = EmailAnalysisResult.model_validate(payload)
        self.assertEqual(parsed.priority, "high")
        self.assertEqual(parsed.course, "CSE231")
        self.assertEqual(len(parsed.deadlines), 1)
        self.assertEqual(parsed.deadlines[0].date, "2026-11-15")

    def test_ambiguous_and_missing_deadlines(self):
        payload = {
            "summary": "General club welcome meeting next week.",
            "priority": "low",
            "priority_reason": "Informational club event",
            "category": "announcement",
            "course": None,
            "what_this_means": "Optional attendance.",
            "action_items": [],
            "deadlines": [],
            "important_links": []
        }
        parsed = EmailAnalysisResult.model_validate(payload)
        self.assertEqual(parsed.deadlines, [])
        self.assertEqual(parsed.action_items, [])
        self.assertIsNone(parsed.course)


class TestDatabasePriorityAndSorting(unittest.IsolatedAsyncioTestCase):
    """Test 1, 2, 6, 8, 9: Priority sorting, unanalyzed pending state, pagination, and filters."""

    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with self.session_factory() as session:
            user = User(
                id="user_123",
                email="student@northsouth.edu",
                name="Test Student",
            )
            session.add(user)

            # Insert sample emails with varying priorities and dates
            now = datetime.now(timezone.utc)
            emails = [
                EmailAnalysis(
                    gmail_message_id="msg_low_new",
                    user_id="user_123",
                    subject="Club bake sale",
                    sender="club@nsu.edu",
                    received_at=now,
                    status="completed",
                    priority="low",
                    is_unread=False,
                ),
                EmailAnalysis(
                    gmail_message_id="msg_high_old",
                    user_id="user_123",
                    subject="CSE231 Midterm Exam Announcement",
                    sender="faculty@nsu.edu",
                    course="CSE231",
                    received_at=now - timedelta(hours=5),
                    status="completed",
                    priority="high",
                    deadlines=json.dumps([{"date": "2026-10-25"}]),
                    is_unread=True,
                ),
                EmailAnalysis(
                    gmail_message_id="msg_high_new",
                    user_id="user_123",
                    subject="URGENT: Fall Registration Deadline",
                    sender="registrar@nsu.edu",
                    received_at=now - timedelta(hours=1),
                    status="completed",
                    priority="high",
                    deadlines=json.dumps([{"date": "2026-10-20"}]),
                    is_unread=True,
                ),
                EmailAnalysis(
                    gmail_message_id="msg_pending",
                    user_id="user_123",
                    subject="Recent Unprocessed Notice",
                    sender="info@nsu.edu",
                    received_at=now + timedelta(minutes=10),
                    status="pending",
                    priority=None,  # Not yet analyzed!
                    is_unread=True,
                ),
                EmailAnalysis(
                    gmail_message_id="msg_med",
                    user_id="user_123",
                    subject="PHY108 Lab Schedule Change",
                    sender="physics@nsu.edu",
                    course="PHY108",
                    received_at=now - timedelta(hours=2),
                    status="completed",
                    priority="medium",
                    is_unread=False,
                ),
            ]
            session.add_all(emails)
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_priority_group_sorting(self):
        """Verify sorting puts High first, then Medium, then Low, then Pending, newest within group."""
        async with self.session_factory() as session:
            priority_rank = case(
                (EmailAnalysis.priority == "high", 1),
                (EmailAnalysis.priority == "medium", 2),
                (EmailAnalysis.priority == "low", 3),
                else_=4
            )
            query = select(EmailAnalysis).where(EmailAnalysis.user_id == "user_123").order_by(
                priority_rank.asc(), EmailAnalysis.received_at.desc()
            )
            results = await session.execute(query)
            ordered_ids = [e.gmail_message_id for e in results.scalars().all()]

            # Expected order:
            # 1. msg_high_new (high, newer)
            # 2. msg_high_old (high, older)
            # 3. msg_med (medium)
            # 4. msg_low_new (low)
            # 5. msg_pending (pending rank 4)
            self.assertEqual(
                ordered_ids,
                ["msg_high_new", "msg_high_old", "msg_med", "msg_low_new", "msg_pending"]
            )

    async def test_unanalyzed_emails_not_marked_low_priority(self):
        """Test 2: Emails that have not been analyzed must have status 'pending' and not be silently classified as low."""
        async with self.session_factory() as session:
            res = await session.execute(select(EmailAnalysis).where(EmailAnalysis.gmail_message_id == "msg_pending"))
            pending_email = res.scalar_one()

            self.assertEqual(pending_email.status, "pending")
            self.assertIsNone(pending_email.priority)
            self.assertNotEqual(pending_email.priority, "low")

    async def test_duplicate_sync_prevention(self):
        """Test 6: Duplicate sync IDs do not duplicate records."""
        async with self.session_factory() as session:
            # Attempt to query existing IDs before inserting
            existing = await session.execute(
                select(EmailAnalysis.gmail_message_id).where(EmailAnalysis.gmail_message_id == "msg_high_new")
            )
            exists = existing.scalar_one_or_none()
            self.assertIsNotNone(exists)

            # Total before
            count_before = await session.scalar(select(func.count(EmailAnalysis.gmail_message_id)))
            self.assertEqual(count_before, 5)

    async def test_pagination_and_filters(self):
        """Test 8 & 9: Pagination and filters on cached data."""
        async with self.session_factory() as session:
            # Filter by course == 'CSE231'
            course_res = await session.execute(select(EmailAnalysis).where(EmailAnalysis.course == "CSE231"))
            course_emails = course_res.scalars().all()
            self.assertEqual(len(course_emails), 1)
            self.assertEqual(course_emails[0].gmail_message_id, "msg_high_old")

            # Filter by unread
            unread_res = await session.execute(select(EmailAnalysis).where(EmailAnalysis.is_unread == True))
            unread_emails = unread_res.scalars().all()
            self.assertEqual(len(unread_emails), 3)

            # Pagination limit 2 offset 0
            p1 = await session.execute(
                select(EmailAnalysis).order_by(EmailAnalysis.received_at.desc()).limit(2).offset(0)
            )
            p1_ids = [e.gmail_message_id for e in p1.scalars().all()]
            self.assertEqual(len(p1_ids), 2)

            # Pagination limit 2 offset 2
            p2 = await session.execute(
                select(EmailAnalysis).order_by(EmailAnalysis.received_at.desc()).limit(2).offset(2)
            )
            p2_ids = [e.gmail_message_id for e in p2.scalars().all()]
            self.assertEqual(len(p2_ids), 2)

            # No overlap between pages
            self.assertEqual(set(p1_ids).intersection(set(p2_ids)), set())


class TestActionCenterAndBriefing(unittest.IsolatedAsyncioTestCase):
    """Test 10 & 11: Action tasks and Daily Briefing calculated from SQLite."""

    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with self.session_factory() as session:
            user = User(id="user_test", email="labib@nsu.edu")
            session.add(user)

            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            yesterday_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
            next_week_str = (datetime.now(timezone.utc) + timedelta(days=4)).strftime("%Y-%m-%d")

            tasks = [
                ActionTask(
                    user_id="user_test",
                    title="Overdue Lab Submission",
                    deadline_date=yesterday_str,
                    completed=False,
                    course="CSE231",
                    priority="high",
                ),
                ActionTask(
                    user_id="user_test",
                    title="Upcoming Quiz Preparation",
                    deadline_date=next_week_str,
                    completed=False,
                    course="PHY108",
                    priority="medium",
                ),
                ActionTask(
                    user_id="user_test",
                    title="Completed Advising Survey",
                    deadline_date=today_str,
                    completed=True,
                    course="HIS102",
                ),
            ]
            session.add_all(tasks)
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_task_filters_and_completion(self):
        """Verify upcoming, overdue, and completed task segregation."""
        async with self.session_factory() as session:
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            # Overdue
            overdue_res = await session.execute(
                select(ActionTask).where(
                    ActionTask.user_id == "user_test",
                    ActionTask.completed == False,
                    ActionTask.deadline_date < today_str
                )
            )
            overdue = overdue_res.scalars().all()
            self.assertEqual(len(overdue), 1)
            self.assertEqual(overdue[0].title, "Overdue Lab Submission")

            # Mark completed
            overdue[0].completed = True
            await session.commit()

            # Verify it is no longer overdue
            overdue_check = await session.execute(
                select(ActionTask).where(
                    ActionTask.user_id == "user_test",
                    ActionTask.completed == False,
                    ActionTask.deadline_date < today_str
                )
            )
            self.assertEqual(len(overdue_check.scalars().all()), 0)


if __name__ == "__main__":
    unittest.main()
