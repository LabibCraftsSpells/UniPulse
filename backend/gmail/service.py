"""
Gmail service — handles communication with the Gmail API, concurrent fetching,
incremental history synchronization, progressive initial import, and timing telemetry for UniPulse 2.0.
"""

import base64
import asyncio
import time
import email.utils
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from fastapi import HTTPException, status

from backend.config import settings
from backend.models import User, EmailAnalysis, UserSyncState, utcnow
from backend.auth.crypto import decrypt_token
from backend.gmail.sanitizer import sanitize_email_html


@dataclass
class SyncResult:
    """Detailed timing and synchronization telemetry."""
    new_message_ids: list[str]
    total_synced: int
    total_available: int
    is_initial_sync_complete: bool
    gmail_api_time_ms: float
    db_time_ms: float
    total_time_ms: float
    sync_type: str  # "incremental_history" or "full_diff"
    history_id: str | None


def clean_html(html_content: str) -> str:
    """Strip HTML tags from email bodies to get clean plain text."""
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "html.parser")
    for element in soup(["script", "style", "head"]):
        element.decompose()

    text = soup.get_text(separator=" ", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def get_header(headers: list, name: str) -> str:
    """Helper to extract a specific header from Gmail payload."""
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def parse_sender_info(raw_sender: str) -> tuple[str, str]:
    """
    Parse a From header into (display_name, clean_email).
    Example: 'Office of Registrar <registrar@nsu.edu>' -> ('Office of Registrar', 'registrar@nsu.edu')
    """
    if not raw_sender:
        return "", ""
    realname, email_addr = email.utils.parseaddr(raw_sender)
    clean_sender = email_addr if email_addr else raw_sender
    clean_name = realname if realname else email_addr.split("@")[0] if "@" in email_addr else raw_sender
    return clean_name, clean_sender


def extract_parts(payload: dict) -> tuple[str, str, bool]:
    """
    Recursively extract (plain_text, html_content, has_attachments) from message payload.
    """
    body_text = ""
    body_html = ""
    has_attachments = False

    def _walk(part):
        nonlocal body_text, body_html, has_attachments
        filename = part.get("filename")
        if filename:
            has_attachments = True

        mime_type = part.get("mimeType", "")
        data = part.get("body", {}).get("data")

        if data:
            try:
                decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                if mime_type == "text/plain" and not body_text:
                    body_text = decoded
                elif mime_type == "text/html" and not body_html:
                    body_html = decoded
            except Exception:
                pass

        for subpart in part.get("parts", []):
            _walk(subpart)

    _walk(payload)

    # Fallback: if plain text was missing but HTML was present, clean HTML to make plain text
    if not body_text and body_html:
        body_text = clean_html(body_html)

    return body_text, body_html, has_attachments


def get_gmail_service_client(user: User):
    """Build and return an authorized Gmail API service client."""
    access_token = decrypt_token(user.access_token)
    refresh_token = decrypt_token(user.refresh_token)

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No Gmail access token found. Please reconnect your account."
        )

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

    return build("gmail", "v1", credentials=creds)


async def _fetch_messages_batch(service, message_ids: list[str]) -> list[dict]:
    """
    Fetch full message payloads using Gmail's native Batch HTTP API.
    Bundles requests into a single HTTP roundtrip to eliminate socket serialization
    and thread lock contention in httplib2.
    """
    if not message_ids:
        return []

    all_results = []
    chunk_size = 25

    for i in range(0, len(message_ids), chunk_size):
        chunk = message_ids[i:i + chunk_size]
        remaining_chunk = list(chunk)

        attempt = 0
        backoff = 2.0
        while remaining_chunk and attempt < 5:
            batch_results = {}
            failed_chunk_ids = []

            def _callback(request_id, response, exception):
                if exception is None and response:
                    batch_results[request_id] = response
                else:
                    failed_chunk_ids.append((request_id, exception))

            def _execute_batch(ids_to_fetch):
                batch = service.new_batch_http_request(callback=_callback)
                for mid in ids_to_fetch:
                    batch.add(service.users().messages().get(userId="me", id=mid, format="full"), request_id=mid)
                batch.execute()

            try:
                await asyncio.to_thread(_execute_batch, remaining_chunk)
            except HttpError as e:
                if e.resp.status in (429, 403) and attempt < 4:
                    print(f"[BATCH RATE LIMIT] HTTP {e.resp.status}. Backing off {backoff:.1f}s...")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    attempt += 1
                    continue
                else:
                    raise

            all_results.extend(batch_results.values())

            # Check if any individual subrequests failed due to quota/rate limiting
            rate_limited_ids = []
            for mid, exc in failed_chunk_ids:
                if isinstance(exc, HttpError) and exc.resp.status in (429, 403):
                    rate_limited_ids.append(mid)
                elif exc:
                    print(f"[BATCH WARNING] Message {mid} skipped: {exc}")

            if rate_limited_ids:
                print(f"[BATCH RATE LIMIT] {len(rate_limited_ids)} subrequests rate-limited. Backing off {backoff:.1f}s...")
                await asyncio.sleep(backoff)
                backoff *= 2
                remaining_chunk = rate_limited_ids
                attempt += 1
            else:
                remaining_chunk = []

        if i + chunk_size < len(message_ids):
            await asyncio.sleep(0.3)

    return all_results


