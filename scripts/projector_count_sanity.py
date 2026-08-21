#!/usr/bin/env python3
# SCOPE: os-only
"""Counterfactual gate over the ADR-275 session-start projector counts.

Every number the projector prints heads the session brief. This gate asserts
that each one stays inside the universe its LABEL promises, by recomputing
that universe from the SOURCE (never from the projector's own report):

  control_plane.open_findings   <= distinct findings in the remediation log
                                   (the log is append-only proposals; its ROW
                                    count is not a finding count)
  pending_truth.total/open      == rows / verified-pending rows in the ledger
  operational_guide.total_p0/p1 must be null when the source carries no
                                   `priority` field (a zero there measures the
                                    missing field, not an empty backlog)
  adr_partials.total            == items in the backlog report
  staged_deployments            == directories matching *staging* on disk

Severity: a count ABOVE its universe is impossible (`red`); at or above 10x the
universe it is off by an order of magnitude (`red`, code `order-of-magnitude`).
A count that is null with a stated reason is ACCEPTED — "I cannot count the
open ones" is a valid answer; a row count wearing an open-findings label is not.

Usage:
  scripts/projector_count_sanity.py                       # run projector, check
  scripts/projector_count_sanity.py --projection FILE     # check a stored payload
  scripts/projector_count_sanity.py --project-dir PATH --json

Exit codes: 0 = no findings, 1 = findings, 2 = error.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PROJECTOR = SCRIPT_DIR / "cos-session-start-projector"
ORDER_OF_MAGNITUDE = 10


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return out
    return out


def run_projector(project_dir: Path) -> dict[str, Any]:
    env = os.environ.copy()
    env["COS_PROJECTOR_NOCACHE"] = "1"
    cp = subprocess.run(
        [sys.executable, str(PROJECTOR), "--project-dir", str(project_dir), "--json"],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"projector failed rc={cp.returncode}: {cp.stderr[:400]}")
    return json.loads(cp.stdout)


def universes(root: Path) -> dict[str, Any]:
    """Independently recompute, from the sources, what each label may span."""
    queue = _load_jsonl(root / ".cognitive-os/tasks/control-plane-remediation.jsonl")
    distinct = {str(e.get("stable_id")) for e in queue if e.get("stable_id")}
    state = _load_json(root / ".cognitive-os/runtime/control-plane-audit/findings-state.json")
    findings = state.get("findings") if isinstance(state.get("findings"), dict) else {}

    pt = _load_json(root / "docs/06-Daily/reports/pending-truth-latest.json")
    pt_items = pt.get("items", []) or []
    og = _load_json(root / "docs/06-Daily/reports/operational-guide-audit-latest.json")
    og_results = og.get("results", []) or []
    ap = _load_json(root / "docs/06-Daily/reports/adr-partial-backlog-latest.json")
    ap_items = ap.get("items", []) or []

    runbooks = root / "docs/05-Methodology/runbooks"
    staged = 0
    if runbooks.is_dir():
        staged = sum(
            1
            for p in runbooks.iterdir()
            if p.is_dir() and (p.name.endswith("-staging") or "staging" in p.name.lower())
        )
    return {
        "cp_distinct_findings": len(distinct),
        "cp_queue_rows": len(queue),
        "cp_tracked": len(findings),
        "pt_items": len(pt_items),
        "pt_pending": sum(1 for i in pt_items if i.get("status") == "verified-pending"),
        "og_results": len(og_results),
        "og_priced": sum(1 for r in og_results if r.get("priority")),
        "ap_items": len(ap_items),
        "staged_dirs": staged,
    }


def _bound(findings: list[dict[str, Any]], label: str, reported: Any, universe: int, universe_label: str) -> None:
    """A count may never exceed the universe its label names."""
    if reported is None or not isinstance(reported, int):
        return
    if universe <= 0:
        if reported > 0:
            findings.append({
                "severity": "red",
                "code": "count-without-universe",
                "label": label,
                "reported": reported,
                "universe": universe,
                "message": f"{label}={reported} but {universe_label} is 0",
            })
        return
    if reported >= ORDER_OF_MAGNITUDE * universe:
        findings.append({
            "severity": "red",
            "code": "order-of-magnitude",
            "label": label,
            "reported": reported,
            "universe": universe,
            "ratio": round(reported / universe, 2),
            "message": (
                f"{label}={reported} is {reported / universe:.1f}x {universe_label}={universe}; "
                "the number cannot mean what the label says"
            ),
        })
    elif reported > universe:
        findings.append({
            "severity": "red",
            "code": "exceeds-universe",
            "label": label,
            "reported": reported,
            "universe": universe,
            "message": f"{label}={reported} exceeds {universe_label}={universe}",
        })


def check(payload: dict[str, Any], u: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    sections = payload.get("sections", {}) or {}

    cp = sections.get("control_plane", {}) or {}
    open_findings = cp.get("open_findings")
    if open_findings is None:
        if not cp.get("unknown_reason"):
            findings.append({
                "severity": "red",
                "code": "silent-null",
                "label": "control_plane.open_findings",
                "reported": None,
                "message": "count is null with no unknown_reason; unknowable must be stated, not blank",
            })
    else:
        _bound(findings, "control_plane.open_findings", open_findings,
               int(u["cp_distinct_findings"]), "distinct findings in the remediation log")
        if u["cp_tracked"]:
            _bound(findings, "control_plane.open_findings", open_findings,
                   int(u["cp_tracked"]), "findings tracked by the audit state machine")

    pt = sections.get("pending_truth", {}) or {}
    if pt.get("total") != u["pt_items"]:
        findings.append({
            "severity": "red",
            "code": "mismatch",
            "label": "pending_truth.total",
            "reported": pt.get("total"),
            "universe": u["pt_items"],
            "message": f"pending_truth.total={pt.get('total')} but ledger has {u['pt_items']} items",
        })
    if pt.get("open") is not None:
        _bound(findings, "pending_truth.open", pt.get("open"), int(u["pt_items"]), "ledger items")
        if pt.get("open") != u["pt_pending"]:
            findings.append({
                "severity": "red",
                "code": "mismatch",
                "label": "pending_truth.open",
                "reported": pt.get("open"),
                "universe": u["pt_pending"],
                "message": f"pending_truth.open={pt.get('open')} but ledger has {u['pt_pending']} verified-pending",
            })

    og = sections.get("operational_guide", {}) or {}
    if u["og_results"] and not u["og_priced"]:
        if og.get("total_p0") is not None or og.get("total_p1") is not None:
            findings.append({
                "severity": "red",
                "code": "false-zero",
                "label": "operational_guide.total_p0/p1",
                "reported": [og.get("total_p0"), og.get("total_p1")],
                "universe": u["og_results"],
                "message": (
                    f"source has {u['og_results']} results and no `priority` field on any of them; "
                    "reporting a number counts the missing field, not the backlog"
                ),
            })
    else:
        _bound(findings, "operational_guide.total_p0", og.get("total_p0"), int(u["og_results"]), "audited ADRs")
        _bound(findings, "operational_guide.total_p1", og.get("total_p1"), int(u["og_results"]), "audited ADRs")

    ap = sections.get("adr_partials", {}) or {}
    _bound(findings, "adr_partials.total", ap.get("total"), max(int(u["ap_items"]), 0), "backlog report items")
    if u["ap_items"] and ap.get("total") != u["ap_items"]:
        findings.append({
            "severity": "red",
            "code": "mismatch",
            "label": "adr_partials.total",
            "reported": ap.get("total"),
            "universe": u["ap_items"],
            "message": f"adr_partials.total={ap.get('total')} but report has {u['ap_items']} items",
        })

    st = sections.get("staged_deployments", {}) or {}
    dirs = st.get("dirs", []) or []
    if len(dirs) != u["staged_dirs"]:
        findings.append({
            "severity": "red",
            "code": "mismatch",
            "label": "staged_deployments.dirs",
            "reported": len(dirs),
            "universe": u["staged_dirs"],
            "message": f"projector lists {len(dirs)} staging dirs but disk has {u['staged_dirs']}",
        })
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Sanity-gate the session-start projector counts")
    ap.add_argument("--project-dir", default=None, help="repo root to audit (default: this script's repo)")
    ap.add_argument("--projection", default=None, help="check a stored projection JSON instead of running the projector")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    root = Path(args.project_dir).resolve() if args.project_dir else REPO_ROOT
    try:
        if args.projection:
            payload = _load_json(Path(args.projection).resolve())
            if not payload:
                print(f"ERROR: unreadable projection {args.projection}", file=sys.stderr)
                return 2
        else:
            payload = run_projector(root)
        u = universes(root)
        findings = check(payload, u)
    except Exception as exc:  # noqa: BLE001 - gate must report, not traceback
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({
            "schema_version": "projector-count-sanity/v1",
            "project_dir": "<repo-root>",
            "universes": u,
            "findings": findings,
            "status": "fail" if findings else "pass",
        }, indent=2))
    else:
        print(f"projector-count-sanity: {'FAIL' if findings else 'PASS'} ({len(findings)} finding(s))")
        for f in findings:
            print(f"  [{f['severity']}] {f['code']}: {f['message']}")
        if not findings:
            print(f"  universes: {json.dumps(u)}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
