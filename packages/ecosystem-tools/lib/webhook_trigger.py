#!/usr/bin/env python3
# SCOPE: both
# scope: both
"""
GitHub Webhook Trigger Server for Cognitive OS SDD Pipeline.

Receives GitHub webhook events (issues.opened, issues.labeled, issue_comment.created),
detects trigger keywords, classifies issues, and launches the SDD pipeline in
background via ClaudeExecutor.

Posts status comments on the GitHub issue via `gh` CLI.

Python 3.9+ compatible.
"""

import hashlib
import hmac
import json
import logging
import os
import subprocess
import threading
import time
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from fastapi import FastAPI as _FastAPI
    from fastapi import HTTPException as _HTTPException
    from fastapi import Request as _Request
    from fastapi import Response as _Response
    import uvicorn as _uvicorn
    FastAPI: Any = _FastAPI
    HTTPException: Any = _HTTPException
    Request: Any = _Request
    Response: Any = _Response
    uvicorn: Any = _uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "webhook_trigger: fastapi/uvicorn not installed. "
        "Server cannot start. Install with: pip install fastapi uvicorn"
    )
    FASTAPI_AVAILABLE = False
    FastAPI = None
    HTTPException = None
    Request = None
    Response = None
    uvicorn = None

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
from lib.claude_executor import ClaudeExecutor, ClaudeResult

logger = logging.getLogger("webhook_trigger")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
PROJECT_DIR = os.getenv("WEBHOOK_PROJECT_DIR", os.getcwd())
PORT = int(os.getenv("WEBHOOK_PORT", "8001"))
CLAUDE_BIN = os.getenv("CLAUDE_BIN", "claude")
CLAUDE_TIMEOUT = int(os.getenv("CLAUDE_TIMEOUT", "900"))

BOT_IDENTIFIER = "<!-- luum-bot -->"

# Trigger keywords detected in issue body or comments
TRIGGER_KEYWORDS: List[str] = ["[sdd-auto]", "[ai-workflow]", "@luum-bot"]

# ---------------------------------------------------------------------------
# Issue classification
# ---------------------------------------------------------------------------


class IssueClass(str, Enum):
    FEATURE = "feature"
    BUG = "bug"
    CHORE = "chore"


# Label text -> classification mapping (case-insensitive)
_LABEL_MAP: Dict[str, IssueClass] = {
    "bug": IssueClass.BUG,
    "fix": IssueClass.BUG,
    "hotfix": IssueClass.BUG,
    "feature": IssueClass.FEATURE,
    "enhancement": IssueClass.FEATURE,
    "feat": IssueClass.FEATURE,
    "chore": IssueClass.CHORE,
    "maintenance": IssueClass.CHORE,
    "refactor": IssueClass.CHORE,
    "docs": IssueClass.CHORE,
    "ci": IssueClass.CHORE,
}


def classify_issue(
    labels: List[str],
    title: str,
    body: str,
) -> IssueClass:
    """Classify an issue based on labels, then title/body heuristics.

    Priority:
      1. Explicit label match (bug, feature, chore, etc.)
      2. /classify_issue pattern in body (e.g. ``/classify_issue feature``)
      3. Title keyword heuristics
      4. Default to feature
    """
    # 1. Label-based
    for label_text in labels:
        normalized = label_text.lower().strip()
        if normalized in _LABEL_MAP:
            return _LABEL_MAP[normalized]

    # 2. /classify_issue command in body
    for line in body.splitlines():
        stripped = line.strip().lower()
        if stripped.startswith("/classify_issue"):
            parts = stripped.split(maxsplit=1)
            if len(parts) == 2:
                candidate = parts[1].strip()
                for member in IssueClass:
                    if candidate == member.value:
                        return member

    # 3. Title heuristics
    title_lower = title.lower()
    if any(kw in title_lower for kw in ("bug", "fix", "error", "crash", "broken")):
        return IssueClass.BUG
    if any(kw in title_lower for kw in ("chore", "refactor", "cleanup", "ci", "docs")):
        return IssueClass.CHORE

    # 4. Default
    return IssueClass.FEATURE


# ---------------------------------------------------------------------------
# Trigger detection
# ---------------------------------------------------------------------------


