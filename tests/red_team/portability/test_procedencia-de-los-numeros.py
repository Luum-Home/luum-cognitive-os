# SCOPE: os-only
"""Prueba de portabilidad de rules/procedencia-de-los-numeros.md.

Sigue el patron de las demas sondas de reglas --copiar a una raiz arbitraria y
verificar que el texto sobreviva-- y le agrega la unica asercion que le importa a
ESTA regla en particular: que su tabla de evidencia viaje entera.

Una regla que dice "ningun numero viaja sin su comando" y que al instalarse en
otro proyecto perdiera los diez casos que la fundamentan seria, ella misma, una
afirmacion sin respaldo. La tabla ES el respaldo.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "rules/procedencia-de-los-numeros.md"


def test_procedencia_de_los_numeros_loads_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Sonda de falsacion: la primitiva de documentacion debe servir fuera del repo."""
    target = tmp_path / ARTIFACT.name
    target.write_text(ARTIFACT.read_text(encoding="utf-8"), encoding="utf-8")
    text = target.read_text(encoding="utf-8")
    assert "SCOPE: both" in text
    assert str(REPO_ROOT) not in text


def test_la_evidencia_viaja_con_la_regla(tmp_path: Path) -> None:
    """La tabla de los diez casos es el respaldo, no un adorno historico."""
    target = tmp_path / ARTIFACT.name
    target.write_text(ARTIFACT.read_text(encoding="utf-8"), encoding="utf-8")
    text = target.read_text(encoding="utf-8")

    assert text.count("|") > 40, "la tabla de evidencia no sobrevivio la copia"
    assert "relatado, sin verificar" in text, "falta la salida cuando no hay comando"
    assert "reimplement" in text.lower(), "falta el segundo tramo: correr, no reimplementar"
