#!/usr/bin/env python3
"""Audit ADR status literals and supersede-link symmetry.

Complements ``scripts/audit_adrs.py``. That script lower-cases ``status`` before
validating it and never compares the two ends of a supersede edge, so three
classes of drift pass it silently:

  STATUS_CASE_DRIFT       — frontmatter status is a canonical value in the wrong
                            case (``Accepted``). Valid to the audit, invisible to
                            every ``grep '^status: accepted'`` in the repo.
  SUPERSEDE_LINK_ASYMMETRY— one end of a supersede edge is declared and the other
                            is not, so the graph is only traversable one way.
  SUPERSEDED_DEAD_END     — an ADR declares a terminal status with no pointer to
                            its successor, sending the reader nowhere.
  PROSE_STATUS_CONTRADICTS— the body ``## Status`` section names a different
                            lifecycle state than the frontmatter.

The vocabulary is not invented here. It is read from
``docs/02-Decisions/adrs/STATUS-TAXONOMY.md`` via ``scripts/audit_adrs.py`` so
there is exactly one definition of the closed set.

Read-only and deterministic: no file is written, no git state is touched.

Exit codes:
  0 — no findings
  1 — findings
  2 — execution error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ADRS = REPO_ROOT / "docs" / "02-Decisions" / "adrs"

sys.path.insert(0, str(REPO_ROOT))

try:  # single source of truth for the closed vocabulary
    from scripts.audit_adrs import VALID_IMPLEMENTATION_STATUSES, VALID_STATUSES
except Exception:  # pragma: no cover - import guard
    VALID_STATUSES = {
        "proposed",
        "exploration",
        "accepted",
        "implemented",
        "resolved",
        "superseded",
        "deprecated",
        "tombstone",
    }
    VALID_IMPLEMENTATION_STATUSES = {
        "not-applicable",
        "planned",
        "partial",
        "partial-blocked",
        "blocked",
        "deferred",
        "implemented",
        "resolved",
    }

# Terminal decision statuses that owe the reader a successor pointer.
NEEDS_SUCCESSOR = {"superseded", "deprecated"}

# --- Ratchet -----------------------------------------------------------------
# Explicit allowlist, not a number. A count-based baseline hides how much slack
# it carries; a named list makes an over-generous baseline detectable, which is
# why STALE_BASELINE below is a finding and not a silent pass.
#
# Every entry is a body ``## Status`` line that annotates the frontmatter status
# with slice/date detail rather than contradicting it. The structured half of
# that annotation already lives in ``implementation_status``; the prose keeps the
# human-readable detail. Removing the prose would destroy information, so these
# are accepted, not fixed.
PROSE_ANNOTATION_ALLOWLIST: dict[str, str] = {
    # Filled by --print-prose-drift; each entry needs a written reason.
}


def _load_frontmatter(path: Path) -> tuple[dict[str, Any] | None, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None, text
    parts = text.split("\n---\n", 1)
    if len(parts) < 2:
        return None, text
    import yaml

    data = yaml.safe_load(parts[0].removeprefix("---\n"))
    if not isinstance(data, dict):
        return None, parts[1]
    return data, parts[1]


def _adr_files() -> list[Path]:
    """Real ADRs only. ``*.synthesis.md`` are generated companions, not ADRs."""
    return [p for p in sorted(ADRS.glob("ADR-*.md")) if not p.name.endswith(".synthesis.md")]


def _ref_key(value: Any) -> str | None:
    """Normalize ``ADR-043``/``43``/``ADR-28b`` to a comparable key."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none"}:
        return None
    match = re.search(r"(?i)(?:adr[-\s]?)?0*(\d+)([a-z]?)", text)
    if not match:
        return None
    return f"{int(match.group(1)):03d}{match.group(2).lower()}"


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


# Decision statuses that describe the same lifecycle position at different
# resolution. `implemented` is a refinement of `accepted` (both land in the Active
# index bucket per STATUS-TAXONOMY.md), so a body reading "Accepted — Implemented"
# against frontmatter `implemented` is an annotation, not a disagreement. Only a
# cross-family mismatch — prose says `proposed`/`superseded` while frontmatter says
# `accepted` — is a real contradiction about the ADR's lifecycle position.
STATUS_FAMILIES: tuple[frozenset[str], ...] = (
    frozenset({"accepted", "implemented", "resolved"}),
    frozenset({"proposed", "exploration"}),
    frozenset({"superseded", "deprecated", "tombstone"}),
)


