from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / ".cognitive-os" / "migrations" / "test-architecture-inventory.md"
ADR = ROOT / "docs" / "02-Decisions" / "adrs" / "ADR-073-test-architecture-role-registry.md"
ROLES = {"Selection", "Execution", "Reporting", "Governance", "Lifecycle"}


def _markdown_table_rows(path: Path, expected_columns: int) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| "):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != expected_columns:
            continue
        if cells[0] in {"Role", "---"}:
            continue
        if set(cells) == {"---"}:
            continue
        rows.append(cells)
    return rows


def _inventory_rows() -> list[dict[str, str]]:
    parsed: list[dict[str, str]] = []
    for cells in _markdown_table_rows(INVENTORY, 7):
        if cells[0] not in ROLES:
            continue
        parsed.append(
            {
                "role": cells[0],
                "primitive": cells[1],
                "path": cells[2],
                "purpose": cells[3],
                "status": cells[4],
                "owner": cells[5],
                "action": cells[6],
            }
        )
    return parsed


def test_inventory_assigns_each_test_primitive_to_exactly_one_role() -> None:
    rows = _inventory_rows()
    assert len(rows) >= 30

    by_primitive: dict[str, set[str]] = {}
    for row in rows:
        by_primitive.setdefault(row["primitive"], set()).add(row["role"])

    duplicates = {primitive: roles for primitive, roles in by_primitive.items() if len(roles) != 1}
    assert duplicates == {}
    assert {row["role"] for row in rows} == ROLES


def test_inventory_records_overlap_and_resource_governance_gap() -> None:
    text = INVENTORY.read_text(encoding="utf-8")
    assert "test-all.sh` | `Deprecation path" not in text

    overlap_rows = _markdown_table_rows(INVENTORY, 3)
    resolutions = {cells[0]: cells[2] for cells in overlap_rows if cells[0] not in {"Overlap / gap", "Primitive"}}
    assert any("Three “smoke/all”" in key for key in resolutions)
    assert any("Resource governance" in key for key in resolutions)
    assert any("separate sprint" in value for value in resolutions.values())


def test_adr_canonical_map_matches_inventory_boundaries() -> None:
    inventory_rows = _inventory_rows()
    inventory_by_path = {row["path"]: row["role"] for row in inventory_rows}
    adr_text = ADR.read_text(encoding="utf-8")

    expected = {
        ".cognitive-os/test-lanes.yaml": "Selection",
        "cmd/cos-test/main.go": "Execution",
        "scripts/pytest-with-summary.sh": "Reporting",
        "hooks/auto-verify.sh": "Governance",
        ".cognitive-os/reports/test-runs/": "Reporting",
    }
    assert {path: inventory_by_path[path] for path in expected} == expected
    assert "Resource governance is intentionally not solved in this ADR" in adr_text
