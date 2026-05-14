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


def required_harnesses(*names: str) -> dict[str, dict[str, str]]:
    return {name: {"status": "required"} for name in names}


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


def test_dispatcher_route_counts_as_codex_projection_closure(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".codex").mkdir()
    (tmp_path / "hooks").mkdir()
    hook = "hooks/orchestrator-skill-invocation-gate.sh"
    dispatcher = "hooks/bash-hot-path-dispatcher.sh"
    (tmp_path / "cognitive-os.yaml").write_text(hook, encoding="utf-8")
    (tmp_path / ".claude" / "settings.json").write_text(hook, encoding="utf-8")
    (tmp_path / ".codex" / "hooks.json").write_text(dispatcher, encoding="utf-8")
    (tmp_path / dispatcher).write_text(f'_run_gate "{hook}"\n', encoding="utf-8")
    manifest = {
        "critical_hook_projections": [
            {
                "primitive": "skill-gate",
                "hook": hook,
                "harness_requirements": required_harnesses("claude", "codex"),
            }
        ]
    }
    custom = tmp_path / "primitive-closure-ratchet.yaml"
    custom.write_text(yaml.safe_dump(manifest, sort_keys=True))

    findings = run(tmp_path, custom)

    assert findings == []


def test_dispatcher_projection_without_route_is_not_closure(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".codex").mkdir()
    (tmp_path / "hooks").mkdir()
    hook = "hooks/orchestrator-skill-invocation-gate.sh"
    dispatcher = "hooks/bash-hot-path-dispatcher.sh"
    (tmp_path / "cognitive-os.yaml").write_text(hook, encoding="utf-8")
    (tmp_path / ".claude" / "settings.json").write_text(hook, encoding="utf-8")
    (tmp_path / ".codex" / "hooks.json").write_text(dispatcher, encoding="utf-8")
    (tmp_path / dispatcher).write_text('echo "different gate"\n', encoding="utf-8")
    manifest = {
        "critical_hook_projections": [
            {
                "primitive": "skill-gate",
                "hook": hook,
                "harness_requirements": required_harnesses("claude", "codex"),
            }
        ]
    }
    custom = tmp_path / "primitive-closure-ratchet.yaml"
    custom.write_text(yaml.safe_dump(manifest, sort_keys=True))

    findings = run(tmp_path, custom)

    assert any(f.code == "missing_codex_projection" for f in findings)


def test_subagent_budget_enforcer_is_in_claude_projection() -> None:
    settings = REPO_ROOT / ".claude" / "settings.json"
    assert "hooks/subagent-budget-enforcer.sh" in settings.read_text()


def test_legacy_claude_codex_only_contract_is_rejected(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".codex").mkdir()
    hook = "hooks/orchestrator-skill-invocation-gate.sh"
    (tmp_path / "cognitive-os.yaml").write_text(hook, encoding="utf-8")
    (tmp_path / ".claude" / "settings.json").write_text(hook, encoding="utf-8")
    (tmp_path / ".codex" / "hooks.json").write_text(hook, encoding="utf-8")
    manifest = {
        "critical_hook_projections": [
            {
                "primitive": "skill-gate",
                "hook": hook,
                "claude_required": True,
                "codex_required": True,
            }
        ]
    }
    custom = tmp_path / "primitive-closure-ratchet.yaml"
    custom.write_text(yaml.safe_dump(manifest, sort_keys=True))

    findings = run(tmp_path, custom)

    assert any(f.code == "legacy_claude_codex_only_projection_contract" for f in findings)


def test_implemented_harnesses_must_be_classified(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / "manifests").mkdir()
    hook = "hooks/orchestrator-skill-invocation-gate.sh"
    (tmp_path / "cognitive-os.yaml").write_text(hook, encoding="utf-8")
    (tmp_path / ".claude" / "settings.json").write_text(hook, encoding="utf-8")
    (tmp_path / "manifests" / "harness-projection.yaml").write_text(
        yaml.safe_dump(
            {
                "harnesses": [
                    {"id": "claude", "status": "implemented"},
                    {"id": "cursor", "status": "implemented"},
                ]
            }
        ),
        encoding="utf-8",
    )
    manifest = {
        "critical_hook_projections": [
            {
                "primitive": "skill-gate",
                "hook": hook,
                "harness_requirements": required_harnesses("claude"),
            }
        ]
    }
    custom = tmp_path / "primitive-closure-ratchet.yaml"
    custom.write_text(yaml.safe_dump(manifest, sort_keys=True))

    findings = run(tmp_path, custom)

    assert any(f.code == "missing_harness_projection_requirement" and "cursor" in f.message for f in findings)


def test_non_required_harness_status_requires_reason(tmp_path: Path) -> None:
    hook = "hooks/orchestrator-skill-invocation-gate.sh"
    (tmp_path / "cognitive-os.yaml").write_text(hook, encoding="utf-8")
    manifest = {
        "critical_hook_projections": [
            {
                "primitive": "skill-gate",
                "hook": hook,
                "harness_requirements": {
                    "cursor": {"status": "structural_advisory"},
                },
            }
        ]
    }
    custom = tmp_path / "primitive-closure-ratchet.yaml"
    custom.write_text(yaml.safe_dump(manifest, sort_keys=True))

    findings = run(tmp_path, custom)

    assert any(f.code == "missing_harness_gap_reason" for f in findings)
