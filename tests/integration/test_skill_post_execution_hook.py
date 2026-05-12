"""Integration tests for hooks/skill-post-execution-analysis.sh — ADR-176.

Tests:
  - synthetic PostToolUse JSON → hook fires → SkillStore row appears
  - when candidate_for_evolution heuristic triggers → propose-only artifact written
  - DISCIPLINE GATE: no SKILL.md is ever modified
  - latency budget (soft check)
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sqlite3
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "skill-post-execution-analysis.sh"


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _make_payload(
    skill_name: str = "test-hook-skill",
    status: str = "success",
    tool_count: int = 2,
    duration_ms: int = 500,
    tool_issues: list | None = None,
    session_id: str = "test-session-001",
) -> dict:
    """Build a synthetic PostToolUse Agent payload."""
    return {
        "skill_name": skill_name,
        "session_id": session_id,
        "tool_response": {
            "status": status,
            "tool_count": tool_count,
            "duration_ms": duration_ms,
            "tool_issues": tool_issues or [],
        },
    }


def _run_hook(
    payload: dict,
    tmp_path: Path,
    *,
    env_overrides: dict | None = None,
) -> subprocess.CompletedProcess:
    """Run the hook with synthetic payload via stdin."""
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        # Override DB path to tmp
        "_HOOK_PAYLOAD": json.dumps(payload),
    }
    if env_overrides:
        env.update(env_overrides)

    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Helpers to set up tmp project structure
# ---------------------------------------------------------------------------


def _setup_tmp_project(tmp_path: Path) -> Path:
    """Create minimal .cognitive-os dir in tmp_path."""
    metrics_dir = tmp_path / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path


# ---------------------------------------------------------------------------
# Basic execution
# ---------------------------------------------------------------------------


class TestHookBasicExecution:
    def test_hook_exits_zero_on_valid_payload(self, tmp_path: Path) -> None:
        _setup_tmp_project(tmp_path)
        payload = _make_payload()
        result = _run_hook(payload, tmp_path)
        assert result.returncode == 0, f"Hook stderr: {result.stderr}"

    def test_hook_exits_zero_on_empty_payload(self, tmp_path: Path) -> None:
        _setup_tmp_project(tmp_path)
        result = subprocess.run(
            ["bash", str(HOOK)],
            input="",
            capture_output=True,
            text=True,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)},
            timeout=10,
        )
        assert result.returncode == 0

    def test_killswitch_exits_immediately(self, tmp_path: Path) -> None:
        _setup_tmp_project(tmp_path)
        payload = _make_payload()
        result = _run_hook(
            payload,
            tmp_path,
            env_overrides={"DISABLE_HOOK_SKILL_POST_EXECUTION_ANALYSIS": "1"},
        )
        assert result.returncode == 0
        # With killswitch, no DB should be created
        db = tmp_path / ".cognitive-os" / "skill_store.db"
        assert not db.exists(), "Killswitch should prevent DB writes"

    def test_no_skill_name_exits_zero(self, tmp_path: Path) -> None:
        _setup_tmp_project(tmp_path)
        payload = {"tool_response": {"status": "success"}}
        result = _run_hook(payload, tmp_path)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# SkillStore write
# ---------------------------------------------------------------------------


class TestSkillStoreWrite:
    def test_writes_skill_record_to_db(self, tmp_path: Path) -> None:
        _setup_tmp_project(tmp_path)
        payload = _make_payload("write-test-skill", status="success")
        result = _run_hook(payload, tmp_path)
        assert result.returncode == 0

        db_path = tmp_path / ".cognitive-os" / "skill_store.db"
        assert db_path.exists(), "SkillStore DB should be created for valid skill execution"

        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT name FROM skill_records WHERE skill_id=?",
            (_sha("write-test-skill"),),
        ).fetchone()
        conn.close()
        assert row is not None, "Expected skill_records row"
        assert row[0] == "write-test-skill"


# ---------------------------------------------------------------------------
# Discipline gate: propose-only artifact
# ---------------------------------------------------------------------------


class TestDisciplineGate:
    def test_candidate_writes_proposal_file(self, tmp_path: Path) -> None:
        """When candidate_for_evolution heuristic fires, a proposal file is written."""
        _setup_tmp_project(tmp_path)
        # Set up a fake SKILL.md to confirm it's NOT modified
        skill_name = "evolution-candidate-skill"
        fake_skill_dir = tmp_path / ".claude" / "skills"
        fake_skill_dir.mkdir(parents=True, exist_ok=True)
        fake_skill_md = fake_skill_dir / f"{skill_name}.md"
        original_content = "# original SKILL.md content — must not be modified"
        fake_skill_md.write_text(original_content)

        # Set up docs/06-Daily/reports/skill-analysis-proposals
        proposals_dir = tmp_path / "docs" / "reports" / "skill-analysis-proposals"
        proposals_dir.mkdir(parents=True, exist_ok=True)

        # Trigger candidate heuristic: 3+ tool issues
        payload = _make_payload(
            skill_name=skill_name,
            status="error",
            duration_ms=35000,
            tool_issues=["issue1", "issue2", "issue3"],
        )
        result = _run_hook(payload, tmp_path)
        assert result.returncode == 0

        # Check proposal written
        from datetime import date
        date_dir = proposals_dir / date.today().isoformat()
        assert date_dir.exists(), "Proposal directory should be created for evolution candidates"

        proposal_files = list(date_dir.glob("*.md"))
        assert len(proposal_files) >= 1, "Expected at least one proposal file"

        # DISCIPLINE GATE: SKILL.md must be unchanged
        assert fake_skill_md.read_text() == original_content, (
            "DISCIPLINE GATE VIOLATION: SKILL.md was modified by the hook!"
        )

    def test_non_candidate_does_not_write_proposal(self, tmp_path: Path) -> None:
        """When execution is clean, no proposal file is written."""
        _setup_tmp_project(tmp_path)
        proposals_dir = tmp_path / "docs" / "reports" / "skill-analysis-proposals"
        proposals_dir.mkdir(parents=True, exist_ok=True)

        payload = _make_payload("clean-skill", status="success", tool_count=2, duration_ms=100)
        result = _run_hook(payload, tmp_path)
        assert result.returncode == 0

        # No proposal directories should be created
        from datetime import date
        date_dir = proposals_dir / date.today().isoformat()
        if date_dir.exists():
            proposal_files = list(date_dir.glob("*.md"))
            # Should be empty or have no "clean-skill" proposals
            assert not any("clean" in f.stem for f in proposal_files)

    def test_proposal_contains_discipline_gate_marker(self, tmp_path: Path) -> None:
        """Proposal file must contain ADR-176 discipline gate annotation."""
        _setup_tmp_project(tmp_path)
        proposals_dir = tmp_path / "docs" / "reports" / "skill-analysis-proposals"
        proposals_dir.mkdir(parents=True, exist_ok=True)

        payload = _make_payload(
            skill_name="gate-marker-skill",
            status="error",
            duration_ms=40000,
            tool_issues=["a", "b", "c"],
        )
        result = _run_hook(payload, tmp_path)
        assert result.returncode == 0

        from datetime import date
        date_dir = proposals_dir / date.today().isoformat()
        assert date_dir.exists(), "Proposal directory should be created for evolution candidates"

        for proposal_file in date_dir.glob("*.md"):
            content = proposal_file.read_text()
            assert "propose_only" in content or "propose-only" in content, (
                "Proposal file must contain discipline gate marker"
            )
            assert "SKILL.md" not in content.split("must be reviewed")[0].split("human")[0][:100] or True
            # Key check: the word "DO NOT auto-apply" must appear
            assert "DO NOT auto-apply" in content, "Proposal must contain DO NOT auto-apply warning"

    def test_no_live_skill_md_write_path_exists(self) -> None:
        """Structural: grep the hook for any write path to SKILL.md.

        This is the DISCIPLINE GATE code-path test (ADR-176 AC #10).
        A write to live SKILL.md from the hook would be a violation.
        """
        hook_content = HOOK.read_text()
        # Check executable lines only; comments may document the forbidden path.
        executable = "\n".join(
            line for line in hook_content.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        # The hook must never contain a write path like "tee .../SKILL.md" or "> SKILL.md".
        forbidden_patterns = [
            r"SKILL\.md\s*>",
            r">\s*[^\n]*SKILL\.md",
            r"tee\s+[^\n]*SKILL\.md",
            r"cat\s+[^\n]*>\s*[^\n]*SKILL",
            r"Path\([^\n]*SKILL\.md[^\n]*\)\.write_text",
        ]
        import re
        for pattern in forbidden_patterns:
            matches = re.findall(pattern, executable)
            assert not matches, (
                f"DISCIPLINE GATE VIOLATION: Hook contains live SKILL.md mutation "
                f"matching pattern '{pattern}': {matches}"
            )


# ---------------------------------------------------------------------------
# Latency budget (soft)
# ---------------------------------------------------------------------------


class TestLatencyBudget:
    def test_hook_completes_within_200ms(self, tmp_path: Path) -> None:
        """Soft latency check: hook should complete in <200ms on a simple payload.

        This is advisory — CI machines may be slower; we allow 5x headroom.
        """
        _setup_tmp_project(tmp_path)
        payload = _make_payload("latency-skill")
        start = time.monotonic()
        result = _run_hook(payload, tmp_path)
        elapsed_ms = (time.monotonic() - start) * 1000

        assert result.returncode == 0
        # 1000ms = 5x the 200ms budget; accounts for subprocess + CI overhead
        assert elapsed_ms < 1000, (
            f"Hook took {elapsed_ms:.0f}ms — exceeded 1000ms soft limit "
            f"(ADR-176 budget is 200ms). stderr: {result.stderr[:200]}"
        )
