from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def run_hook(name: str, project: Path, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(project),
        "COGNITIVE_OS_PROJECT_DIR": str(project),
        "COGNITIVE_OS_SESSION_ID": "test-session",
    }
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(REPO / "hooks" / name)],
        cwd=REPO,
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )


def test_branch_ownership_release_fails_open_without_project_state(tmp_path: Path) -> None:
    result = run_hook("branch-ownership-release.sh", tmp_path)
    assert result.returncode == 0


def test_cross_session_coordination_guard_fails_open_without_project_script(tmp_path: Path) -> None:
    result = run_hook("cross-session-coordination-guard.sh", tmp_path, {"PROJECT_DIR": str(tmp_path)})
    assert result.returncode == 0


def test_dangerous_env_flag_detector_fails_open_without_detector_script(tmp_path: Path) -> None:
    result = run_hook("dangerous-env-flag-detector.sh", tmp_path)
    assert result.returncode == 0
    assert "DANGEROUS ENV FLAG DETECTOR" not in result.stderr


def test_promotion_proposer_weekly_respects_disable_flag(tmp_path: Path) -> None:
    result = run_hook("promotion-proposer-weekly.sh", tmp_path, {"DISABLE_PROMOTION_PROPOSER": "1"})
    assert result.returncode == 0


def test_validator_soak_weekly_throttle_skips_recent_marker(tmp_path: Path) -> None:
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / ".last-validator-soak-eval").write_text(str(int(time.time())), encoding="utf-8")

    result = run_hook("validator-soak-weekly.sh", tmp_path)
    assert result.returncode == 0
    assert "promotion proposal" not in result.stderr.lower()
