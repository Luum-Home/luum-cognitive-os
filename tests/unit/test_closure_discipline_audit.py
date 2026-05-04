from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

import scripts.cos_closure_discipline_audit as audit

REPO_ROOT = Path(__file__).resolve().parents[2]


def write_min_project(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "tests" / "unit").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "manifests").mkdir()
    (root / "scripts" / "primitive_lifecycle.py").write_text(
        "#!/usr/bin/env python3\nimport json; print(json.dumps({'findings': []}))\n",
        encoding="utf-8",
    )
    (root / "manifests" / "primitive-lifecycle.yaml").write_text("primitives: []\n", encoding="utf-8")
    (root / "scripts" / "cos-ci-local.sh").write_text("scripts/cos-closure-discipline-audit --json\n", encoding="utf-8")
    (root / "scripts" / "cos-validation-capsule.sh").write_text(
        "# COS_VALIDATION_CAPSULE_SAFE_WORKTREE_FALLBACK\nsource safe-worktree-remove.sh\n",
        encoding="utf-8",
    )
    return root


def test_flags_stale_active_workflow_reference_when_only_disabled_exists(tmp_path: Path) -> None:
    root = write_min_project(tmp_path)
    (root / ".github" / "workflows" / "test-lanes.yml.disabled").write_text("jobs: {}\n", encoding="utf-8")
    (root / "tests" / "unit" / "test_workflow.py").write_text(
        'WORKFLOW = REPO_ROOT / ".github/workflows/test-lanes.yml"\n', encoding="utf-8"
    )

    report = audit.build_report(root)

    assert report["status"] == "fail"
    assert any(item["id"] == "stale-active-workflow-reference" for item in report["findings"])


def test_allows_explicit_disabled_workflow_fallback_helper(tmp_path: Path) -> None:
    root = write_min_project(tmp_path)
    (root / ".github" / "workflows" / "test-lanes.yml.disabled").write_text("jobs: {}\n", encoding="utf-8")
    (root / "tests" / "unit" / "test_workflow.py").write_text(
        'def workflow_file(name):\n    return Path(".github/workflows/test-lanes.yml.disabled")\n', encoding="utf-8"
    )

    report = audit.build_report(root)

    assert report["checks"]["disabled_workflow_references"]["status"] == "pass"


def test_flags_hardcoded_runtime_hook_count(tmp_path: Path) -> None:
    root = write_min_project(tmp_path)
    (root / "tests" / "unit" / "test_runtime.py").write_text("assert len(projected) == 115\n", encoding="utf-8")

    report = audit.build_report(root)

    assert any(item["id"] == "hardcoded-runtime-hook-count" for item in report["findings"])


def test_flags_validation_capsule_without_minimal_repo_fallback(tmp_path: Path) -> None:
    root = write_min_project(tmp_path)
    (root / "scripts" / "cos-validation-capsule.sh").write_text('source "$REPO_ROOT/hooks/_lib/safe-worktree-remove.sh"\n', encoding="utf-8")

    report = audit.build_report(root)

    assert any(item["id"] == "validation-capsule-no-minimal-repo-fallback" for item in report["findings"])


def test_flags_primitive_lifecycle_findings(tmp_path: Path) -> None:
    root = write_min_project(tmp_path)
    (root / "scripts" / "primitive_lifecycle.py").write_text(
        "#!/usr/bin/env python3\nimport json; print(json.dumps({'findings': [{'primitive_id': 'x', 'field': 'governance_class', 'message': 'bad'}]}))\n",
        encoding="utf-8",
    )

    report = audit.build_report(root)

    assert any(item["id"] == "primitive-lifecycle-finding" for item in report["findings"])


def test_current_repository_closure_audit_passes() -> None:
    report = audit.build_report(REPO_ROOT)

    assert report["status"] == "pass", json.dumps(report["findings"], indent=2)


def test_cli_json_exits_zero_without_fail_flag() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "cos_closure_discipline_audit.py"), "--project-dir", str(REPO_ROOT), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"


def test_manifest_registers_closure_discipline_gate() -> None:
    manifest = yaml.safe_load((REPO_ROOT / "manifests" / "primitive-lifecycle.yaml").read_text(encoding="utf-8"))
    ids = {item["id"] for item in manifest["primitives"] if isinstance(item, dict)}

    assert "scripts/cos-closure-discipline-audit" in ids
