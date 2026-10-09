# UniPulse

**An AI-powered university assistant for academic email and student workflows.**

UniPulse is a full-stack web application built to help students manage academic communication using Gmail integration and AI-powered email analysis.

## Features

- Gmail integration through Google APIs
- AI-powered email analysis using Google Gemini
- React-based dashboard
- Backend authentication and profile management
- Local database support using SQLite

## Tech Stack

**Frontend**
- React
- TypeScript
- Vite
- CSS

**Backend**
- Python
- FastAPI
- SQLAlchemy
- SQLite and aiosqlite
- Google OAuth and Gmail API
- Google Gemini API

## Project Structure

- `backend/` — FastAPI backend, authentication, Gmail integration, and AI analysis
- `frontend/` — React and TypeScript frontend
- `requirements.txt` — Python dependencies
- `.env.example` — Environment configuration template

## Run Locally

### Prerequisites

- Python
- Node.js and npm
- Google OAuth and Gmail API configuration
- Gemini API key

### 1. Clone the repository

```bash
git clone https://github.com/LabibCraftsSpells/UniPulse.git
cd UniPulse
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Configure the required values in your local `.env` file. Never commit real API keys, passwords, OAuth secrets, or tokens.

### 3. Install backend dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Start the backend

From the project root:

```bash
uvicorn backend.main:app --reload
```

If enabled, the FastAPI documentation is available at `http://127.0.0.1:8000/docs`.

### 5. Start the frontend

Open a second Terminal window:

```bash
cd UniPulse/frontend
npm install
npm run dev
```

Open the local URL displayed by Vite.

## Project Status

UniPulse has been run locally during development. Further configuration may be required to run it on another machine or deploy it publicly.

## Author

**LabibCraftsSpells**

GitHub: https://github.com/LabibCraftsSpells