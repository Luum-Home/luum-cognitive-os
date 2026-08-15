#!/usr/bin/env python3
# SCOPE: os-only
"""Compare two independent claim runs and surface where they disagree.

Input: two JSON files produced by `scripts/verify_claims.py --json`, each one
the output of an agent that measured the repository with its own context. The
disagreement is the product: today it only surfaced because a second session
happened to be open.

Pairing, in precedence order:
  1. `topic` — the explicit cross-run alignment key.
  2. `id` — when both runs happen to use the same slug.
  3. normalised `cmd` — two agents that ran the very same command measured the
     same thing, whatever they called it.

Verdicts:
  AGREE               both observed the same output
  DISAGREE            both measured, observed outputs differ  <- the product
  DISAGREE_CLAIM      same observed output, contradictory expectations
  INCOMPARABLE        one side errored, was blocked, or was malformed
  ONLY_A / ONLY_B     only one run measured it

Exit codes: 0 no disagreement, 1 disagreement found, 2 error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA_VERSION = "claim-run-comparison.v1"
RUNNABLE = ("REPRODUCE", "MISMATCH")
DISAGREEMENTS = ("DISAGREE", "DISAGREE_CLAIM")


def normalise_cmd(cmd: str) -> str:
    return re.sub(r"\s+", " ", cmd or "").strip()


def normalise_output(text: str) -> str:
    return re.sub(r"[ \t]+", " ", (text or "").strip())


def load_run(path: Path) -> list[dict[str, Any]]:
    """Flatten a verify_claims payload into a list of claim records."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "reports" not in payload:
        raise ValueError(f"{path}: not a verify_claims run (missing 'reports')")
    claims: list[dict[str, Any]] = []
    for report in payload["reports"]:
        for claim in report.get("claims", []):
            record = dict(claim)
            record.setdefault("source", report.get("path", path.as_posix()))
            claims.append(record)
    return claims


def _index(claims: list[dict[str, Any]]) -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
    by_topic: dict[str, dict] = {}
    by_id: dict[str, dict] = {}
    by_cmd: dict[str, dict] = {}
    for claim in claims:
        topic = (claim.get("topic") or "").strip()
        ident = (claim.get("id") or "").strip()
        cmd = normalise_cmd(claim.get("cmd", ""))
        if topic and topic not in by_topic:
            by_topic[topic] = claim
        if ident and ident not in by_id:
            by_id[ident] = claim
        if cmd and cmd not in by_cmd:
            by_cmd[cmd] = claim
    return by_topic, by_id, by_cmd


def _pair(claim: dict[str, Any], indexes: tuple[dict, dict, dict]) -> tuple[dict[str, Any] | None, str]:
    by_topic, by_id, by_cmd = indexes
    topic = (claim.get("topic") or "").strip()
    if topic and topic in by_topic:
        return by_topic[topic], "topic"
    ident = (claim.get("id") or "").strip()
    if ident and ident in by_id:
        return by_id[ident], "id"
    cmd = normalise_cmd(claim.get("cmd", ""))
    if cmd and cmd in by_cmd:
        return by_cmd[cmd], "cmd"
    return None, ""


def _label(claim: dict[str, Any]) -> str:
    return (claim.get("topic") or claim.get("id") or normalise_cmd(claim.get("cmd", ""))[:60] or "?").strip()