def _parse_message_to_model(raw_msg: dict, user_id: str) -> EmailAnalysis:
    """Parse raw Gmail API message dict into an EmailAnalysis model instance."""
    msg_id = raw_msg["id"]
    thread_id = raw_msg.get("threadId")
    history_id = raw_msg.get("historyId")
    label_ids = raw_msg.get("labelIds", [])
    is_unread = "UNREAD" in label_ids

    payload = raw_msg.get("payload", {})
    headers = payload.get("headers", [])

    subject = get_header(headers, "Subject") or "(No Subject)"
    raw_sender = get_header(headers, "From")
    sender_name, sender_email = parse_sender_info(raw_sender)
    date_str = get_header(headers, "Date")

    received_at = None
    if date_str:
        try:
            received_at = parsedate_to_datetime(date_str)
        except Exception:
            received_at = utcnow()
    else:
        received_at = utcnow()

    body_text, raw_html, has_attachments = extract_parts(payload)
    snippet = raw_msg.get("snippet", "")
    if not body_text:
        body_text = snippet

    body_html = sanitize_email_html(raw_html) if raw_html else ""
    body_preview = body_text[:500] + ("..." if len(body_text) > 500 else "")

    return EmailAnalysis(
        gmail_message_id=msg_id,
        user_id=user_id,
        thread_id=thread_id,
        sender=sender_email,
        sender_name=sender_name,
        subject=subject,
        received_at=received_at,
        snippet=snippet,
        body_preview=body_preview,
        body_text=body_text,
        body_html=body_html,
        is_unread=is_unread,
        has_attachments=has_attachments,
        history_id=history_id,
        status="pending",
        last_synced_at=utcnow(),
    )


def _collect_gmail_message_ids(service, target_count: int = 0) -> list[str]:
    """
    Paginate through Gmail messages.list using nextPageToken until target_count
    is reached, or the entire mailbox is retrieved if target_count <= 0.
    """
    collected = []
    page_token = None

    while True:
        # Request up to 100 per page (max allowed by Gmail API messages.list)
        batch_size = min(100, target_count - len(collected)) if target_count > 0 else 100
        kwargs = {"userId": "me", "maxResults": batch_size}
        if page_token:
            kwargs["pageToken"] = page_token

        max_retries = 3
        backoff = 2.0
        res = None
        for attempt in range(max_retries):
            try:
                res = service.users().messages().list(**kwargs).execute()
                break
            except HttpError as e:
                if e.resp.status in (429, 403) and attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    raise

        if not res:
            break

        msgs = res.get("messages", [])
        if isinstance(msgs, list):
            collected.extend([m["id"] for m in msgs if isinstance(m, dict) and "id" in m])

        page_token = res.get("nextPageToken")
        if not page_token or not isinstance(page_token, str):
            break
        if target_count > 0 and len(collected) >= target_count:
            break

    return collected


