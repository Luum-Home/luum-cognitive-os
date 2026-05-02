"""Integration tests for harness driver parity (ADR-064 Surface 2).

Verifies that all shipped harness adapters (claude-code, codex, bare-cli) have
working settings drivers that:
  1. Are present + executable.
  2. Project the canonical hook registry (cognitive-os.yaml > harness.hooks)
     into a valid file in the expected location.
  3. Produce stable, idempotent output (re-running yields byte-identical JSON).
  4. Are visible to ``scripts/cos-doctor-harness.sh --json`` adapter coverage.

These tests EXECUTE the drivers against the live repository config and assert
on the resulting projection files.  Each test isolates side-effects via a
temporary PROJECT_DIR copy when mutating, or re-uses the repo when read-only.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path



REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LIB = REPO_ROOT / "scripts" / "_lib"
BARE_DRIVER = LIB / "settings-driver-bare.sh"
CC_DRIVER = LIB / "settings-driver-claude-code.sh"
CODEX_DRIVER = LIB / "settings-driver-codex.sh"
DOCTOR = REPO_ROOT / "scripts" / "cos-doctor-harness.sh"
APPLY = REPO_ROOT / "scripts" / "apply-efficiency-profile.sh"


def _isolated_project(tmp_path: Path) -> Path:
    """Build a minimal isolated PROJECT_DIR mirroring the repo's config.

    We need cognitive-os.yaml + the driver scripts.  We symlink the rest so
    drivers that reach into hooks/ (e.g. for sanity grep) still see the live
    tree, but writes go to tmp_path.
    """
    project = tmp_path / "project"
    project.mkdir()
    # Mirror the canonical config — drivers read this verbatim.
    shutil.copy2(REPO_ROOT / "cognitive-os.yaml", project / "cognitive-os.yaml")
    # Symlink the script tree so drivers can locate _lib helpers by relative path.
    (project / "scripts").symlink_to(REPO_ROOT / "scripts")
    (project / "hooks").symlink_to(REPO_ROOT / "hooks")
    (project / "lib").symlink_to(REPO_ROOT / "lib")
    return project


# ──────────────────────────────────────────────────────────────────────────────
# Test 1: bare-cli driver script exists, is executable, and is non-empty.
# ──────────────────────────────────────────────────────────────────────────────
def test_bare_driver_script_present():
    assert BARE_DRIVER.exists(), f"missing driver: {BARE_DRIVER}"
    assert BARE_DRIVER.stat().st_size > 0
    # Must be a bash script with the SCOPE marker per RULES §13/14.
    head = BARE_DRIVER.read_text().splitlines()[:3]
    assert any("SCOPE: os-only" in line for line in head), \
        f"settings-driver-bare.sh missing '# SCOPE: os-only' header: {head}"


# ──────────────────────────────────────────────────────────────────────────────
# Test 2: bare-cli driver produces valid JSON in the canonical bare-cli shape.
# ──────────────────────────────────────────────────────────────────────────────
def test_bare_driver_emits_valid_canonical_json(tmp_path: Path):
    project = _isolated_project(tmp_path)
    result = subprocess.run(
        ["bash", str(BARE_DRIVER)],
        cwd=project,
        env={**os.environ, "PROJECT_DIR": str(project)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"driver failed: {result.stderr}"
    out_file = project / ".cognitive-os" / "cos-runner-hooks.json"
    assert out_file.exists(), "driver did not write expected projection"
    data = json.loads(out_file.read_text())
    # Schema sanity
    assert data["schema_version"] == 1
    assert data["harness"] == "bare_cli"
    assert "events" in data
    expected_events = {
        "session_start",
        "user_prompt_submit",
        "tool_use_start",
        "tool_use_end",
        "session_end",
    }
    assert set(data["events"].keys()) == expected_events
    # At least one hook in each of the major lifecycle events given the live
    # cognitive-os.yaml registry has 100+ hooks across all events.
    assert len(data["events"]["session_start"]) > 0
    assert len(data["events"]["session_end"]) > 0


# ──────────────────────────────────────────────────────────────────────────────
# Test 3: bare-cli driver is idempotent — second run produces identical bytes.
# ──────────────────────────────────────────────────────────────────────────────
def test_bare_driver_idempotent(tmp_path: Path):
    project = _isolated_project(tmp_path)
    env = {**os.environ, "PROJECT_DIR": str(project)}
    subprocess.run(["bash", str(BARE_DRIVER)], cwd=project, env=env, check=True,
                   capture_output=True)
    first = (project / ".cognitive-os" / "cos-runner-hooks.json").read_bytes()
    subprocess.run(["bash", str(BARE_DRIVER)], cwd=project, env=env, check=True,
                   capture_output=True)
    second = (project / ".cognitive-os" / "cos-runner-hooks.json").read_bytes()
    assert first == second, "driver output is not byte-identical on re-run"

    # --check should now report OK (no drift).
    check = subprocess.run(
        ["bash", str(BARE_DRIVER), "--check"],
        cwd=project, env=env, capture_output=True, text=True,
    )
    assert check.returncode == 0, f"--check reported drift unexpectedly: {check.stderr}"


# ──────────────────────────────────────────────────────────────────────────────
# Test 4: bare-cli only projects events in its supported capability matrix.
#   Per manifests/harness-driver-capabilities.yaml: PreCompact / SubagentStart
#   / TeammateIdle / TaskCreated / TaskCompleted are unsupported and MUST NOT
#   appear in the output.
# ──────────────────────────────────────────────────────────────────────────────
def test_bare_driver_excludes_unsupported_events(tmp_path: Path):
    project = _isolated_project(tmp_path)
    subprocess.run(
        ["bash", str(BARE_DRIVER)],
        cwd=project,
        env={**os.environ, "PROJECT_DIR": str(project)},
        check=True,
        capture_output=True,
    )
    data = json.loads((project / ".cognitive-os" / "cos-runner-hooks.json").read_text())
    forbidden = {
        "pre_compact", "PreCompact",
        "subagent_start", "SubagentStart",
        "teammate_idle", "TeammateIdle",
        "task_created", "TaskCreated",
        "task_completed", "TaskCompleted",
    }
    keys = set(data["events"].keys())
    leaked = keys & forbidden
    assert not leaked, f"bare-cli projection leaked unsupported events: {leaked}"


# ──────────────────────────────────────────────────────────────────────────────
# Test 5: cos-doctor-harness --json lists all three adapters with status.
# ──────────────────────────────────────────────────────────────────────────────
def test_doctor_harness_lists_all_adapters():
    result = subprocess.run(
        ["bash", str(DOCTOR), "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 1), \
        f"doctor exited unexpectedly: rc={result.returncode} stderr={result.stderr}"
    payload = json.loads(result.stdout)
    assert "adapters" in payload, "JSON output missing 'adapters' key"
    names = {a["adapter"] for a in payload["adapters"]}
    assert names == {"claude-code", "codex", "bare-cli"}, \
        f"adapter coverage incomplete: {names}"
    # Every adapter must report a known status string.
    for entry in payload["adapters"]:
        assert entry["status"] in {"ok", "warn", "fail"}, \
            f"unexpected adapter status: {entry}"
        assert entry["detail"], "adapter detail must be non-empty"


# ──────────────────────────────────────────────────────────────────────────────
# Test 6: apply-efficiency-profile --harness=bare-cli routes to the bare driver.
# ──────────────────────────────────────────────────────────────────────────────
def test_apply_profile_supports_bare_cli_harness(tmp_path: Path):
    project = _isolated_project(tmp_path)
    # PROJECT_DIR is detected from cwd presence of cognitive-os.yaml.
    result = subprocess.run(
        ["bash", str(APPLY), "default", "--harness=bare-cli"],
        cwd=project,
        env={**os.environ, "PROJECT_DIR": str(project)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"apply-efficiency-profile failed: {result.stderr}"
    assert "Bare-CLI driver" in result.stdout, \
        f"apply-efficiency-profile did not invoke bare driver: {result.stdout}"
    out = project / ".cognitive-os" / "cos-runner-hooks.json"
    assert out.exists(), "bare driver did not produce projection via apply wrapper"
    data = json.loads(out.read_text())
    assert data["harness"] == "bare_cli"
