#!/usr/bin/env python3
# SCOPE: os-only
"""Aggregate real token usage from agent session transcripts.

Reads JSONL transcript/session files from supported harnesses, normalizes provider
usage into a portable schema, and appends ONE real cost event
(``is_estimate: false``, ``source: "transcript"``) to
``.cognitive-os/metrics/cost-events.jsonl``.

Supported input shapes include Claude Code ``message.usage``, OpenAI
Responses/Chat ``usage`` blocks, and generic Codex/OpenCode JSONL usage events.

Dedup: if a row with the same ``session_id`` and ``source: "transcript"`` already
exists in ``cost-events.jsonl``, the script exits 0 without writing a duplicate.

Graceful exit 0 when the transcript is unavailable (CI / remote environment).

Usage::

    python3 scripts/aggregate_session_tokens.py [<session_jsonl_path>]

If no path is given the script checks explicit transcript env vars first, then
known Claude/Codex/OpenCode local session directories, then the legacy Claude
project-hash finder (Stop-hook mode).
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

from cos_lib.record_completion import (
    _MODEL_PRICING,
    _DEFAULT_PRICING,
    _get_pricing,
    calculate_cost_usd,
    find_session_jsonl,
)
from cos_lib.metric_event import MetricEvent, append_event
from cos_lib.paths import runtime_project_root_or_cwd
from cos_lib.token_usage import summarize_usage_jsonl

_TRANSCRIPT_ENV_VARS = (
    "COGNITIVE_OS_SESSION_JSONL",
    "CODEX_SESSION_JSONL",
    "OPENCODE_SESSION_JSONL",
    "CLAUDE_SESSION_JSONL",
)


def _latest_jsonl_under(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        candidates = [item for item in path.rglob("*.jsonl") if item.is_file()]
    except OSError:
        return None
    if not candidates:
        return None
    return str(max(candidates, key=lambda item: item.stat().st_mtime))


def find_portable_session_jsonl(project_dir: str) -> str | None:
    """Find the most likely local transcript across supported harnesses."""
    for env_name in _TRANSCRIPT_ENV_VARS:
        value = os.environ.get(env_name)
        if value and Path(value).exists():
            return value

    home = Path.home()
    search_roots = (
        home / ".codex" / "sessions",
        home / ".opencode" / "sessions",
        home / ".local" / "share" / "opencode" / "sessions",
    )
    discovered: list[str] = []
    for root in search_roots:
        latest = _latest_jsonl_under(root)
        if latest:
            discovered.append(latest)
    # The Claude Code transcript competes on mtime with the other harnesses;
    # short-circuiting on codex/opencode would pick a stale foreign-project
    # rollout over the session that actually just stopped.
    claude_latest = find_session_jsonl(project_dir)
    if claude_latest:
        discovered.append(claude_latest)
    if discovered:
        return max(discovered, key=lambda item: Path(item).stat().st_mtime)

    return None


# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------

def parse_claude_transcript(path: str) -> dict:
    """Backward-compatible wrapper for Claude transcript aggregation."""
    return parse_usage_transcript(path, default_harness="claude-code")


def parse_usage_transcript(path: str, *, default_harness: str = "unknown") -> dict:
    """Normalize and sum real usage across supported harness transcript shapes."""
    return summarize_usage_jsonl(path, default_harness=default_harness).as_dict()


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
        "telemetry_schema": "token-usage-normalized.v1",
        "session_id": session_id,
        "model": model,
        "models_seen": totals.get("models_seen", []),
        "providers_seen": totals.get("providers_seen", []),
        "harnesses_seen": totals.get("harnesses_seen", []),
        "source_kind": totals.get("source_kind", "usage"),
        "parser_version": totals.get("parser_version", "token-usage-normalizer.v1"),
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
        description="Aggregate real token usage from supported harness session transcripts "
        "and append a normalized cost event to cost-events.jsonl.",
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
        transcript_path = find_portable_session_jsonl(project_dir)

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
        totals = parse_usage_transcript(transcript_path, default_harness="auto")
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