async def sync_user_emails(
    user: User,
    db: AsyncSession,
    max_emails: int = settings.INITIAL_SYNC_MAX_EMAILS,
    first_chunk_only: bool = False
) -> SyncResult:
    """
    Sub-second Gmail synchronization.
    1. If initial sync is complete: runs fast incremental synchronization using Gmail history.list (~500ms).
    2. If initial sync is NOT complete:
       - Paginates through Gmail using nextPageToken to collect intended scope.
       - Discovers all missing messages.
       - Imports in fast 50-message batches.
       - If first_chunk_only is True, imports the first 50 messages immediately (<2s) and leaves remainder for background worker.
    """
    t_start = time.perf_counter()
    gmail_api_time = 0.0
    db_time = 0.0

    service = get_gmail_service_client(user)

    # 1. Retrieve current sync state from SQLite
    t_db_0 = time.perf_counter()
    sync_res = await db.execute(select(UserSyncState).where(UserSyncState.user_id == user.id))
    sync_state = sync_res.scalar_one_or_none()
    db_time += (time.perf_counter() - t_db_0) * 1000

    # Incremental sync is ONLY allowed if initial sync is genuinely complete across all messages
    is_initial_complete = bool(
        sync_state
        and sync_state.is_initial_sync_complete
        and (sync_state.total_available <= 0 or sync_state.total_synced >= sync_state.total_available)
    )
    last_history_id = sync_state.last_history_id if sync_state else None

    # 2. Try Incremental Sync via history.list ONLY IF initial sync was already completed
    if is_initial_complete and last_history_id:
        try:
            t_api_0 = time.perf_counter()
            history_res = await asyncio.to_thread(
                service.users().history().list(
                    userId="me",
                    startHistoryId=last_history_id,
                    historyTypes=["messageAdded"],
                    maxResults=50
                ).execute
            )
            api_dur = (time.perf_counter() - t_api_0) * 1000
            gmail_api_time += api_dur

            new_history_id = str(history_res.get("historyId", last_history_id))
            history_records = history_res.get("history", [])

            # Extract any newly added message IDs
            added_ids = []
            for h in history_records:
                for added in h.get("messagesAdded", []):
                    msg = added.get("message", {})
                    if msg.get("id"):
                        added_ids.append(msg["id"])

            added_ids = list(set(added_ids))

            if not added_ids:
                # ZERO NEW MESSAGES! Super fast path (<500-600ms).
                t_db_1 = time.perf_counter()
                if sync_state:
                    sync_state.last_history_id = new_history_id
                    sync_state.last_synced_at = utcnow()
                    sync_state.sync_status = "idle"
                    await db.commit()
                db_time += (time.perf_counter() - t_db_1) * 1000

                total_dur = (time.perf_counter() - t_start) * 1000
                total_synced = sync_state.total_synced if sync_state else 0
                total_available = sync_state.total_available if sync_state else total_synced
                print(f"[SYNC] Incremental (0 new): Gmail API: {gmail_api_time:.1f}ms | DB: {db_time:.1f}ms | Total: {total_dur:.1f}ms")

                return SyncResult(
                    new_message_ids=[],
                    total_synced=total_synced,
                    total_available=total_available,
                    is_initial_sync_complete=True,
                    gmail_api_time_ms=round(gmail_api_time, 1),
                    db_time_ms=round(db_time, 1),
                    total_time_ms=round(total_dur, 1),
                    sync_type="incremental_history",
                    history_id=new_history_id,
                )

            # Check if any of these are already in SQLite
            t_db_2 = time.perf_counter()
            existing_res = await db.execute(
                select(EmailAnalysis.gmail_message_id).where(
                    EmailAnalysis.user_id == user.id,
                    EmailAnalysis.gmail_message_id.in_(added_ids)
                )
            )
            already_cached = set(existing_res.scalars().all())
            truly_new_ids = [mid for mid in added_ids if mid not in already_cached]
            db_time += (time.perf_counter() - t_db_2) * 1000

            if truly_new_ids:
                t_api_1 = time.perf_counter()
                raw_messages = await _fetch_messages_batch(service, truly_new_ids)
                gmail_api_time += (time.perf_counter() - t_api_1) * 1000

                t_db_3 = time.perf_counter()
                new_models = [_parse_message_to_model(m, user.id) for m in raw_messages]
                if new_models:
                    db.add_all(new_models)

                total_in_db = await db.scalar(
                    select(func.count(EmailAnalysis.gmail_message_id)).where(EmailAnalysis.user_id == user.id)
                ) or 0

                sync_state.last_history_id = new_history_id
                sync_state.last_synced_at = utcnow()
                sync_state.sync_status = "idle"
                sync_state.total_synced = total_in_db + len(new_models)

                await db.commit()
                db_time += (time.perf_counter() - t_db_3) * 1000

                total_dur = (time.perf_counter() - t_start) * 1000
                print(f"[SYNC] Incremental ({len(truly_new_ids)} new): Gmail API: {gmail_api_time:.1f}ms | DB: {db_time:.1f}ms | Total: {total_dur:.1f}ms")

                return SyncResult(
                    new_message_ids=truly_new_ids,
                    total_synced=sync_state.total_synced,
                    total_available=sync_state.total_available,
                    is_initial_sync_complete=True,
                    gmail_api_time_ms=round(gmail_api_time, 1),
                    db_time_ms=round(db_time, 1),
                    total_time_ms=round(total_dur, 1),
                    sync_type="incremental_history",
                    history_id=new_history_id,
                )

        except HttpError as e:
            if e.resp.status == 404:
                print(f"[SYNC WARNING] startHistoryId {last_history_id} expired or invalid. Falling back to full pagination...")
            else:
                print(f"[SYNC ERROR] Gmail API error during history.list: {e}")
                raise HTTPException(status_code=502, detail="Gmail synchronization failed.")
        except RefreshError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Gmail session expired or revoked. Please disconnect and reconnect your account."
            )

    # 3. Initial Import / Fallback Sync with nextPageToken pagination
    try:
        t_api_f = time.perf_counter()
        profile = await asyncio.to_thread(service.users().getProfile(userId="me").execute)
        total_available = int(profile.get("messagesTotal", 0))
        latest_history_id = str(profile.get("historyId", ""))

        # Paginate through Gmail results until max_emails is reached
        incoming_ids = await asyncio.to_thread(_collect_gmail_message_ids, service, max_emails)
        gmail_api_time += (time.perf_counter() - t_api_f) * 1000
    except RefreshError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gmail session expired or revoked. Please disconnect and reconnect your account."
        )
    except Exception as e:
        print(f"[SYNC ERROR] Failed listing messages from Gmail: {e}")
        raise HTTPException(status_code=502, detail="Failed to connect to Gmail API.")

    t_db_f0 = time.perf_counter()
    existing_result = await db.execute(
        select(EmailAnalysis.gmail_message_id).where(
            EmailAnalysis.user_id == user.id,
            EmailAnalysis.gmail_message_id.in_(incoming_ids)
        )
    )
    existing_ids = set(existing_result.scalars().all())
    missing_ids = [mid for mid in incoming_ids if mid not in existing_ids]
    db_time += (time.perf_counter() - t_db_f0) * 1000

    print(f"[SYNC] Initial Import Scope: {len(incoming_ids)} target messages across pages ({total_available} total in mailbox). {len(existing_ids)} in SQLite, {len(missing_ids)} to import.")

    # Determine which missing IDs to import in this immediate request
    if first_chunk_only and len(missing_ids) > settings.SYNC_BATCH_SIZE:
        ids_to_import_now = missing_ids[:settings.SYNC_BATCH_SIZE]
        initial_complete = False
    else:
        ids_to_import_now = missing_ids
        initial_complete = (
            (len(missing_ids) == len(ids_to_import_now))
            and (total_available <= 0 or (len(existing_ids) + len(ids_to_import_now)) >= total_available)
        )

    new_models = []
    if ids_to_import_now:
        t_api_f1 = time.perf_counter()
        raw_msgs = await _fetch_messages_batch(service, ids_to_import_now)
        gmail_api_time += (time.perf_counter() - t_api_f1) * 1000

        new_models = [_parse_message_to_model(m, user.id) for m in raw_msgs]

    t_db_f1 = time.perf_counter()
    if new_models:
        db.add_all(new_models)

    total_in_db = len(existing_ids) + len(new_models)

    if not sync_state:
        sync_state = UserSyncState(
            user_id=user.id,
            last_history_id=latest_history_id,
            last_synced_at=utcnow(),
            sync_status="syncing" if not initial_complete else "idle",
            total_synced=total_in_db,
            total_available=total_available,
            is_initial_sync_complete=initial_complete,
            sync_progress=total_in_db,
        )
        db.add(sync_state)
    else:
        sync_state.last_history_id = latest_history_id
        sync_state.last_synced_at = utcnow()
        sync_state.sync_status = "syncing" if not initial_complete else "idle"
        sync_state.total_synced = total_in_db
        sync_state.total_available = total_available
        sync_state.is_initial_sync_complete = initial_complete
        sync_state.sync_progress = total_in_db

    await db.commit()
    db_time += (time.perf_counter() - t_db_f1) * 1000

    total_dur = (time.perf_counter() - t_start) * 1000
    print(f"[SYNC] Import batch ({len(new_models)} new / {total_in_db} total cached): Gmail API: {gmail_api_time:.1f}ms | DB: {db_time:.1f}ms | Total: {total_dur:.1f}ms | Initial complete: {initial_complete}")

    return SyncResult(
        new_message_ids=[m.gmail_message_id for m in new_models],
        total_synced=sync_state.total_synced,
        total_available=total_available,
        is_initial_sync_complete=initial_complete,
        gmail_api_time_ms=round(gmail_api_time, 1),
        db_time_ms=round(db_time, 1),
        total_time_ms=round(total_dur, 1),
        sync_type="full_diff",
        history_id=latest_history_id,
    )


