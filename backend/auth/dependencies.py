"""
Auth dependencies for FastAPI endpoints.

KEY CONCEPT: Protecting API Routes
------------------------------------
When a user visits the dashboard, the frontend makes an API call to get their data.
We need a way to check: "Is this request from a valid, logged-in user?"

This dependency checks the session cookie, looks up the user in the database,
and returns the User object. If they aren't logged in, it throws a 401 error.
"""

from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models import User

async def get_current_user(
    request: Request, 
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the currently authenticated user.
    Usage in route: async def my_route(user: User = Depends(get_current_user))
    """
    user_id = request.session.get("user_id")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
        )

    # Fetch user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        # Session exists but user is deleted from DB
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please log in again.",
        )

    return user
