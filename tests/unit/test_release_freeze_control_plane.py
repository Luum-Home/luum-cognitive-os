from __future__ import annotations

from pathlib import Path

import yaml

from lib.release_freeze import prepare


def test_release_freeze_runs_pre_public_control_plane_when_enabled(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    import subprocess
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo, check=True)
    (repo / "README.md").write_text("hi\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    (repo / "manifests").mkdir()
    command = repo / "fake-pre-public.sh"
    command.write_text("#!/usr/bin/env bash\necho '{\"schema_version\":\"control-plane-audit-run/v1\",\"status\":\"block\",\"summary\":{\"block\":1,\"warn\":0,\"findings\":1},\"audits\":[]}'\nexit 1\n", encoding="utf-8")
    command.chmod(0o755)
    manifest = {
        "schema_version": "release-freeze/v1",
        "expected_branch": "main",
        "checks": {
            "clean_worktree": {"enabled": True, "allowlisted_paths": []},
            "branch": {"enabled": True},
            "task_claims": {"enabled": False},
            "agent_heartbeats": {"enabled": False},
            "pre_public_risk_audit": {"enabled": False},
            "primitive_coherence": {"enabled": False},
            "control_plane_pre_public": {"enabled": True, "command": [str(command)]},
        },
    }
    (repo / "manifests" / "release-freeze.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    subprocess.run(["git", "add", "manifests/release-freeze.yaml", "fake-pre-public.sh"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "manifest"], cwd=repo, check=True, capture_output=True)

    report = prepare(repo)

    assert report["status"] == "block"
    assert any(f["code"] == "control_plane_pre_public-failed" for f in report["findings"])
