from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

import lib.history_sanitization as hs
from lib.history_sanitization import (
    build_report,
    commit_message_rewrite_enabled,
    load_manifest,
    metadata_rewrite_enabled,
    normalize_pattern,
    preserve_conflicts,
    resolved_rules,
)

MACOS_HOME = "/" + "Users/example/dev/project"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, check=False)


def _make_repo(tmp_path: Path, manifest: dict | None = None) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "manifests").mkdir()
    _git(repo, "init").check_returncode()
    _git(repo, "config", "user.email", "test@example.com").check_returncode()
    _git(repo, "config", "user.name", "Test User").check_returncode()
    payload = "path=" + MACOS_HOME + "\nref=.env\nlicense=Apache-2.0\n"
    (repo / "README.md").write_text(payload, encoding="utf-8")
    _git(repo, "add", "README.md").check_returncode()
    _git(repo, "commit", "-m", "seed").check_returncode()
    data = manifest or {
        "schema_version": "history-sanitization/v1",
        "rules": [
            {"id": "operator-email", "mode": "literal", "value_env": "COS_HISTORY_SANITIZE_OPERATOR_EMAIL", "replacement": "2144218+MatiasNAmendola@users.noreply.github.com", "required": False},
        ],
        "sensitive_history_patterns": [
            {"id": "home", "mode": "regex", "pattern": r"/U[s]ers/[^/ ]+", "severity": "warn"},
            {"id": "env", "mode": "regex", "pattern": r"(^|/|\s)\.env($|\s)", "severity": "warn"},
        ],
        "preserve": [
            {"id": "license-transition", "mode": "regex", "pattern": r"Apache-2\.0|FSL-1\.1"},
        ],
        "execution": {"require_env": "COS_ALLOW_DESTRUCTIVE_GIT", "require_env_value": "1"},
    }
    (repo / "manifests" / "history-sanitization.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return repo


def test_load_manifest_and_normalize_regex(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    manifest = load_manifest(repo)
    assert manifest["schema_version"] == "history-sanitization/v1"
    assert normalize_pattern(r"[^/[:space:]]+") == r"[^/\s]+"


def test_unresolved_env_rule_warns_without_exposing_value(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.delenv("COS_HISTORY_SANITIZE_OPERATOR_EMAIL", raising=False)
    rules, findings = resolved_rules(load_manifest(repo), environ={})
    assert rules[0]["value"] is None
    assert findings[0].severity == "warn"
    assert findings[0].code == "replacement-value-unresolved"


def test_dry_run_reports_sensitive_and_preserve_hits_without_mutating(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    before = _git(repo, "rev-parse", "HEAD").stdout.strip()
    report = build_report(repo, mode="dry-run")
    after = _git(repo, "rev-parse", "HEAD").stdout.strip()
    assert before == after
    assert report["schema_version"] == "history-sanitization-report/v1"
    assert report["status"] == "warn"
    assert any(hit["id"] == "home" and hit["hit_count"] > 0 for hit in report["sensitive_hits"])
    assert any(hit["id"] == "license-transition" and hit["hit_count"] > 0 for hit in report["preserve_hits"])


def test_history_scan_timeout_is_reported_without_hanging(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)

    def fake_git(project_dir: Path, args: list[str], *, timeout_seconds: float | None = None):
        if args and args[0] == "log":
            raise subprocess.TimeoutExpired(cmd=["git", *args], timeout=timeout_seconds or 0)
        return _git(project_dir, *args)

    monkeypatch.setenv("COS_HISTORY_SCAN_TIMEOUT_SECONDS", "0.1")
    monkeypatch.setattr(hs, "git", fake_git)

    report = build_report(repo, mode="dry-run")

    assert report["status"] == "warn"
    assert any(finding["code"] == "history-scan-timeout" for finding in report["findings"])
    assert any(hit["timed_out"] is True and hit["hit_count"] is None for hit in report["sensitive_hits"])



def test_metadata_rewrite_is_disabled_by_default_and_requires_env(monkeypatch) -> None:
    monkeypatch.delenv("COS_HISTORY_SANITIZE_METADATA", raising=False)
    assert metadata_rewrite_enabled({}) is False
    monkeypatch.setenv("COS_HISTORY_SANITIZE_METADATA", "1")
    assert metadata_rewrite_enabled({}) is True


def test_commit_message_rewrite_is_disabled_by_default_and_requires_env(monkeypatch) -> None:
    monkeypatch.delenv("COS_HISTORY_SANITIZE_COMMIT_MESSAGES", raising=False)
    assert commit_message_rewrite_enabled({}) is False
    monkeypatch.setenv("COS_HISTORY_SANITIZE_COMMIT_MESSAGES", "1")
    assert commit_message_rewrite_enabled({}) is True


def test_metadata_scoped_rule_blocks_without_metadata_env(tmp_path: Path, monkeypatch) -> None:
    manifest = {
        "schema_version": "history-sanitization/v1",
        "rules": [
            {
                "id": "operator-author-email",
                "mode": "literal",
                "scope": "metadata",
                "value_env": "COS_HISTORY_SANITIZE_OPERATOR_EMAIL",
                "replacement": "2144218+MatiasNAmendola@users.noreply.github.com",
            }
        ],
        "sensitive_history_patterns": [],
        "preserve": [],
        "execution": {"require_env": "COS_ALLOW_DESTRUCTIVE_GIT", "require_env_value": "1"},
    }
    repo = _make_repo(tmp_path, manifest)
    monkeypatch.setenv("COS_HISTORY_SANITIZE_OPERATOR_EMAIL", "test@example.com")
    monkeypatch.delenv("COS_HISTORY_SANITIZE_METADATA", raising=False)

    report = build_report(repo, mode="execute")

    assert report["status"] == "block"
    assert any(f["code"] == "metadata-rewrite-not-enabled" for f in report["findings"])


def test_commit_message_scoped_rule_blocks_without_message_env(tmp_path: Path, monkeypatch) -> None:
    manifest = {
        "schema_version": "history-sanitization/v1",
        "rules": [
            {
                "id": "internal-trailer",
                "mode": "literal",
                "scope": "commit-message",
                "pattern": "X-COS-Session:",
                "replacement": "",
            }
        ],
        "sensitive_history_patterns": [],
        "preserve": [],
        "execution": {"require_env": "COS_ALLOW_DESTRUCTIVE_GIT", "require_env_value": "1"},
    }
    repo = _make_repo(tmp_path, manifest)
    monkeypatch.delenv("COS_HISTORY_SANITIZE_COMMIT_MESSAGES", raising=False)

    report = build_report(repo, mode="execute")

    assert report["status"] == "block"
    assert any(f["code"] == "commit-message-rewrite-not-enabled" for f in report["findings"])


def test_execute_without_destructive_env_blocks(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.delenv("COS_ALLOW_DESTRUCTIVE_GIT", raising=False)
    report = build_report(repo, mode="execute")
    assert report["status"] == "block"
    assert any(finding["code"] == "destructive-git-env-missing" for finding in report["findings"])


def test_replacement_preserve_conflict_blocks(tmp_path: Path, monkeypatch) -> None:
    manifest = {
        "schema_version": "history-sanitization/v1",
        "rules": [
            {"id": "bad-license-rewrite", "mode": "literal", "value_env": "COS_HISTORY_SANITIZE_LICENSE_VALUE", "replacement": "LICENSE", "required": True},
        ],
        "sensitive_history_patterns": [],
        "preserve": [{"id": "license-transition", "mode": "regex", "pattern": r"Apache-2\.0|FSL-1\.1"}],
        "execution": {"require_env": "COS_ALLOW_DESTRUCTIVE_GIT", "require_env_value": "1"},
    }
    repo = _make_repo(tmp_path, manifest)
    monkeypatch.setenv("COS_HISTORY_SANITIZE_LICENSE_VALUE", "Apache-2.0")
    report = build_report(repo, mode="dry-run")
    assert report["status"] == "block"
    assert any(finding["code"] == "replacement-preserve-conflict" for finding in report["findings"])


def test_preserve_conflicts_detects_literal_against_regex() -> None:
    conflicts = preserve_conflicts(
        [{"id": "candidate", "value": "Functional Source License FSL-1.1-MIT"}],
        [{"id": "license-transition", "mode": "regex", "pattern": r"FSL-1\.1"}],
    )
    assert conflicts == [{"replacement_rule_id": "candidate", "preserve_rule_id": "license-transition"}]
