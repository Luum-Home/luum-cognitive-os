from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC = PROJECT_ROOT / "docs" / "manual-tests" / "local-connected-systems-validation.md"


def test_local_connected_systems_validation_uses_manifest_as_source_of_truth() -> None:
    text = DOC.read_text(encoding="utf-8")

    assert "manifests/dependencies.yaml" in text
    assert "scripts/manifest-check.sh" in text
    assert "scripts/setup.sh" in text
    assert "scripts/cos-doctor-tools.sh" in text
    assert text.index("## Source of Truth") < text.index("## Profiles")


def test_local_connected_systems_validation_bounds_automatic_installation() -> None:
    text = DOC.read_text(encoding="utf-8")

    assert "## Automatic Install Boundary" in text
    assert "is advisory by default" in text
    assert "Heavy services must be explicit" in text
    assert "Secrets must come from environment variables" in text
    assert "full profile never runs implicitly" in text


def test_local_connected_systems_validation_proves_connected_runtime_steps() -> None:
    text = DOC.read_text(encoding="utf-8")

    required_sections = [
        "### 1. Verify declared dependencies",
        "### 2. Install profile dependencies intentionally",
        "### 3. Verify harness and MCP wiring",
        "### 4. Verify memory lifecycle",
        "### 5. Start optional connected services only when requested",
        "### 6. Run a persistent test summary",
    ]
    for section in required_sections:
        assert section in text

    assert "scripts/cos-bootstrap.sh --profile full" in text
    assert "scripts/pytest-with-summary.sh tests/ -m" in text


def test_local_connected_systems_validation_is_linked_from_entrypoints() -> None:
    docs_readme = (PROJECT_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    runtime_plan = (
        PROJECT_ROOT / "docs" / "architecture" / "plans" / "headless-clustered-runtime-plan.md"
    ).read_text(encoding="utf-8")
    checklist = (PROJECT_ROOT / "docs" / "business" / "master-plan-checklist.md").read_text(
        encoding="utf-8"
    )

    assert docs_readme.count("manual-tests/local-connected-systems-validation.md") == 1
    assert runtime_plan.count("manual-tests/local-connected-systems-validation.md") == 2
    assert checklist.count("manual-tests/local-connected-systems-validation.md") == 1
