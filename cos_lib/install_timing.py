# SCOPE: os-only
"""install_timing.py — JSONL logger for SO install-timing measurements.

Writes append-only records to .cognitive-os/metrics/install-timing.jsonl.
Each record captures one end-to-end install run's timing and quality signals.

Record schema (ADR-059 §Phase 2):
  timestamp      str   UTC ISO-8601 (e.g. "2026-04-30T12:00:00Z")
  profile        str   setup.sh profile used ("--minimal"|"--standard"|"--full")
  elapsed_s      int   wall-clock seconds for the full install run
  manual_steps   int   count of interactive prompts requiring user input
  errors         int   stderr lines containing ERROR|FAIL|fatal
  docker_required int  1 if Docker was needed, 0 otherwise
  final_hook_count int hooks registered in settings.json after install
  exit_code      int   exit code of scripts/setup.sh (0 = success)

Python 3.9+ compatible. No third-party dependencies.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

# Default path relative to project root
DEFAULT_JSONL_PATH = ".cognitive-os/metrics/install-timing.jsonl"

# Budget thresholds from ADR-059 §Phase 2 exit criteria
BUDGET_ELAPSED_S = 300       # 5 minutes
BUDGET_MANUAL_STEPS = 3
BUDGET_ERRORS = 0


def _iso_now() -> str:
    """Return current UTC time in ISO 8601 format."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def append_install_record(
    *,
    elapsed_s: int,
    profile: str = "--standard",
    manual_steps: int = 0,
    errors: int = 0,
    docker_required: int = 0,
    final_hook_count: int = 0,
    exit_code: int = 0,
    jsonl_path: Optional[str] = None,
) -> dict:
    """Append one install-timing record to the JSONL log.

    Args:
        elapsed_s:        Wall-clock seconds for the install run.
        profile:          setup.sh profile (--minimal, --standard, --full).
        manual_steps:     Count of interactive prompts the user had to answer.
        errors:           Count of ERROR|FAIL|fatal lines in setup output.
        docker_required:  1 if Docker was required; 0 otherwise.
        final_hook_count: Number of hooks registered after install completes.
        exit_code:        Exit code from scripts/setup.sh.
        jsonl_path:       Override path for the JSONL file. Defaults to
                          DEFAULT_JSONL_PATH relative to cwd.

    Returns:
        The dict record that was written.
    """
    path = Path(jsonl_path or DEFAULT_JSONL_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": _iso_now(),
        "profile": profile,
        "elapsed_s": int(elapsed_s),
        "manual_steps": int(manual_steps),
        "errors": int(errors),
        "docker_required": int(docker_required),
        "final_hook_count": int(final_hook_count),
        "exit_code": int(exit_code),
    }

    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")

    return record


def within_budget(record: dict) -> bool:
    """Return True if the record satisfies ADR-059 §Phase 2 exit criteria.

    Criteria:
      elapsed_s < 300  (5 minutes)
      manual_steps <= 3
      errors == 0
    """
    return (
        record.get("elapsed_s", 9999) < BUDGET_ELAPSED_S
        and record.get("manual_steps", 9999) <= BUDGET_MANUAL_STEPS
        and record.get("errors", 9999) == BUDGET_ERRORS
    )


def read_records(jsonl_path: Optional[str] = None) -> list:
    """Read all records from the JSONL log.

    Args:
        jsonl_path: Override path. Defaults to DEFAULT_JSONL_PATH.

    Returns:
        List of record dicts. Returns [] if file does not exist.
    """
    path = Path(jsonl_path or DEFAULT_JSONL_PATH)
    if not path.exists():
        return []

    records = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
