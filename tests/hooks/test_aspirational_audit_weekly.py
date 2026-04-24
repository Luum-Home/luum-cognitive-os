"""
tests/hooks/test_aspirational_audit_weekly.py

Behavioral tests for hooks/aspirational-audit-weekly.sh.
Tests use subprocess to invoke the hook with a synthetic project root.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
HOOK = REPO_ROOT / "hooks" / "aspirational-audit-weekly.sh"


def run_hook(
    project_dir: Path,
    *,
    env_overrides: dict | None = None,
    timeout: int = 15,
) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir)}
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(HOOK)],
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def make_minimal_project(tmp_path: Path, *, with_audit_script: bool = True) -> Path:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps({"hooks": {}}))
    (tmp_path / "hooks").mkdir()
    (tmp_path / "lib").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "skills").mkdir()
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)
    (tmp_path / "tests" / "contracts").mkdir(parents=True)
    (tmp_path / "rules").mkdir()
    (tmp_path / "docs").mkdir()
    if with_audit_script:
        # Copy real script so the hook can actually run it
        real_script = REPO_ROOT / "scripts" / "aspirational_audit.py"
        if real_script.exists():
            import shutil
            shutil.copy(real_script, tmp_path / "scripts" / "aspirational_audit.py")
    return tmp_path


class TestHookExitBehavior:
    def test_hook_exits_0_when_marker_fresh(self, tmp_path):
        """Hook exits 0 silently when last-run marker is < 7 days old."""
        project = make_minimal_project(tmp_path)
        marker = project / ".cognitive-os" / "metrics" / ".last-aspirational-audit"
        marker.write_text(str(time.time()))  # just now

        result = run_hook(project)
        assert result.returncode == 0
        # No advisory emitted since it was throttled
        assert result.stderr == "" or "aspirational" not in result.stderr.lower()

    def test_hook_runs_audit_when_stale(self, tmp_path):
        """Hook runs audit when marker is older than 7 days (or missing)."""
        project = make_minimal_project(tmp_path)
        # No marker → fresh run should happen (and exit 0)
        result = run_hook(project)
        assert result.returncode == 0

    def test_hook_fail_safe_on_missing_script(self, tmp_path):
        """Hook exits 0 when aspirational_audit.py is missing (fail-open)."""
        project = make_minimal_project(tmp_path, with_audit_script=False)
        # Do NOT create scripts/aspirational_audit.py
        result = run_hook(project)
        assert result.returncode == 0

    def test_hook_silent_when_ratio_low(self, tmp_path):
        """Hook emits no advisory when dormant+aspirational ratio ≤ 40%."""
        project = make_minimal_project(tmp_path, with_audit_script=False)
        # No scripts/skills/hooks — zero components → ratio = 0% → no advisory
        result = run_hook(project)
        assert result.returncode == 0
        assert "aspirational audit" not in result.stderr.lower()

    def test_hook_emits_advisory_when_ratio_high(self, tmp_path):
        """Hook emits advisory to stderr when ratio > 40%."""
        project = make_minimal_project(tmp_path)
        # Add several unregistered hooks to push ratio above 40%
        for i in range(5):
            (project / "hooks" / f"future-hook-{i}.sh").write_text(
                f"#!/usr/bin/env bash\necho hook{i}\n"
            )
        # No registered hooks → all 5 are ASPIRATIONAL → ratio = 100% > 40%
        result = run_hook(project)
        assert result.returncode == 0
        # Advisory should appear on stderr
        assert "aspirational audit" in result.stderr.lower() or \
               "dormant" in result.stderr.lower() or \
               "%" in result.stderr
