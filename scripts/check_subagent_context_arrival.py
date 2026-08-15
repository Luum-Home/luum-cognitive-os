#!/usr/bin/env python3
"""Measure whether the injected sub-agent context ACTUALLY ARRIVES.

Why this is a script and not a pytest case
------------------------------------------
``tests/hooks/test_subagent_context_injector.py`` runs the hook under
``subprocess.run`` and asserts on ``result.stdout``. That measures EMISSION: it
proves the hook composes the right bytes and prints them in the shape the host
documents. It cannot prove ARRIVAL, because arrival happens inside a real
sub-agent's context window, one layer past anything a unit test can observe.

Three ways to close that gap, and why this is the one taken:

  (A) Stop claiming what is not proven. Done — the test class was renamed from
      ``TestMandatoryRulesDelivery`` to ``TestMandatoryRulesEmission`` and its
      assertion messages no longer say "arrive". Costs nothing, and it is what
      keeps the unit suite honest.
  (B) A separate, on-demand check against real transcripts. This file. It is
      not deterministic — it reads whatever sub-agents happen to have run on
      this machine — so it is a script with exit codes, not a CI gate.
  (C) Mock the transcript and assert the mock contains what the mock put there.
      Rejected. It would turn a red signal green while proving nothing, which
      is the exact failure mode this whole investigation was about.

Both (A) and (B) were taken. (C) was not.

Method
------
Reads sub-agent transcripts under ``~/.claude/projects/<slug>/*/subagents/*.jsonl``
and looks for the interpolated marker ``Phase: `<phase>` ``. The marker is
load-bearing: ``templates/agent-preamble.md`` ships the literal ``Phase:
{{phase}}``, and only the hook substitutes it. Finding the interpolated form in
a transcript means the hook's output reached that sub-agent.

Two false-positive sources are filtered, both observed on 2026-08-15:

  1. A brief that QUOTES the marker (an orchestrator pasting this very check
     into a sub-agent prompt). Counted as a mention, not an arrival.
  2. An assistant turn that WRITES the marker (an agent reporting on the
     template). Also a mention.

An arrival only counts when the marker appears in a system-reminder / injected
context block, not in a user prompt or an assistant message.

Exit codes
----------
  0  at least one genuine arrival found
  1  transcripts found, zero genuine arrivals (the defect is live)
  2  error, or no transcripts to measure

Usage
-----
    python3 scripts/check_subagent_context_arrival.py [--project-dir PATH] [-v]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _slug(project_dir: Path) -> str:
    """Claude Code encodes a project path into a flat directory name.

    Both path separators AND dots collapse to dashes — a path segment
    containing dots (a dotted account name, a versioned directory) is not
    round-trippable, which is why this maps forward rather than parsing back.
    """
    return re.sub(r"[/.]", "-", str(project_dir.resolve()))


def _expected_marker(project_dir: Path) -> str | None:
    """Build the interpolated marker the hook would have produced."""
    template = project_dir / "templates" / "agent-preamble.md"
    if not template.exists():
        return None
    # The template ships ``Phase: `{{phase}}`.`` — backticks around the
    # placeholder, not around the whole thing. Getting this wrong makes the
    # check report "template no longer carries the placeholder" on a template
    # that carries it fine, so the literal is asserted, not assumed.
    if "`{{phase}}`" not in template.read_text(encoding="utf-8", errors="ignore"):
        return None

    # Phase resolution mirrors get_phase() in hooks/_lib/common.sh: it is read
    # from the `phase:` key of cognitive-os.yaml, defaulting to reconstruction.
    phase = "reconstruction"
    config = project_dir / "cognitive-os.yaml"
    if config.exists():
        for line in config.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if stripped.startswith("phase:"):
                value = stripped.split(":", 1)[1].split("#", 1)[0].strip()
                if value:
                    phase = value
                break
    return f"Phase: `{phase}`"


def _classify(path: Path, marker: str) -> str:
    """Return 'arrival', 'mention', or 'absent' for one transcript."""
    saw_mention = False
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if marker not in line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            saw_mention = True
            continue

        message = record.get("message") or {}
        role = message.get("role")
        content = message.get("content")
        blocks = content if isinstance(content, list) else [{"text": str(content)}]

        for block in blocks:
            text = block.get("text", "") if isinstance(block, dict) else str(block)
            if marker not in text:
                continue
            # An injected additionalContext is wrapped by the host in a system
            # reminder. A user prompt quoting the marker, or an assistant turn
            # writing it, is not arrival.
            if "<system-reminder>" in text and role != "assistant":
                return "arrival"
            saw_mention = True

    return "mention" if saw_mention else "absent"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=REPO_ROOT)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    marker = _expected_marker(project_dir)
    if marker is None:
        print(
            "ERROR: templates/agent-preamble.md missing or no longer carries the "
            "uninterpolated `Phase: {{phase}}` placeholder. Without it this check "
            "cannot tell an injection from any other text.",
            file=sys.stderr,
        )
        return 2

    root = Path(os.path.expanduser("~/.claude/projects")) / _slug(project_dir)
    transcripts = sorted(root.glob("*/subagents/*.jsonl"))
    if not transcripts:
        print(f"ERROR: no sub-agent transcripts under {root}", file=sys.stderr)
        return 2

    counts = {"arrival": [], "mention": [], "absent": []}
    for path in transcripts:
        counts[_classify(path, marker)].append(path)

    total = len(transcripts)
    arrivals = len(counts["arrival"])
    mentions = len(counts["mention"])

    print(f"marker           : {marker!r}")
    print(f"transcripts      : {total}")
    print(f"genuine arrivals : {arrivals}")
    print(f"mentions (quoted or authored, NOT arrivals): {mentions}")

    if args.verbose:
        for kind in ("arrival", "mention"):
            for path in counts[kind]:
                print(f"  [{kind}] {path.parent.parent.name}/{path.name}")

    if arrivals:
        print("\nOK: the injected context reaches sub-agents.")
        return 0

    print(
        "\nFAIL: zero sub-agents received the injected context.\n"
        "  The hook emits the correct payload (see the emission tests), so the\n"
        "  loss is downstream: check `async` on the SubagentStart registration\n"
        "  in .claude/settings.json — an async hook cannot meet an insertion\n"
        "  point defined as 'before the first prompt'.\n"
        "  Contract: manifests/claude-code-hooks-schema.yaml",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
