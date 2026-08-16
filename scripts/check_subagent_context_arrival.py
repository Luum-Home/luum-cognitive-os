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

Where the marker actually lands (measured 2026-08-15, 165 transcripts). This
harness does NOT deliver the payload as a system-reminder inside a user turn;
it writes two top-level ``type: attachment`` records per sub-agent:

  ``attachment.type == "hook_success"``             hook exited 0, stdout captured
  ``attachment.type == "hook_additional_context"``  host merged it into context

Only the second is arrival. The first is emission — it is precisely the record
an ``async: true`` registration kept producing while nothing reached any
sub-agent, so accepting it would rebuild the false green this check exists to
prevent. The system-reminder form is still accepted, for harness builds that
deliver that way.

Four false-positive sources are filtered, all observed on 2026-08-15:

  1. A brief that QUOTES the marker (an orchestrator pasting this very check
     into a sub-agent prompt). Counted as a mention, not an arrival.
  2. An assistant turn that WRITES the marker (an agent reporting on the
     template). Also a mention.
  3. A ``hook_success`` attachment — emission, see above.
  4. A ``tool_result`` block carrying the marker: an agent that RAN this script
     and read its output back. Also a mention.

Exit codes
----------
  0  at least one genuine arrival found
  1  transcripts found, zero genuine arrivals (the defect is live)
  2  error, or no transcripts to measure

Usage
-----
    python3 scripts/check_subagent_context_arrival.py [--project-dir PATH] [-v]
    python3 scripts/check_subagent_context_arrival.py --until 2026-08-15T21:58:00Z
    python3 scripts/check_subagent_context_arrival.py --since 2026-08-15T21:58:00Z

The --since/--until window filters on each transcript's first record. It exists
so a fix can be shown to have taken effect on the real corpus: red before, green
after. A change that only produces the green half has not been demonstrated.
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


def _is_arrival_attachment(record: dict, marker: str) -> bool:
    """True when the host MERGED the hook payload into this sub-agent's context.

    Claude Code records the SubagentStart hook twice, and the two records mean
    different things — telling them apart is the whole point of this check:

      ``hook_success``            the hook exited 0 and its stdout is captured
                                  verbatim. EMISSION. An ``async: true``
                                  registration produced exactly this record and
                                  nothing else: the bytes existed, the sub-agent
                                  never saw them.
      ``hook_additional_context`` the host took ``additionalContext`` and merged
                                  it into the sub-agent's context window.
                                  ARRIVAL. This is the only record that proves
                                  delivery.

    So ``hook_success`` is deliberately NOT accepted here. Accepting it would
    re-create the pre-fix false green.
    """
    attachment = record.get("attachment") or {}
    if attachment.get("type") != "hook_additional_context":
        return False
    if attachment.get("hookEvent") != "SubagentStart":
        return False
    content = attachment.get("content")
    parts = content if isinstance(content, list) else [content]
    return any(marker in str(part) for part in parts)


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

        # Form 1 (this harness, measured 2026-08-15): the injected context is a
        # top-level ``type: attachment`` record, not a message. The original
        # check only knew form 2 and therefore reported 0 arrivals on a channel
        # that was in fact delivering.
        if record.get("type") == "attachment":
            if _is_arrival_attachment(record, marker):
                return "arrival"
            saw_mention = True
            continue

        message = record.get("message") or {}
        role = message.get("role")
        content = message.get("content")
        blocks = content if isinstance(content, list) else [{"text": str(content)}]

        for block in blocks:
            if isinstance(block, dict):
                # A tool_result carrying the marker is this very script's own
                # output being read back by an agent. Never an arrival.
                if block.get("type") == "tool_result":
                    saw_mention = True
                    continue
                text = block.get("text", "")
            else:
                text = str(block)
            if marker not in text:
                continue
            # Form 2 (other harness builds): the injected additionalContext is
            # wrapped by the host in a system reminder inside a user turn. A
            # user prompt quoting the marker, or an assistant turn writing it,
            # is not arrival.
            if "<system-reminder>" in text and role != "assistant":
                return "arrival"
            saw_mention = True

    return "mention" if saw_mention else "absent"


def _first_timestamp(path: Path) -> str:
    """ISO timestamp of the transcript's first record ('' when unreadable).

    Used only by the --since/--until window, which exists so a fix can be shown
    to have taken effect: green over transcripts after it, red over transcripts
    before it. Both halves, on the same real corpus.
    """
    try:
        with path.open(encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                try:
                    stamp = json.loads(line).get("timestamp")
                except json.JSONDecodeError:
                    continue
                if stamp:
                    return str(stamp)
    except OSError:
        pass
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--since",
        default=None,
        metavar="ISO",
        help="only transcripts whose first record is at or after this UTC ISO timestamp",
    )
    parser.add_argument(
        "--until",
        default=None,
        metavar="ISO",
        help="only transcripts whose first record is before this UTC ISO timestamp",
    )
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
    if args.since or args.until:
        transcripts = [
            path
            for path in transcripts
            if (stamp := _first_timestamp(path))
            and (not args.since or stamp >= args.since)
            and (not args.until or stamp < args.until)
        ]
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
