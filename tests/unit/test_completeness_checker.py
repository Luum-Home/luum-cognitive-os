import pytest

from lib.completeness_checker import (
    check_artifact,
    check_predev_artifacts,
    format_report,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# check_artifact
# ---------------------------------------------------------------------------


def test_check_artifact_missing_directory(tmp_path):
    status = check_artifact(str(tmp_path), "docs/01-context/")
    assert status.exists is False
    assert status.file_count == 0
    assert status.last_modified is None


def test_check_artifact_exists_with_md_files(tmp_path):
    artifact_dir = tmp_path / "docs" / "01-context"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "context.md").write_text("# Context")
    (artifact_dir / "extra.md").write_text("# Extra")

    status = check_artifact(str(tmp_path), "docs/01-context/")
    assert status.exists is True
    assert status.file_count == 2
    assert status.last_modified is not None


def test_empty_directory_not_counted(tmp_path):
    """An existing directory with no .md files is NOT considered present."""
    artifact_dir = tmp_path / "docs" / "01-context"
    artifact_dir.mkdir(parents=True)
    # No .md files — only a non-md file
    (artifact_dir / "notes.txt").write_text("some text")

    status = check_artifact(str(tmp_path), "docs/01-context/")
    assert status.exists is True
    assert status.file_count == 0
    assert status.last_modified is None

    # The report must treat this as missing
    report = check_predev_artifacts(str(tmp_path))
    assert "context" in report.missing


# ---------------------------------------------------------------------------
# check_predev_artifacts — verdict logic
# ---------------------------------------------------------------------------


def test_all_required_present_is_ready(tmp_path):
    """When all required artifact directories contain at least one .md file, verdict is READY."""
    required_paths = [
        "docs/01-context/context.md",
        "docs/04-security/threats.md",
        "docs/09-execution-plan/plan.md",
    ]
    for rel in required_paths:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# content")

    report = check_predev_artifacts(str(tmp_path))

    assert report.verdict == "READY"
    assert report.missing == []
    assert set(report.present) == {"context", "threat-model", "execution-plan"}


def test_missing_required_is_not_ready(tmp_path):
    """When only one required artifact is present the verdict is NOT_READY for zero, PARTIAL for one."""
    # Only context is present
    ctx_dir = tmp_path / "docs" / "01-context"
    ctx_dir.mkdir(parents=True)
    (ctx_dir / "context.md").write_text("# Context")

    report = check_predev_artifacts(str(tmp_path))

    # One of three required present → PARTIAL (not NOT_READY)
    assert report.verdict == "PARTIAL"
    assert "threat-model" in report.missing
    assert "execution-plan" in report.missing
    assert "context" in report.present


def test_no_required_present_is_not_ready(tmp_path):
    """When none of the required artifacts exist, verdict must be NOT_READY."""
    report = check_predev_artifacts(str(tmp_path))

    assert report.verdict == "NOT_READY"
    assert set(report.missing) == {"context", "threat-model", "execution-plan"}
    assert report.present == []


# ---------------------------------------------------------------------------
# Optional artifacts
# ---------------------------------------------------------------------------


def test_optional_artifacts_tracked_separately(tmp_path):
    # Satisfy all required
    for rel in [
        "docs/01-context/c.md",
        "docs/04-security/t.md",
        "docs/09-execution-plan/p.md",
    ]:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")

    # Add one optional
    arch = tmp_path / "docs" / "02-architecture"
    arch.mkdir(parents=True)
    (arch / "arch.md").write_text("# arch")

    report = check_predev_artifacts(str(tmp_path))

    assert report.verdict == "READY"
    assert "architecture" in report.optional_present
    assert "features" in report.optional_missing


# ---------------------------------------------------------------------------
# format_report
# ---------------------------------------------------------------------------


def test_format_report_ready(tmp_path):
    for rel in [
        "docs/01-context/c.md",
        "docs/04-security/t.md",
        "docs/09-execution-plan/p.md",
    ]:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")

    report = check_predev_artifacts(str(tmp_path))
    text = format_report(report)

    assert "READY" in text
    assert "✓" in text


def test_format_report_missing_shows_skill_hint(tmp_path):
    report = check_predev_artifacts(str(tmp_path))
    text = format_report(report)

    assert "NOT_READY" in text
    assert "/sdd-explore" in text   # hint for context
    assert "/security-audit" in text  # hint for threat-model
    assert "/plan-feature" in text  # hint for execution-plan
