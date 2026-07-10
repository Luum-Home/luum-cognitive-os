# SCOPE: os-only
"""
Skill Failure Repair — Phase 1 of learning-loop closure (ADR-089).

Reads .cognitive-os/metrics/skill-feedback.jsonl (written by
hooks/skill-feedback-tracker.sh) and identifies skills that have crossed
a failure threshold inside a rolling time window.

Schema of each JSONL line (as produced by skill-feedback-tracker.sh):
    {"timestamp": "<ISO-8601-UTC>", "skill": "<name>", "success": <bool>}

The module emits repair signals to
.cognitive-os/metrics/skill-repair-queue.jsonl for a downstream consumer
(skills/repair-skill/SKILL.md or /queue-drain) to act on.  It does NOT
auto-regenerate skills — that would risk a runaway feedback loop where a
bad regen produces more failures.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _default_metrics_dir() -> Path:
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return Path(project_dir) / ".cognitive-os" / "metrics"


def _parse_ts(ts_str: str) -> datetime | None:
    """Parse an ISO-8601 UTC timestamp, returning None on failure."""
    try:
        # Python 3.10 fromisoformat doesn't handle trailing 'Z'; normalise.
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read all valid JSONL records from *path*; skip malformed lines."""
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return records


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_failing_skills(
    jsonl_path: Path,
    threshold: int = 5,
    window_hours: int = 24,
) -> list[dict[str, Any]]:
    """Return skills that crossed *threshold* failures inside *window_hours*.

    Each returned item is a dict::

        {
            "skill": str,
            "failure_count": int,
            "failure_records": list[dict],   # all failure lines in window
            "success_count": int,            # successes in window (for context)
        }

    Records whose ``success`` field is absent or non-boolean are skipped so
    that schema evolution doesn't silently inflate counts.
    """
    records = _read_jsonl(jsonl_path)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

    # Bucket records by skill, within window only
    failures_by_skill: dict[str, list[dict[str, Any]]] = {}
    successes_by_skill: dict[str, int] = {}

    for rec in records:
        skill = rec.get("skill", "")
        if not skill:
            continue
        ts = _parse_ts(rec.get("timestamp", ""))
        if ts is None or ts < cutoff:
            continue
        success = rec.get("success")
        if not isinstance(success, bool):
            continue
        if success:
            successes_by_skill[skill] = successes_by_skill.get(skill, 0) + 1
        else:
            failures_by_skill.setdefault(skill, []).append(rec)

    results: list[dict[str, Any]] = []
    for skill, failure_records in failures_by_skill.items():
        if len(failure_records) >= threshold:
            results.append(
                {
                    "skill": skill,
                    "failure_count": len(failure_records),
                    "failure_records": failure_records,
                    "success_count": successes_by_skill.get(skill, 0),
                }
            )
    return results


def propose_repair_action(
    skill_name: str,
    failure_records: list[dict[str, Any]],
    all_records_path: Path | None = None,
    stale_days: int = 7,
) -> dict[str, Any]:
    """Return a repair plan for *skill_name*.

    ``suggested_action`` is one of:

    * ``"regenerate"``  — all recent failures share the same error signature
      (deterministic failure; regeneration is likely to help).
    * ``"investigate"`` — failures are varied (non-deterministic; regen may
      not fix the root cause; human/LLM investigation required first).
    * ``"deprecate"``   — the skill has had zero successes in the last
      *stale_days* days (and has failures); it may be obsolete.

    *all_records_path* is the path to skill-feedback.jsonl; if provided it is
    used to compute the last-success date for the "deprecate" heuristic.
    """
    # Gather error messages from failure records (field names that trackers
    # might populate; gracefully absent is fine — we work with what we have)
    errors = [
        str(r.get("error") or r.get("output") or r.get("reason") or "")
        for r in failure_records
    ]
    non_empty_errors = [e for e in errors if e]

    # Heuristic: uniform error → regenerate; varied → investigate
    if non_empty_errors:
        unique_errors = set(non_empty_errors)
        if len(unique_errors) == 1:
            suggested_action = "regenerate"
        else:
            suggested_action = "investigate"
    else:
        # No error metadata → conservative default
        suggested_action = "investigate"

    # Override to "deprecate" if no successful run in the last stale_days
    if all_records_path is not None:
        stale_cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
        all_records = _read_jsonl(all_records_path)
        last_success: datetime | None = None
        for rec in all_records:
            if rec.get("skill") != skill_name:
                continue
            if rec.get("success") is not True:
                continue
            ts = _parse_ts(rec.get("timestamp", ""))
            if ts is None:
                continue
            if last_success is None or ts > last_success:
                last_success = ts
        if last_success is None or last_success < stale_cutoff:
            suggested_action = "deprecate"

    sample_errors = non_empty_errors[:3]  # cap to avoid huge payloads

    return {
        "skill": skill_name,
        "failure_count": len(failure_records),
        "sample_errors": sample_errors,
        "suggested_action": suggested_action,
    }


def emit_repair_signal(plan: dict[str, Any], output_jsonl: Path) -> None:
    """Append a repair signal record to *output_jsonl*.

    Creates parent directories and the file if they do not exist.  Uses
    append mode so concurrent writers don't truncate each other (each line
    is atomic on POSIX for writes ≤ PIPE_BUF when written in one call).
    """
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "skill": plan.get("skill", ""),
        "failure_count": plan.get("failure_count", 0),
        "sample_errors": plan.get("sample_errors", []),
        "suggested_action": plan.get("suggested_action", "investigate"),
        "status": "pending",
    }
    line = json.dumps(record, ensure_ascii=False)
    with output_jsonl.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
