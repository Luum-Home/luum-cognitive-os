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
    (root / "packages" / "quality" / "skills" / "portable-package").mkdir(parents=True)
    (root / "manifests").mkdir(parents=True)

    (root / "scripts" / "cos_init.py").write_text("#!/usr/bin/env python3\n# SCOPE: both\nprint('install')\n")
    (root / "scripts" / "security_red_team.py").write_text("#!/usr/bin/env python3\n# SCOPE: os-only\nprint('security')\n")
    (root / "skills" / "portable" / "SKILL.md").write_text(
        "<!-- SCOPE: both -->\n---\nname: portable\naudience: os-dev\n---\nMentions manifests/ and docs/02-Decisions/ but is exported.\n"
    )
    (root / "skills" / "local" / "SKILL.md").write_text(
        "<!-- SCOPE: both -->\n---\nname: local\n---\nNo distribution evidence.\n"
    )
    (root / "packages" / "quality" / "skills" / "portable-package" / "SKILL.md").write_text(
        "<!-- SCOPE: both -->\n---\nname: portable-package\n---\nPackaged portable skill.\n"
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
                    {
                        "id": "skills/portable/SKILL.md",
                        "kind": "skill",
                        "distribution": "core",
                        "lifecycle_state": "advisory",
                        "consumer_accessibility": "lifecycle-declared-shared-surface",
                    },
                    {
                        "id": "packages/quality/skills/portable-package/SKILL.md",
                        "kind": "skill",
                        "distribution": "team",
                        "lifecycle_state": "candidate",
                        "consumer_accessibility": "lifecycle-declared-shared-surface",
                    },
                ],
            }
        )
    )
    proof = root / "tests" / "red_team" / "portability"
    proof.mkdir(parents=True)
    (proof / "test_skill_portable.py").write_text("def test_portable(): pass\n")
    (proof / "test_package_skill_quality_portable_package.py").write_text("def test_portable_package(): pass\n")
    return root


