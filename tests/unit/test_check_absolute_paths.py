"""Behavior tests for scripts/check_absolute_paths.py."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import check_absolute_paths as cap


pytestmark = [pytest.mark.unit, pytest.mark.behavior]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "check_absolute_paths.py"
DOC = PROJECT_ROOT / "docs" / "architecture" / "path-portability-and-privacy.md"


def mac_home_path(user: str, *parts: str) -> str:
    return str(Path("/") / "Users" / user / Path(*parts))


def linux_home_path(user: str, *parts: str) -> str:
    return str(Path("/") / "home" / user / Path(*parts))


def test_scan_file_detects_developer_home_path(tmp_path: Path) -> None:
    doc = tmp_path / "README.md"
    leaked = mac_home_path("alice", "Projects", "private-app", "README.md")
    doc.write_text(f"See {leaked}\n", encoding="utf-8")

    findings = cap.scan_file(doc, tmp_path)

    assert len(findings) == 1
    assert findings[0].matched_text == leaked
    assert findings[0].reason == "developer home path"


def test_scan_file_allows_portable_placeholders(tmp_path: Path) -> None:
    doc = tmp_path / "README.md"
    doc.write_text(
        "Use <repo-root>, $PROJECT_DIR, or $HOME in docs instead.\n"
        "Container notebook path is allowed: /home/jovyan/work/notebook.ipynb\n",
        encoding="utf-8",
    )

    assert cap.scan_file(doc, tmp_path) == []


def test_cli_blocks_tracked_style_home_paths_in_docs(tmp_path: Path) -> None:
    doc = tmp_path / "guide.md"
    doc.write_text(
        f"Do not commit {linux_home_path('dev', 'projects', 'secret')}\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["python3", str(SCRIPT), "--root", str(tmp_path), str(doc)],
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 1
    assert "developer home path" in result.stderr
    assert "BLOCKED" in result.stderr


def test_repo_has_no_tracked_developer_home_paths() -> None:
    result = subprocess.run(
        ["python3", str(SCRIPT), "--root", str(PROJECT_ROOT)],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr



def test_default_scan_ignores_paths_staged_for_deletion(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
    )
    export = tmp_path / "memory.jsonl"
    export.write_text(mac_home_path("alice", "private", "note.md") + "\n", encoding="utf-8")
    subprocess.run(["git", "add", "memory.jsonl"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "rm", "--cached", "memory.jsonl"], cwd=tmp_path, check=True, capture_output=True)

    result = subprocess.run(
        ["python3", str(SCRIPT), "--root", str(tmp_path)],
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr


def test_staged_scan_ignores_gitlink_submodule_contents(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
    )
    plugin = tmp_path / "vendor" / "plugin"
    plugin.mkdir(parents=True)
    (plugin / "README.md").write_text(
        f"Upstream fixture path: {mac_home_path('upstream-dev', 'repo')}\n",
        encoding="utf-8",
    )
    subprocess.run(
        [
            "git",
            "update-index",
            "--add",
            "--cacheinfo",
            "160000,0123456789012345678901234567890123456789,vendor/plugin",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    result = subprocess.run(
        ["python3", str(SCRIPT), "--root", str(tmp_path), "--staged"],
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr


def test_path_portability_policy_is_documented_and_linked() -> None:
    content = DOC.read_text()

    for phrase in [
        "Do not commit paths rooted in a developer home directory",
        "python3 scripts/check_absolute_paths.py --root .",
        ".engram/exports/*.jsonl",
        "git rm --cached",
        "Consumer Projects",
    ]:
        assert phrase in content

    assert "architecture/path-portability-and-privacy.md" in (
        PROJECT_ROOT / "docs" / "README.md"
    ).read_text()
