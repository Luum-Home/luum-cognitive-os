from __future__ import annotations

import re
from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parents[3]
SOURCE_CHECKOUT_PATTERNS = (str(REPO), "/Users/")

BOTH_PRIMITIVES = [
    "hooks/aguara-scan.sh",
    "hooks/ai-provider-identity-guard.sh",
    "hooks/code-review-on-commit.sh",
    "hooks/confidentiality-enforcer.sh",
    "hooks/content-policy.sh",
    "hooks/destructive-rm-blocker.sh",
    "hooks/doc-sync-detector.sh",
    "hooks/git-commit-scope-guard.sh",
    "hooks/global-verify.sh",
    "hooks/guardrails-validator.sh",
    "hooks/mcp-scan.sh",
    "hooks/parry-scan.sh",
    "hooks/pre-commit-gate.sh",
    "hooks/predev-completeness-check.sh",
    "hooks/private-mode-gate.sh",
    "hooks/private-mode-metrics-gate.sh",
    "hooks/rate-limit-drain.sh",
    "hooks/rate-limit-precheck.sh",
    "hooks/rate-limiter.sh",
    "hooks/reinvention-check.sh",
    "hooks/release-guard.sh",
    "hooks/semgrep-scan.sh",
    "hooks/valkey-ensure.sh",
    "hooks/worktree-submodule-fix.sh",
    "scripts/cos-postgres-local.sh",
    "scripts/cos-valkey-local.sh",
    "scripts/credibility-audit.sh",
    "scripts/doctor.sh",
    "scripts/install-aguara.sh",
    "scripts/install-credibility-tools.sh",
    "scripts/install-garak.sh",
    "scripts/install-mcp-scan.sh",
    "scripts/install-promptfoo.sh",
    "scripts/install-syft-grype.sh",
    "scripts/install-tob-skills.sh",
    "scripts/install-trivy.sh",
    "scripts/license-audit-syft-grype.sh",
    "scripts/license-audit-trivy.sh",
]

PROJECT_PRIMITIVES = [
    "hooks/architecture-compliance.sh",
    "hooks/dry-run-preview.sh",
    "hooks/infra-intent-detector.sh",
    "hooks/jupyter-sandbox.sh",
]

OS_ONLY_PRIMITIVES = [
    "hooks/ecosystem-check.sh",
    "hooks/pre-cleanup-snapshot.sh",
    "scripts/cos-cloud-worker-bootstrap.sh",
    "scripts/dependency-lane.sh",
    "scripts/deps-update.sh",
    "scripts/install-git-filter-repo.sh",
    "scripts/setup-git-hooks.sh",
]


def _scope(relpath: str) -> str | None:
    header = "\n".join((REPO / relpath).read_text(encoding="utf-8", errors="replace").splitlines()[:8])
    match = re.search(r"\bSCOPE:\s*([A-Za-z0-9_-]+)", header)
    return match.group(1) if match else None


def _consumer_rows() -> dict[str, dict[str, object]]:
    manifest = yaml.safe_load((REPO / "manifests" / "primitive-consumer-availability.yaml").read_text(encoding="utf-8"))
    return {row["path"]: row for row in manifest["items"] if isinstance(row, dict) and row.get("path")}


def _behavior_rows() -> dict[str, dict[str, object]]:
    manifest = yaml.safe_load((REPO / "manifests" / "primitive-behavior-evidence.yaml").read_text(encoding="utf-8"))
    return {row["primitive"]: row for row in manifest["evidence"] if isinstance(row, dict) and row.get("primitive")}


def test_low_confidence_batch_has_expected_scope_headers() -> None:
    expected = {rel: "both" for rel in BOTH_PRIMITIVES}
    expected.update({rel: "project" for rel in PROJECT_PRIMITIVES})
    expected.update({rel: "os-only" for rel in OS_ONLY_PRIMITIVES})

    failures = [f"{rel}: expected {scope}, got {_scope(rel)}" for rel, scope in expected.items() if _scope(rel) != scope]
    assert not failures, "unexpected SCOPE header after surgical low-confidence review:\n" + "\n".join(failures)


def test_low_confidence_batch_has_consumer_availability_evidence() -> None:
    rows = _consumer_rows()
    expected = {rel: "shared-surface" for rel in BOTH_PRIMITIVES}
    expected.update({rel: "projected-consumer-surface" for rel in PROJECT_PRIMITIVES})
    expected.update({rel: "maintainer-only" for rel in OS_ONLY_PRIMITIVES})

    failures = [f"{rel}: expected {status}, got {rows.get(rel, {}).get('status')}" for rel, status in expected.items() if rows.get(rel, {}).get("status") != status]
    assert not failures, "missing or incorrect consumer availability evidence:\n" + "\n".join(failures)


def test_both_low_confidence_batch_has_portability_evidence_rows() -> None:
    rows = _behavior_rows()
    proof = "tests/red_team/portability/test_low_confidence_scope_batch.py"
    failures = []
    for rel in BOTH_PRIMITIVES:
        row = rows.get(rel, {})
        if proof not in row.get("tests", []):
            failures.append(f"{rel}: missing {proof}")
        if "shell-ci" not in set(row.get("harnesses", [])):
            failures.append(f"{rel}: missing shell-ci portability evidence label")
    assert not failures, "both primitives need paired portability evidence:\n" + "\n".join(failures)


def test_shared_batch_does_not_hardcode_local_source_checkout() -> None:
    failures = []
    for rel in BOTH_PRIMITIVES + PROJECT_PRIMITIVES:
        text = (REPO / rel).read_text(encoding="utf-8", errors="replace")
        if any(pattern in text for pattern in SOURCE_CHECKOUT_PATTERNS):
            failures.append(rel)
    assert not failures, "portable/project primitives must not hardcode local source checkout paths:\n" + "\n".join(failures)
