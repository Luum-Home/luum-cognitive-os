# SCOPE: os-only
"""
Skill Synthesizer — Phase 2 of learning-loop closure (ADR-095).

Reads .cognitive-os/metrics/tool-sequences.jsonl (written by
hooks/tool-sequence-capture.sh) and identifies recurring tool-call sequences
that appear across sessions without an existing skill match.

The module proposes skill drafts to skills/experimental/<auto-name>/SKILL.md
and surfaces auto-promotion candidates based on feedback data.

Public API
----------
find_recurring_sequences(jsonl_path, min_length, min_occurrences, window_days)
    -> list[dict]

propose_skill_draft(sequence_record, draft_dir)
    -> Path

auto_promote_eligible(experimental_dir, feedback_jsonl, threshold)
    -> list[Path]
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import textwrap
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _default_metrics_dir() -> Path:
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return Path(project_dir) / ".cognitive-os" / "metrics"


def _parse_ts(ts_str: str) -> datetime | None:
    """Parse ISO-8601 UTC timestamp; return None on failure."""
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read valid JSONL records; skip malformed lines."""
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return records


def _sequence_signature(tools: list[str]) -> str:
    """Stable string key for a tool sequence list."""
    return "->".join(tools)


def _auto_name(tools: list[str]) -> str:
    """Generate a slug skill name from the tool sequence."""
    base = "-".join(t.lower() for t in tools[:4])
    # Strip non-alphanumeric except hyphens
    base = re.sub(r"[^a-z0-9-]", "", base)
    # Append short hash for uniqueness
    sig = _sequence_signature(tools)
    suffix = hashlib.sha256(sig.encode()).hexdigest()[:6]
    return f"auto-{base}-{suffix}"


def _friendly_description(tools: list[str], occurrences: int, sessions: int) -> str:
    """Human-readable description for the synthesized skill draft."""
    tool_str = " → ".join(tools)
    return (
        f"Auto-synthesized skill from recurring tool sequence detected "
        f"{occurrences} time(s) across {sessions} session(s): {tool_str}"
    )


# ---------------------------------------------------------------------------
# Sliding-window n-gram extraction
# ---------------------------------------------------------------------------

def _extract_ngrams(tools: list[str], n: int) -> list[tuple[str, ...]]:
    """Return all n-grams from *tools*."""
    return [tuple(tools[i : i + n]) for i in range(len(tools) - n + 1)]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_recurring_sequences(
    jsonl_path: Path,
    min_length: int = 3,
    min_occurrences: int = 3,
    window_days: int = 7,
) -> list[dict[str, Any]]:
    """Identify tool sequences that recur at least *min_occurrences* times.

    Scans *jsonl_path* (tool-sequences.jsonl) for rows within the last
    *window_days* days, groups tool names per session in order, then counts
    n-gram occurrences across all sessions.

    Each returned dict::

        {
            "signature": "Read->Edit->Bash",    # canonical sequence key
            "tools": ["Read", "Edit", "Bash"],  # tool name list
            "length": 3,
            "occurrences": 5,                   # total cross-session hits
            "sessions": ["sess-a", "sess-b"],   # distinct session IDs
            "session_count": 2,
        }

    Sequences already covered by an existing skill (deduplication) are NOT
    filtered here — the operator/skill handles that via skill_router.best_match.
    """
    records = _read_jsonl(jsonl_path)
    if not records:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

    # Group tool names per session in chronological order (within window)
    session_tools: dict[str, list[str]] = defaultdict(list)
    session_timestamps: dict[str, list[datetime]] = defaultdict(list)

    for rec in records:
        ts = _parse_ts(rec.get("timestamp", ""))
        if ts is None or ts < cutoff:
            continue
        success = rec.get("success")
        if success is not True:
            # Only count successful invocations — noise reduction
            continue
        tool = rec.get("tool", "")
        if not tool:
            continue
        session_id = rec.get("session_id", "unknown")
        session_tools[session_id].append(tool)
        session_timestamps[session_id].append(ts)

    # Count n-gram occurrences across sessions
    # Key: tuple of tool names → {occurrences: int, sessions: set}
    ngram_counts: dict[tuple[str, ...], dict[str, Any]] = defaultdict(
        lambda: {"occurrences": 0, "sessions": set()}
    )

    for session_id, tools in session_tools.items():
        if len(tools) < min_length:
            continue
        # Extract n-grams of length min_length up to min_length+3 to avoid explosion
        max_len = min(min_length + 3, len(tools))
        seen_in_session: set[tuple[str, ...]] = set()
        for n in range(min_length, max_len + 1):
            for gram in _extract_ngrams(tools, n):
                if gram not in seen_in_session:
                    ngram_counts[gram]["occurrences"] += 1
                    ngram_counts[gram]["sessions"].add(session_id)
                    seen_in_session.add(gram)

    # Filter by threshold and build result list
    results: list[dict[str, Any]] = []
    for gram, data in ngram_counts.items():
        if data["occurrences"] >= min_occurrences:
            tools_list = list(gram)
            results.append(
                {
                    "signature": _sequence_signature(tools_list),
                    "tools": tools_list,
                    "length": len(tools_list),
                    "occurrences": data["occurrences"],
                    "sessions": sorted(data["sessions"]),
                    "session_count": len(data["sessions"]),
                }
            )

    # Sort by occurrences descending, then by length descending (prefer longer patterns)
    results.sort(key=lambda r: (r["occurrences"], r["length"]), reverse=True)
    return results


