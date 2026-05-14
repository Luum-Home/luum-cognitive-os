# SCOPE: both
"""Contract tests for ADR-311 primitive closure ratchet."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.primitive_closure_ratchet import run

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "cos-primitive-closure-ratchet"
MANIFEST = REPO_ROOT / "manifests" / "primitive-closure-ratchet.yaml"


def test_repository_closure_ratchet_passes_current_baseline() -> None:
    result = subprocess.run(
        [str(SCRIPT), "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads(result.stdout)
    assert report["valid"] is True
    assert report["findings"] == []


def test_language_baseline_regression_blocks(tmp_path: Path) -> None:
    report = tmp_path / "language-dependence-audit.md"
    report.write_text(
        "# Language Dependence Audit\n\n"
        "| Severity | Category | File | Line | Primitive | Languages | Pattern |\n"
        "|---|---|---|---:|---|---|---|\n"
        "| medium | `regex_without_intents` | `skills/x/SKILL.md` | 1 | `x` | en | `\\bhelp\\b` |\n",
        encoding="utf-8",
    )
    manifest = yaml.safe_load(MANIFEST.read_text())
    manifest["language_dependence"]["report"] = str(report)
    manifest["language_dependence"]["max_medium_plus_findings"] = 0
    custom = tmp_path / "primitive-closure-ratchet.yaml"
    custom.write_text(yaml.safe_dump(manifest, sort_keys=True))

    findings = run(REPO_ROOT, custom)

    assert any(f.code == "language_medium_plus_regression" and f.severity == "block" for f in findings)


def test_required_runtime_proof_must_exist(tmp_path: Path) -> None:
    manifest = yaml.safe_load(MANIFEST.read_text())
    manifest["required_runtime_proofs"] = [
        {
            "primitive": "missing-proof",
            "hook": "hooks/subagent-budget-enforcer.sh",
            "test": "tests/contracts/does_not_exist.py",
        }
    ]
    custom = tmp_path / "primitive-closure-ratchet.yaml"
    custom.write_text(yaml.safe_dump(manifest, sort_keys=True))

    findings = run(REPO_ROOT, custom)

    assert any(f.code == "missing_runtime_proof" for f in findings)


def test_subagent_budget_enforcer_is_in_claude_projection() -> None:
    settings = REPO_ROOT / ".claude" / "settings.json"
    assert "hooks/subagent-budget-enforcer.sh" in settings.read_text()
