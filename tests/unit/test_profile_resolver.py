from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from lib.adaptive_profile import resolve_profile

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos-profile-explain"


def git(project: Path, *args: str) -> None:
    result = subprocess.run(["git", *args], cwd=project, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr


def repo(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    git(project, "init", "-b", "feature/profile")
    git(project, "config", "user.email", "profile@example.invalid")
    git(project, "config", "user.name", "Profile Test")
    (project / "README.md").write_text("ok\n", encoding="utf-8")
    git(project, "add", "README.md")
    git(project, "commit", "-m", "init")
    return project


def test_clean_feature_branch_resolves_lean(tmp_path: Path) -> None:
    payload = resolve_profile(repo(tmp_path))

    assert payload["profile"] == "lean"
    assert payload["reasons"] == ["clean low-risk feature work"]


def test_lean_profile_keeps_secret_and_destructive_protections(tmp_path: Path) -> None:
    payload = resolve_profile(repo(tmp_path))

    assert payload["profile"] == "lean"
    policy = payload["guard_policy"]
    assert policy["blocking_posture"] == "baseline-safety-only"
    protected = {item["risk"]: item["hook"] for item in policy["minimum_protections"]}
    assert protected["secrets"] == "secret-detector"
    assert protected["destructive_git"] == "destructive-git-blocker"
    assert protected["destructive_rm"] == "destructive-rm-blocker"
    assert protected["untracked_work_loss"] == "untracked-work-preservation-guard"


def test_dirty_worktree_resolves_standard(tmp_path: Path) -> None:
    project = repo(tmp_path)
    (project / "README.md").write_text("dirty\n", encoding="utf-8")

    payload = resolve_profile(project)

    assert payload["profile"] == "standard"
    assert "dirty worktree" in payload["reasons"]


def test_landing_intent_resolves_strict(tmp_path: Path) -> None:
    payload = resolve_profile(repo(tmp_path), landing_intent=True)

    assert payload["profile"] == "strict"
    assert "landing intent" in payload["reasons"]


def test_profile_explain_json_cli(tmp_path: Path) -> None:
    project = repo(tmp_path)

    result = subprocess.run([str(SCRIPT), "--project-dir", str(project), "--json"], cwd=REPO, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "adaptive-profile.v1"
    assert payload["profile"] == "lean"
    assert payload["guard_policy"]["blocking_posture"] == "baseline-safety-only"


def test_profile_explain_human_output_lists_minimum_protections(tmp_path: Path) -> None:
    project = repo(tmp_path)

    result = subprocess.run([str(SCRIPT), "--project-dir", str(project)], cwd=REPO, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr
    assert "blocking_posture: baseline-safety-only" in result.stdout
    assert "secrets: secret-detector" in result.stdout
    assert "destructive_git: destructive-git-blocker" in result.stdout


def test_active_resource_lease_resolves_strict(tmp_path: Path) -> None:
    project = repo(tmp_path)
    leases = project / ".cognitive-os" / "runtime" / "resource-leases"
    leases.mkdir(parents=True)
    (leases / "hooks.json").write_text(
        json.dumps({"resource": "hooks", "expires_at": 4102444800}) + "\n",
        encoding="utf-8",
    )

    payload = resolve_profile(project)

    assert payload["profile"] == "strict"
    assert payload["signals"]["active_resource_leases"] == 1
    assert "active resource leases=1" in payload["reasons"]


def test_high_risk_changed_surface_resolves_strict(tmp_path: Path) -> None:
    project = repo(tmp_path)
    hooks = project / "hooks"
    hooks.mkdir()
    (hooks / "new-hook.sh").write_text("echo hook\n", encoding="utf-8")

    payload = resolve_profile(project)

    assert payload["profile"] == "strict"
    assert "hooks" in payload["signals"]["high_risk_surfaces"]
    assert "high-risk changed surfaces=hooks" in payload["reasons"]


def test_stash_signal_resolves_standard(tmp_path: Path) -> None:
    project = repo(tmp_path)
    (project / "README.md").write_text("stash me\n", encoding="utf-8")
    git(project, "stash", "push", "-m", "manual stash")

    payload = resolve_profile(project)

    assert payload["profile"] == "standard"
    assert payload["signals"]["stash_count"] == 1
    assert "stashes=1" in payload["reasons"]


def test_pre_agent_marker_resolves_strict(tmp_path: Path) -> None:
    project = repo(tmp_path)
    markers = project / ".cognitive-os" / "pre-agent-markers"
    markers.mkdir(parents=True)
    (markers / "agent-a.json").write_text("{}\n", encoding="utf-8")

    payload = resolve_profile(project)

    assert payload["profile"] == "strict"
    assert payload["signals"]["pre_agent_marker_count"] == 1
    assert "pre-agent markers=1" in payload["reasons"]


def test_operator_override_is_logged_and_scoped(tmp_path: Path) -> None:
    project = repo(tmp_path)

    payload = resolve_profile(project, override="standard", override_ttl_seconds=60)

    assert payload["profile"] == "standard"
    assert payload["override"] is True
    assert payload["override_scope"] == str(project.resolve())
    assert payload["override_expires_at"] is not None
    rows = [
        json.loads(line)
        for line in (project / ".cognitive-os" / "metrics" / "adaptive-profile-overrides.jsonl").read_text().splitlines()
    ]
    assert rows[-1]["profile"] == "standard"
    assert rows[-1]["project_dir"] == str(project.resolve())
