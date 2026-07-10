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
SAFE_SCAN_TOKENS = (".cognitive-os", ".codex", "docs/04-Concepts/architecture", "docs/99-Archive/archived", "docs/99-Archive/archive")
SAFE_EXECUTABLE_PATTERNS = (
    "ugrep",
    "grep",
    "find",
    "rg",
    "ripgrep",
    "zsh -c source",
    "bash -c source",
)
CLAUDE_SNAPSHOT_MARKER = "/.claude/shell-snapshots/snapshot-zsh-"


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


def _command_matches_safe_scanner(command: str, safe_tokens: Sequence[str]) -> str | None:
    lowered = command.lower()
    has_scan_token = any(token.lower() in lowered for token in safe_tokens)
    if not has_scan_token:
        return None

    if CLAUDE_SNAPSHOT_MARKER in command and re.search(r"\b(grep|ugrep|rg|find)\b", lowered):
        return "claude-shell-snapshot-repo-scan"

    first_token = lowered.split(None, 1)[0] if lowered.split(None, 1) else lowered
    executable = Path(first_token).name
    if executable in {"ugrep", "grep", "find", "rg"} or any(p in lowered for p in SAFE_EXECUTABLE_PATTERNS):
        return "orphaned-repo-scan-process"
    return None


def find_orphan_scan_processes(
    rows: Iterable[ProcessRow],
    *,
    older_than_seconds: int = DEFAULT_OLDER_THAN_SECONDS,
    safe_tokens: Sequence[str] = SAFE_SCAN_TOKENS,
    current_pid: int | None = None,
) -> list[OrphanFinding]:
    """Return PPID=1 safe scanner processes older than the threshold."""
    current = os.getpid() if current_pid is None else current_pid
    findings: list[OrphanFinding] = []
    for row in rows:
        if row.pid == current:
            continue
        if row.ppid != 1:
            continue
        if row.etime_seconds < older_than_seconds:
            continue
        reason = _command_matches_safe_scanner(row.command, safe_tokens)
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
