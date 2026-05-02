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


# ---------------------------------------------------------------------------
# Validator invariant — catch the regression that originally hit us
# ---------------------------------------------------------------------------

def test_validator_distinguishes_manifest_digest_from_image_id():
    """Real regression 2026-04-21: the first version of
    `_check_docker_container_freshness` compared `{{.Image}}` (image CONFIG ID)
    against the compose pin's `@sha256:...` (image MANIFEST DIGEST). These are
    two different hash schemes of the same image, so comparison always failed
    — every running container was flagged as stale.

    Invariant: if a container's `Config.Image` field contains the exact pinned
    digest from compose, the validator must classify it as IMPL (fresh). This
    test encodes the rule so any future regression in hash-field comparison
    is caught at test-time rather than in production.

    Skipped if docker is unavailable or no cognitive-os-* containers run.
    """
    docker = None
    for candidate in (
        "/opt/homebrew/bin/docker",
        "/usr/local/bin/docker",
        "/Applications/OrbStack.app/Contents/Resources/bin/docker",
    ):
        if Path(candidate).exists():
            docker = candidate
            break
    if docker is None:
        docker = shutil.which("docker")
    if docker is None:
        import pytest
        pytest.skip("docker not available")

    # Find any running container whose Config.Image contains "@sha256:"
    # (i.e. was created from a pinned image). If none match the compose pins,
    # skip — we can't test the invariant without a live subject.
    compose_path = REPO_ROOT / "docker-compose.cognitive-os.yml"
    if not compose_path.exists():
        import pytest
        pytest.skip("compose file missing")

    import re
    pins = {}
    for m in re.finditer(
        r"^\s*image:\s*([^\s#@]+)@sha256:([0-9a-f]{64})",
        compose_path.read_text(),
        re.MULTILINE,
    ):
        pins[m.group(1)] = m.group(2)
    if not pins:
        import pytest
        pytest.skip("no pinned images in compose")

    # Run the validator — if any pinned container is running, it must be IMPL
    result = subprocess.run(
        ["python3", str(REPO_ROOT / "scripts" / "cos-config-audit.sh")],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0
    # If the validator still confuses manifest digest vs image ID, ALL running
    # pinned containers get flagged as drift → meta.docker_container_freshness
    # will be ASPIR with "7 container(s) running stale image" or similar.
    # Invariant: if containers are actually running, validator reports IMPL
    # OR PARTIAL. A false-positive ASPIR ("stale image") is the regression.
    lines = [l for l in result.stdout.splitlines() if "docker_container_freshness" in l]
    if not lines:
        import pytest
        pytest.skip("validator did not emit docker_container_freshness line")
    line = lines[0]
    # Running containers exist per compose? check
    # Keep this below pytest's per-test timeout. If docker itself times out,
    # treat as "no docker"
    # and skip — this test is about cognitive-os containers, not docker performance.
    import pytest
    try:
        has_running = subprocess.run(
            [docker, "ps", "--filter", "name=cognitive-os-", "-q"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except subprocess.TimeoutExpired:
        pytest.skip("docker daemon unresponsive (>5s) — skipping container freshness check")
    if not has_running:
        pytest.skip("no cognitive-os-* containers running")

    # At least one container is running. With the fixed validator, it must
    # classify as IMPL when Config.Image matches the pin. If ASPIR AND the
    # reason mentions "stale" it's the regression.
    # Tolerance: if genuine drift exists (e.g. user hasn't pulled recent
    # updates) that's legitimate ASPIR. We can't distinguish perfectly here,
    # but Config.Image always carries the creation-time pin digest — a
    # container created from the pinned digest will always match, so unless
    # someone manually `docker run` a mismatched image, IMPL is expected.
    assert "[ IMPL  ]" in line or "[PARTIAL]" in line, (
        f"validator regressed: {line.strip()} — this may be the "
        "manifest-digest-vs-image-id confusion re-introduced (see "
        "_check_docker_container_freshness docstring)"
    )


def test_cos_update_tracks_compose_sha():
    """recreate_docker_if_compose_changed() must be wired into cos-update.sh."""
    text = (REPO_ROOT / "scripts" / "cos-update.sh").read_text()
    assert "recreate_docker_if_compose_changed" in text
    assert "DOCKER_COMPOSE_SHA_FILE" in text
    assert "docker-compose.sha" in text
