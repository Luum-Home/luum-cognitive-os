# SCOPE: os-only
"""Portability proof for hooks/session-token-aggregator.sh.

Stop-hook wrapper that delegates to scripts/aggregate_session_tokens.py. It is
shared (scope=both, consumer_surface=shared per primitive_scope_health.py)
rather than maintainer-only, so it does not belong to the os-only family proof
(tests/red_team/portability/test_os_only_scope_family.py).

Every probe here runs against a project root that has its OWN aggregator
script, because the hook exits silently when it finds none (line 23). Probing
an empty directory is how the first version of this file ended up asserting
that the killswitch produced no output when NEITHER branch produced any:
measured 2026-08-19, both paths returned rc=0 with zero bytes, so the
assertion held whether or not the killswitch worked at all.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "hooks" / "session-token-aggregator.sh"
MARKER = "AGREGADOR-DEL-PROYECTO-CORRIO"


def _project(tmp_path: Path, *, with_aggregator: bool) -> Path:
    """A project root unrelated to the OS repo, optionally carrying its own script."""
    if with_aggregator:
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "aggregate_session_tokens.py").write_text(
            f'import sys\nsys.stderr.write("{MARKER}\\n")\n', encoding="utf-8"
        )
    return tmp_path


def _run(project_dir: Path, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(HOOK)],
        text=True,
        capture_output=True,
        cwd=project_dir,
        env=env,
        timeout=20,
        check=False,
    )


def test_resolves_the_aggregator_from_the_project_root_not_the_os_repo(tmp_path: Path) -> None:
    """The portability claim itself: the script comes from PROJECT_DIR."""
    result = _run(_project(tmp_path, with_aggregator=True))
    output = result.stdout + result.stderr

    assert result.returncode == 0, output
    assert MARKER in output, "the hook did not run the project's own aggregator"
    assert str(REPO_ROOT) not in output
    assert "Traceback" not in output


def test_killswitch_suppresses_an_aggregator_that_would_otherwise_run(tmp_path: Path) -> None:
    """Discriminates only because the control above proves the marker appears."""
    project = _project(tmp_path, with_aggregator=True)
    result = _run(project, {"DISABLE_HOOK_SESSION_TOKEN_AGGREGATOR": "1"})
    output = result.stdout + result.stderr

    assert result.returncode == 0, output
    assert MARKER not in output, "the killswitch did not short-circuit"
    assert output.strip() == ""


def test_exits_quietly_when_the_project_has_no_aggregator(tmp_path: Path) -> None:
    """Null control: absence of the script is not an error, and not a crash."""
    result = _run(_project(tmp_path, with_aggregator=False))
    output = result.stdout + result.stderr

    assert result.returncode == 0, output
    assert output.strip() == ""
    assert "No such file or directory" not in output
