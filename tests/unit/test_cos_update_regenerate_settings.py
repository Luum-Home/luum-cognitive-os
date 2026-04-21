"""
tests/unit/test_cos_update_regenerate_settings.py

Unit tests for the `regenerate_settings_if_profile_changed` function added to
scripts/cos-update.sh. Tests run against a fake project tmpdir with a MOCK
apply-efficiency-profile.sh (must NOT execute the real one — it mutates
.claude/settings.json globally).

Strategy: extract the function from cos-update.sh, source it into a bash
subshell alongside a minimal scaffold of the variables/helpers it depends on,
then invoke it against a tmp "project".

Covers:
  1. First run (no SHA file)     → regen triggered, SHA file written
  2. Matching SHA                → regen skipped, SHA file unchanged
  3. SHA mismatch                → regen triggered, SHA file updated
  4. Missing profile script      → silent skip, no error, no SHA file
"""

import hashlib
import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
COS_UPDATE = REPO_ROOT / "scripts" / "cos-update.sh"


# ---------------------------------------------------------------------------
# Harness: build a bash snippet that sources the regen function with env vars
# pointing at a tmp project. The MOCK apply-efficiency-profile.sh simply
# records that it was called into a marker file — it does NOT touch any
# real settings.
# ---------------------------------------------------------------------------

MOCK_PROFILE_SCRIPT = """#!/usr/bin/env bash
# Mock apply-efficiency-profile.sh for tests. Records invocation + argv.
set -e
printf '%s\\n' "$@" > "${MARKER_FILE}"
exit 0
"""

MOCK_PROFILE_SCRIPT_FAILING = """#!/usr/bin/env bash
# Mock that records invocation but exits non-zero.
set -e
printf '%s\\n' "$@" > "${MARKER_FILE}"
exit 17
"""


def _build_harness(tmp_project: Path, force: str = "false") -> str:
    """
    Produce a bash script that:
      1. Sets up all variables the regen function expects
      2. Defines the helpers it calls (note/warn/sha256_of)
      3. Extracts and sources the `regenerate_settings_if_profile_changed`
         function body from cos-update.sh
      4. Invokes it once
    """
    return f"""
set -euo pipefail

PROJECT_ROOT="{tmp_project}"
SCRIPT_DIR="{tmp_project}/scripts"
COS_DIR="{tmp_project}/.cognitive-os"
STATE_DIR="$COS_DIR/state"
APPLY_EFF_PROFILE_SCRIPT="$SCRIPT_DIR/apply-efficiency-profile.sh"
APPLY_EFF_PROFILE_SHA_FILE="$STATE_DIR/apply-efficiency-profile.sha"
COGNITIVE_OS_YAML="$PROJECT_ROOT/cognitive-os.yaml"
FORCE={force}

note() {{ printf '%s\\n' "$*" >&2; }}
warn() {{ printf 'WARN: %s\\n' "$*" >&2; }}

sha256_of() {{
  local file="$1"
  if [[ ! -f "$file" ]]; then echo "MISSING"; return 0; fi
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file" | awk '{{print $1}}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" | awk '{{print $1}}'
  else
    wc -c < "$file" | tr -d ' '
  fi
}}

# Source just the function body from cos-update.sh.
# We extract lines between `regenerate_settings_if_profile_changed() {{` and
# the following closing `}}` at column 0. Write to a tmp file first because
# `source <(...)` (process substitution) is flaky under bash 3.2 on macOS.
EXTRACTED="$(mktemp -t regen-XXXXXX.sh)"
awk '
  /^regenerate_settings_if_profile_changed\\(\\) \\{{/ {{flag=1}}
  flag {{print}}
  /^\\}}$/ {{if (flag) exit}}
' "{COS_UPDATE}" > "$EXTRACTED"
# shellcheck disable=SC1090
source "$EXTRACTED"
rm -f "$EXTRACTED"

regenerate_settings_if_profile_changed
echo "EXIT=$?"
"""


def _make_project(tmp_path: Path, script_body: Optional[str] = MOCK_PROFILE_SCRIPT,
                  marker: Optional[Path] = None,
                  yaml_profile: Optional[str] = "default") -> Tuple[Path, Path]:
    """
    Build a minimal fake project under tmp_path:
      - scripts/apply-efficiency-profile.sh (the mock, or absent if None)
      - cognitive-os.yaml with efficiency.profile
      - .cognitive-os/state/ present
    Returns (project_root, marker_file_path).
    """
    project = tmp_path / "fake-project"
    (project / "scripts").mkdir(parents=True)
    (project / ".cognitive-os" / "state").mkdir(parents=True)

    marker_file = marker or (project / "mock_called.txt")

    if script_body is not None:
        script = project / "scripts" / "apply-efficiency-profile.sh"
        script.write_text(script_body)
        script.chmod(0o755)

    if yaml_profile is not None:
        yaml = project / "cognitive-os.yaml"
        yaml.write_text(f"efficiency:\n  profile: {yaml_profile}\n")

    return project, marker_file


