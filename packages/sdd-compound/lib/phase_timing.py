# SCOPE: both
# scope: both
"""Phase Timing — wall-clock measurement and cost estimation for SDD phases.

Provides a context manager for timing phases, ASCII table rendering,
and persistence to both Engram-compatible dicts and JSONL metrics.
Python 3.9+ compatible.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

# Model cost per 1M tokens (input, output) in USD
MODEL_COSTS: Dict[str, Dict[str, float]] = {
    "opus": {"input": 15.00, "output": 75.00},
    "sonnet": {"input": 3.00, "output": 15.00},
    "haiku": {"input": 0.25, "output": 1.25},
}

# Default model routing for SDD phases (from rules/model-routing.md)
PHASE_MODEL_ROUTING: Dict[str, str] = {
    "explore": "sonnet",
    "propose": "opus",
    "spec": "sonnet",
    "design": "opus",
    "tasks": "sonnet",
    "apply": "sonnet",
    "verify": "sonnet",
    "archive": "haiku",
}

# Estimated token usage per phase (input + output, rough averages)
# Used for cost estimation when actual token counts are unavailable
PHASE_ESTIMATED_TOKENS: Dict[str, Dict[str, int]] = {
    "explore": {"input": 5000, "output": 3000},
    "propose": {"input": 8000, "output": 5000},
    "spec": {"input": 10000, "output": 8000},
    "design": {"input": 10000, "output": 6000},
    "tasks": {"input": 12000, "output": 8000},
    "apply": {"input": 15000, "output": 12000},
    "verify": {"input": 10000, "output": 5000},
    "archive": {"input": 5000, "output": 3000},
}


@dataclass
class TimingRecord:
    """Record of a single phase timing."""

    phase: str
    duration_secs: float
    model: str
    estimated_cost_usd: float
    timestamp: str
    change_name: str = ""
    actual_input_tokens: Optional[int] = None
    actual_output_tokens: Optional[int] = None


def _iso_now() -> str:
    """Return current UTC time in ISO 8601 format."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def estimate_phase_cost(
    phase: str,
    model: Optional[str] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
) -> float:
    """Estimate cost for a phase execution.

    Args:
        phase: SDD phase name.
        model: Model name override. Defaults to routing table.
        input_tokens: Actual input tokens (uses estimate if None).
        output_tokens: Actual output tokens (uses estimate if None).

    Returns:
        Estimated cost in USD.
    """
    model_name = model or PHASE_MODEL_ROUTING.get(phase, "sonnet")
    costs = MODEL_COSTS.get(model_name, MODEL_COSTS["sonnet"])

    estimates = PHASE_ESTIMATED_TOKENS.get(phase, {"input": 8000, "output": 5000})
    inp = input_tokens if input_tokens is not None else estimates["input"]
    out = output_tokens if output_tokens is not None else estimates["output"]

    cost = (inp * costs["input"] + out * costs["output"]) / 1_000_000
    return round(cost, 4)


class PhaseTimer:
    """Context manager that records wall-clock duration of a phase.

    Usage:
        with PhaseTimer("apply", change_name="auth-refactor") as timer:
            # ... do phase work ...
        print(timer.record)
    """

    def __init__(
        self,
        phase: str,
        change_name: str = "",
        model: Optional[str] = None,
    ):
        self.phase = phase
        self.change_name = change_name
        self.model = model or PHASE_MODEL_ROUTING.get(phase, "sonnet")
        self._start: float = 0.0
        self._end: float = 0.0
        self.record: Optional[TimingRecord] = None

    def __enter__(self) -> "PhaseTimer":
        self._start = time.monotonic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._end = time.monotonic()
        duration = round(self._end - self._start, 2)
        cost = estimate_phase_cost(self.phase, model=self.model)

        self.record = TimingRecord(
            phase=self.phase,
            duration_secs=duration,
            model=self.model,
            estimated_cost_usd=cost,
            timestamp=_iso_now(),
            change_name=self.change_name,
        )

    @property
    def duration_secs(self) -> float:
        """Return duration in seconds (0.0 if not yet completed)."""
        if self.record:
            return self.record.duration_secs
        if self._start > 0:
            return round(time.monotonic() - self._start, 2)
        return 0.0

    def to_dict(self) -> Dict:
        """Return timing record as dict for persistence."""
        if not self.record:
            return {}
        return {
            "phase": self.record.phase,
            "duration_secs": self.record.duration_secs,
            "model": self.record.model,
            "estimated_cost_usd": self.record.estimated_cost_usd,
            "timestamp": self.record.timestamp,
            "change_name": self.record.change_name,
        }


