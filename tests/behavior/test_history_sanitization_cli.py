from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "cos-history-sanitization"
COS = ROOT / "scripts" / "cos"
MACOS_HOME = "/" + "Users/example/repo"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, check=False)


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "manifests").mkdir()
    _git(repo, "init").check_returncode()
    _git(repo, "config", "user.email", "test@example.com").check_returncode()
    _git(repo, "config", "user.name", "Test User").check_returncode()
    (repo / "README.md").write_text("local=" + MACOS_HOME + "\nlicense=Apache-2.0\n", encoding="utf-8")
    _git(repo, "add", "README.md").check_returncode()
    _git(repo, "commit", "-m", "seed").check_returncode()
    manifest = {
        "schema_version": "history-sanitization/v1",
        "rules": [{"id": "operator-email", "mode": "literal", "value_env": "COS_HISTORY_SANITIZE_OPERATOR_EMAIL", "replacement": "2144218+MatiasNAmendola@users.noreply.github.com", "required": False}],
        "sensitive_history_patterns": [{"id": "home", "mode": "regex", "pattern": r"/U[s]ers/[^/ ]+", "severity": "warn"}],
        "preserve": [{"id": "license-transition", "mode": "regex", "pattern": r"Apache-2\.0|FSL-1\.1"}],
        "execution": {"require_env": "COS_ALLOW_DESTRUCTIVE_GIT", "require_env_value": "1"},
    }
    (repo / "manifests" / "history-sanitization.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return repo


def test_history_sanitization_cli_dry_run_json_is_non_mutating(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    before = _git(repo, "rev-parse", "HEAD").stdout.strip()
    proc = subprocess.run([str(CLI), "--project-dir", str(repo), "--dry-run", "--json"], text=True, capture_output=True, check=False)
    after = _git(repo, "rev-parse", "HEAD").stdout.strip()
    assert proc.returncode == 0
    assert before == after
    report = json.loads(proc.stdout)
    assert report["schema_version"] == "history-sanitization-report/v1"
    assert report["mode"] == "dry-run"


def test_history_sanitization_cli_execute_without_env_blocks(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    env = dict(os.environ)
    env.pop("COS_ALLOW_DESTRUCTIVE_GIT", None)
    proc = subprocess.run([str(CLI), "--project-dir", str(repo), "--execute", "--json", "--adr-ref", "ADR-269"], text=True, capture_output=True, check=False, env=env)
    assert proc.returncode == 2
    report = json.loads(proc.stdout)
    assert report["status"] == "block"
    assert any(finding["code"] == "destructive-git-env-missing" for finding in report["findings"])


def test_cos_history_route_smoke_json() -> None:
    proc = subprocess.run([str(COS), "history", "sanitize", "--dry-run", "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    assert proc.returncode in {0, 2}
    report = json.loads(proc.stdout)
    assert report["schema_version"] == "history-sanitization-report/v1"
    assert report["mode"] == "dry-run"