def _has_trigger(text: str) -> bool:
    """Return True if *text* contains any trigger keyword."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in TRIGGER_KEYWORDS)


def _is_bot_comment(text: str) -> bool:
    """Return True if the text was posted by this bot (avoid loops)."""
    return BOT_IDENTIFIER in text


# ---------------------------------------------------------------------------
# HMAC-SHA256 signature verification
# ---------------------------------------------------------------------------


def _verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature.

    Returns True if the signature is valid or if no secret is configured
    (allows running without signature validation in dev).
    """
    if not WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET not set — skipping signature validation")
        return True

    if not signature_header:
        return False

    # GitHub sends: sha256=<hex>
    if not signature_header.startswith("sha256="):
        return False

    expected_sig = signature_header[len("sha256="):]
    mac = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    )
    return hmac.compare_digest(mac.hexdigest(), expected_sig)


# ---------------------------------------------------------------------------
# GitHub comment helper (via gh CLI)
# ---------------------------------------------------------------------------


def _gh_comment(repo: str, issue_number: int, body: str) -> bool:
    """Post a comment on a GitHub issue via ``gh`` CLI.

    Returns True on success.
    """
    comment_body = f"{BOT_IDENTIFIER}\n{body}"
    env = dict(os.environ)
    if GITHUB_TOKEN:
        env["GH_TOKEN"] = GITHUB_TOKEN

    try:
        proc = subprocess.run(
            [
                "gh", "issue", "comment",
                str(issue_number),
                "--repo", repo,
                "--body", comment_body,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        if proc.returncode != 0:
            logger.warning("gh comment failed: %s", proc.stderr)
            return False
        return True
    except Exception as exc:
        logger.warning("gh comment error: %s", exc)
        return False


# ---------------------------------------------------------------------------
# SDD pipeline runner (runs in background thread)
# ---------------------------------------------------------------------------


def _make_change_name(issue_number: int, title: str) -> str:
    """Derive a kebab-case change name from the issue."""
    slug = title.lower().strip()
    # Keep only alphanumeric and spaces, then kebab-case
    slug = "".join(c if c.isalnum() or c == " " else " " for c in slug)
    slug = "-".join(slug.split())[:60]
    return f"issue-{issue_number}-{slug}" if slug else f"issue-{issue_number}"


def _run_pipeline(
    repo: str,
    issue_number: int,
    change_name: str,
    issue_class: IssueClass,
    phases: Optional[List[str]] = None,
) -> None:
    """Execute the SDD pipeline in the current thread (meant for background).

    Posts status updates as GitHub issue comments.
    """
    if phases is None:
        phases = ["explore", "propose", "spec", "design", "tasks", "apply", "verify"]

    executor = ClaudeExecutor(
        working_dir=PROJECT_DIR,
        claude_path=CLAUDE_BIN,
        default_timeout=CLAUDE_TIMEOUT,
    )

    _gh_comment(
        repo,
        issue_number,
        f"**SDD Pipeline Started**\n\n"
        f"- Change: `{change_name}`\n"
        f"- Classification: `{issue_class.value}`\n"
        f"- Phases: {', '.join(phases)}\n\n"
        f"I will post updates as each phase completes.",
    )

    results: List[ClaudeResult] = []
    start_time = time.time()

    for phase in phases:
        phase_start = time.time()
        logger.info("Running phase %s for %s", phase, change_name)

        result = _run_phase(executor, phase, change_name)
        results.append(result)
        elapsed = time.time() - phase_start

        if result.success:
            _gh_comment(
                repo,
                issue_number,
                f"**Phase `{phase}` completed** ({elapsed:.0f}s)",
            )
        else:
            stderr_snippet = (result.error_message or result.result_text or "")[:500]
            _gh_comment(
                repo,
                issue_number,
                f"**Phase `{phase}` FAILED** ({elapsed:.0f}s)\n\n"
                f"```\n{stderr_snippet}\n```\n\n"
                f"Pipeline halted. Fix the issue and re-trigger.",
            )
            logger.error(
                "Phase %s failed for %s: %s",
                phase,
                change_name,
                stderr_snippet,
            )
            return

    total_elapsed = time.time() - start_time
    _gh_comment(
        repo,
        issue_number,
        f"**SDD Pipeline Complete**\n\n"
        f"- Change: `{change_name}`\n"
        f"- Phases completed: {len(results)}\n"
        f"- Total time: {total_elapsed:.0f}s",
    )
    logger.info(
        "Pipeline complete for %s (%d phases, %.0fs)",
        change_name,
        len(results),
        total_elapsed,
    )


# ---------------------------------------------------------------------------
# FastAPI application (only constructed when fastapi is available)
# ---------------------------------------------------------------------------

app: Any = None


def _run_phase(executor: ClaudeExecutor, phase: str, change_name: str) -> ClaudeResult:
    """Run one SDD phase through the current ClaudeExecutor API."""
    command = f"/sdd-{phase} {change_name}"
    return executor.run(command, timeout=CLAUDE_TIMEOUT)


if FASTAPI_AVAILABLE:
    assert FastAPI is not None
    assert HTTPException is not None
    assert uvicorn is not None
    app = FastAPI(
        title="Luum Webhook Trigger",
        description="GitHub webhook receiver for Cognitive OS SDD pipeline",
        version="1.0.0",
    )

    @app.get("/health")
    async def health() -> Dict[str, str]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "luum-webhook-trigger",
            "project_dir": PROJECT_DIR,
        }

    @app.post("/gh-webhook")
    async def github_webhook(request: Any) -> Dict[str, Any]:
        """Receive and process GitHub webhook events.

        Supported events:
          - ``issues`` (action: opened, labeled)
          - ``issue_comment`` (action: created)

        Returns a JSON response with processing status.
        """
        # --- Signature verification ---
        raw_body = await request.body()
        sig_header = request.headers.get("X-Hub-Signature-256", "")

        if not _verify_signature(raw_body, sig_header):
            raise HTTPException(status_code=401, detail="Invalid signature")

        # --- Parse event ---
        event_type = request.headers.get("X-GitHub-Event", "")
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

        action = payload.get("action", "")
        issue = payload.get("issue", {})
        issue_number = issue.get("number")
        repo_full_name = payload.get("repository", {}).get("full_name", "")

        if not issue_number or not repo_full_name:
            return {"status": "ignored", "reason": "missing issue or repo info"}

        # --- Determine trigger text ---
        trigger_text: Optional[str] = None

        if event_type == "issues" and action == "opened":
            body = issue.get("body", "") or ""
            if not _is_bot_comment(body) and _has_trigger(body):
                trigger_text = body

        elif event_type == "issues" and action == "labeled":
            # Check if the newly-added label plus existing body has a trigger
            body = issue.get("body", "") or ""
            if not _is_bot_comment(body) and _has_trigger(body):
                trigger_text = body

        elif event_type == "issue_comment" and action == "created":
            comment_body = payload.get("comment", {}).get("body", "") or ""
            if not _is_bot_comment(comment_body) and _has_trigger(comment_body):
                trigger_text = comment_body

        else:
            return {"status": "ignored", "reason": f"unhandled event: {event_type}.{action}"}

        if trigger_text is None:
            return {"status": "ignored", "reason": "no trigger keyword found"}

        # --- Classify issue ---
        labels = [lbl.get("name", "") for lbl in issue.get("labels", [])]
        title = issue.get("title", "")
        body = issue.get("body", "") or ""
        issue_class = classify_issue(labels, title, body)

        # --- Build change name ---
        change_name = _make_change_name(issue_number, title)

        logger.info(
            "Trigger detected: repo=%s issue=#%d class=%s change=%s",
            repo_full_name,
            issue_number,
            issue_class.value,
            change_name,
        )

        # --- Launch pipeline in background ---
        thread = threading.Thread(
            target=_run_pipeline,
            args=(repo_full_name, issue_number, change_name, issue_class),
            daemon=True,
            name=f"sdd-{change_name}",
        )
        thread.start()

        return {
            "status": "accepted",
            "issue_number": issue_number,
            "issue_class": issue_class.value,
            "change_name": change_name,
            "repo": repo_full_name,
        }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not FASTAPI_AVAILABLE:
        raise SystemExit("Cannot start server: fastapi/uvicorn not installed. "
                         "Run: pip install fastapi uvicorn")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Starting webhook trigger on port %d", PORT)
    assert uvicorn is not None
    uvicorn.run(app, host="0.0.0.0", port=PORT)
