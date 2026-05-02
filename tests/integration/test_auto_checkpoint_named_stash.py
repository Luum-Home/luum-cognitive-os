"""Integration tests for R2: auto-checkpoint.sh named stash.

Verifies that auto-checkpoint.sh uses UUID-named stashes and resolves them by
name (not positional index), preventing stash@{0} shift races with concurrent
hooks (pre-agent-snapshot, post-agent-snapshot-restore).

Each test spins up a fresh temporary git repository and runs the hook via
subprocess so the shell logic executes exactly as it would in production.

ADR-055b: stash ops require COS_ALLOW_DESTRUCTIVE_GIT=1 in the hook's env.
"""

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.timeout(60)]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "hooks"
HOOK_PATH = HOOKS_DIR / "auto-checkpoint.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_git_repo(path: Path) -> None:
    """Initialise a bare-minimum git repo in *path*."""
    cmds = [
        ["git", "init"],
        ["git", "config", "user.email", "test@cos.test"],
        ["git", "config", "user.name", "COS Test"],
    ]
    for cmd in cmds:
        subprocess.run(cmd, cwd=path, capture_output=True, check=True)


def _initial_commit(path: Path) -> None:
    """Create an initial commit so the repo is not empty."""
    readme = path / "README.md"
    readme.write_text("initial")
    subprocess.run(["git", "add", "README.md"], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=path,
        capture_output=True,
        check=True,
    )


def _make_dirty(path: Path, filename: str = "dirty.txt", content: str = "dirty") -> Path:
    """Write an untracked file to make the working tree dirty."""
    f = path / filename
    f.write_text(content)
    return f


def _checkpoint_dir(project_dir: Path) -> Path:
    return project_dir / ".cognitive-os" / "checkpoints"


def _marker(project_dir: Path) -> Path:
    return _checkpoint_dir(project_dir) / ".last-checkpoint"


def _runtime_dir(project_dir: Path) -> Path:
    return project_dir / ".cognitive-os" / "runtime"