def propose_skill_draft(
    sequence_record: dict[str, Any],
    draft_dir: Path,
) -> Path:
    """Write a draft SKILL.md to *draft_dir*/<auto-name>/SKILL.md.

    Idempotent: if the file already exists with the same signature, it is
    not overwritten (returns the existing path).

    *sequence_record* is one item from ``find_recurring_sequences`` output.

    Returns the path of the written (or already-existing) draft.
    """
    tools: list[str] = sequence_record.get("tools", [])
    if not tools:
        raise ValueError("sequence_record must contain non-empty 'tools' list")

    name = _auto_name(tools)
    skill_dir = draft_dir / name
    skill_file = skill_dir / "SKILL.md"

    # Idempotency: do not overwrite existing draft
    if skill_file.exists():
        return skill_file

    skill_dir.mkdir(parents=True, exist_ok=True)

    description = _friendly_description(
        tools,
        sequence_record.get("occurrences", 0),
        sequence_record.get("session_count", 0),
    )
    signature = sequence_record.get("signature", _sequence_signature(tools))
    tools_bullet = "\n".join(f"- {t}" for t in tools)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    platform = "claude" + "-code"

    content = textwrap.dedent(f"""\
        <!-- SCOPE: os-only -->
        <!-- AUTO-GENERATED by lib/skill_synthesizer.py on {now} — do not edit header fields manually -->
        ---
        name: {name}
        description: "{description}"
        trigger: "synthesized-skill, {name}"
        model: sonnet
        effort: sonnet
        audience: project
        version: "0.1.0-experimental"
        platforms: ["{platform}"]
        prerequisites: []
        user-invocable: true
        tier: experimental
        tags: [auto-generated, synthesis]
        synthesis_signature: "{signature}"
        synthesis_occurrences: {sequence_record.get("occurrences", 0)}
        synthesis_sessions: {sequence_record.get("session_count", 0)}
        ---

        # {name}

        > **Experimental skill** — auto-synthesized from a recurring tool-call pattern.
        > Review and promote to `skills/{name}/` if useful, or delete this draft.

        ## Detected Pattern

        The following tool sequence was observed {sequence_record.get("occurrences", 0)} time(s)
        across {sequence_record.get("session_count", 0)} session(s):

        {tools_bullet}

        ## Suggested Usage

        Invoke this skill when you need to perform a workflow that involves the
        tools listed above in sequence. Review the session history for context on
        what each step accomplished.

        ## Promotion

        To promote this experimental skill to active status, first run `/primitive-authoring` and the exact-path classifier gate after moving it:

        ```bash
        mv skills/experimental/{name}/ skills/{name}/
        python3 scripts/primitive_scope_classifier.py \
          --project-dir . \
          --paths skills/{name}/SKILL.md \
          --fail-contradictions \
          --fail-low-confidence
        git add skills/{name}/
        git commit -m "feat(skills): promote experimental skill {name}"
        ```

        Add consumer availability, behavior evidence, and paired portability proof before claiming `SCOPE: both`.

        To reject (delete) this draft:

        ```bash
        rm -rf skills/experimental/{name}/
        ```

        ## Lineage

        - Generated: {now}
        - Sequence signature: `{signature}`
        - Sessions observed: {", ".join(sequence_record.get("sessions", [])[:5])}
        """)

    skill_file.write_text(content, encoding="utf-8")
    return skill_file


def auto_promote_eligible(
    experimental_dir: Path,
    feedback_jsonl: Path,
    threshold: int = 5,
) -> list[Path]:
    """Return paths of experimental skill dirs eligible for promotion.

    A skill is promotion-eligible when it has received at least *threshold*
    successful feedback entries in skill-feedback.jsonl.

    IMPORTANT: this function only IDENTIFIES candidates — it does NOT move or
    modify any files. Movement is operator-gated through /synthesize-skill.

    Returns a list of SKILL.md paths for eligible experimental skills.
    """
    if not experimental_dir.exists():
        return []

    # Build success counts from feedback
    feedback = _read_jsonl(feedback_jsonl)
    success_counts: dict[str, int] = defaultdict(int)
    for rec in feedback:
        skill = rec.get("skill", "")
        if skill and rec.get("success") is True:
            success_counts[skill] += 1

    eligible: list[Path] = []
    for skill_dir in sorted(experimental_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        skill_name = skill_dir.name
        if success_counts.get(skill_name, 0) >= threshold:
            eligible.append(skill_file)

    return eligible
