# SCOPE: os-only
"""MetricEvent — canonical JSONL event schema for SO observability (ADR-028 D1.A).

Schema versioning and migration strategy: docs/02-Decisions/adrs/ADR-028c.md
"""

from __future__ import annotations

import dataclasses
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

SCHEMA_VERSION = 1


class MetricEventError(ValueError):
    """Raised when a MetricEvent fails validation."""


@dataclass
class MetricEvent:
    """Canonical event record for .cognitive-os/metrics/*.jsonl.

    Fields:
        timestamp: ISO-8601 UTC string. Auto-filled to now() if not provided.
        source: The emitter's stable identifier (hook basename, skill id, agent id).
        event_type: Semantic category (e.g. "cost.recorded", "hook.health",
            "agent.escalation").
        severity: One of "debug" | "info" | "warn" | "error" | "critical".
        payload: Arbitrary dict with event-specific fields.
        schema_version: Integer, defaults to current SCHEMA_VERSION.
    """

    source: str
    event_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"
    timestamp: str = ""
    schema_version: int = SCHEMA_VERSION

    _VALID_SEVERITIES = frozenset({"debug", "info", "warn", "error", "critical"})

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.validate()

    def validate(self) -> None:
        if not isinstance(self.source, str) or not self.source:
            raise MetricEventError("source must be a non-empty string")
        if not isinstance(self.event_type, str) or not self.event_type:
            raise MetricEventError("event_type must be a non-empty string")
        if self.severity not in self._VALID_SEVERITIES:
            raise MetricEventError(
                f"severity must be one of {sorted(self._VALID_SEVERITIES)};"
                f" got {self.severity!r}"
            )
        if not isinstance(self.payload, dict):
            raise MetricEventError("payload must be a dict")
        if not isinstance(self.schema_version, int) or self.schema_version < 1:
            raise MetricEventError("schema_version must be a positive int")
        # best-effort ISO-8601 check
        try:
            datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise MetricEventError(
                f"timestamp must be ISO-8601: {self.timestamp!r}"
            ) from exc

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    def to_jsonl(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MetricEvent":
        """Construct a MetricEvent from a dict, tolerating legacy rows.

        Legacy rows (pre-MetricEvent) that lack ``source`` / ``event_type`` /
        ``payload`` are mapped to sensible defaults so they remain readable.

        Unknown top-level keys (fields that are not part of the MetricEvent
        schema) are folded into ``payload`` so no data is lost during the
        mixed-schema transition period.
        """
        _known = frozenset(
            {"source", "event_type", "payload", "severity", "timestamp", "schema_version"}
        )
        payload = d.get("payload", {})
        if not isinstance(payload, dict):
            payload = {"legacy_payload": payload}

        # Fold extra top-level keys into payload (legacy schema drift)
        extra = {k: v for k, v in d.items() if k not in _known}
        if extra:
            payload = {**extra, **payload}  # payload explicit fields win on collision

        return cls(
            source=d.get("source", "unknown"),
            event_type=d.get("event_type", "legacy"),
            payload=payload,
            severity=d.get("severity", "info"),
            timestamp=d.get("timestamp", ""),
            schema_version=int(d.get("schema_version", SCHEMA_VERSION)),
        )


def append_event(path: str, event: MetricEvent) -> bool:
    """Append a MetricEvent to a JSONL file, creating parent dirs if needed.

    Returns True on success, False on OSError (ENOSPC, EROFS, permission,
    parent-mkdir failure). Callers that care about backpressure can check
    the return value; most callers can ignore it — the function never
    raises, so a full disk will not crash a hook or session.

    ADR-028 D4 fix per chaos test_disk_full_metrics.py: the previous
    implementation let OSError propagate, which would cascade into hook
    failures and session instability under disk pressure.
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(event.to_jsonl() + "\n")
        return True
    except OSError as e:
        # Log once and degrade gracefully. No logger import at module top
        # to keep this path dependency-free; use stderr directly.
        import sys as _sys
        _sys.stderr.write(
            f"[metric_event] append_event failed ({type(e).__name__}: {e}); "
            f"degrading — event for path={path!r} dropped\n"
        )
        return False


def normalize_legacy_row(
    row: Dict[str, Any],
    source: str,
    event_type: str,
) -> Dict[str, Any]:
    """Convert a pre-MetricEvent JSONL row into a MetricEvent-shaped dict.

    The original fields are preserved under ``payload``.  The ``timestamp``
    key is lifted to the top level if present.  Used for the cost-events
    backfill script.
    """
    row = dict(row)  # do not mutate the caller's copy
    timestamp = row.pop("timestamp", None) or datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )
    event = MetricEvent(
        source=source,
        event_type=event_type,
        timestamp=timestamp,
        payload=row,
    )
    return event.to_dict()