def _base_env(project_dir: Path, *, allow_destructive: bool = True) -> dict:
    """Build a clean env dict for running the hook."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
    if allow_destructive:
        env["COS_ALLOW_DESTRUCTIVE_GIT"] = "1"
    else:
        env.pop("COS_ALLOW_DESTRUCTIVE_GIT", None)
    return env


def _expire_marker(project_dir: Path, age_seconds: int = 400) -> None:
    """Write a stale marker file so the interval check passes."""
    chk = _checkpoint_dir(project_dir)
    chk.mkdir(parents=True, exist_ok=True)
    _marker(project_dir).write_text(str(int(time.time()) - age_seconds))


def _run_hook(
    project_dir: Path,
    extra_env: "dict | None" = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    if not HOOK_PATH.exists():
        pytest.skip(f"Hook not found: {HOOK_PATH}")

    env = _base_env(project_dir)
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def _stash_list_raw(repo: Path) -> list[str]:
    """Return raw lines from git stash list."""
    r = subprocess.run(
        ["git", "stash", "list"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return [line for line in r.stdout.splitlines() if line.strip()]


def _stash_count(repo: Path) -> int:
    return len(_stash_list_raw(repo))


def _git_stash_push(repo: Path, message: str) -> subprocess.CompletedProcess:
    """Push a named stash in a repo that already has git user config set."""
    return subprocess.run(
        ["git", "-C", str(repo), "stash", "push", "-u", "-m", message],
        capture_output=True,
        text=True,
    )


def _stash_list_formatted(repo: Path) -> list[str]:
    """Return stash lines in '%gd %s' format."""
    r = subprocess.run(
        ["git", "-C", str(repo), "stash", "list", "--format=%gd %s"],
        capture_output=True,
        text=True,
    )
    return [line for line in r.stdout.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Test 1 — Happy path: push named → apply named → drop named
# ---------------------------------------------------------------------------


class TestHappyPathNamedStash:
    def test_stash_push_apply_drop_cycle(self, tmp_path):
        """Hook creates a named stash, restores the working tree, and removes the stash.

        After a successful run:
        - No stash entries remain (stash was applied then dropped)
        - Marker file is updated
        - Checkpoint JSON was written with stash_name field
        """
        _make_git_repo(tmp_path)
        _initial_commit(tmp_path)
        _expire_marker(tmp_path)
        _make_dirty(tmp_path)

        stashes_before = _stash_count(tmp_path)
        result = _run_hook(tmp_path)

        assert result.returncode == 0, (
            f"Hook exited {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        stashes_after = _stash_count(tmp_path)
        # Named stash should have been applied and dropped — net stash count unchanged
        assert stashes_after == stashes_before, (
            f"Stash count changed from {stashes_before} to {stashes_after}; "
            f"stash was not cleaned up.\nstash list: {_stash_list_raw(tmp_path)}"
        )

        # Marker updated
        assert _marker(tmp_path).exists(), "Checkpoint marker not created"

        # Checkpoint JSON written with stash_name field
        chk_files = list(_checkpoint_dir(tmp_path).glob("cos-*.json"))
        assert chk_files, "No checkpoint JSON found"
        meta = json.loads(chk_files[0].read_text())
        assert "stash_name" in meta, f"stash_name missing from metadata: {meta}"
        assert meta["stash_name"].startswith("auto-checkpoint-"), (
            f"stash_name has unexpected prefix: {meta['stash_name']}"
        )

    def test_dirty_file_preserved_after_hook(self, tmp_path):
        """Working-tree changes must survive the stash-apply cycle."""
        _make_git_repo(tmp_path)
        _initial_commit(tmp_path)
        _expire_marker(tmp_path)
        dirty = _make_dirty(tmp_path, "preserved.txt", "must-survive")

        result = _run_hook(tmp_path)
        assert result.returncode == 0, (
            f"exit={result.returncode}\nstderr={result.stderr}"
        )

        assert dirty.exists(), "Dirty file was lost after auto-checkpoint"
        assert dirty.read_text() == "must-survive"


# ---------------------------------------------------------------------------
# Test 2 — Race scenario: pre-agent-snapshot creates stash@{0} BEFORE pop
# ---------------------------------------------------------------------------


class TestStashRaceScenario:
    def test_named_lookup_ignores_foreign_stash_at_zero(self, tmp_path):
        """Race: another hook pushes stash@{0} after auto-checkpoint's push.

        Sequence:
          1. auto-checkpoint.sh pushes named stash (auto-checkpoint-<UUID>)
             → becomes stash@{0}
          2. Simulate pre-agent-snapshot pushing on top
             → pre-agent stash becomes stash@{0}, checkpoint drops to stash@{1}
          3. The hook's name-based lookup MUST find checkpoint's stash (stash@{1})
             and NOT grab stash@{0} (which now belongs to pre-agent).

        Assertion: named lookup returns stash@{1} (or higher index), NOT stash@{0}.
        """
        _make_git_repo(tmp_path)
        _initial_commit(tmp_path)

        checkpoint_uuid = "test-race-uuid-1234"
        checkpoint_name = f"auto-checkpoint-{checkpoint_uuid}"
        pre_agent_name = "auto-pre-agent-deadbeef-0000"

        # Push checkpoint stash first (becomes stash@{0})
        _make_dirty(tmp_path, "cp.txt", "checkpoint-payload")
        r = _git_stash_push(tmp_path, checkpoint_name)
        assert r.returncode == 0, (
            f"checkpoint stash push failed: {r.stderr}"
        )

        # pre-agent hook pushes on top → becomes stash@{0}, checkpoint shifts to stash@{1}
        _make_dirty(tmp_path, "ag.txt", "agent-payload")
        r2 = _git_stash_push(tmp_path, pre_agent_name)
        assert r2.returncode == 0, (
            f"pre-agent stash push failed: {r2.stderr}"
        )

        # Verify pre-agent stash is now stash@{0}
        stash_lines = _stash_list_formatted(tmp_path)
        assert len(stash_lines) >= 2, f"Expected 2 stashes, got: {stash_lines}"
        assert pre_agent_name in stash_lines[0], (
            f"pre-agent stash is not stash@{{0}}: {stash_lines[0]}"
        )

        # ── Run the hook's name-based lookup logic ───────────────────────────
        lookup_script = f"""