def _run_harness(tmp_project: Path, marker_file: Path, force: str = "false") -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["MARKER_FILE"] = str(marker_file)
    return subprocess.run(
        ["bash", "-c", _build_harness(tmp_project, force=force)],
        capture_output=True, text=True, env=env,
    )


def _current_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRegenerateSettings:
    def test_first_run_creates_sha_and_triggers_regen(self, tmp_path):
        """No SHA file → mock should be called, SHA file should be written."""
        project, marker = _make_project(tmp_path)
        sha_file = project / ".cognitive-os" / "state" / "apply-efficiency-profile.sha"
        assert not sha_file.exists()
        assert not marker.exists()

        result = _run_harness(project, marker)
        assert result.returncode == 0, f"harness failed: {result.stderr}"

        # Mock was invoked with the profile argument
        assert marker.exists(), f"mock script was not invoked\nstderr: {result.stderr}"
        assert marker.read_text().strip() == "default"

        # SHA file written and matches the script
        assert sha_file.exists()
        expected = _current_sha(project / "scripts" / "apply-efficiency-profile.sh")
        assert sha_file.read_text().strip() == expected

    def test_matching_sha_skips_regen(self, tmp_path):
        """SHA file matches current script → regen MUST be skipped."""
        project, marker = _make_project(tmp_path)
        script = project / "scripts" / "apply-efficiency-profile.sh"
        sha_file = project / ".cognitive-os" / "state" / "apply-efficiency-profile.sha"

        # Pre-seed the SHA file with the CURRENT script hash
        sha_file.write_text(_current_sha(script) + "\n")

        result = _run_harness(project, marker)
        assert result.returncode == 0, f"harness failed: {result.stderr}"

        # Mock MUST NOT have been called
        assert not marker.exists(), (
            f"mock was invoked when SHA matched (skip path broken)\nstderr: {result.stderr}"
        )
        # SHA file unchanged
        assert sha_file.read_text().strip() == _current_sha(script)

    def test_sha_mismatch_triggers_regen(self, tmp_path):
        """Stale SHA file → regen triggered, SHA file updated."""
        project, marker = _make_project(tmp_path)
        script = project / "scripts" / "apply-efficiency-profile.sh"
        sha_file = project / ".cognitive-os" / "state" / "apply-efficiency-profile.sha"

        # Pre-seed with a bogus/old SHA
        stale_sha = "0" * 64
        sha_file.write_text(stale_sha + "\n")

        result = _run_harness(project, marker)
        assert result.returncode == 0, f"harness failed: {result.stderr}"

        # Mock was invoked
        assert marker.exists(), f"mock was not invoked on SHA mismatch\nstderr: {result.stderr}"
        # SHA file now has the CURRENT hash, not the stale one
        current = _current_sha(script)
        assert sha_file.read_text().strip() == current
        assert sha_file.read_text().strip() != stale_sha

    def test_missing_profile_script_exits_zero(self, tmp_path):
        """Absent apply-efficiency-profile.sh → silent skip, no error."""
        project, marker = _make_project(tmp_path, script_body=None)
        sha_file = project / ".cognitive-os" / "state" / "apply-efficiency-profile.sha"

        result = _run_harness(project, marker)
        assert result.returncode == 0, f"harness failed: {result.stderr}"

        # Nothing called, nothing written
        assert not marker.exists()
        assert not sha_file.exists()

    def test_script_failure_leaves_sha_file_unwritten(self, tmp_path):
        """If the profile script fails, the SHA file MUST NOT be updated."""
        project, marker = _make_project(tmp_path, script_body=MOCK_PROFILE_SCRIPT_FAILING)
        sha_file = project / ".cognitive-os" / "state" / "apply-efficiency-profile.sha"
        assert not sha_file.exists()

        result = _run_harness(project, marker)
        # The harness itself uses `set -e` but the regen function returns 1
        # rather than `exit 1`, so the harness script should still terminate
        # cleanly via the trailing `echo EXIT=...`. We accept either pattern:
        # the key invariant is that the SHA file remains absent.
        assert marker.exists(), "mock should have been invoked"
        assert not sha_file.exists(), (
            "SHA file MUST NOT be written when the profile script fails"
        )

    def test_force_flag_triggers_regen_even_when_sha_matches(self, tmp_path):
        """FORCE=true must override the match-skip shortcut."""
        project, marker = _make_project(tmp_path)
        script = project / "scripts" / "apply-efficiency-profile.sh"
        sha_file = project / ".cognitive-os" / "state" / "apply-efficiency-profile.sha"
        sha_file.write_text(_current_sha(script) + "\n")

        result = _run_harness(project, marker, force="true")
        assert result.returncode == 0, f"harness failed: {result.stderr}"
        assert marker.exists(), "FORCE=true should trigger regen even when SHAs match"
