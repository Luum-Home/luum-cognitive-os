"""Unit tests for ADR-199 state retention audit and stash cleanup."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "state_retention_audit.py"
MANIFEST = ROOT / "manifests" / "state-retention.yaml"


def run_cmd(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, env=merged)


def git(repo: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = run_cmd(["git", *args], repo, env=env)
    assert result.returncode == 0, result.stderr or result.stdout
    return result


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test User")
    (tmp_path / "README.md").write_text("base\n", encoding="utf-8")
    git(tmp_path, "add", "README.md")
    git(tmp_path, "commit", "-m", "initial")
    return tmp_path


def make_stash(repo: Path, name: str, filename: str, content: str, hours_ago: int = 2) -> None:
    # git stash does not include untracked files by default; track each test file
    # first so the retention path exercises normal tracked WIP stashes.
    target = repo / filename
    target.write_text("base\n", encoding="utf-8")
    git(repo, "add", filename)
    git(repo, "commit", "-m", f"track {filename}")
    target.write_text(content, encoding="utf-8")
    stamp = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%S +0000")
    git(repo, "stash", "push", "-m", name, env={"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp})


def manifest_with_zero_stash_ttl(tmp_path: Path) -> Path:
    text = MANIFEST.read_text(encoding="utf-8")
    text = text.replace("max_age: P1H", "max_age: P0H", 1)
    manifest = tmp_path / "state-retention.yaml"
    manifest.write_text(text, encoding="utf-8")
    return manifest


def run_audit(repo: Path, *args: str, manifest: Path = MANIFEST) -> subprocess.CompletedProcess[str]:
    return run_cmd([sys.executable, str(SCRIPT), "--project-dir", str(repo), "--manifest", str(manifest), *args], ROOT)


def parse_json(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.returncode in (0, 2), result.stderr
    return json.loads(result.stdout)


def test_manifest_declares_required_surface_fields() -> None:
    result = run_audit(ROOT, "--json", "--no-metrics")
    payload = parse_json(result)
    assert payload["manifest_findings"] == []
    surfaces = {surface["surface"] for surface in payload["surfaces"]}
    assert "auto-pre-agent-stashes" in surfaces
    assert "task-claims-ledger" in surfaces
    assert "agent-bus-directories" in surfaces


def test_stash_cleanup_preview_selects_only_stale_auto_pre_agent(git_repo: Path, tmp_path: Path) -> None:
    make_stash(git_repo, "manual-preserve-important", "manual.txt", "manual\n")
    make_stash(git_repo, "auto-pre-agent-toolu_abc", "auto.txt", "auto\n")
    time.sleep(1.1)

    result = run_audit(git_repo, "--surface", "auto-pre-agent-stashes", "--reap", "--json", "--no-metrics", manifest=manifest_with_zero_stash_ttl(tmp_path))
    payload = parse_json(result)

    assert payload["reap"][0]["candidate_count"] == 1
    actions = payload["reap"][0]["actions"]
    assert len(actions) == 1
    assert "auto-pre-agent-toolu_abc" in actions[0]["subject"]
    assert actions[0]["execute"] is False
    assert "manual-preserve-important" not in json.dumps(actions)

    stash_list = git(git_repo, "stash", "list").stdout
    assert "manual-preserve-important" in stash_list
    assert "auto-pre-agent-toolu_abc" in stash_list


def test_stash_cleanup_execute_archives_then_drops_only_auto_stash(git_repo: Path, tmp_path: Path) -> None:
    make_stash(git_repo, "manual-preserve-important", "manual.txt", "manual\n")
    make_stash(git_repo, "auto-pre-agent-toolu_abc", "auto.txt", "auto\n")
    time.sleep(1.1)

    result = run_audit(git_repo, "--surface", "auto-pre-agent-stashes", "--reap", "--execute", "--json", "--no-metrics", manifest=manifest_with_zero_stash_ttl(tmp_path))
    payload = parse_json(result)
    action = payload["reap"][0]["actions"][0]

    assert action["dropped"] is True
    assert action["preserved_ref"].startswith("refs/cos-preserved-stash/")
    assert (git_repo / action["patch"]).is_file()
    assert (git_repo / action["name_status"]).is_file()
    assert git(git_repo, "rev-parse", action["preserved_ref"]).stdout.strip() == action["sha"]

    stash_list = git(git_repo, "stash", "list").stdout
    assert "auto-pre-agent-toolu_abc" not in stash_list
    assert "manual-preserve-important" in stash_list


def test_claim_ledger_compaction_dry_run_reports_terminal_records(git_repo: Path) -> None:
    claims_path = git_repo / ".cognitive-os" / "tasks" / "active-claims.json"
    claims_path.parent.mkdir(parents=True)
    old = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    claims_path.write_text(json.dumps({"claims": [{"task_id": "a", "status": "released", "released_at": old}, {"task_id": "b", "status": "active"}]}) + "\n", encoding="utf-8")

    result = run_audit(git_repo, "--surface", "task-claims-ledger", "--reap", "--json", "--no-metrics")
    payload = parse_json(result)

    assert payload["surfaces"][0]["old_terminal_count"] == 1
    assert payload["reap"][0]["removed"] == 1
    assert json.loads(claims_path.read_text(encoding="utf-8"))["claims"][0]["task_id"] == "a"


def test_auto_safe_selects_only_repair_safe_surfaces(git_repo: Path) -> None:
    claims_path = git_repo / ".cognitive-os" / "tasks" / "active-claims.json"
    claims_path.parent.mkdir(parents=True)
    old = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    claims_path.write_text(json.dumps({"claims": [{"task_id": "a", "status": "released", "released_at": old}]}) + "\n", encoding="utf-8")
    bus_dir = git_repo / ".cognitive-os" / "agent-bus" / "old-agent"
    bus_dir.mkdir(parents=True)

    result = run_audit(git_repo, "--auto-safe", "--reap", "--json", "--no-metrics")
    payload = parse_json(result)

    # Derive the expectation from the manifest instead of hardcoding a surface
    # list: --auto-safe must select exactly the repair-safe surfaces, whichever
    # those are. A literal set here silently turns every newly-registered
    # retention surface into a test failure, which is what previously
    # discouraged registering surfaces at all.
    manifest = yaml.safe_load(
        (ROOT / "manifests" / "state-retention.yaml").read_text(encoding="utf-8")
    )
    expected = {
        surface["id"]
        for surface in manifest["surfaces"]
        if surface.get("retention_mode") == "repair-safe"
    }
    assert expected, "manifest must declare at least one repair-safe surface"

    surfaces = {surface["surface"] for surface in payload["surfaces"]}
    assert surfaces == expected
    assert {item["surface"] for item in payload["reap"]} == expected


def test_repair_before_block_selects_only_auto_stash_surface(git_repo: Path, tmp_path: Path) -> None:
    make_stash(git_repo, "auto-pre-agent-toolu_repair", "repair.txt", "repair\n")
    time.sleep(1.1)

    result = run_audit(
        git_repo,
        "--repair-before-block",
        "--reap",
        "--json",
        "--no-metrics",
        manifest=manifest_with_zero_stash_ttl(tmp_path),
    )
    payload = parse_json(result)

    assert [surface["surface"] for surface in payload["surfaces"]] == ["auto-pre-agent-stashes"]
    assert payload["reap"][0]["candidate_count"] == 1


def test_auto_safe_execute_sets_cooldown_and_skips_second_run(git_repo: Path) -> None:
    claims_path = git_repo / ".cognitive-os" / "tasks" / "active-claims.json"
    claims_path.parent.mkdir(parents=True)
    old = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    claims_path.write_text(json.dumps({"claims": [{"task_id": "cool", "status": "released", "released_at": old}]}) + "\n", encoding="utf-8")

    first = run_audit(
        git_repo,
        "--auto-safe",
        "--reap",
        "--execute",
        "--json",
        "--no-metrics",
        "--cooldown-seconds",
        "300",
    )
    first_payload = parse_json(first)
    assert first_payload["cooldown_skipped"] is False
    assert any(item["surface"] == "task-claims-ledger" and item["removed"] == 1 for item in first_payload["reap"])

    # Re-add eligible terminal state immediately. Cooldown must prevent an
    # automatic repair storm from repeatedly mutating state in the same window.
    claims_path.write_text(json.dumps({"claims": [{"task_id": "cool2", "status": "released", "released_at": old}]}) + "\n", encoding="utf-8")
    second = run_audit(
        git_repo,
        "--auto-safe",
        "--reap",
        "--execute",
        "--json",
        "--no-metrics",
        "--cooldown-seconds",
        "300",
    )
    second_payload = parse_json(second)
    assert second_payload["cooldown_skipped"] is True
    assert second_payload["reap"] == []
    assert json.loads(claims_path.read_text(encoding="utf-8"))["claims"][0]["task_id"] == "cool2"


# --- global budget (tree ceiling vs per-surface caps) -----------------------
#
# Regression guard for the defect where every surface was inside its own cap,
# the audit reported findings=0, and the tree was over the .cognitive-os
# ceiling anyway. The audit checked each surface and never summed them.

MIB = 1024 * 1024


def _write_mib(path: Path, mib: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * int(mib * MIB))


def _budget_manifest(tmp_path: Path, *, ceiling_mib: float, unregistered_cap_mib: float | None = None) -> Path:
    """Manifest with two byte-capped surfaces; caller controls the tree ceiling."""
    def surface(sid: str, glob: str) -> dict:
        return {
            "id": sid, "kind": "artifact-pool", "path": glob,
            "max_age": "P7D", "max_count": 100, "max_total_mib": 2,
            "reaper": "manual", "retention_mode": "observe",
            "tombstone": "none-recovery-artifact", "owner_pid": False,
            "owner_files": ["scripts/state_retention_audit.py"],
            "documentation": ["docs/04-Concepts/architecture/state-retention.md"],
        }

    budget: dict = {
        "path": ".cognitive-os", "max_total_mib": ceiling_mib,
        "measurement": "allocated-blocks", "env_override": "COS_VITALS_DISK_CEILING_MIB",
    }
    if unregistered_cap_mib is not None:
        budget["max_unregistered_mib"] = unregistered_cap_mib
    data = {
        "schema_version": "state-retention.v1",
        "global_budget": budget,
        "surfaces": [
            surface("pool-a", ".cognitive-os/pool-a/*"),
            surface("pool-b", ".cognitive-os/pool-b/*"),
        ],
    }
    manifest = tmp_path / "budget-manifest.yaml"
    manifest.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return manifest


def _budget_tree(tmp_path: Path) -> Path:
    """Every surface at 1.5 MiB — inside its own 2 MiB cap, 3.0 MiB together."""
    project = tmp_path / "project"
    _write_mib(project / ".cognitive-os" / "pool-a" / "entry-1", 1.5)
    _write_mib(project / ".cognitive-os" / "pool-b" / "entry-1", 1.5)
    return project


def _global_row(payload: dict) -> dict:
    rows = [row for row in payload["surfaces"] if row.get("kind") == "budget"]
    assert len(rows) == 1, f"expected exactly one global budget row, got {rows}"
    return rows[0]


def test_global_budget_flags_tree_over_ceiling_when_every_surface_is_within_cap(tmp_path: Path) -> None:
    project = _budget_tree(tmp_path)
    manifest = _budget_manifest(tmp_path, ceiling_mib=2)
    payload = parse_json(run_audit(project, "--json", "--no-metrics", manifest=manifest))

    # Premise of the defect: nobody is individually at fault.
    per_surface = [row for row in payload["surfaces"] if row.get("kind") != "budget"]
    assert len(per_surface) == 2
    assert all(row["findings"] == [] for row in per_surface), per_surface

    row = _global_row(payload)
    assert row["total_mib"] >= 3.0, row
    codes = [f["code"] for f in row["findings"]]
    assert codes == ["global-budget-exceeded"], row["findings"]
    finding = row["findings"][0]
    assert finding["level"] == "BLOCK"
    assert finding["max_total_mib"] == 2.0
    assert finding["over_by_mib"] > 0
    # No surface to blame must be stated, not implied.
    assert finding["attributable_surfaces"] == []
    assert "no single surface is at fault" in finding["message"]
    # Both real exits are offered, and neither is "lower a cap below usage".
    assert len(finding["remedies"]) == 2
    assert any("max_total_mib" in r for r in finding["remedies"])
    # The finding is counted like any other, not sidelined.
    assert payload["summary"]["finding_count"] == 1
    # Surface count still names surfaces only.
    assert payload["summary"]["surface_count"] == 2


def test_global_budget_silent_when_tree_is_under_ceiling(tmp_path: Path) -> None:
    project = _budget_tree(tmp_path)
    manifest = _budget_manifest(tmp_path, ceiling_mib=50)
    payload = parse_json(run_audit(project, "--json", "--no-metrics", manifest=manifest))

    row = _global_row(payload)
    assert row["findings"] == [], row
    assert payload["summary"]["finding_count"] == 0
    assert row["registered_mib"] >= 3.0
    assert row["unregistered_mib"] == 0.0


def test_global_budget_reports_bytes_no_registered_surface_owns(tmp_path: Path) -> None:
    project = _budget_tree(tmp_path)
    _write_mib(project / ".cognitive-os" / "orphan-area" / "blob", 1.0)
    manifest = _budget_manifest(tmp_path, ceiling_mib=50, unregistered_cap_mib=0.5)
    payload = parse_json(run_audit(project, "--json", "--no-metrics", manifest=manifest))

    row = _global_row(payload)
    assert row["unregistered_mib"] >= 1.0, row
    codes = [f["code"] for f in row["findings"]]
    assert codes == ["global-unregistered-bytes"], row["findings"]
    assert row["findings"][0]["top_areas"][0]["area"].startswith("orphan-area")


def test_global_budget_ceiling_comes_from_the_manifest_not_the_script(tmp_path: Path) -> None:
    """The number has one source; the env override moves it for both consumers."""
    project = _budget_tree(tmp_path)
    manifest = _budget_manifest(tmp_path, ceiling_mib=2)
    payload = parse_json(run_audit(project, "--json", "--no-metrics", manifest=manifest))
    assert _global_row(payload)["max_total_mib"] == 2.0

    override = run_cmd(
        [sys.executable, str(SCRIPT), "--project-dir", str(project), "--manifest", str(manifest), "--json", "--no-metrics"],
        ROOT,
        env={"COS_VITALS_DISK_CEILING_MIB": "500"},
    )
    row = _global_row(parse_json(override))
    assert row["max_total_mib"] == 500.0
    assert row["findings"] == []


def test_repo_manifest_declares_the_global_budget_the_ram_ceiling_test_reads() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    budget = data.get("global_budget")
    assert budget, "manifests/state-retention.yaml must declare global_budget"
    assert budget["path"] == ".cognitive-os"
    assert float(budget["max_total_mib"]) > 0
    assert budget["env_override"] == "COS_VITALS_DISK_CEILING_MIB"