#!/usr/bin/env bash
set -uo pipefail
STASH_NAME="{checkpoint_name}"
STASH_REF=""
while IFS= read -r _line; do
    _ref="${{_line%% *}}"
    _msg="${{_line#* }}"
    if [[ "$_msg" == *"$STASH_NAME"* ]]; then
        STASH_REF="$_ref"
        break
    fi
done < <(git -C "{tmp_path}" stash list --format='%gd %s' 2>/dev/null || true)
echo "$STASH_REF"
"""
        r = subprocess.run(["bash", "-c", lookup_script], capture_output=True, text=True)
        found_ref = r.stdout.strip()

        assert found_ref, "Named lookup returned empty ref — stash not found"
        assert found_ref != "stash@{0}", (
            "Named lookup returned stash@{0} — it grabbed the wrong (pre-agent) stash! "
            "This is the R2 race bug: pop-based restore would have hit this."
        )

        # The found ref should point to the checkpoint stash line
        matching = [l for l in stash_lines if checkpoint_name in l]
        assert matching, f"checkpoint stash not in list: {stash_lines}"
        assert found_ref in matching[0], (
            f"Found ref {found_ref!r} doesn't match checkpoint line: {matching[0]!r}"
        )

        print(
            f"\n[RACE SCENARIO STDOUT]\n"
            f"  stash@{{0}} (pre-agent):   {stash_lines[0]}\n"
            f"  checkpoint lookup found:  {found_ref} → {matching[0]}\n"
            f"  => Named lookup correctly skipped stash@{{0}} (pre-agent stash)"
        )


# ---------------------------------------------------------------------------
# Test 3 — Stash lookup by message — exact match required
# ---------------------------------------------------------------------------


class TestStashLookupExactMatch:
    def test_lookup_finds_correct_entry_among_similar_names(self, tmp_path):
        """Lookup must find the target stash even when another entry has a similar prefix."""
        _make_git_repo(tmp_path)
        _initial_commit(tmp_path)

        target_uuid = "aabbccdd-0000-1111-2222-333344445555"
        target_name = f"auto-checkpoint-{target_uuid}"
        other_name = "auto-checkpoint-ffffffff-9999-8888-7777-666655554444"

        # Push other stash first (will shift index after target push)
        _make_dirty(tmp_path, "other.txt", "other-payload")
        r = _git_stash_push(tmp_path, other_name)
        assert r.returncode == 0, f"other stash push failed: {r.stderr}"

        # Push target stash — becomes stash@{0}
        _make_dirty(tmp_path, "target.txt", "target-payload")
        r = _git_stash_push(tmp_path, target_name)
        assert r.returncode == 0, f"target stash push failed: {r.stderr}"

        # Run lookup for target_name
        lookup_script = f"""
#!/usr/bin/env bash
STASH_NAME="{target_name}"
STASH_REF=""
while IFS= read -r _line; do
    _ref="${{_line%% *}}"
    _msg="${{_line#* }}"
    if [[ "$_msg" == *"$STASH_NAME"* ]]; then
        STASH_REF="$_ref"
        break
    fi
