"""
Automated tests for sub-second Gmail synchronization, incremental history sync,
fallback on 404, and database persistence (Priority 1 & 4).
"""

import unittest
from unittest.mock import MagicMock, patch
import asyncio
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from googleapiclient.errors import HttpError
import httplib2

from backend.database import Base
from backend.models import User, EmailAnalysis, UserSyncState
from backend.gmail.service import sync_user_emails


class TestSyncPerformanceAndHistory(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with self.session_factory() as session:
            user = User(
                id="user_perf",
                email="student@northsouth.edu",
                access_token="test_token",
                refresh_token="test_refresh",
            )
            # Create existing sync state with history_id="1000"
            sync_state = UserSyncState(
                user_id="user_perf",
                last_history_id="1000",
                last_synced_at=datetime.now(timezone.utc),
                sync_status="idle",
                total_synced=1,
                is_initial_sync_complete=True,
            )
            existing_email = EmailAnalysis(
                gmail_message_id="msg_existing",
                user_id="user_perf",
                subject="Existing message",
                sender="prof@nsu.edu",
                status="completed",
            )
            session.add_all([user, sync_state, existing_email])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    @patch("backend.gmail.service.get_gmail_service_client")
    async def test_incremental_sync_zero_new_messages(self, mock_get_client):
        """Repeat sync with 0 new messages uses history.list and completes immediately."""
        mock_service = MagicMock()
        mock_history_list = MagicMock()
        # Gmail API returns new historyId and no history records
        mock_history_list.execute.return_value = {
            "historyId": "1050",
            "history": []
        }
        mock_service.users().history().list.return_value = mock_history_list
        mock_get_client.return_value = mock_service

        async with self.session_factory() as session:
            user = await session.scalar(select(User).where(User.id == "user_perf"))

            result = await sync_user_emails(user, session)

            self.assertEqual(result.sync_type, "incremental_history")
            self.assertEqual(result.new_message_ids, [])
            self.assertEqual(result.history_id, "1050")

            # Verify SQLite sync_state was updated
            sync_state = await session.scalar(select(UserSyncState).where(UserSyncState.user_id == "user_perf"))
            self.assertEqual(sync_state.last_history_id, "1050")
            self.assertEqual(sync_state.sync_status, "idle")

    @patch("backend.gmail.service.get_gmail_service_client")
    async def test_incremental_sync_with_new_messages(self, mock_get_client):
        """Repeat sync with new messages fetches ONLY new message details and persists to SQLite."""
        mock_service = MagicMock()

        # 1. history.list returns 1 new message
        mock_history_list = MagicMock()
        mock_history_list.execute.return_value = {
            "historyId": "1100",
            "history": [
                {
                    "messagesAdded": [
                        {"message": {"id": "msg_new_123", "threadId": "th_123"}}
                    ]
                }
            ]
        }
        mock_service.users().history().list.return_value = mock_history_list

        mock_payload = {
            "id": "msg_new_123",
            "threadId": "th_123",
            "historyId": "1100",
            "snippet": "New announcement body",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "CSE231 Lab 4 Released"},
                    {"name": "From", "value": "Dr. Smith <smith@nsu.edu>"},
                    {"name": "Date", "value": "Fri, 09 Oct 2026 12:00:00 +0600"},
                ],
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": "Q1NFMjMxIExhYiA0IGRldGFpbHM="}  # base64 "CSE231 Lab 4 details"
                    }
                ]
            }
        }
        def fake_batch(callback):
            batch_mock = MagicMock()
            def fake_execute():
                callback("msg_new_123", mock_payload, None)
            batch_mock.execute = fake_execute
            return batch_mock

        mock_service.new_batch_http_request.side_effect = fake_batch
        mock_get_client.return_value = mock_service

        async with self.session_factory() as session:
            user = await session.scalar(select(User).where(User.id == "user_perf"))

            result = await sync_user_emails(user, session)

            self.assertEqual(result.sync_type, "incremental_history")
            self.assertEqual(result.new_message_ids, ["msg_new_123"])
            self.assertEqual(result.history_id, "1100")

            # Verify the new email record is persisted in SQLite with status='pending'
            saved_email = await session.scalar(
                select(EmailAnalysis).where(EmailAnalysis.gmail_message_id == "msg_new_123")
            )
            self.assertIsNotNone(saved_email)
            self.assertEqual(saved_email.subject, "CSE231 Lab 4 Released")
            self.assertEqual(saved_email.sender, "smith@nsu.edu")
            self.assertEqual(saved_email.sender_name, "Dr. Smith")
            self.assertEqual(saved_email.status, "pending")
            self.assertTrue(saved_email.is_unread)

    @patch("backend.gmail.service.get_gmail_service_client")
    async def test_fallback_on_404_expired_history(self, mock_get_client):
        """When historyId expires (404), safely fall back to full diff sync."""
        mock_service = MagicMock()

        # 1. history.list throws HttpError 404
        resp = httplib2.Response({"status": 404, "reason": "Not Found"})
        mock_history_list = MagicMock()
        mock_history_list.execute.side_effect = HttpError(resp=resp, content=b"History ID not found")
        mock_service.users().history().list.return_value = mock_history_list

        # 2. getProfile returns fresh historyId
        mock_profile = MagicMock()
        mock_profile.execute.return_value = {"historyId": "2000"}
        mock_service.users().getProfile.return_value = mock_profile

        # 3. messages.list returns existing message
        mock_msg_list = MagicMock()
        mock_msg_list.execute.return_value = {"messages": [{"id": "msg_existing"}]}
        mock_service.users().messages().list.return_value = mock_msg_list

        mock_get_client.return_value = mock_service

        async with self.session_factory() as session:
            user = await session.scalar(select(User).where(User.id == "user_perf"))

            result = await sync_user_emails(user, session)

            # Verified fallback to full diff
            self.assertEqual(result.sync_type, "full_diff")
            self.assertEqual(result.new_message_ids, [])
            self.assertEqual(result.history_id, "2000")

    @patch("backend.gmail.service.get_gmail_service_client")
    async def test_initial_sync_multi_page_pagination(self, mock_get_client):
        """Initial sync paginates through multiple pages with nextPageToken."""
        mock_service = MagicMock()
        mock_profile = MagicMock()
        mock_profile.execute.return_value = {"messagesTotal": "15", "historyId": "3000"}
        mock_service.users().getProfile.return_value = mock_profile

        # Page 1: returns 10 IDs with nextPageToken='token_page_2'
        page1_res = {"messages": [{"id": f"msg_p1_{i}"} for i in range(10)], "nextPageToken": "token_page_2"}
        # Page 2: returns 5 IDs with no nextPageToken
        page2_res = {"messages": [{"id": f"msg_p2_{i}"} for i in range(5)]}

        def fake_list(**kwargs):
            list_mock = MagicMock()
            if kwargs.get("pageToken") == "token_page_2":
                list_mock.execute.return_value = page2_res
            else:
                list_mock.execute.return_value = page1_res
            return list_mock

        mock_service.users().messages().list.side_effect = fake_list

        def fake_batch(callback):
            batch_mock = MagicMock()
            def fake_execute():
                pass
            batch_mock.execute = fake_execute
            return batch_mock

        # When _fetch_messages_batch is called, return items for each id
        def make_msg(mid):
            return {
                "id": mid,
                "threadId": f"th_{mid}",
                "snippet": "Preview",
                "labelIds": ["INBOX"],
                "payload": {"headers": [{"name": "Subject", "value": f"Test {mid}"}]}
            }

        with patch("backend.gmail.service._fetch_messages_batch") as mock_fetch:
            mock_fetch.side_effect = lambda svc, ids: [make_msg(i) for i in ids]
            mock_get_client.return_value = mock_service

            async with self.session_factory() as session:
                # Create a user with NO prior sync state
                new_user = User(
                    id="user_new",
                    email="newbie@northsouth.edu",
                    access_token="tok",
                )
                session.add(new_user)
                await session.commit()

                result = await sync_user_emails(new_user, session, max_emails=0, first_chunk_only=False)

                self.assertEqual(result.sync_type, "full_diff")
                self.assertEqual(len(result.new_message_ids), 15)  # 10 from page 1 + 5 from page 2
                self.assertEqual(result.total_available, 15)
                # When all 15 of 15 messages are imported, it is genuinely complete
                self.assertTrue(result.is_initial_sync_complete)

                # Verify records saved to SQLite
                saved_count = await session.scalar(
                    select(UserSyncState.total_synced).where(UserSyncState.user_id == "user_new")
                )
                self.assertEqual(saved_count, 15)


if __name__ == "__main__":
    unittest.main()
