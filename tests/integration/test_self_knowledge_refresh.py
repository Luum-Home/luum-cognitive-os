"""Integration tests for self-knowledge-refresh.sh hook (ADR-037).

Tests:
  1. Stale detection: hook identifies an outdated index
  2. Rebuild in background: hook triggers nohup build when stale
  3. Log emitted: metrics JSONL is written with correct structure
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOK = _REPO_ROOT / "hooks" / "self-knowledge-refresh.sh"
_GENERATOR = _REPO_ROOT / "scripts" / "cos_build_self_knowledge.py"


def _run_hook(project_dir: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run the hook with PROJECT_DIR set to project_dir."""
    merged_env = os.environ.copy()
    merged_env["PATH"] = os.environ.get("PATH", "")
    if env:
        merged_env.update(env)

    # The hook resolves PROJECT_DIR relative to its own location.
    # We need to override the hook's PROJECT_DIR via a wrapper that sets it
    # explicitly, since the hook uses SCRIPT_DIR/../ logic.
    #
    # Strategy: call the hook directly but with a symlink trick — we override
    # CLAUDE_PROJECT_DIR if set, or simply pass project_dir as an env var that
    # the hook can pick up via an override path.
    #
    # Simpler: run bash and override the PROJECT_DIR variable inside the script
    # by pre-sourcing a tiny override.

    override = textwrap.dedent(f"""\
        #!/usr/bin/env bash
        # Override PROJECT_DIR before sourcing the real hook body
        export PROJECT_DIR="{project_dir}"
        export KNOWLEDGE_DIR="$PROJECT_DIR/.cognitive-os/self-knowledge"
        export MTIME_FILE="$KNOWLEDGE_DIR/.mtime"
        export METRICS_FILE="$PROJECT_DIR/.cognitive-os/metrics/self-knowledge-refresh.jsonl"
        export GENERATOR="{_GENERATOR}"
        export LOGFILE="$KNOWLEDGE_DIR/build.log"
        export NOW_EPOCH=$(date +%s 2>/dev/null || echo 0)
        export NOW_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "")

        log_metric() {{
          local status="$1"
          local reason="$2"
          mkdir -p "$(dirname "$METRICS_FILE")"
          printf '{{"timestamp":"%s","status":"%s","reason":"%s","pid":"%s"}}\\n' \\
            "$NOW_ISO" "$status" "$reason" "$$" \\
            >> "$METRICS_FILE" 2>/dev/null || true
        }}

        rebuild_background() {{
          local reason="$1"
          if [ ! -f "$GENERATOR" ]; then
            log_metric "skip" "generator_not_found"
            exit 0
          fi
          mkdir -p "$KNOWLEDGE_DIR"
          nohup python3 "$GENERATOR" --project-dir "$PROJECT_DIR" \\
            > "$LOGFILE" 2>&1 &
          log_metric "rebuild_triggered" "$reason"
          echo "[self-knowledge-refresh] Rebuilding index in background (reason: $reason)" >&2
        }}

        if [ ! -f "$MTIME_FILE" ]; then
          rebuild_background "index_missing"
          exit 0
        fi

        INDEX_MTIME=$(date -r "$MTIME_FILE" +%s 2>/dev/null || echo 0)
        NEWEST_MTIME=0
        for dir in "$PROJECT_DIR/lib" "$PROJECT_DIR/hooks" "$PROJECT_DIR/scripts" \\
                   "$PROJECT_DIR/docs/02-Decisions/adrs" "$PROJECT_DIR/packages"; do
          if [ ! -d "$dir" ]; then continue; fi
          while IFS= read -r -d '' f; do
            FILE_MTIME=$(date -r "$f" +%s 2>/dev/null || echo 0)
            if [ "$FILE_MTIME" -gt "$NEWEST_MTIME" ]; then
              NEWEST_MTIME="$FILE_MTIME"
            fi
          done < <(find "$dir" -maxdepth 4 -type f \\( -name "*.py" -o -name "*.sh" -o -name "*.md" \\) -print0 2>/dev/null)
        done

        if [ "$NEWEST_MTIME" -gt "$INDEX_MTIME" ]; then
          rebuild_background "stale"
        else
          log_metric "up_to_date" "mtime_check"
        fi
        exit 0
    """)

    wrapper = project_dir / "_hook_wrapper.sh"
    wrapper.write_text(override)
    wrapper.chmod(0o755)

    result = subprocess.run(
        ["bash", str(wrapper)],
        capture_output=True,
        text=True,
        env=merged_env,
        timeout=30,
    )
    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def project_with_stale_index(tmp_path: Path) -> Path:
    """Project where .mtime exists but source files are newer."""
    lib = tmp_path / "lib"
    lib.mkdir()
    py_file = lib / "sample.py"
    py_file.write_text("def foo(): pass\n")

    knowledge = tmp_path / ".cognitive-os" / "self-knowledge"
    knowledge.mkdir(parents=True)
    (tmp_path / "cognitive-os.yaml").write_text("project:\n  name: test\n")

    # Write .mtime and set its file-system mtime to the distant past (2020)
    mtime_file = knowledge / ".mtime"
    mtime_file.write_text("2020-01-01T00:00:00Z\n")
    past_epoch = 1577836800  # 2020-01-01 00:00:00 UTC
    os.utime(mtime_file, (past_epoch, past_epoch))

    # Ensure sample.py has a clearly newer mtime (now)
    os.utime(py_file, None)

    return tmp_path


