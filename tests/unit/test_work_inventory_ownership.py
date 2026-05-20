"""ADR-121-S2 WIP ownership inventory coverage."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos_work_inventory.py"


def git(project: Path, *args: str) -> None:
    result = subprocess.run(["git", *args], cwd=project, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr


def make_repo(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    git(project, "init", "-b", "feature/ownership")
    git(project, "config", "user.email", "ownership@example.invalid")
    git(project, "config", "user.name", "Ownership Test")
    (project / "owned.txt").write_text("base\n", encoding="utf-8")
    git(project, "add", "owned.txt")
    git(project, "commit", "-m", "base")
    return project


def run_inventory(project: Path, *extra_args: str) -> dict:
    result = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(project), "--all", "--json", *extra_args],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode in {0, 1, 2}, result.stderr
    return json.loads(result.stdout)


def test_work_inventory_reports_task_claim_owner_and_conflict_action(tmp_path: Path) -> None:
    project = make_repo(tmp_path)
    tasks = project / ".cognitive-os" / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "active-claims.json").write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "task_id": "TASK-OWNED",
                        "session_id": "session-a",
                        "agent_id": "agent-a",
                        "expected_files": ["owned.txt"],
                        "scope": "ownership-test",
                        "status": "active",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = run_inventory(project)

    assert payload["summary"]["claim_count"] == 1
    assert payload["claims"][0]["session_id"] == "session-a"
    assert payload["claims"][0]["expected_files"] == ["owned.txt"]


def test_work_inventory_distinguishes_dirty_wip_with_repair_action(tmp_path: Path) -> None:
    project = make_repo(tmp_path)
    (project / "owned.txt").write_text("dirty\n", encoding="utf-8")

    payload = run_inventory(project)
    finding = next(item for item in payload["findings"] if item["code"] == "worktree-dirty")

    assert finding["level"] == "WARN"
    assert finding["subject"] == "current worktree"
    assert finding["action"] == "Commit, intentionally preserve, or discard current WIP before cleanup."


def test_work_inventory_reports_unknown_user_stash_provenance(tmp_path: Path) -> None:
    project = make_repo(tmp_path)
    (project / "owned.txt").write_text("stash me\n", encoding="utf-8")
    git(project, "stash", "push", "-m", "manual user stash")

    payload = run_inventory(project)

    assert payload["stashes_extended"]
    assert payload["stashes_extended"][0]["provenance_tag"] == "user"
    assert payload["summary"]["stash_count"] >= 1


def test_path_ownership_fails_closed_on_dirty_linked_worktree(tmp_path: Path) -> None:
    project = make_repo(tmp_path)
    linked = tmp_path / "linked"
    git(project, "worktree", "add", "-b", "agent/license-switch", str(linked))
    (linked / "owned.txt").write_text("agent dirty\n", encoding="utf-8")

    payload = run_inventory(project, "--paths", "owned.txt")

    ownership = payload["path_ownership"][0]
    assert ownership["path"] == "owned.txt"
    assert ownership["status"] == "active_or_unknown"
    assert ownership["operator_review_required"] is True
    assert ownership["dirty_worktrees"][0]["path"] == str(linked.resolve())
    assert ownership["edit_lock"]["state"] in {"free", "unknown"}
    assert "Do not clean/drop/merge automatically" in ownership["action"]


def test_path_ownership_reports_stash_temp_branch_as_preservation_not_liveness(tmp_path: Path) -> None:
    project = make_repo(tmp_path)
    git(project, "checkout", "-b", "codex/stash-license-review-test")
    (project / "owned.txt").write_text("preserved copy\n", encoding="utf-8")
    git(project, "add", "owned.txt")
    git(project, "commit", "-m", "preserve test patch")
    git(project, "checkout", "feature/ownership")

    payload = run_inventory(project, "--paths", "owned.txt")

    ownership = payload["path_ownership"][0]
    assert ownership["status"] == "preserved_copy_only"
    assert ownership["preserve_branches"] == ["codex/stash-license-review-test"]
    assert "does not prove the original agent is inactive" in ownership["action"]


def test_path_ownership_includes_stash_agent_heartbeat(tmp_path: Path) -> None:
    project = make_repo(tmp_path)
    metrics = project / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "agent-heartbeat.jsonl").write_text(
        json.dumps(
            {
                "agent_id": "toolu_01ABC",
                "alive": False,
                "event_type": "agent_end",
                "ts": 1234,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (project / "owned.txt").write_text("stash me\n", encoding="utf-8")
    git(project, "stash", "push", "-m", "auto-pre-agent-toolu_01ABC")

    payload = run_inventory(project, "--paths", "owned.txt")

    stash = payload["path_ownership"][0]["stashes"][0]
    assert stash["agent_id"] == "toolu_01ABC"
    assert stash["agent_heartbeat"]["seen"] is True
    assert stash["agent_heartbeat"]["alive"] is False


def test_work_inventory_reports_domain_lease_for_hook_path(tmp_path: Path) -> None:
    project = make_repo(tmp_path)
    leases = project / ".cognitive-os" / "runtime" / "resource-leases"
    leases.mkdir(parents=True)
    (leases / "hooks.json").write_text(
        json.dumps(
            {
                "resource": "hooks",
                "agent_id": "agent-a",
                "session_id": "session-a",
                "reason": "hook edit",
                "expires_at": 4102444800,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = run_inventory(project, "--paths", "hooks/example.sh")

    ownership = payload["path_ownership"][0]
    assert "hooks" in ownership["ownership_domains"]
    assert ownership["domain_leases"][0]["session_id"] == "session-a"
    assert ownership["status"] == "active_or_unknown"
    assert payload["summary"]["resource_lease_count"] == 1


def test_work_inventory_maps_manifests_to_registry_domain(tmp_path: Path) -> None:
    project = make_repo(tmp_path)
    leases = project / ".cognitive-os" / "runtime" / "resource-leases"
    leases.mkdir(parents=True)
    (leases / "registry.json").write_text(
        json.dumps(
            {
                "resource": "registry",
                "agent_id": "agent-r",
                "session_id": "session-r",
                "reason": "registry projection",
                "expires_at": 4102444800,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = run_inventory(project, "--paths", "manifests/primitive-lifecycle.yaml")

    ownership = payload["path_ownership"][0]
    assert "registry" in ownership["ownership_domains"]
    assert ownership["domain_leases"][0]["resource"] == "registry"
