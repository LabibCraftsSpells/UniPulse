"""
Database setup using SQLAlchemy (async).

KEY CONCEPT: ORM (Object-Relational Mapper)
---------------------------------------------
Instead of writing raw SQL, an ORM lets you define database tables as
Python classes. SQLAlchemy then translates your Python code into SQL.

Example:
    Python: User(email="labib@gmail.com")
    SQL:    INSERT INTO users (email) VALUES ('labib@gmail.com')

KEY CONCEPT: Async Database
-----------------------------
FastAPI is async (handles many requests at once). We use aiosqlite
so database queries don't block other requests while waiting for I/O.

KEY CONCEPT: Sessions
-----------------------
A database "session" is like a conversation with the database.
You open one, do your queries, then close it. The get_db() function
below handles this automatically for each API request.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from backend.config import settings

# Create the database engine — this manages the actual connection to SQLite
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set True to see SQL queries in terminal (useful for debugging)
)

# Session factory — creates new database sessions
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Base class for all database models
class Base(DeclarativeBase):
    pass


async def init_db():
    """
    Create all database tables on startup.
    
    This looks at all classes that inherit from Base (our models)
    and creates the corresponding tables in SQLite if they don't exist.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """
    Dependency that provides a database session to API endpoints.
    
    KEY CONCEPT: Dependency Injection
    -----------------------------------
    FastAPI's dependency system. When an endpoint declares:
    
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
    
    FastAPI automatically:
    1. Calls get_db() to create a session
    2. Passes it to your endpoint function
    3. Closes the session after the request finishes
    
    The "yield" keyword makes this a generator — code before yield runs
    before the request, code after yield runs after the request (cleanup).
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
