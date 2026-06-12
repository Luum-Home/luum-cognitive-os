#!/usr/bin/env python3
# SCOPE: os-only
"""Aggregate real token usage from a Claude Code session transcript.

Reads all ``assistant`` events from a session JSONL file, sums ``message.usage``
across every turn, and appends ONE real cost event (``is_estimate: false``,
``source: "transcript"``) to ``.cognitive-os/metrics/cost-events.jsonl``.

Dedup: if a row with the same ``session_id`` and ``source: "transcript"`` already
exists in ``cost-events.jsonl``, the script exits 0 without writing a duplicate.

Graceful exit 0 when the transcript is unavailable (CI / remote environment).

Usage::

    python3 scripts/aggregate_session_tokens.py [<session_jsonl_path>]

If no path is given the most-recently-modified JSONL in the project's
``~/.claude/projects/<hash>/`` directory is used (Stop-hook mode).
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Make ``lib/`` importable when called directly or from the project root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from lib.record_completion import (
    _MODEL_PRICING,
    _DEFAULT_PRICING,
    _get_pricing,
    calculate_cost_usd,
    find_session_jsonl,
)
from lib.metric_event import MetricEvent, append_event
from lib.paths import runtime_project_root_or_cwd


# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------

def parse_claude_transcript(path: str) -> dict:
    """Sum ``message.usage`` across all ``assistant`` events in a session JSONL.

    Returns a dict:
      {
        "input_tokens": int,
        "output_tokens": int,
        "cache_read_input_tokens": int,
        "cache_creation_input_tokens": int,
        "model": str,             # most-frequent model seen
        "turn_count": int,
        "models_seen": list[str],
      }

    Raises ``FileNotFoundError`` if ``path`` does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Transcript not found: {path}")

    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_creation_input_tokens": 0,
    }
    model_counts: dict[str, int] = {}
    turn_count = 0

    with p.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            if record.get("type") != "assistant":
                continue

            message = record.get("message", {})
            usage = message.get("usage")
            if not usage:
                continue

            turn_count += 1
            totals["input_tokens"] += usage.get("input_tokens", 0)
            totals["output_tokens"] += usage.get("output_tokens", 0)
            totals["cache_read_input_tokens"] += usage.get("cache_read_input_tokens", 0)
            totals["cache_creation_input_tokens"] += usage.get("cache_creation_input_tokens", 0)

            model = message.get("model", "")
            if model:
                model_counts[model] = model_counts.get(model, 0) + 1

    # Pick the most-frequent model; fall back to "unknown"
    dominant_model = (
        max(model_counts, key=lambda m: model_counts[m]) if model_counts else "unknown"
    )

    return {
        **totals,
        "model": dominant_model,
        "turn_count": turn_count,
        "models_seen": sorted(model_counts.keys()),
    }


# ---------------------------------------------------------------------------
# Dedup check
# ---------------------------------------------------------------------------

def _session_already_recorded(cost_file: str, session_id: str) -> bool:
    """Return True if a ``source: "transcript"`` row for ``session_id`` exists."""
    p = Path(cost_file)
    if not p.exists():
        return False
    try:
        with p.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    row = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                payload = row.get("payload", {})
                if (
                    payload.get("source") == "transcript"
                    and payload.get("session_id") == session_id
                ):
                    return True
    except OSError:
        pass
    return False


# ---------------------------------------------------------------------------
# Cost event writer
# ---------------------------------------------------------------------------

def _is_pricing_known(model: str) -> bool:
    """Return True when the model has explicit pricing (not the default fallback)."""
    model_lower = model.lower()
    if model_lower in _MODEL_PRICING:
        return True
    for key in _MODEL_PRICING:
        if key in model_lower:
            return True
    return False