def test_classifier_uses_distribution_evidence_not_grep_mentions(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    rows = {row.path: row for row in primitive_scope_classifier.build_rows(root)}

    assert rows["scripts/cos_init.py"].suggested_scope == "both"
    assert rows["scripts/cos_init.py"].confidence in {"high", "medium"}
    assert rows["scripts/security_red_team.py"].suggested_scope == "os-only"
    assert rows["scripts/security_red_team.py"].confidence in {"high", "medium"}

    portable = rows["skills/portable/SKILL.md"]
    assert portable.suggested_scope == "both"
    assert portable.declared_scope == "both"
    assert not portable.contradiction
    assert any(item.source == "lifecycle" for item in portable.evidence)


def test_classifier_flags_unsupported_both_instead_of_silently_accepting(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    rows = {row.path: row for row in primitive_scope_classifier.build_rows(root)}

    local = rows["skills/local/SKILL.md"]
    assert local.suggested_scope == "unknown"
    assert local.effective_scope == "os-only"
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


def test_unknown_keeps_safe_effective_scope_separate_from_suggestion(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    rows = primitive_scope_classifier.build_rows(root)
    summary = primitive_scope_classifier.summarize(rows)

    assert summary["by_suggested_scope"]["unknown"] >= 1
    assert summary["by_effective_scope"]["os-only"] >= summary["by_suggested_scope"]["unknown"]
    assert summary["safe_fallback_os_only_from_unknown"] == summary["by_suggested_scope"]["unknown"]


def test_classifier_includes_packaged_skills_from_commit_scope(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    rows = {row.path: row for row in primitive_scope_classifier.build_rows(root)}

    package = rows["packages/quality/skills/portable-package/SKILL.md"]
    assert package.suggested_scope == "both"
    assert package.effective_scope == "both"
    assert package.paired_portability_test == "tests/red_team/portability/test_package_skill_quality_portable_package.py"
    assert any(item.source == "lifecycle" for item in package.evidence)


def test_conflicting_consumer_and_lifecycle_evidence_becomes_unknown(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "scripts" / "conflict.py").write_text("#!/usr/bin/env python3\n# SCOPE: both\nprint('conflict')\n")

    consumer_path = root / "manifests" / "primitive-consumer-availability.yaml"
    consumer = yaml.safe_load(consumer_path.read_text())
    consumer["items"].append({"path": "scripts/conflict.py", "status": "maintainer-only", "rationale": "synthetic conflict"})
    consumer_path.write_text(yaml.safe_dump(consumer))

    lifecycle_path = root / "manifests" / "primitive-lifecycle.yaml"
    lifecycle = yaml.safe_load(lifecycle_path.read_text())
    lifecycle["primitives"].append(
        {
            "id": "scripts/conflict.py",
            "kind": "script",
            "distribution": "team",
            "lifecycle_state": "candidate",
            "consumer_accessibility": "lifecycle-declared-shared-surface",
        }
    )
    lifecycle_path.write_text(yaml.safe_dump(lifecycle))

    row = {row.path: row for row in primitive_scope_classifier.build_rows(root)}["scripts/conflict.py"]

    assert row.suggested_scope == "unknown"
    assert row.effective_scope == "os-only"
    assert row.decision_source == "conflicting-distribution-evidence"
    assert "resolve conflicting" in row.next_action


def test_declared_project_without_metadata_stays_visible_as_project_pending_proof(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "hooks" ).mkdir(exist_ok=True)
    (root / "hooks" / "project-only.sh").write_text("#!/usr/bin/env bash\n# SCOPE: project\necho project\n")

    row = {row.path: row for row in primitive_scope_classifier.build_rows(root)}["hooks/project-only.sh"]

    assert row.suggested_scope == "project"
    assert row.effective_scope == "project"
    assert row.confidence == "low"
    assert row.decision_source == "declared-project-pending-proof"
    assert "consumer-project-only" in row.next_action


def test_projectable_consumer_status_is_project_not_both(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "scripts" / "consumer_tool.py").write_text("#!/usr/bin/env python3\n# SCOPE: project\nprint('consumer')\n")

    consumer_path = root / "manifests" / "primitive-consumer-availability.yaml"
    consumer = yaml.safe_load(consumer_path.read_text())
    consumer["items"].append({"path": "scripts/consumer_tool.py", "status": "shell-ci-candidate", "rationale": "synthetic project tool"})
    consumer_path.write_text(yaml.safe_dump(consumer))

    row = {row.path: row for row in primitive_scope_classifier.build_rows(root)}["scripts/consumer_tool.py"]

    assert row.suggested_scope == "project"
    assert row.effective_scope == "project"
    assert any(item.source == "consumer-availability" and item.scope == "project" for item in row.evidence)


def test_lifecycle_consumer_candidate_is_project_not_both(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "scripts" / "consumer_candidate.py").write_text("#!/usr/bin/env python3\n# SCOPE: project\nprint('consumer')\n")

    lifecycle_path = root / "manifests" / "primitive-lifecycle.yaml"
    lifecycle = yaml.safe_load(lifecycle_path.read_text())
    lifecycle["primitives"].append(
        {
            "id": "scripts/consumer_candidate.py",
            "kind": "script",
            "distribution": "team",
            "lifecycle_state": "candidate",
            "consumer_accessibility": "lifecycle-declared-consumer-candidate",
        }
    )
    lifecycle_path.write_text(yaml.safe_dump(lifecycle))

    row = {row.path: row for row in primitive_scope_classifier.build_rows(root)}["scripts/consumer_candidate.py"]

    assert row.suggested_scope == "project"
    assert row.effective_scope == "project"
    assert any(item.source == "lifecycle" and item.scope == "project" for item in row.evidence)


def test_lifecycle_distribution_tier_is_not_scope_evidence(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "skills" / "lab-tool").mkdir(parents=True)
    (root / "skills" / "lab-tool" / "SKILL.md").write_text(
        "<!-- SCOPE: both -->\n---\nname: lab-tool\n---\nReusable but opt-in.\n"
    )

    lifecycle_path = root / "manifests" / "primitive-lifecycle.yaml"
    lifecycle = yaml.safe_load(lifecycle_path.read_text())
    lifecycle["primitives"].append(
        {
            "id": "skills/lab-tool/SKILL.md",
            "kind": "skill",
            "distribution": "lab",
            "lifecycle_state": "advisory",
        }
    )
    lifecycle_path.write_text(yaml.safe_dump(lifecycle))

    row = {row.path: row for row in primitive_scope_classifier.build_rows(root)}["skills/lab-tool/SKILL.md"]

    assert row.suggested_scope == "unknown"
    assert row.effective_scope == "os-only"
    assert not any(item.source == "lifecycle" and item.scope == "os-only" for item in row.evidence)


def test_lab_distribution_with_shared_accessibility_remains_both(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "skills" / "lab-shared").mkdir(parents=True)
    (root / "skills" / "lab-shared" / "SKILL.md").write_text(
        "<!-- SCOPE: both -->\n---\nname: lab-shared\n---\nReusable but opt-in.\n"
    )
    proof = root / "tests" / "red_team" / "portability"
    (proof / "test_skill_lab_shared.py").write_text("def test_lab_shared(): pass\n")

    lifecycle_path = root / "manifests" / "primitive-lifecycle.yaml"
    lifecycle = yaml.safe_load(lifecycle_path.read_text())
    lifecycle["primitives"].append(
        {
            "id": "skills/lab-shared/SKILL.md",
            "kind": "skill",
            "distribution": "lab",
            "lifecycle_state": "advisory",
            "consumer_accessibility": "lifecycle-declared-shared-surface",
        }
    )
    lifecycle_path.write_text(yaml.safe_dump(lifecycle))

    row = {row.path: row for row in primitive_scope_classifier.build_rows(root)}["skills/lab-shared/SKILL.md"]

    assert row.suggested_scope == "both"
    assert row.effective_scope == "both"
    assert any(item.source == "lifecycle" and item.scope == "both" for item in row.evidence)
