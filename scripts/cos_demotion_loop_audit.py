#!/usr/bin/env python3
# SCOPE: both
"""Audit whether ADR-126 demotion has become a loop, not a one-off proof.

The first demotion can be a semantic proof. The second demotion, especially one
signed primarily by governance ROI, proves the lifecycle governor is operating as
a control loop rather than as a showcase commit.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "manifests" / "primitive-lifecycle.yaml"
ROI_WARNING_BUDGET_DAYS = 30


@dataclass(frozen=True)
class DemotionRecord:
    primitive_id: str
    reason: str
    primary_signal: str
    roi_signed: bool
    demoted_on: str | None = None


@dataclass(frozen=True)
class Finding:
    id: str
    severity: str
    message: str


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError("primitive lifecycle manifest must be a mapping")
    return loaded


def _demotion_evidence(primitive: dict[str, Any]) -> dict[str, Any]:
    evidence = primitive.get("demotion_evidence")
    return evidence if isinstance(evidence, dict) else {}


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def demotion_records(manifest: dict[str, Any]) -> list[DemotionRecord]:
    primitives = manifest.get("primitives")
    if not isinstance(primitives, list):
        return []
    records: list[DemotionRecord] = []
    for primitive in primitives:
        if not isinstance(primitive, dict) or primitive.get("lifecycle_state") != "demoted":
            continue
        evidence = _demotion_evidence(primitive)
        primary_signal = str(evidence.get("primary_signal") or "unknown")
        commands = " ".join(str(item) for item in evidence.get("control_plane_commands", []) if item)
        reason = str(evidence.get("reason") or primitive.get("sunset_criteria") or "")
        roi_signed = primary_signal == "governance-roi" or "cos-governance-roi" in commands or "cos-boring-reliability" in commands and "ROI" in reason.upper()
        records.append(
            DemotionRecord(
                primitive_id=str(primitive.get("id") or "<unknown>"),
                reason=reason,
                primary_signal=primary_signal,
                roi_signed=roi_signed,
                demoted_on=str(evidence.get("demoted_on")) if evidence.get("demoted_on") else None,
            )
        )
    return sorted(records, key=lambda item: item.primitive_id)


def _second_demotion_date(records: list[DemotionRecord]) -> date | None:
    dates = sorted(parsed for record in records if (parsed := _parse_date(record.demoted_on)) is not None)
    return dates[1] if len(dates) >= 2 else None


def build_report(manifest_path: Path = MANIFEST, *, today: date | None = None) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    records = demotion_records(manifest)
    roi_signed = [record for record in records if record.roi_signed]
    findings: list[Finding] = []
    today = today or date.today()
    if len(records) < 2:
        findings.append(
            Finding(
                id="second-demotion-missing",
                severity="warn",
                message="ADR-126 has only one semantic demotion; the lifecycle governor is not yet proven as a repeated control loop.",
            )
        )
    if not roi_signed:
        roi_warning_open_since = _second_demotion_date(records)
        roi_warning_age_days = (today - roi_warning_open_since).days if roi_warning_open_since else None
        roi_warning_expired = roi_warning_age_days is not None and roi_warning_age_days >= ROI_WARNING_BUDGET_DAYS
        findings.append(
            Finding(
                id="roi-signed-demotion-missing",
                severity="fail" if roi_warning_expired else "warn",
                message=(
                    "No demotion records governance ROI as the primary signing signal; ROI dashboard remains an instrument, not a decision knife. "
                    f"The warning budget expired after {roi_warning_age_days} days without ROI-signed demotion."
                    if roi_warning_expired
                    else "No demotion records governance ROI as the primary signing signal; ROI dashboard remains an instrument, not a decision knife."
                ),
            )
        )
    has_failures = any(finding.severity == "fail" for finding in findings)
    status = "fail" if has_failures else ("pass" if not findings else "warn")
    return {
        "status": status,
        "manifest": str(manifest_path),
        "today": today.isoformat(),
        "demotion_count": len(records),
        "roi_signed_demotion_count": len(roi_signed),
        "demotions": [asdict(record) for record in records],
        "finding_count": len(findings),
        "findings": [asdict(finding) for finding in findings],
        "roi_warning_budget_days": ROI_WARNING_BUDGET_DAYS,
        "roi_warning_open_since": _second_demotion_date(records).isoformat() if _second_demotion_date(records) else None,
        "roi_warning_age_days": (
            (today - second).days if (second := _second_demotion_date(records)) is not None and not roi_signed else None
        ),
        "policy": "ADR-126 is mature when at least two demotions exist and at least one is primarily ROI-signed.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--today", type=lambda raw: date.fromisoformat(raw), default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.manifest.resolve(), today=args.today)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"demotion-loop-audit: {report['status']} demotions={report['demotion_count']} roi_signed={report['roi_signed_demotion_count']}")
        for finding in report["findings"]:
            print(f"- [{finding['severity']}] {finding['id']}: {finding['message']}")
    if args.fail_on_findings and report["finding_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
