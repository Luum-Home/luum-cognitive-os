#!/usr/bin/env python3
# SCOPE: os-only
"""Atomic primitive-closure check and repair workflow.

When a Cognitive OS agentic primitive changes, several derived surfaces must be
kept in lockstep: lifecycle metadata, portable .ai overlay, ACC/readiness
reports, registry locks, harness projections, and red-team portability proofs.
This command gives maintainers one deterministic entrypoint instead of relying
on test cascades to reveal each missing projection one lane at a time.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ClosureStep:
    id: str
    title: str
    command: list[str]
    status: str
    stdout_tail: str = ""
    stderr_tail: str = ""
    returncode: int | None = None
    remediation: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


REPAIR_COMMANDS: list[tuple[str, str, list[str]]] = [
    (
        "refresh-acc-readiness",
        "Refresh primitive readiness ledgers, harness coverage, authority reports, and ACC outputs",
        [sys.executable, "scripts/acc_pipeline.py", "--refresh"],
    ),
    (
        "refresh-portable-ai-overlay",
        "Regenerate the portable .ai primitive overlay",
        [sys.executable, "scripts/portable_ai_overlay.py"],
    ),
    (
        "refresh-registry-locks",
        "Regenerate primitive and skill registry locks",
        ["scripts/cos-registry-lock", "--write"],
    ),
]

CHECK_COMMANDS: list[tuple[str, str, list[str], str]] = [
    (
        "derived-artifact-gate",
        "Harness projections and derived hook artifacts are coherent",
        [sys.executable, "scripts/derived_artifact_gate.py", "--json"],
        "Run scripts/generate-project-settings.sh or the relevant settings driver, then rerun this check.",
    ),
    (
        "script-lifecycle-backlog",
        "Agentic script wrappers have lifecycle metadata or an explicit boundary",
        [sys.executable, "scripts/primitive_readiness_ledger.py", "--project-dir", ".", "--fail-agentic-without-lifecycle"],
        "Add ADR-126 lifecycle rows for new agentic wrappers or downgrade their role before claiming primitive support.",
    ),
    (
        "portable-ai-overlay",
        "Portable .ai overlay matches lifecycle/contracts/source primitives",
        [sys.executable, "scripts/portable_ai_overlay.py", "--check"],
        "Run python3 scripts/portable_ai_overlay.py and stage the generated .ai files.",
    ),
    (
        "registry-lock",
        "Primitive and skill registry locks match current lifecycle and skills",
        ["scripts/cos-registry-lock", "--audit"],
        "Run scripts/cos-registry-lock --write and stage manifests/agentic-primitive-registry.lock.yaml plus skills/REGISTRY.lock.",
    ),
    (
        "acc-readable",
        "ACC pipeline can read the current generated reports",
        [sys.executable, "scripts/acc_pipeline.py", "--brief"],
        "Run python3 scripts/acc_pipeline.py --refresh and stage docs/07-Capabilities/acc plus docs/06-Daily/reports outputs.",
    ),
]

PRIMITIVE_TOUCH_PREFIXES = (
    "hooks/",
    "rules/",
    "skills/",
    "scripts/",
    "templates/",
    "agents/",
    "manifests/primitive-lifecycle.yaml",
    "manifests/primitive-contracts.yaml",
    "manifests/harness-projection.yaml",
)

DERIVED_SURFACE_PREFIXES = (
    ".ai/",
    ".claude/",
    ".codex/",
    ".cognitive-os/skills/",
    "docs/06-Daily/reports/primitive-",
    "docs/07-Capabilities/acc/",
    "manifests/agentic-primitive-registry.lock.yaml",
    "skills/REGISTRY.lock",
)


def _tail(text: str, limit: int = 2400) -> str:
    return text[-limit:] if len(text) > limit else text


def _run(command: Sequence[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _git_changed(args: Sequence[str]) -> set[str]:
    proc = _run(["git", *args], timeout=30)
    if proc.returncode != 0:
        return set()
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def changed_paths(include_untracked: bool = True) -> set[str]:
    paths: set[str] = set()
    paths.update(_git_changed(["diff", "--name-only", "--diff-filter=ACMR", "HEAD"]))
    paths.update(_git_changed(["diff", "--cached", "--name-only", "--diff-filter=ACMR"]))
    if include_untracked:
        paths.update(_git_changed(["ls-files", "--others", "--exclude-standard"]))
    return paths


def primitive_paths(paths: Iterable[str]) -> list[str]:
    return sorted(path for path in paths if path.startswith(PRIMITIVE_TOUCH_PREFIXES))


def derived_paths(paths: Iterable[str]) -> list[str]:
    return sorted(path for path in paths if path.startswith(DERIVED_SURFACE_PREFIXES))


def run_repair() -> list[ClosureStep]:
    steps: list[ClosureStep] = []
    for step_id, title, command in REPAIR_COMMANDS:
        proc = _run(command, timeout=600)
        steps.append(
            ClosureStep(
                id=step_id,
                title=title,
                command=command,
                status="pass" if proc.returncode == 0 else "fail",
                stdout_tail=_tail(proc.stdout),
                stderr_tail=_tail(proc.stderr),
                returncode=proc.returncode,
            )
        )
        if proc.returncode != 0:
            break
    return steps


def run_checks() -> list[ClosureStep]:
    steps: list[ClosureStep] = []
    for step_id, title, command, remediation in CHECK_COMMANDS:
        proc = _run(command, timeout=300)
        steps.append(
            ClosureStep(
                id=step_id,
                title=title,
                command=command,
                status="pass" if proc.returncode == 0 else "fail",
                stdout_tail=_tail(proc.stdout),
                stderr_tail=_tail(proc.stderr),
                returncode=proc.returncode,
                remediation=remediation,
            )
        )
    return steps


def closure_context() -> dict[str, object]:
    paths = changed_paths()
    primitive = primitive_paths(paths)
    derived = derived_paths(paths)
    return {
        "changed_count": len(paths),
        "primitive_changed_count": len(primitive),
        "derived_changed_count": len(derived),
        "primitive_changed": primitive[:200],
        "derived_changed": derived[:200],
        "requires_primitive_closure": bool(primitive),
        "note": (
            "Primitive changes require lifecycle/overlay/ACC/registry/projection/red-team closure before broad tests."
            if primitive
            else "No primitive-surface changes detected from git diff/untracked scan."
        ),
    }


def build_report(*, repair: bool) -> dict[str, object]:
    repair_steps = run_repair() if repair else []
    check_steps = run_checks()
    all_steps = [*repair_steps, *check_steps]
    failures = [step for step in all_steps if step.status != "pass"]
    context = closure_context()
    return {
        "schema_version": "primitive-closure-check/v1",
        "status": "pass" if not failures else "fail",
        "mode": "repair-check" if repair else "check",
        "context": context,
        "steps": [step.to_dict() for step in all_steps],
        "next_actions": next_actions(failures, context),
    }


def next_actions(failures: Sequence[ClosureStep], context: dict[str, object]) -> list[str]:
    if failures:
        return [f"{item.id}: {item.remediation or 'Inspect stdout/stderr and repair before broad tests.'}" for item in failures]
    if context.get("requires_primitive_closure"):
        return [
            "Run targeted tests for the touched primitive family before make test-laptop.",
            "Stage canonical and derived surfaces together so contract lanes do not fail one-by-one.",
        ]
    return ["No primitive closure drift detected."]


def print_text(report: dict[str, object]) -> None:
    print(f"Primitive closure: {str(report['status']).upper()} ({report['mode']})")
    context = report["context"] if isinstance(report.get("context"), dict) else {}
    print(
        "changed={changed_count} primitive_changed={primitive_changed_count} derived_changed={derived_changed_count}".format(
            **context
        )
    )
    print(str(context.get("note", "")))
    print("\nSteps:")
    for raw in report.get("steps", []):
        if not isinstance(raw, dict):
            continue
        print(f"- {raw['id']}: {str(raw['status']).upper()} — {raw['title']}")
        if raw.get("status") != "pass" and raw.get("remediation"):
            print(f"  remediation: {raw['remediation']}")
    print("\nNext actions:")
    for action in report.get("next_actions", []):
        print(f"- {action}")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repair", action="store_true", help="refresh generated primitive surfaces before checking")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument("--strict", action="store_true", help="exit non-zero on closure failure")
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = build_report(repair=args.repair)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report)
    return 2 if args.strict and report["status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
