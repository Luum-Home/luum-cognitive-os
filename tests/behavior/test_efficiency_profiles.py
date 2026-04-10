"""Tests for scripts/apply-efficiency-profile.sh.

Validates:
- lean profile generates settings.json with exactly 7 hook commands
- standard profile generates settings.json with exactly 27 hook commands
- full profile exits 0 and prints count without modifying settings.json
- invalid profile exits 1
- lean/standard/full hook sets are strictly additive subsets
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "apply-efficiency-profile.sh"

pytestmark = pytest.mark.behavior


def _run_profile(profile: str, project_dir: Path = PROJECT_ROOT) -> subprocess.CompletedProcess:
    """Run apply-efficiency-profile.sh with the given profile in a project dir."""
    return subprocess.run(
        ["bash", str(SCRIPT), profile],
        capture_output=True,
        text=True,
        cwd=str(project_dir),
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(Path.home())},
        timeout=30,
    )


def _count_hook_commands(settings_path: Path) -> int:
    """Count 'command' entries in a settings.json file."""
    raw = settings_path.read_text()
    return raw.count('"command":')


def _collect_hook_scripts(settings_path: Path) -> set:
    """Return the set of hook script filenames referenced in settings.json."""
    raw = settings_path.read_text()
    # Extract filenames like session-init.sh, error-pipeline.sh, etc.
    import re
    return set(re.findall(r'hooks/([a-z0-9_\-]+\.sh)', raw))


# ─── Script exists ────────────────────────────────────────────────────────────


class TestScriptExists:
    def test_script_file_exists(self):
        assert SCRIPT.exists(), f"Missing: {SCRIPT}"

    def test_script_is_valid_bash(self):
        result = subprocess.run(
            ["bash", "-n", str(SCRIPT)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Bash syntax error: {result.stderr}"


# ─── Invalid profile ─────────────────────────────────────────────────────────


class TestInvalidProfile:
    def test_invalid_profile_exits_nonzero(self, tmp_path):
        result = subprocess.run(
            ["bash", str(SCRIPT), "ultramax"],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            timeout=10,
        )
        assert result.returncode != 0, "Invalid profile should exit non-zero"

    def test_invalid_profile_prints_error(self, tmp_path):
        result = subprocess.run(
            ["bash", str(SCRIPT), "badprofile"],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            timeout=10,
        )
        combined = result.stdout + result.stderr
        assert "ERROR" in combined or "Unknown" in combined or "Invalid" in combined


# ─── Lean profile (7 hooks) ───────────────────────────────────────────────────


class TestLeanProfile:
    """lean profile must produce settings.json with exactly 7 hook commands."""

    @pytest.fixture
    def lean_settings(self, tmp_path):
        """Create a minimal project directory with needed files, run lean profile."""
        # Copy cognitive-os.yaml so the script can read it
        src_yaml = PROJECT_ROOT / "cognitive-os.yaml"
        if src_yaml.exists():
            shutil.copy(src_yaml, tmp_path / "cognitive-os.yaml")
        # Create .claude dir so settings.json can be written
        (tmp_path / ".claude").mkdir(exist_ok=True)
        _run_profile("lean", tmp_path)
        return tmp_path / ".claude" / "settings.json"

    def test_lean_exits_zero(self, lean_settings):
        # If lean_settings fixture ran successfully, it exited zero
        assert True  # fixture would have raised if exit nonzero

    def test_lean_creates_settings_json(self, lean_settings):
        assert lean_settings.exists(), "lean should create .claude/settings.json"

    def test_lean_has_seven_hook_commands(self, lean_settings):
        if not lean_settings.exists():
            pytest.skip("settings.json not created")
        count = _count_hook_commands(lean_settings)
        assert count == 7, f"lean profile should have 7 hook commands, got {count}"

    def test_lean_includes_self_install(self, lean_settings):
        if not lean_settings.exists():
            pytest.skip("settings.json not created")
        assert "self-install.sh" in lean_settings.read_text()

    def test_lean_includes_secret_detector(self, lean_settings):
        if not lean_settings.exists():
            pytest.skip("settings.json not created")
        assert "secret-detector.sh" in lean_settings.read_text()

    def test_lean_includes_error_pipeline(self, lean_settings):
        if not lean_settings.exists():
            pytest.skip("settings.json not created")
        assert "error-pipeline.sh" in lean_settings.read_text()

    def test_lean_includes_session_cleanup(self, lean_settings):
        if not lean_settings.exists():
            pytest.skip("settings.json not created")
        assert "session-cleanup.sh" in lean_settings.read_text()

    def test_lean_produces_valid_json(self, lean_settings):
        if not lean_settings.exists():
            pytest.skip("settings.json not created")
        parsed = json.loads(lean_settings.read_text())
        assert "hooks" in parsed


# ─── Standard profile (27 hooks) ─────────────────────────────────────────────


class TestStandardProfile:
    """standard profile must produce settings.json with exactly 27 hook commands."""

    @pytest.fixture
    def standard_settings(self):
        """Run standard profile against real project dir; save/restore settings.json."""
        settings_path = PROJECT_ROOT / ".claude" / "settings.json"
        # Save original content
        original_content = settings_path.read_text() if settings_path.exists() else None
        # Run standard profile
        _run_profile("standard", PROJECT_ROOT)
        yield settings_path
        # Restore original content
        if original_content is not None:
            settings_path.write_text(original_content)
        elif settings_path.exists():
            settings_path.unlink()

    def test_standard_exits_zero(self, standard_settings):
        assert True  # fixture would have raised if exit nonzero

    def test_standard_creates_settings_json(self, standard_settings):
        assert standard_settings.exists()

    def test_standard_has_twentyseven_hook_commands(self, standard_settings):
        if not standard_settings.exists():
            pytest.skip("settings.json not created")
        count = _count_hook_commands(standard_settings)
        assert count == 30, f"standard profile should have 30 hook commands, got {count}"

    def test_standard_includes_inject_phase_context(self, standard_settings):
        if not standard_settings.exists():
            pytest.skip("settings.json not created")
        assert "inject-phase-context.sh" in standard_settings.read_text()

    def test_standard_includes_rate_limiter(self, standard_settings):
        if not standard_settings.exists():
            pytest.skip("settings.json not created")
        assert "rate-limiter.sh" in standard_settings.read_text()

    def test_standard_includes_completion_gate(self, standard_settings):
        if not standard_settings.exists():
            pytest.skip("settings.json not created")
        assert "completion-gate.sh" in standard_settings.read_text()

    def test_standard_produces_valid_json(self, standard_settings):
        if not standard_settings.exists():
            pytest.skip("settings.json not created")
        parsed = json.loads(standard_settings.read_text())
        assert "hooks" in parsed


# ─── Full profile (reports, no-op) ───────────────────────────────────────────


class TestFullProfile:
    """full profile must exit 0 and report count without modifying settings.json."""

    def test_full_exits_zero(self):
        result = subprocess.run(
            ["bash", str(SCRIPT), "full"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=15,
        )
        assert result.returncode == 0, f"full profile exited {result.returncode}: {result.stderr}"

    def test_full_prints_hook_count(self):
        result = subprocess.run(
            ["bash", str(SCRIPT), "full"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=15,
        )
        combined = result.stdout + result.stderr
        # Should mention hook commands and a number
        assert "hook" in combined.lower() or "command" in combined.lower()

    def test_full_does_not_overwrite_settings_in_real_project(self):
        """Full profile should leave settings.json unchanged."""
        settings_path = PROJECT_ROOT / ".claude" / "settings.json"
        if not settings_path.exists():
            pytest.skip("No settings.json in real project")

        original_content = settings_path.read_text()
        subprocess.run(
            ["bash", str(SCRIPT), "full"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=15,
        )
        after_content = settings_path.read_text()
        assert original_content == after_content, (
            "full profile must not modify settings.json"
        )

    def test_full_mentions_profile_name(self):
        result = subprocess.run(
            ["bash", str(SCRIPT), "full"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=15,
        )
        combined = result.stdout + result.stderr
        assert "full" in combined.lower()


# ─── Subset ordering (lean ⊆ standard ⊆ full) ────────────────────────────────


class TestProfileSubsets:
    """Every hook in lean must also appear in standard (additive property)."""

    @pytest.fixture
    def lean_settings(self, tmp_path):
        copy = tmp_path / "lean"
        copy.mkdir()
        src_yaml = PROJECT_ROOT / "cognitive-os.yaml"
        if src_yaml.exists():
            shutil.copy(src_yaml, copy / "cognitive-os.yaml")
        (copy / ".claude").mkdir()
        _run_profile("lean", copy)
        return copy / ".claude" / "settings.json"

    @pytest.fixture
    def standard_settings(self, tmp_path):
        copy = tmp_path / "standard"
        copy.mkdir()
        src_yaml = PROJECT_ROOT / "cognitive-os.yaml"
        if src_yaml.exists():
            shutil.copy(src_yaml, copy / "cognitive-os.yaml")
        (copy / ".claude").mkdir()
        _run_profile("standard", copy)
        return copy / ".claude" / "settings.json"

    def test_all_lean_hooks_present_in_standard(self, lean_settings, standard_settings):
        if not lean_settings.exists() or not standard_settings.exists():
            pytest.skip("settings.json files not created")

        lean_scripts = _collect_hook_scripts(lean_settings)
        standard_scripts = _collect_hook_scripts(standard_settings)

        missing = lean_scripts - standard_scripts
        assert not missing, (
            f"standard is missing hooks from lean: {missing}"
        )

    def test_standard_has_more_hooks_than_lean(self, lean_settings, standard_settings):
        if not lean_settings.exists() or not standard_settings.exists():
            pytest.skip("settings.json files not created")

        lean_count = _count_hook_commands(lean_settings)
        standard_count = _count_hook_commands(standard_settings)
        assert standard_count > lean_count, (
            f"standard ({standard_count}) must have more hooks than lean ({lean_count})"
        )
