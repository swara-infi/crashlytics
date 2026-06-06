import logging

from app.database.models import ProcessedCrash
from app.database.session import get_session
from app.firebase.crash_utils import get_exception, get_issue_id
from app.firebase.crashlytics_client import CrashlyticsClient
from app.services.jira_service import create_ticket

logger = logging.getLogger("crash-agent")
firebase_client = CrashlyticsClient()


def get_new_crashes() -> list[dict]:
    crashes = firebase_client.get_crashes()
    return crashes


def process_crashes() -> None:
    crashes = firebase_client.get_crashes()
    session = get_session()
    try:
        for crash in crashes:
            issue_id = get_issue_id(crash)
            existing = session.get(ProcessedCrash, issue_id)
            if existing:
                logger.info(
                    "Duplicate skipped for issue_id=%s, jira_ticket=%s",
                    issue_id,
                    existing.jira_ticket,
                )
                continue
            logger.info(
                "Crash detected: issue_id=%s, exception=%s",
                issue_id,
                get_exception(crash),
            )
            try:
                jira_key = create_ticket(crash)
            except Exception as ex:
                logger.exception("Failed to create Jira ticket for %s: %s", issue_id, ex)
                continue
            processed = ProcessedCrash(
                issue_id=issue_id,
                jira_ticket=jira_key,
            )
            session.add(processed)
            logger.info(
                "Jira ticket created: issue_id=%s, jira_ticket=%s",
                issue_id,
                jira_key,
            )
        session.commit()
    except Exception as ex:
        session.rollback()
        logger.exception("Error processing crashes: %s", ex)
    finally:
        session.close()
