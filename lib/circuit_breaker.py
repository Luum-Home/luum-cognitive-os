# scope: both
"""Circuit breaker for agent task launches.

Prevents launching agents for a task_type that keeps failing by tracking
consecutive failure counts and enforcing CLOSED → OPEN → HALF_OPEN transitions.

States:
    CLOSED    — normal operation; agent launches are allowed
    OPEN      — blocked; too many consecutive failures, cooldown in effect
    HALF_OPEN — cooldown expired; one probe launch is allowed to test recovery

Usage:
    from lib.circuit_breaker import CircuitBreaker

    cb = CircuitBreaker()
    if not cb.can_launch("sdd-apply"):
        print("Circuit open — skipping launch")
    else:
        # launch agent ...
        cb.record_failure("sdd-apply")   # on failure
        cb.record_success("sdd-apply")   # on success

State is persisted to .cognitive-os/metrics/circuit-breaker-state.json.

Python 3.9+ compatible. No external dependencies.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_CLOSED = "closed"
STATE_OPEN = "open"
STATE_HALF_OPEN = "half_open"

DEFAULT_FAILURE_THRESHOLD = 3   # consecutive failures before OPEN
DEFAULT_COOLDOWN_SECONDS = 3600  # 1 hour


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class CircuitState:
    task_type: str
    state: str                  # "closed" | "open" | "half_open"
    failure_count: int
    last_failure_at: Optional[str]   # ISO-8601 or None
    opened_at: Optional[str]         # ISO-8601 or None
    cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS


# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------


class CircuitBreaker:
    """Per-task-type circuit breaker with JSON persistence."""

    def __init__(
        self,
        state_file: Optional[Path] = None,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
    ):
        if state_file is None:
            # Resolve relative to repo root (two levels up from lib/)
            repo_root = Path(__file__).resolve().parent.parent
            state_file = (
                repo_root / ".cognitive-os" / "metrics" / "circuit-breaker-state.json"
            )
        self._state_file = Path(state_file)
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._circuits: Dict[str, CircuitState] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_failure(self, task_type: str) -> CircuitState:
        """Record a failure for task_type.

        Increments the consecutive failure count.  If the count reaches
        the threshold the circuit transitions to OPEN.
        """
        circuit = self._get_or_create(task_type)
        circuit.failure_count += 1
        circuit.last_failure_at = _now_iso()

        if circuit.failure_count >= self._failure_threshold:
            circuit.state = STATE_OPEN
            if circuit.opened_at is None:
                circuit.opened_at = _now_iso()

        self._save()
        return circuit

    def record_success(self, task_type: str) -> CircuitState:
        """Record a successful launch for task_type.

        Resets the failure count.  If the circuit was HALF_OPEN it is
        promoted back to CLOSED (recovery confirmed).
        """
        circuit = self._get_or_create(task_type)
        circuit.failure_count = 0
        circuit.last_failure_at = None
        circuit.opened_at = None
        circuit.state = STATE_CLOSED
        self._save()
        return circuit

    def can_launch(self, task_type: str) -> bool:
        """Return True if an agent of task_type is allowed to launch.

        CLOSED / HALF_OPEN → True (launch allowed)
        OPEN               → False, unless the cooldown has expired in which
                             case the circuit is moved to HALF_OPEN and True
                             is returned (one probe is permitted).
        """
        circuit = self._get_or_create(task_type)

        if circuit.state == STATE_CLOSED:
            return True

        if circuit.state == STATE_HALF_OPEN:
            return True

        # OPEN — check whether the cooldown has expired
        if circuit.opened_at is not None:
            opened_epoch = _iso_to_epoch(circuit.opened_at)
            elapsed = _now_epoch() - opened_epoch
            if elapsed >= self._cooldown_seconds:
                circuit.state = STATE_HALF_OPEN
                self._save()
                return True

        return False

    def get_status(self) -> Dict[str, dict]:
        """Return all circuit states as a plain dict (task_type → state dict)."""
        return {tt: asdict(cs) for tt, cs in self._circuits.items()}

    def format_status(self) -> str:
        """Return a human-readable summary of all circuit states."""
        if not self._circuits:
            return "Circuit Breaker Status: no circuits tracked yet."

        lines = ["Circuit Breaker Status:"]
        for task_type, cs in sorted(self._circuits.items()):
            icon = {"closed": "✓", "open": "✗", "half_open": "~"}.get(cs.state, "?")
            lines.append(
                f"  {icon} {task_type}: {cs.state.upper()}"
                f"  (failures={cs.failure_count},"
                f" opened_at={cs.opened_at or 'n/a'})"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create(self, task_type: str) -> CircuitState:
        if task_type not in self._circuits:
            self._circuits[task_type] = CircuitState(
                task_type=task_type,
                state=STATE_CLOSED,
                failure_count=0,
                last_failure_at=None,
                opened_at=None,
                cooldown_seconds=self._cooldown_seconds,
            )
        return self._circuits[task_type]

    def _load(self) -> None:
        if not self._state_file.exists():
            return
        try:
            raw = json.loads(self._state_file.read_text())
            for tt, data in raw.items():
                self._circuits[tt] = CircuitState(
                    task_type=data.get("task_type", tt),
                    state=data.get("state", STATE_CLOSED),
                    failure_count=data.get("failure_count", 0),
                    last_failure_at=data.get("last_failure_at"),
                    opened_at=data.get("opened_at"),
                    cooldown_seconds=data.get("cooldown_seconds", self._cooldown_seconds),
                )
        except (json.JSONDecodeError, KeyError):
            # Corrupt state file — start fresh
            self._circuits = {}

    def _save(self) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {tt: asdict(cs) for tt, cs in self._circuits.items()}
        self._state_file.write_text(json.dumps(payload, indent=2))


# ---------------------------------------------------------------------------
# Time helpers (kept local to avoid import complexity)
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_epoch() -> float:
    return datetime.now(timezone.utc).timestamp()


def _iso_to_epoch(iso: str) -> float:
    """Parse an ISO-8601 UTC string back to a Unix timestamp."""
    # Support both trailing-Z and +00:00 forms
    iso_clean = iso.replace("Z", "+00:00")
    return datetime.fromisoformat(iso_clean).timestamp()
