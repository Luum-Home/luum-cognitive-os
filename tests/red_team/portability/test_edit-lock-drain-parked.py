# SCOPE: os-only
"""Portability proof for hooks/edit-lock-drain-parked.sh.

The previous version of this file ran the hook FROM ITS PATH IN THE OS REPO and
asserted only `returncode == 0`. Both halves were wrong for this artifact:

  * `$(dirname "$0")/../scripts/_lib/session-id.sh` resolves perfectly when the
    hook runs from hooks/, so the probe varied PROJECT_DIR -- barely involved in
    the failure at issue -- and never varied the one thing that breaks: WHERE
    THE HOOK ITSELF LIVES. In a consumer install it lands under
    .cognitive-os/hooks/cos/, where that relative path resolves to nothing.
  * the broken hook exited 0 too. `set -uo pipefail` carries no `-e`, so a
    failed `source` prints, continues, and still reaches `exit 0`. Asserting the
    exit code alone cannot see this class at all.

Measured 2026-08-19: three stderr lines on EVERY UserPromptSubmit in a consumer
install, and an empty session id that collapsed the inbox path to the
negotiations root.

So: copy the hook into a consumer-shaped tree, and assert on stderr.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "hooks/edit-lock-drain-parked.sh"
LIB = REPO_ROOT / "scripts/_lib/session-id.sh"


def _consumer_tree(root: Path, *, with_lib: bool) -> Path:
    """A consumer install: the hook ships, scripts/_lib does not."""
    hooks_dir = root / ".cognitive-os" / "hooks" / "cos"
    hooks_dir.mkdir(parents=True)
    (root / ".cognitive-os" / "runtime" / "edit-negotiations").mkdir(parents=True)
    (root / ".cognitive-os" / "runtime" / "edit-locks").mkdir(parents=True)
    shipped = hooks_dir / ARTIFACT.name
    shipped.write_text(ARTIFACT.read_text(encoding="utf-8"), encoding="utf-8")
    if with_lib:
        # WHERE the hook looks, not where it would live in the OS repo:
        # `$(dirname "$0")/../scripts/_lib`. Placing it at <root>/scripts/_lib
        # instead -- the first thing this fixture did -- put it somewhere the
        # hook never consults, so the "lib present" case silently exercised the
        # SAME branch as the "lib absent" one and controlled nothing.
        lib_dir = hooks_dir.parent / "scripts" / "_lib"
        lib_dir.mkdir(parents=True)
        (lib_dir / LIB.name).write_text(LIB.read_text(encoding="utf-8"), encoding="utf-8")
    return shipped


def _run(script: Path, project_dir: Path, **extra: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
        "CLAUDE_PROJECT_DIR": str(project_dir),
    })
    env.pop("CODEX_PROJECT_DIR", None)
    env.update(extra)
    return subprocess.run(
        ["bash", str(script)],
        input=json.dumps({"tool_name": "Read", "tool_input": {}}),
        text=True,
        capture_output=True,
        cwd=str(project_dir),
        env=env,
        timeout=20,
        check=False,
    )


def test_runs_silently_in_a_consumer_install_without_the_shared_lib(tmp_path: Path) -> None:
    """The bug: scripts/_lib is os-only and never travels; this hook does."""
    shipped = _consumer_tree(tmp_path, with_lib=False)
    result = _run(shipped, tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stderr.strip() == "", (
        "the hook complained on stderr in a consumer install; "
        f"got: {result.stderr!r}"
    )
    assert "session-id.sh" not in result.stderr
    assert "cos_session_id" not in result.stderr


def test_still_silent_when_the_shared_lib_is_present(tmp_path: Path) -> None:
    """Null control: without it, "stays quiet" would hold just as well for a
    hook that does nothing at all, and the guarded source would look untested."""
    shipped = _consumer_tree(tmp_path, with_lib=True)
    result = _run(shipped, tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stderr.strip() == ""


def test_exit_code_alone_cannot_see_this_class(tmp_path: Path) -> None:
    """Pins WHY the old probe missed it: a hook whose `source` fails still exits
    0 under `set -uo pipefail`. If this ever starts failing, the shell options
    changed and the stderr assertions above became load-bearing for a different
    reason than the one written here."""
    shipped = _consumer_tree(tmp_path, with_lib=False)
    broken = shipped.read_text(encoding="utf-8").replace(
        '_SESSION_ID_LIB="$(dirname "$0")/../scripts/_lib/session-id.sh"',
        '_SESSION_ID_LIB="/nonexistent/session-id.sh"; source "$_SESSION_ID_LIB"',
    )
    shipped.write_text(broken, encoding="utf-8")
    result = _run(shipped, tmp_path)

    assert result.returncode == 0, "precondition: a failed source still exits 0"
    assert result.stderr.strip() != "", "and it is only visible on stderr"
