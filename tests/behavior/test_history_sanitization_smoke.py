"""Behavior tests for `scripts/cos-history-sanitization-smoke.sh` (ADR-218 §M4).

The smoke script reads `manifests/history-sanitization.yaml` to discover
the env-var names that hold sensitive tokens, resolves each from the
process environment, and asserts each token has 0 hits across `git log
--all -p` plus every ref tip.

These tests build a synthetic git repo and a synthetic manifest in a
tmp_path, then invoke the smoke script under three conditions:

  1. Clean repo, env vars set with tokens that DO NOT appear in history.
     Expected: exit 0, "PASS — 0 leaked tokens".
  2. Dirty repo, env vars set with a token that DOES appear in history.
     Expected: exit 1, "FAIL — at least one configured token still …".
  3. Clean repo, env vars NOT set.
     Expected: exit 0, "skip-with-warning".
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SMOKE = ROOT / "scripts" / "cos-history-sanitization-smoke.sh"


pytestmark = pytest.mark.skipif(
    not SMOKE.exists() or shutil.which("bash") is None,
    reason="smoke script or bash unavailable",
)


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=False)


def _init_repo(repo: Path, *, with_leak: str | None = None) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "--initial-branch=main"], repo)
    _run(["git", "config", "user.email", "test@fixture.invalid"], repo)
    _run(["git", "config", "user.name", "Fixture Tester"], repo)
    (repo / "README.md").write_text("# clean fixture\n", encoding="utf-8")
    _run(["git", "add", "README.md"], repo)
    _run(["git", "commit", "-m", "initial"], repo)
    if with_leak:
        (repo / "leak.txt").write_text(f"sensitive: {with_leak}\n", encoding="utf-8")
        _run(["git", "add", "leak.txt"], repo)
        _run(["git", "commit", "-m", "introduce leak"], repo)


def _write_manifest(path: Path, env_vars: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "schema_version: history-sanitization/v1",
        "status: active",
        "rules:",
    ]
    for i, var in enumerate(env_vars):
        lines += [
            f"  - id: rule-{i}",
            "    mode: literal",
            f"    value_env: {var}",
            f"    replacement: <placeholder-{i}>",
            "    required: false",
        ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _smoke_env(extra: dict[str, str]) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COS_HISTORY_SANITIZE_")}
    env.update(extra)
    return env


def test_smoke_passes_on_clean_repo(tmp_path: Path) -> None:
    repo = tmp_path / "clean-repo"
    _init_repo(repo, with_leak=None)
    manifest = tmp_path / "manifest.yaml"
    _write_manifest(manifest, ["COS_HISTORY_SANITIZE_TEST_TOKEN_A"])

    env = _smoke_env({"COS_HISTORY_SANITIZE_TEST_TOKEN_A": "absent-token-xyz-never-committed"})

    proc = subprocess.run(
        ["bash", str(SMOKE), "--repo", str(repo), "--manifest", str(manifest)],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    assert "PASS" in proc.stdout
    assert "0 leaked tokens" in proc.stdout


def test_smoke_fails_on_dirty_repo(tmp_path: Path) -> None:
    leak = "very-secret-codename-foo"
    repo = tmp_path / "dirty-repo"
    _init_repo(repo, with_leak=leak)
    manifest = tmp_path / "manifest.yaml"
    _write_manifest(manifest, ["COS_HISTORY_SANITIZE_TEST_TOKEN_A"])

    env = _smoke_env({"COS_HISTORY_SANITIZE_TEST_TOKEN_A": leak})

    proc = subprocess.run(
        ["bash", str(SMOKE), "--repo", str(repo), "--manifest", str(manifest)],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 1, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    assert "FAIL" in (proc.stdout + proc.stderr)
    # Verify the table reports the offending token by its env-var name
    assert "COS_HISTORY_SANITIZE_TEST_TOKEN_A" in proc.stdout


def test_smoke_skips_with_warning_when_env_unset(tmp_path: Path) -> None:
    repo = tmp_path / "clean-repo"
    _init_repo(repo, with_leak=None)
    manifest = tmp_path / "manifest.yaml"
    _write_manifest(manifest, ["COS_HISTORY_SANITIZE_TEST_TOKEN_A", "COS_HISTORY_SANITIZE_TEST_TOKEN_B"])

    env = _smoke_env({})  # explicitly nothing

    proc = subprocess.run(
        ["bash", str(SMOKE), "--repo", str(repo), "--manifest", str(manifest)],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    assert "skip-with-warning" in proc.stdout
    assert "no sanitization env vars are set" in proc.stdout


def test_smoke_json_mode_reports_structured_summary(tmp_path: Path) -> None:
    repo = tmp_path / "clean-repo"
    _init_repo(repo, with_leak=None)
    manifest = tmp_path / "manifest.yaml"
    _write_manifest(manifest, ["COS_HISTORY_SANITIZE_TEST_TOKEN_A"])

    env = _smoke_env({"COS_HISTORY_SANITIZE_TEST_TOKEN_A": "absent-xyz-123"})

    proc = subprocess.run(
        ["bash", str(SMOKE), "--repo", str(repo), "--manifest", str(manifest), "--json"],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    import json
    payload = json.loads(proc.stdout)
    assert payload["status"] == "PASS"
    assert payload["tokens_resolved"] == 1
    assert payload["results"][0]["env_var"] == "COS_HISTORY_SANITIZE_TEST_TOKEN_A"
    assert payload["results"][0]["hits"] == 0
    assert payload["results"][0]["verdict"] == "PASS"
