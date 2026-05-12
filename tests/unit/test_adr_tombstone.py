from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.adr_tombstone import create_tombstone, render_tombstone, validate_tombstone_text


def test_render_tombstone_is_contract_compliant() -> None:
    text = render_tombstone(
        number=42,
        title="Removed architecture decision",
        reason="This slot is intentionally reserved.",
        date="2026-05-05",
    )

    assert validate_tombstone_text(text, number=42, forbidden_tokens=("removed-name",)) == []
    assert "# ADR-042: Removed architecture decision" in text
    assert "status: tombstone" in text
    assert "## Alternatives rejected" in text
    assert "## Verification" in text


def test_create_tombstone_refuses_to_replace_active_adr_by_default(tmp_path: Path) -> None:
    project = tmp_path
    adrs = project / "docs" / "adrs"
    adrs.mkdir(parents=True)
    old = adrs / "ADR-007-old-system.md"
    old.write_text("# ADR-007: Old System\n\nlegacy-token\n", encoding="utf-8")

    try:
        create_tombstone(
            project_dir=project,
            number=7,
            title="Removed architecture decision",
            reason="The old decision was removed.",
            date="2026-05-05",
        )
    except ValueError as exc:
        assert "active ADR file" in str(exc)
    else:
        raise AssertionError("expected active ADR replacement to be blocked")

    assert old.exists()


def test_create_tombstone_force_replaces_old_file_and_updates_references(tmp_path: Path) -> None:
    project = tmp_path
    adrs = project / "docs" / "adrs"
    adrs.mkdir(parents=True)
    old = adrs / "ADR-007-old-system.md"
    old.write_text("# ADR-007: Old System\n\nlegacy-token\n", encoding="utf-8")
    readme = project / "docs" / "README.md"
    readme.parent.mkdir(exist_ok=True)
    readme.write_text("See ADR-007-old-system.md.\n", encoding="utf-8")

    result = create_tombstone(
        project_dir=project,
        number=7,
        title="Removed architecture decision",
        reason="The old decision was removed.",
        date="2026-05-05",
        forbidden_tokens=("legacy-token",),
        force_replace_active=True,
    )

    target = project / result.path
    assert target.exists()
    assert not old.exists()
    assert result.removed_paths == ["docs/02-Decisions/adrs/ADR-007-old-system.md"]
    assert result.updated_references == ["docs/00-MOCs/entrypoints/README.md"]
    assert "ADR-007-tombstone.md" in readme.read_text(encoding="utf-8")
    assert "legacy-token" not in target.read_text(encoding="utf-8")


def test_create_tombstone_can_validate_forbidden_tokens(tmp_path: Path) -> None:
    project = tmp_path
    (project / "docs" / "adrs").mkdir(parents=True)
    note = project / "docs" / "note.md"
    note.parent.mkdir(exist_ok=True)
    note.write_text("forbidden-surface\n", encoding="utf-8")

    try:
        create_tombstone(
            project_dir=project,
            number=9,
            title="Removed architecture decision",
            reason="Removed.",
            date="2026-05-05",
            forbidden_tokens=("forbidden-surface",),
            validate_forbidden_tokens=True,
        )
    except ValueError as exc:
        assert "Forbidden token" in str(exc)
    else:
        raise AssertionError("expected forbidden token validation to fail")


def test_cli_json_dry_run(tmp_path: Path) -> None:
    project = tmp_path
    (project / "docs" / "adrs").mkdir(parents=True)
    script = Path(__file__).resolve().parents[2] / "scripts" / "adr_tombstone.py"

    result = subprocess.run(
        [
            "python3",
            str(script),
            "--project-dir",
            str(project),
            "--number",
            "11",
            "--date",
            "2026-05-05",
            "--dry-run",
            "--json",
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["wrote"] is False
    assert payload["path"] == "docs/02-Decisions/adrs/ADR-011-tombstone.md"
    assert not (project / payload["path"]).exists()
