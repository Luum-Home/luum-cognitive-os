"""Tests for scripts/cos-patch-release."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.behavior]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "cos-patch-release"


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "tester@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "remote", "add", "origin", "https://example.invalid/repo.git"], cwd=path, check=True)


def seed_release_repo(path: Path) -> None:
    (path / "cmd" / "cos").mkdir(parents=True)
    (path / "VERSION").write_text("0.29.6\n", encoding="utf-8")
    (path / "cmd" / "cos" / "VERSION").write_text("0.29.6\n", encoding="utf-8")
    (path / "pyproject.toml").write_text('[project]\nname = "fixture"\nversion = "0.29.6"\n', encoding="utf-8")
    (path / "uv.lock").write_text('name = "fixture"\nversion = "0.29.6"\n', encoding="utf-8")
    (path / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n\n", encoding="utf-8")


def fake_uv_bin(path: Path) -> Path:
    bindir = path / "bin"
    bindir.mkdir()
    uv = bindir / "uv"
    uv.write_text(
        "#!/usr/bin/env python3\n"
        "import pathlib, re, sys\n"
        "cmd=sys.argv[1:]\n"
        "root=pathlib.Path.cwd()\n"
        "if cmd and cmd[0]=='lock':\n"
        "    py=(root/'pyproject.toml').read_text()\n"
        "    version=re.search(r'version = \\\"([^\\\"]+)\\\"', py).group(1)\n"
        "    (root/'uv.lock').write_text(f'name = \\\"fixture\\\"\\nversion = \\\"{version}\\\"\\n')\n"
        "    sys.exit(0)\n"
        "if cmd[:2]==['sync','--extra']:\n"
        "    sys.exit(0)\n"
        "sys.exit(2)\n",
        encoding="utf-8",
    )
    uv.chmod(0o755)
    return bindir


def run_script(root: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        [str(SCRIPT), "--project-dir", str(root), *args],
        cwd=root,
        text=True,
        capture_output=True,
        env=merged,
        timeout=30,
        check=False,
    )


def test_prepare_dry_run_lists_release_files_without_writing(tmp_path: Path) -> None:
    init_repo(tmp_path)
    seed_release_repo(tmp_path)
    before = (tmp_path / "VERSION").read_text(encoding="utf-8")

    result = run_script(tmp_path, "prepare", "--version", "0.29.7", "--dry-run")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "dry-run"
    assert payload["prepare"]["version"] == "0.29.7"
    assert "VERSION" in payload["prepare"]["files"]
    assert "uv sync --extra testing --locked" in payload["prepare"]["commands"]
    assert (tmp_path / "VERSION").read_text(encoding="utf-8") == before


def test_prepare_updates_versions_changelog_and_uv_lock(tmp_path: Path) -> None:
    init_repo(tmp_path)
    seed_release_repo(tmp_path)
    bindir = fake_uv_bin(tmp_path)
    env = {"PATH": str(bindir) + os.pathsep + os.environ.get("PATH", "")}

    result = run_script(tmp_path, "prepare", "--version", "0.29.7", "--title", "Fixture Patch", env=env)

    assert result.returncode == 0, result.stderr
    assert "patch-release-prepare-ok version=0.29.7" in result.stdout
    assert (tmp_path / "VERSION").read_text(encoding="utf-8") == "0.29.7\n"
    assert 'version = "0.29.7"' in (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.29.7"' in (tmp_path / "uv.lock").read_text(encoding="utf-8")
    assert "## [0.29.7]" in (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")


def test_publish_dry_run_never_pushes_directly_to_main(tmp_path: Path) -> None:
    init_repo(tmp_path)
    seed_release_repo(tmp_path)

    result = run_script(tmp_path, "publish", "--version", "0.29.7", "--dry-run")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    steps = "\n".join(payload["publish"]["steps"])
    assert "scripts/merge-to-main.sh" in steps
    assert "git push origin main" not in steps
    assert payload["publish"]["branch"] == "codex/release-v0.29.7"
    assert payload["publish"]["tag"] == "v0.29.7"


def test_doctor_blocks_existing_local_tag(tmp_path: Path) -> None:
    init_repo(tmp_path)
    seed_release_repo(tmp_path)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "tag", "v0.29.7"], cwd=tmp_path, check=True)

    result = run_script(tmp_path, "doctor", "--version", "0.29.7", "--json")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "block"
    assert any(check["name"] == "tag_available" and not check["ok"] for check in payload["checks"])


def test_validate_print_commands_matches_patch_lane(tmp_path: Path) -> None:
    init_repo(tmp_path)
    seed_release_repo(tmp_path)

    result = run_script(tmp_path, "validate", "--print-commands")

    assert result.returncode == 0, result.stderr
    assert "scripts/check-local-privacy.sh --root . --all" in result.stdout
    assert "tests/unit/test_check_local_privacy.py" in result.stdout
    assert "cd cmd/cos && go test ./..." in result.stdout
