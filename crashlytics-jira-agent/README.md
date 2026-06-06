# Crashlytics Jira Agent

Automatically reads crash issues from Firebase Crashlytics, creates Jira Bug tickets for new crashes, and stores processed crashes in PostgreSQL to prevent duplicates.

## Architecture

```text
Firebase Crashlytics
        |
        v
Crash Reader Service
        |
        v
Duplicate Checker
        |
        v
Jira Ticket Creator
        |
        v
PostgreSQL Database
```

## Tech Stack

- Python 3.12+
- FastAPI
- PostgreSQL
- SQLAlchemy
- Firebase Admin SDK
- Jira REST API
- APScheduler
- Pydantic
- Python-dotenv

## Project Structure

```text
crashlytics-jira-agent/
├── app/
│   ├── firebase/
│   │   ├── config.py
│   │   └── crashlytics_client.py
│   ├── jira/
│   │   └── jira_client.py
│   ├── database/
│   │   ├── models.py
│   │   ├── session.py
│   │   └── base.py
│   ├── services/
│   │   ├── crash_service.py
│   │   └── jira_service.py
│   ├── scheduler/
│   │   └── scheduler.py
│   └── main.py
├── config/
│   └── google-services.json
├── requirements.txt
├── .env
├── service-account.json
└── README.md
```

## Firebase Project (one-nest)

This project is configured for the **one-nest** Firebase project with two Android apps:

| Package Name | Firebase App Id |
|---|---|
| `com.infimatrix.bhre.one_nest` | `1:693284173557:android:bdb2c2c6c3adc6a71f37bc` |
| `com.infimatrix.one_nest` | `1:693284173557:android:fb43cbfb53ad7ed11f37bc` |

Credential files (not committed to git):

- `service-account.json` — Firebase Admin SDK service account
- `config/google-services.json` — Android Firebase config

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Copy and update `.env` with your credentials:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost/crash_agent
JIRA_URL=https://your-company.atlassian.net
JIRA_EMAIL=admin@company.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECT_KEY=BUG

FIREBASE_PROJECT_ID=one-nest
FIREBASE_PROJECT_NUMBER=693284173557
FIREBASE_SERVICE_ACCOUNT_PATH=service-account.json
FIREBASE_GOOGLE_SERVICES_PATH=config/google-services.json
```

Place your Firebase credentials at:

- `service-account.json` — Admin SDK key (already configured for one-nest)
- `config/google-services.json` — Android app config (already configured)

## Running

```bash
uvicorn app.main:app --reload
```

Health check: `GET http://localhost:8000/health`

The scheduler runs `process_crashes` every 5 minutes automatically.

## How It Works

1. Reads crashes from Firebase Crashlytics (mock data used when credentials are missing).
2. Checks PostgreSQL for existing `ProcessedCrash` records by `issue_id`.
3. Creates a Jira Bug ticket for new crashes.
4. Stores the Crashlytics-to-Jira mapping in the database.
5. Skips duplicates and continues processing on individual failures.

## Success Criteria

- New Crashlytics issues are detected automatically.
- Jira Bug tickets are created for new crashes.
- Duplicate tickets are prevented via database persistence.
- Scheduler runs every 5 minutes.
- Structured logs maintain traceability.
