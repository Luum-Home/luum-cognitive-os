"""Phase 2.3 parity tests — install_rule(), install_hook(), install_skill_dir() must match
the expected behavior derived from the original bash logic in cos-init.sh.

Strategy: test Python via --internal-call subprocess vs Python direct module call
and verify filesystem side-effects against the bash truth table.

Bash truth table for install_rule (cos-init.sh install_rule function):
  source exists → prints "installed", copies file to each dest → exit 0
  source missing → prints "skipped" → exit 0

Bash truth table for install_hook (cos-init.sh install_hook function):
  source exists → prints "installed", copies file, chmod +x → exit 0
  source missing → prints "skipped" → exit 0

Bash truth table for install_skill_dir (cos-init.sh install_skill_dir function):
  skill_scope_allows fails → prints "skipped" → exit 0
  source dir exists → prints "installed", cp -r to kernel, ln -s to driver → exit 0
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent.parent
COS_INIT_PY = REPO / "scripts" / "cos_init.py"

sys.path.insert(0, str(REPO / "scripts"))
import cos_init  # noqa: E402


# ── Helpers ──────────────────────────────────────────────────────────

def _subprocess_internal_call(
    function_name: str,
    *args: str,
    env_extra: dict | None = None,
) -> tuple[int, str]:
    """Run --internal-call via subprocess. Returns (returncode, stdout.strip())."""
    env = {**os.environ, **(env_extra or {})}
    result = subprocess.run(
        ["python3", str(COS_INIT_PY), "--internal-call", function_name, *args],
        env=env,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip()


def _make_rule(src_dir: Path, name: str, content: str = "# rule") -> None:
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / f"{name}.md").write_text(content)


def _make_hook(src_dir: Path, name: str, content: str = "#!/bin/bash\necho hook\n") -> None:
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / f"{name}.sh").write_text(content)


def _make_skill(skills_src: Path, name: str, audience: str = "project") -> Path:
    skill_dir = skills_src / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"---\naudience: {audience}\n---\n# Skill\n")
    return skill_dir


# ── install_rule parity tests ─────────────────────────────────────────

class TestParityInstallRule:
    """Subprocess --internal-call output must match direct module call AND filesystem state."""

    def test_parity_installs_single_dest(self, tmp_path: Path) -> None:
        """Rule with existing source → 'installed', file present in dest."""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        dest.mkdir()
        _make_rule(src, "trust-score")

        rc, stdout = _subprocess_internal_call(
            "install_rule", "trust-score", str(src), str(dest)
        )
        assert rc == 0, f"Expected exit 0, got {rc}"
        assert stdout == "installed", f"Expected 'installed', got {stdout!r}"
        assert (dest / "trust-score.md").is_file()

    def test_parity_installs_two_dests(self, tmp_path: Path) -> None:
        """Rule with colon-separated dests → both destinations receive the file."""
        src = tmp_path / "src"
        dest1 = tmp_path / "d1"
        dest2 = tmp_path / "d2"
        dest1.mkdir()
        dest2.mkdir()
        _make_rule(src, "adaptive-bypass")

        rc, stdout = _subprocess_internal_call(
            "install_rule", "adaptive-bypass", str(src), f"{dest1}:{dest2}"
        )
        assert rc == 0
        assert stdout == "installed"
        assert (dest1 / "adaptive-bypass.md").is_file()
        assert (dest2 / "adaptive-bypass.md").is_file()

    def test_parity_missing_source_returns_skipped(self, tmp_path: Path) -> None:
        """Missing source → 'skipped', exit 0, no file created."""
        src = tmp_path / "src"
        src.mkdir()
        dest = tmp_path / "dest"
        dest.mkdir()

        rc, stdout = _subprocess_internal_call(
            "install_rule", "nonexistent", str(src), str(dest)
        )
        assert rc == 0, f"Expected exit 0, got {rc}"
        assert stdout == "skipped", f"Expected 'skipped', got {stdout!r}"
        assert not (dest / "nonexistent.md").exists()

    def test_parity_subprocess_matches_direct(self, tmp_path: Path) -> None:
        """Subprocess and direct-call produce identical status and filesystem state."""
        src1 = tmp_path / "src1"
        src2 = tmp_path / "src2"
        dest_sub = tmp_path / "dest_sub"
        dest_dir = tmp_path / "dest_dir"
        dest_sub.mkdir()
        dest_dir.mkdir()
        _make_rule(src1, "error-learning")
        _make_rule(src2, "error-learning")

        rc_sub, stdout_sub = _subprocess_internal_call(
            "install_rule", "error-learning", str(src1), str(dest_sub)
        )
        dir_status = cos_init.install_rule("error-learning", str(src2), [str(dest_dir)])
        dir_rc = 0 if dir_status != "error" else 1
        dir_stdout = dir_status

        assert rc_sub == dir_rc, f"subprocess rc={rc_sub} direct rc={dir_rc}"
        assert stdout_sub == dir_stdout, f"subprocess={stdout_sub!r} direct={dir_stdout!r}"
        assert (dest_sub / "error-learning.md").is_file()
        assert (dest_dir / "error-learning.md").is_file()


# ── install_hook parity tests ─────────────────────────────────────────

class TestParityInstallHook:
    """Subprocess --internal-call output must match direct module call AND filesystem state."""

    def test_parity_installs_hook_and_sets_executable(self, tmp_path: Path) -> None:
        """Hook with existing source → 'installed', file present and executable."""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        dest.mkdir()
        _make_hook(src, "auto-refine")

        rc, stdout = _subprocess_internal_call(
            "install_hook", "auto-refine", str(src), str(dest)
        )
        assert rc == 0, f"Expected exit 0, got {rc}"
        assert stdout == "installed", f"Expected 'installed', got {stdout!r}"
        installed = dest / "auto-refine.sh"
        assert installed.is_file()
        assert os.access(str(installed), os.X_OK), "Installed hook must be executable"

    def test_parity_missing_source_returns_skipped(self, tmp_path: Path) -> None:
        """Missing source → 'skipped', exit 0, no file created."""
        src = tmp_path / "src"
        src.mkdir()
        dest = tmp_path / "dest"
        dest.mkdir()

        rc, stdout = _subprocess_internal_call(
            "install_hook", "nonexistent", str(src), str(dest)
        )
        assert rc == 0, f"Expected exit 0, got {rc}"
        assert stdout == "skipped"
        assert not (dest / "nonexistent.sh").exists()

    def test_parity_subprocess_matches_direct(self, tmp_path: Path) -> None:
        """Subprocess and direct-call produce identical status and filesystem state."""
        src1 = tmp_path / "src1"
        src2 = tmp_path / "src2"
        dest_sub = tmp_path / "dest_sub"
        dest_dir = tmp_path / "dest_dir"
        dest_sub.mkdir()
        dest_dir.mkdir()
        _make_hook(src1, "blast-radius")
        _make_hook(src2, "blast-radius")

        rc_sub, stdout_sub = _subprocess_internal_call(
            "install_hook", "blast-radius", str(src1), str(dest_sub)
        )
        dir_status = cos_init.install_hook("blast-radius", str(src2), str(dest_dir))
        dir_rc = 0 if dir_status != "error" else 1
        dir_stdout = dir_status

        assert rc_sub == dir_rc, f"subprocess rc={rc_sub} direct rc={dir_rc}"
        assert stdout_sub == dir_stdout, f"subprocess={stdout_sub!r} direct={dir_stdout!r}"


# ── install_skill_dir parity tests ────────────────────────────────────

class TestParityInstallSkillDir:
    """Subprocess --internal-call output must match direct module call AND filesystem state."""

    def test_parity_installs_skill_creates_symlink(self, tmp_path: Path) -> None:
        """Valid project skill → 'installed', kernel copy + driver symlink."""
        src = tmp_path / "skills"
        kernel = tmp_path / ".cognitive-os" / "skills" / "cos"
        driver = tmp_path / ".claude" / "skills"
        skill_dir = _make_skill(src, "plan-feature")
        kernel.mkdir(parents=True)
        driver.mkdir(parents=True)

        rc, stdout = _subprocess_internal_call(
            "install_skill_dir", str(skill_dir), str(kernel), str(driver),
            env_extra={"INSTALL_SCOPE": "both"},
        )
        assert rc == 0, f"Expected exit 0, got {rc}"
        assert stdout == "installed", f"Expected 'installed', got {stdout!r}"
        assert (kernel / "plan-feature" / "SKILL.md").is_file()
        assert (driver / "plan-feature").is_symlink()

    def test_parity_os_only_skill_returns_skipped(self, tmp_path: Path) -> None:
        """os-only skill → 'skipped', exit 0, nothing installed."""
        src = tmp_path / "skills"
        kernel = tmp_path / "kernel"
        driver = tmp_path / "driver"
        skill_dir = _make_skill(src, "os-internal", audience="os-only")
        kernel.mkdir()
        driver.mkdir()

        rc, stdout = _subprocess_internal_call(
            "install_skill_dir", str(skill_dir), str(kernel), str(driver),
            env_extra={"INSTALL_SCOPE": "both"},
        )
        assert rc == 0, f"Expected exit 0, got {rc}"
        assert stdout == "skipped", f"Expected 'skipped', got {stdout!r}"
        assert not (kernel / "os-internal").exists()
        assert not (driver / "os-internal").exists()

    def test_parity_subprocess_matches_direct(self, tmp_path: Path) -> None:
        """Subprocess and direct-call produce identical status and filesystem state."""
        src1 = tmp_path / "skills1"
        src2 = tmp_path / "skills2"
        kernel_sub = tmp_path / "kernel_sub"
        driver_sub = tmp_path / "driver_sub"
        kernel_dir = tmp_path / "kernel_dir"
        driver_dir = tmp_path / "driver_dir"
        for d in (kernel_sub, driver_sub, kernel_dir, driver_dir):
            d.mkdir()
        skill1 = _make_skill(src1, "session-backlog")
        skill2 = _make_skill(src2, "session-backlog")

        rc_sub, stdout_sub = _subprocess_internal_call(
            "install_skill_dir", str(skill1), str(kernel_sub), str(driver_sub),
            env_extra={"INSTALL_SCOPE": "both"},
        )
        dir_status = cos_init.install_skill_dir(
            str(skill2), str(kernel_dir), str(driver_dir), install_scope="both"
        )
        dir_rc = 0 if dir_status != "error" else 1
        dir_stdout = dir_status

        assert rc_sub == dir_rc, f"subprocess rc={rc_sub} direct rc={dir_rc}"
        assert stdout_sub == dir_stdout, f"subprocess={stdout_sub!r} direct={dir_stdout!r}"
        assert (kernel_sub / "session-backlog" / "SKILL.md").is_file()
        assert (kernel_dir / "session-backlog" / "SKILL.md").is_file()