_INITIAL_IMPORT_LOCKS: dict[str, bool] = {}


async def complete_initial_sync_background(user_id: str, max_emails: int = settings.INITIAL_SYNC_MAX_EMAILS):
    """
    Background worker that continues importing remaining batches of emails until
    the full mailbox scope is fully imported.
    """
    if _INITIAL_IMPORT_LOCKS.get(user_id):
        print(f"[BACKGROUND IMPORT] Import already in progress for user {user_id}. Skipping.")
        return

    _INITIAL_IMPORT_LOCKS[user_id] = True
    try:
        from backend.database import async_session
        from backend.ai.analyzer import process_pending_email_batch

        async with async_session() as db:
            user_res = await db.execute(select(User).where(User.id == user_id))
            user = user_res.scalar_one_or_none()
            if not user:
                return

            sync_res = await db.execute(select(UserSyncState).where(UserSyncState.user_id == user_id))
            sync_state = sync_res.scalar_one_or_none()
            if not sync_state:
                return
            # If initial sync was marked complete prematurely but mailbox has more:
            if sync_state.is_initial_sync_complete and sync_state.total_available > 0 and sync_state.total_synced >= sync_state.total_available:
                return

            print(f"[BACKGROUND IMPORT] Resuming full import for user {user.email}...")
            service = get_gmail_service_client(user)

            profile = await asyncio.to_thread(service.users().getProfile(userId="me").execute)
            total_available = int(profile.get("messagesTotal", 0))
            latest_history_id = str(profile.get("historyId", ""))
            sync_state.total_available = total_available
            sync_state.last_history_id = latest_history_id

            incoming_ids = await asyncio.to_thread(_collect_gmail_message_ids, service, max_emails)

            # Check what is still missing (Duplicate Prevention)
            existing_res = await db.execute(
                select(EmailAnalysis.gmail_message_id).where(
                    EmailAnalysis.user_id == user.id,
                    EmailAnalysis.gmail_message_id.in_(incoming_ids)
                )
            )
            existing_ids = set(existing_res.scalars().all())
            missing_ids = [mid for mid in incoming_ids if mid not in existing_ids]

            chunk_size = settings.SYNC_BATCH_SIZE
            imported_count = len(existing_ids)

            print(f"[BACKGROUND IMPORT] Mailbox: {len(incoming_ids)} IDs found ({total_available} total in Gmail). {len(existing_ids)} in SQLite, {len(missing_ids)} to import.")

            for i in range(0, len(missing_ids), chunk_size):
                chunk = missing_ids[i:i + chunk_size]
                t0 = time.perf_counter()
                raw_msgs = await _fetch_messages_batch(service, chunk)
                new_models = [_parse_message_to_model(m, user.id) for m in raw_msgs]
                if new_models:
                    db.add_all(new_models)

                imported_count += len(new_models)
                sync_state.total_synced = imported_count
                sync_state.sync_progress = imported_count
                sync_state.sync_status = "syncing"
                await db.commit()

                dur = (time.perf_counter() - t0) * 1000
                print(f"[BACKGROUND IMPORT] Imported batch of {len(new_models)} emails in {dur:.1f}ms ({imported_count}/{len(incoming_ids)} total).")
                await asyncio.sleep(0.2)

            # Genuinely complete ONLY when all mailbox messages are stored in SQLite
            total_in_db = await db.scalar(
                select(func.count(EmailAnalysis.gmail_message_id)).where(EmailAnalysis.user_id == user.id)
            ) or 0

            is_fully_done = (total_available <= 0 or total_in_db >= total_available or len(missing_ids) == 0)
            sync_state.is_initial_sync_complete = is_fully_done
            sync_state.total_synced = total_in_db
            sync_state.sync_progress = total_in_db
            sync_state.sync_status = "idle" if is_fully_done else "syncing"
            sync_state.last_synced_at = utcnow()
            await db.commit()
            print(f"[BACKGROUND IMPORT] Finished import for {user.email}: {total_in_db} in SQLite / {total_available} in mailbox. Genuinely complete: {is_fully_done}")

        # Queue background AI analysis for a manageable batch of newly imported emails
        await process_pending_email_batch(user_id, limit=10)
    finally:
        _INITIAL_IMPORT_LOCKS.pop(user_id, None)
