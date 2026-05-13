from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "primitive_readiness_ledger.py"
spec = importlib.util.spec_from_file_location("primitive_readiness_ledger", MODULE_PATH)
assert spec and spec.loader
primitive_readiness_ledger = importlib.util.module_from_spec(spec)
sys.modules["primitive_readiness_ledger"] = primitive_readiness_ledger
spec.loader.exec_module(primitive_readiness_ledger)


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts" / "_lib").mkdir(parents=True)
    (root / "scripts" / "chaos").mkdir(parents=True)
    (root / "skills" / "runner").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "docs").mkdir()
    (root / "manifests").mkdir()

    (root / "scripts" / "tool.py").write_text("print('tool')\n")
    (root / "scripts" / "audit.py").write_text("print('audit')\n")
    (root / "scripts" / "backfill_old.py").write_text("print('backfill')\n")
    (root / "scripts" / "_lib" / "settings-driver-codex.sh").write_text("#!/usr/bin/env bash\n")
    (root / "scripts" / "chaos" / "race.sh").write_text("#!/usr/bin/env bash\n")
    (root / "scripts" / "cos-sample").write_text("python3 scripts/tool.py\n")

    (root / "skills" / "runner" / "SKILL.md").write_text("Run scripts/tool.py\n")
    (root / "tests" / "test_audit.py").write_text("def test_audit(): assert 'scripts/audit.py'\n")
    (root / "docs" / "note.md").write_text("Historical: scripts/backfill_old.py and scripts/chaos/race.sh\n")
    (root / "manifests" / "primitive-lifecycle.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "primitives": [
                    {
                        "id": "scripts/cos-sample",
                        "kind": "script",
                        "lifecycle_state": "advisory",
                        "distribution": "core",
                        "supported_harnesses": ["shell"],
                    }
                ],
            }
        )
    )

    (root / "manifests" / "primitive-readiness-protected-install-surfaces.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "scripts": [
                    {
                        "path": "scripts/tool.py",
                        "surface": "bootstrap",
                        "rationale": "Synthetic protected install surface",
                    }
                ],
            }
        )
    )
    return root


def test_build_ledger_classifies_script_roles(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    rows = primitive_readiness_ledger.build_ledger(root)
    by_path = {row.path: row for row in rows}

    assert by_path["scripts/tool.py"].role == "agentic-primitive"
    assert by_path["scripts/tool.py"].role_source == "usage:skill"
    assert by_path["scripts/audit.py"].role == "maintainer-tool"
    assert by_path["scripts/backfill_old.py"].role == "migration-only"
    assert by_path["scripts/_lib/settings-driver-codex.sh"].role == "driver-specific"
    assert by_path["scripts/chaos/race.sh"].role == "lab"
    assert by_path["scripts/cos-sample"].role == "agentic-primitive"
    assert by_path["scripts/cos-sample"].lifecycle_state == "advisory"
    assert by_path["scripts/cos-sample"].supported_harnesses == ["shell"]
    assert by_path["scripts/tool.py"].protected_install_surface is True
    assert by_path["scripts/tool.py"].install_surface == "bootstrap"
    assert by_path["scripts/tool.py"].consumer_accessibility == "install-profile-managed"
    assert by_path["scripts/cos-sample"].consumer_accessibility == "lifecycle-declared-consumer-candidate"
    assert by_path["scripts/audit.py"].consumer_accessibility == "so-local-only"


def test_cli_writes_machine_readable_and_markdown_ledgers(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--project-dir", str(root)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads((root / "docs" / "06-Daily" / "reports" / "primitive-readiness-ledger-scripts-latest.json").read_text())
    assert payload["schema_version"] == 1
    assert payload["target_family"] == "scripts"
    assert payload["summary"]["total_scripts"] == 6
    assert payload["summary"]["consumer_accessibility"]["install-profile-managed"] == 1
    assert payload["summary"]["consumer_accessibility"]["lifecycle-declared-consumer-candidate"] == 1
    assert set(payload["allowed_roles"]) == primitive_readiness_ledger.ROLES
    assert all(row["consumer_accessibility"] for row in payload["scripts"])
    assert all(row["consumer_access_next_action"] for row in payload["scripts"])
    assert "Primitive Readiness Ledger" in (
        root / "docs" / "06-Daily" / "reports" / "primitive-readiness-ledger-scripts-latest.md"
    ).read_text()
    assert "Consumer Access" in (
        root / "docs" / "06-Daily" / "reports" / "primitive-readiness-ledger-scripts-latest.md"
    ).read_text()
    backlog = json.loads((root / "docs" / "06-Daily" / "reports" / "primitive-readiness-lifecycle-backlog-scripts-latest.json").read_text())
    assert backlog["purpose"] == "agentic primitives missing ADR-126 lifecycle metadata"
    assert backlog["summary"]["total"] >= 1
    protected = [item for item in backlog["items"] if item["priority"] == "protected"]
    assert protected
    assert protected[0]["protected_install_surface"] is True


def test_fail_flags_make_weak_rows_actionable(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--project-dir",
            str(root),
            "--fail-agentic-without-lifecycle",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["agentic_primitives_without_lifecycle"] >= 1


def test_overrides_remove_low_confidence_and_record_rationale(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    overrides = root / "manifests" / "primitive-readiness-script-overrides.yaml"
    overrides.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "scripts": [
                    {
                        "path": "scripts/audit.py",
                        "role": "lab",
                        "rationale": "Synthetic override for test",
                    }
                ],
            }
        )
    )

    rows = primitive_readiness_ledger.build_ledger(root, "manifests/primitive-readiness-script-overrides.yaml")
    by_path = {row.path: row for row in rows}

    assert by_path["scripts/audit.py"].role == "lab"
    assert by_path["scripts/audit.py"].role_source == "override"
    assert by_path["scripts/audit.py"].confidence == "high"
    assert by_path["scripts/audit.py"].override_rationale == "Synthetic override for test"
