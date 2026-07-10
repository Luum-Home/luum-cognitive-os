# SCOPE: os-only
"""COS-native goal state model: dataclasses, JSON store, and append-only event log.

Implements REQ-001 (goal creation), REQ-013 (persistence/re-projection),
REQ-015 (audit log), REQ-016 (concurrent writer lock).

File layout per workspace/thread:
  .cognitive-os/goals/<workspace_thread_id>/current.json   -- active or paused state
  .cognitive-os/goals/<workspace_thread_id>/events.jsonl   -- append-only audit log
  .cognitive-os/goals/<workspace_thread_id>/archive/<goal_id>.json -- terminal state
"""

from __future__ import annotations

import fcntl
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


# ---------------------------------------------------------------------------
# Status literals
# ---------------------------------------------------------------------------

GoalStatus = Literal["active", "paused", "budget_limited", "complete", "escalated", "cleared"]

# Legal state transitions: (from_status, to_status)
_LEGAL_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    [
        ("active", "paused"),
        ("active", "budget_limited"),
        ("active", "complete"),
        ("active", "escalated"),
        ("active", "cleared"),
        ("paused", "active"),
        ("paused", "cleared"),
        ("paused", "budget_limited"),
    ]
)

# Terminal statuses (cannot transition out of)
_TERMINAL_STATUSES: frozenset[str] = frozenset(
    ["budget_limited", "complete", "escalated", "cleared"]
)

