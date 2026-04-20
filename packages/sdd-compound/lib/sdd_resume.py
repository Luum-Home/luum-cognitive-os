# SCOPE: both
# scope: both
"""SDD Pipeline Resume — state management and phase continuation.

Loads SDD state from Engram, determines next phase, and persists
phase completion. Python 3.9+ compatible.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

# Ordered SDD phases in dependency chain
SDD_PHASES: List[str] = [
    "explore",
    "propose",
    "spec",
    "design",
    "tasks",
    "apply",
    "verify",
    "archive",
]

# Which phases are required before each phase can start
PHASE_DEPENDENCIES: Dict[str, List[str]] = {
    "explore": [],
    "propose": [],  # explore is optional
    "spec": ["propose"],
    "design": ["propose"],
    "tasks": ["spec", "design"],
    "apply": ["tasks"],
    "verify": ["apply"],
    "archive": ["verify"],
}

# Engram topic key format for SDD state
STATE_TOPIC_KEY = "planning/{change}/state"
ARTIFACT_TOPIC_KEYS: Dict[str, str] = {
    "explore": "planning/{change}/explore",
    "propose": "planning/{change}/proposal",
    "spec": "planning/{change}/spec",
    "design": "planning/{change}/design",
    "tasks": "planning/{change}/tasks",
    "apply": "planning/{change}/apply-progress",
    "verify": "planning/{change}/verify-report",
    "archive": "planning/{change}/archive-report",
}


@dataclass
class PhaseRecord:
    """Record of a single phase execution."""

    phase: str
    status: str  # "completed", "failed", "in_progress"
    duration_secs: float = 0.0
    timestamp: str = ""
    retry_count: int = 0


@dataclass
class SDDState:
    """Full state of an SDD change pipeline."""

    change_name: str
    current_phase: Optional[str] = None
    phases_completed: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    timings: Dict[str, float] = field(default_factory=dict)
    history: List[Dict] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict) -> "SDDState":
        return cls(
            change_name=data.get("change_name", ""),
            current_phase=data.get("current_phase"),
            phases_completed=data.get("phases_completed", []),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            timings=data.get("timings", {}),
            history=data.get("history", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    @classmethod
    def from_json(cls, text: str) -> "SDDState":
        return cls.from_dict(json.loads(text))


def _iso_now() -> str:
    """Return current UTC time in ISO 8601 format. Avoids datetime for simplicity."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def determine_next_phase(
    state: SDDState,
    start_from: Optional[str] = None,
) -> Tuple[Optional[str], str]:
    """Determine the next phase to execute.

    Args:
        state: Current SDD state.
        start_from: Optional phase to force-start from.

    Returns:
        Tuple of (phase_name, reason).
        phase_name is None if the pipeline is complete.
    """
    if start_from is not None:
        if start_from not in SDD_PHASES:
            return None, f"Unknown phase: {start_from}. Valid: {', '.join(SDD_PHASES)}"
        # Check dependencies are met
        missing = [
            dep
            for dep in PHASE_DEPENDENCIES.get(start_from, [])
            if dep not in state.phases_completed
        ]
        if missing:
            return None, (
                f"Cannot start from '{start_from}': "
                f"missing dependencies: {', '.join(missing)}"
            )
        return start_from, f"Resuming from requested phase '{start_from}'"

    # If current_phase is set and not completed, resume it
    if (
        state.current_phase
        and state.current_phase not in state.phases_completed
    ):
        if state.retry_count >= state.max_retries:
            return None, (
                f"Phase '{state.current_phase}' has exceeded "
                f"{state.max_retries} retries. Human intervention required."
            )
        return state.current_phase, (
            f"Resuming in-progress phase '{state.current_phase}' "
            f"(retry {state.retry_count}/{state.max_retries})"
        )

    # Find the next phase whose dependencies are met
    for phase in SDD_PHASES:
        if phase in state.phases_completed:
            continue
        deps = PHASE_DEPENDENCIES.get(phase, [])
        missing = [d for d in deps if d not in state.phases_completed]
        if not missing:
            return phase, f"Next phase in pipeline: '{phase}'"

    return None, "Pipeline complete. All phases finished."


def resume(
    change_name: str,
    state_json: Optional[str] = None,
    start_from: Optional[str] = None,
) -> Dict:
    """Load SDD state and determine next phase.

    Args:
        change_name: Name of the SDD change.
        state_json: JSON string of persisted state from Engram.
            If None, a fresh state is created.
        start_from: Optional phase to force-start from.

    Returns:
        Dict with keys: change_name, next_phase, reason, state.
    """
    if state_json:
        state = SDDState.from_json(state_json)
        # Ensure change_name matches
        state.change_name = change_name
    else:
        state = SDDState(
            change_name=change_name,
            created_at=_iso_now(),
            updated_at=_iso_now(),
        )

    next_phase, reason = determine_next_phase(state, start_from)

    return {
        "change_name": change_name,
        "next_phase": next_phase,
        "reason": reason,
        "state": state.to_dict(),
        "topic_key": STATE_TOPIC_KEY.format(change=change_name),
    }


