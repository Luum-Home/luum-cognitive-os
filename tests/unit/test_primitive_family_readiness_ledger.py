from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "primitive_family_readiness_ledger.py"
spec = importlib.util.spec_from_file_location("primitive_family_readiness_ledger", MODULE_PATH)
assert spec and spec.loader
primitive_family_readiness_ledger = importlib.util.module_from_spec(spec)
sys.modules["primitive_family_readiness_ledger"] = primitive_family_readiness_ledger
spec.loader.exec_module(primitive_family_readiness_ledger)


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "hooks").mkdir(parents=True)
    (root / "skills" / "runner").mkdir(parents=True)
    (root / "rules").mkdir(parents=True)
    (root / "templates").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "manifests").mkdir(parents=True)
    (root / "hooks" / "memory.sh").write_text("#!/usr/bin/env bash\n# memory session summary\n")
    (root / "skills" / "runner" / "SKILL.md").write_text("---\nname: runner\n---\nRun scripts/example.py as a wrapper.\n")
    (root / "rules" / "guard.md").write_text("This policy is enforced by PreToolUse hook.\n")
    (root / "templates" / "quality.md").write_text("<!-- SCOPE: both -->\n# Quality gate template\nAcceptance criteria and verification.\n")
    (root / "docs" / "usage.md").write_text("Use hooks/memory.sh and skills/runner/SKILL.md and rules/guard.md and templates/quality.md\n")
    (root / "manifests" / "primitive-lifecycle.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "primitives": [
                    {
                        "id": "hooks/memory.sh",
                        "kind": "hook",
                        "lifecycle_state": "candidate",
                        "distribution": "core",
                        "supported_harnesses": ["claude-code"],
                    }
                ],
            }
        )
    )
    return root


def test_family_ledgers_classify_roles_and_consumer_access(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    hook = primitive_family_readiness_ledger.build_ledger(root, "hooks")[0]
    skill = primitive_family_readiness_ledger.build_ledger(root, "skills")[0]
    rule = primitive_family_readiness_ledger.build_ledger(root, "rules")[0]
    template = primitive_family_readiness_ledger.build_ledger(root, "templates")[0]

    assert hook.role == "memory-lifecycle"
    assert hook.consumer_accessibility == "lifecycle-declared-consumer-candidate"
    assert skill.role == "compatibility-wrapper"
    assert skill.consumer_accessibility == "repo-skill-not-projectable"
    assert rule.role == "hook-enforced"
    assert rule.consumer_accessibility == "so-local-only"
    assert template.role == "quality-gate"
    assert template.consumer_accessibility == "so-local-only"


def test_cli_writes_family_json_and_markdown(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--project-dir", str(root), "--target-family", "hooks"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads((root / "docs" / "06-Daily" / "reports" / "primitive-readiness-ledger-hooks-latest.json").read_text())
    assert payload["target_family"] == "hooks"
    assert payload["summary"]["total"] == 1
    assert payload["items"][0]["consumer_accessibility"] == "lifecycle-declared-consumer-candidate"
    assert "Primitive Readiness Ledger" in (root / "docs" / "06-Daily" / "reports" / "primitive-readiness-ledger-hooks-latest.md").read_text()
