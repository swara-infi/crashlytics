"""
gemini_autofix.py
─────────────────
Called by the GitHub Actions workflow. It:
  1. Reads the repo diff (base branch vs. current bugfix branch)
  2. Sends the Jira ticket + diff to Gemini and asks for a fix
  3. Commits the patched files back to the bugfix branch
  4. Opens a Pull Request with the AI-generated fix
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import google.generativeai as genai
from github import Github

# ── Config from environment ──────────────────────────────────────────────────
GEMINI_API_KEY     = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL       = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GITHUB_TOKEN       = os.environ["GITHUB_TOKEN"]
REPO_NAME          = os.environ["REPO"]               # owner/repo
BASE_BRANCH        = os.environ["BASE_BRANCH"]         # main / master
HEAD_BRANCH        = os.environ["HEAD_BRANCH"]         # bugfix/PROJ-123
TICKET_ID          = os.environ["TICKET_ID"]
JIRA_BASE_URL      = os.environ.get("JIRA_BASE_URL", "")
TICKET_SUMMARY     = os.environ.get("TICKET_SUMMARY", "")
TICKET_DESCRIPTION = os.environ.get("TICKET_DESCRIPTION", "")

MAX_DIFF_CHARS = int(os.environ.get("GEMINI_MAX_DIFF_CHARS", "80000"))


# ── Helpers ──────────────────────────────────────────────────────────────────

def run(cmd: str, **kwargs) -> str:
    """Run a shell command and return stdout."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(f"[ERROR] Command failed: {cmd}\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def get_diff() -> str:
    """Return the unified diff between the base branch and HEAD."""
    run(f"git fetch origin {BASE_BRANCH} --depth=1")
    diff = run(f"git diff origin/{BASE_BRANCH}...HEAD")
    if not diff:
        # Branch was just created with no commits — diff the full tree instead
        diff = run("git show HEAD --stat")
    return diff[:MAX_DIFF_CHARS]


def get_changed_files() -> list[str]:
    """Return list of files changed relative to base branch."""
    out = run(f"git diff --name-only origin/{BASE_BRANCH}...HEAD")
    return [f for f in out.splitlines() if f and Path(f).exists()]


def read_file_contents(files: list[str]) -> str:
    """Return concatenated file contents for context."""
    parts: list[str] = []
    for path in files[:20]:  # cap to 20 files
        try:
            content = Path(path).read_text(errors="replace")
            parts.append(f"### File: {path}\n```\n{content[:8000]}\n```")
        except Exception:
            pass
    return "\n\n".join(parts)


def build_prompt(diff: str, file_contents: str) -> str:
    jira_link = f"{JIRA_BASE_URL.rstrip('/')}/browse/{TICKET_ID}" if JIRA_BASE_URL else TICKET_ID
    return textwrap.dedent(f"""
        You are an expert software engineer performing a bugfix.

        ## Jira Ticket
        - **ID**: [{TICKET_ID}]({jira_link})
        - **Summary**: {TICKET_SUMMARY}
        - **Description**:
        {textwrap.indent(TICKET_DESCRIPTION, "  ")}

        ## Current diff (branch `{HEAD_BRANCH}` vs `{BASE_BRANCH}`)
        ```diff
        {diff}
        ```

        ## Full content of changed files
        {file_contents}

        ## Task
        Analyse the ticket description and the current state of the code, then produce
        the minimal, correct fix for the reported bug.

        Respond with **only** a JSON object in this exact schema — no markdown fences,
        no prose outside the JSON:

        {{
          "pr_title": "<concise PR title>",
          "pr_body": "<markdown PR description explaining what was changed and why>",
          "changed_files": [
            {{
              "path": "<relative file path>",
              "content": "<complete new file content — not a diff>"
            }}
          ]
        }}

        Rules:
        - Only include files that actually need to change.
        - Preserve existing code style, indentation, and formatting.
        - Do not add unrelated refactors or comments.
        - If no code change is needed, return an empty `changed_files` array and
          explain in `pr_body`.
    """).strip()


def call_gemini(prompt: str) -> dict:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()

    return json.loads(raw)


def commit_and_push(changed_files: list[dict]) -> bool:
    """Write files, commit, and push. Returns True if anything was committed."""
    if not changed_files:
        print("Gemini returned no file changes.")
        return False

    for entry in changed_files:
        path = Path(entry["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(entry["content"])
        print(f"  ✏️  Written: {path}")

    run("git config user.name  'github-actions[bot]'")
    run("git config user.email 'github-actions[bot]@users.noreply.github.com'")
    run("git add -A")

    status = subprocess.run("git diff --cached --quiet", shell=True).returncode
    if status == 0:
        print("Nothing to commit — working tree clean after applying fix.")
        return False

    run(f'git commit -m "fix({TICKET_ID}): apply Gemini-generated bugfix"')
    run(f"git push origin HEAD:{HEAD_BRANCH}")
    print(f"✅ Pushed fix to {HEAD_BRANCH}")
    return True


def open_pull_request(pr_title: str, pr_body: str) -> None:
    gh   = Github(GITHUB_TOKEN)
    repo = gh.get_repo(REPO_NAME)

    # Check if a PR already exists for this branch
    existing = list(repo.get_pulls(state="open", head=f"{repo.owner.login}:{HEAD_BRANCH}"))
    if existing:
        pr = existing[0]
        pr.edit(title=pr_title, body=pr_body)
        print(f"✅ Updated existing PR #{pr.number}: {pr.html_url}")
        return

    pr = repo.create_pull(
        title=pr_title,
        body=pr_body,
        head=HEAD_BRANCH,
        base=BASE_BRANCH,
    )
    print(f"✅ Opened PR #{pr.number}: {pr.html_url}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{'='*60}")
    print(f"🎫 Ticket  : {TICKET_ID}")
    print(f"📋 Summary : {TICKET_SUMMARY}")
    print(f"🌿 Branch  : {HEAD_BRANCH}  →  {BASE_BRANCH}")
    print(f"{'='*60}\n")

    diff          = get_diff()
    changed_files = get_changed_files()
    file_contents = read_file_contents(changed_files)

    print("🤖 Calling Gemini…")
    prompt  = build_prompt(diff, file_contents)
    result  = call_gemini(prompt)

    pr_title = result.get("pr_title", f"fix({TICKET_ID}): Gemini-generated bugfix")
    pr_body  = result.get("pr_body",  "Automated fix generated by Gemini.")
    files    = result.get("changed_files", [])

    print(f"\n📝 PR title  : {pr_title}")
    print(f"📂 Files to change: {[f['path'] for f in files]}\n")

    committed = commit_and_push(files)

    if committed or not files:
        open_pull_request(pr_title, pr_body)
    else:
        print("No changes committed — skipping PR creation.")


if __name__ == "__main__":
    main()
