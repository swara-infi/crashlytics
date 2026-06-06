from datetime import datetime

from sqlalchemy import Column, DateTime, String

from app.database.base import Base


class ProcessedCrash(Base):
    __tablename__ = "processed_crashes"

    issue_id = Column(String, primary_key=True)
    jira_ticket = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
