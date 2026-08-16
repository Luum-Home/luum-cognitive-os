# SCOPE: both
"""Orphan process audit for unregistered repo scan pipelines.

ADR-279 primitive: detect conservative, safe-to-review process orphans such as
Claude/zsh grep pipelines and ugrep/find children that were reparented to PID 1.
Default mode is dry-run; signal delivery requires an explicit caller opt-in.
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

SCHEMA_VERSION = "orphan-process-audit/v1"
DEFAULT_OLDER_THAN_SECONDS = 60 * 60
REPO_ROOT = Path(__file__).resolve().parents[1]

# Repo-relative path fragments. They are matched on path-component boundaries,
# never as bare substrings: an unanchored ``.codex`` also matches the vendor
# namespace ``com.openai.codex`` and made this primitive point SIGTERM at
# another product's updater (measured 2026-08-15).
SAFE_SCAN_TOKENS = (".cognitive-os", ".codex", "docs/04-Concepts/architecture", "docs/99-Archive/archived", "docs/99-Archive/archive")
SAFE_EXECUTABLE_NAMES = ("ugrep", "grep", "find", "rg", "ripgrep")
SAFE_SHELL_SOURCE_PATTERNS = ("zsh -c source", "bash -c source")
CLAUDE_SNAPSHOT_MARKER = "/.claude/shell-snapshots/snapshot-zsh-"

# argv markers meaning "this process was born detached on purpose". ``ppid=1``
# is only evidence of a leak when the process did NOT declare itself a daemon.
# Canonical source, shared with scripts/audit_hanging_processes.py.
DAEMON_MARKERS = ("--daemon", "--serve", "daemon-launcher")

# Floor for --kill. The 2026-08-15 census measured a natural orphan lifetime
# ceiling of 505 s with 95% collected inside 288 s, so anything below this is
# killing processes that are still doing work.
KILL_MIN_AGE_SECONDS = 600

_SAFE_EXECUTABLE_RE = re.compile(r"\b(?:" + "|".join(SAFE_EXECUTABLE_NAMES) + r")\b")


@dataclass(frozen=True)
class ProcessRow:
    """One parsed `ps` row."""

    pid: int
    ppid: int
    etime_seconds: int
    command: str


@dataclass(frozen=True)
class OrphanFinding:
    """Auditable finding for a candidate orphan process."""

    pid: int
    ppid: int
    age_seconds: int
    command: str
    reason: str
    action: str = "dry-run"
    signal_sent: str | None = None
    stable_id: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "stable_id", f"adr-279/orphan-process/{self.pid}")


def parse_etime_seconds(raw: str) -> int:
    """Parse BSD/GNU ps etime strings such as `04:30`, `01:02:03`, `2-03:04:05`."""
    value = raw.strip()
    if not value:
        return 0
    days = 0
    if "-" in value:
        day_text, value = value.split("-", 1)
        days = int(day_text)
    parts = [int(part) for part in value.split(":")]
    if len(parts) == 2:
        hours = 0
        minutes, seconds = parts
    elif len(parts) == 3:
        hours, minutes, seconds = parts
    else:
        raise ValueError(f"unsupported ps etime value: {raw!r}")
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def parse_ps_output(text: str) -> list[ProcessRow]:
    """Parse `ps -axo pid,ppid,etime,command` output into rows."""
    rows: list[ProcessRow] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.upper().startswith("PID "):
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        try:
            rows.append(
                ProcessRow(
                    pid=int(parts[0]),
                    ppid=int(parts[1]),
                    etime_seconds=parse_etime_seconds(parts[2]),
                    command=parts[3],
                )
            )
        except (TypeError, ValueError):
            continue
    return rows


def collect_processes() -> list[ProcessRow]:
    """Collect process rows using portable BSD-style ps fields."""
    result = subprocess.run(
        ["ps", "-axo", "pid,ppid,etime,command"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        return []
    return parse_ps_output(result.stdout)


def _token_present(command: str, token: str) -> bool:
    """True when *token* appears as a path component, not as a bare substring.

    ``.codex`` must match ``/.codex/`` and `` .codex`` but NOT the vendor
    namespace ``com.openai.codex``: the character before the token may not be a
    word, dot or dash character.
    """
    pattern = r"(?<![\w.\-])" + re.escape(token) + r"(?![\w\-])"
    return re.search(pattern, command, flags=re.IGNORECASE) is not None


def _is_scanner_shaped(command: str) -> bool:
    lowered = command.lower()
    first_token = lowered.split(None, 1)[0] if lowered.split(None, 1) else lowered
    if Path(first_token).name in set(SAFE_EXECUTABLE_NAMES):
        return True
    if any(p in lowered for p in SAFE_SHELL_SOURCE_PATTERNS):
        return True
    # Word-boundary match: an unanchored "rg" also matches "org.sparkle-project".
    return _SAFE_EXECUTABLE_RE.search(lowered) is not None


def _classify(command: str, safe_tokens: Sequence[str], project_root: Path) -> str | None:
    """Return the finding reason, or None when the process is not ours to touch.

    Ownership is required first: a process is a candidate only when its argv
    references this repository. Without that check the primitive classified
    foreign processes purely on a shared substring.
    """
    if any(marker in command for marker in DAEMON_MARKERS):
        return None  # declared detached on purpose — ppid=1 is expected here

    root_referenced = str(project_root) in command
    token_referenced = any(_token_present(command, token) for token in safe_tokens)
    if not (root_referenced or token_referenced):
        return None

    scanner = _is_scanner_shaped(command)
    if scanner and CLAUDE_SNAPSHOT_MARKER in command:
        return "claude-shell-snapshot-repo-scan"
    if scanner:
        return "orphaned-repo-scan-process"
    # Non-scanner processes need the strong ownership signal: the absolute repo
    # path in argv. This is the family the audit used to miss entirely — every
    # orphan measured on 2026-08-15 was a `scripts/*.py`, not a grep pipeline.
    if root_referenced:
        return "orphaned-repo-process"
    return None


def find_orphan_scan_processes(
    rows: Iterable[ProcessRow],
    *,
    older_than_seconds: int = DEFAULT_OLDER_THAN_SECONDS,
    safe_tokens: Sequence[str] = SAFE_SCAN_TOKENS,
    current_pid: int | None = None,
    project_root: Path | str | None = None,
) -> list[OrphanFinding]:
    """Return orphaned processes owned by this repo, older than the threshold.

    A row is a candidate when all of these hold:
      * ``ppid == 1`` — reparented to init;
      * argv carries no daemon marker (see ``DAEMON_MARKERS``);
      * argv references this repository (absolute root, or a repo path token
        matched on component boundaries);
      * it is older than *older_than_seconds*.
    """
    current = os.getpid() if current_pid is None else current_pid
    root = Path(project_root).resolve() if project_root else REPO_ROOT
    findings: list[OrphanFinding] = []
    for row in rows:
        if row.pid == current:
            continue
        if row.ppid != 1:
            continue
        if row.etime_seconds < older_than_seconds:
            continue
        reason = _classify(row.command, safe_tokens, root)
        if not reason:
            continue
        findings.append(
            OrphanFinding(
                pid=row.pid,
                ppid=row.ppid,
                age_seconds=row.etime_seconds,
                command=row.command[:500],
                reason=reason,
            )
        )
    return findings


def terminate_findings(
    findings: Iterable[OrphanFinding],
    *,
    grace_seconds: float = 1.0,
    force: bool = True,
) -> list[OrphanFinding]:
    """Send SIGTERM, optionally SIGKILL, to previously classified findings."""
    terminated: list[OrphanFinding] = []
    for finding in findings:
        sent = "SIGTERM"
        try:
            os.kill(finding.pid, signal.SIGTERM)
        except ProcessLookupError:
            sent = "already-exited"
        except PermissionError:
            sent = "permission-denied"
        if sent == "SIGTERM" and force:
            deadline = time.time() + grace_seconds
            while time.time() < deadline:
                if not _pid_alive(finding.pid):
                    break
                time.sleep(0.05)
            if _pid_alive(finding.pid):
                try:
                    os.kill(finding.pid, signal.SIGKILL)
                    sent = "SIGTERM+SIGKILL"
                except (ProcessLookupError, PermissionError):
                    pass
        terminated.append(
            OrphanFinding(
                pid=finding.pid,
                ppid=finding.ppid,
                age_seconds=finding.age_seconds,
                command=finding.command,
                reason=finding.reason,
                action="killed" if sent not in {"permission-denied"} else "kill-failed",
                signal_sent=sent,
            )
        )
    return terminated


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def build_report(findings: Sequence[OrphanFinding], *, killed: bool) -> dict:
    """Build stable JSON report."""
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "kill" if killed else "dry-run",
        "summary": {
            "candidate_count": len(findings),
            "killed_count": sum(1 for item in findings if item.action == "killed"),
        },
        "findings": [asdict(item) for item in findings],
    }


def append_metric(project_dir: Path, report: dict) -> None:
    """Append JSONL metric evidence; failure is non-fatal."""
    try:
        metrics = project_dir / ".cognitive-os" / "metrics"
        metrics.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": report["generated_at"],
            "source": "cos-orphan-process-audit",
            "event_type": "orphan_process_audit",
            "payload": report,
        }
        with (metrics / "orphan-processes.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")
    except OSError:
        return
