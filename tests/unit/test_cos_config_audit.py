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


# ---------------------------------------------------------------------------
# Annotation coherence tests (STATUS annotations vs runtime checks)
# ---------------------------------------------------------------------------

import importlib.util
from importlib.machinery import SourceFileLoader


def _load_audit_module():
    """Dynamically load cos-config-audit.sh as a Python module (despite .sh ext)."""
    loader = SourceFileLoader("cos_config_audit", str(AUDIT_SCRIPT))
    spec = importlib.util.spec_from_loader("cos_config_audit", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class TestStatusAnnotations:
    """Parser correctly extracts # STATUS: comments from cognitive-os.yaml."""

    def test_status_annotations_parsed(self, tmp_path):
        """Parser extracts annotation→section bindings from YAML."""
        mod = _load_audit_module()
        yaml_text = (
            "project:\n"
            "  # STATUS: implemented\n"
            "  phase: reconstruction\n"
            "efficiency:\n"
            "  # STATUS: partial\n"
            "  profile: default\n"
            "# STATUS: aspirational\n"
            "orchestration:\n"
            "  sub_agent_cwd: current\n"
        )
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_text)
        annotations = mod.parse_status_annotations(yaml_file)
        assert annotations.get("project.phase") == "IMPL"
        assert annotations.get("efficiency.profile") == "PARTIAL"
        assert annotations.get("orchestration") == "ASPIR"


class TestDriftDetection:
    """Drift: annotation contradicts computed status."""

    def test_drift_detected(self, tmp_path, monkeypatch):
        """When annotation says implemented but check returns ASPIR -> [DRIFT]."""
        mod = _load_audit_module()

        # Fake annotations with a drift
        fake_annotations = {"runtime.ttft_watchdog": "IMPL"}  # drift: actual is ASPIR
        monkeypatch.setattr(mod, "parse_status_annotations", lambda p: fake_annotations)

        results = mod.run_audit(use_color=False)
        ttft = next(r for r in results if r["section"] == "runtime.ttft_watchdog")
        assert ttft["coherence"] == "DRIFT", f"Expected DRIFT, got {ttft['coherence']}"
        assert ttft["annotation"] == "IMPL"
        assert ttft["status"] == "ASPIR"

        text = mod.format_text(results, use_color=False)
        assert "DRIFT" in text, "Expected [DRIFT] marker in text output"
        assert "runtime.ttft_watchdog" in text

    def test_strict_mode_exits_nonzero_on_drift(self):
        """--strict flag returns exit 1 when DRIFT present (simulated via env patching)."""
        # We simulate by writing a temporary yaml that introduces drift.
        # Simpler: invoke the script with a monkey-patched annotation parser via
        # a helper script. Easiest path: patch cognitive-os.yaml temporarily.
        yaml_path = REPO_ROOT / "cognitive-os.yaml"
        backup = yaml_path.read_text()
        try:
            # Flip one annotation to create drift
            tampered = backup.replace(
                "# STATUS: aspirational\n  ttft_watchdog:",
                "# STATUS: implemented\n  ttft_watchdog:",
                1,
            )
            assert tampered != backup, "Failed to tamper yaml for drift test"
            yaml_path.write_text(tampered)

            # Non-strict exits 0
            r_normal = _run_audit()
            assert r_normal.returncode == 0, (
                f"Non-strict should exit 0 even on drift, got {r_normal.returncode}"
            )
            assert "DRIFT" in r_normal.stdout, "Expected DRIFT marker in tampered output"

            # Strict exits 1
            r_strict = _run_audit("--strict")
            assert r_strict.returncode == 1, (
                f"--strict should exit 1 on drift, got {r_strict.returncode}\n"
                f"stdout: {r_strict.stdout}"
            )
        finally:
            yaml_path.write_text(backup)


class TestUnannotatedFlagged:
    """Sections without annotation are flagged with [unannotated]."""

    def test_unannotated_sections_flagged(self, monkeypatch):
        """Remove all annotations; every non-meta contract line should show [unannotated].

        `meta.*` sections are cross-file contracts exempt from annotation; they
        stay coherent ("OK") even when annotations are wiped.
        """
        mod = _load_audit_module()
        monkeypatch.setattr(mod, "parse_status_annotations", lambda p: {})
        results = mod.run_audit(use_color=False)
        for r in results:
            if r["section"].startswith("meta."):
                assert r["coherence"] == "OK", (
                    f"Expected meta.* to be OK, got {r['coherence']} for {r['section']}"
                )
            else:
                assert r["coherence"] == "UNANNOTATED", (
                    f"Expected UNANNOTATED for {r['section']}, got {r['coherence']}"
                )
        text = mod.format_text(results, use_color=False)
        assert "[unannotated]" in text, "Expected [unannotated] marker in text output"


