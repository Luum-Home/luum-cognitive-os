# SCOPE: both
"""Behavioural test for the rate-limit pre-check hook.

Audited on 2026-08-19 as one of three registered hooks with no behaviour test.
Unlike the symlink guard, this one **cannot deny anything**: every path ends in
`exit 0`, by design and by its own header comment. The tests below pin that
incapacity as the contract instead of pretending there is a decision:

  * it never blocks — match, no match, no queue, malformed queue, empty stdin;
  * its single real side effect is the queue mutation: a queued command whose
    hash matches is removed, a command that does not match is left alone;
  * the value it computes (`RATE_LIMIT_RETRY_COUNT`) is `export`ed inside its own
    process and therefore reaches nobody. The harness runs each hook as a
    separate child; the sibling test below spawns one and shows the variable is
    absent. That is the hook's structural ceiling, not a bug in the test.

Falsification run (report of 2026-08-19): with ``COS_TEST_HOOK_SOURCE_DIR``
pointing at a copy whose queue lookup was neutered, the removal tests go red;
with a copy that exits 2 on a match, the never-blocks tests go red.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_REL = "hooks/rate-limit-precheck.sh"
HOOK_BASENAME = "rate-limit-precheck.sh"
QUEUE_REL = ".cognitive-os/rate-limit-queue.json"

sys.path.insert(0, str(REPO_ROOT))
from cos_lib.rate_limiter import RateLimitQueue  # noqa: E402

QUEUED_CMD = "pytest tests/unit -q"
OTHER_CMD = "ruff check ."


def _hook_source() -> Path:
    """Where to copy the hook from — overridable only for the falsification run."""
    override = os.environ.get("COS_TEST_HOOK_SOURCE_DIR")
    base = Path(override) if override else REPO_ROOT
    return base / HOOK_REL


def command_hash(command: str) -> str:
    """Same digest the hook computes with sha256sum/shasum: first 16 hex chars."""
    return hashlib.sha256(command.encode()).hexdigest()[:16]


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    repo = (tmp_path / "repo").resolve()
    (repo / "hooks").mkdir(parents=True)
    shutil.copy(_hook_source(), repo / HOOK_REL)
    (repo / HOOK_REL).chmod(0o755)
    shutil.copytree(REPO_ROOT / "hooks" / "_lib", repo / "hooks" / "_lib")
    # The hook puts its own root on sys.path to import cos_lib; give the copy a
    # real one instead of vendoring the library into the fixture.
    (repo / "cos_lib").symlink_to(REPO_ROOT / "cos_lib")
    (repo / ".cognitive-os").mkdir()
    return repo


def queue_for(repo: Path) -> RateLimitQueue:
    return RateLimitQueue(state_path=str(repo / QUEUE_REL))


def seed_queue(repo: Path, command: str, retry_count: int = 0) -> str:
    return queue_for(repo).enqueue(
        "bash_command",
        context={"command_hash": command_hash(command), "command": command},
        retry_count=retry_count,
    )


def hook_env(repo: Path) -> dict:
    env = dict(os.environ)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    env.pop("RATE_LIMIT_RETRY_COUNT", None)
    return env


def run_hook(repo: Path, command: str, tool: str = "Bash") -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_name": tool, "tool_input": {"command": command}})
    return subprocess.run(
        ["/bin/bash", str(repo / HOOK_REL)],
        input=payload,
        text=True,
        capture_output=True,
        env=hook_env(repo),
        cwd=str(repo),
        timeout=60,
    )


def queued_hashes(repo: Path) -> list[str]:
    return [(item.get("context") or {}).get("command_hash") for item in queue_for(repo).peek()]


# --- the side effect it really has -------------------------------------------


def test_matching_command_is_removed_from_the_queue(repo: Path) -> None:
    seed_queue(repo, QUEUED_CMD)
    assert command_hash(QUEUED_CMD) in queued_hashes(repo)

    result = run_hook(repo, QUEUED_CMD)

    assert result.returncode == 0, result.stderr
    assert command_hash(QUEUED_CMD) not in queued_hashes(repo), (
        "the queued retry survived — the hook did not consume it"
    )


def test_non_matching_command_leaves_the_queue_intact(repo: Path) -> None:
    seed_queue(repo, QUEUED_CMD)

    result = run_hook(repo, OTHER_CMD)

    assert result.returncode == 0, result.stderr
    assert command_hash(QUEUED_CMD) in queued_hashes(repo), (
        "an unrelated command drained somebody else's queued retry"
    )


def test_only_the_matching_entry_is_consumed(repo: Path) -> None:
    seed_queue(repo, QUEUED_CMD)
    seed_queue(repo, OTHER_CMD)

    run_hook(repo, QUEUED_CMD)

    remaining = queued_hashes(repo)
    assert command_hash(QUEUED_CMD) not in remaining
    assert command_hash(OTHER_CMD) in remaining


def test_non_bash_tool_does_not_touch_the_queue(repo: Path) -> None:
    seed_queue(repo, QUEUED_CMD)

    result = run_hook(repo, QUEUED_CMD, tool="Edit")

    assert result.returncode == 0, result.stderr
    assert command_hash(QUEUED_CMD) in queued_hashes(repo)


# --- what it cannot do -------------------------------------------------------


def test_never_blocks_on_a_match(repo: Path) -> None:
    seed_queue(repo, QUEUED_CMD)
    result = run_hook(repo, QUEUED_CMD)
    assert result.returncode == 0, f"a PreToolUse exit != 0 blocks the tool call: {result.stderr}"


def test_never_blocks_without_a_queue(repo: Path) -> None:
    result = run_hook(repo, QUEUED_CMD)
    assert result.returncode == 0, result.stderr


def test_never_blocks_on_a_corrupt_queue(repo: Path) -> None:
    (repo / ".cognitive-os" / "rate-limit-queue.jsonl").write_text(
        "{not json at all\n", encoding="utf-8"
    )
    result = run_hook(repo, QUEUED_CMD)
    assert result.returncode == 0, result.stderr


def test_never_blocks_on_empty_stdin(repo: Path) -> None:
    result = subprocess.run(
        ["/bin/bash", str(repo / HOOK_REL)],
        input="",
        text=True,
        capture_output=True,
        env=hook_env(repo),
        cwd=str(repo),
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


def test_retry_count_never_reaches_the_next_hook(repo: Path) -> None:
    """The export dies with the process — this is the hook's structural ceiling.

    rate-limiter.sh runs as a separate child of the harness, so nothing the
    pre-check exports can be read by it. If this ever starts failing, somebody
    gave the hook a real channel (stdout contract, state file) and the queue
    mutation is no longer its only effect.
    """
    seed_queue(repo, QUEUED_CMD, retry_count=1)

    result = run_hook(repo, QUEUED_CMD)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "", f"hook now writes to stdout: {result.stdout!r}"

    sibling = subprocess.run(
        ["/bin/bash", "-c", 'printf %s "${RATE_LIMIT_RETRY_COUNT:-unset}"'],
        text=True,
        capture_output=True,
        env=hook_env(repo),
        cwd=str(repo),
        timeout=30,
    )
    assert sibling.stdout == "unset"
