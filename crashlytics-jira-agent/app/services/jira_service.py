import logging

from app.firebase.crash_utils import format_stack_trace, get_exception, get_issue_id
from app.jira.jira_client import JiraClient

logger = logging.getLogger("crash-agent")
_jira_client: JiraClient | None = None


def _get_jira_client() -> JiraClient:
    global _jira_client
    if _jira_client is None:
        _jira_client = JiraClient()
    return _jira_client


def create_ticket(crash: dict) -> str:
    exception = get_exception(crash)
    summary = f"[Crashlytics] {exception}"
    issue_id = get_issue_id(crash)
    message = crash.get("message", "N/A")
    file_name = crash.get("file", "N/A")
    line_number = crash.get("line", "N/A")
    package_name = crash.get("package_name", "N/A")
    app_id = crash.get("app_id", "N/A")
    app_version = crash.get("app_version", "N/A")
    affected_users = crash.get("affected_users", "N/A")
    stack_trace = format_stack_trace(crash)
    description = f"""
Issue Id: {issue_id}

Exception:
{exception}

Message:
{message}

File:
{file_name}

Line:
{line_number}

Stack Trace:
{stack_trace}

Affected Users:
{affected_users}

App Version:
{app_version}

Package Name:
{package_name}

Firebase App Id:
{app_id}
"""
    return _get_jira_client().create_bug(summary, description)
