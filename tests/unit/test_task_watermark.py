"""Tests for the P1.4 watermark sweep (ADR-102 Fix P1.4).

Coverage:
1. Mode A: task with expectedOutputs pointing to existing files -> marked
2. Mode A negative: file missing -> still pending
3. Mode B: >=3 token overlap with recent commit subject -> marked
4. Mode B negative: only 1-2 token overlap -> still pending
5. Mode B: task description too short (< 3 content tokens) -> not matched
6. Real-data smoke: run sweep on a copy of active-tasks.json,
   verify task-1777745639 gets marked (or is already terminal/cancelled,
   which is also acceptable).
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers -- mirror the sweep logic from so-reaper.sh for unit-testability
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "have",
    "will", "are", "was", "were", "been", "also", "when", "then", "than",
    "not", "but", "all", "any", "its", "our", "they", "their", "there",
    "what", "which", "some", "such", "via", "add", "use", "run",
}
_MIN_TOKEN_LEN = 4
_WATERMARK_THRESHOLD = 3


def _tokenize(text: str) -> set:
    words = re.findall(r"[a-z]+", text.lower())
    return {w for w in words if len(w) >= _MIN_TOKEN_LEN and w not in _STOPWORDS}


def _mode_a(task: dict, project_dir: Path) -> Tuple[bool, Optional[dict]]:
    outputs = task.get("expectedOutputs") or []
    if not outputs:
        return False, None
    for rel_path in outputs:
        abs_path = project_dir / rel_path
        if not abs_path.is_file():
            return False, None
        if abs_path.stat().st_size < 10:
            return False, None
    return True, {"mode": "A", "matched_paths": list(outputs)}


def _mode_b(
    task: dict, commits: List[Tuple[str, str]]
) -> Tuple[bool, Optional[dict]]:
    desc = task.get("description") or ""
    task_tokens = _tokenize(desc)
    if len(task_tokens) < _WATERMARK_THRESHOLD:
        return False, None
    for sha, subj in commits:
        commit_tokens = _tokenize(subj)
        overlap = task_tokens & commit_tokens
        if len(overlap) >= _WATERMARK_THRESHOLD:
            return True, {
                "mode": "B",
                "commit_sha": sha,
                "commit_subject": subj,
                "matched_tokens": sorted(overlap),
            }
    return False, None


def _now_iso(offset_secs: float = 0.0) -> str:
    dt = datetime.now(timezone.utc) + timedelta(seconds=offset_secs)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_tasks_file(tmp_path: Path, tasks: List[Dict[str, Any]]) -> Path:
    d = tmp_path / ".cognitive-os" / "tasks"
    d.mkdir(parents=True, exist_ok=True)
    path = d / "active-tasks.json"
    path.write_text(
        json.dumps({"version": 1, "tasks": tasks, "lastUpdated": _now_iso()})
    )
    return path


def _read_tasks(tasks_file: Path) -> List[Dict[str, Any]]:
    return json.loads(tasks_file.read_text()).get("tasks", [])


def _run_watermark_sweep(
    tasks_file: Path,
    commits: List[Tuple[str, str]],
    project_dir: Optional[Path] = None,
) -> List[Tuple[str, dict]]:
    """Run the watermark sweep logic directly (no subprocess).

    Returns a list of (task_id, evidence) for every task marked
    completed-by-watermark.
    """
    if project_dir is None:
        project_dir = tasks_file.parent.parent.parent  # tmp_path root

    lock_path = tasks_file.parent / ".active-tasks.lock"
    watermarked: List[Tuple[str, dict]] = []

    with open(lock_path, "w") as lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_EX)
        try:
            data = json.loads(tasks_file.read_text())
            tasks = data.get("tasks", [])
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            changed = False

            active = [t for t in tasks if t.get("status") in ("pending", "in_progress")]
            for t in active:
                matched, evidence = _mode_a(t, project_dir)
                if not matched:
                    matched, evidence = _mode_b(t, commits)
                if matched:
                    t["status"] = "completed-by-watermark"
                    t["completedAt"] = now_iso
                    t["watermark_evidence"] = evidence
                    changed = True
                    watermarked.append((t["id"], evidence))

            if changed:
                data["lastUpdated"] = now_iso
                tmp_fd, tmp_str = tempfile.mkstemp(
                    dir=str(tasks_file.parent),
                    prefix=".active-tasks-tmp-",
                    suffix=".json",
                )
                with os.fdopen(tmp_fd, "w") as fh:
                    json.dump(data, fh, indent=2)
                os.replace(tmp_str, str(tasks_file))
        finally:
            fcntl.flock(lock_fh, fcntl.LOCK_UN)

    return watermarked


# ---------------------------------------------------------------------------
# Mode A tests
# ---------------------------------------------------------------------------


class TestModeA:
    def test_mode_a_marks_when_all_outputs_exist(self, tmp_path):
        """Mode A: task with expectedOutputs pointing to a real file -> marked."""
        out_file = tmp_path / "docs" / "foo.md"
        out_file.parent.mkdir(parents=True)
        out_file.write_text("# Foo\nSome content that is non-trivial.")

        tasks_file = _make_tasks_file(
            tmp_path,
            [
                {
                    "id": "task-mode-a-001",
                    "toolUseId": "toolu_mode_a_001",
                    "description": "create documentation file",
                    "status": "pending",
                    "requested_at": _now_iso(-3600),
                    "launchedAt": _now_iso(-3600),
                    "started_at": _now_iso(-3600),
                    "pid": None,
                    "completedAt": None,
                    "outputSummary": None,
                    "expectedOutputs": ["docs/foo.md"],
                    "checkCommand": None,
                }
            ],
        )

        watermarked = _run_watermark_sweep(tasks_file, commits=[], project_dir=tmp_path)

        assert len(watermarked) == 1, "Expected exactly one task marked by Mode A"
        tid, evidence = watermarked[0]
        assert tid == "task-mode-a-001"
        assert evidence["mode"] == "A"
        assert "docs/foo.md" in evidence["matched_paths"]

        tasks = _read_tasks(tasks_file)
        task = next(t for t in tasks if t["id"] == "task-mode-a-001")
        assert task["status"] == "completed-by-watermark"
        assert task["completedAt"] is not None
        assert task["watermark_evidence"]["mode"] == "A"

    def test_mode_a_skips_when_file_missing(self, tmp_path):
        """Mode A negative: expectedOutputs file does not exist -> task stays pending."""
        tasks_file = _make_tasks_file(
            tmp_path,
            [
                {
                    "id": "task-mode-a-neg-001",
                    "toolUseId": "toolu_mode_a_neg_001",
                    "description": "generate output that has not been created yet",
                    "status": "pending",
                    "requested_at": _now_iso(-300),
                    "launchedAt": _now_iso(-300),
                    "started_at": _now_iso(-300),
                    "pid": None,
                    "completedAt": None,
                    "outputSummary": None,
                    "expectedOutputs": ["docs/nonexistent-output.md"],
                    "checkCommand": None,
                }
            ],
        )

        watermarked = _run_watermark_sweep(tasks_file, commits=[], project_dir=tmp_path)

        assert len(watermarked) == 0, "Task must stay pending when expected file is missing"

        tasks = _read_tasks(tasks_file)
        task = next(t for t in tasks if t["id"] == "task-mode-a-neg-001")
        assert task["status"] == "pending"

    def test_mode_a_skips_trivial_size_file(self, tmp_path):
        """Mode A: file < 10 bytes -> Mode A fails, falls back to Mode B (no match -> pending)."""
        out_file = tmp_path / "empty.md"
        out_file.write_bytes(b"tiny")  # 4 bytes

        tasks_file = _make_tasks_file(
            tmp_path,
            [
                {
                    "id": "task-mode-a-tiny-001",
                    "toolUseId": "toolu_tiny_001",
                    "description": "generate tiny output file document",
                    "status": "pending",
                    "requested_at": _now_iso(-300),
                    "launchedAt": _now_iso(-300),
                    "started_at": _now_iso(-300),
                    "pid": None,
                    "completedAt": None,
                    "outputSummary": None,
                    "expectedOutputs": ["empty.md"],
                    "checkCommand": None,
                }
            ],
        )

        watermarked = _run_watermark_sweep(tasks_file, commits=[], project_dir=tmp_path)

        assert len(watermarked) == 0


# ---------------------------------------------------------------------------
# Mode B tests
# ---------------------------------------------------------------------------


class TestModeB:
    def test_mode_b_marks_on_sufficient_token_overlap(self, tmp_path):
        """Mode B: >=3 distinct content token overlap with recent commit -> marked."""
        tasks_file = _make_tasks_file(
            tmp_path,
            [
                {
                    "id": "task-mode-b-001",
                    "toolUseId": "toolu_mode_b_001",
                    "description": "Fix claim gate false positives",
                    "status": "pending",
                    "requested_at": _now_iso(-7200),
                    "launchedAt": _now_iso(-7200),
                    "started_at": _now_iso(-7200),
                    "pid": None,
                    "completedAt": None,
                    "outputSummary": None,
                    "expectedOutputs": [],
                    "checkCommand": None,
                }
            ],
        )

        commits = [
            ("f4e4ddd1abc123", "fix: suppress prose claim gate false positives"),
        ]

        watermarked = _run_watermark_sweep(tasks_file, commits=commits, project_dir=tmp_path)

        assert len(watermarked) == 1, "Expected task marked by Mode B"
        tid, evidence = watermarked[0]
        assert tid == "task-mode-b-001"
        assert evidence["mode"] == "B"
        assert evidence["commit_sha"] == "f4e4ddd1abc123"
        overlap = set(evidence["matched_tokens"])
        assert len(overlap) >= _WATERMARK_THRESHOLD

        tasks = _read_tasks(tasks_file)
        task = next(t for t in tasks if t["id"] == "task-mode-b-001")
        assert task["status"] == "completed-by-watermark"
        assert task["watermark_evidence"]["mode"] == "B"

    def test_mode_b_skips_on_insufficient_overlap(self, tmp_path):
        """Mode B negative: only 1-2 token overlap -> task stays pending."""
        tasks_file = _make_tasks_file(
            tmp_path,
            [
                {
                    "id": "task-mode-b-neg-001",
                    "toolUseId": "toolu_mode_b_neg_001",
                    "description": "Update authentication middleware configuration",
                    "status": "pending",
                    "requested_at": _now_iso(-3600),
                    "launchedAt": _now_iso(-3600),
                    "started_at": _now_iso(-3600),
                    "pid": None,
                    "completedAt": None,
                    "outputSummary": None,
                    "expectedOutputs": [],
                    "checkCommand": None,
                }
            ],
        )

        commits = [
            # Only "authentication" overlaps (1 token)
            ("abc000000001", "fix: authentication token refresh"),
            # Only "middleware" overlaps (1 token)
            ("abc000000002", "feat: middleware timeout handling"),
        ]

        watermarked = _run_watermark_sweep(tasks_file, commits=commits, project_dir=tmp_path)

        assert len(watermarked) == 0, "Task must stay pending with insufficient token overlap"

        tasks = _read_tasks(tasks_file)
        task = next(t for t in tasks if t["id"] == "task-mode-b-neg-001")
        assert task["status"] == "pending"

    def test_mode_b_skips_short_description(self, tmp_path):
        """Mode B: description with < 3 content tokens is not matched (too ambiguous)."""
        tasks_file = _make_tasks_file(
            tmp_path,
            [
                {
                    "id": "task-mode-b-short-001",
                    "toolUseId": "toolu_short_001",
                    "description": "fix bug",  # "fix" 3 chars, "bug" 3 chars -> 0 tokens >=4
                    "status": "pending",
                    "requested_at": _now_iso(-3600),
                    "launchedAt": _now_iso(-3600),
                    "started_at": _now_iso(-3600),
                    "pid": None,
                    "completedAt": None,
                    "outputSummary": None,
                    "expectedOutputs": [],
                    "checkCommand": None,
                }
            ],
        )

        commits = [("abc111", "fix: fix the bug in handler")]

        watermarked = _run_watermark_sweep(tasks_file, commits=commits, project_dir=tmp_path)

        assert len(watermarked) == 0, "Short description must not produce watermark"

    def test_mode_b_does_not_mark_genuinely_pending(self, tmp_path):
        """A task with no commit match and no expected outputs must stay pending."""
        tasks_file = _make_tasks_file(
            tmp_path,
            [
                {
                    "id": "task-genuinely-pending-001",
                    "toolUseId": "toolu_genuine_001",
                    "description": "Implement distributed caching layer with Redis",
                    "status": "pending",
                    "requested_at": _now_iso(-120),
                    "launchedAt": _now_iso(-120),
                    "started_at": _now_iso(-120),
                    "pid": None,
                    "completedAt": None,
                    "outputSummary": None,
                    "expectedOutputs": [],
                    "checkCommand": None,
                }
            ],
        )

        commits = [
            ("aaa001", "feat: add prometheus metrics exporter"),
            ("aaa002", "fix: correct typo in docs"),
            ("aaa003", "chore: update dependencies"),
        ]

        watermarked = _run_watermark_sweep(tasks_file, commits=commits, project_dir=tmp_path)

        assert len(watermarked) == 0, "Genuinely pending task must not be false-marked"

        tasks = _read_tasks(tasks_file)
        task = next(t for t in tasks if t["id"] == "task-genuinely-pending-001")
        assert task["status"] == "pending"

    def test_mode_b_terminal_tasks_not_affected(self, tmp_path):
        """completed/failed/cancelled tasks must never be touched by watermark sweep."""
        tasks_file = _make_tasks_file(
            tmp_path,
            [
                {
                    "id": "task-already-done-001",
                    "status": "completed",
                    "description": "Fix claim gate false positives",
                    "launchedAt": _now_iso(-7200),
                    "started_at": _now_iso(-7200),
                    "pid": None,
                    "completedAt": _now_iso(-3600),
                    "outputSummary": "done",
                    "expectedOutputs": [],
                    "checkCommand": None,
                },
                {
                    "id": "task-already-cancelled-001",
                    "status": "cancelled-stale",
                    "description": "Fix claim gate false positives",
                    "launchedAt": _now_iso(-7200),
                    "started_at": _now_iso(-7200),
                    "pid": None,
                    "completedAt": _now_iso(-3600),
                    "outputSummary": "stale",
                    "expectedOutputs": [],
                    "checkCommand": None,
                },
            ],
        )

        commits = [("f4e4ddd1abc", "fix: suppress claim gate false positives")]

        watermarked = _run_watermark_sweep(tasks_file, commits=commits, project_dir=tmp_path)

        assert len(watermarked) == 0, "Terminal tasks must not be re-processed"

        tasks = _read_tasks(tasks_file)
        assert tasks[0]["status"] == "completed"
        assert tasks[1]["status"] == "cancelled-stale"


# ---------------------------------------------------------------------------
# Tokenizer unit tests
# ---------------------------------------------------------------------------


class TestTokenizer:
    def test_removes_stopwords(self):
        tokens = _tokenize("fix the bug with this feature")
        assert "the" not in tokens
        assert "with" not in tokens
        assert "this" not in tokens

    def test_minimum_length_filter(self):
        tokens = _tokenize("fix bug add run the feature")
        for t in tokens:
            assert len(t) >= _MIN_TOKEN_LEN, f"Token {t!r} is shorter than minimum"

    def test_real_example(self):
        task_tokens = _tokenize("Fix claim gate false positives")
        commit_tokens = _tokenize("fix: suppress prose claim gate false positives")
        overlap = task_tokens & commit_tokens
        assert len(overlap) >= _WATERMARK_THRESHOLD, (
            f"Expected >={_WATERMARK_THRESHOLD} overlap tokens, got {overlap}"
        )


# ---------------------------------------------------------------------------
# Real-data smoke test
# ---------------------------------------------------------------------------


class TestRealDataSmoke:
    """Smoke test against a read-only copy of the real active-tasks.json.

    The target task 'task-1777745639' may already be in a terminal state
    (cancelled-stale, cancelled-zombie, or completed-by-watermark) because the
    zombie sweep runs before the watermark sweep in production.  This test
    accepts any terminal state as "the task is no longer blocking the panel".

    If the task IS still pending/in_progress, it must be matched by Mode B
    against the real git log (commit f4e4ddd1 is already in HEAD).
    """

    REAL_TASKS_FILE = (
        PROJECT_ROOT / ".cognitive-os" / "tasks" / "active-tasks.json"
    )
    TARGET_ID_PREFIX = "task-1777745639"

    def test_target_task_handled(self, tmp_path):
        if not self.REAL_TASKS_FILE.is_file():
            pytest.skip("active-tasks.json not present in this environment")

        real_data = json.loads(self.REAL_TASKS_FILE.read_text())
        tasks = real_data.get("tasks", [])

        target = next(
            (t for t in tasks if self.TARGET_ID_PREFIX in t.get("id", "")), None
        )
        if target is None:
            pytest.skip(f"Task with prefix {self.TARGET_ID_PREFIX} not found")

        status = target.get("status")
        terminal_states = {
            "completed", "completed-by-watermark", "failed",
            "cancelled-stale", "cancelled-zombie", "cancelled-dequeued",
        }
        if status in terminal_states:
            # Already handled -- pass.
            return

        # Task is still pending/in_progress. Run watermark sweep on a copy.
        copy_dir = tmp_path / ".cognitive-os" / "tasks"
        copy_dir.mkdir(parents=True)
        copy_file = copy_dir / "active-tasks.json"
        copy_file.write_text(json.dumps(real_data))

        since_ts = target.get("requested_at") or target.get("launchedAt") or "2026-05-01T00:00:00Z"
        try:
            result = subprocess.run(
                ["git", "log", "--format=%H\x1f%s", f"--since={since_ts}"],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(PROJECT_ROOT),
            )
            commits = []
            for line in result.stdout.splitlines():
                if "\x1f" in line:
                    sha, subj = line.split("\x1f", 1)
                    commits.append((sha.strip(), subj.strip()))
        except Exception:
            commits = []

        watermarked = _run_watermark_sweep(
            copy_file, commits=commits, project_dir=tmp_path
        )

        task_ids = [tid for tid, _ in watermarked]
        assert any(self.TARGET_ID_PREFIX in tid for tid in task_ids), (
            f"Expected {self.TARGET_ID_PREFIX} to be watermark-matched. "
            f"Commits checked: {[s for _, s in commits[:5]]}. "
            f"Task description: {target.get('description')!r}"
        )

        for tid, evidence in watermarked:
            if self.TARGET_ID_PREFIX in tid:
                assert evidence.get("mode") == "B", "Expected Mode B match"
                sha = evidence.get("commit_sha", "")
                assert sha.startswith("f4e4ddd1"), (
                    f"Expected commit f4e4ddd1..., got {sha!r}"
                )
                break

    def test_reaper_script_exits_zero_and_prints_watermark_line(self):
        """so-reaper.sh must exit 0 and print the watermark-sweep summary line."""
        reaper = PROJECT_ROOT / "scripts" / "so-reaper.sh"
        if not reaper.is_file():
            pytest.skip("so-reaper.sh not found")

        env = os.environ.copy()
        env["COGNITIVE_OS_PROJECT_DIR"] = str(PROJECT_ROOT)

        result = subprocess.run(
            ["bash", str(reaper)],
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
            cwd=str(PROJECT_ROOT),
        )

        assert result.returncode == 0, (
            f"so-reaper.sh exited {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        combined = result.stdout + result.stderr
        assert "[so-reaper] watermark-sweep:" in combined, (
            f"Expected '[so-reaper] watermark-sweep:' in output.\nGot: {combined[:500]}"
        )
