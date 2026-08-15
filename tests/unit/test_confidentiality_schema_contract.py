"""Contract tests binding the shipped confidentiality template to its parser.

Root cause these tests exist to prevent (2026-08-15): the shipped template
declared ``protected_terms`` / ``protected_orgs`` / ``scan_external_paths``
while ``load_protected_terms`` only ever read ``project_names`` /
``client_names`` / ``repo_urls`` / ``org_names``. A config written against the
template loaded zero terms, and the scanner reported nothing — silently, with
no error on either side. The mismatch survived because nothing asserted that
the two agreed.

Every test here fails if a key is documented without being consumed, or
consumed without surviving a round trip through the template.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cos_lib.confidentiality_scanner import (
    CONFIG_KEYS,
    ProtectedTerms,
    load_protected_terms,
    scan_text,
)

pytestmark = [pytest.mark.unit, pytest.mark.behavior]

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = REPO_ROOT / "templates" / "confidentiality.yaml"


def _template_top_level_keys(text: str) -> set[str]:
    """Top-level YAML keys, read without requiring PyYAML."""
    keys: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip() or line[0].isspace():
            continue
        if ":" in line:
            keys.add(line.split(":", 1)[0].strip())
    return keys


# ---------------------------------------------------------------------------
# The contract itself
# ---------------------------------------------------------------------------


def test_template_exists_in_a_versioned_path():
    """The template must live somewhere git tracks, or it cannot be shipped.

    Its previous home, .cognitive-os/templates/, is ignored by .gitignore:8
    (".cognitive-os/*"), so no installer path could ever have taken it.
    """
    assert TEMPLATE.is_file(), f"missing shipped template: {TEMPLATE}"


def test_every_template_key_is_consumed_by_the_loader():
    """No key may be documented in the template that the parser ignores."""
    declared = _template_top_level_keys(TEMPLATE.read_text(encoding="utf-8"))
    unconsumed = declared - set(CONFIG_KEYS)
    assert not unconsumed, (
        f"template declares keys the loader never reads: {sorted(unconsumed)}. "
        "Either consume them in load_protected_terms() or delete them from the "
        "template — a documented key that does nothing is the 2026-08-15 defect."
    )


def test_every_active_loader_key_is_documented_in_the_template():
    """No active key may be readable by the parser but undiscoverable by users.

    Legacy aliases are deliberately exempt: they are accepted for backward
    compatibility and documented in prose, not as live keys.
    """
    legacy = {"protected_terms", "protected_orgs"}
    declared = _template_top_level_keys(TEMPLATE.read_text(encoding="utf-8"))
    undocumented = (set(CONFIG_KEYS) - legacy) - declared
    assert not undocumented, (
        f"loader reads keys absent from the template: {sorted(undocumented)}"
    )


# ---------------------------------------------------------------------------
# Round trip: a filled config must actually produce terms
# ---------------------------------------------------------------------------


def test_filled_modern_config_round_trips(tmp_path: Path):
    """The canonical schema loads every category."""
    cfg = tmp_path / "confidentiality.yaml"
    cfg.write_text(
        "project_names:\n"
        "  - internal-codename\n"
        "client_names:\n"
        "  - acme-corp\n"
        "repo_urls:\n"
        "  - private-org/service\n"
        "org_names:\n"
        "  - private-org\n"
        "scan_external_paths: false\n",
        encoding="utf-8",
    )
    terms = load_protected_terms(str(cfg))

    assert terms.project_names == ["internal-codename"]
    assert terms.client_names == ["acme-corp"]
    assert terms.repo_urls == ["private-org/service"]
    assert terms.org_names == ["private-org"]
    assert terms.scan_external_paths is False


def test_legacy_config_no_longer_loads_empty(tmp_path: Path):
    """The exact shape that used to load zero terms must now load terms.

    This is the regression test for the original defect: a config written
    against the old template.
    """
    cfg = tmp_path / "confidentiality.yaml"
    cfg.write_text(
        "protected_terms:\n"
        '  - term: "internal-codename"\n'
        '    reason: "internal project reference"\n'
        "protected_orgs:\n"
        '  - "my-private-org"\n'
        "scan_external_paths: true\n",
        encoding="utf-8",
    )
    terms = load_protected_terms(str(cfg))

    assert terms.project_names == ["internal-codename"], (
        "legacy protected_terms must fold into project_names; loading empty "
        "here is the silent no-op this contract exists to prevent"
    )
    assert terms.org_names == ["my-private-org"]
    assert terms.scan_external_paths is True
    # The reason field is metadata, never a protected term.
    assert "internal project reference" not in terms.project_names


def test_legacy_plain_string_list_also_folds(tmp_path: Path):
    """protected_terms written as plain strings is accepted too."""
    cfg = tmp_path / "confidentiality.yaml"
    cfg.write_text('protected_terms:\n  - "codename-one"\n  - "codename-two"\n', encoding="utf-8")
    terms = load_protected_terms(str(cfg))
    assert terms.project_names == ["codename-one", "codename-two"]


def test_modern_and_legacy_merge_without_duplicates(tmp_path: Path):
    """Both spellings may coexist; values merge and de-duplicate."""
    cfg = tmp_path / "confidentiality.yaml"
    cfg.write_text(
        "project_names:\n  - shared\n  - only-modern\n"
        "protected_terms:\n  - shared\n  - only-legacy\n",
        encoding="utf-8",
    )
    terms = load_protected_terms(str(cfg))
    assert terms.project_names == ["shared", "only-modern", "only-legacy"]


def test_shipped_template_loads_without_error_and_is_empty():
    """The template as shipped is a valid, inert config."""
    terms = load_protected_terms(str(TEMPLATE))
    assert terms.project_names == []
    assert terms.client_names == []
    assert terms.repo_urls == []
    assert terms.org_names == []
    assert terms.scan_external_paths is True


# ---------------------------------------------------------------------------
# scan_external_paths must actually gate the scan
# ---------------------------------------------------------------------------


def test_scan_external_paths_false_suppresses_path_violations():
    """A documented toggle that the scanner ignores is the same class of bug."""
    text = f"see {Path('/') / 'Users' / 'someone' / 'Projects' / 'other' / 'a.py'}"

    on = scan_text(text, current_project_dir="", terms=ProtectedTerms())
    assert any(v.pattern_type == "external_path" for v in on)

    off = scan_text(
        text,
        current_project_dir="",
        terms=ProtectedTerms(scan_external_paths=False),
    )
    assert not any(v.pattern_type == "external_path" for v in off)


def test_scan_external_paths_defaults_to_on():
    """Absent config must not silently disable the one detection that works."""
    assert ProtectedTerms().scan_external_paths is True
    assert load_protected_terms("/nonexistent/confidentiality.yaml").scan_external_paths is True
