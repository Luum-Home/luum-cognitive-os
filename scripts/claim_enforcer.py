#!/usr/bin/env python3
"""ADR-244 high-stakes completion claim enforcer.

A TRUST_REPORT with a high-stakes completion/test claim must carry a structured
`verification:` field. Shell verification is rerun in a fresh process; failures
block the completion and emit downgraded_status=partial. `verification: manual`
is allowed but audited.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

SCHEMA_VERSION = "claim-enforcer/v1"
TRIGGERS = [
    re.compile(r"\b\d+\s*(?:passed|tests? pass|tests? passing)\b", re.IGNORECASE),
    re.compile(r"\b(?:fix|fixed|closes|resolves)\s+#?\d+\b", re.IGNORECASE),
    re.compile(r"\b(?:green|all green|all passing)\b", re.IGNORECASE),
]
VERIFICATION_RE = re.compile(r"^\s*verification\s*:\s*(?P<value>.+?)\s*$", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True)
class EnforcementFinding:
    severity: str
    code: str
    message: str
    details: dict | None = None

    def to_dict(self) -> dict:
        payload = {"severity": self.severity, "code": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


def high_stakes(text: str) -> bool:
    return any(pattern.search(text) for pattern in TRIGGERS)


def extract_verification(text: str) -> str | None:
    match = VERIFICATION_RE.search(text)
    if not match:
        return None
    value = match.group("value").strip()
    if (value.startswith("`") and value.endswith("`")) or (value.startswith('"') and value.endswith('"')):
        value = value[1:-1].strip()
    return value


def _run_verification(project_dir: Path, command: str, timeout_seconds: float) -> subprocess.CompletedProcess[str]:
    # shell=True is deliberate because TRUST_REPORT verification is an operator
    # evidence string (often pipes/&&). It is not passed through from untrusted
    # external input; hooks execute inside the local repo trust boundary.
    return subprocess.run(
        command,
        cwd=str(project_dir),
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
        check=False,
    )


def evaluate(text: str, project_dir: Path, *, timeout_seconds: float = 60) -> dict:
    triggered = high_stakes(text)
    verification = extract_verification(text)
    findings: list[EnforcementFinding] = []
    status = "noop"
    downgraded_status = None
    evidence: dict = {}

    if not triggered:
        status = "noop"
    elif not verification:
        status = "block"
        downgraded_status = "partial"
        findings.append(
            EnforcementFinding(
                "block",
                "verification-field-missing",
                "High-stakes completion/test claim requires a structured verification: field.",
            )
        )
    elif verification.lower() == "manual":
        status = "manual"
        findings.append(
            EnforcementFinding(
                "warn",
                "verification-manual",
                "High-stakes claim used verification: manual; allowed but recorded for quality telemetry.",
            )
        )
    else:
        try:
            proc = _run_verification(project_dir, verification, timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            status = "block"
            downgraded_status = "partial"
            findings.append(
                EnforcementFinding(
                    "block",
                    "verification-timeout",
                    "Cited verification command timed out.",
                    {"command": verification, "timeout_seconds": timeout_seconds, "stdout": (exc.stdout or "")[:1000], "stderr": (exc.stderr or "")[:1000]},
                )
            )
        else:
            evidence = {
                "command": verification,
                "returncode": proc.returncode,
                "stdout_tail": proc.stdout[-2000:],
                "stderr_tail": proc.stderr[-2000:],
            }
            if proc.returncode == 0:
                status = "pass"
            else:
                status = "block"
                downgraded_status = "partial"
                findings.append(
                    EnforcementFinding(
                        "block",
                        "verification-command-failed",
                        "Cited verification command exited non-zero; completed claim is downgraded to partial.",
                        evidence,
                    )
                )

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "ok": status in {"noop", "pass", "manual"},
        "triggered": triggered,
        "verification": verification,
        "downgraded_status": downgraded_status,
        "findings": [finding.to_dict() for finding in findings],
        "evidence": evidence,
    }


def write_metric(project_dir: Path, report: dict) -> Path:
    metrics_dir = project_dir / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    path = metrics_dir / "claim-enforcer.jsonl"
    payload = dict(report)
    payload["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")
    return path


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ADR-244 high-stakes claim enforcer")
    parser.add_argument("--project-dir", type=Path, default=Path(os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd()))
    parser.add_argument("--response-file", type=Path)
    parser.add_argument("--text", default="")
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=float(os.environ.get("COS_CLAIM_ENFORCER_TIMEOUT_SECONDS", "60")))
    parser.add_argument("--metrics", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    text = args.text
    if args.response_file:
        text = args.response_file.read_text(encoding="utf-8", errors="replace")
    if args.stdin:
        text = sys.stdin.read()
    report = evaluate(text, args.project_dir.resolve(), timeout_seconds=args.timeout_seconds)
    if args.metrics:
        write_metric(args.project_dir.resolve(), report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"claim-enforcer: {report['status']}")
        for finding in report.get("findings", []):
            print(f"[{finding['severity']}] {finding['code']}: {finding['message']}")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
