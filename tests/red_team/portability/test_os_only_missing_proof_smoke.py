# SCOPE: os-only
"""Smoke portability proof for reviewed os-only primitives with previously missing evidence rows."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OS_ONLY_PRIMITIVES = [
    "hooks/goal-stop-gate.sh",
    "hooks/subagent-input-schema-validator.sh",
    "rules/goal-loop.md",
    "rules/hook-maturity.md",
    "rules/routing-pattern-authoring.md",
    "rules/routing-quality-gate.md",
    "scripts/audit-routing-intents",
    "scripts/cos-english-only-content-audit",
    "scripts/cos-exercised-coverage",
    "scripts/cos-goal",
    "scripts/cos-graphify-build",
    "scripts/cos-graphify-context-replay-benchmark",
    "scripts/cos-graphify-hotspot-report",
    "scripts/cos-graphify-phase-d-semantic",
    "scripts/cos-graphify-preload-matrix",
    "scripts/cos-graphify-run-telemetry",
    "scripts/cos-graphify-token-footprint",
    "scripts/cos-graphify-token-reduction-smoke",
    "scripts/cos-install-hook",
    "scripts/cos-install-skill",
    "scripts/cos-lean-core-5min-proof",
    "scripts/cos-maintainer-impact",
    "scripts/cos-plan-closure-disposition-audit",
    "scripts/cos-routing-corpus-audit",
    "scripts/cos-routing-max-gate",
    "scripts/cos-routing-quality-gate",
    "scripts/cos-self-improvement-runner",
    "scripts/cos-strict-maintainer-concurrency-proof",
    "scripts/cos-subprocess-timeout-backfill",
    "scripts/cos_goal.py",
    "scripts/english_only_content_audit.py",
    "scripts/plan_closure_disposition_audit.py",
    "scripts/routing_corpus_audit.py",
    "scripts/routing_intent_audit.py",
    "scripts/routing_quality_gate.py",
    "scripts/skill_platform_support_audit.py",
    "scripts/workstation_container_benchmark_report.py",
    "skills/graphify-query/SKILL.md",
    "skills/install-hook/SKILL.md",
    "skills/install-skill/SKILL.md",
    "templates/agent-planning.md",
]


def test_os_only_missing_proof_primitives_have_portable_markers() -> None:
    failures: list[str] = []
    for rel in OS_ONLY_PRIMITIVES:
        path = REPO / rel
        if not path.exists():
            failures.append(f"{rel}: missing")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        header = "\n".join(text.splitlines()[:20])
        has_os_only_marker = (
            "SCOPE: os-only" in header
            or "tag: os-only" in header
            or "audience: os" in header
        )
        if not has_os_only_marker:
            failures.append(f"{rel}: missing os-only scope marker")
        if str(REPO) in text or "/Users/" in text:
            failures.append(f"{rel}: hardcodes local source checkout path")
    assert not failures, "os-only smoke portability failures:\n" + "\n".join(failures)
