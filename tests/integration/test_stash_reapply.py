"""Integration tests for ADR-116 P4.3 — stash provenance auto-reapply.

Tests exercise the SessionStart hook (session-start-stash-reapply.sh) plus the
stash_provenance Python library against real git repositories spun up in tmp_path.

All git operations use subprocess so the shell logic runs as production would.
No mocks for git ops.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.timeout(60)]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_DIR = PROJECT_ROOT / "hooks"
HOOK_PATH = HOOKS_DIR / "session-start-stash-reapply.sh"
LIB_PATH = PROJECT_ROOT / "lib"
PACKAGES_LIB = PROJECT_ROOT / "packages" / "agent-coordination" / "lib"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(args: List[str], cwd: Path, check: bool = True, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    full_env = os.environ.copy()
    full_env["GIT_AUTHOR_NAME"] = "COS Test"
    full_env["GIT_AUTHOR_EMAIL"] = "test@cos.test"
    full_env["GIT_COMMITTER_NAME"] = "COS Test"
    full_env["GIT_COMMITTER_EMAIL"] = "test@cos.test"
    if env:
        full_env.update(env)
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
        env=full_env,
    )


def _make_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git(["init"], cwd=path)
    _git(["config", "user.email", "test@cos.test"], cwd=path)
    _git(["config", "user.name", "COS Test"], cwd=path)
    readme = path / "README.md"
    readme.write_text("initial")
    _git(["add", "README.md"], cwd=path)
    _git(["commit", "-m", "initial"], cwd=path)


def _make_tracked_dirty(repo: Path, filename: str = "work.txt", content: str = "dirty") -> Path:
    f = repo / filename
    f.write_text(content)
    _git(["add", filename], cwd=repo)
    return f


def _stash(repo: Path, message: str) -> str:
    """Stash all staged/unstaged tracked changes; returns stash ref like 'stash@{0}'."""
    _git(["stash", "push", "-m", message], cwd=repo)
    result = _git(["stash", "list", "--max-count=1"], cwd=repo)
    ref = result.stdout.split(":")[0].strip()
    return ref


def _seed_provenance(
    repo: Path,
    stash_ref: str,
    session_id: str,
    agent_id: str = "agent-test-001",
    original_files: Optional[List[str]] = None,
) -> None:
    """Write a provenance record directly via the Python API."""
    runtime_dir = repo / ".cognitive-os" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    env["PYTHONPATH"] = str(PACKAGES_LIB) + os.pathsep + str(LIB_PATH) + os.pathsep + str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    files_str = "\n".join(original_files or ["work.txt"])
    subprocess.run(
        [
            sys.executable, "-m", "stash_provenance", "record",
            "--stash-ref", stash_ref,
            "--session-id", session_id,
            "--agent-id", agent_id,
            "--original-files", files_str,
            "--created-at", ts,
        ],
        cwd=repo,
        env=env,
        capture_output=True,
        check=True,
    )


def _run_hook(
    repo: Path,
    session_id: str,
    env_extra: Optional[dict] = None,
) -> subprocess.CompletedProcess:
    """Run the SessionStart hook against repo."""
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    env["COGNITIVE_OS_SESSION_ID"] = session_id
    env["PYTHONPATH"] = str(PACKAGES_LIB) + os.pathsep + str(LIB_PATH) + os.pathsep + str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    # Suppress killswitch and validation mode guards
    env["COS_SUPPRESS_AGENT_SNAPSHOT"] = "0"
    env["COS_VALIDATION_MODE"] = "0"
    # Disable stash lock timeouts to speed up tests
    env["COS_STASH_LOCK_TIMEOUT"] = "5"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


def _provenance_records(repo: Path, session_id: str) -> list:
    """Return provenance records for session_id via the Python API."""
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    env["PYTHONPATH"] = str(PACKAGES_LIB) + os.pathsep + str(LIB_PATH) + os.pathsep + str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-m", "stash_provenance", "find-by-session", session_id, "--json"],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    return json.loads(result.stdout.strip())


def _read_all_provenance(repo: Path) -> list:
    """Read all provenance records from the JSONL file directly."""
    pf = repo / ".cognitive-os" / "runtime" / "stash-provenance.jsonl"
    if not pf.exists():
        return []
    records = []
    for line in pf.read_text().splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_same_session_id_reapplies(tmp_path: Path) -> None:
    """SessionStart with matching session_id and clean tree auto-reapplies the stash."""
    repo = tmp_path / "repo"
    _make_repo(repo)

    # Create a dirty tracked file and stash it
    work_file = _make_tracked_dirty(repo, "work.txt", "important change")
    stash_ref = _stash(repo, "auto-pre-agent-testrun001")

    # Verify file is gone after stash
    assert not work_file.exists() or work_file.read_text() != "important change", \
        "work.txt should not contain dirty content after stash"

    session_id = "session-abc-123"
    _seed_provenance(repo, stash_ref, session_id)

    result = _run_hook(repo, session_id, {"COS_AUTO_REAPPLY_STASH": "1"})
    assert result.returncode == 0, f"Hook must exit 0, got: {result.stderr}"

    # File should be restored
    assert work_file.exists(), "work.txt should be restored after auto-reapply"
    assert work_file.read_text() == "important change", \
        f"work.txt content should match original, got: {work_file.read_text()}"

    # Provenance should be marked reapplied
    all_records = _read_all_provenance(repo)
    matching = [r for r in all_records if r.get("stash_ref") == stash_ref]
    assert matching, "Provenance record must exist"
    assert matching[0]["status"] == "reapplied", \
        f"Expected status='reapplied', got: {matching[0]['status']}"
    assert matching[0].get("reapplied_at"), "reapplied_at must be set"


def test_dirty_tree_skips_reapply(tmp_path: Path) -> None:
    """If the working tree is dirty when the hook runs, reapply must be skipped."""
    repo = tmp_path / "repo"
    _make_repo(repo)

    # Create, stash a tracked file
    _make_tracked_dirty(repo, "first.txt", "first change")
    stash_ref = _stash(repo, "auto-pre-agent-dirty001")

    session_id = "session-dirty-999"
    _seed_provenance(repo, stash_ref, session_id, original_files=["first.txt"])

    # Make the tree dirty again (different file) so skip logic fires
    second = repo / "second.txt"
    second.write_text("concurrent work")
    _git(["add", "second.txt"], cwd=repo)

    result = _run_hook(repo, session_id, {"COS_AUTO_REAPPLY_STASH": "1"})
    assert result.returncode == 0, f"Hook must exit 0 even when dirty, got: {result.stderr}"

    # Stderr should contain skipped event
    combined = result.stdout + result.stderr
    assert "stash_reapply_skipped" in combined or "working_tree_dirty" in combined, \
        f"Expected skip event in output, got:\n{combined}"

    # Provenance record should NOT be marked reapplied
    all_records = _read_all_provenance(repo)
    matching = [r for r in all_records if r.get("stash_ref") == stash_ref]
    assert matching, "Provenance record must still exist"
    assert matching[0]["status"] != "reapplied", \
        f"Record should not be reapplied when tree was dirty, got: {matching[0]['status']}"


def test_mismatched_session_id_skips(tmp_path: Path) -> None:
    """Stash for session-A must not be applied when hook runs for session-B."""
    repo = tmp_path / "repo"
    _make_repo(repo)

    _make_tracked_dirty(repo, "work.txt", "session-a data")
    stash_ref = _stash(repo, "auto-pre-agent-session-a")

    session_a = "session-aaa-001"
    session_b = "session-bbb-002"
    _seed_provenance(repo, stash_ref, session_a)

    # Run hook as session-B
    result = _run_hook(repo, session_b, {"COS_AUTO_REAPPLY_STASH": "1"})
    assert result.returncode == 0, f"Hook must exit 0, got: {result.stderr}"

    # Stash should NOT have been applied
    work_file = repo / "work.txt"
    if work_file.exists():
        assert work_file.read_text() != "session-a data", \
            "session-B must not have received session-A's stash content"

    # Provenance record for session-A should remain pending
    all_records = _read_all_provenance(repo)
    matching = [r for r in all_records if r.get("stash_ref") == stash_ref]
    assert matching, "Provenance record must still exist"
    assert matching[0]["status"] != "reapplied", \
        "Session-A's stash must not be marked reapplied by session-B"


def test_env_var_gates_auto_apply(tmp_path: Path) -> None:
    """Without COS_AUTO_REAPPLY_STASH=1, the hook emits 'offered' but does not apply."""
    repo = tmp_path / "repo"
    _make_repo(repo)

    _make_tracked_dirty(repo, "work.txt", "gate test content")
    stash_ref = _stash(repo, "auto-pre-agent-gate001")

    session_id = "session-gate-456"
    _seed_provenance(repo, stash_ref, session_id)

    # Run without COS_AUTO_REAPPLY_STASH
    env = {"COS_AUTO_REAPPLY_STASH": ""}
    result = _run_hook(repo, session_id, env)
    assert result.returncode == 0, f"Hook must exit 0, got: {result.stderr}"

    # Stash should NOT be applied (work.txt stays absent / unchanged)
    work_file = repo / "work.txt"
    if work_file.exists():
        assert work_file.read_text() != "gate test content", \
            "File must not be restored without COS_AUTO_REAPPLY_STASH=1"

    # offered event must appear
    combined = result.stdout + result.stderr
    assert "stash_reapply_offered" in combined, \
        f"Expected stash_reapply_offered in output without env var, got:\n{combined}"

    # Record remains unconsumed
    all_records = _read_all_provenance(repo)
    matching = [r for r in all_records if r.get("stash_ref") == stash_ref]
    assert matching, "Provenance record must exist"
    assert matching[0]["status"] != "reapplied", \
        "Record must remain pending when auto-reapply gate is not set"


def test_mark_reapplied_prevents_double_apply(tmp_path: Path) -> None:
    """Running the hook twice on the same stash must not apply it a second time."""
    repo = tmp_path / "repo"
    _make_repo(repo)

    _make_tracked_dirty(repo, "work.txt", "double apply test")
    stash_ref = _stash(repo, "auto-pre-agent-double001")

    session_id = "session-double-789"
    _seed_provenance(repo, stash_ref, session_id)

    # First run — should apply
    result1 = _run_hook(repo, session_id, {"COS_AUTO_REAPPLY_STASH": "1"})
    assert result1.returncode == 0

    work_file = repo / "work.txt"
    assert work_file.exists(), "First apply must restore the file"
    first_content = work_file.read_text()
    assert first_content == "double apply test"

    # Re-stash so the working tree is clean for second run
    _git(["stash", "push", "-m", "second-round-cleanup"], cwd=repo)

    # Second run — record is now marked reapplied, find_by_session returns empty
    result2 = _run_hook(repo, session_id, {"COS_AUTO_REAPPLY_STASH": "1"})
    assert result2.returncode == 0

    # The original stash (stash_ref) must not be applied again.
    # Since the provenance record status == "reapplied", find_by_session skips it.
    all_records = _read_all_provenance(repo)
    matching = [r for r in all_records if r.get("stash_ref") == stash_ref]
    assert matching, "Provenance record must still exist"
    assert matching[0]["status"] == "reapplied", \
        "Record must remain 'reapplied' after first successful apply"