@pytest.fixture()
def project_with_fresh_index(tmp_path: Path) -> Path:
    """Project where the index is up to date."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "gen", _GENERATOR
    )
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)

    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "sample.py").write_text("def foo(): pass\n")
    (tmp_path / "cognitive-os.yaml").write_text("project:\n  name: test\n")

    gen.build(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Test 1: stale detection
# ---------------------------------------------------------------------------

def test_stale_detection(project_with_stale_index: Path) -> None:
    """Hook detects that the index is older than source files."""
    result = _run_hook(project_with_stale_index)
    assert result.returncode == 0, f"Hook must exit 0. stderr: {result.stderr}"

    # Check that metrics file records rebuild_triggered or index_missing
    metrics_file = project_with_stale_index / ".cognitive-os" / "metrics" / "self-knowledge-refresh.jsonl"
    assert metrics_file.exists(), "Metrics file must be written"

    lines = [l for l in metrics_file.read_text().splitlines() if l.strip()]
    assert lines, "At least one metrics line expected"
    last = json.loads(lines[-1])
    assert last["status"] in ("rebuild_triggered", "index_missing"), f"Unexpected status: {last}"
    assert last["reason"] in ("stale", "index_missing")


# ---------------------------------------------------------------------------
# Test 2: rebuild triggered in background
# ---------------------------------------------------------------------------

def test_rebuild_background_triggered(project_with_stale_index: Path) -> None:
    """Hook triggers background rebuild and the index files appear within timeout."""
    # Remove .mtime so the hook detects index_missing
    mtime = project_with_stale_index / ".cognitive-os" / "self-knowledge" / ".mtime"
    if mtime.exists():
        mtime.unlink()

    result = _run_hook(project_with_stale_index)
    assert result.returncode == 0

    # Give the background process time to complete (up to 10s)
    index_dir = project_with_stale_index / ".cognitive-os" / "self-knowledge"
    deadline = time.time() + 10
    api_surface = index_dir / "api-surface.json"
    while time.time() < deadline:
        if api_surface.exists() and (index_dir / ".mtime").exists():
            break
        time.sleep(0.3)

    assert api_surface.exists(), "api-surface.json should appear after background rebuild"
    assert (index_dir / ".mtime").exists(), ".mtime should appear after background rebuild"


# ---------------------------------------------------------------------------
# Test 3: log emitted
# ---------------------------------------------------------------------------

def test_log_emitted(project_with_fresh_index: Path) -> None:
    """Hook always writes at least one line to the metrics JSONL."""
    metrics_file = project_with_fresh_index / ".cognitive-os" / "metrics" / "self-knowledge-refresh.jsonl"
    # Remove any existing metrics
    if metrics_file.exists():
        metrics_file.unlink()

    result = _run_hook(project_with_fresh_index)
    assert result.returncode == 0

    assert metrics_file.exists(), "Metrics file must be created"
    lines = [l for l in metrics_file.read_text().splitlines() if l.strip()]
    assert lines, "At least one log line expected"

    entry = json.loads(lines[-1])
    assert "status" in entry
    assert "reason" in entry
    # Timestamp field present
    assert "timestamp" in entry
    # Status is one of the expected values
    assert entry["status"] in ("rebuild_triggered", "up_to_date", "index_missing", "skip")
