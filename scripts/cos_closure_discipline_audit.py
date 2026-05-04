#!/usr/bin/env python3
# SCOPE: os-only
"""Audit closure-discipline surfaces that commonly drift after fast agent batches.

This is a structural closure gate, not a substitute for running the relevant test
lane. It catches stale tests/gates that let agents claim local success while the
broader validation nervous system is no longer aligned with repository reality.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

WORKFLOW_REF_RE = re.compile(r"\.github/workflows/([A-Za-z0-9_.-]+\.ya?ml)\b")
HARDCODED_HOOK_COUNT_RE = re.compile(r"len\s*\(\s*projected\s*\)\s*==\s*\d+")
HARDCODED_HOOK_TEST_NAME_RE = re.compile(r"currently_project_\d+_unique_hooks")
CAPSULE_FALLBACK_MARKER = "COS_VALIDATION_CAPSULE_SAFE_WORKTREE_FALLBACK"


@dataclass(frozen=True)
class Finding:
    id: str
    severity: str
    path: str
    message: str
    repair: str


def iter_text_files(root: Path, dirs: Iterable[str]) -> Iterable[Path]:
    for dirname in dirs:
        base = root / dirname
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in {".py", ".sh", ".md", ".yaml", ".yml"}:
                continue
            if "__pycache__" in path.parts:
                continue
            if path.name == "test_closure_discipline_audit.py":
                continue
            yield path


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def audit_disabled_workflow_references(root: Path) -> list[Finding]:
    """Fail tests/scripts that reference active workflow names after ADR-130 suspension."""
    findings: list[Finding] = []
    for path in iter_text_files(root, ["tests", "scripts"]):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in WORKFLOW_REF_RE.finditer(text):
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.end())
            if line_end == -1:
                line_end = len(text)
            line = text[line_start:line_end]
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Fixture repositories and domain-router examples may legitimately use
            # active workflow names. Closure drift is the class where a test/script
            # points at the real repository workflow artifact as a source of truth.
            if not ("WORKFLOW" in line or "workflow" in line and "read_text" in text[max(0, match.start() - 240): match.end() + 240]):
                continue
            workflow_name = match.group(1)
            active = root / ".github" / "workflows" / workflow_name
            disabled = active.with_name(active.name + ".disabled")
            if not active.exists() and disabled.exists():
                # Allow explicit compatibility helpers that mention both states.
                window = text[max(0, match.start() - 240) : match.end() + 240]
                if ".disabled" in window or "workflow_file(" in window:
                    continue
                findings.append(
                    Finding(
                        id="stale-active-workflow-reference",
                        severity="fail",
                        path=rel(root, path),
                        message=f"references suspended workflow {active.relative_to(root)} while only .disabled exists",
                        repair="Use a helper that prefers the active workflow and falls back to the ADR-130 .disabled artifact, or remove the obsolete test.",
                    )
                )
    return findings


def audit_hardcoded_runtime_hook_counts(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in (root / "tests").rglob("*.py") if (root / "tests").exists() else []:
        if path.name == "test_closure_discipline_audit.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if HARDCODED_HOOK_COUNT_RE.search(text) or HARDCODED_HOOK_TEST_NAME_RE.search(text):
            findings.append(
                Finding(
                    id="hardcoded-runtime-hook-count",
                    severity="fail",
                    path=rel(root, path),
                    message="runtime hook reality test hardcodes a projected hook count",
                    repair="Assert report-derived parity/findings instead of a bare integer; hook demotions/promotions must not require updating a magic number.",
                )
            )
    return findings


def audit_validation_capsule_minimal_repo_fallback(root: Path) -> list[Finding]:
    path = root / "scripts" / "cos-validation-capsule.sh"
    if not path.exists():
        return [
            Finding(
                id="validation-capsule-missing",
                severity="fail",
                path="scripts/cos-validation-capsule.sh",
                message="validation capsule script is missing",
                repair="Restore the validation capsule or remove Makefile targets that depend on it.",
            )
        ]
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "safe-worktree-remove.sh" in text and CAPSULE_FALLBACK_MARKER not in text:
        return [
            Finding(
                id="validation-capsule-no-minimal-repo-fallback",
                severity="fail",
                path=rel(root, path),
                message="validation capsule sources the COS safe-worktree helper without an explicit minimal-repo fallback",
                repair="Keep ADR-129 helper for COS checkouts but provide a non-rm-rf git worktree fallback for minimal consumer repos.",
            )
        ]
    return []


def audit_primitive_lifecycle(root: Path) -> list[Finding]:
    script = root / "scripts" / "primitive_lifecycle.py"
    manifest = root / "manifests" / "primitive-lifecycle.yaml"
    if not script.exists() or not manifest.exists():
        return []
    proc = subprocess.run(
        [sys.executable, str(script), "--json", str(manifest)],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return [
            Finding(
                id="primitive-lifecycle-audit-unparseable",
                severity="fail",
                path=rel(root, script),
                message="primitive lifecycle audit did not emit parseable JSON",
                repair="Run python3 scripts/primitive_lifecycle.py --json and fix the script output.",
            )
        ]
    findings = []
    for item in payload.get("findings", []) or []:
        findings.append(
            Finding(
                id="primitive-lifecycle-finding",
                severity="fail",
                path="manifests/primitive-lifecycle.yaml",
                message=f"{item.get('primitive_id')}: {item.get('field')} — {item.get('message')}",
                repair="Fix lifecycle metadata or relax the lifecycle audit with an ADR-backed exception.",
            )
        )
    return findings


def audit_ci_wiring(root: Path) -> list[Finding]:
    path = root / "scripts" / "cos-ci-local.sh"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "cos-closure-discipline-audit" not in text:
        return [
            Finding(
                id="closure-discipline-not-wired",
                severity="fail",
                path=rel(root, path),
                message="local quick CI does not run the closure discipline audit",
                repair="Add a quick-tier step for scripts/cos-closure-discipline-audit --json.",
            )
        ]
    return []


def build_report(root: Path) -> dict[str, object]:
    root = root.resolve()
    checks = {
        "disabled_workflow_references": audit_disabled_workflow_references(root),
        "hardcoded_runtime_hook_counts": audit_hardcoded_runtime_hook_counts(root),
        "validation_capsule_minimal_repo_fallback": audit_validation_capsule_minimal_repo_fallback(root),
        "primitive_lifecycle": audit_primitive_lifecycle(root),
        "ci_wiring": audit_ci_wiring(root),
    }
    findings = [finding for group in checks.values() for finding in group]
    return {
        "schema_version": 1,
        "status": "fail" if findings else "pass",
        "finding_count": len(findings),
        "findings": [asdict(finding) for finding in findings],
        "checks": {name: {"status": "fail" if group else "pass", "finding_count": len(group)} for name, group in checks.items()},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.project_dir)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["status"] == "pass":
        print("closure-discipline-audit: PASS")
    else:
        print("closure-discipline-audit: FAIL", file=sys.stderr)
        for item in report["findings"]:  # type: ignore[index]
            print(f"- {item['id']}: {item['path']}: {item['message']}", file=sys.stderr)
    if args.fail_on_findings and report["status"] == "fail":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
