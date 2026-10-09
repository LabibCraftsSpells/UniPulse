"""
Database setup using SQLAlchemy (async).
Includes automated backward-compatible migrations for UniPulse 2.0.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from backend.config import settings

# Create the database engine — this manages the actual connection to SQLite
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)

# Session factory — creates new database sessions
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Base class for all database models
class Base(DeclarativeBase):
    pass


def _migrate_db_sync(connection):
    """
    Synchronous migration callback run inside a connection block.
    Checks SQLite PRAGMA table_info and adds any missing columns safely
    without altering existing records.
    """
    # 1. Check if email_analyses table exists
    result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='email_analyses'")).fetchone()
    if not result:
        return

    # 2. Get existing column names
    columns_info = connection.execute(text("PRAGMA table_info(email_analyses)")).fetchall()
    existing_cols = {col[1] for col in columns_info}

    # Desired new columns with their SQLite type definition
    new_columns = [
        ("thread_id", "VARCHAR"),
        ("sender_name", "VARCHAR"),
        ("snippet", "TEXT"),
        ("body_text", "TEXT"),
        ("body_html", "TEXT"),
        ("is_unread", "BOOLEAN DEFAULT 1"),
        ("has_attachments", "BOOLEAN DEFAULT 0"),
        ("history_id", "VARCHAR"),
        ("status", "VARCHAR DEFAULT 'pending'"),
        ("priority", "VARCHAR"),
        ("priority_reason", "TEXT"),
        ("category", "VARCHAR"),
        ("course", "VARCHAR"),
        ("summary", "TEXT"),
        ("what_this_means", "TEXT"),
        ("action_items", "TEXT"),
        ("deadlines", "TEXT"),
        ("important_links", "TEXT"),
        ("last_synced_at", "DATETIME"),
    ]

    for col_name, col_def in new_columns:
        if col_name not in existing_cols:
            connection.execute(text(f"ALTER TABLE email_analyses ADD COLUMN {col_name} {col_def}"))

    # 3. Check if user_sync_states table exists and migrate new columns
    sync_table = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='user_sync_states'")).fetchone()
    if sync_table:
        sync_cols = {col[1] for col in connection.execute(text("PRAGMA table_info(user_sync_states)")).fetchall()}
        sync_new_cols = [
            ("total_available", "INTEGER DEFAULT 0"),
            ("is_initial_sync_complete", "BOOLEAN DEFAULT 0"),
            ("sync_progress", "INTEGER DEFAULT 0"),
        ]
        for col_name, col_def in sync_new_cols:
            if col_name not in sync_cols:
                connection.execute(text(f"ALTER TABLE user_sync_states ADD COLUMN {col_name} {col_def}"))


async def init_db():
    """
    Create all database tables on startup and run non-destructive migrations.
    """
    # Import models so Base.metadata is aware of all table definitions
    import backend.models  # noqa: F401

    async with engine.begin() as conn:
        # First create any newly declared tables (action_tasks, user_sync_states)
        await conn.run_sync(Base.metadata.create_all)
        # Migrate existing tables with new columns if missing
        await conn.run_sync(_migrate_db_sync)


async def get_db():
    """
    Dependency that provides a database session to API endpoints.
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
