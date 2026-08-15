#!/usr/bin/env python3
"""Measure whether a memory RETRIEVAL was actually recorded — arrival, not emission.

The distinction this file exists for
------------------------------------
A test that runs ``hooks/engram-reinforce-on-access.sh`` under ``subprocess.run``
and asserts on its stdout measures EMISSION: it proves the hook parses a payload
handed to it and would write the right row. It cannot prove the row is ever
written in production, because that depends on the harness invoking the hook with
a payload of the shape the hook expects — one layer past anything a unit test
observes. On 2026-08-15 a sibling hook was measured emitting 10,253 perfect bytes
to 0 of 149 recipients with 18 tests green, for exactly this reason.

So this checks the ARTIFACT the harness caused, never the hook's output:

  ground truth   engram retrievals visible in real transcripts, with the
                 observation ids the MCP server actually returned
  measured       rows in ``.cognitive-os/metrics/lifecycle-reinforcement.jsonl``
  arrival        a ledger row whose ids were really returned by a retrieval in
                 the transcripts — the hook saw a real retrieval and recorded it

It answers ADR-342 question 4 for this hook ("Has it been seen deciding? At least
one recorded decision over a real input, not a fixture") over real data.

Why a script and not a pytest case
-----------------------------------
It reads whatever retrievals happen to have run on this machine, so it is not
deterministic and cannot be a CI gate. Same shape and same reasoning as
``scripts/check_subagent_context_arrival.py``.

What it deliberately does NOT do
---------------------------------
It does not synthesise a payload, feed it to the hook and then find its own row.
That would turn the signal green while proving nothing — the failure mode the
whole investigation was about. If you want to exercise the parser, run the hook
against ``tests/fixtures/payload-corpus/`` yourself; that is emission, and this
script will not count it.

Exit codes
----------
  0  at least one genuine arrival: a ledger row backed by a real retrieval
  1  retrievals happened and the ledger did not record them (defect live)
  2  error, or nothing to measure (no transcripts and no ledger)

Usage
-----
    python3 scripts/check_memory_retrieval_arrival.py [--project-dir PATH] [-v]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

ENGRAM_TOOLS = ("mem_search", "mem_get_observation")

# Same anchored patterns the hook uses. A bare r"#(\d+)" would also match issue
# and PR numbers quoted inside an observation's own body.
_ID_PATTERNS = (
    re.compile(r"\s*\[\d+\]\s+#(\d+)\b"),
    re.compile(r"\s*#(\d+)\s+[\[(]"),
)


def _slug(project_dir: Path) -> str:
    """Claude Code flattens a project path into a directory name.

    Both separators AND dots collapse to dashes, so this maps forward only.
    """
    return re.sub(r"[/.]", "-", str(project_dir.resolve()))


def _ids_from_result_text(text: str) -> list[str]:
    ids: list[str] = []
    for line in text.splitlines():
        for pat in _ID_PATTERNS:
            m = pat.match(line)
            if m and m.group(1) not in ids:
                ids.append(m.group(1))
                break
    return ids


def _payload_text(tur: object) -> str:
    """Pull the text out of an MCP tool response of any observed shape."""
    if isinstance(tur, list):
        return "".join(
            b.get("text", "")
            for b in tur
            if isinstance(b, dict) and isinstance(b.get("text"), str)
        )
    if isinstance(tur, str):
        return tur
    if isinstance(tur, dict):
        for key in ("text", "result"):
            if isinstance(tur.get(key), str):
                return tur[key]
    return ""


def scan_transcripts(transcript_dir: Path) -> list[dict]:
    """Every engram retrieval visible on disk, with the ids it returned."""
    events: list[dict] = []
    if not transcript_dir.is_dir():
        return events

    for tf in sorted(transcript_dir.rglob("*.jsonl")):
        try:
            lines = tf.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        # tool_use_id -> engram tool name, resolved within this transcript
        calls: dict[str, str] = {}
        for line in lines:
            if not any(t in line for t in ENGRAM_TOOLS):
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            content = (rec.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = str(block.get("name") or "")
                if any(t in name for t in ENGRAM_TOOLS):
                    calls[block.get("id")] = name

        if not calls:
            continue

        for line in lines:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            content = (rec.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                name = calls.get(block.get("tool_use_id"))
                if not name:
                    continue
                text = _payload_text(rec.get("toolUseResult"))
                project = ""
                result = text
                try:
                    inner = json.loads(text)
                    if isinstance(inner, dict):
                        project = str(inner.get("project") or "")
                        if isinstance(inner.get("result"), str):
                            result = inner["result"]
                except ValueError:
                    pass
                ids = _ids_from_result_text(result)
                events.append(
                    {
                        "tool": "mem_get_observation"
                        if "mem_get_observation" in name
                        else "mem_search",
                        "ids": ids,
                        "project": project,
                        "timestamp": rec.get("timestamp") or "",
                        "miss": bool(
                            re.search(r"No memories found|Found 0 memories", result)
                        ),
                    }
                )
    return events


def read_ledger(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-dir", default=str(REPO_ROOT))
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    project_dir = Path(args.project_dir).resolve()
    ledger_path = project_dir / ".cognitive-os" / "metrics" / "lifecycle-reinforcement.jsonl"
    transcript_dir = Path.home() / ".claude" / "projects" / _slug(project_dir)

    events = scan_transcripts(transcript_dir)
    rows = read_ledger(ledger_path)

    # ids the harness really returned, from transcripts only
    real_ids = {i for e in events for i in e["ids"]}
    hits = [e for e in events if e["ids"]]
    misses = [e for e in events if e["miss"]]

    print(f"transcript dir : {transcript_dir.name}")
    print(f"retrievals seen: {len(events)}  (hits {len(hits)}, stated misses {len(misses)})")
    print(f"ledger         : {'present' if ledger_path.is_file() else 'ABSENT'}  rows={len(rows)}")

    if not events and not rows:
        print("VERDICT: nothing to measure — no engram retrievals on record here.")
        return 2

    ledger_ids = {str(i) for r in rows for i in (r.get("observation_ids") or [])}
    corroborated = sorted(ledger_ids & real_ids)
    unbacked = sorted(ledger_ids - real_ids)

    if args.verbose:
        if hits:
            last = hits[-1]
            print(f"  last real hit : {last['timestamp']} {last['tool']} ids={last['ids']}")
        print(f"  ledger ids    : {sorted(ledger_ids) or '[]'}")
        print(f"  corroborated  : {corroborated or '[]'}")
        if unbacked:
            print(f"  UNBACKED      : {unbacked}  (rows no transcript retrieval explains)")

    if corroborated:
        print(
            f"VERDICT: ARRIVES — {len(corroborated)} observation id(s) present in both a real "
            "retrieval and the ledger. ADR-342 Q4 satisfied for this hook."
        )
        return 0

    if rows and not real_ids:
        # Rows exist but no transcript corroborates them. Either the transcripts
        # were rotated away, or the rows were manufactured. Not an arrival.
        print(
            "VERDICT: UNCORROBORATED — ledger has rows but no transcript retrieval "
            "backs them. Do not count as coverage."
        )
        return 1

    print(
        f"VERDICT: DOES NOT ARRIVE — {len(events)} real retrieval(s) on record, "
        f"{len(rows)} ledger row(s) corroborated by them. The hook is not recording "
        "what the harness retrieves."
    )
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(2)
    except Exception as exc:  # noqa: BLE001 — a checker must not traceback at operators
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
