# SCOPE: os-only
"""Portability proof for hooks/edit-lock-pre-tool.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "hooks/edit-lock-pre-tool.sh"


def test_edit_lock_pre_tool_passes_unrelated_tool_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: hook must not depend on OS repo cwd for passthrough input."""
    payload = {"tool_name": "Read", "tool_input": {"file_path": str(tmp_path / "probe.txt")}}
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "CODEX_PROJECT_DIR": str(tmp_path),
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "COS_METRICS_DIR": str(tmp_path / ".cognitive-os" / "metrics"),
        "COS_PRIVATE_MODE": "0",
    })
    result = subprocess.run(
        ["bash", str(ARTIFACT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr


# ── The consumer layout: hooks ship, the primitive now ships too ─────────────
# Until 2026-08-19 hooks/edit-lock-*.sh projected under --full and every one of
# them looked for scripts/edit-coop.sh, which no installer copied. They guarded
# ([ -x "$COOP" ] || exit 0) so nothing crashed -- the subsystem was simply
# registered and inert in every consumer install, while
# primitive-consumer-availability.yaml called it a shared surface.

import json as _json
import shutil as _shutil
import sys as _sys


def _consumer_install(root):
    """What cos_init produces, built by cos_init itself -- not by hand."""
    _sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import cos_init

    cos_init._install_edit_lock_primitive(root, REPO_ROOT)
    hooks_dir = root / ".cognitive-os" / "hooks" / "cos"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for name in ("edit-lock-pre-tool.sh", "edit-lock-session-end.sh"):
        _shutil.copy2(REPO_ROOT / "hooks" / name, hooks_dir / name)
    return hooks_dir


def _fire(hook, root, payload=None):
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(root),
        "CLAUDE_PROJECT_DIR": str(root),
        "COS_EDIT_LOCK_NO_PID_CHECK": "1",
        "COGNITIVE_OS_SESSION_ID": "sesion-de-prueba",
    })
    env.pop("CODEX_PROJECT_DIR", None)
    return subprocess.run(
        ["bash", str(hook)], input=_json.dumps(payload or {}), text=True,
        capture_output=True, env=env, cwd=str(root), timeout=30, check=False,
    )


def test_lock_cycle_completes_in_a_consumer_install(tmp_path) -> None:
    """Acquire through the hook, release through the hook, in the projected layout."""
    hooks_dir = _consumer_install(tmp_path)
    lock = tmp_path / ".cognitive-os" / "runtime" / "edit-locks" / "docs--ejemplo.md"

    acquired = _fire(hooks_dir / "edit-lock-pre-tool.sh", tmp_path,
                     {"tool_name": "Edit", "tool_input": {"file_path": "docs/ejemplo.md"}})
    assert acquired.returncode == 0, acquired.stderr
    assert lock.is_dir(), "the hook did not acquire a lock in the consumer layout"
    assert 'sesion-de-prueba' in (lock / "meta.yaml").read_text(encoding="utf-8"), (
        "the lock carries the wrong identity: hook and CLI disagree"
    )

    released = _fire(hooks_dir / "edit-lock-session-end.sh", tmp_path)
    assert released.returncode == 0, released.stderr
    assert not lock.exists(), "session-end did not release the lock"


def test_hook_is_inert_when_the_primitive_is_absent(tmp_path) -> None:
    """Null control: the cycle above must prove PROJECTION, not just that a hook
    runs. With no primitive the same hook acquires nothing and stays quiet -- the
    state every consumer install was in before the primitive shipped."""
    hooks_dir = tmp_path / ".cognitive-os" / "hooks" / "cos"
    hooks_dir.mkdir(parents=True)
    _shutil.copy2(REPO_ROOT / "hooks" / "edit-lock-pre-tool.sh", hooks_dir / "edit-lock-pre-tool.sh")

    result = _fire(hooks_dir / "edit-lock-pre-tool.sh", tmp_path,
                   {"tool_name": "Edit", "tool_input": {"file_path": "docs/ejemplo.md"}})

    assert result.returncode == 0, result.stderr
    assert result.stderr.strip() == ""
    assert not (tmp_path / ".cognitive-os" / "runtime" / "edit-locks").exists()
