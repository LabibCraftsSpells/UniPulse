"""
Student profile router — manage academic context for AI relevance.

The student profile tells Gemini what's relevant to THIS student.
Without it, the AI doesn't know if a "CSE231" email matters to you.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/profile")
async def get_profile():
    """
    Get the current student's academic profile.
    
    → Implemented in Phase 5
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Profile not yet implemented — coming in Phase 5"},
    )


@router.put("/profile")
async def update_profile():
    """
    Update the student's academic profile.
    
    Accepts: university, major, semester, courses, interests.
    This data is sent to Gemini along with emails for context.
    
    → Implemented in Phase 5
    """
    return JSONResponse(
        status_code=501,
        content={"detail": "Profile update not yet implemented — coming in Phase 5"},
    )
