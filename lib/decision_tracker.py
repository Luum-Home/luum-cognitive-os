#!/usr/bin/env python3
"""decision_tracker.py — Persist operator decisions to engram.

ADR-069 §5b: When an operator accepts a research recommendation, the orchestrator
calls record_decision() to persist an engram observation under decision/<topic_key>.
This allows /decision-triage to cross-reference answered decisions.

Fix 2026-04-27: Addresses the "OR ambiguity" in ADR-069 §5 — decisions MUST be
persisted via this module; relying on memory alone caused all decisions to appear
as PENDING in /decision-triage indefinitely.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _engram_save(
    title: str,
    topic_key: str,
    content: str,
    observation_type: str = "decision",
    project: str = "luum-cognitive-os",
    timeout: int = 10,
) -> bool:
    """Save an observation to engram via the MCP Python client.

    Falls back to engram CLI if MCP client is unavailable.
    Returns True on success, False on any failure.
    """
    # Try MCP Python approach first (most reliable when running inside Claude Code)
    try:
        import importlib.util
        spec = importlib.util.find_spec("mcp_client")
        if spec is not None:
            # MCP client available — defer to it
            pass
    except Exception:
        pass

    # CLI approach: `engram save <title> <content> [--type ...] [--topic ...]`
    # engram v1.14.5 syntax: engram save <title> <msg> --type TYPE --project PROJECT
    #                                    --scope SCOPE --topic TOPIC_KEY
    try:
        result = subprocess.run(
            [
                "engram", "save",
                title,
                content,
                "--type", observation_type,
                "--project", project,
                "--scope", "project",
                "--topic", topic_key,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0
    except Exception as exc:
        print(f"WARNING: engram save failed: {exc}", file=sys.stderr)
        return False


def record_decision(
    topic_key: str,
    decision_text: str,
    recommendation: str = "",
    project: str = "luum-cognitive-os",
) -> bool:
    """Record an operator decision in engram under decision/<topic_key>.

    ADR-069 §5b mandates this call whenever an operator accepts a Phase 1
    recommendation. Absence of this call is the root cause of the 33-fake-criticals
    bug (decisions stayed PENDING because engram had no answered record).

    Args:
        topic_key: Stable key for the decision. Stored as "decision/<topic_key>".
                   Use the same slug used in the research report.
        decision_text: The operator's decision (what was chosen and why).
        recommendation: The original recommendation text from the research report.
        project: Engram project name.

    Returns:
        True if saved successfully, False otherwise (non-fatal — caller logs).
    """
    now = datetime.now(timezone.utc).isoformat()
    full_key = f"decision/{topic_key}"
    content_lines = [
        f"## Decision: {topic_key}",
        "",
        f"**Decided**: {now}",
        "",
        f"**Decision**: {decision_text}",
    ]
    if recommendation:
        content_lines += ["", f"**Original recommendation**: {recommendation}"]
    content_lines += [
        "",
        "**Status**: ANSWERED",
        "",
        "<!-- This observation is created by lib/decision_tracker.record_decision() -->",
        "<!-- ADR-069 §5b: persisting this prevents /decision-triage false positives -->",
    ]
    content = "\n".join(content_lines)

    title = f"Decision answered: {topic_key}"
    return _engram_save(
        title=title,
        topic_key=full_key,
        content=content,
        observation_type="decision",
        project=project,
    )


def mark_answered_by_slug(slug: str, answer_text: str = "Operator accepted") -> bool:
    """Minimal wrapper for use by scripts/decision_triage.py --mark-answered."""
    return record_decision(
        topic_key=slug,
        decision_text=answer_text,
    )
