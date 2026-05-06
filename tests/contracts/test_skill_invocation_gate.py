"""Contract tests for ADR-188: orchestrator-skill-invocation-gate.

Covers all five acceptance scenarios from the ADR.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "orchestrator-skill-invocation-gate.sh"


def _seed_suggestion(workdir: Path, *, session_id: str, skill: str, confidence: float) -> str:
    """Write a skill-suggestion.jsonl entry and return the prompt_hash."""
    metrics = workdir / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": "2026-05-06T05:00:00+00:00",
        "session_id": session_id,
        "prompt_hash": "deadbeefcafebabe",
        "skill_name": skill,
        "invoke_command": f"/{skill}",
        "confidence": confidence,
        "threshold_met": confidence >= 0.80,
    }
    with (metrics / "skill-suggestion.jsonl").open("a") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry["prompt_hash"]


def _run_hook(workdir: Path, *, tool_name: str, tool_input: dict, env_extra=None) -> subprocess.CompletedProcess:
    payload = {"tool_name": tool_name, "tool_input": tool_input, "session_id": "test-session-188"}
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(workdir)
    env["CLAUDE_PROJECT_DIR"] = str(workdir)
    env["COGNITIVE_OS_SESSION_ID"] = "test-session-188"
    # Disable any inherited overrides
    env.pop("COS_ALLOW_SKILL_BYPASS", None)
    env.pop("COS_SKILL_BYPASS_REASON", None)
    env.pop("DISABLE_HOOK_ORCHESTRATOR_SKILL_INVOCATION_GATE", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )


@pytest.fixture
def workdir(tmp_path: Path):
    # Provide a project-shaped tmp dir with a symlink to the real lib/skill_router
    (tmp_path / "lib").mkdir()
    real_router = REPO_ROOT / "lib" / "skill_router.py"
    shutil.copy(real_router, tmp_path / "lib" / "skill_router.py")
    # Empty __init__ so `from lib.skill_router import ...` works
    (tmp_path / "lib" / "__init__.py").write_text("")
    return tmp_path


def test_high_confidence_skill_invoked_passes(workdir: Path):
    _seed_suggestion(workdir, session_id="test-session-188", skill="repo-scout", confidence=0.95)
    # tool_input.prompt loads the skill explicitly
    res = _run_hook(
        workdir,
        tool_name="Agent",
        tool_input={"prompt": "Load skills/repo-scout/SKILL.md and proceed", "description": "x"},
    )
    assert res.returncode == 0, res.stderr
    # No counter file should be created (PASS)
    counter = workdir / ".cognitive-os" / "runtime" / "skill-bypass-counter-test-session-188"
    assert not counter.exists()


def test_high_confidence_bypass_annotation_passes_and_audits(workdir: Path):
    _seed_suggestion(workdir, session_id="test-session-188", skill="repo-scout", confidence=0.95)
    res = _run_hook(
        workdir,
        tool_name="Agent",
        tool_input={
            "prompt": "SKILL_BYPASS: repo-scout confidence=0.95 reason=already-evaluated\nProceed with bespoke task.",
            "description": "x",
        },
    )
    assert res.returncode == 0, res.stderr
    audit = workdir / ".cognitive-os" / "metrics" / "skill-bypass.jsonl"
    assert audit.exists()
    lines = [json.loads(l) for l in audit.read_text().splitlines() if l.strip()]
    assert len(lines) == 1
    assert lines[0]["suggested_skill"] == "repo-scout"
    assert lines[0]["actor"] == "orchestrator-annotation"
    assert lines[0]["confidence"] == 0.95


def test_high_confidence_bespoke_warns_then_blocks_after_three(workdir: Path):
    _seed_suggestion(workdir, session_id="test-session-188", skill="repo-scout", confidence=0.95)

    # 1st: WARN, exit 0
    r1 = _run_hook(workdir, tool_name="Agent", tool_input={"prompt": "do something custom"})
    assert r1.returncode == 0
    assert "WARN" in r1.stderr
    assert "1/3" in r1.stderr

    # 2nd: WARN, exit 0
    r2 = _run_hook(workdir, tool_name="Agent", tool_input={"prompt": "do something else"})
    assert r2.returncode == 0
    assert "WARN" in r2.stderr
    assert "2/3" in r2.stderr

    # 3rd: BLOCK, exit 2
    r3 = _run_hook(workdir, tool_name="Agent", tool_input={"prompt": "still bespoke"})
    assert r3.returncode == 2
    assert "BLOCK" in r3.stderr


def test_low_confidence_no_enforcement(workdir: Path):
    _seed_suggestion(workdir, session_id="test-session-188", skill="repo-scout", confidence=0.70)
    res = _run_hook(workdir, tool_name="Agent", tool_input={"prompt": "do bespoke thing"})
    assert res.returncode == 0
    # No counter, no audit
    counter = workdir / ".cognitive-os" / "runtime" / "skill-bypass-counter-test-session-188"
    assert not counter.exists()
    audit = workdir / ".cognitive-os" / "metrics" / "skill-bypass.jsonl"
    assert not audit.exists()
    # No WARN emitted
    assert "WARN" not in res.stderr


def test_env_override_with_reason_passes_and_audits(workdir: Path):
    _seed_suggestion(workdir, session_id="test-session-188", skill="repo-scout", confidence=0.95)
    res = _run_hook(
        workdir,
        tool_name="Agent",
        tool_input={"prompt": "do bespoke"},
        env_extra={"COS_ALLOW_SKILL_BYPASS": "1", "COS_SKILL_BYPASS_REASON": "broken-skill-test"},
    )
    assert res.returncode == 0, res.stderr
    audit = workdir / ".cognitive-os" / "metrics" / "skill-bypass.jsonl"
    assert audit.exists()
    rec = json.loads(audit.read_text().splitlines()[-1])
    assert rec["actor"] == "env-override"
    assert "broken-skill-test" in rec["reason"]


def test_env_override_without_reason_blocks(workdir: Path):
    _seed_suggestion(workdir, session_id="test-session-188", skill="repo-scout", confidence=0.95)
    res = _run_hook(
        workdir,
        tool_name="Agent",
        tool_input={"prompt": "do bespoke"},
        env_extra={"COS_ALLOW_SKILL_BYPASS": "1"},
    )
    assert res.returncode == 2
    assert "COS_SKILL_BYPASS_REASON" in res.stderr


def test_killswitch_disables_hook(workdir: Path):
    _seed_suggestion(workdir, session_id="test-session-188", skill="repo-scout", confidence=0.95)
    res = _run_hook(
        workdir,
        tool_name="Agent",
        tool_input={"prompt": "do bespoke"},
        env_extra={"DISABLE_HOOK_ORCHESTRATOR_SKILL_INVOCATION_GATE": "1"},
    )
    assert res.returncode == 0
    assert "WARN" not in res.stderr


def test_last_suggestion_returns_highest_confidence_for_session():
    """Unit-style coverage of lib.skill_router.last_suggestion()."""
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from lib.skill_router import last_suggestion  # noqa

    # Use an isolated tmp project to avoid colliding with real metrics.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        m = tdp / ".cognitive-os" / "metrics"
        m.mkdir(parents=True)
        s = tdp / ".cognitive-os" / "sessions"
        s.mkdir(parents=True)
        # Write two suggestions for same session, second has higher conf.
        with (m / "skill-suggestion.jsonl").open("w") as fh:
            fh.write(json.dumps({"ts": "2026-05-06T05:00:00+00:00", "session_id": "S",
                                  "prompt_hash": "h1", "skill_name": "a",
                                  "confidence": 0.85, "threshold_met": True}) + "\n")
            fh.write(json.dumps({"ts": "2026-05-06T05:01:00+00:00", "session_id": "S",
                                  "prompt_hash": "h2", "skill_name": "b",
                                  "confidence": 0.95, "threshold_met": True}) + "\n")
        out = last_suggestion("S", project_root=tdp)
        assert out is not None
        assert out["skill"] == "b"
        assert out["confidence"] == 0.95

        # Different session -> None
        assert last_suggestion("OTHER", project_root=tdp) is None
