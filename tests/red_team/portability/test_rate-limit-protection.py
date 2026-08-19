# SCOPE: os-only
"""Portability + contract proof for rules/rate-limit-protection.md.

The rule documents `hooks/token-budget-monitor.sh` (PreToolUse on Agent).
Until 2026-08-19 this proof pointed at `hooks/rate-limit-protection.sh`, a
deprecated no-op shim: the rule's only behavior evidence came from a script
that did nothing but print a deprecation warning. The shim was deleted; this
file now exercises the hook the rule actually describes.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "hooks/token-budget-monitor.sh"
RULE = REPO_ROOT / "rules/rate-limit-protection.md"


def _env(project_dir: Path, **extra: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
            "CODEX_PROJECT_DIR": str(project_dir),
            "CLAUDE_PROJECT_DIR": str(project_dir),
            "COS_PRIVATE_MODE": "0",
        }
    )
    env.pop("COS_KILLSWITCH", None)
    env.update(extra)
    return env


def _run(project_dir: Path, **extra: str) -> subprocess.CompletedProcess[str]:
    payload = {"tool_name": "Agent", "tool_input": {"prompt": "probe"}}
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(project_dir),
        env=_env(project_dir, **extra),
        timeout=60,
    )


def test_rule_names_the_hook_that_implements_it() -> None:
    """The rule must point at a hook that exists; the shim it named is gone."""
    text = RULE.read_text(encoding="utf-8")
    assert "hooks/token-budget-monitor.sh" in text
    assert HOOK.exists(), "rule documents a hook that is not on disk"
    assert "hooks/rate-limit-protection.sh" not in text


def test_override_contract_short_circuits_the_hook(tmp_path: Path) -> None:
    """Rule §Override: RATE_LIMIT_OVERRIDE=true bypasses the block."""
    result = _run(tmp_path, RATE_LIMIT_OVERRIDE="true")
    assert result.returncode == 0, result.stderr
    # Override runs before any metrics work: nothing is written under the probe root.
    assert not (tmp_path / ".cognitive-os" / "metrics").exists()


def test_fresh_budget_does_not_block_and_stays_inside_probe_root(tmp_path: Path) -> None:
    """With no recorded spend the hook passes, and writes only under the probe root."""
    result = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert str(REPO_ROOT) not in result.stdout
    metrics = tmp_path / ".cognitive-os" / "metrics"
    assert metrics.is_dir(), "hook must write its metrics under the caller's project dir"


def _spend(project_dir: Path, total_tokens: int) -> Path:
    """Record *total_tokens* of spend inside the last hour, in the shape the hook reads."""
    import time

    metrics = project_dir / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    (metrics / "cost-events.jsonl").write_text(
        json.dumps({"timestamp": int(time.time()), "total_tokens": total_tokens}) + "\n",
        encoding="utf-8",
    )
    return metrics


def test_exhausted_hourly_budget_blocks_with_exit_2(tmp_path: Path) -> None:
    """Rule §Thresholds: >=95% of the hourly token budget must BLOCK (exit 2)."""
    _spend(tmp_path, 4_900_000)  # 98% of 5M
    result = _run(tmp_path, RATE_LIMIT_HOURLY_TOKENS="5000000")
    assert result.returncode == 2, (result.returncode, result.stdout, result.stderr)
    assert "RATE LIMIT REACHED" in result.stderr
    assert "RATE_LIMIT_OVERRIDE" in result.stderr, "block must state the documented escape hatch"


def test_warn_band_reports_but_does_not_block(tmp_path: Path) -> None:
    """Rule §Thresholds: 80-94% must WARN, not block — the band must be distinguishable."""
    _spend(tmp_path, 4_250_000)  # 85% of 5M
    result = _run(tmp_path, RATE_LIMIT_HOURLY_TOKENS="5000000")
    assert result.returncode == 0, (result.returncode, result.stderr)
    assert "WARNING" in result.stderr


def test_override_still_wins_over_an_exhausted_budget(tmp_path: Path) -> None:
    """Rule §Override: the escape hatch must survive the blocking condition."""
    _spend(tmp_path, 4_900_000)
    blocked = _run(tmp_path, RATE_LIMIT_HOURLY_TOKENS="5000000")
    assert blocked.returncode == 2, "precondition: this budget must block without the override"
    allowed = _run(tmp_path, RATE_LIMIT_HOURLY_TOKENS="5000000", RATE_LIMIT_OVERRIDE="true")
    assert allowed.returncode == 0, (allowed.returncode, allowed.stderr)