# Statuses that allow Stop without blocking
_ALLOW_STOP_STATUSES: frozenset[str] = frozenset(
    ["paused", "budget_limited", "complete", "escalated", "cleared"]
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CommandEvidence:
    """Record of a command run during a worker iteration."""

    command: str
    exit_code: int
    output_excerpt: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CommandEvidence":
        return cls(
            command=d["command"],
            exit_code=d["exit_code"],
            output_excerpt=d.get("output_excerpt", ""),
        )


@dataclass
class EvidencePacket:
    """Structured evidence produced by a worker iteration.

    source is always 'explicit-packet' in MVP (transcript scraping is out of scope).
    """

    iteration: int
    files_changed: list[str]
    commands_run: list[CommandEvidence]
    passing_checks: list[str]
    acceptance_coverage: dict[str, str]
    remaining_gaps: list[str]
    blockers: list[str]
    next_action: str | None
    raw_summary: str
    source: Literal["explicit-packet"] = "explicit-packet"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["commands_run"] = [c.to_dict() for c in self.commands_run]
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EvidencePacket":
        return cls(
            iteration=d["iteration"],
            files_changed=d.get("files_changed", []),
            commands_run=[CommandEvidence.from_dict(c) for c in d.get("commands_run", [])],
            passing_checks=d.get("passing_checks", []),
            acceptance_coverage=d.get("acceptance_coverage", {}),
            remaining_gaps=d.get("remaining_gaps", []),
            blockers=d.get("blockers", []),
            next_action=d.get("next_action"),
            raw_summary=d.get("raw_summary", ""),
            source=d.get("source", "explicit-packet"),
        )


@dataclass
class EvaluatorVerdict:
    """Verdict produced by GoalEvaluator after examining an evidence packet."""

    verdict: Literal["complete", "incomplete", "escalate"]
    reason: str
    missing_checks: list[str]
    confidence: float
    evaluated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EvaluatorVerdict":
        return cls(
            verdict=d["verdict"],
            reason=d["reason"],
            missing_checks=d.get("missing_checks", []),
            confidence=d.get("confidence", 0.0),
            evaluated_at=d["evaluated_at"],
        )


@dataclass
class GoalState:
    """Full persisted state for a COS-native goal.

    All four budget dimensions are tracked (OD-002):
      max_turns / turns_used — turn counter, incremented each Stop-hook cycle.
      max_minutes            — wall-clock budget, derived from started_at_epoch.
      max_tokens             — cumulative tokens read from llm-dispatch.jsonl.
      max_cost_usd           — cumulative cost_usd from the same log.
    """

    goal_id: str
    status: GoalStatus
    objective: str
    acceptance_checks: list[str]
    constraints: list[str]
    created_at: str
    updated_at: str
    max_turns: int | None
    max_minutes: int | None
    max_tokens: int | None
    max_cost_usd: float | None
    turns_used: int
    started_at_epoch: float
    evidence_history: list[EvidencePacket] = field(default_factory=list)
    evaluator_history: list[EvaluatorVerdict] = field(default_factory=list)
    last_guidance: str | None = None
    lock_owner: str | None = None
    workspace_thread_id: str = ""
    consecutive_no_progress: int = 0
    """Counter tracking consecutive turns with no evaluator progress.

    Incremented each time the evaluator returns 'incomplete' without any new
    acceptance checks being satisfied compared to the previous turn.
    Reset to zero when at least one check is newly satisfied.
    Used by GoalEvaluator to trigger the 'escalated' transition per REQ-017.
    """
    escalation_threshold: int = 5
    """Number of consecutive no-progress turns before auto-escalation (REQ-017).

    Default is 5. Configurable per goal at creation time.
    """
    dispatch_cursor: int = 0
    """Byte offset into llm-dispatch.jsonl for bounded incremental reads.

    check_budget advances this cursor after each read so that subsequent calls
    start from where the last call left off, keeping the hot path O(new records)
    rather than O(total file size).  If the file is smaller than the cursor
    (log rotation), the cursor is reset to 0 and the file is re-read from the
    start.
    """
    dispatch_tokens_used: int = 0
    """Cumulative token count already charged to this goal from dispatch metrics."""
    dispatch_cost_used: float = 0.0
    """Cumulative USD cost already charged to this goal from dispatch metrics."""

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        objective: str,
        acceptance_checks: list[str],
        *,
        constraints: list[str] | None = None,
        max_turns: int | None = None,
        max_minutes: int | None = None,
        max_tokens: int | None = None,
        max_cost_usd: float | None = None,
        workspace_thread_id: str = "default",
        escalation_threshold: int = 5,
    ) -> "GoalState":
        """Create a new GoalState with status 'active'."""
        now = _now_iso()
        return cls(
            goal_id=str(uuid.uuid4()),
            status="active",
            objective=objective,
            acceptance_checks=list(acceptance_checks),
            constraints=list(constraints or []),
            created_at=now,
            updated_at=now,
            max_turns=max_turns,
            max_minutes=max_minutes,
            max_tokens=max_tokens,
            max_cost_usd=max_cost_usd,
            turns_used=0,
            started_at_epoch=time.time(),
            evidence_history=[],
            evaluator_history=[],
            last_guidance=None,
            lock_owner=None,
            workspace_thread_id=workspace_thread_id,
            consecutive_no_progress=0,
            escalation_threshold=escalation_threshold,
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "status": self.status,
            "objective": self.objective,
            "acceptance_checks": self.acceptance_checks,
            "constraints": self.constraints,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "max_turns": self.max_turns,
            "max_minutes": self.max_minutes,
            "max_tokens": self.max_tokens,
            "max_cost_usd": self.max_cost_usd,
            "turns_used": self.turns_used,
            "started_at_epoch": self.started_at_epoch,
            "evidence_history": [e.to_dict() for e in self.evidence_history],
            "evaluator_history": [v.to_dict() for v in self.evaluator_history],
            "last_guidance": self.last_guidance,
            "lock_owner": self.lock_owner,
            "workspace_thread_id": self.workspace_thread_id,
            "consecutive_no_progress": self.consecutive_no_progress,
            "escalation_threshold": self.escalation_threshold,
            "dispatch_cursor": self.dispatch_cursor,
            "dispatch_tokens_used": self.dispatch_tokens_used,
            "dispatch_cost_used": self.dispatch_cost_used,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GoalState":
        return cls(
            goal_id=d["goal_id"],
            status=d["status"],
            objective=d["objective"],
            acceptance_checks=d.get("acceptance_checks", []),
            constraints=d.get("constraints", []),
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            max_turns=d.get("max_turns"),
            max_minutes=d.get("max_minutes"),
            max_tokens=d.get("max_tokens"),
            max_cost_usd=d.get("max_cost_usd"),
            turns_used=d.get("turns_used", 0),
            started_at_epoch=d.get("started_at_epoch", time.time()),
            evidence_history=[EvidencePacket.from_dict(e) for e in d.get("evidence_history", [])],
            evaluator_history=[EvaluatorVerdict.from_dict(v) for v in d.get("evaluator_history", [])],
            last_guidance=d.get("last_guidance"),
            lock_owner=d.get("lock_owner"),
            workspace_thread_id=d.get("workspace_thread_id", "default"),
            consecutive_no_progress=d.get("consecutive_no_progress", 0),
            escalation_threshold=d.get("escalation_threshold", 5),
            dispatch_cursor=d.get("dispatch_cursor", 0),
            dispatch_tokens_used=d.get("dispatch_tokens_used", 0),
            dispatch_cost_used=d.get("dispatch_cost_used", 0.0),
        )

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def allows_stop(self) -> bool:
        """Return True when the Stop hook should NOT block on this goal."""
        return self.status in _ALLOW_STOP_STATUSES

    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_STATUSES


# ---------------------------------------------------------------------------
# Transition validation
# ---------------------------------------------------------------------------


class InvalidTransitionError(ValueError):
    """Raised when a requested state transition is not legal."""


def validate_transition(current_status: str, new_status: str) -> None:
    """Raise InvalidTransitionError if the transition is not legal.

    Terminal states cannot transition to any other status.
    """
    if current_status in _TERMINAL_STATUSES:
        raise InvalidTransitionError(
            f"Cannot transition from terminal status '{current_status}' to '{new_status}'."
        )
    if (current_status, new_status) not in _LEGAL_TRANSITIONS:
        raise InvalidTransitionError(
            f"Transition '{current_status}' -> '{new_status}' is not allowed. "
            f"Legal transitions from '{current_status}': "
            + str([t for t in _LEGAL_TRANSITIONS if t[0] == current_status])
        )


def apply_transition(goal: GoalState, new_status: GoalStatus) -> GoalState:
    """Return a new GoalState with status updated after validation."""
    validate_transition(goal.status, new_status)
    now = _now_iso()
    return GoalState(
        **{
            **goal.to_dict(),
            "status": new_status,
            "updated_at": now,
            "evidence_history": goal.evidence_history,
            "evaluator_history": goal.evaluator_history,
        }
    )


# ---------------------------------------------------------------------------
# GoalStateStore
# ---------------------------------------------------------------------------


class GoalConflictError(OSError):
    """Raised when a concurrent session holds the lock."""


class GoalStateStore:
    """Manages goal state persistence for a workspace/thread.

    Directory layout:
      <base_dir>/<workspace_thread_id>/current.json
      <base_dir>/<workspace_thread_id>/events.jsonl
      <base_dir>/<workspace_thread_id>/archive/<goal_id>.json
    """

    def __init__(
        self,
        base_dir: Path | str | None = None,
        workspace_thread_id: str = "default",
    ):
        if base_dir is None:
            # Resolve from CWD
            base_dir = Path.cwd() / ".cognitive-os" / "goals"
        self._base = Path(base_dir)
        self._wt_id = workspace_thread_id
        self._dir = self._base / workspace_thread_id
        self._current_path = self._dir / "current.json"
        self._events_path = self._dir / "events.jsonl"
        self._archive_dir = self._dir / "archive"
        self._lock_path = self._dir / ".lock"

    # ------------------------------------------------------------------
    # Paths (for tests and inspection)
    # ------------------------------------------------------------------

    @property
    def current_path(self) -> Path:
        return self._current_path

    @property
    def events_path(self) -> Path:
        return self._events_path

    @property
    def archive_dir(self) -> Path:
        return self._archive_dir

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_dirs(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._archive_dir.mkdir(parents=True, exist_ok=True)

    def _append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Append an event to the append-only event log (best-effort, never raises)."""
        try:
            self._ensure_dirs()
            record = {
                "ts": _now_iso(),
                "event": event_type,
                **payload,
            }
            with self._events_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        except OSError:
            pass

    def _write_current(self, goal: GoalState) -> None:
        """Write current.json atomically."""
        self._ensure_dirs()
        tmp = self._current_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(goal.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._current_path)

    # ------------------------------------------------------------------
    # Lock
    # ------------------------------------------------------------------

    def _acquire_lock(self, owner: str, timeout: float = 5.0) -> "Any":
        """Acquire an exclusive fcntl lock on the lock file.

        Returns an open file handle that must be released by the caller.
        Raises GoalConflictError if the lock cannot be acquired within timeout.
        """
        self._ensure_dirs()
        fh = self._lock_path.open("w", encoding="utf-8")
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fh.write(owner)
                fh.flush()
                return fh
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    fh.close()
                    raise GoalConflictError(
                        f"Cannot acquire goal lock for workspace '{self._wt_id}': "
                        "another session holds the lock."
                    )
                time.sleep(0.05)

    @staticmethod
    def _release_lock(fh: "Any") -> None:
        try:
            fcntl.flock(fh, fcntl.LOCK_UN)
            fh.close()
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> GoalState | None:
        """Load and return the current goal state, or None if no active goal."""
        if not self._current_path.exists():
            return None
        try:
            data = json.loads(self._current_path.read_text(encoding="utf-8"))
            return GoalState.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def save(self, goal: GoalState, owner: str = "session", timeout: float = 5.0) -> None:
        """Persist goal state, appending a create/update event to the log.

        Acquires an exclusive file lock; raises GoalConflictError on timeout.
        """
        lock_fh = self._acquire_lock(owner, timeout)
        try:
            existing = self.load()
            event_type = "create" if existing is None else "update"
            self._write_current(goal)
            self._append_event(event_type, {"goal_id": goal.goal_id, "status": goal.status})
        finally:
            self._release_lock(lock_fh)

    def archive(self, goal: GoalState, owner: str = "session", timeout: float = 5.0) -> Path:
        """Move a terminal goal to archive/ and remove current.json.

        Appends an archive event. Returns the archive path.
        """
        lock_fh = self._acquire_lock(owner, timeout)
        try:
            self._ensure_dirs()
            archive_path = self._archive_dir / f"{goal.goal_id}.json"
            archive_path.write_text(
                json.dumps(goal.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
            )
            if self._current_path.exists():
                self._current_path.unlink()
            self._append_event(
                "archive",
                {"goal_id": goal.goal_id, "status": goal.status, "archive_path": str(archive_path)},
            )
            return archive_path
        finally:
            self._release_lock(lock_fh)

    def append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Public interface to append an arbitrary event to the log."""
        self._append_event(event_type, payload)

    def load_events(self) -> list[dict[str, Any]]:
        """Return all events from the JSONL log."""
        if not self._events_path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in self._events_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
