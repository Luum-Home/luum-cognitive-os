#!/usr/bin/env python3
# SCOPE: both
"""Gate the headless self-improvement loop against default-surface inflation."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_ACTION_PATTERNS = (
    re.compile(r"\bauto[_-]?merge\b", re.IGNORECASE),
    re.compile(r"\bauto[_-]?promote\b", re.IGNORECASE),
    re.compile(r"\bpromote[_-]?(to[_-]?)?(core|team)\b", re.IGNORECASE),
    re.compile(r"\badd[_-]?(to[_-]?)?(core|team)\b", re.IGNORECASE),
    re.compile(r"\bexpand[_-]?default\b", re.IGNORECASE),
    re.compile(r"\bextend[_-]?warning[_-]?budget\b", re.IGNORECASE),
    re.compile(r"\binvent[_-]?roi\b", re.IGNORECASE),
)
CONTROL_ACTION_KEYWORDS = (
    "demote",
    "defer",
    "classify",
    "refine",
    "evidence",
    "collect",
    "import",
    "request",
    "document",
)


@dataclass(frozen=True)
class Finding:
    id: str
    severity: str
    message: str
    proposal: str | None = None


def _load_plan(project_root: Path, profile: str) -> dict[str, Any]:
    result = subprocess.run(
        ["scripts/cos-self-improvement-loop", "--profile", profile, "--json"],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return {
            "status": "fail",
            "proposal_count": 0,
            "proposals": [],
            "error": result.stderr[-2000:],
        }
    return json.loads(result.stdout)


def _has_forbidden_action(value: str) -> bool:
    return any(pattern.search(value) for pattern in FORBIDDEN_ACTION_PATTERNS)


def evaluate_plan(plan: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    policy = plan.get("policy", {})
    if policy.get("auto_merge") is not False:
        findings.append(
            Finding(
                id="auto-merge-policy-open",
                severity="fail",
                message="self-improvement loop must keep auto_merge=false",
            )
        )
    if policy.get("auto_promote_core_or_team") is not False:
        findings.append(
            Finding(
                id="auto-promote-policy-open",
                severity="fail",
                message="self-improvement loop must keep auto_promote_core_or_team=false",
            )
        )
    if policy.get("human_approval_required") is not True:
        findings.append(
            Finding(
                id="human-approval-policy-missing",
                severity="fail",
                message="self-improvement loop must require human approval",
            )
        )

    proposals = plan.get("proposals", [])
    if not isinstance(proposals, list):
        return findings + [
            Finding(
                id="proposal-list-invalid",
                severity="fail",
                message="self-improvement plan proposals must be a list",
            )
        ]

    control_like = 0
    for proposal in proposals:
        if not isinstance(proposal, dict):
            findings.append(
                Finding(
                    id="proposal-invalid",
                    severity="fail",
                    message="proposal entries must be objects",
                )
            )
            continue
        finding_id = str(proposal.get("finding_id", "<unknown>"))
        action = str(proposal.get("candidate_action", ""))
        summary = str(proposal.get("summary", ""))
        blocked_actions = proposal.get("blocked_actions", [])
        allowed_write_paths = proposal.get("allowed_write_paths", [])

        if proposal.get("human_approval_required") is not True:
            findings.append(
                Finding(
                    id="proposal-human-approval-missing",
                    severity="fail",
                    message="every self-improvement proposal must require human approval",
                    proposal=finding_id,
                )
            )
        if proposal.get("reversible") is not True:
            findings.append(
                Finding(
                    id="proposal-reversibility-missing",
                    severity="fail",
                    message="every self-improvement proposal must declare reversible=true",
                    proposal=finding_id,
                )
            )
        if _has_forbidden_action(" ".join([action, summary])):
            findings.append(
                Finding(
                    id="proposal-default-surface-expansion",
                    severity="fail",
                    message="proposal appears to expand/promote default surface instead of preserving lab-first discipline",
                    proposal=finding_id,
                )
            )
        for required in ("auto_merge", "auto_promote_core_or_team", "invent_roi_evidence"):
            if required not in blocked_actions:
                findings.append(
                    Finding(
                        id="proposal-blocked-action-missing",
                        severity="fail",
                        message=f"proposal must explicitly block {required}",
                        proposal=finding_id,
                    )
                )
        if any(str(path).startswith(("hooks/", "rules/", "skills/")) for path in allowed_write_paths):
            findings.append(
                Finding(
                    id="proposal-runtime-write-path",
                    severity="fail",
                    message="proposal allowed_write_paths must not include live runtime surfaces directly",
                    proposal=finding_id,
                )
            )
        if any(keyword in action for keyword in CONTROL_ACTION_KEYWORDS):
            control_like += 1

    if proposals and control_like / len(proposals) < 0.5:
        findings.append(
            Finding(
                id="proposal-control-ratio-low",
                severity="warn",
                message="less than half of proposals are classify/refine/demote/defer/evidence/control oriented",
            )
        )
    return findings


def build_report(project_root: Path = REPO_ROOT, profile: str = "core") -> dict[str, Any]:
    plan = _load_plan(project_root, profile)
    findings = evaluate_plan(plan)
    fail_count = sum(1 for finding in findings if finding.severity == "fail")
    warn_count = sum(1 for finding in findings if finding.severity == "warn")
    return {
        "status": "fail" if fail_count else ("warn" if warn_count else "pass"),
        "profile": profile,
        "proposal_count": plan.get("proposal_count", 0),
        "findings": [asdict(finding) for finding in findings],
        "fail_count": fail_count,
        "warn_count": warn_count,
        "policy": "self-improvement proposals must preserve lab-first, approval-required, reversible growth discipline",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=REPO_ROOT)
    parser.add_argument("--profile", choices=["core", "team", "maintainer", "lab"], default="core")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-warn", action="store_true")
    args = parser.parse_args(argv)

    report = build_report(args.project_dir.resolve(), args.profile)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            f"self-improvement-discipline-gate: {report['status']} "
            f"proposals={report['proposal_count']} fail={report['fail_count']} warn={report['warn_count']}"
        )
        for finding in report["findings"]:
            suffix = f" ({finding['proposal']})" if finding.get("proposal") else ""
            print(f"- {finding['severity'].upper()} {finding['id']}{suffix}: {finding['message']}")

    if report["status"] == "fail":
        return 1
    if args.fail_on_warn and report["status"] == "warn":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
