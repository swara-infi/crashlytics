import logging
import os

from jira import JIRA

logger = logging.getLogger("crash-agent")


def _get_jira_server_url() -> str:
    jira_url = os.getenv("JIRA_URL", "").strip().rstrip("/")
    if not jira_url:
        raise ValueError("JIRA_URL environment variable is not set")
    if "/jira/" in jira_url:
        jira_url = jira_url.split("/jira/")[0]
    return jira_url


class JiraClient:
    def __init__(self) -> None:
        jira_email = os.getenv("JIRA_EMAIL")
        jira_api_token = os.getenv("JIRA_API_TOKEN")
        jira_project_key = os.getenv("JIRA_PROJECT_KEY")
        if not jira_email or not jira_api_token or not jira_project_key:
            raise ValueError(
                "JIRA_EMAIL, JIRA_API_TOKEN, and JIRA_PROJECT_KEY must be set"
            )
        self.project_key = jira_project_key
        self.client = JIRA(
            server=_get_jira_server_url(),
            basic_auth=(jira_email, jira_api_token),
        )
        logger.info("Jira client initialized for project=%s", self.project_key)

    def create_bug(self, summary: str, description: str) -> str:
        issue = self.client.create_issue(
            project=self.project_key,
            summary=summary,
            description=description,
            issuetype={"name": "Bug"},
        )
        logger.info("Jira ticket created: %s", issue.key)
        return issue.key
