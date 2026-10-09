"""
Authentication router — handles Google OAuth flow.
"""

import os
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google_auth_oauthlib.flow import Flow

from backend.config import settings
from backend.database import get_db
from backend.models import User
from backend.schemas import UserResponse
from backend.auth.crypto import encrypt_token, decrypt_token
from backend.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

def get_google_flow() -> Flow:
    """Helper to initialize the Google OAuth Flow using our config."""
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=settings.GOOGLE_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )


@router.get("/google")
async def google_login(request: Request):
    """
    Step 1: Redirect user to Google's OAuth consent screen.
    """
    flow = get_google_flow()
    
    # Generate the Google login URL
    # prompt='consent' forces Google to show the consent screen so we get a refresh token
    # access_type='offline' means we want a refresh token to access APIs while the user is offline
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    # Store 'state' in session to prevent CSRF attacks
    request.session['oauth_state'] = state
    
    # Send the user to Google
    return RedirectResponse(url=authorization_url)


@router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Step 2: Handle Google's redirect after user approves.
    """
    # Verify the state matches what we stored to prevent CSRF attacks
    state = request.session.get('oauth_state')
    if not state or state != request.query_params.get('state'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state parameter")
    
    # Allow insecure transport for local development (http://localhost)
    if "localhost" in settings.GOOGLE_REDIRECT_URI:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        
    # Prevent oauthlib from crashing with a 500 error if Google returns fewer scopes than requested
    # (e.g., if the user unchecked the Gmail permission box)
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
        
    flow = get_google_flow()
    
    # Exchange the code from the URL for actual tokens
    authorization_response = str(request.url)
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    
    # Verify the user actually granted the Gmail read scope.
    # Google makes sensitive scopes optional checkboxes on the consent screen.
    granted_scopes = credentials.scopes if credentials.scopes else []
    gmail_readonly_scope = "https://www.googleapis.com/auth/gmail.readonly"
    
    if gmail_readonly_scope not in granted_scopes:
        # The user logged in, but refused to grant Gmail read access.
        # We cannot proceed.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Gmail read permission is required. Please reconnect and ensure you check the box granting Gmail access."
        )
    
    # Fetch the user's profile info from Google using the new access token
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {credentials.token}"}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch user info")
        user_info = response.json()
        
    user_id = user_info["id"]
    email = user_info["email"]
    name = user_info.get("name")
    picture = user_info.get("picture")
    
    # Check if this user is already in our database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        # First time login, create the user
        user = User(id=user_id, email=email)
        db.add(user)
        
    # Update latest profile info and encrypted tokens
    user.name = name
    user.picture = picture
    user.access_token = encrypt_token(credentials.token)
    
    # We only get a refresh token on the first authorization (or if prompt='consent')
    if credentials.refresh_token:
        user.refresh_token = encrypt_token(credentials.refresh_token)
        
    if credentials.expiry:
        user.token_expiry = credentials.expiry.replace(tzinfo=timezone.utc)
        
    await db.commit()
    
    # Log the user into our app by setting their ID in our session cookie
    request.session["user_id"] = user.id
    
    # Send them to the dashboard
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/dashboard")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: User = Depends(get_current_user)):
    """
    Returns the currently authenticated user's info.
    Protected by get_current_user dependency.
    """
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        picture=user.picture,
        has_profile=False # We will update this in Phase 5
    )


@router.post("/disconnect")
async def disconnect(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Revoke Google access and log out.
    """
    user_id = request.session.get("user_id")
    if user_id:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if user and user.access_token:
            # Tell Google we no longer want access to this user's data
            async with httpx.AsyncClient() as client:
                await client.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": decrypt_token(user.access_token)}
                )
            
            # Remove tokens from our database
            user.access_token = None
            user.refresh_token = None
            await db.commit()
            
    # Clear our session cookie
    request.session.clear()
    
    return {"status": "success", "message": "Disconnected and logged out."}