def format_timing_table(timings: Dict[str, float], models: Optional[Dict[str, str]] = None) -> str:
    """Render an ASCII table of per-phase durations with cost estimates.

    Args:
        timings: Dict mapping phase name to duration in seconds.
        models: Optional dict mapping phase name to model used.
            Defaults to PHASE_MODEL_ROUTING.

    Returns:
        Formatted ASCII table string.
    """
    if not timings:
        return "No timing data available."

    models = models or {}

    # Column headers
    headers = ["Phase", "Duration", "Model", "Est. Cost"]
    rows: List[List[str]] = []

    total_secs = 0.0
    total_cost = 0.0

    for phase, secs in timings.items():
        model = models.get(phase, PHASE_MODEL_ROUTING.get(phase, "sonnet"))
        cost = estimate_phase_cost(phase, model=model)

        total_secs += secs
        total_cost += cost

        duration_str = _format_duration(secs)
        rows.append([phase, duration_str, model, f"${cost:.4f}"])

    # Add totals row
    rows.append(["TOTAL", _format_duration(total_secs), "---", f"${total_cost:.4f}"])

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    # Build table
    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    header_line = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |"

    lines = [sep, header_line, sep]
    for i, row in enumerate(rows):
        line = "| " + " | ".join(cell.ljust(w) for cell, w in zip(row, widths)) + " |"
        lines.append(line)
        # Separator before totals
        if i == len(rows) - 2:
            lines.append(sep)
    lines.append(sep)

    return "\n".join(lines)


def _format_duration(secs: float) -> str:
    """Format seconds as human-readable duration."""
    if secs < 60:
        return f"{secs:.1f}s"
    minutes = int(secs // 60)
    remaining = secs % 60
    if minutes < 60:
        return f"{minutes}m {remaining:.0f}s"
    hours = int(minutes // 60)
    mins = minutes % 60
    return f"{hours}h {mins}m"


def append_timing_jsonl(
    filepath: str,
    phase: str,
    duration_secs: float,
    change_name: str = "",
    model: Optional[str] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
) -> Dict:
    """Append a timing record to the JSONL metrics file.

    Args:
        filepath: Path to the sdd-timings.jsonl file.
        phase: SDD phase name.
        duration_secs: Wall-clock duration.
        change_name: Name of the SDD change.
        model: Model used (defaults to routing table).
        input_tokens: Actual input tokens (optional).
        output_tokens: Actual output tokens (optional).

    Returns:
        The record dict that was written.
    """
    model_name = model or PHASE_MODEL_ROUTING.get(phase, "sonnet")
    cost = estimate_phase_cost(
        phase, model=model_name,
        input_tokens=input_tokens, output_tokens=output_tokens,
    )

    record = {
        "timestamp": _iso_now(),
        "change_name": change_name,
        "phase": phase,
        "duration_secs": round(duration_secs, 2),
        "model": model_name,
        "estimated_cost_usd": cost,
    }
    if input_tokens is not None:
        record["input_tokens"] = input_tokens
    if output_tokens is not None:
        record["output_tokens"] = output_tokens

    # Ensure parent directory exists
    parent = os.path.dirname(filepath)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return record


def build_engram_timing_content(
    change_name: str,
    timings: Dict[str, float],
    models: Optional[Dict[str, str]] = None,
) -> Dict:
    """Build Engram-compatible content for timing persistence.

    Args:
        change_name: SDD change name.
        timings: Phase -> duration mapping.
        models: Phase -> model mapping (optional).

    Returns:
        Dict with title, content, topic_key, and type fields
        ready to pass to mem_save.
    """
    table = format_timing_table(timings, models)
    total = round(sum(timings.values()), 2)
    phases_done = len(timings)

    content = (
        f"**What**: SDD timing data for '{change_name}'\n"
        f"**Phases timed**: {phases_done}\n"
        f"**Total duration**: {_format_duration(total)}\n\n"
        f"```\n{table}\n```"
    )

    return {
        "title": f"SDD timings: {change_name}",
        "content": content,
        "topic_key": f"planning/{change_name}/timings",
        "type": "pattern",
    }
