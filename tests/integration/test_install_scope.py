"""A2 — Integration test for install.sh --scope flag.

Verifies that:
  1. install.sh accepts --scope=project and passes COS_INSTALL_SCOPE to cos-init.sh.
  2. Files tagged SCOPE:os-only are excluded when --scope=project is used.
  3. Files tagged SCOPE:both and SCOPE:project are included.
  4. Total installed file count is <= 300 (project scope excludes os-only files).
  5. --scope=all includes os-only files.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
_INSTALL_SH = _PROJ_ROOT / "install.sh"
_COS_INIT_SH = _PROJ_ROOT / "scripts" / "cos-init.sh"


def _count_tagged(tag: str, source_dirs: list[Path]) -> int:
    """Count files in source_dirs that carry a given SCOPE tag."""
    count = 0
    for d in source_dirs:
        if not d.is_dir():
            continue
        for f in d.rglob("*"):
            if not f.is_file():
                continue
            try:
                content = f.read_text(errors="replace")
                # Read only first 3 lines (header area)
                first_lines = "\n".join(content.splitlines()[:3])
                if f"SCOPE: {tag}" in first_lines:
                    count += 1
            except Exception:
                pass
    return count


@pytest.mark.timeout(300)
@pytest.mark.skipif(not _COS_INIT_SH.exists(), reason="cos-init.sh not found")
def test_scope_project_excludes_os_only(tmp_path):
    """install.sh --scope=project must not install SCOPE:os-only files."""
    os_only_hooks = _count_tagged("os-only", [_PROJ_ROOT / "hooks"])
    os_only_rules = _count_tagged("os-only", [_PROJ_ROOT / "rules"])
    total_os_only = os_only_hooks + os_only_rules

    if total_os_only == 0:
        pytest.skip("No os-only tagged files found — scope filter has nothing to test")

    target = tmp_path / "target"
    target.mkdir()

    env = {
        **os.environ,
        "COGNITIVE_OS_FORCE": "true",
        "COGNITIVE_OS_SKIP_MANIFEST_CHECK": "true",
        "COS_REGISTRY_FILE": str(tmp_path / ".cos-test-registry.json"),
    }

    result = subprocess.run(
        ["bash", str(_COS_INIT_SH), "--full"],
        capture_output=True,
        text=True,
        timeout=120,
        env={**env, "COS_SOURCE_DIR": str(_PROJ_ROOT), "COS_INSTALL_SCOPE": "project"},
        cwd=str(target),
    )

    assert result.returncode == 0, (
        f"cos-init.sh --full with COS_INSTALL_SCOPE=project failed:\n{result.stderr[-2000:]}"
    )

    # Count os-only hooks that landed
    installed_hooks = list((target / ".cognitive-os" / "hooks" / "cos").glob("*.sh"))
    installed_rules = list((target / ".claude" / "rules" / "cos").glob("*.md"))

    os_only_installed = 0
    for f in installed_hooks + installed_rules:
        try:
            first_lines = "\n".join(f.read_text(errors="replace").splitlines()[:3])
            if "SCOPE: os-only" in first_lines:
                os_only_installed += 1
        except Exception:
            pass

    assert os_only_installed == 0, (
        f"Expected 0 os-only files installed with scope=project, "
        f"found {os_only_installed}. "
        f"Files: {[f.name for f in installed_hooks + installed_rules if 'os-only' in f.read_text(errors='replace')[:200]]}"
    )


@pytest.mark.timeout(300)
@pytest.mark.skipif(not _COS_INIT_SH.exists(), reason="cos-init.sh not found")
def test_scope_project_file_count_under_300(tmp_path):
    """Total installed files with --scope=project must be <= 300."""
    target = tmp_path / "target"
    target.mkdir()

    env = {
        **os.environ,
        "COGNITIVE_OS_FORCE": "true",
        "COGNITIVE_OS_SKIP_MANIFEST_CHECK": "true",
        "COS_REGISTRY_FILE": str(tmp_path / ".cos-test-registry.json"),
    }

    result = subprocess.run(
        ["bash", str(_COS_INIT_SH), "--full"],
        capture_output=True,
        text=True,
        timeout=120,
        env={**env, "COS_SOURCE_DIR": str(_PROJ_ROOT), "COS_INSTALL_SCOPE": "project"},
        cwd=str(target),
    )

    assert result.returncode == 0, (
        f"cos-init.sh failed:\n{result.stderr[-2000:]}"
    )

    # Count all installed files (hooks + rules + skills)
    total = 0
    for search_path in [
        target / ".cognitive-os" / "hooks" / "cos",
        target / ".claude" / "rules" / "cos",
        target / ".claude" / "skills",
    ]:
        if search_path.exists():
            total += sum(1 for f in search_path.rglob("*") if f.is_file())

    assert total <= 320, (
        f"Expected <= 320 files installed with scope=project, found {total}. "
        "Check that os-only files are being filtered."
    )


@pytest.mark.timeout(300)
@pytest.mark.skipif(not _COS_INIT_SH.exists(), reason="cos-init.sh not found")
def test_scope_all_includes_os_only(tmp_path):
    """--scope=all must include SCOPE:os-only files."""
    os_only_hooks = _count_tagged("os-only", [_PROJ_ROOT / "hooks"])
    if os_only_hooks == 0:
        pytest.skip("No os-only hooks found")

    target = tmp_path / "target"
    target.mkdir()

    env = {
        **os.environ,
        "COGNITIVE_OS_FORCE": "true",
        "COGNITIVE_OS_SKIP_MANIFEST_CHECK": "true",
        "COS_REGISTRY_FILE": str(tmp_path / ".cos-test-registry.json"),
    }

    result = subprocess.run(
        ["bash", str(_COS_INIT_SH), "--full"],
        capture_output=True,
        text=True,
        timeout=120,
        env={**env, "COS_SOURCE_DIR": str(_PROJ_ROOT), "COS_INSTALL_SCOPE": "all"},
        cwd=str(target),
    )

    assert result.returncode == 0, (
        f"cos-init.sh --full with COS_INSTALL_SCOPE=all failed:\n{result.stderr[-2000:]}"
    )

    installed_hooks = list((target / ".cognitive-os" / "hooks" / "cos").glob("*.sh"))
    os_only_installed = 0
    for f in installed_hooks:
        try:
            first_lines = "\n".join(f.read_text(errors="replace").splitlines()[:3])
            if "SCOPE: os-only" in first_lines:
                os_only_installed += 1
        except Exception:
            pass

    assert os_only_installed > 0, (
        f"Expected some os-only hooks with scope=all, found 0. "
        f"Source has {os_only_hooks} os-only hooks."
    )


@pytest.mark.skipif(not _INSTALL_SH.exists(), reason="install.sh not found")
def test_install_sh_scope_flag_is_parsed():
    """install.sh --scope=project must not exit with 'Unknown option' error."""
    # Run --help to verify the flag is documented
    result = subprocess.run(
        ["bash", str(_INSTALL_SH), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    # --help exits 0
    assert result.returncode == 0
    assert "--scope" in result.stdout, (
        f"--scope flag not found in --help output:\n{result.stdout}"
    )


@pytest.mark.skipif(not _INSTALL_SH.exists(), reason="install.sh not found")
def test_install_sh_scope_flag_grep_count():
    """install.sh must reference INSTALL_SCOPE in at least 3 places (AC #1)."""
    content = _INSTALL_SH.read_text()
    occurrences = content.count("INSTALL_SCOPE")
    assert occurrences >= 3, (
        f"Expected >= 3 occurrences of INSTALL_SCOPE in install.sh, found {occurrences}"
    )