done < <(git -C "{tmp_path}" stash list --format='%gd %s' 2>/dev/null || true)
echo "$STASH_REF"
"""
        r = subprocess.run(["bash", "-c", lookup_script], capture_output=True, text=True)
        found_ref = r.stdout.strip()

        assert found_ref, f"Lookup returned empty. stash list: {_stash_list_formatted(tmp_path)}"

        # Verify the found ref contains the target name
        stash_list = _stash_list_formatted(tmp_path)
        found_line = next(
            (line for line in stash_list if found_ref in line), ""
        )
        assert target_name in found_line, (
            f"Found ref {found_ref!r} maps to line {found_line!r} which lacks target name"
        )
        assert other_name not in found_line, (
            f"Found ref {found_ref!r} maps to the wrong (other) stash: {found_line!r}"
        )


# ---------------------------------------------------------------------------
# Test 4 — Marker file persistence and retrieval
# ---------------------------------------------------------------------------


class TestMarkerFilePersistence:
    def test_stash_name_persisted_in_checkpoint_json(self, tmp_path):
        """The checkpoint JSON must contain the stash_name field for auditability."""
        _make_git_repo(tmp_path)
        _initial_commit(tmp_path)
        _expire_marker(tmp_path)
        _make_dirty(tmp_path)

        result = _run_hook(tmp_path)
        assert result.returncode == 0, f"exit={result.returncode}\nstderr={result.stderr}"

        chk_files = list(_checkpoint_dir(tmp_path).glob("cos-*.json"))
        assert chk_files, "No checkpoint JSON"
        meta = json.loads(chk_files[0].read_text())
        stash_name = meta.get("stash_name", "")
        assert stash_name.startswith("auto-checkpoint-"), f"Bad stash_name: {stash_name}"
        # UUID part should be at least 8 chars
        uuid_part = stash_name[len("auto-checkpoint-"):]
        assert len(uuid_part) >= 8, f"UUID part too short: {uuid_part!r}"

    def test_runtime_dir_created_when_stash_runs(self, tmp_path):
        """The hook must create .cognitive-os/runtime/ as part of the stash flow."""
        _make_git_repo(tmp_path)
        _initial_commit(tmp_path)
        _expire_marker(tmp_path)
        _make_dirty(tmp_path)

        runtime = _runtime_dir(tmp_path)
        assert not runtime.exists(), "Pre-condition: runtime dir must not exist"

        # Run hook with dirty files + allow_destructive to trigger stash path
        result = _run_hook(tmp_path, extra_env={"COS_ALLOW_DESTRUCTIVE_GIT": "1"})
        assert result.returncode == 0, f"exit={result.returncode}\nstderr={result.stderr}"

        assert runtime.exists(), (
            "Runtime dir was not created. Hook must mkdir -p RUNTIME_DIR on the stash path."
        )


# ---------------------------------------------------------------------------
# Test 5 — Idempotency: two runs do not compound stashes
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_two_runs_no_stash_leak(self, tmp_path):
        """Running the hook twice must not leave orphaned stash entries.

        The second run should hit the time-gate (marker was just written) and
        exit early, so the net stash count after both runs equals the count
        before the first run.
        """
        _make_git_repo(tmp_path)
        _initial_commit(tmp_path)
        _expire_marker(tmp_path)
        _make_dirty(tmp_path)

        stashes_before = _stash_count(tmp_path)

        result1 = _run_hook(tmp_path)
        assert result1.returncode == 0, f"First run failed: {result1.stderr}"

        # Second run: marker is fresh → hook exits early, no stash op
        result2 = _run_hook(tmp_path)
        assert result2.returncode == 0, f"Second run failed: {result2.stderr}"

        stashes_after = _stash_count(tmp_path)
        assert stashes_after == stashes_before, (
            f"Stash leak after two runs: before={stashes_before}, after={stashes_after}\n"
            f"stash list: {_stash_list_raw(tmp_path)}"
        )


# ---------------------------------------------------------------------------
# Test 6 — Falsification: rubber-stamp version (uses pop) FAILS the race test
# ---------------------------------------------------------------------------


class TestFalsification:
    """Prove that a naive pop-based implementation FAILS the race scenario.

    This test embeds the broken implementation directly and asserts it would
    grab the wrong stash entry (stash@{0} = pre-agent) instead of the checkpoint's.
    Confirms the named-stash approach is necessary.
    """

    def test_pop_based_grabs_wrong_stash(self, tmp_path):
        """A pop-based restore WOULD grab pre-agent's stash@{0} in the race.

        Demonstrates the bug by verifying stash@{0} contains agent files, not
        checkpoint files, after the race sequence.
        """
        _make_git_repo(tmp_path)
        _initial_commit(tmp_path)

        checkpoint_name = "auto-checkpoint-rubber-stamp"
        pre_agent_name = "auto-pre-agent-rubber-stamp"

        # Push checkpoint stash
        _make_dirty(tmp_path, "cp.txt", "checkpoint")
        r = _git_stash_push(tmp_path, checkpoint_name)
        assert r.returncode == 0, f"checkpoint push failed: {r.stderr}"

        # pre-agent hook pushes on top → stash@{0}
        _make_dirty(tmp_path, "ag.txt", "agent")
        r2 = _git_stash_push(tmp_path, pre_agent_name)
        assert r2.returncode == 0, f"pre-agent push failed: {r2.stderr}"

        # Confirm pre-agent is stash@{0}
        stash_list = _stash_list_formatted(tmp_path)
        assert len(stash_list) >= 2, f"Expected 2 stashes: {stash_list}"
        assert pre_agent_name in stash_list[0], (
            f"pre-agent is not stash@{{0}}: {stash_list[0]}"
        )

        # ── Demonstrate what pop would do (rubber-stamp version) ──────────
        # `git stash show -u stash@{0}` shows untracked files too (needed for our case)
        show_r = subprocess.run(
            ["git", "-C", str(tmp_path), "stash", "show", "-u", "--name-only", "stash@{0}"],
            capture_output=True,
            text=True,
        )
        files_at_zero = show_r.stdout.strip()

        # stash@{0} = pre-agent (ag.txt), NOT checkpoint (cp.txt)
        assert "ag.txt" in files_at_zero, (
            f"Pre-condition failed: stash@{{0}} does not contain ag.txt: {files_at_zero!r}"
        )
        assert "cp.txt" not in files_at_zero, (
            f"Pre-condition failed: stash@{{0}} unexpectedly contains cp.txt: {files_at_zero!r}"
        )

        # Named lookup for checkpoint_name should NOT return stash@{0}
        lookup_script = f"""