def write_transcript_cost_event(
    metrics_dir: str,
    session_id: str,
    totals: dict,
) -> None:
    """Append a real cost event for the session to ``cost-events.jsonl``.

    If the model pricing is unknown, ``actual_cost_usd`` is recorded as ``null``
    and ``pricing_known`` is ``false`` — never fabricated.
    """
    model = totals.get("model", "unknown")
    input_tokens = totals.get("input_tokens", 0)
    output_tokens = totals.get("output_tokens", 0)
    cache_read = totals.get("cache_read_input_tokens", 0)
    cache_write = totals.get("cache_creation_input_tokens", 0)
    pricing_known = _is_pricing_known(model)

    if pricing_known:
        actual_cost_usd: Optional[float] = calculate_cost_usd(
            input_tokens, output_tokens, cache_read, cache_write, model
        )
    else:
        actual_cost_usd = None

    payload: dict = {
        "source": "transcript",
        "session_id": session_id,
        "model": model,
        "models_seen": totals.get("models_seen", []),
        "turn_count": totals.get("turn_count", 0),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_input_tokens": cache_read,
        "cache_creation_input_tokens": cache_write,
        "actual_cost_usd": actual_cost_usd,
        "pricing_known": pricing_known,
        "is_estimate": False,
    }

    cost_file = os.path.join(metrics_dir, "cost-events.jsonl")
    os.makedirs(metrics_dir, exist_ok=True)
    event = MetricEvent(
        source="aggregate_session_tokens",
        event_type="cost.recorded",
        payload=payload,
    )
    append_event(cost_file, event)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate token usage from a Claude Code session transcript "
        "and append a real cost event to cost-events.jsonl.",
    )
    parser.add_argument(
        "transcript",
        nargs="?",
        default=None,
        help="Path to session JSONL transcript. "
        "Auto-detected (most-recent) if omitted.",
    )
    parser.add_argument(
        "--project-dir",
        default=None,
        help="Project root. Defaults to runtime_project_root_or_cwd().",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print totals without writing to cost-events.jsonl.",
    )
    args = parser.parse_args(argv)

    project_dir = args.project_dir or str(runtime_project_root_or_cwd())

    # Resolve transcript path
    transcript_path = args.transcript
    if not transcript_path:
        transcript_path = find_session_jsonl(project_dir)

    if not transcript_path or not Path(transcript_path).exists():
        # Graceful exit in CI / remote where transcript is unavailable
        print("[aggregate_session_tokens] No transcript available — skipping.", file=sys.stderr)
        return 0

    session_id = Path(transcript_path).stem

    metrics_dir = os.path.join(project_dir, ".cognitive-os", "metrics")
    cost_file = os.path.join(metrics_dir, "cost-events.jsonl")

    if _session_already_recorded(cost_file, session_id):
        print(
            f"[aggregate_session_tokens] session {session_id} already recorded — skipping.",
            file=sys.stderr,
        )
        return 0

    try:
        totals = parse_claude_transcript(transcript_path)
    except FileNotFoundError as exc:
        print(f"[aggregate_session_tokens] {exc} — skipping.", file=sys.stderr)
        return 0

    if args.dry_run:
        print(json.dumps({"session_id": session_id, **totals}, indent=2))
        return 0

    # Zero-token sessions ("not logged in" stubs, error sessions) are noise,
    # not telemetry — recording them would contaminate token_report.py output.
    total_tokens = (
        totals["input_tokens"]
        + totals["output_tokens"]
        + totals["cache_read_input_tokens"]
        + totals["cache_creation_input_tokens"]
    )
    if total_tokens == 0:
        print(
            f"[aggregate_session_tokens] session {session_id} has zero tokens — skipping.",
            file=sys.stderr,
        )
        return 0

    write_transcript_cost_event(metrics_dir, session_id, totals)

    model = totals.get("model", "unknown")
    pricing_known = _is_pricing_known(model)
    cost_info = (
        f"actual_cost_usd={calculate_cost_usd(totals['input_tokens'], totals['output_tokens'], totals['cache_read_input_tokens'], totals['cache_creation_input_tokens'], model):.6f}"
        if pricing_known
        else "actual_cost_usd=null (unknown model)"
    )
    print(
        f"[aggregate_session_tokens] Recorded session {session_id}: "
        f"input={totals['input_tokens']} output={totals['output_tokens']} "
        f"cache_read={totals['cache_read_input_tokens']} cache_write={totals['cache_creation_input_tokens']} "
        f"model={model} turns={totals['turn_count']} {cost_info}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
