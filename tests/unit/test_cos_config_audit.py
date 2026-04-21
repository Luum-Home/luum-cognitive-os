"""
tests/unit/test_cos_config_audit.py

Unit tests for scripts/cos-config-audit.sh (the aspirational-vs-real validator).

Test (a): script exits 0
Test (b): output contains expected status markers
Test (c): --json mode produces valid, parseable JSON with correct structure
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_SCRIPT = REPO_ROOT / "scripts" / "cos-config-audit.sh"


def _run_audit(*extra_args) -> subprocess.CompletedProcess:
    """Run the audit script and return the CompletedProcess result."""
    return subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), *extra_args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


class TestCosConfigAuditExitCode:
    """Test (a): script always exits 0 regardless of findings."""

    def test_exits_zero_text_mode(self):
        result = _run_audit()
        assert result.returncode == 0, (
            f"Expected exit 0, got {result.returncode}\nstderr: {result.stderr}"
        )

    def test_exits_zero_json_mode(self):
        result = _run_audit("--json")
        assert result.returncode == 0, (
            f"Expected exit 0 in --json mode, got {result.returncode}\nstderr: {result.stderr}"
        )


class TestCosConfigAuditTextOutput:
    """Test (b): output contains the expected status markers and structure."""

    def _get_output(self):
        result = _run_audit()
        assert result.returncode == 0
        return result.stdout

    def test_output_contains_impl_marker(self):
        """At least one section must be IMPL (killswitch_respected should be)."""
        output = self._get_output()
        assert "[IMPL" in output or "[ IMPL" in output, (
            "Expected at least one [IMPL] in output — killswitch_respected should be IMPL"
        )

    def test_output_contains_aspir_marker(self):
        """At least two sections must be ASPIR (ttft_watchdog and engram_mcp)."""
        output = self._get_output()
        aspir_count = output.count("ASPIR")
        assert aspir_count >= 2, (
            f"Expected >= 2 ASPIR entries; found {aspir_count}. "
            "ttft_watchdog and engram_mcp should both be aspirational."
        )

    def test_output_contains_summary_line(self):
        output = self._get_output()
        assert "Summary:" in output, "Expected 'Summary:' line at end of output"
        assert "implemented" in output, "Expected 'implemented' count in Summary"
        assert "partial" in output, "Expected 'partial' count in Summary"
        assert "aspirational" in output, "Expected 'aspirational' count in Summary"

    def test_output_has_nine_section_lines(self):
        """Exactly 9 contracts are defined — one line per contract."""
        output = self._get_output()
        section_lines = [
            line for line in output.splitlines()
            if any(marker in line for marker in ["[IMPL", "[ IMPL", "PARTIAL", "ASPIR"])
            and "—" in line
        ]
        assert len(section_lines) >= 9, (
            f"Expected >= 9 section lines, got {len(section_lines)}"
        )

    def test_known_aspir_sections_present(self):
        output = self._get_output()
        assert "runtime.ttft_watchdog" in output, "runtime.ttft_watchdog section missing from output"
        assert "runtime.engram_mcp" in output, "runtime.engram_mcp section missing from output"

    def test_killswitch_is_impl(self):
        output = self._get_output()
        for line in output.splitlines():
            if "runtime.killswitch_respected" in line:
                assert "IMPL" in line, (
                    f"Expected runtime.killswitch_respected to be IMPL, got: {line}"
                )
                break
        else:
            raise AssertionError("runtime.killswitch_respected section not found in output")

    def test_reaper_is_impl_or_partial(self):
        """Reaper has both so-reaper.sh and reaper-daemon-launcher — should be IMPL or PARTIAL."""
        output = self._get_output()
        for line in output.splitlines():
            if "runtime.reaper" in line:
                assert any(s in line for s in ("IMPL", "PARTIAL")), (
                    f"Expected runtime.reaper to be IMPL or PARTIAL, got: {line}"
                )
                break
        else:
            raise AssertionError("runtime.reaper section not found in output")


class TestCosConfigAuditJsonMode:
    """Test (c): --json flag produces valid JSON parseable by standard library."""

    def _get_json(self):
        result = _run_audit("--json")
        assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
        return json.loads(result.stdout)

    def test_json_is_valid_and_parseable(self):
        data = self._get_json()
        assert isinstance(data, list), "Expected JSON array at top level"

    def test_json_has_expected_count(self):
        data = self._get_json()
        assert len(data) >= 9, f"Expected >= 9 entries in JSON output, got {len(data)}"

    def test_json_entries_have_required_keys(self):
        data = self._get_json()
        required_keys = {"section", "status", "reason"}
        for entry in data:
            missing = required_keys - set(entry.keys())
            assert not missing, f"Entry missing keys {missing}: {entry}"

    def test_json_status_values_are_valid(self):
        data = self._get_json()
        valid_statuses = {"IMPL", "PARTIAL", "ASPIR"}
        for entry in data:
            assert entry["status"] in valid_statuses, (
                f"Invalid status '{entry['status']}' for section '{entry['section']}'"
            )

    def test_json_contains_aspir_entries(self):
        data = self._get_json()
        aspir_entries = [e for e in data if e["status"] == "ASPIR"]
        assert len(aspir_entries) >= 2, (
            f"Expected >= 2 ASPIR entries in JSON; got {len(aspir_entries)}: "
            f"{[e['section'] for e in aspir_entries]}"
        )

    def test_json_contains_impl_entries(self):
        data = self._get_json()
        impl_entries = [e for e in data if e["status"] == "IMPL"]
        assert len(impl_entries) >= 1, (
            f"Expected >= 1 IMPL entry in JSON; got 0"
        )

    def test_json_sections_are_unique(self):
        data = self._get_json()
        sections = [e["section"] for e in data]
        assert len(sections) == len(set(sections)), (
            f"Duplicate sections found: {[s for s in sections if sections.count(s) > 1]}"
        )

    def test_json_no_empty_reasons(self):
        data = self._get_json()
        for entry in data:
            assert entry.get("reason", "").strip(), (
                f"Empty reason for section '{entry['section']}'"
            )
