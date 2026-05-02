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


def init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=path,
        check=True,
    )


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
    init_git_repo(tmp_path)
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
    init_git_repo(tmp_path)
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


def test_staged_scan_reads_index_not_dirty_worktree(tmp_path: Path) -> None:
    init_git_repo(tmp_path)
    doc = tmp_path / "README.md"
    doc.write_text("Portable staged content uses $PROJECT_DIR.\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    doc.write_text(
        f"Dirty worktree content mentions {mac_home_path('alice', 'private')}.\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["python3", str(SCRIPT), "--root", str(tmp_path), "--staged"],
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr


def test_staged_scan_blocks_index_even_if_worktree_was_fixed(tmp_path: Path) -> None:
    init_git_repo(tmp_path)
    doc = tmp_path / "README.md"
    leaked = mac_home_path("alice", "private")
    doc.write_text(f"Staged leak: {leaked}\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    doc.write_text("Worktree has been fixed to $PROJECT_DIR.\n", encoding="utf-8")

    result = subprocess.run(
        ["python3", str(SCRIPT), "--root", str(tmp_path), "--staged"],
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 1
    assert leaked in result.stderr


def test_staged_scan_rename_uses_new_path(tmp_path: Path) -> None:
    init_git_repo(tmp_path)
    old_doc = tmp_path / "old.md"
    new_doc = tmp_path / "new.md"
    old_doc.write_text("portable\n", encoding="utf-8")
    subprocess.run(["git", "add", "old.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=tmp_path, check=True, capture_output=True)
    old_doc.rename(new_doc)
    leaked = mac_home_path("alice", "renamed")
    new_doc.write_text(f"renamed leak: {leaked}\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

    staged = cap.staged_files(tmp_path)
    result = subprocess.run(
        ["python3", str(SCRIPT), "--root", str(tmp_path), "--staged"],
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert [f.path for f in staged] == ["new.md"]
    assert result.returncode == 1
    assert "new.md" in result.stderr
    assert "old.md\tnew.md" not in result.stderr
    assert leaked in result.stderr


def test_staged_scan_copy_uses_new_path(tmp_path: Path) -> None:
    init_git_repo(tmp_path)
    source = tmp_path / "source.md"
    copied = tmp_path / "copied.md"
    source.write_text(("portable reference line\n" * 20), encoding="utf-8")
    subprocess.run(["git", "add", "source.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=tmp_path, check=True, capture_output=True)
    leaked = mac_home_path("alice", "copied")
    copied.write_text(source.read_text(encoding="utf-8") + f"path: {leaked}\n", encoding="utf-8")
    subprocess.run(["git", "add", "copied.md"], cwd=tmp_path, check=True)

    staged = cap.staged_files(tmp_path)
    result = subprocess.run(
        ["python3", str(SCRIPT), "--root", str(tmp_path), "--staged"],
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert [f.path for f in staged] == ["copied.md"]
    assert result.returncode == 1
    assert "copied.md" in result.stderr
    assert "source.md\tcopied.md" not in result.stderr
    assert leaked in result.stderr


def test_staged_scan_file_with_spaces(tmp_path: Path) -> None:
    init_git_repo(tmp_path)
    doc = tmp_path / "docs with spaces.md"
    leaked = mac_home_path("alice", "spacey")
    doc.write_text(f"path: {leaked}\n", encoding="utf-8")
    subprocess.run(["git", "add", "docs with spaces.md"], cwd=tmp_path, check=True)

    result = subprocess.run(
        ["python3", str(SCRIPT), "--root", str(tmp_path), "--staged"],
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 1
    assert "docs with spaces.md" in result.stderr
    assert leaked in result.stderr


def test_staged_scan_blocks_symlink_to_developer_home(tmp_path: Path) -> None:
    init_git_repo(tmp_path)
    link = tmp_path / "private-link"
    leaked = mac_home_path("alice", "private")
    link.symlink_to(leaked)
    subprocess.run(["git", "add", "private-link"], cwd=tmp_path, check=True)

    result = subprocess.run(
        ["python3", str(SCRIPT), "--root", str(tmp_path), "--staged"],
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 1
    assert "private-link" in result.stderr
    assert leaked in result.stderr


def test_staged_scan_blocks_gitmodules_local_absolute_path(tmp_path: Path) -> None:
    init_git_repo(tmp_path)
    leaked = mac_home_path("alice", "plugins", "tool")
    (tmp_path / ".gitmodules").write_text(
        '[submodule "local-tool"]\n'
        "\tpath = .claude/plugins/local-tool\n"
        f"\turl = {leaked}\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", ".gitmodules"], cwd=tmp_path, check=True)

    result = subprocess.run(
        ["python3", str(SCRIPT), "--root", str(tmp_path), "--staged"],
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 1
    assert ".gitmodules" in result.stderr
    assert leaked in result.stderr


def test_staged_scan_new_submodule_ignores_dirty_checkout_content(tmp_path: Path) -> None:
    init_git_repo(tmp_path)
    plugin = tmp_path / ".claude" / "plugins" / "dirty-tool"
    plugin.mkdir(parents=True)
    (plugin / "README.md").write_text(
        f"upstream fixture path: {mac_home_path('upstream-dev', 'tool')}\n",
        encoding="utf-8",
    )
    (tmp_path / ".gitmodules").write_text(
        '[submodule ".claude/plugins/dirty-tool"]\n'
        "\tpath = .claude/plugins/dirty-tool\n"
        "\turl = https://example.invalid/dirty-tool.git\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", ".gitmodules"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "update-index",
            "--add",
            "--cacheinfo",
            "160000,0123456789012345678901234567890123456789,.claude/plugins/dirty-tool",
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


def test_staged_scan_skips_binary_blob(tmp_path: Path) -> None:
    init_git_repo(tmp_path)
    binary = tmp_path / "payload.bin"
    binary.write_bytes(b"\0" + mac_home_path("alice", "binary").encode("utf-8"))
    subprocess.run(["git", "add", "payload.bin"], cwd=tmp_path, check=True)

    result = subprocess.run(
        ["python3", str(SCRIPT), "--root", str(tmp_path), "--staged"],
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr


def test_staged_scan_blocks_windows_developer_home_path(tmp_path: Path) -> None:
    init_git_repo(tmp_path)
    doc = tmp_path / "windows.md"
    leaked = "C:" + "\\" + "Users" + "\\" + "alice" + "\\" + "secret"
    doc.write_text(f"Windows leak: {leaked}\n", encoding="utf-8")
    subprocess.run(["git", "add", "windows.md"], cwd=tmp_path, check=True)

    result = subprocess.run(
        ["python3", str(SCRIPT), "--root", str(tmp_path), "--staged"],
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 1
    assert "windows.md" in result.stderr
    assert leaked in result.stderr


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
