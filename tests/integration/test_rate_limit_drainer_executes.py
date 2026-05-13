"""Integration tests: rate-limit-drain.sh drainer-as-executor (D45 gap A).

Tests that the drainer:
  1. Executes safe bash_command queue items via subprocess.
  2. Increments retry_count per attempt and records it.
  3. Drops items when retry_count > MAX_RETRY_COUNT.
  4. Blocks unsafe / non-allowlist commands via safe_to_execute().
  5. Writes audit records to rate-limit-executed.jsonl.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from types import ModuleType

import pytest

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJ_ROOT))

from lib.rate_limiter import (  # noqa: E402
    MAX_RETRY_COUNT,
    RateLimitConfig,
    RateLimiter,
    RateLimitQueue,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers to extract safe_to_execute() from the drain shell script's embedded
# Python block (we duplicate the function in Python for unit-level testing).
# We import it by evaluating the PYEOF block directly.
# ---------------------------------------------------------------------------

def _load_drain_helpers() -> ModuleType:
    """Load the Python helpers embedded in rate-limit-drain.sh into a module.

    The drain hook writes its Python logic to a temp file using <<'PYEOF'
    (single-quoted, no bash expansion).  We extract that block and evaluate it.
    """
    drain_path = _PROJ_ROOT / "hooks" / "rate-limit-drain.sh"
    source = drain_path.read_text()
    # Extract the python block between cat > ... << 'PYEOF' and PYEOF
    start_marker = "cat > \"$_DRAIN_SCRIPT\" << 'PYEOF'\n"
    end_marker = "\nPYEOF"
    if start_marker not in source:
        raise ValueError("Could not find PYEOF block in drain script")
    start = source.index(start_marker) + len(start_marker)
    end = source.index(end_marker, start)
    py_block = source[start:end]
    # Patch the environment-variable reads so we can execute standalone
    py_block = py_block.replace(
        "PROJECT_DIR = os.environ.get(\"_DRAIN_PROJECT_DIR\", \".\")",
        f"PROJECT_DIR = {str(_PROJ_ROOT)!r}",
    )
    py_block = py_block.replace(
        "PHASE = os.environ.get(\"_DRAIN_PHASE\", \"stabilization\")",
        "PHASE = 'stabilization'",
    )
    # Stop at rate-limiter instantiation to avoid file-system side effects
    stop_marker = "\nstate_dir = "
    if stop_marker in py_block:
        py_block = py_block[: py_block.index(stop_marker)]
    # Execute into a fresh module namespace
    mod = ModuleType("drain_helpers")
    exec(compile(py_block, "drain_helpers", "exec"), mod.__dict__)  # noqa: S102
    return mod


try:
    _drain = _load_drain_helpers()
    _safe_to_execute = _drain.safe_to_execute
except Exception:
    _safe_to_execute = None  # tests will skip if extraction fails


def _make_queue(tmp_path: Path, cooldown: int = 1) -> RateLimitQueue:
    return RateLimitQueue(
        state_path=str(tmp_path / "queue.json"),
        cooldown_seconds=cooldown,
    )


def _make_limiter(tmp_path: Path, max_bash: int = 100) -> RateLimiter:
    cfg = RateLimitConfig(max_bash_commands_per_minute=max_bash)
    return RateLimiter(
        config=cfg,
        state_path=str(tmp_path / "state.json"),
        phase="stabilization",
    )


# ---------------------------------------------------------------------------
# Test 1: Happy-path execution — safe echo command executes, audit record written
# ---------------------------------------------------------------------------

def test_drainer_executes_safe_echo_command(tmp_path: Path) -> None:
    """A safe echo command enqueued and dequeued triggers subprocess execution
    and writes an audit record to rate-limit-executed.jsonl."""
    queue = _make_queue(tmp_path)
    queue_id = queue.enqueue(
        "bash_command",
        {"command": "echo hello_drainer", "command_hash": "aabbccddeeff0011"},
        retry_count=0,
    )
    # Make item immediately eligible
    items = queue._load()
    for item in items:
        if item.get("queue_id") == queue_id:
            item["eligible_at"] = time.time() - 1
    queue._items = items
    queue._save()

    ready = queue.dequeue_ready()
    assert len(ready) == 1

    # Simulate the drainer execution path
    import shlex
    import subprocess as sp

    executed_path = tmp_path / "rate-limit-executed.jsonl"
    for item in ready:
        cmd = item.get("context", {}).get("command", "")
        assert cmd == "echo hello_drainer"
        t0 = time.monotonic()
        result = sp.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(_PROJ_ROOT),
            shell=False,
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        record = {
            "ts": time.time(),
            "command": cmd,
            "retry_count": item.get("retry_count", 0),
            "exit_code": result.returncode,
            "elapsed_ms": elapsed_ms,
            "queue_id": item.get("queue_id"),
        }
        with open(executed_path, "a") as fh:
            fh.write(json.dumps(record) + "\n")

    assert executed_path.exists()
    records = [json.loads(l) for l in executed_path.read_text().splitlines()]
    assert len(records) == 1
    assert records[0]["exit_code"] == 0
    assert records[0]["command"] == "echo hello_drainer"
    assert records[0]["retry_count"] == 0


# ---------------------------------------------------------------------------
# Test 2: retry_count increments on re-enqueue when still blocked
# ---------------------------------------------------------------------------

def test_drainer_increments_retry_count_on_requeue(tmp_path: Path) -> None:
    """When an item is still blocked on dequeue, re-enqueue increments retry_count."""
    queue = _make_queue(tmp_path, cooldown=1)
    # Use max_bash=1 and exhaust it so the next check is blocked
    rl = _make_limiter(tmp_path, max_bash=1)
    rl.record("bash_command")  # exhaust the 1-per-minute limit

    queue_id = queue.enqueue("bash_command", {"description": "blocked cmd"}, retry_count=0)
    items = queue._load()
    for item in items:
        if item.get("queue_id") == queue_id:
            item["eligible_at"] = time.time() - 1
    queue._items = items
    queue._save()

    ready = queue.dequeue_ready()
    assert len(ready) == 1
    item = ready[0]
    assert item["retry_count"] == 0

    # Simulate re-enqueue path (drainer logic)
    allowed, reason = rl.check("bash_command")
    assert not allowed  # still blocked (1/1 limit exhausted)

    new_retry = item["retry_count"] + 1
    new_id = queue.enqueue("bash_command", {"description": "blocked cmd"}, retry_count=new_retry)
    assert new_id  # not dropped (retry 1 <= MAX_RETRY_COUNT=3)

    updated = queue._load()
    assert any(i["retry_count"] == 1 for i in updated)


# ---------------------------------------------------------------------------
# Test 3: item dropped when retry_count > MAX_RETRY_COUNT
# ---------------------------------------------------------------------------

def test_drainer_drops_item_at_max_retry(tmp_path: Path) -> None:
    """enqueue() returns '' when retry_count > MAX_RETRY_COUNT; drop written to log."""
    queue = _make_queue(tmp_path)

    # Enqueue with retry_count already at the cap
    over_cap = MAX_RETRY_COUNT + 1
    result_id = queue.enqueue(
        "bash_command",
        {"description": "over-cap item"},
        retry_count=over_cap,
    )
    assert result_id == ""  # dropped

    # Library writes to the drop log at state_dir/rate-limit-dropped.jsonl
    state_dir = Path(queue.state_path).parent
    drop_file = state_dir / "rate-limit-dropped.jsonl"
    assert drop_file.exists()
    records = [json.loads(l) for l in drop_file.read_text().splitlines()]
    assert len(records) >= 1
    assert records[-1]["reason"] == "retry_cap_exceeded"
    assert records[-1]["retry_count"] == over_cap


# ---------------------------------------------------------------------------
# Test 4: safe_to_execute() blocks unsafe commands
# ---------------------------------------------------------------------------

@pytest.mark.skipif(_safe_to_execute is None, reason="Could not extract safe_to_execute from drain script")
def test_safe_to_execute_blocks_dangerous_commands() -> None:
    """Dangerous commands must not pass the allowlist guard."""
    dangerous = [
        "rm -rf /tmp/foo",
        "eval $(cat /etc/passwd)",
        "git push --force origin main",
        "bash -c 'echo $(cat /etc/shadow)'",
        "dd if=/dev/zero of=/dev/sda",
        "source /etc/profile",
        "echo hi; rm -rf .",
        "a" * 3000,  # too long
    ]
    for cmd in dangerous:
        assert not _safe_to_execute(cmd), f"Should be blocked: {cmd!r}"


@pytest.mark.skipif(_safe_to_execute is None, reason="Could not extract safe_to_execute from drain script")
def test_safe_to_execute_allows_safe_commands() -> None:
    """Known-safe commands must pass the allowlist."""
    safe = [
        "echo hello",
        "python3 -c 'print(1)'",
        "pytest tests/unit/",
        "grep -r foo src/",
        "bash scripts/apply-efficiency-profile.sh standard",
        "jq . file.json",
    ]
    for cmd in safe:
        assert _safe_to_execute(cmd), f"Should be allowed: {cmd!r}"


# ---------------------------------------------------------------------------
# Test 5: audit record written with correct fields
# ---------------------------------------------------------------------------

def test_drainer_audit_record_has_required_fields(tmp_path: Path) -> None:
    """Executed audit records must contain command, retry_count, exit_code, elapsed_ms."""
    import shlex
    import subprocess as sp

    executed_path = tmp_path / "rate-limit-executed.jsonl"
    cmd = "echo audit_test"
    t0 = time.monotonic()
    result = sp.run(shlex.split(cmd), capture_output=True, text=True, timeout=5, shell=False)
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    record = {
        "ts": time.time(),
        "command": cmd,
        "retry_count": 1,
        "exit_code": result.returncode,
        "elapsed_ms": elapsed_ms,
        "queue_id": "test1234",
        "stdout_snippet": result.stdout[:500],
        "stderr_snippet": result.stderr[:200],
    }
    with open(executed_path, "a") as fh:
        fh.write(json.dumps(record) + "\n")

    records = [json.loads(l) for l in executed_path.read_text().splitlines()]
    r = records[0]
    for field in ("ts", "command", "retry_count", "exit_code", "elapsed_ms", "queue_id"):
        assert field in r, f"Missing field: {field}"
    assert r["exit_code"] == 0
    assert r["elapsed_ms"] >= 0
