"""
Student Mail Copilot — Main Application Entry Point.

This is where everything comes together. FastAPI starts here.

KEY CONCEPT: How a Web Server Works
--------------------------------------
When you run this app, it starts a web server on port 8000.
The server listens for HTTP requests and routes them to the
appropriate handler function based on the URL path.

    Browser visits localhost:8000/auth/google
         ↓
    FastAPI matches the path to auth router
         ↓
    Calls google_login() function
         ↓
    Returns the response to the browser

KEY CONCEPT: CORS (Cross-Origin Resource Sharing)
---------------------------------------------------
Your frontend runs on localhost:5173 and your backend on localhost:8000.
By default, browsers block requests between different origins (ports).
CORS middleware tells the browser: "requests from localhost:5173 are OK."

Without CORS, your frontend would get errors when trying to call the API.

KEY CONCEPT: Routers
----------------------
Instead of defining all endpoints in this file, we split them into
"routers" — separate files grouped by feature (auth, emails, profile).
This keeps the code organized as the app grows.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db

# Import routers — each handles a group of related endpoints
from backend.auth.router import router as auth_router
from backend.auth.profile_router import router as profile_router
from backend.gmail.router import router as gmail_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on app startup and shutdown.
    
    KEY CONCEPT: Lifespan Events
    ------------------------------
    Some things need to happen once when the server starts
    (like creating database tables) and once when it stops
    (like closing connections). This function handles both.
    
    The "yield" splits startup (before) from shutdown (after).
    """
    # --- STARTUP ---
    print("🚀 Starting Student Mail Copilot...")
    await init_db()  # Create database tables if they don't exist
    print("✅ Database initialized")
    print(f"📧 Frontend URL: {settings.FRONTEND_URL}")
    print(f"🔗 Backend URL: {settings.BACKEND_URL}")
    print(f"📖 API docs: {settings.BACKEND_URL}/docs")

    yield  # App is running, handle requests

    # --- SHUTDOWN ---
    print("👋 Shutting down Student Mail Copilot...")


from starlette.middleware.sessions import SessionMiddleware

# Create the FastAPI application
app = FastAPI(
    title="Student Mail Copilot",
    description="AI-powered university email analysis for students",
    version="0.1.0",
    lifespan=lifespan,
)

# --- Session Middleware ---
# This creates a secure, encrypted cookie in the user's browser to remember who is logged in.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.APP_SECRET_KEY,
    max_age=14 * 24 * 60 * 60,  # Session lasts for 14 days
    same_site="lax",            # Required for OAuth redirects to work correctly
)

# --- CORS Middleware ---
# Allow the frontend (localhost:5173) to make API calls to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,  # React dev server
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,      # Allow cookies (needed for sessions)
    allow_methods=["*"],         # Allow all HTTP methods
    allow_headers=["*"],         # Allow all headers
)

# --- Register Routers ---
# Each router adds its endpoints to the app
app.include_router(auth_router)       # /auth/*
app.include_router(gmail_router)      # /api/emails, /api/dashboard
app.include_router(profile_router)    # /api/profile


# --- Health Check ---
@app.get("/", tags=["health"])
async def root():
    """
    Simple health check endpoint.
    
    Visit http://localhost:8000/ to verify the server is running.
    Also useful for monitoring tools.
    """
    return {
        "app": "Student Mail Copilot",
        "status": "running",
        "version": "0.1.0",
        "docs": f"{settings.BACKEND_URL}/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Lightweight health check for monitoring."""
    return {"status": "ok"}