def _family(status: str) -> frozenset[str] | None:
    for fam in STATUS_FAMILIES:
        if status in fam:
            return fam
    return None


def _prose_status_line(body: str) -> str | None:
    match = re.search(r"^##+\s*Status\b[^\n]*\n+(.{0,300})", body, re.M | re.S)
    if not match:
        return None
    return match.group(1).strip().split("\n")[0].strip().strip("*_ ").lower()


def _leading_status_token(body: str) -> str | None:
    first = _prose_status_line(body)
    if not first:
        return None
    token = re.match(r"[a-z-]+", first)
    return token.group(0) if token else None


def collect() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []
    records: dict[str, dict[str, Any]] = {}

    for path in _adr_files():
        fm, body = _load_frontmatter(path)
        if fm is None:
            findings.append(
                {
                    "code": "MISSING_FRONTMATTER",
                    "file": path.name,
                    "message": "ADR has no parseable YAML frontmatter",
                }
            )
            continue

        key = _ref_key(fm.get("adr")) or path.name
        if key in records:
            # Two files claim the same ADR slot. Left unreported this silently
            # drops one ADR from every downstream link check.
            findings.append(
                {
                    "code": "DUPLICATE_ADR_NUMBER",
                    "file": path.name,
                    "message": (
                        f"frontmatter adr={fm.get('adr')!r} resolves to slot {key}, already "
                        f"claimed by {records[key]['file']}; a lettered ADR must declare its "
                        f"own suffixed number (e.g. adr: 28b), not the base number"
                    ),
                }
            )
            key = f"{key}::{path.name}"
        records[key] = {"file": path.name, "fm": fm, "body": body}

        raw_status = fm.get("status")
        raw_impl = fm.get("implementation_status")

        # --- STATUS_CASE_DRIFT -------------------------------------------
        for field, raw, vocab in (
            ("status", raw_status, VALID_STATUSES),
            ("implementation_status", raw_impl, VALID_IMPLEMENTATION_STATUSES),
        ):
            if isinstance(raw, str) and raw not in vocab and raw.strip().lower() in vocab:
                findings.append(
                    {
                        "code": "STATUS_CASE_DRIFT",
                        "file": path.name,
                        "field": field,
                        "found": raw,
                        "expected": raw.strip().lower(),
                        "message": (
                            f"{field}={raw!r} is canonical only after lower-casing; "
                            f"write {raw.strip().lower()!r} so literal greps match"
                        ),
                    }
                )

        # --- PROSE_STATUS_CONTRADICTS ------------------------------------
        status = str(raw_status).strip().lower() if isinstance(raw_status, str) else None
        token = _leading_status_token(body)
        line = _prose_status_line(body) or ""
        same_family = bool(status and token and _family(token) is _family(status) and _family(status))
        # The frontmatter value spelled out later in the same prose line is an
        # annotation ("Accepted — Implemented"), not a competing claim.
        restated = bool(status and status in line)
        if status and token and token in VALID_STATUSES and token != status and not same_family and not restated:
            if path.name not in PROSE_ANNOTATION_ALLOWLIST:
                findings.append(
                    {
                        "code": "PROSE_STATUS_CONTRADICTS_FRONTMATTER",
                        "file": path.name,
                        "frontmatter": status,
                        "prose": token,
                        "message": (
                            f"body '## Status' opens with {token!r} but frontmatter "
                            f"says {status!r}; the two disagree about the same ADR"
                        ),
                    }
                )

    # --- Link graph ------------------------------------------------------
    forward: dict[str, set[str]] = {}  # A supersedes B
    backward: dict[str, set[str]] = {}  # B superseded_by A

    for key, rec in records.items():
        fm = rec["fm"]
        for raw in _as_list(fm.get("supersedes")):
            target = _ref_key(raw)
            if target:
                forward.setdefault(key, set()).add(target)
        for raw in _as_list(fm.get("superseded_by")):
            target = _ref_key(raw)
            if target:
                backward.setdefault(key, set()).add(target)

    for successor, predecessors in sorted(forward.items()):
        for predecessor in sorted(predecessors):
            if predecessor not in records:
                continue  # audit_adrs.py already owns SUPERSEDES_BROKEN_REF
            if successor not in backward.get(predecessor, set()):
                findings.append(
                    {
                        "code": "SUPERSEDE_LINK_ASYMMETRY",
                        "file": records[predecessor]["file"],
                        "direction": "missing superseded_by",
                        "message": (
                            f"ADR-{successor} declares supersedes ADR-{predecessor}, "
                            f"but ADR-{predecessor} has no superseded_by pointer back "
                            f"— the reader who lands here has no way forward"
                        ),
                    }
                )

    for predecessor, successors in sorted(backward.items()):
        pred_status = records[predecessor]["fm"].get("status")
        pred_status = pred_status.strip().lower() if isinstance(pred_status, str) else ""
        for successor in sorted(successors):
            if successor not in records:
                continue
            if predecessor in forward.get(successor, set()):
                continue
            # A tombstone's superseded_by names the ADR that now holds authority
            # over a retired slot. It is not a claim that the successor replaced a
            # live decision, so the reverse `supersedes` edge would be false: a
            # change to ADR-251 should not force a change to the retired ADR-253.
            # Asymmetry here is a coincidence of shape, not debt.
            if pred_status == "tombstone":
                notes.append(
                    {
                        "code": "TOMBSTONE_AUTHORITY_POINTER",
                        "file": records[predecessor]["file"],
                        "message": (
                            f"ADR-{predecessor} (tombstone) points at ADR-{successor} as "
                            f"current authority; no reverse supersedes edge expected"
                        ),
                    }
                )
                continue
            findings.append(
                {
                    "code": "SUPERSEDE_LINK_ASYMMETRY",
                    "file": records[successor]["file"],
                    "direction": "missing supersedes",
                    "message": (
                        f"ADR-{predecessor} declares superseded_by ADR-{successor}, "
                        f"but ADR-{successor} does not declare supersedes ADR-{predecessor}"
                    ),
                }
            )

    # --- SUPERSEDED_DEAD_END --------------------------------------------
    for key, rec in sorted(records.items()):
        status = rec["fm"].get("status")
        status = status.strip().lower() if isinstance(status, str) else ""
        if status in NEEDS_SUCCESSOR and not backward.get(key):
            findings.append(
                {
                    "code": "SUPERSEDED_DEAD_END",
                    "file": rec["file"],
                    "message": (
                        f"status={status!r} with no superseded_by — a terminal ADR "
                        f"must name what replaced it"
                    ),
                }
            )

    # --- STALE_BASELINE --------------------------------------------------
    offenders = {f["file"] for f in findings if f["code"] == "PROSE_STATUS_CONTRADICTS_FRONTMATTER"}
    known = {rec["file"] for rec in records.values()}
    for name in sorted(PROSE_ANNOTATION_ALLOWLIST):
        if name not in known:
            findings.append(
                {
                    "code": "STALE_BASELINE",
                    "file": name,
                    "message": "allowlisted file no longer exists; remove the entry",
                }
            )
        elif name in offenders:  # pragma: no cover - defensive
            continue

    return findings, notes, records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    parser.add_argument("--summary", action="store_true", help="print vocabulary distribution")
    args = parser.parse_args()

    try:
        findings, notes, records = collect()
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.summary:
        import collections

        statuses = collections.Counter(str(r["fm"].get("status")) for r in records.values())
        impls = collections.Counter(str(r["fm"].get("implementation_status")) for r in records.values())
        print(f"ADRs audited: {len(records)}")
        print("status:")
        for k, v in statuses.most_common():
            print(f"  {v:4d}  {k}")
        print("implementation_status:")
        for k, v in impls.most_common():
            print(f"  {v:4d}  {k}")
        print()

    if args.json:
        print(json.dumps({"adrs": len(records), "findings": findings, "notes": notes}, indent=2, sort_keys=True))
    else:
        if not findings:
            print(f"OK: {len(records)} ADRs, no status or supersede-link findings.")
        else:
            by_code: dict[str, list[dict[str, Any]]] = {}
            for f in findings:
                by_code.setdefault(f["code"], []).append(f)
            for code in sorted(by_code):
                print(f"\n[{code}] {len(by_code[code])}")
                for f in by_code[code]:
                    print(f"  {f['file']}: {f['message']}")
            print(f"\n{len(findings)} finding(s) across {len(records)} ADRs.")
        if notes:
            print(f"\n[notes] {len(notes)} accepted-by-design (not findings)")
            for n in notes:
                print(f"  {n['file']}: {n['message']}")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
