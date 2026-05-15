from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EAS_DOC = ROOT / "docs/05-Methodology/root/executable-acceptance-specification.md"
EAS_TEMPLATE = ROOT / "templates/eas.md"
EAS_RULE = ROOT / "rules/eas-evidence-artifact.md"
EAS_ADR = ROOT / "docs/02-Decisions/adrs/ADR-324-executable-acceptance-specification-eas.md"
DETRACTOR_ADR = ROOT / "docs/02-Decisions/adrs/ADR-319-detractor-review-modes.md"
EAS_VALIDATOR = ROOT / "scripts/eas_validate.py"


REQUIRED_SECTIONS = [
    "Intent",
    "Requirements",
    "Non-goals",
    "Executable Acceptance Criteria",
    "Gap Matrix",
    "Adversarial Personas",
    "Detractor Mode",
    "Detractor Objection Log",
    "Verification Commands",
    "Residual Risks",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_eas_artifacts_exist() -> None:
    assert EAS_DOC.is_file()
    assert EAS_TEMPLATE.is_file()
    assert EAS_RULE.is_file()
    assert EAS_ADR.is_file()
    assert DETRACTOR_ADR.is_file()
    assert EAS_VALIDATOR.is_file()


def test_eas_doc_defines_required_sections() -> None:
    text = _read(EAS_DOC)
    for section in REQUIRED_SECTIONS:
        assert section in text


def test_eas_template_contains_required_sections() -> None:
    text = _read(EAS_TEMPLATE)
    for section in REQUIRED_SECTIONS:
        assert f"## {section}" in text


def test_eas_detractor_role_names_selectable_modes_sources_and_adr() -> None:
    doc = _read(EAS_DOC)
    template = _read(EAS_TEMPLATE)
    rule = _read(EAS_RULE)
    adr = _read(EAS_ADR) + "\n" + _read(DETRACTOR_ADR)
    corpus = "\n".join([doc, template, rule, adr])

    for mode in ["Tenth Man Rule", "Devil's Advocate", "Pre-mortem", "Black Hat", "Red Team"]:
        assert mode in corpus

    for source in ["Brookings", "CIA", "de Bono", "Mollick", "Microsoft"]:
        assert source in corpus

    assert "ADR-319" in doc


def test_eas_doc_rule_and_template_distinguish_eas_from_ears() -> None:
    corpus = "\n".join([_read(EAS_DOC), _read(EAS_TEMPLATE), _read(EAS_RULE), _read(EAS_ADR)])
    assert "Easy Approach to Requirements Syntax" in corpus
    assert "WHEN <event> THE SYSTEM SHALL" in corpus
    assert "IF <condition> THEN THE SYSTEM SHALL" in corpus
    assert "EARS is" in corpus


def test_eas_rule_points_to_template_validator_and_sdd_integration() -> None:
    text = _read(EAS_RULE)
    assert "templates/eas.md" in text
    assert "scripts/eas_validate.py" in text
    for phase in ["sdd-spec", "sdd-tasks", "sdd-apply", "sdd-verify", "sdd-archive"]:
        assert phase in text


def test_eas_validator_rejects_incomplete_artifact(tmp_path: Path) -> None:
    import subprocess

    incomplete = tmp_path / "incomplete-eas.md"
    incomplete.write_text("# EAS: incomplete\n\n## Intent\nOnly intent is present.\n", encoding="utf-8")

    result = subprocess.run(
        ["python3", "scripts/eas_validate.py", str(incomplete)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode != 0
    assert "missing required section" in result.stdout.lower()
