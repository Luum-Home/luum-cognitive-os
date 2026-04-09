"""Auto-repair system — minimal viable version.

Classifies errors and applies known remediations from a registry.
NOT the full aspirational system — just pattern matching + fix commands.
"""
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class Remediation:
    """A known fix for a common error pattern."""
    error_pattern: str  # regex
    fix_command: str     # bash command (may contain {placeholders})
    description: str
    safe: bool = True    # True = auto-apply, False = suggest only
    _compiled: re.Pattern = field(default=None, init=False, repr=False)

    def __post_init__(self):
        self._compiled = re.compile(self.error_pattern, re.IGNORECASE)

    def matches(self, message: str) -> Optional[re.Match]:
        return self._compiled.search(message)


# ---------------------------------------------------------------------------
# Registry of known remediations
# ---------------------------------------------------------------------------

REMEDIATION_REGISTRY: List[Remediation] = [
    Remediation(
        error_pattern=r"ModuleNotFoundError: No module named '(\w+)'",
        fix_command="pip install {module}",
        description="Install missing Python module",
        safe=False,
    ),
    Remediation(
        error_pattern=r"Cannot find module '([^']+)'",
        fix_command="npm install {module}",
        description="Install missing npm package",
        safe=False,
    ),
    Remediation(
        error_pattern=r"go: .*missing go\.sum entry",
        fix_command="go mod tidy",
        description="Fix missing Go module checksums",
        safe=True,
    ),
    Remediation(
        error_pattern=r"permission denied.*?([^\s]+\.sh)",
        fix_command="chmod +x {file}",
        description="Make script executable",
        safe=True,
    ),
    Remediation(
        error_pattern=r"address already in use.*?:(\d+)",
        fix_command="lsof -ti:{port} | xargs kill -9",
        description="Kill process using port",
        safe=False,
    ),
    Remediation(
        error_pattern=r"SyntaxError:.*?line (\d+)",
        fix_command="python3 -m py_compile {file}",
        description="Python syntax error — check file compilation",
        safe=False,
    ),
    Remediation(
        error_pattern=r"ENOSPC: no space left on device",
        fix_command="docker system prune -f",
        description="Free Docker disk space",
        safe=False,
    ),
    Remediation(
        error_pattern=r"fatal: not a git repository",
        fix_command="git init",
        description="Initialize git repository",
        safe=False,
    ),
]


def classify_error(error_type: str, message: str) -> Optional[Remediation]:
    """Match an error message against the registry. Return first match or None."""
    combined = f"{error_type} {message}"
    for remediation in REMEDIATION_REGISTRY:
        if remediation.matches(combined):
            return remediation
    return None


def apply_remediation(
    remediation: Remediation,
    message: str = "",
    dry_run: bool = False,
    metrics_dir: str = ".cognitive-os/metrics",
) -> dict:
    """Apply a remediation. In dry_run or unsafe mode, only suggest."""
    # Extract placeholders from the match
    match = remediation.matches(message) if message else None
    command = remediation.fix_command

    if match and match.groups():
        groups = match.groups()
        # Replace common placeholders
        placeholders = {"module": 0, "file": 0, "port": 0}
        for key in placeholders:
            if f"{{{key}}}" in command and len(groups) > 0:
                command = command.replace(f"{{{key}}}", groups[0])

    result = {
        "action": "suggest" if (dry_run or not remediation.safe) else "applied",
        "command": command,
        "description": remediation.description,
        "safe": remediation.safe,
        "dry_run": dry_run,
    }

    if not dry_run and remediation.safe:
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )
            result["exit_code"] = proc.returncode
            result["stdout"] = proc.stdout[:500]
            result["stderr"] = proc.stderr[:500]
            result["action"] = "applied" if proc.returncode == 0 else "failed"
        except (subprocess.TimeoutExpired, OSError) as exc:
            result["action"] = "failed"
            result["error"] = str(exc)

    # Log outcome
    _log_repair_outcome(result, metrics_dir)
    return result


def format_repair_suggestion(remediation: Remediation, message: str = "") -> str:
    """Human-readable suggestion string."""
    match = remediation.matches(message) if message else None
    command = remediation.fix_command
    if match and match.groups():
        for key in ("module", "file", "port"):
            if f"{{{key}}}" in command:
                command = command.replace(f"{{{key}}}", match.groups()[0])

    safe_tag = "[AUTO]" if remediation.safe else "[MANUAL]"
    return f"{safe_tag} {remediation.description}: {command}"


def _log_repair_outcome(result: dict, metrics_dir: str) -> None:
    """Append repair outcome to metrics."""
    try:
        os.makedirs(metrics_dir, exist_ok=True)
        path = os.path.join(metrics_dir, "repair-outcomes.jsonl")
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **result,
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except OSError:
        pass
