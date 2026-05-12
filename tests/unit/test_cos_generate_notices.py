"""Unit tests for scripts/cos-generate-notices.py.

Test coverage:
  1. Schema validation of manifests/external-tool-licenses.yaml
  2. Generator output matches expected fixture for a known-input case
  3. --check mode detects drift when NOTICE.md is mutated
  4. --mode oss vs --mode saas produce different output for a copyleft entry
"""
from __future__ import annotations

import importlib.util
import textwrap
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Load the script as a module (it lives in scripts/, not a package)
# ---------------------------------------------------------------------------

_SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "cos-generate-notices.py"
_MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent.parent / "manifests" / "external-tool-licenses.yaml"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("cos_generate_notices", _SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.fixture(scope="module")
def gen():
    """Return the loaded cos-generate-notices module."""
    return _load_module()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_MANIFEST_TEXT = textwrap.dedent("""\
    schema_version: 1
    entries:
      - name: "Fake MIT Lib"
        upstream_url: "https://example.com/fake-mit"
        spdx: "MIT"
        status: "ALLOWED"
        copyright: "Copyright (c) 2025 Fake Author"
        attribution: "Ported by test."
        cos_files:
          - "lib/fake.py"
        annex_f: "docs/03-PoCs/research/fake-annex-f.md"
        notes: >
          This is a test entry.

      - name: "AGPL Lib"
        upstream_url: "https://example.com/agpl-lib"
        spdx: "AGPL-3.0"
        status: "TRIAL-PATTERNS"
        copyright: "Copyright (c) 2025 AGPL Corp"
        attribution: "Pattern only."
        cos_files: []
        annex_f: "docs/03-PoCs/research/agpl-annex-f.md"
        notes: >
          Copyleft — rejected at runtime.
""")


@pytest.fixture()
def minimal_manifest_file(tmp_path) -> Path:
    p = tmp_path / "external-tool-licenses.yaml"
    p.write_text(MINIMAL_MANIFEST_TEXT, encoding="utf-8")
    return p


@pytest.fixture()
def minimal_entries(gen, minimal_manifest_file) -> list[dict[str, Any]]:
    manifest = gen._parse_yaml_manifest(minimal_manifest_file)
    return manifest["entries"]


# ---------------------------------------------------------------------------
# 1. Schema validation of manifests/external-tool-licenses.yaml
# ---------------------------------------------------------------------------

class TestManifestSchema:
    """Validate the real manifest has expected structure and required fields."""

    REQUIRED_ENTRY_FIELDS = {
        "name", "upstream_url", "spdx", "status",
        "copyright", "attribution", "cos_files", "annex_f",
    }

    ALLOWED_STATUSES = {"ALLOWED", "BLOCKED", "HOLD", "TRIAL-PATTERNS", "PATTERN-ONLY"}

    def _load_manifest(self, gen) -> dict[str, Any]:
        return gen._parse_yaml_manifest(_MANIFEST_PATH)

    def test_manifest_file_exists(self):
        assert _MANIFEST_PATH.exists(), f"Manifest not found at {_MANIFEST_PATH}"

    def test_schema_version_present(self, gen):
        manifest = self._load_manifest(gen)
        assert "schema_version" in manifest
        assert manifest["schema_version"] == 1

    def test_entries_list_non_empty(self, gen):
        manifest = self._load_manifest(gen)
        entries = manifest.get("entries", [])
        assert len(entries) > 0, "Manifest must have at least one entry"

    def test_every_entry_has_required_fields(self, gen):
        manifest = self._load_manifest(gen)
        for entry in manifest["entries"]:
            missing = self.REQUIRED_ENTRY_FIELDS - set(entry.keys())
            assert not missing, (
                f"Entry '{entry.get('name', '?')}' missing fields: {missing}"
            )

    def test_cos_files_is_list(self, gen):
        manifest = self._load_manifest(gen)
        for entry in manifest["entries"]:
            assert isinstance(entry.get("cos_files"), list), (
                f"Entry '{entry.get('name')}' cos_files must be a list"
            )

    def test_all_statuses_are_known(self, gen):
        manifest = self._load_manifest(gen)
        for entry in manifest["entries"]:
            status = entry.get("status", "")
            assert status in self.ALLOWED_STATUSES, (
                f"Entry '{entry.get('name')}' has unexpected status: {status!r}"
            )

    def test_expected_entries_present(self, gen):
        """The eight tools from the audit brief must all be represented."""
        manifest = self._load_manifest(gen)
        names = {e["name"] for e in manifest["entries"]}
        expected = {
            "Hermes Agent",
            "HKUDS/OpenHarness",
            "Pi coding-agent",
            "Sprut Agent Kit",
            "HelixDB",
            "iFixAi",
            "MegaMemory",
            "holaOS",
        }
        missing = expected - names
        assert not missing, f"Expected entries not found in manifest: {missing}"

    def test_helixdb_is_agpl_trial_patterns(self, gen):
        manifest = self._load_manifest(gen)
        helix = next(e for e in manifest["entries"] if e["name"] == "HelixDB")
        assert helix["spdx"] == "AGPL-3.0"
        assert helix["status"] == "TRIAL-PATTERNS"

    def test_sprut_and_pi_are_blocked_or_hold(self, gen):
        manifest = self._load_manifest(gen)
        for name in ("Sprut Agent Kit", "Pi coding-agent"):
            entry = next(e for e in manifest["entries"] if e["name"] == name)
            assert entry["status"] in ("BLOCKED", "HOLD"), (
                f"{name} should be BLOCKED or HOLD, got {entry['status']!r}"
            )


# ---------------------------------------------------------------------------
# 2. Generator output matches expected fixture for a known-input case
# ---------------------------------------------------------------------------

class TestGeneratorOutput:
    """Test that _generate_notice_md produces expected content."""

    def test_notice_contains_auto_generated_header(self, gen, minimal_entries):
        notice = gen._generate_notice_md(minimal_entries, [], "oss")
        assert "auto-generated" in notice.lower()

    def test_notice_contains_section_headers(self, gen, minimal_entries):
        notice = gen._generate_notice_md(minimal_entries, [], "oss")
        assert "§1" in notice
        assert "§2" in notice
        assert "§3" in notice

    def test_notice_contains_entry_names(self, gen, minimal_entries):
        notice = gen._generate_notice_md(minimal_entries, [], "oss")
        assert "Fake MIT Lib" in notice
        assert "AGPL Lib" in notice

    def test_notice_contains_spdx(self, gen, minimal_entries):
        notice = gen._generate_notice_md(minimal_entries, [], "oss")
        assert "MIT" in notice
        assert "AGPL-3.0" in notice

    def test_notice_contains_copyright(self, gen, minimal_entries):
        notice = gen._generate_notice_md(minimal_entries, [], "oss")
        assert "Fake Author" in notice

    def test_notice_contains_license_summary_table(self, gen, minimal_entries):
        notice = gen._generate_notice_md(minimal_entries, [], "oss")
        assert "License Families Summary" in notice

    def test_third_party_contains_entry_names(self, gen, minimal_entries):
        txt = gen._generate_third_party_licenses(minimal_entries)
        assert "Fake MIT Lib" in txt
        assert "AGPL Lib" in txt

    def test_third_party_has_separators(self, gen, minimal_entries):
        txt = gen._generate_third_party_licenses(minimal_entries)
        assert "=" * 10 in txt  # separator lines

    def test_third_party_mit_includes_permission_text(self, gen, minimal_entries):
        txt = gen._generate_third_party_licenses(minimal_entries)
        assert "Permission is hereby granted" in txt

    def test_third_party_agpl_includes_no_vendoring_note(self, gen, minimal_entries):
        txt = gen._generate_third_party_licenses(minimal_entries)
        assert "REJECTED" in txt or "no upstream" in txt.lower() or "TRIAL-PATTERNS" in txt

    def test_transitive_deps_appear_in_table(self, gen, minimal_entries):
        deps = [
            {"name": "requests", "version": "2.31.0", "license": "Apache-2.0", "url": "https://github.com/psf/requests"},
        ]
        notice = gen._generate_notice_md(minimal_entries, deps, "oss")
        assert "requests" in notice
        assert "2.31.0" in notice


# ---------------------------------------------------------------------------
# 3. --check mode detects drift
# ---------------------------------------------------------------------------

class TestCheckMode:
    """Test that --check exits 0 on match and 1 on drift."""

    def test_check_exits_0_when_files_match(self, gen, tmp_path, minimal_manifest_file):
        # Generate files first
        rc_gen = gen.main(["--out", str(tmp_path), "--manifest", str(minimal_manifest_file)])
        assert rc_gen == 0

        # --check should pass
        rc_check = gen.main([
            "--check",
            "--out", str(tmp_path),
            "--manifest", str(minimal_manifest_file),
        ])
        assert rc_check == 0

    def test_check_exits_1_when_notice_mutated(self, gen, tmp_path, minimal_manifest_file):
        # Generate files
        gen.main(["--out", str(tmp_path), "--manifest", str(minimal_manifest_file)])

        # Mutate NOTICE.md
        notice_path = tmp_path / "NOTICE.md"
        original = notice_path.read_text(encoding="utf-8")
        notice_path.write_text(original + "\n<!-- MANUALLY INJECTED DRIFT -->\n", encoding="utf-8")

        rc_check = gen.main([
            "--check",
            "--out", str(tmp_path),
            "--manifest", str(minimal_manifest_file),
        ])
        assert rc_check == 1

    def test_check_exits_1_when_third_party_mutated(self, gen, tmp_path, minimal_manifest_file):
        gen.main(["--out", str(tmp_path), "--manifest", str(minimal_manifest_file)])

        tp_path = tmp_path / "THIRD_PARTY_LICENSES.txt"
        original = tp_path.read_text(encoding="utf-8")
        tp_path.write_text(original + "\nDRIFT INJECTED\n", encoding="utf-8")

        rc_check = gen.main([
            "--check",
            "--out", str(tmp_path),
            "--manifest", str(minimal_manifest_file),
        ])
        assert rc_check == 1

    def test_check_exits_1_when_files_missing(self, gen, tmp_path, minimal_manifest_file):
        # Don't generate first — files don't exist
        rc_check = gen.main([
            "--check",
            "--out", str(tmp_path),
            "--manifest", str(minimal_manifest_file),
        ])
        assert rc_check == 1


# ---------------------------------------------------------------------------
# 4. --mode oss vs --mode saas produce different output for copyleft entry
# ---------------------------------------------------------------------------

class TestOssSaasMode:
    """Test that oss mode flags copyleft entries more prominently than saas."""

    def test_oss_mode_flags_agpl_copyleft(self, gen, minimal_entries):
        notice_oss = gen._generate_notice_md(minimal_entries, [], "oss")
        # OSS mode should include a copyleft warning for AGPL entry
        assert "COPYLEFT" in notice_oss or "copyleft" in notice_oss.lower() or "OSS MODE WARNING" in notice_oss

    def test_saas_mode_does_not_warn_on_agpl(self, gen, minimal_entries):
        notice_saas = gen._generate_notice_md(minimal_entries, [], "saas")
        # saas mode should NOT emit the OSS-specific warning
        assert "OSS MODE WARNING" not in notice_saas

    def test_oss_and_saas_output_differ_for_copyleft(self, gen, minimal_entries):
        notice_oss = gen._generate_notice_md(minimal_entries, [], "oss")
        notice_saas = gen._generate_notice_md(minimal_entries, [], "saas")
        # The outputs must differ at least by the warning text
        assert notice_oss != notice_saas

    def test_oss_mode_flags_copyleft_in_transitive_deps(self, gen, minimal_entries):
        deps = [
            {"name": "gpl-lib", "version": "1.0", "license": "GPL-3.0", "url": ""},
            {"name": "safe-lib", "version": "1.0", "license": "MIT", "url": ""},
        ]
        notice_oss = gen._generate_notice_md(minimal_entries, deps, "oss")
        # GPL dep should be flagged in oss mode
        assert "COPYLEFT" in notice_oss

    def test_saas_mode_does_not_flag_transitive_deps(self, gen, minimal_entries):
        deps = [
            {"name": "gpl-lib", "version": "1.0", "license": "GPL-3.0", "url": ""},
        ]
        notice_saas = gen._generate_notice_md(minimal_entries, deps, "saas")
        assert "COPYLEFT" not in notice_saas

    def test_mode_arg_accepted_in_main(self, gen, tmp_path, minimal_manifest_file):
        for mode in ("oss", "saas"):
            rc = gen.main([
                "--mode", mode,
                "--out", str(tmp_path),
                "--manifest", str(minimal_manifest_file),
            ])
            assert rc == 0, f"main() returned {rc} for --mode {mode}"
