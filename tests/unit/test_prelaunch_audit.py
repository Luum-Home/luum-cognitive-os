"""Tests for prelaunch history and message audit tooling."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lib.prelaunch_audit import audit_history, audit_messages, build_rewrite_plan, apply_rewrite


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True)


def _init_repo(repo: Path) -> Path:
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    return repo


def test_message_audit_flags_quote_mine_risk(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("demo\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "wip: preserve FSL license switch stash")

    report = audit_messages(repo)

    assert report["status"] in {"pass", "warn"}
    finding = report["findings"][0]
    assert finding["rule_id"] in {"wip-message", "license-switch-message"}
    assert finding.get("suggested_rewrite")


@pytest.mark.parametrize(
    ("content", "expected_rule"),
    [
        ("OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz\n", "openai-token"),
        ("path=" + "/" + "Users/privateperson/Projects/customer-app\n", "local-home-path"),
    ],
)
def test_history_audit_flags_sensitive_content(tmp_path: Path, content: str, expected_rule: str) -> None:
    repo = _init_repo(tmp_path)
    (repo / "notes.txt").write_text(content, encoding="utf-8")
    _git(repo, "add", "notes.txt")
    _git(repo, "commit", "-m", "add notes")

    report = audit_history(repo)

    assert any(finding["rule_id"] == expected_rule for finding in report["findings"])


def test_rewrite_plan_writes_editable_files(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("demo\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "feat(license): switch from Apache 2.0 to FSL-1.1-MIT")

    plan = build_rewrite_plan(repo)

    plan_dir = repo / ".cognitive-os/prelaunch"
    assert (plan_dir / "message-rewrites.json").exists()
    assert (plan_dir / "replacements.txt").exists()
    assert (plan_dir / "remote-snapshot.json").exists()
    assert (plan_dir / "branch-upstream-snapshot.json").exists()
    assert plan["message_rewrites"]
    assert plan["remotes"] == []
    assert plan["branch_upstreams"] == []
    assert plan["message_rewrites"][0]["new"] == "chore(license): establish FSL-1.1-MIT before public launch"


def test_rewrite_plan_snapshots_remotes(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], text=True, capture_output=True, check=True)
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "README.md").write_text("demo\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "normal commit")
    _git(repo, "remote", "add", "origin", str(remote))

    plan = build_rewrite_plan(repo)

    snapshot = json.loads((repo / ".cognitive-os/prelaunch/remote-snapshot.json").read_text(encoding="utf-8"))
    assert plan["remotes"] == ["origin"]
    assert snapshot["origin"]["fetch"] == str(remote)


def test_rewrite_plan_snapshots_branch_upstreams(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], text=True, capture_output=True, check=True)
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "README.md").write_text("demo\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "normal commit")
    branch = _git(repo, "branch", "--show-current").stdout.strip()
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", f"HEAD:{branch}")

    plan = build_rewrite_plan(repo)

    snapshot = json.loads((repo / ".cognitive-os/prelaunch/branch-upstream-snapshot.json").read_text(encoding="utf-8"))
    assert plan["current_branch"] == branch
    assert plan["branch_upstreams"] == [branch]
    assert snapshot["branches"][branch]["remote"] == "origin"
    assert snapshot["branches"][branch]["merge"] == f"refs/heads/{branch}"


def test_apply_rewrite_dry_run_requires_no_env(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("demo\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "feat(license): switch from Apache 2.0 to FSL-1.1-MIT")
    build_rewrite_plan(repo)

    result = apply_rewrite(repo, dry_run=True)

    assert result["status"] == "dry-run"
    assert result["message_rewrites"] == 1


def test_apply_rewrite_without_flag_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("demo\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "feat(license): switch from Apache 2.0 to FSL-1.1-MIT")
    build_rewrite_plan(repo)
    monkeypatch.delenv("COS_ALLOW_PRELAUNCH_REWRITE", raising=False)

    with pytest.raises(SystemExit, match="COS_ALLOW_PRELAUNCH_REWRITE=1"):
        apply_rewrite(repo)


def test_apply_rewrite_restores_remotes_after_filter_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if not shutil.which("git-filter-repo"):
        pytest.skip("git-filter-repo is required for rewrite execution")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], text=True, capture_output=True, check=True)
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "notes.txt").write_text("private-token-before-public\n", encoding="utf-8")
    _git(repo, "add", "notes.txt")
    _git(repo, "commit", "-m", "seed")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "HEAD:main")
    _git(repo, "branch", "--set-upstream-to=origin/main")
    plan_dir = tmp_path / "rewrite-plan"
    plan_dir.mkdir(parents=True)
    (plan_dir / "replacements.txt").write_text(
        "private-token-before-public==>private-token-redacted\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("COS_ALLOW_PRELAUNCH_REWRITE", "1")
    monkeypatch.delenv("COS_ALLOW_PRELAUNCH_FORCE_PUSH", raising=False)

    result = apply_rewrite(repo, plan_dir=plan_dir)

    assert result["status"] == "rewritten"
    assert result["remotes_restored"] == ["origin"]
    assert result["remote_restore_issues"] == []
    assert result["branch_upstream_restore_issues"] == []
    restored_origin = _git(repo, "remote", "get-url", "origin").stdout.strip()
    assert restored_origin == str(remote)
    assert _git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}").stdout.strip() == "origin/main"


def test_message_audit_cli_imports_from_repo_root(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("demo\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "normal commit")
    project_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [str(project_root / "scripts/prelaunch-message-audit"), "--repo", str(repo), "--json"],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert '"audit": "messages"' in result.stdout


def test_history_audit_downgrades_fixture_like_secret_material(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "fixture.go").write_text(
        'writeFile(t, dir, "key.pem", "-----BEGIN RSA PRIVATE KEY-----\\ndata\\n-----END RSA PRIVATE KEY-----")\n',
        encoding="utf-8",
    )
    _git(repo, "add", "fixture.go")
    _git(repo, "commit", "-m", "add scanner fixture")

    report = audit_history(repo)

    private_key_finding = next(f for f in report["findings"] if f["rule_id"] == "private-key-material")
    assert private_key_finding["severity"] == "info"
    hit = next(h for h in report["rule_hits"] if h["rule_id"] == "private-key-material")
    assert hit["risky_commit_count"] == 0
    assert hit["fixture_like_commit_count"] == 1


def test_history_audit_keeps_non_fixture_secret_assignment_blocking(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "config.txt").write_text('token = "real-looking-token-value-ZYXWVUT98765"\n', encoding="utf-8")
    _git(repo, "add", "config.txt")
    _git(repo, "commit", "-m", "add config")

    report = audit_history(repo)

    finding = next(f for f in report["findings"] if f["rule_id"] == "env-assignment-secret")
    assert finding["severity"] == "block"


def test_history_audit_downgrades_known_dev_credentials(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "docker-compose.yml").write_text(
        '# UI: http://localhost:8888 (token: cognitive-os-dev)\n'
        'password="langfuse_pass"\n'
        'Auth password: langfuse_redis\n',
        encoding="utf-8",
    )
    _git(repo, "add", "docker-compose.yml")
    _git(repo, "commit", "-m", "add dev compose fixture")

    report = audit_history(repo)

    env_finding = next(f for f in report["findings"] if f["rule_id"] == "env-assignment-secret")
    assert env_finding["severity"] == "info"
    hit = next(h for h in report["rule_hits"] if h["rule_id"] == "env-assignment-secret")
    assert hit["risky_commit_count"] == 0


def test_history_audit_downgrades_reviewed_privacy_and_trust_context(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "TRANSPARENCY.md").write_text(
        '> (`reviewer@gmail.com`) appears **2 times** in `git log -p`, not a leak.\n'
        '- cd ' + '/' + 'Users/exampleuser/Projects/luum-agent-os\n'
        '+ Claiming "100% confident" is a RED FLAG.\n',
        encoding="utf-8",
    )
    _git(repo, "add", "TRANSPARENCY.md")
    _git(repo, "commit", "-m", "document reviewed audit context")

    report = audit_history(repo)

    for rule_id in {"personal-email", "local-home-path", "absolute-claim-content"}:
        finding = next(f for f in report["findings"] if f["rule_id"] == rule_id)
        assert finding["severity"] == "info"
