# SCOPE: os-only
"""Portability proof for scripts/edit-coop.sh.

Two layouts have to work, because the primitive lives in two places:

  * the OS repo, at scripts/edit-coop.sh with its lib at scripts/_lib/;
  * a consumer install, where cos_init._install_edit_lock_primitive copies it to
    .cognitive-os/bin/edit-coop.sh with the lib at .cognitive-os/bin/_lib/.

Until 2026-08-19 the second layout did not exist: no installer copied the
script, so the four hooks/edit-lock-*.sh hooks shipped, registered under --full,
and could never do anything. primitive-consumer-availability.yaml declared a
shared surface that was never delivered.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/edit-coop.sh"
LIB = REPO_ROOT / "scripts/_lib/session-id.sh"


def _env(project_dir: Path, **extra: str) -> dict:
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "PYTHONPATH": str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", ""),
    })
    env.pop("CODEX_PROJECT_DIR", None)
    env.update(extra)
    return env


def test_edit_coop_safe_invocation_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: script safe invocation must not depend on OS repo cwd."""
    result = subprocess.run(
        ["bash", str(ARTIFACT), "--help"],
        text=True, capture_output=True, cwd=tmp_path,
        env=_env(tmp_path), timeout=20, check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode in {0, 1, 2, 12, 64, 77}, output
    assert "No such file or directory" not in output
    assert "Traceback" not in output


def test_installer_projects_the_primitive_with_its_lib(tmp_path: Path) -> None:
    """The gap that made the whole subsystem inert: the CLI never shipped.

    Asserts the lib travels too. Shipping edit-coop.sh alone leaves each side on
    its own fallback identity -- `default-session` inside the script,
    `shell-$PPID` inside the hooks -- so a lock taken by one is invisible to the
    other, which is a subtler break than not shipping at all.
    """
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import cos_init

    assert cos_init._install_edit_lock_primitive(tmp_path, REPO_ROOT) is True

    coop = tmp_path / ".cognitive-os" / "bin" / "edit-coop.sh"
    lib = tmp_path / ".cognitive-os" / "bin" / "_lib" / "session-id.sh"
    assert coop.is_file(), "the primitive did not ship"
    assert os.access(coop, os.X_OK), "shipped but not executable"
    assert lib.is_file(), "the identity lib did not travel with it"


def test_projected_primitive_resolves_its_lib_in_the_consumer_layout(tmp_path: Path) -> None:
    """The projected copy must find its own lib, not the OS repo's.

    Probed by giving the SHIPPED lib a marked identity: if the script silently
    fell back to its inline default, the marker would not appear.
    """
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import cos_init

    cos_init._install_edit_lock_primitive(tmp_path, REPO_ROOT)
    lib = tmp_path / ".cognitive-os" / "bin" / "_lib" / "session-id.sh"
    lib.write_text("cos_session_id() { printf 'IDENTIDAD-DEL-LIB-PROYECTADO'; }\n", encoding="utf-8")
    coop = tmp_path / ".cognitive-os" / "bin" / "edit-coop.sh"

    result = subprocess.run(
        ["bash", str(coop), "acquire", "docs/probe.md"],
        text=True, capture_output=True, cwd=tmp_path,
        env=_env(tmp_path, COS_EDIT_LOCK_NO_PID_CHECK="1"), timeout=20, check=False,
    )
    meta = tmp_path / ".cognitive-os" / "runtime" / "edit-locks" / "docs--probe.md" / "meta.yaml"
    assert meta.is_file(), result.stdout + result.stderr
    assert "IDENTIDAD-DEL-LIB-PROYECTADO" in meta.read_text(encoding="utf-8"), (
        "the projected script did not source the projected lib"
    )


def test_the_lib_is_absent_control(tmp_path: Path) -> None:
    """Null control: with no lib the script still works, on its own fallback.

    Without this, the marker test above would also pass for a script that simply
    always writes whatever the lib says, and 'resolves its lib' would be
    indistinguishable from 'cannot run without it'.
    """
    shutil.copy2(ARTIFACT, tmp_path / "edit-coop.sh")
    result = subprocess.run(
        ["bash", str(tmp_path / "edit-coop.sh"), "acquire", "docs/probe.md"],
        text=True, capture_output=True, cwd=tmp_path,
        env=_env(tmp_path, COS_EDIT_LOCK_NO_PID_CHECK="1"), timeout=20, check=False,
    )
    meta = tmp_path / ".cognitive-os" / "runtime" / "edit-locks" / "docs--probe.md" / "meta.yaml"
    assert meta.is_file(), result.stdout + result.stderr
    assert "IDENTIDAD-DEL-LIB-PROYECTADO" not in meta.read_text(encoding="utf-8")
