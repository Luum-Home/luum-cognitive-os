# SCOPE: os-only
"""Portability proof for hooks/session-token-aggregator.sh.

Stop-hook wrapper that delegates to scripts/aggregate_session_tokens.py. It is
shared (scope=both, consumer_surface=shared per primitive_scope_health.py)
rather than maintainer-only, so it does not belong to the os-only family
proof (tests/red_team/portability/test_os_only_scope_family.py).

Falsification probes:

1. The hook must not crash and must exit 0 when invoked from an arbitrary
   project root that has no scripts/aggregate_session_tokens.py -- it must not
   hardcode the OS repo's own path.
2. The killswitch (DISABLE_HOOK_SESSION_TOKEN_AGGREGATOR=1) must short-circuit
   before any project-dir resolution happens.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "hooks" / "session-token-aggregator.sh"


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


def test_session_token_aggregator_safe_invocation_from_arbitrary_project_root(tmp_path: Path) -> None:
    result = _run(tmp_path)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert str(REPO_ROOT) not in output
    assert "No such file or directory" not in output
    assert "Traceback" not in output


def test_session_token_aggregator_killswitch_short_circuits(tmp_path: Path) -> None:
    result = _run(tmp_path, {"DISABLE_HOOK_SESSION_TOKEN_AGGREGATOR": "1"})
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert output.strip() == ""