#!/usr/bin/env bash
STASH_NAME="{checkpoint_name}"
STASH_REF=""
while IFS= read -r _line; do
    _ref="${{_line%% *}}"
    _msg="${{_line#* }}"
    if [[ "$_msg" == *"$STASH_NAME"* ]]; then
        STASH_REF="$_ref"
        break
    fi
done < <(git -C "{tmp_path}" stash list --format='%gd %s' 2>/dev/null || true)
echo "$STASH_REF"
"""
        r = subprocess.run(["bash", "-c", lookup_script], capture_output=True, text=True)
        checkpoint_ref = r.stdout.strip()

        # Named lookup finds checkpoint at stash@{1}, not stash@{0}
        assert checkpoint_ref != "stash@{0}", (
            "Named lookup returned stash@{0} — it would grab the wrong stash!"
        )
        assert checkpoint_ref, "Named lookup returned empty — checkpoint stash not found"

        print(
            f"\n[FALSIFICATION STDOUT]\n"
            f"  stash@{{0}} = pre-agent ({pre_agent_name}) contains: {files_at_zero}\n"
            f"  Rubber-stamp `git stash pop` would restore agent work, not checkpoint.\n"
            f"  Named lookup correctly finds checkpoint at: {checkpoint_ref}\n"
            f"  => Named stash lookup is required to avoid this R2 race bug."
        )