def compare_runs(run_a: list[dict[str, Any]], run_b: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pair the two runs' claims and score every pair."""
    index_b = _index(run_b)
    rows: list[dict[str, Any]] = []
    matched_b: set[int] = set()

    for claim in run_a:
        other, matched_by = _pair(claim, index_b)
        if other is None:
            rows.append(
                {
                    "key": _label(claim),
                    "verdict": "ONLY_A",
                    "matched_by": "",
                    "method_differs": False,
                    "a": _side(claim),
                    "b": None,
                    "note": "only run A measured this",
                }
            )
            continue
        matched_b.add(id(other))
        rows.append(_score(claim, other, matched_by))

    for claim in run_b:
        if id(claim) in matched_b:
            continue
        rows.append(
            {
                "key": _label(claim),
                "verdict": "ONLY_B",
                "matched_by": "",
                "method_differs": False,
                "a": None,
                "b": _side(claim),
                "note": "only run B measured this",
            }
        )
    return rows


def _side(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": claim.get("source", ""),
        "id": claim.get("id", ""),
        "claim": claim.get("claim", ""),
        "cmd": claim.get("cmd", ""),
        "expect": claim.get("expect", ""),
        "observed": claim.get("observed", ""),
        "status": claim.get("status", ""),
    }


def _score(a: dict[str, Any], b: dict[str, Any], matched_by: str) -> dict[str, Any]:
    method_differs = normalise_cmd(a.get("cmd", "")) != normalise_cmd(b.get("cmd", ""))
    row = {
        "key": _label(a),
        "matched_by": matched_by,
        "method_differs": method_differs,
        "a": _side(a),
        "b": _side(b),
    }
    if a.get("status") not in RUNNABLE or b.get("status") not in RUNNABLE:
        row["verdict"] = "INCOMPARABLE"
        row["note"] = f"status A={a.get('status')} B={b.get('status')}"
        return row

    observed_a = normalise_output(a.get("observed", ""))
    observed_b = normalise_output(b.get("observed", ""))
    if observed_a != observed_b:
        row["verdict"] = "DISAGREE"
        row["note"] = (
            f"observed {observed_a!r} vs {observed_b!r}"
            + (" measured with different commands" if method_differs else " with the SAME command (non-deterministic measurement)")
        )
        return row

    if normalise_output(a.get("expect", "")) != normalise_output(b.get("expect", "")):
        row["verdict"] = "DISAGREE_CLAIM"
        row["note"] = f"same observed output {observed_a!r}, contradictory expectations {a.get('expect')!r} vs {b.get('expect')!r}"
        return row

    row["verdict"] = "AGREE"
    row["note"] = (
        f"observed {observed_a!r}"
        + (" from two different commands (independent corroboration)" if method_differs else "")
    )
    return row


def _print(rows: list[dict[str, Any]], totals: dict[str, int]) -> None:
    order = {"DISAGREE": 0, "DISAGREE_CLAIM": 1, "INCOMPARABLE": 2, "ONLY_A": 3, "ONLY_B": 4, "AGREE": 5}
    for row in sorted(rows, key=lambda item: (order.get(item["verdict"], 9), item["key"])):
        print(f"[{row['verdict']:<14}] {row['key']}")
        print(f"    matched by: {row['matched_by'] or '-'}   {row['note']}")
        for side in ("a", "b"):
            data = row.get(side)
            if not data:
                continue
            print(f"    {side.upper()}: {data['source']}")
            print(f"       claim   : {data['claim']}")
            print(f"       cmd     : {data['cmd']}")
            print(f"       expect  : {data['expect']!r}   observed: {data['observed']!r}   ({data['status']})")
    print("\n-- totals --")
    for verdict in ("AGREE", "DISAGREE", "DISAGREE_CLAIM", "INCOMPARABLE", "ONLY_A", "ONLY_B"):
        print(f"   {verdict:<15}: {totals.get(verdict, 0)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare two independent verify_claims runs.")
    parser.add_argument("run_a", help="JSON produced by verify_claims --json (run A)")
    parser.add_argument("run_b", help="JSON produced by verify_claims --json (run B)")
    parser.add_argument("--json", dest="json_out", help="write the comparison to this path")
    args = parser.parse_args(argv)

    try:
        claims_a = load_run(Path(args.run_a))
        claims_b = load_run(Path(args.run_b))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rows = compare_runs(claims_a, claims_b)
    totals: dict[str, int] = {}
    for row in rows:
        totals[row["verdict"]] = totals.get(row["verdict"], 0) + 1

    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_a": Path(args.run_a).as_posix(),
        "run_b": Path(args.run_b).as_posix(),
        "totals": totals,
        "rows": rows,
    }
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    _print(rows, totals)
    return 1 if any(totals.get(verdict, 0) for verdict in DISAGREEMENTS) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(2)