def save_state(
    change_name: str,
    phase: str,
    status: str,
    timing_secs: float = 0.0,
    state_json: Optional[str] = None,
) -> Dict:
    """Persist phase completion to state.

    Args:
        change_name: Name of the SDD change.
        phase: Phase that was executed.
        status: "completed" or "failed".
        timing_secs: Wall-clock duration of the phase.
        state_json: Existing state JSON from Engram (optional).

    Returns:
        Dict with updated state ready to persist to Engram.
    """
    if state_json:
        state = SDDState.from_json(state_json)
        state.change_name = change_name
    else:
        state = SDDState(
            change_name=change_name,
            created_at=_iso_now(),
        )

    now = _iso_now()
    state.updated_at = now

    history_entry = {
        "phase": phase,
        "status": status,
        "duration_secs": round(timing_secs, 2),
        "timestamp": now,
    }

    if status == "completed":
        if phase not in state.phases_completed:
            state.phases_completed.append(phase)
        state.timings[phase] = round(timing_secs, 2)
        state.current_phase = None
        state.retry_count = 0
        history_entry["action"] = "completed"
    elif status == "failed":
        state.current_phase = phase
        state.retry_count += 1
        history_entry["action"] = "failed"
        history_entry["retry_count"] = state.retry_count

    state.history.append(history_entry)

    return {
        "change_name": change_name,
        "state_json": state.to_json(),
        "state": state.to_dict(),
        "topic_key": STATE_TOPIC_KEY.format(change=change_name),
        "engram_title": f"SDD state: {change_name} ({phase} {status})",
    }


def get_state(change_name: str, state_json: Optional[str] = None) -> Dict:
    """Return current state of a change.

    Args:
        change_name: Name of the SDD change.
        state_json: JSON string of persisted state from Engram.

    Returns:
        Dict with state details and progress summary.
    """
    if not state_json:
        return {
            "change_name": change_name,
            "exists": False,
            "message": f"No state found for '{change_name}'.",
        }

    state = SDDState.from_json(state_json)
    total = len(SDD_PHASES)
    done = len(state.phases_completed)
    remaining = [p for p in SDD_PHASES if p not in state.phases_completed]

    return {
        "change_name": change_name,
        "exists": True,
        "progress": f"{done}/{total} phases completed",
        "phases_completed": state.phases_completed,
        "phases_remaining": remaining,
        "current_phase": state.current_phase,
        "retry_count": state.retry_count,
        "timings": state.timings,
        "total_time_secs": round(sum(state.timings.values()), 2),
        "state": state.to_dict(),
    }


def list_changes(engram_results: Optional[List[Dict]] = None) -> List[Dict]:
    """List all in-progress SDD changes from Engram search results.

    Args:
        engram_results: List of dicts from Engram mem_search results.
            Each dict should have 'title', 'content', and optionally
            'topic_key' fields.

    Returns:
        List of dicts with change_name, progress, and current_phase.
    """
    if not engram_results:
        return []

    changes = []
    for result in engram_results:
        content = result.get("content", "")
        title = result.get("title", "")

        # Try to parse as JSON state
        try:
            # Content might be wrapped in markdown code blocks
            clean = content.strip()
            if clean.startswith("```"):
                lines = clean.split("\n")
                # Remove first and last lines (``` markers)
                clean = "\n".join(lines[1:-1]) if len(lines) > 2 else ""
            state = SDDState.from_json(clean)
            done = len(state.phases_completed)
            total = len(SDD_PHASES)
            changes.append({
                "change_name": state.change_name,
                "progress": f"{done}/{total}",
                "current_phase": state.current_phase,
                "phases_completed": state.phases_completed,
                "retry_count": state.retry_count,
                "total_time_secs": round(sum(state.timings.values()), 2),
            })
        except (json.JSONDecodeError, KeyError):
            # Extract change name from title or topic_key
            name = title.replace("SDD state: ", "").split(" (")[0]
            changes.append({
                "change_name": name or "unknown",
                "progress": "unknown",
                "current_phase": None,
                "error": "Could not parse state",
            })

    return changes


def format_state_summary(state_dict: Dict) -> str:
    """Render a human-readable summary of an SDD state.

    Args:
        state_dict: Dict from get_state() or state.to_dict().

    Returns:
        Formatted string summary.
    """
    lines = []
    name = state_dict.get("change_name", "unknown")
    lines.append(f"SDD Change: {name}")
    lines.append(f"Progress: {state_dict.get('progress', 'N/A')}")

    current = state_dict.get("current_phase")
    if current:
        retry = state_dict.get("retry_count", 0)
        lines.append(f"Current Phase: {current} (retry {retry})")

    completed = state_dict.get("phases_completed", [])
    remaining = state_dict.get("phases_remaining", [])

    if completed:
        lines.append(f"Completed: {', '.join(completed)}")
    if remaining:
        lines.append(f"Remaining: {', '.join(remaining)}")

    timings = state_dict.get("timings", {})
    if timings:
        total = state_dict.get("total_time_secs", sum(timings.values()))
        lines.append(f"Total Time: {total:.1f}s")

    return "\n".join(lines)
