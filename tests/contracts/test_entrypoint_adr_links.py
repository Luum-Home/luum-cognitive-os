"""Contract for entrypoint ADR links."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check_entrypoint_adr_links.py"
spec = importlib.util.spec_from_file_location("check_entrypoint_adr_links", SCRIPT)
assert spec and spec.loader
check_entrypoint_adr_links = importlib.util.module_from_spec(spec)
sys.modules["check_entrypoint_adr_links"] = check_entrypoint_adr_links
spec.loader.exec_module(check_entrypoint_adr_links)


def test_entrypoint_adr_links_resolve_to_canonical_adr_files() -> None:
    missing = check_entrypoint_adr_links.find_broken_links(ROOT)
    assert not missing, "Broken entrypoint ADR links:\n" + "\n".join(missing)


def test_entrypoint_adr_link_checker_catches_missing_adr(tmp_path: Path) -> None:
    readme = tmp_path / "docs/00-MOCs/entrypoints/README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text(
        "[ADR-999](../../02-Decisions/adrs/ADR-999-missing.md)\n", encoding="utf-8"
    )
    (tmp_path / "docs/02-Decisions/adrs").mkdir(parents=True)

    missing = check_entrypoint_adr_links.find_broken_links(tmp_path)

    assert missing == [
        "docs/00-MOCs/entrypoints/README.md -> ../../02-Decisions/adrs/ADR-999-missing.md"
    ]


def test_checker_does_not_normalise_away_a_wrong_relative_path(tmp_path: Path) -> None:
    """Un link que solo resuelve desde el root de ADRs debe reportarse igual.

    Es el defecto que el checker tenia: resolvia cada target contra
    docs/02-Decisions/adrs en vez del directorio del archivo que enlaza,
    asi que una ruta que ningun lector puede seguir parecia valida. El contrato
    viejo asserteaba ese comportamiento, y por eso el bug sobrevivio: estaba fijado.
    """
    readme = tmp_path / "docs/00-MOCs/entrypoints/README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("[ADR-001](adrs/ADR-001-real.md)\n", encoding="utf-8")
    adrs = tmp_path / "docs/02-Decisions/adrs"
    adrs.mkdir(parents=True)
    (adrs / "ADR-001-real.md").write_text("# real\n", encoding="utf-8")

    missing = check_entrypoint_adr_links.find_broken_links(tmp_path)

    assert missing == [
        "docs/00-MOCs/entrypoints/README.md -> adrs/ADR-001-real.md"
    ], "el ADR existe, pero no donde este link apunta desde su ubicacion"
