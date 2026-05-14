from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "primitive_scope_classifier.py"
spec = importlib.util.spec_from_file_location("primitive_scope_classifier", MODULE_PATH)
assert spec and spec.loader
primitive_scope_classifier = importlib.util.module_from_spec(spec)
sys.modules["primitive_scope_classifier"] = primitive_scope_classifier
spec.loader.exec_module(primitive_scope_classifier)


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "skills" / "portable").mkdir(parents=True)
    (root / "skills" / "local").mkdir(parents=True)
    (root / "manifests").mkdir(parents=True)

    (root / "scripts" / "cos_init.py").write_text("#!/usr/bin/env python3\n# SCOPE: both\nprint('install')\n")
    (root / "scripts" / "security_red_team.py").write_text("#!/usr/bin/env python3\n# SCOPE: os-only\nprint('security')\n")
    (root / "skills" / "portable" / "SKILL.md").write_text(
        "<!-- SCOPE: both -->\n---\nname: portable\naudience: os-dev\n---\nMentions manifests/ and docs/02-Decisions/ but is exported.\n"
    )
    (root / "skills" / "local" / "SKILL.md").write_text(
        "<!-- SCOPE: both -->\n---\nname: local\n---\nNo distribution evidence.\n"
    )
    (root / "manifests" / "primitive-scope-overrides.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "primitive-scope-overrides.v1",
                "rules": [
                    {"pattern": "scripts/*.py", "scope": "os-only", "rationale": "default script fallback"},
                    {"pattern": "scripts/cos_init.py", "scope": "both", "rationale": "installer/project bootstrap surface"},
                ],
            }
        )
    )
    (root / "manifests" / "primitive-readiness-protected-install-surfaces.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "scripts": [{"path": "scripts/cos_init.py", "surface": "bootstrap"}]})
    )
    (root / "manifests" / "primitive-consumer-availability.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "primitive-consumer-availability.v1",
                "items": [{"path": "scripts/security_red_team.py", "status": "maintainer-only", "rationale": "SO security runner"}],
            }
        )
    )
    (root / "manifests" / "primitive-lifecycle.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "primitives": [
                    {"id": "skills/portable/SKILL.md", "kind": "skill", "distribution": "core", "lifecycle_state": "advisory"}
                ],
            }
        )
    )
    proof = root / "tests" / "red_team" / "portability"
    proof.mkdir(parents=True)
    (proof / "test_skill_portable.py").write_text("def test_portable(): pass\n")
    return root


def test_classifier_uses_distribution_evidence_not_grep_mentions(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    rows = {row.path: row for row in primitive_scope_classifier.build_rows(root)}

    assert rows["scripts/cos_init.py"].suggested_scope == "both"
    assert rows["scripts/cos_init.py"].confidence == "high"
    assert rows["scripts/security_red_team.py"].suggested_scope == "os-only"
    assert rows["scripts/security_red_team.py"].confidence == "high"

    portable = rows["skills/portable/SKILL.md"]
    assert portable.suggested_scope == "both"
    assert portable.declared_scope == "both"
    assert not portable.contradiction
    assert any(item.source == "lifecycle" for item in portable.evidence)


def test_classifier_flags_unsupported_both_instead_of_silently_accepting(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    rows = {row.path: row for row in primitive_scope_classifier.build_rows(root)}

    local = rows["skills/local/SKILL.md"]
    assert local.suggested_scope == "os-only"
    assert local.confidence == "low"
    assert "declared both" in local.contradiction or "without paired portability proof" in local.contradiction
    assert "lifecycle/projection/consumer-availability" in local.next_action or "SCOPE marker" in local.next_action


def test_cli_writes_report_and_can_fail_contradictions(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--project-dir", str(root), "--fail-contradictions"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    stdout = json.loads(result.stdout)
    assert stdout["contradictions"] >= 1
    report = json.loads((root / ".cognitive-os" / "reports" / "primitive-scope-classifier.json").read_text())
    assert report["schema_version"] == "primitive-scope-classifier/v1"
    assert report["summary"]["contradictions"] >= 1


def test_changed_only_limits_enforcement_to_git_status_rows(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=root, check=True, stdout=subprocess.DEVNULL)

    (root / "scripts" / "security_red_team.py").write_text("#!/usr/bin/env python3\n# SCOPE: os-only\nprint('changed')\n")

    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--project-dir", str(root), "--changed-only", "--fail-contradictions"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    stdout = json.loads(result.stdout)
    assert stdout["total"] == 1
    assert stdout["contradictions"] == 0


def test_paths_option_limits_enforcement_to_explicit_primitive_paths(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--project-dir",
            str(root),
            "--paths",
            "scripts/security_red_team.py",
            "--fail-contradictions",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    stdout = json.loads(result.stdout)
    assert stdout["total"] == 1
    assert stdout["contradictions"] == 0
