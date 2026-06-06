# Firebase Crashlytics → Jira Ticket Automation

## Overview

This project automatically:

1. Reads crash issues from Firebase Crashlytics.
2. Checks whether a Jira ticket already exists for the crash.
3. Creates a Jira Bug ticket for new crashes.
4. Stores processed crashes in a database to avoid duplicate tickets.
5. Runs continuously on a schedule.

---

# Architecture

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

---

# Tech Stack

* Python 3.12+
* FastAPI
* PostgreSQL
* SQLAlchemy
* Firebase Admin SDK
* Jira REST API
* APScheduler
* Pydantic
* Python-dotenv

---

# Project Structure

```text
crashlytics-jira-agent/

├── app/
│   ├── firebase/
│   │   └── crashlytics_client.py
│   │
│   ├── jira/
│   │   └── jira_client.py
│   │
│   ├── database/
│   │   ├── models.py
│   │   ├── session.py
│   │   └── base.py
│   │
│   ├── services/
│   │   ├── crash_service.py
│   │   └── jira_service.py
│   │
│   ├── scheduler/
│   │   └── scheduler.py
│   │
│   └── main.py
│
├── requirements.txt
├── .env
├── service-account.json
└── README.md
```

---

# Environment Variables

Create a `.env` file.

```env
DATABASE_URL=postgresql://postgres:postgres@localhost/crash_agent

JIRA_URL=https://your-company.atlassian.net

JIRA_EMAIL=admin@company.com

JIRA_API_TOKEN=your-jira-api-token

JIRA_PROJECT_KEY=BUG
```

---

# Installation

```bash
python -m venv venv

source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# Requirements

```txt
fastapi
uvicorn
python-dotenv
jira
sqlalchemy
psycopg2-binary
firebase-admin
apscheduler
pydantic
```

---

# Database Model

## Processed Crash Table

```python
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class ProcessedCrash(Base):
    __tablename__ = "processed_crashes"

    issue_id = Column(String, primary_key=True)

    jira_ticket = Column(String)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
```

Purpose:

* Prevent duplicate Jira tickets.
* Maintain mapping between Crashlytics issue and Jira issue.

---

# Firebase Client

File:

```text
app/firebase/crashlytics_client.py
```

Example structure:

```python
class CrashlyticsClient:

    def get_crashes(self):

        crashes = [
            {
                "issue_id": "crash_101",
                "title": "NullPointerException",
                "affected_users": 20,
                "app_version": "1.0.0"
            }
        ]

        return crashes
```

Note:

Actual implementation should connect to Firebase Crashlytics APIs and retrieve issue data.

Return format should remain consistent.

---

# Jira Client

File:

```text
app/jira/jira_client.py
```

```python
from jira import JIRA
from os import getenv

class JiraClient:

    def __init__(self):

        self.client = JIRA(
            server=getenv("JIRA_URL"),
            basic_auth=(
                getenv("JIRA_EMAIL"),
                getenv("JIRA_API_TOKEN")
            )
        )

    def create_bug(
        self,
        summary,
        description
    ):

        issue = self.client.create_issue(
            project=getenv("JIRA_PROJECT_KEY"),
            summary=summary,
            description=description,
            issuetype={"name": "Bug"}
        )

        return issue.key
```

---

# Jira Service

File:

```text
app/services/jira_service.py
```

```python
from app.jira.jira_client import JiraClient

jira_client = JiraClient()

def create_ticket(crash):

    summary = (
        f"[Crashlytics] "
        f"{crash['title']}"
    )

    description = f"""
Issue Id: {crash['issue_id']}

Affected Users:
{crash['affected_users']}

App Version:
{crash['app_version']}
"""

    return jira_client.create_bug(
        summary,
        description
    )
```

---

# Crash Processing Service

File:

```text
app/services/crash_service.py
```

```python
from app.firebase.crashlytics_client import CrashlyticsClient

firebase_client = CrashlyticsClient()

def get_new_crashes():

    crashes = firebase_client.get_crashes()

    return crashes
```

---

# Duplicate Detection

Before creating Jira tickets:

```python
existing = session.get(
    ProcessedCrash,
    issue_id
)

if existing:
    return
```

If record exists:

```text
Skip Jira creation
```

Otherwise:

```text
Create Jira ticket
Store mapping
```

---

# Main Processing Logic

```python
def process_crashes():

    crashes = firebase_client.get_crashes()

    for crash in crashes:

        exists = session.get(
            ProcessedCrash,
            crash["issue_id"]
        )

        if exists:
            continue

        jira_key = create_ticket(
            crash
        )

        processed = ProcessedCrash(
            issue_id=crash["issue_id"],
            jira_ticket=jira_key
        )

        session.add(processed)

    session.commit()
```

---

# Scheduler

File:

```text
app/scheduler/scheduler.py
```

```python
from apscheduler.schedulers.background import (
    BackgroundScheduler
)

scheduler = BackgroundScheduler()

scheduler.add_job(
    process_crashes,
    "interval",
    minutes=5
)

scheduler.start()
```

---

# FastAPI Entry Point

File:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():

    return {
        "status": "running"
    }
```

Run:

```bash
uvicorn app.main:app --reload
```

---

# Logging Standard

Create structured logs.

```python
import logging

logger = logging.getLogger(
    "crash-agent"
)

logger.info(
    "jira ticket created"
)
```

Log:

* Crash detected
* Jira ticket created
* Duplicate skipped
* API failures

---

# Error Handling

Always wrap integrations.

```python
try:

    jira_key = create_ticket(
        crash
    )

except Exception as ex:

    logger.exception(ex)
```

Never stop processing because one ticket fails.

Continue with the next crash.

---

# Production Best Practices

## Do Not

❌ Hardcode credentials

❌ Create duplicate Jira tickets

❌ Store secrets in Git

❌ Use print statements

---

## Do

✅ Use environment variables

✅ Use structured logging

✅ Add retries

✅ Add monitoring

✅ Add database persistence

✅ Add Docker support

✅ Add unit tests

---

# Future Enhancements

## Phase 2

AI Root Cause Analysis

```text
Crash
   |
   v
OpenAI Analysis
   |
   v
Root Cause
```

---

## Phase 3

Automatic Jira Assignment

```text
Crash File
     |
     v
Git History
     |
     v
Assign Developer
```

---

## Phase 4

Automatic Branch Creation

```text
BUG-123
    |
    v
bugfix/BUG-123-login-crash
```

---

## Phase 5

Automatic Pull Request

```text
Crash
  |
  v
AI Fix
  |
  v
PR Creation
```

---

# Success Criteria

The MVP is successful when:

1. A new Crashlytics issue appears.
2. Python service detects it.
3. Jira Bug ticket is created.
4. Duplicate tickets are prevented.
5. System runs automatically every 5 minutes.
6. Logs and database maintain traceability.

```
```