class TestSettingsFreshness:
    """Contract: meta.settings_freshness tracks apply-efficiency-profile.sh SHA."""

    def test_settings_freshness_matches_when_sha_equal(self, tmp_path, monkeypatch):
        """When tracked SHA equals current script SHA → IMPL."""
        import hashlib
        mod = _load_audit_module()

        # Build a fake root with script + settings + matching SHA file
        script = tmp_path / "scripts" / "apply-efficiency-profile.sh"
        script.parent.mkdir(parents=True)
        script.write_text("#!/bin/bash\necho hi\n")
        settings = tmp_path / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text("{}")
        sha_file = tmp_path / ".cognitive-os" / "state" / "apply-efficiency-profile.sha"
        sha_file.parent.mkdir(parents=True)
        sha_file.write_text(hashlib.sha256(script.read_bytes()).hexdigest())

        status, reason = mod._check_settings_freshness(tmp_path)
        assert status == "IMPL", f"expected IMPL, got {status}: {reason}"
        assert "in sync" in reason

    def test_settings_freshness_drift_when_sha_differs(self, tmp_path):
        """Stale tracked SHA → ASPIR with guidance to re-run."""
        mod = _load_audit_module()
        script = tmp_path / "scripts" / "apply-efficiency-profile.sh"
        script.parent.mkdir(parents=True)
        script.write_text("#!/bin/bash\necho hi\n")
        settings = tmp_path / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text("{}")
        sha_file = tmp_path / ".cognitive-os" / "state" / "apply-efficiency-profile.sha"
        sha_file.parent.mkdir(parents=True)
        sha_file.write_text("0" * 64)  # stale

        status, reason = mod._check_settings_freshness(tmp_path)
        assert status == "ASPIR", f"expected ASPIR, got {status}: {reason}"
        assert "apply-efficiency-profile.sh changed" in reason


class TestSettingsDriverResolution:
    """Audit settings parsing should tolerate more than one harness driver."""

    def test_settings_commands_read_codex_hooks_when_codex_is_active(self, tmp_path, monkeypatch):
        mod = _load_audit_module()

        codex = tmp_path / ".codex" / "hooks.json"
        codex.parent.mkdir(parents=True)
        codex.write_text(
            json.dumps(
                {
                    "SessionStart": [
                        {
                            "matcher": "startup",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": 'bash "$PWD/hooks/self-install.sh"',
                                }
                            ],
                        }
                    ]
                }
            )
        )

        monkeypatch.setenv("COGNITIVE_OS_HARNESS", "codex")
        monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)

        commands = mod._settings_commands()
        assert commands == ['bash "$PWD/hooks/self-install.sh"']

    def test_settings_candidates_prefer_claude_projection_by_default(self, tmp_path, monkeypatch):
        mod = _load_audit_module()

        (tmp_path / ".claude").mkdir(parents=True)
        (tmp_path / ".codex").mkdir(parents=True)
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.delenv("CODEX_HOME", raising=False)

        candidates = mod._settings_driver_candidates(tmp_path)
        assert candidates[0] == tmp_path / ".claude" / "settings.local.json"
        assert candidates[1] == tmp_path / ".claude" / "settings.json"

    def test_settings_freshness_partial_when_no_sha_tracked(self, tmp_path):
        """settings.json present but no SHA file → PARTIAL."""
        mod = _load_audit_module()
        script = tmp_path / "scripts" / "apply-efficiency-profile.sh"
        script.parent.mkdir(parents=True)
        script.write_text("#!/bin/bash\necho hi\n")
        settings = tmp_path / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text("{}")
        # No SHA file

        status, reason = mod._check_settings_freshness(tmp_path)
        assert status == "PARTIAL", f"expected PARTIAL, got {status}: {reason}"
        assert "no profile SHA tracked" in reason

    def test_meta_sections_not_required_to_have_status_annotation(self, monkeypatch):
        """meta.* contracts are cross-file; they should NOT produce [unannotated]."""
        mod = _load_audit_module()
        # Force empty annotations — every contract is "unannotated" by lookup
        monkeypatch.setattr(mod, "parse_status_annotations", lambda p: {})

        results = mod.run_audit(use_color=False)
        meta_entries = [r for r in results if r["section"].startswith("meta.")]
        assert meta_entries, "Expected at least one meta.* contract (meta.settings_freshness)"
        for r in meta_entries:
            assert r["coherence"] == "OK", (
                f"meta.* section should be coherent without annotation, "
                f"got {r['coherence']} for {r['section']}"
            )
        # And the text output MUST NOT mark these as [unannotated]
        text = mod.format_text(results, use_color=False)
        for r in meta_entries:
            # Find the line for this section and assert no [unannotated] suffix
            for line in text.splitlines():
                if r["section"] in line:
                    assert "[unannotated]" not in line, (
                        f"meta.* line should not carry [unannotated]: {line}"
                    )


class TestCoherenceInvariant:
    """Invariant: committed cognitive-os.yaml annotations must match runtime checks."""

    def test_all_current_sections_coherent(self):
        """Run validator against real cognitive-os.yaml — ZERO drift allowed."""
        result = _run_audit("--json")
        assert result.returncode == 0, f"audit failed: {result.stderr}"
        data = json.loads(result.stdout)
        drift_entries = [e for e in data if e.get("coherence") == "DRIFT"]
        assert not drift_entries, (
            f"Coherence violation: {len(drift_entries)} section(s) drift from annotation.\n"
            + "\n".join(
                f"  - {e['section']}: annotation={e.get('annotation')} actual={e['status']}"
                for e in drift_entries
            )
        )
        unannotated = [e for e in data if e.get("coherence") == "UNANNOTATED"]
        assert not unannotated, (
            f"Missing annotations on {len(unannotated)} contract section(s): "
            f"{[e['section'] for e in unannotated]}"
        )
