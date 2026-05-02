"""
Portability proofs for lib/queue_rebase — P2.2 (ADR-116).

3 proofs:
1. Works with any writable tmp repo path (no .cognitive-os anchor needed)
2. RebaseResult is a plain dataclass (pickleable, no hidden state)
3. Module imports cleanly with no side effects (no git operations at import time)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
    )


def _setup_minimal_repo(repo_dir: Path) -> None:
    _git(["init", "-b", "main"], repo_dir)
    _git(["config", "user.email", "port@cos.test"], repo_dir)
    _git(["config", "user.name", "COS Port"], repo_dir)
    (repo_dir / "seed.txt").write_text("seed\n")
    _git(["add", "seed.txt"], repo_dir)
    _git(["commit", "-m", "chore: seed"], repo_dir)


# ---------------------------------------------------------------------------
# Proof 1: arbitrary repo path, no .cognitive-os anchor
# ---------------------------------------------------------------------------


class TestArbitraryRepoPath:
    """queue_rebase works with any git repo path — no project-root dependency."""

    def test_is_ff_possible_arbitrary_path(self, tmp_path):
        """is_ff_possible works with a totally arbitrary tmp git repo."""
        from lib.queue_rebase import is_ff_possible  # noqa: PLC0415

        _setup_minimal_repo(tmp_path)
        # Branch is at same tip as main — ff IS possible.
        _git(["checkout", "-b", "session/arb"], tmp_path)
        (tmp_path / "arb.txt").write_text("arb\n")
        _git(["add", "arb.txt"], tmp_path)
        _git(["commit", "-m", "feat: arb"], tmp_path)
        _git(["checkout", "main"], tmp_path)

        result = is_ff_possible("session/arb", "main", tmp_path)
        assert result is True

    def test_rebase_onto_arbitrary_path(self, tmp_path):
        """rebase_onto works with an arbitrary tmp git repo."""
        from lib.queue_rebase import rebase_onto  # noqa: PLC0415

        _setup_minimal_repo(tmp_path)

        _git(["checkout", "-b", "session/arb-rebase"], tmp_path)
        (tmp_path / "session_arb.txt").write_text("session\n")
        _git(["add", "session_arb.txt"], tmp_path)
        _git(["commit", "-m", "feat: session"], tmp_path)
        _git(["checkout", "main"], tmp_path)

        (tmp_path / "main_arb.txt").write_text("main\n")
        _git(["add", "main_arb.txt"], tmp_path)
        _git(["commit", "-m", "feat: main advance"], tmp_path)

        result = rebase_onto("session/arb-rebase", "main", tmp_path)
        assert result.success is True


# ---------------------------------------------------------------------------
# Proof 2: RebaseResult is a plain pickleable dataclass
# ---------------------------------------------------------------------------


class TestRebaseResultPortability:
    """RebaseResult carries no hidden state and is safely pickleable."""

    def test_rebase_result_is_pickleable(self, tmp_path):
        """RebaseResult can round-trip through pickle (cross-process safe)."""
        import pickle  # noqa: PLC0415
        from lib.queue_rebase import RebaseResult  # noqa: PLC0415

        r = RebaseResult(
            success=True,
            new_sha="abc123def456",
            conflicts=[],
            aborted=False,
            evidence={"repo_root": str(tmp_path), "dry_run": False},
        )
        serialised = pickle.dumps(r)
        recovered = pickle.loads(serialised)

        assert recovered.success == r.success
        assert recovered.new_sha == r.new_sha
        assert recovered.conflicts == r.conflicts
        assert recovered.evidence == r.evidence

    def test_rebase_result_bool_semantics(self):
        """bool(RebaseResult) reflects the success field."""
        from lib.queue_rebase import RebaseResult  # noqa: PLC0415

        assert bool(RebaseResult(success=True)) is True
        assert bool(RebaseResult(success=False)) is False


# ---------------------------------------------------------------------------
# Proof 3: import has no side effects
# ---------------------------------------------------------------------------


class TestImportNoSideEffects:
    """Importing queue_rebase does not spawn processes or touch disk."""

    def test_import_does_not_execute_git(self, tmp_path, monkeypatch):
        """Importing the module does not run git commands."""
        # Record all subprocess.run calls during import.
        calls: list = []
        original_run = subprocess.run

        def spy_run(*args, **kwargs):
            calls.append(args)
            return original_run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", spy_run)

        # Force re-import by removing from sys.modules.
        import importlib  # noqa: PLC0415
        mod_key = next((k for k in sys.modules if "queue_rebase" in k), None)
        if mod_key:
            del sys.modules[mod_key]

        importlib.import_module("lib.queue_rebase")

        assert len(calls) == 0, (
            f"Import should not call subprocess.run, but got: {calls}"
        )
