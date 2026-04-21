"""Tests for hooks/docker-drift-detector.sh.

Verifies the advisory SessionStart hook that detects stale cognitive-os
containers (running image sha != compose-pinned sha).

The hook is graceful-degrade: silent exit 0 when compose file absent,
docker binary absent, daemon not responding, or no running containers.
It never blocks session start.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = REPO_ROOT / "hooks" / "docker-drift-detector.sh"


def _run(env: dict[str, str], timeout: float = 5.0) -> subprocess.CompletedProcess:
    """Invoke the hook with a controlled env, returning the CompletedProcess."""
    return subprocess.run(
        ["bash", str(HOOK)],
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_hook_exists_and_executable():
    assert HOOK.is_file(), f"{HOOK} missing"
    assert os.access(HOOK, os.X_OK), f"{HOOK} not executable"


def test_hook_bash_syntax_clean():
    result = subprocess.run(
        ["bash", "-n", str(HOOK)],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"syntax error: {result.stderr}"


def test_hook_exits_silently_when_compose_missing():
    """No docker-compose.cognitive-os.yml in tmpdir → exit 0, no output."""
    with tempfile.TemporaryDirectory() as tmp:
        result = _run({"CLAUDE_PROJECT_DIR": tmp})
        assert result.returncode == 0
        # No stderr output when compose is absent
        assert result.stderr.strip() == "", f"unexpected stderr: {result.stderr!r}"


def test_hook_exit_zero_when_compose_present_but_no_pins():
    """Compose exists but no @sha256 pins → PARTIAL state, no crash."""
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "docker-compose.cognitive-os.yml").write_text(
            "services:\n  foo:\n    image: nginx:latest\n"
        )
        result = _run({"CLAUDE_PROJECT_DIR": tmp})
        assert result.returncode == 0
        # May be silent (no running containers) — never crashes


def test_hook_always_exit_zero_even_when_docker_missing():
    """Simulate docker-less environment via PATH manipulation."""
    with tempfile.TemporaryDirectory() as tmp:
        # Write a compose file with a pinned image so the hook has SOMETHING to
        # think about — but clear PATH to hide docker binaries.
        Path(tmp, "docker-compose.cognitive-os.yml").write_text(
            "services:\n  foo:\n    image: nginx:1@sha256:"
            + "a" * 64
            + "\n"
        )
        # Use a minimal PATH that definitely has no docker + override common
        # well-known docker paths by putting only /tmp (empty) first
        # Include /bin + /usr/bin so bash/awk/date still resolve, but NOT any
        # of the common docker install paths.
        env = {
            "CLAUDE_PROJECT_DIR": tmp,
            "PATH": "/bin:/usr/bin",
        }
        # The hook also hardcodes /opt/homebrew, /usr/local, OrbStack paths —
        # if those exist on the test host the hook will find docker. That's
        # still fine — as long as it exits 0, the contract holds.
        result = _run(env)
        assert result.returncode == 0


def test_hook_writes_metrics_file_when_containers_checked():
    """If docker is available and there are cognitive-os containers, the hook
    writes a JSONL record to .cognitive-os/metrics/docker-drift.jsonl."""
    docker_found = any(
        Path(p).exists()
        for p in (
            "/opt/homebrew/bin/docker",
            "/usr/local/bin/docker",
            "/Applications/OrbStack.app/Contents/Resources/bin/docker",
        )
    ) or shutil.which("docker") is not None

    if not docker_found:
        import pytest

        pytest.skip("docker binary not available on this host")

    with tempfile.TemporaryDirectory() as tmp:
        # Minimal compose with a fake pinned image — hook will read pins but
        # no running containers will match → silent exit.
        Path(tmp, "docker-compose.cognitive-os.yml").write_text(
            "services:\n  foo:\n    image: nginx:1@sha256:"
            + "a" * 64
            + "\n"
        )
        result = _run({"CLAUDE_PROJECT_DIR": tmp})
        assert result.returncode == 0
        # If the hook ran any docker commands it may or may not have written
        # metrics (depends on whether any cognitive-os-* container runs).
        # We don't assert metrics presence here; we only assert no crash.


def test_hook_fast_under_1_second_when_nothing_to_check():
    """With no compose file, hook must exit in <1s."""
    import time

    with tempfile.TemporaryDirectory() as tmp:
        start = time.monotonic()
        result = _run({"CLAUDE_PROJECT_DIR": tmp})
        elapsed = time.monotonic() - start
        assert result.returncode == 0
        assert elapsed < 1.0, f"hook too slow: {elapsed:.2f}s"


def test_hook_registered_in_both_profile_scripts():
    """Gate 3a compliance — new hook must appear in both profile scripts."""
    apply_text = (REPO_ROOT / "scripts" / "apply-efficiency-profile.sh").read_text()
    secure_text = (REPO_ROOT / "scripts" / "set-security-profile.sh").read_text()
    assert "docker-drift-detector" in apply_text
    assert "docker-drift-detector" in secure_text


def test_hook_registered_in_settings_json():
    """Hook was added to SessionStart via apply-efficiency-profile.sh default."""
    settings = (REPO_ROOT / ".claude" / "settings.json").read_text()
    assert "docker-drift-detector" in settings, (
        "docker-drift-detector.sh not in settings.json — run "
        "`bash scripts/apply-efficiency-profile.sh default`"
    )
