# UniPulse 🎓📬

**An AI-powered academic email assistant that helps students prioritize important university emails, summarize messages, and stay on top of academic tasks.**

UniPulse is a student-focused email productivity tool designed to reduce the effort of managing university emails. It fetches academic emails, organizes them by priority, and uses AI to generate concise summaries so students can focus on what matters most.

## 📸 Screenshots

### Dashboard
![UniPulse Dashboard](screenshots/dashboard.png)

### Fetched Emails
![UniPulse Fetched Emails](screenshots/fetched-emails.png)

### High-Priority Emails
Quickly identify important academic emails that deserve attention first.

![UniPulse High-Priority Emails](screenshots/high-priority.png)

## ✨ Features

- **📥 Academic Email Fetching** — Retrieve and view university emails in one place.
- **🚦 Priority-Based Organization** — Identify high-priority emails and focus on important academic updates.
- **🤖 AI-Powered Summarization** — Turn lengthy emails into concise, easier-to-understand summaries.
- **🎯 Student-Focused Workflow** — Designed around the needs of university students.
- **🖥️ Web-Based Interface** — Access email information through a dedicated dashboard.
- **🔌 API Integration** — Backend API endpoints connect the frontend with the application's email and processing functionality.

*Features depend on the current implementation and the services configured in your environment.*

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI
- **Frontend:** Web-based interface
- **Database:** SQLite
- **AI Integration:** LLM API
- **Development Tools:** Git, GitHub, VS Code

## ⚙️ How It Works

1. **Fetch emails** from the configured email source.
2. **Process the messages** through the backend.
3. **Prioritize emails** to help surface important academic information.
4. **Generate summaries** using the configured AI service.
5. **Review everything** through the UniPulse dashboard.

## 🚀 Getting Started

### Prerequisites

Make sure you have the following installed:

- Python 3.10 or a compatible version
- Node.js and npm, if required by the frontend
- Git
- API credentials for any external services you configure

### 1. Clone the repository

```bash
git clone https://github.com/LabibCraftsSpells/UniPulse.git
cd UniPulse
```

### 2. Set up the Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the backend dependencies:

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create your local environment file using the example file:

```bash
cp .env.example .env
```

Open `.env` and configure the required variables for your email provider and AI service.

**Important:** Use your own credentials. Never commit `.env` or expose API keys, passwords, or email tokens in the repository.

### 4. Start the backend

From the project root, activate the virtual environment if it is not already active, then run:

```bash
uvicorn backend.main:app --reload
```

The backend should be available at:

- **API:** http://127.0.0.1:8000
- **API documentation:** http://127.0.0.1:8000/docs

### 5. Start the frontend

Run the frontend using the commands and package manager specified by its `package.json`. For a typical npm-based frontend:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed in your terminal, commonly:

http://localhost:5173

*If your project uses a different frontend directory or start command, follow the configuration in that directory.*

## 📁 Project Structure

```text
UniPulse/
├── backend/          # Backend application and API
├── frontend/         # User interface
├── screenshots/      # Project screenshots
├── .env.example      # Example environment configuration
├── .gitignore        # Files excluded from Git
├── README.md         # Project documentation
└── requirements.txt  # Python dependencies
```

*The structure above highlights the main project components; individual files may vary.*

## 🔐 Security & Privacy

- Store credentials and API keys in your local `.env` file.
- Keep `.env`, local databases, and other sensitive files out of version control.
- Use `.env.example` only for placeholder values and configuration guidance.
- Review email-provider permissions before connecting an account.
- Avoid using real personal or university emails in public demos or screenshots.

UniPulse is a personal development project. Review its configuration and security practices before using it with sensitive email accounts.

## 🗺️ Future Improvements

- [ ] Improve email priority classification.
- [ ] Add filters for categories such as assignments, exams, announcements, and deadlines.
- [ ] Improve AI-generated summaries and action-item extraction.
- [ ] Add deadline and task reminders.
- [ ] Improve loading states, error handling, and overall user experience.
- [ ] Add automated tests and more comprehensive documentation.

## 🎯 Project Goal

The goal of UniPulse is to make university email management less overwhelming by helping students quickly understand their messages and identify what needs attention.

## 👨‍💻 Author

**LabibCraftsSpells**

GitHub: [@LabibCraftsSpells](https://github.com/LabibCraftsSpells)

---

*Built as a student project exploring AI-powered productivity tools, backend development, and practical application building.*
