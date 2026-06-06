from typing import Any


def get_issue_id(crash: dict[str, Any]) -> str:
    return crash.get("issueId") or crash.get("issue_id", "")


def get_exception(crash: dict[str, Any]) -> str:
    return crash.get("exception") or crash.get("title", "Unknown crash")


def format_stack_trace(crash: dict[str, Any]) -> str:
    stack_trace = crash.get("stackTrace", [])
    if not stack_trace:
        return "N/A"
    return "\n".join(f"  - {frame}" for frame in stack_trace)
