#!/usr/bin/env python3
# SCOPE: os-only
"""Gate: a declared omission must carry a date and an owner, and the date must hold.

Read-only. Deterministic. Never mutates registration.

    .venv/bin/python3 scripts/audit_omission_expiry.py
    .venv/bin/python3 scripts/audit_omission_expiry.py --json
    .venv/bin/python3 scripts/audit_omission_expiry.py --as-of 2027-01-01

Exit codes:
    0 -- every row has owner+expires, no row is overdue
    1 -- at least one row is overdue, or a row violates the schema
    2 -- error: manifest missing, unparseable, or ZERO rows parsed

Why exit 2 on zero rows: a checker that walks an empty list exits green exactly
like a healthy one. A typo in a path, a `entries: []` left by a bad edit, a
renamed key -- all of those silently turn this gate into a no-op that reports
success forever. Zero rows is a broken instrument, not a clean bill of health.

WHAT THIS DOES NOT DO: it does not unregister, demote, disable or delete
anything when a date passes. An automaton that switches hooks off by calendar
is an incident with a cron entry. This reports; a person acts.

Two ledgers, one mechanism:
  * manifests/hook-registration-classification.yaml -- hooks ABSENT from
    .claude/settings.json with a declared reason. `expires: never` is legal
    only for statuses whose absence is structural (see PERMANENT_STATUSES);
    on any other status `never` is a schema violation, which is what stops
    "just write never" from being the cheap green.
  * manifests/gate-instrumentation-ultimatum.yaml -- gates that ARE registered
    but whose blocking exit nobody has ever seen taken. Every row carries a
    real date; `never` is never legal here.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

CLASSIFICATION = "manifests/hook-registration-classification.yaml"
ULTIMATUM = "manifests/gate-instrumentation-ultimatum.yaml"

SCHEMA_VERSION = "omission-expiry-audit/v1"

# Absence from .claude/settings.json is STRUCTURAL for these statuses: the hook
# is registered, is registered on another harness/profile, or is not the kind of
# hook a session registers at all. Only these may say `expires: never`.
PERMANENT_STATUSES = frozenset(
    {
        "active",
        "internal_helper",
        "projected_elsewhere",
        "git_or_manual",
        "manual_trigger",
        "profile_scoped",
    }
)

DUE_SOON_DAYS = 14


class AuditError(RuntimeError):
    """Raised for the exit-2 contract: the instrument itself is broken."""


def _load(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    if not path.is_file():
        raise AuditError(f"{rel}: manifest not found at {path}")
    try:
        # yaml.safe_load parses JSON too -- hook-registration-classification.yaml
        # has a .yaml extension over JSON content.
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - surfaced as exit 2
        raise AuditError(f"{rel}: unparseable ({exc})") from exc
    if not isinstance(data, dict):
        raise AuditError(f"{rel}: top level is {type(data).__name__}, expected a mapping")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise AuditError(f"{rel}: 'entries' is {type(entries).__name__}, expected a list")
    if not entries:
        raise AuditError(f"{rel}: ZERO entries parsed -- a gate over an empty list is a no-op")
    data["entries"] = entries
    return data


def _parse_date(value: Any) -> dt.date | None:
    if not isinstance(value, str):
        return None
    try:
        return dt.date.fromisoformat(value.strip())
    except ValueError:
        return None


def _finding(severity: str, code: str, message: str, stable_id: str, **details: Any) -> dict[str, Any]:
    item = {"severity": severity, "code": code, "message": message, "stable_id": stable_id}
    if details:
        item["details"] = details
    return item


def _check_row(
    *,
    ledger: str,
    key: str,
    row: dict[str, Any],
    as_of: dt.date,
    never_allowed: bool,
    status: str | None,
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    sid_base = f"omission-expiry/{ledger}/{key}"

    owner = row.get("owner")
    if not isinstance(owner, str) or not owner.strip():
        found.append(
            _finding(
                "warn",
                "omission-owner-missing",
                f"{ledger}: {key} has no owner field. An unowned exception is nobody's to cash.",
                f"{sid_base}/owner-missing",
                ledger=ledger,
                entry=key,
            )
        )

    raw = row.get("expires")
    if not isinstance(raw, str) or not raw.strip():
        found.append(
            _finding(
                "warn",
                "omission-expires-missing",
                f"{ledger}: {key} has no expires field. An exception without a date is a permanent decision.",
                f"{sid_base}/expires-missing",
                ledger=ledger,
                entry=key,
            )
        )
        return found

    value = raw.strip()
    if value == "never":
        if not never_allowed:
            found.append(
                _finding(
                    "warn",
                    "omission-never-not-allowed",
                    f"{ledger}: {key} claims expires: never, but status {status!r} is a deferred "
                    f"decision, not a structural absence. Give it a date or change the status.",
                    f"{sid_base}/never-not-allowed",
                    ledger=ledger,
                    entry=key,
                    status=status,
                )
            )
        return found

    when = _parse_date(value)
    if when is None:
        found.append(
            _finding(
                "warn",
                "omission-expires-malformed",
                f"{ledger}: {key} has expires={value!r}, which is neither an ISO date nor 'never'.",
                f"{sid_base}/expires-malformed",
                ledger=ledger,
                entry=key,
                expires=value,
            )
        )
        return found

    if when < as_of:
        found.append(
            _finding(
                "warn",
                "omission-expired",
                f"{ledger}: {key} expired on {value} ({(as_of - when).days}d ago). "
                f"Owner: {row.get('owner', 'unassigned')}. Next action on record: "
                f"{str(row.get('next_action', '(none)'))[:160]}",
                f"{sid_base}/expired",
                ledger=ledger,
                entry=key,
                expires=value,
                days_overdue=(as_of - when).days,
                owner=row.get("owner"),
            )
        )
    elif (when - as_of).days <= DUE_SOON_DAYS:
        found.append(
            _finding(
                "warn",
                "omission-due-soon",
                f"{ledger}: {key} comes due on {value} (in {(when - as_of).days}d).",
                f"{sid_base}/due-soon",
                ledger=ledger,
                entry=key,
                expires=value,
                days_remaining=(when - as_of).days,
            )
        )
    return found


def audit(root: Path, as_of: dt.date) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    counts = {
        "rows": 0,
        "expired": 0,
        "due_soon": 0,
        "never": 0,
        "unassigned_owner": 0,
        "schema_violations": 0,
    }

    classification = _load(root, CLASSIFICATION)
    for row in classification["entries"]:
        if not isinstance(row, dict):
            raise AuditError(f"{CLASSIFICATION}: entry is {type(row).__name__}, expected a mapping")
        key = str(row.get("path") or "(no path)")
        status = row.get("status")
        counts["rows"] += 1
        if str(row.get("expires", "")).strip() == "never":
            counts["never"] += 1
        if str(row.get("owner", "")).strip() in ("", "unassigned"):
            counts["unassigned_owner"] += 1
        findings.extend(
            _check_row(
                ledger="hook-registration-classification",
                key=key,
                row=row,
                as_of=as_of,
                never_allowed=status in PERMANENT_STATUSES,
                status=status if isinstance(status, str) else None,
            )
        )

    ultimatum = _load(root, ULTIMATUM)
    for row in ultimatum["entries"]:
        if not isinstance(row, dict):
            raise AuditError(f"{ULTIMATUM}: entry is {type(row).__name__}, expected a mapping")
        key = str(row.get("gate") or row.get("path") or "(no gate)")
        counts["rows"] += 1
        if str(row.get("owner", "")).strip() in ("", "unassigned"):
            counts["unassigned_owner"] += 1
        findings.extend(
            _check_row(
                ledger="gate-instrumentation-ultimatum",
                key=key,
                row=row,
                as_of=as_of,
                never_allowed=False,
                status=None,
            )
        )

    for item in findings:
        code = item["code"]
        if code == "omission-expired":
            counts["expired"] += 1
        elif code == "omission-due-soon":
            counts["due_soon"] += 1
        else:
            counts["schema_violations"] += 1

    # `owner: unassigned` is deliberately a COUNT, not a finding. Every row is
    # unassigned today, so emitting it as a finding would paint the control-plane
    # lane yellow from birth -- and a gate that is yellow on day one is a gate
    # everyone learns to scroll past. Backfilling 124 real owners is an operator
    # pass, not something this audit can nag into existence. The count is printed
    # on every run and carried in JSON so it cannot hide.
    return {
        "schema_version": SCHEMA_VERSION,
        "as_of": as_of.isoformat(),
        "counts": counts,
        "summary": {
            "block": 0,
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
            "findings": len(findings),
        },
        "findings": findings,
        "action_on_expiry": (
            "REPORT ONLY. Nothing is unregistered, demoted or deleted because a date passed. "
            "A person renews the row with a written reason, promotes the hook, or removes it."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        default=str(REPO_ROOT),
        help="project root (default: the repo this script lives in, not the cwd)",
    )
    parser.add_argument(
        "--as-of",
        default=None,
        help="evaluate against this ISO date instead of today (for drills and counterfactuals)",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    if args.as_of:
        as_of = _parse_date(args.as_of)
        if as_of is None:
            print(f"audit_omission_expiry: ERROR: --as-of {args.as_of!r} is not an ISO date", file=sys.stderr)
            return 2
    else:
        as_of = dt.date.today()

    try:
        report = audit(Path(args.root), as_of)
    except AuditError as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "summary": {"block": 1, "warn": 0, "findings": 1},
                        "findings": [
                            _finding(
                                "block",
                                "omission-expiry-audit-broken",
                                str(exc),
                                "omission-expiry/audit-broken",
                            )
                        ],
                    },
                    indent=2,
                )
            )
        else:
            print(f"audit_omission_expiry: ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - exit 2 is the error contract
        print(f"audit_omission_expiry: ERROR: {exc}", file=sys.stderr)
        return 2

    counts = report["counts"]
    bad = counts["expired"] + counts["schema_violations"]

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=False))
        return 1 if bad else 0

    print("=== DECLARED-OMISSION EXPIRY AUDIT ===")
    print(f"as-of: {report['as_of']}  rows: {counts['rows']}")
    print(
        f"expired={counts['expired']} due-soon(<={DUE_SOON_DAYS}d)={counts['due_soon']} "
        f"schema-violations={counts['schema_violations']} "
        f"never={counts['never']} owner-unassigned={counts['unassigned_owner']}"
    )
    for item in report["findings"]:
        if item["code"] in ("omission-expired", "omission-due-soon"):
            continue
        print(f"  SCHEMA  {item['message']}")
    for item in report["findings"]:
        if item["code"] == "omission-expired":
            print(f"  EXPIRED {item['message']}")
    for item in report["findings"]:
        if item["code"] == "omission-due-soon":
            print(f"  SOON    {item['message']}")

    if not bad:
        print("\nOK: every declared omission carries an owner and a date that still holds.")
        return 0

    print(
        "\nFAIL - fix by RENEWING the row (new date + owner + why), promoting the hook, "
        "or removing it. This audit never changes registration on its own."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
